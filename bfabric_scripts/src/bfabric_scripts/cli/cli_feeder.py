from pathlib import Path
import datetime
import sys
import cyclopts
from loguru import logger
from pydantic import BaseModel

from bfabric import Bfabric
from bfabric.entities import Storage, Application
from bfabric.utils.cli_integration import use_client
from bfabric_scripts.feeder.application_mapping import SystemConfig, load_or_update_cache
from bfabric_scripts.feeder.file_attributes import FileAttributes
from bfabric_scripts.feeder.import_resource_db import ImportResourcesDB, RegistrationStatus
from bfabric_scripts.feeder.path_convention_compms import PathConventionCompMS, ParsedPath
from bfabric_scripts.feeder.register_importresources import register_import_resources


class ImportResourcePath(BaseModel):
    relative_path: Path
    application_name: str


def _create_importresources(storage_id: int, files: list[Path], client: Bfabric) -> None:
    storage = client.reader.read_id("storage", storage_id, expected_type=Storage)
    if storage is None:
        raise ValueError(f"Storage with ID {storage_id} not found.")

    # Parse the paths
    convention = PathConventionCompMS(storage=storage)
    parsed_paths = [convention.parse_absolute_path(absolute_path=file) for file in files]

    # Obtain the mapping for application names and ids
    application_mapping = _get_application_mapping(parsed_paths=parsed_paths, client=client)

    # Create the entities in B-Fabric.
    for parsed_path in parsed_paths:
        importresource_data = _generate_importresource_object(
            storage=storage, parsed_path=parsed_path, application_mapping=application_mapping
        )
        if importresource_data is not None:
            _create_importresource(importresource_data=importresource_data, parsed_path=parsed_path, client=client)


def _create_importresource(importresource_data: dict[str, str | int], parsed_path: ParsedPath, client: Bfabric):
    result = client.save("importresource", importresource_data)
    logger.trace("Created importresource: {}", result)
    if len(result) == 1:
        datestring = result[0]["created"]
        if not isinstance(datestring, str):
            raise ValueError("created field is not a string")
        importresource_id = result[0]["id"]
        importtresource_datetime = datetime.datetime.fromisoformat(datestring)
        delay = datetime.datetime.now() - importtresource_datetime
        if delay > datetime.timedelta(seconds=30):
            logger.info(f"Importresource {importresource_id} updated for file {parsed_path.absolute_path}.")
        else:
            logger.success(f"Importresource {importresource_id} created for file {parsed_path.absolute_path}.")


def _get_application_mapping(parsed_paths: list[ParsedPath], client: Bfabric) -> dict[str, int]:
    unique_app_names = {parsed_path.application_name for parsed_path in parsed_paths}
    if not unique_app_names:
        # Could be demoted to empty dictionary later.
        raise RuntimeError("Nothing to be processed.")
    # TODO this will have to be cached in the future and only request if there is anything missing
    result = Application.find_by({"name": sorted(unique_app_names)}, client=client, max_results=None)
    return {str(app["name"]): id for id, app in result.items()}


def _generate_importresource_object(
    storage: Storage, parsed_path: ParsedPath, application_mapping: dict[str, int]
) -> dict[str, str | int] | None:
    file_attributes = FileAttributes.compute(file=parsed_path.absolute_path)
    file_date = file_attributes.file_date.strftime("%Y-%m-%d %H:%M:%S")
    if parsed_path.application_name not in application_mapping:
        logger.error(
            f"Application {parsed_path.application_name} not found in B-Fabric. Skipping file {parsed_path.absolute_path}."
        )
        return None
    result = {
        "applicationid": application_mapping[parsed_path.application_name],
        "filechecksum": file_attributes.md5_checksum,
        "containerid": parsed_path.container_id,
        "filedate": file_date,
        "relativepath": str(parsed_path.relative_path),
        "name": parsed_path.relative_path.name,
        "size": file_attributes.file_size,
        "storageid": storage.id,
    }
    # TODO maybe this should be handled differently in the future
    if parsed_path.sample_id is not None:
        result["sampleid"] = parsed_path.sample_id
    return result


@use_client
def cmd_feeder_create_importresource(
    storage: int,
    files: list[Path],
    *,
    client: Bfabric,
) -> None:
    """Creates an importresource for each of the given files.

    :param storage: the target storage ID
    :param files: one or multiple file paths to create importresources for
    """
    # Normalize the file names to absolute
    files = [f.resolve() for f in files]
    missing = {f for f in files if not f.exists()}
    if missing:
        raise FileNotFoundError(f"Files {', '.join(map(str, missing))} do not exist.")

    # Execute
    _create_importresources(storage_id=storage, files=files, client=client)


def _parse_input_line(line: str) -> dict:
    """Parse a feeder input line into an entry dict.

    Accepts either pre-computed 'md5;timestamp;size;path' or just 'path' (computes attributes on-the-fly).
    """
    parts = line.split(";")
    if len(parts) == 4:
        md5, timestamp, size, path = parts
        return {
            "file_path": path.strip(),
            "file_size": int(size),
            "file_unix_timestamp": int(timestamp),
            "md5_checksum": md5.strip(),
        }
    elif len(parts) == 1:
        attrs = FileAttributes.compute(Path(line))
        return {
            "file_path": line,
            "file_size": attrs.file_size,
            "file_unix_timestamp": int(attrs.file_date.timestamp()),
            "md5_checksum": attrs.md5_checksum,
        }
    else:
        raise ValueError(f"Invalid input line format: {line!r}")


@use_client
def cmd_feeder_register_importresources(
    storage: int,
    db_path: Path,
    *,
    cache_path: Path | None = None,
    cache_ttl_hours: float = 24.0,
    client: Bfabric,
) -> None:
    """Registers importresources from stdin lines into bfabric with deduplication tracking.

    Each stdin line must be either 'md5;unix_timestamp;size;relative_path'
    or just 'relative_path' (file attributes are then computed on-the-fly).

    :param storage: the target storage ID
    :param db_path: path to the SQLite tracking database
    :param cache_path: path to the application mapping cache (default: db_path with .app_mapping.tsv suffix)
    :param cache_ttl_hours: how long to reuse the application mapping cache before refreshing it
    """
    if cache_path is None:
        cache_path = db_path.with_suffix(".app_mapping.tsv")

    storage_entity = client.reader.read_id("storage", storage, expected_type=Storage)
    if storage_entity is None:
        raise ValueError(f"Storage with ID {storage} not found.")

    feeder_config = SystemConfig(storage_id=storage)
    path_convention = PathConventionCompMS(storage=storage_entity)
    app_mapping = load_or_update_cache(path=cache_path, client=client, config=feeder_config, ttl_hours=cache_ttl_hours)

    entries = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(_parse_input_line(line))
        except Exception as e:
            logger.error(f"Failed to parse input line {line!r}: {e}")

    register_import_resources(
        entries=entries,
        db_path=str(db_path),
        bfabric_client=client,
        app_mapping=app_mapping,
        path_convention=path_convention,
        feeder_config=feeder_config,
    )


def _read_file_paths(file_paths: tuple[str, ...]) -> list[str]:
    """Read file paths from positional args, or from stdin if none are given."""
    if not file_paths:
        lines = [line.strip() for line in sys.stdin if line.strip()]
    else:
        lines = list(file_paths)
    return [_parse_input_line(line)["file_path"] for line in lines]


def cmd_feeder_db_status(
    db_path: Path,
    *file_paths: str,
) -> None:
    """Show the registration status of files in the tracking database.

    :param db_path: path to the SQLite tracking database
    :param file_paths: one or more file paths (or input lines); reads from stdin if omitted
    """
    paths = _read_file_paths(file_paths)
    with ImportResourcesDB(str(db_path)) as db:
        rows = db.get_entries_by_paths(paths)
    found = {r["file_path"]: r for r in rows}
    for path in paths:
        if path in found:
            row = found[path]
            status_name = RegistrationStatus(row["registration_status"]).name
            updated = datetime.datetime.fromtimestamp(row["status_updated_at"]).isoformat()
            print(f"{status_name}\t{updated}\t{path}")
        else:
            print(f"not_in_db\t-\t{path}")


def cmd_feeder_db_delete(
    db_path: Path,
    *file_paths: str,
) -> None:
    """Delete entries from the tracking database so they will be re-processed on the next run.

    :param db_path: path to the SQLite tracking database
    :param file_paths: one or more file paths (or input lines); reads from stdin if omitted
    """
    paths = _read_file_paths(file_paths)
    with ImportResourcesDB(str(db_path)) as db:
        deleted = db.delete_by_paths(paths)
    print(f"Deleted {deleted} of {len(paths)} entries.")


cmd_feeder = cyclopts.App(help="Feeder commands")
_ = cmd_feeder.command(cmd_feeder_create_importresource, name="create-importresource")
_ = cmd_feeder.command(cmd_feeder_register_importresources, name="register-importresources")
_ = cmd_feeder.command(cmd_feeder_db_status, name="db-status")
_ = cmd_feeder.command(cmd_feeder_db_delete, name="db-delete")

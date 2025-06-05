from pathlib import Path
import datetime
import cyclopts
from loguru import logger
from pydantic import BaseModel

from bfabric import Bfabric
from bfabric.entities import Storage, Application
from bfabric.utils.cli_integration import use_client
from bfabric_scripts.feeder.path_convention_compms import PathConventionCompMS, ParsedPath
from bfabric_scripts.feeder.file_attributes import FileAttributes


class ImportResourcePath(BaseModel):
    relative_path: Path
    application_name: str


def _create_importresources(storage_id: int, files: list[Path], client: Bfabric) -> None:
    storage = Storage.find(id=storage_id, client=client)
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
        importresource_id = result[0]["id"]
        importtresource_datetime = datetime.datetime.fromisoformat(result[0]["created"])
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
    return {app["name"]: id for id, app in result.items()}


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


cmd_feeder = cyclopts.App(help="Feeder commands")
cmd_feeder.command(cmd_feeder_create_importresource, name="create-importresource")

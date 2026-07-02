from __future__ import annotations

from typing import TYPE_CHECKING, Literal, assert_never

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from loguru import logger

from bfabric_app_runner.inputs.prepare.prepare_resolved_directory import prepare_resolved_directory
from bfabric_app_runner.inputs.prepare.prepare_resolved_file import prepare_resolved_file
from bfabric_app_runner.inputs.prepare.prepare_resolved_static_file import prepare_resolved_static_file
from bfabric_app_runner.inputs.resolve.resolved_inputs import (
    ResolvedInputs,
    ResolvedFile,
    ResolvedStaticFile,
    ResolvedDirectory,
)
from bfabric_app_runner.inputs.resolve.resolver import Resolver
from bfabric_app_runner.specs.inputs.file_spec import FileSourceHttp
from bfabric_app_runner.specs.inputs_spec import (
    InputsSpec,
)

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric.bfabric import Bfabric


def prepare_folder(
    inputs_yaml: Path,
    target_folder: Path | None,
    client: Bfabric,
    ssh_user: str | None,
    filter: str | None,
    action: Literal["prepare", "clean"] = "prepare",
) -> None:
    """Prepares the input files of a chunk folder according to the provided specs.

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be downloaded.
    :param client: Bfabric client to use for obtaining metadata about the input files.
    :param ssh_user: SSH user to use for downloading the input files, should it be different from the current user.
    :param filter: only this input file will be prepared.
    :param action: Action to perform.
    """
    # set defaults
    inputs_yaml = inputs_yaml.absolute()
    if target_folder is None:
        target_folder = inputs_yaml.parent

    # parse the specs
    inputs_spec = InputsSpec.read_yaml(inputs_yaml)

    # resolve the specs
    resolver = Resolver(client=client)
    input_files = resolver.resolve(specs=inputs_spec.inputs)

    # Note: In some cases, this will be very inefficient to do after resolving compared to doing it before, but in
    #       general not all filenames will be known upfront.
    if filter is not None:
        input_files = input_files.apply_filter(filter_files=[filter])
        if not input_files.files:
            raise ValueError(f"Filter {filter} did not match any input files")

    # prepare the folder
    if action == "prepare":
        # Only touch the client's auth (which may trigger an OAuth token fetch/refresh) when an HTTP input
        # actually needs a bearer token; otherwise SSH/local-only prepares stay independent of auth.
        bearer_token = _resolve_bearer_token(client) if _needs_bearer_token(input_files) else None
        _prepare_input_files(
            input_files=input_files, working_dir=target_folder, ssh_user=ssh_user, bearer_token=bearer_token
        )
    elif action == "clean":
        _clean_input_files(input_files=input_files, working_dir=target_folder)
    else:
        raise ValueError(f"Unknown action: {action}")


def _needs_bearer_token(input_files: ResolvedInputs) -> bool:
    """Whether any resolved input is an HTTP source that requires a bearer token."""
    return any(
        isinstance(f, ResolvedFile | ResolvedDirectory)
        and isinstance(f.source, FileSourceHttp)
        and f.source.http.require_auth
        for f in input_files.files
    )


def _resolve_bearer_token(client: Bfabric) -> str | None:
    """Returns the OAuth bearer token if the client is OAuth-backed, else ``None``.

    HTTP downloads only send a bearer token when it is a genuine OAuth JWT (``login == "__oauth__"``); a
    config-file client's 32-char web-service password must never be transmitted as a bearer token.
    """
    try:
        auth = client.auth
    except ValueError:
        return None
    if auth.login != OAUTH_LOGIN:
        return None
    return auth.password.get_secret_value()


def _prepare_input_files(
    input_files: ResolvedInputs, working_dir: Path, ssh_user: str | None, bearer_token: str | None
) -> None:
    """Prepares the input files in the working directory according to the provided specs."""
    for input_file in input_files.files:
        match input_file:
            case ResolvedFile():
                prepare_resolved_file(
                    file=input_file, working_dir=working_dir, ssh_user=ssh_user, bearer_token=bearer_token
                )
            case ResolvedStaticFile():
                prepare_resolved_static_file(file=input_file, working_dir=working_dir)
            case ResolvedDirectory():
                prepare_resolved_directory(
                    file=input_file, working_dir=working_dir, ssh_user=ssh_user, bearer_token=bearer_token
                )
            case _:
                assert_never(input_file)


def _clean_input_files(input_files: ResolvedInputs, working_dir: Path) -> None:
    """Removes the specified files from working_dir, if they exist."""
    for input_file in input_files.files:
        path = working_dir / input_file.filename
        if path.exists():
            path.unlink()
            logger.info(f"Removed {path}")

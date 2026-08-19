from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING, Literal, assert_never

from bfabric.transfer import ScopeError, check_download_scope, token_provider
from loguru import logger

from bfabric_app_runner.inputs.prepare.prepare_context import PrepareContext
from bfabric_app_runner.inputs.prepare.prepare_resolved_directory import (
    archive_cache_path,
    prepare_resolved_directory,
)
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
    from collections.abc import Callable
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
        provider = _resolve_token_provider(client) if _needs_bearer_token(input_files) else None
        context = PrepareContext(ssh_user=ssh_user, token_provider=provider)
        _prepare_input_files(input_files=input_files, working_dir=target_folder, context=context)
    elif action == "clean":
        _clean_input_files(input_files=input_files, working_dir=target_folder)
    else:
        raise ValueError(f"Unknown action: {action}")


def _needs_bearer_token(input_files: ResolvedInputs) -> bool:
    """Whether any resolved input is an HTTP source that requires the B-Fabric bearer token."""
    return any(
        isinstance(f, ResolvedFile) and isinstance(f.source, FileSourceHttp) and f.source.http.auth == "bfabric"
        for f in input_files.files
    )


def _resolve_token_provider(client: Bfabric) -> Callable[[], str] | None:
    """Returns a live OAuth bearer-token provider if the client is OAuth-backed, else ``None``.

    The provider reads the client's access token fresh on each call (see
    :func:`bfabric.transfer.token_provider`), so a long multi-file prepare survives a mid-batch OAuth
    token refresh. Returns ``None`` for classic login+password / no-auth clients, whose 32-char
    web-service password must never be transmitted as a bearer token.
    """
    provider = token_provider(client)
    if provider is None:
        return None
    # Warn (do not fail) if the OAuth token appears to lack the 'containers' scope needed to download
    # resources over HTTP: the server is authoritative on scope and may authorize via injected claims,
    # so a missing scope claim is a hint, not a hard failure. Let the download proceed; a genuine
    # authorization failure still surfaces as a decorated 401/403.
    try:
        check_download_scope(client)
    except ScopeError as scope_error:
        logger.warning(str(scope_error))
    return provider


def _prepare_input_files(input_files: ResolvedInputs, working_dir: Path, context: PrepareContext) -> None:
    """Prepares the input files in the working directory according to the provided specs."""
    for input_file in input_files.files:
        match input_file:
            case ResolvedFile():
                prepare_resolved_file(file=input_file, working_dir=working_dir, context=context)
            case ResolvedStaticFile():
                prepare_resolved_static_file(file=input_file, working_dir=working_dir)
            case ResolvedDirectory():
                prepare_resolved_directory(file=input_file, working_dir=working_dir, context=context)
            case _:
                assert_never(input_file)


def _clean_input_files(input_files: ResolvedInputs, working_dir: Path) -> None:
    """Removes the specified files from working_dir, if they exist."""
    for input_file in input_files.files:
        path = working_dir / input_file.filename
        if not _is_inside(path, working_dir):
            # A filename of "." resolves to working_dir itself, and one containing ".." can point
            # outside it; removing a directory input there would take the whole chunk folder (or a
            # sibling) with it.
            logger.warning(f"Refusing to remove {path}, which is not inside {working_dir}")
            continue
        _remove_input_path(path)
        if isinstance(input_file, ResolvedDirectory):
            # The cached archive sits beside the extracted directory and the next prepare would reuse
            # it, so leaving it behind would not be a clean.
            _remove_input_path(archive_cache_path(path))


def _is_inside(path: Path, working_dir: Path) -> bool:
    """Whether ``path`` is strictly inside ``working_dir``, collapsing ``.`` and ``..`` lexically.

    Lexically rather than via ``resolve()``, so a symlinked input (``link: true``, whose target lives
    outside the working directory) still counts as inside and gets cleaned.
    """
    normalized = os.path.normpath(path)
    base = os.path.normpath(working_dir)
    # normpath strips any trailing separator, so appending one makes this a true path-component prefix
    # check: "/work/sub" is inside "/work", "/workspace" is not.
    return normalized.startswith(f"{base}{os.sep}")


def _remove_input_path(path: Path) -> None:
    """Removes a file, symlink or directory tree, logging only what was actually there."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()
    else:
        return
    logger.info(f"Removed {path}")

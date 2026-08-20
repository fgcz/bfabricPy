from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from bfabric.entities import Order, Project, Workunit

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities import Resource

SENTINEL_ID = 0
"""Stands in for the resource and external-job ids the legacy wrapper creator used to register.

app-runner owns workunit and resource state itself, so no resource or external job is created here.
``0`` rather than ``null`` keeps a consumer that flattens the YAML into shell variables working
under ``set -u``.
"""

NO_LOG_URL = "/dev/null"
"""Log path written into the ``stdout``/``stderr`` sections; app-runner captures the real log itself."""


def build_legacy_wrapper_yaml(
    *,
    client: Bfabric,
    workunit_id: int,
    output_path: str,
    executable: str | None = None,
) -> dict[str, object]:
    """Builds the legacy wrapper-creator YAML for a workunit, writing nothing to B-Fabric.

    The result matches what ``bfabric.wrapper_creator.BfabricWrapperCreator`` produces, except where
    app-runner owns the output itself: ``application.output`` is whatever ``output_path`` says, every
    resource and external-job id is :data:`SENTINEL_ID`, and ``job_configuration.output`` describes a
    local file (``protocol: file``, empty ``ssh_args``) rather than the wrapper creator's scp
    destination. ``application.protocol`` stays ``scp``, since it describes the *inputs*.

    :param output_path: Where the app should deposit its output; ends up in ``application.output``.
    :param executable: ``job_configuration.executable``; ``None`` reads the application's own
        ``program``, which under app-runner points at the ``app.yml`` rather than the legacy app.
    """
    workunit = client.reader.read_id(Workunit, workunit_id)
    if workunit is None:
        raise ValueError(f"Workunit {workunit_id} does not exist")

    input_urls, input_references = _collect_inputs(workunit.input_resources.list)
    container = workunit.container
    order = container if isinstance(container, Order) else None
    project = container if isinstance(container, Project) else (order.project if order is not None else None)
    dataset = workunit.input_dataset

    return {
        "application": {
            "parameters": {key: value or "" for key, value in workunit.application_parameters.items()},
            "protocol": "scp",
            "input": input_urls,
            "output": [output_path],
        },
        "job_configuration": {
            "executable": executable if executable is not None else _application_program(workunit),
            "external_job_id": SENTINEL_ID,
            "fastasequence": _fasta_sequence(order),
            "input": input_references,
            "inputdataset": None if dataset is None else {"_id": dataset.id, "name": dataset["name"]},
            "order_id": order.id if order is not None else None,
            "project_id": project.id if project is not None else None,
            "output": {"protocol": "file", "resource_id": SENTINEL_ID, "ssh_args": ""},
            # Distinct dicts on purpose: yaml.safe_dump would emit an anchor/alias for a shared one.
            "stderr": _log_section(),
            "stdout": _log_section(),
            "workunit_createdby": workunit["createdby"],
            "workunit_id": workunit.id,
            "workunit_url": str(workunit.uri),
        },
    }


def _application_program(workunit: Workunit) -> str:
    """The application's own ``program``, used when the spec names no executable.

    An application with no executable at all already raises from ``HasOne``, which is not optional
    here; this only covers an executable that carries no ``program``, which would be a bare KeyError.
    """
    executable = workunit.application.executable
    if "program" not in executable.data_dict:
        raise ValueError(
            f"Executable {executable.id} of application {workunit.application.id} has no `program`, "
            f"so the spec must set `executable`"
        )
    return str(executable["program"])


def _collect_inputs(resources: list[Resource]) -> tuple[dict[str, list[str]], dict[str, list[dict[str, object]]]]:
    """Groups input resources by the name of the application that produced them.

    Returns the ``application.input`` (scp URLs) and ``job_configuration.input`` (id plus URI) views.
    """
    urls: dict[str, list[str]] = defaultdict(list)
    references: dict[str, list[dict[str, object]]] = defaultdict(list)
    for resource in resources:
        scp_prefix = resource.storage.scp_prefix
        if scp_prefix is None:
            # Interpolating None would yield a "bfabric@None/..." URL that only fails inside the app.
            raise ValueError(f"Storage {resource.storage.id} of input resource {resource.id} is not scp-accessible")
        application_name = str(resource.workunit.application["name"])
        urls[application_name].append(f"bfabric@{scp_prefix}{resource['relativepath']}")
        references[application_name].append({"resource_id": resource.id, "resource_url": str(resource.uri)})
    return dict(urls), dict(references)


def _fasta_sequence(order: Order | None) -> str:
    if order is None or "fastasequence" not in order.data_dict:
        return ""
    return "\n".join(part.strip() for part in str(order["fastasequence"]).split("\r"))


def _log_section() -> dict[str, object]:
    return {"protocol": "file", "resource_id": SENTINEL_ID, "url": NO_LOG_URL}

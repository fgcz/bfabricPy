from __future__ import annotations

from typing import TYPE_CHECKING, assert_never

from bfabric.entities import Order, Workunit
from loguru import logger

from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedStaticFile

if TYPE_CHECKING:
    from bfabric import Bfabric

    from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec


class ResolveBfabricOrderFastaSpecs:
    def __init__(self, client: Bfabric) -> None:
        self._client = client

    def __call__(self, specs: list[BfabricOrderFastaSpec]) -> list[ResolvedStaticFile]:
        """Convert order FASTA specifications to file specifications."""
        # Note: This approach is not efficient if there are multiple entries, but usually we only have one so it is
        #       not optimized yet.
        return [ResolvedStaticFile(content=self._get_order_fasta(spec=spec), filename=spec.filename) for spec in specs]

    def _get_order_fasta(self, spec: BfabricOrderFastaSpec) -> str:
        """Extract FASTA sequence from an order or workunit."""
        # find the order
        if spec.entity == "workunit":
            workunit = Workunit.find(id=spec.id, client=self._client)
            if not isinstance(workunit.container, Order):
                msg = f"Workunit {spec.id} is not associated with an order"
                if spec.required:
                    raise ValueError(msg)
                logger.warning(msg)
                return ""
            order = workunit.container
        elif spec.entity == "order":
            order = Order.find(id=spec.id, client=self._client)
            if order is None:
                msg = f"Order {spec.id} not found"
                if spec.required:
                    raise ValueError(msg)
                logger.warning(msg)
                return ""
        else:
            assert_never(spec.entity)

        # get the fasta sequence
        result = order.data_dict.get("fastasequence", "")
        if not isinstance(result, str):
            raise ValueError("fastasequence must be a string")
        return result

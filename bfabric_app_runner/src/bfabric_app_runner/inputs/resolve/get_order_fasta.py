from __future__ import annotations

from typing import assert_never, TYPE_CHECKING

from loguru import logger

from bfabric.entities import Workunit, Order

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec


def get_order_fasta(spec: BfabricOrderFastaSpec, client: Bfabric) -> str:
    """Extract FASTA sequence from an order or workunit."""
    if spec.entity == "workunit":
        workunit = Workunit.find(id=spec.id, client=client)
        if not isinstance(workunit.container, Order):
            msg = f"Workunit {spec.id} is not associated with an order"
            if spec.required:
                raise ValueError(msg)
            logger.warning(msg)
            return ""
        order = workunit.container
    elif spec.entity == "order":
        order = Order.find(id=spec.id, client=client)
    else:
        assert_never(spec.entity)

    return order.data_dict.get("fastasequence", "")

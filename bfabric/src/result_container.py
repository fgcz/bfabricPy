from enum import Enum

from bfabric.src.suds_format import suds_asdict_recursive


class BfabricResultType(Enum):
    LISTDICT = 1
    LISTSUDS = 2
    LISTZEEP = 3


class ResultContainer:
    def __init__(self, results: list, resultType: BFABRIC_RESULT_TYPE):
        self.results = results
        self.resultType = resultType

    def to_dict(self):
        match self.resultType:
            case BFABRIC_RESULT_TYPE.LISTDICT:
                return self.results
            case BFABRIC_RESULT_TYPE.LISTSUDS:
                return [suds_asdict_recursive(v) for v in self.results]
            case BFABRIC_RESULT_TYPE.LISTZEEP:
                return self.results   # TODO: Implement me
            case _:
                raise ValueError("Unexpected results type", self.resultType)
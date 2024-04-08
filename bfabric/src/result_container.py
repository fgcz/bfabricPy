
from enum import Enum

class BFABRIC_RESULT_TYPE(Enum):
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
                return self.results   # TODO: Implement me
            case BFABRIC_RESULT_TYPE.LISTZEEP:
                return self.results   # TODO: Implement me
            case _:
                raise ValueError("Unexpected results type", self.resultType)
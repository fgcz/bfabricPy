from __future__ import annotations

import re
from typing import Any

from loguru import logger
from zeep.helpers import serialize_object

from bfabric.engine.response_format_suds import suds_asdict_recursive
from bfabric.errors import BfabricRequestError
from bfabric.results.result_container import ResultContainer


class ResponseDelete(ResultContainer):
    """A response to a `delete` request.

    Any errors will be contained in errors, whereas the result will be a list of dictionaries with `id` of only the
    successfully deleted entities.
    """

    __msg_success_pattern = re.compile(r"\w+ (\d+) removed successfully\.")
    __report_key = "deletionreport"

    @classmethod
    def from_empty_request(cls) -> ResponseDelete:
        """Creates an empty `ResponseDelete`."""
        logger.warning("Attempted to delete an empty list, no request will be performed.")
        return cls(results=[], errors=[], total_pages_api=0)

    @classmethod
    def from_suds(cls, suds_response: Any, endpoint: str) -> ResponseDelete:
        """Creates a `ResponseDelete` from a SUDS response."""
        result_parsed = [suds_asdict_recursive(entry, convert_types=True) for entry in suds_response[endpoint]]
        results, errors = cls.__convert_parsed_response(result_parsed)
        return cls(results=results, errors=errors, total_pages_api=None)

    @classmethod
    def from_zeep(cls, zeep_response: Any, endpoint: str) -> ResponseDelete:
        """Creates a `ResponseDelete` from a ZEEP response."""
        result_parsed = [dict(serialize_object(result, target_cls=dict)) for result in zeep_response[endpoint]]
        results, errors = cls.__convert_parsed_response(result_parsed)
        return cls(results=results, errors=errors, total_pages_api=None)

    @classmethod
    def __convert_parsed_response(
        cls, result_parsed: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[BfabricRequestError]]:
        """Converts the response to a `delete` request."""
        results = []
        errors = []
        for result in result_parsed:
            if "errorreport" in result and result["errorreport"]:
                errors.append(BfabricRequestError(result["errorreport"]))
                continue
            report_msg = result[cls.__report_key]
            match_success = cls.__msg_success_pattern.match(report_msg)
            if match_success:
                results.append({"id": int(match_success.group(1)), cls.__report_key: report_msg})
            else:
                errors.append(BfabricRequestError(report_msg))
        return results, errors

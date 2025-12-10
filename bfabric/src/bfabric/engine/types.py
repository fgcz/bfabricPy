from __future__ import annotations

import datetime
from collections.abc import Mapping

# Request types (data sent TO the API)
ApiRequestScalarType = int | float | str | bool | datetime.datetime | None
ApiRequestDataType = ApiRequestScalarType | list["ApiRequestDataType"] | Mapping[str, "ApiRequestDataType"]
ApiRequestObjectType = Mapping[str, ApiRequestDataType]

# Response types (data received FROM the API)
ApiResponseScalarType = int | float | str | bool | None
ApiResponseDataType = ApiResponseScalarType | list["ApiResponseDataType"] | dict[str, "ApiResponseDataType"]
ApiResponseObjectType = dict[str, ApiResponseDataType]

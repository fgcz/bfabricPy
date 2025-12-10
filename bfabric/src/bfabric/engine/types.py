from __future__ import annotations

import datetime

# Request types (data sent TO the API)
ApiRequestScalarType = int | float | str | bool | datetime.datetime | None
ApiRequestDataType = ApiRequestScalarType | list["ApiRequestDataType"] | dict[str, "ApiRequestDataType"]
ApiRequestObjectType = dict[str, ApiRequestDataType]

# Response types (data received FROM the API)
ApiResponseScalarType = int | float | str | bool | None
ApiResponseDataType = ApiResponseScalarType | list["ApiResponseDataType"] | dict[str, "ApiResponseDataType"]
ApiResponseObjectType = dict[str, ApiResponseDataType]

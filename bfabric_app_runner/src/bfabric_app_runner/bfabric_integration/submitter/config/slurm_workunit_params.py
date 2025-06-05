from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, field_validator, Field, AliasChoices


class SlurmWorkunitSpecialStrings(Enum):
    default = "[default]"
    auto = "[auto]"

    @classmethod
    def parse(cls, string: str) -> SlurmWorkunitSpecialStrings | None:
        if string == cls.default.value:
            return cls.default
        elif string == cls.auto.value:
            return cls.auto
        else:
            return None


class SlurmWorkunitParams(BaseModel):
    partition: Annotated[
        SlurmWorkunitSpecialStrings | str, Field(validation_alias=AliasChoices("partition", "--partition"))
    ] = SlurmWorkunitSpecialStrings.default
    nodelist: Annotated[
        SlurmWorkunitSpecialStrings | str, Field(validation_alias=AliasChoices("nodelist", "--nodelist"))
    ] = SlurmWorkunitSpecialStrings.default
    mem: Annotated[SlurmWorkunitSpecialStrings | str, Field(validation_alias=AliasChoices("mem", "--mem"))] = (
        SlurmWorkunitSpecialStrings.default
    )
    time: Annotated[SlurmWorkunitSpecialStrings | str, Field(validation_alias=AliasChoices("time", "--time"))] = (
        SlurmWorkunitSpecialStrings.default
    )

    @classmethod
    def _parse_string(cls, value: str | SlurmWorkunitSpecialStrings) -> SlurmWorkunitSpecialStrings | str:
        if isinstance(value, SlurmWorkunitSpecialStrings):
            return value
        parsed = SlurmWorkunitSpecialStrings.parse(value)
        if parsed is not None:
            return parsed
        return value

    @field_validator("partition", "nodelist", "mem", "time", mode="before")
    def validate_special_string(cls, value: SlurmWorkunitSpecialStrings | str) -> SlurmWorkunitSpecialStrings | str:
        return cls._parse_string(value)

    def _get_field(self, field_name: str) -> str | None:
        """Returns the value to be used for the field, or None if the default should be used (when merging configs)."""
        value = getattr(self, field_name)
        if isinstance(value, str):
            return value
        if value == SlurmWorkunitSpecialStrings.default:
            return None
        else:
            raise NotImplementedError(f"Currently unsupported value for {field_name}: {value}")

    def as_dict(self) -> dict[str, str | None]:
        """Returns a dictionary with the values that should be passed to sbatch."""
        field_mapping = {
            "partition": "--partition",
            "nodelist": "--nodelist",
            "mem": "--mem",
            "time": "--time",
        }

        values = {}
        for field_name, flag in field_mapping.items():
            value = self._get_field(field_name)
            if value is not None:
                values[flag] = value

        return values

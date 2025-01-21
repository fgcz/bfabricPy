from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, field_validator


class SlurmSubmitterSpecialStrings(Enum):
    default = "[default]"
    auto = "[auto]"

    @classmethod
    def parse(cls, string: str) -> SlurmSubmitterSpecialStrings | None:
        if string == cls.default.value:
            return cls.default
        elif string == cls.auto.value:
            return cls.auto
        else:
            return None


class SlurmSubmitterWorkunitParams(BaseModel):
    # TODO maybe we could actually just make it so these names are already used as param
    #      (i.e. --partition, --nodeslist, --mem)
    #      especially as the memory could be confusing
    partition: SlurmSubmitterSpecialStrings | str = SlurmSubmitterSpecialStrings.default
    nodeslist: SlurmSubmitterSpecialStrings | str = SlurmSubmitterSpecialStrings.default
    memory: SlurmSubmitterSpecialStrings | str = SlurmSubmitterSpecialStrings.default

    @classmethod
    def _parse_string(cls, value: str | SlurmSubmitterSpecialStrings) -> SlurmSubmitterSpecialStrings | str:
        if isinstance(value, SlurmSubmitterSpecialStrings):
            return value
        parsed = SlurmSubmitterSpecialStrings.parse(value)
        if parsed is not None:
            return parsed
        return value

    @field_validator("partition", "nodeslist", "memory", mode="before")
    def validate_special_string(cls, value: SlurmSubmitterSpecialStrings | str) -> SlurmSubmitterSpecialStrings | str:
        return cls._parse_string(value)

    def _get_field(self, field_name: str) -> str | None:
        value = getattr(self, field_name)
        if isinstance(value, str):
            return value
        if value == SlurmSubmitterSpecialStrings.default:
            return None
        else:
            raise NotImplementedError(f"Currently unsupported value for {field_name}: {value}")

    def as_dict(self) -> dict[str, str | None]:
        values = {}

        partition = self._get_field("partition")
        if partition is not None:
            values["--partition"] = partition

        nodeslist = self._get_field("nodeslist")
        if nodeslist is not None:
            values["--nodeslist"] = nodeslist

        memory = self._get_field("memory")
        if memory is not None:
            values["--mem"] = memory

        return values

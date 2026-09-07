from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class StrictModel(BaseModel):
    """Request payload that rejects any field it does not declare."""

    model_config = ConfigDict(extra="forbid")


class PartialUpdate(StrictModel):
    """Patch payload that has to carry at least one field."""

    @model_validator(mode="after")
    def _require_a_field(self) -> PartialUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self

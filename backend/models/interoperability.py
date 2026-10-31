"""Schemas for the Interoperability Validation endpoint."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class UnitConversionReport(BaseModel):
    """Detailed record of a unit conversion performed during normalization."""

    model_config = ConfigDict(extra="forbid")

    field: str
    original_value: Any
    original_unit: str | None = None
    canonical_value: Any
    canonical_unit: str


class FieldMappingReport(BaseModel):
    """Detailed record of a field name alias mapping to its canonical name."""

    model_config = ConfigDict(extra="forbid")

    original_field: str
    canonical_field: str
    original_value: Any
    normalized_value: Any


class InteropIncompatibilityError(BaseModel):
    """Structured error detailing why a telemetry payload is incompatible."""

    model_config = ConfigDict(extra="forbid")

    error_type: str
    field: str | None = None
    message: str


class InteropValidationRequest(BaseModel):
    """Request payload for the interoperability validation endpoint."""

    model_config = ConfigDict(extra="forbid")

    domain: Literal["performance", "infrastructure", "connectivity", "diagnosis"]
    payload: dict[str, Any]
    schema_version: str | None = None


class InteropValidationResponse(BaseModel):
    """Response reporting schema compatibility, recognized aliases, conversions, and errors."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["compatible", "compatible_with_normalization", "incompatible"]
    schema_version: str
    domain: str
    recognized_aliases: list[str] = Field(default_factory=list)
    field_mappings: list[FieldMappingReport] = Field(default_factory=list)
    unit_conversions: list[UnitConversionReport] = Field(default_factory=list)
    missing_required_fields: list[str] = Field(default_factory=list)
    errors: list[InteropIncompatibilityError] = Field(default_factory=list)
    normalized_payload: dict[str, Any] | None = None

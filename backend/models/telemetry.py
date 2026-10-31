"""Validated performance telemetry accepted by the Performance Agent."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


from backend.services.interoperability import (
    normalize_sample_payload,
    validate_schema_version,
)


class TelemetrySample(BaseModel):
    """A measurement snapshot for one network device or interface."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1)
    interface_id: str | None = None
    observed_at: datetime | None = None
    latency_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    jitter_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    packet_loss_pct: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )
    throughput_mbps: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    link_utilization_pct: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )
    rssi_dbm: float | None = Field(
        default=None, le=0, ge=-120, allow_inf_nan=False
    )
    dns_lookup_time_ms: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: object) -> object:
        return normalize_sample_payload(data, "performance")

    @field_validator("device_id", "interface_id")
    @classmethod
    def strip_identifiers(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("identifier must not be empty")
        return value

    @model_validator(mode="after")
    def require_a_performance_measurement(self) -> "TelemetrySample":
        metric_fields = (
            "latency_ms",
            "jitter_ms",
            "packet_loss_pct",
            "throughput_mbps",
            "link_utilization_pct",
            "rssi_dbm",
            "dns_lookup_time_ms",
        )
        if all(getattr(self, field) is None for field in metric_fields):
            raise ValueError("at least one performance metric is required")
        return self


class TelemetryBatch(BaseModel):
    """Telemetry samples grouped into one diagnosis request."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    diagnosis_id: str = Field(min_length=1)
    samples: list[TelemetrySample] = Field(min_length=1)

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return validate_schema_version(value)

    @field_validator("diagnosis_id")
    @classmethod
    def strip_diagnosis_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("diagnosis_id must not be empty")
        return value

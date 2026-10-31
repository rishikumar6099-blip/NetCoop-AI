"""Validated infrastructure telemetry and configurable analysis thresholds."""

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


from backend.services.interoperability import (
    normalize_sample_payload,
    validate_schema_version,
)

DeviceStatus = Literal["online", "offline", "degraded"]
DhcpStatus = Literal["bound", "failed", "timeout", "renewing", "unknown"]
InteroperabilityStatus = Literal["compatible", "incompatible", "unknown"]


class InfrastructureTelemetrySample(BaseModel):
    """A device-level infrastructure health snapshot."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1)
    interface_id: str | None = None
    observed_at: datetime | None = None
    cpu_utilization_pct: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )
    memory_utilization_pct: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )
    interface_errors: int | None = Field(default=None, ge=0)
    egress_queue_drops: int | None = Field(default=None, ge=0)
    device_status: DeviceStatus | None = None
    dhcp_status: DhcpStatus | None = None
    link_flaps: int | None = Field(default=None, ge=0)
    interoperability_status: InteroperabilityStatus | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: object) -> object:
        return normalize_sample_payload(data, "infrastructure")

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
    def require_an_infrastructure_measurement(self) -> "InfrastructureTelemetrySample":
        fields = (
            "cpu_utilization_pct",
            "memory_utilization_pct",
            "interface_errors",
            "egress_queue_drops",
            "device_status",
            "dhcp_status",
            "link_flaps",
            "interoperability_status",
        )
        if all(getattr(self, field) is None for field in fields):
            raise ValueError("at least one infrastructure measurement is required")
        return self


class InfrastructureTelemetryBatch(BaseModel):
    """Device telemetry grouped into one diagnosis request."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    diagnosis_id: str = Field(min_length=1)
    samples: list[InfrastructureTelemetrySample] = Field(min_length=1)

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


class InfrastructureThresholds(BaseModel):
    """Configurable prototype thresholds; values are not universal SLAs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cpu_warning_pct: float = Field(default=80, ge=0, le=100)
    cpu_critical_pct: float = Field(default=95, ge=0, le=100)
    memory_warning_pct: float = Field(default=80, ge=0, le=100)
    memory_critical_pct: float = Field(default=95, ge=0, le=100)
    interface_errors_warning: int = Field(default=1, ge=0)
    interface_errors_critical: int = Field(default=10, ge=0)
    queue_drops_warning: int = Field(default=1, ge=0)
    queue_drops_critical: int = Field(default=10, ge=0)

    @model_validator(mode="after")
    def require_critical_above_warning(self) -> "InfrastructureThresholds":
        pairs = (
            (self.cpu_warning_pct, self.cpu_critical_pct, "CPU"),
            (self.memory_warning_pct, self.memory_critical_pct, "memory"),
            (
                self.interface_errors_warning,
                self.interface_errors_critical,
                "interface errors",
            ),
            (self.queue_drops_warning, self.queue_drops_critical, "queue drops"),
        )
        for warning, critical, name in pairs:
            if critical <= warning:
                raise ValueError(f"{name} critical threshold must exceed warning threshold")
        return self

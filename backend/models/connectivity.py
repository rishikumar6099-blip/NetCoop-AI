"""Validated topology and connectivity observations."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.services.interoperability import (
    normalize_connectivity_payload,
    normalize_device_payload,
    normalize_link_payload,
    validate_schema_version,
)

Reachability = Literal["reachable", "unreachable", "unknown"]
LinkStatus = Literal["up", "down", "unknown"]


def _clean_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("identifier must not be empty")
    return cleaned


class TopologyDevice(BaseModel):
    """A device observation and its explicitly supplied segment membership."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1)
    segment_id: str | None = None
    reachability: Reachability | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: object) -> object:
        return normalize_device_payload(data)

    @field_validator("device_id", "segment_id")
    @classmethod
    def clean_identifiers(cls, value: str | None) -> str | None:
        return _clean_identifier(value)


class TopologyLink(BaseModel):
    """A link reported by the supplied topology source."""

    model_config = ConfigDict(extra="forbid")

    link_id: str = Field(min_length=1)
    source_device_id: str = Field(min_length=1)
    target_device_id: str = Field(min_length=1)
    status: LinkStatus = "unknown"
    medium: Literal["ethernet", "wifi", "fiber", "unknown"] = "unknown"

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: object) -> object:
        return normalize_link_payload(data)

    @field_validator("link_id", "source_device_id", "target_device_id")
    @classmethod
    def clean_identifiers(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("identifier must not be empty")
        return cleaned


class ConnectivityTelemetry(BaseModel):
    """Topology and observations for one diagnosis request."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    diagnosis_id: str = Field(min_length=1)
    devices: list[TopologyDevice] = Field(default_factory=list)
    links: list[TopologyLink] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: object) -> object:
        return normalize_connectivity_payload(data)

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return validate_schema_version(value)

    @field_validator("diagnosis_id")
    @classmethod
    def clean_diagnosis_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("diagnosis_id must not be empty")
        return cleaned

    @model_validator(mode="after")
    def validate_topology_shape(self) -> "ConnectivityTelemetry":
        if not self.devices and not self.links:
            raise ValueError("at least one device or link observation is required")

        device_ids = [device.device_id for device in self.devices]
        link_ids = [link.link_id for link in self.links]
        if len(device_ids) != len(set(device_ids)):
            raise ValueError("device identifiers must be unique within a topology")
        if len(link_ids) != len(set(link_ids)):
            raise ValueError("link identifiers must be unique within a topology")
        return self

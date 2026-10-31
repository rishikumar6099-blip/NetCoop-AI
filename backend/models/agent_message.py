"""Structured findings returned by an analysis agent."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    value: float | str
    unit: str
    severity: Literal["info", "warning", "critical"]
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    device_id: str | None = None
    interface_id: str | None = None
    observed_at: datetime | None = None
    assessment: str
    evidence: list[str] = Field(default_factory=list)
    affected_device_ids: list[str] = Field(default_factory=list)
    affected_link_ids: list[str] = Field(default_factory=list)
    affected_segment_ids: list[str] = Field(default_factory=list)


from backend.services.interoperability import validate_schema_version


class AgentMessage(BaseModel):
    """Versioned, JSON-serializable result from one agent."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    diagnosis_id: str
    agent: str
    status: Literal["complete"] = "complete"
    summary: str
    samples_analyzed: int
    findings: list[AgentFinding]

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return validate_schema_version(value)

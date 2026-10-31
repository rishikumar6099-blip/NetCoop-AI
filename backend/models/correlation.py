"""Input and output schemas for fault correlation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.models.agent_message import AgentMessage


class CorrelationInput(BaseModel):
    """The three completed agent messages for one diagnosis."""

    model_config = ConfigDict(extra="forbid")

    performance: AgentMessage
    infrastructure: AgentMessage
    connectivity: AgentMessage
    telemetry_gaps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_agent_messages(self) -> "CorrelationInput":
        expected_agents = {
            "performance": "performance",
            "infrastructure": "infrastructure",
            "connectivity": "connectivity",
        }
        diagnosis_ids = set()
        for field, expected_agent in expected_agents.items():
            message = getattr(self, field)
            if message.agent != expected_agent:
                raise ValueError(
                    f"{field} message must have agent='{expected_agent}'"
                )
            diagnosis_ids.add(message.diagnosis_id)
        if len(diagnosis_ids) != 1:
            raise ValueError("all agent messages must share the same diagnosis_id")
        return self


class EvidenceReference(BaseModel):
    """Stable reference to a finding in one input AgentMessage."""

    model_config = ConfigDict(extra="forbid")

    agent: Literal["performance", "infrastructure", "connectivity"]
    finding_index: int = Field(ge=0)
    metric: str
    value: float | str
    severity: Literal["info", "warning", "critical"]
    assessment: str
    device_id: str | None = None
    interface_id: str | None = None
    observed_at: datetime | None = None
    affected_device_ids: list[str] = Field(default_factory=list)
    affected_link_ids: list[str] = Field(default_factory=list)
    affected_segment_ids: list[str] = Field(default_factory=list)


class RootCauseHypothesis(BaseModel):
    """A ranked cause candidate supported by source finding references."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    cause: str
    explanation: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceReference] = Field(min_length=2)
    affected_device_ids: list[str] = Field(default_factory=list)
    affected_link_ids: list[str] = Field(default_factory=list)
    affected_segment_ids: list[str] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class EvidenceConflict(BaseModel):
    """Two findings that report mutually inconsistent states."""

    model_config = ConfigDict(extra="forbid")

    description: str
    evidence: list[EvidenceReference] = Field(min_length=2)
    affected_device_ids: list[str] = Field(default_factory=list)


from backend.services.interoperability import validate_schema_version


class CorrelationResult(BaseModel):
    """Structured result from the Fault Correlation Agent."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    diagnosis_id: str
    agent: Literal["fault_correlation"] = "fault_correlation"
    status: Literal["complete", "no_fault_detected", "insufficient_evidence"]
    summary: str
    hypotheses: list[RootCauseHypothesis] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    insufficient_evidence: bool
    limitations: list[str] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return validate_schema_version(value)

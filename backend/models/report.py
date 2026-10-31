"""Structured diagnostic report produced from a correlation result."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models.correlation import (
    ConfidenceBreakdown,
    EvidenceConflict,
    EvidenceReference,
    RootCauseHypothesis,
)
from backend.services.interoperability import validate_schema_version


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: Literal["high", "medium", "low"]
    action: str
    related_cause: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)


class DiagnosticReport(BaseModel):
    """Final, JSON-serializable diagnosis report."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    diagnosis_id: str
    incident_status: Literal[
        "probable_cause", "no_fault_detected", "insufficient_evidence"
    ]
    probable_root_cause: str | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    confidence_category: Literal[
        "high", "moderate", "low", "insufficient", "not_applicable"
    ]
    confidence_breakdown: ConfidenceBreakdown | None = None
    affected_device_ids: list[str] = Field(default_factory=list)
    affected_link_ids: list[str] = Field(default_factory=list)
    affected_segment_ids: list[str] = Field(default_factory=list)
    supporting_evidence: list[EvidenceReference] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    alternative_hypotheses: list[RootCauseHypothesis] = Field(default_factory=list)
    recommended_actions: list[Recommendation] = Field(default_factory=list)
    evidence_sources: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return validate_schema_version(value)

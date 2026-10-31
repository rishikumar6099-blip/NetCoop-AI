"""Pydantic schemas for persistent diagnosis history and records."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from backend.models.correlation import ConfidenceBreakdown


class DiagnosisSummary(BaseModel):
    """Compact summary of a diagnosis for paginated history listings."""

    model_config = ConfigDict(extra="forbid")

    diagnosis_id: str
    created_at: str
    status: Literal["complete", "partial"]
    incident_status: str | None = None
    probable_root_cause: str | None = None
    confidence_score: float | None = None
    confidence_category: str | None = None
    affected_device_ids: list[str] = Field(default_factory=list)
    review_status: str = "unreviewed"


class DiagnosisHistoryResponse(BaseModel):
    """Paginated list of historical diagnoses."""

    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    items: list[DiagnosisSummary]


class FindingRecord(BaseModel):
    """Stored agent finding record."""

    model_config = ConfigDict(extra="forbid")

    id: int
    diagnosis_id: str
    agent: str
    finding_index: int
    metric: str
    value: str
    unit: str
    severity: str
    assessment: str
    device_id: str | None = None
    observed_at: str | None = None


class DiagnosisRecord(BaseModel):
    """Comprehensive diagnosis record containing all inputs, outputs, and findings."""

    model_config = ConfigDict(extra="forbid")

    diagnosis_id: str
    created_at: str
    status: Literal["complete", "partial"]
    incident_status: str | None = None
    probable_root_cause: str | None = None
    confidence_score: float | None = None
    confidence_category: str | None = None
    confidence_breakdown: ConfidenceBreakdown | None = None
    affected_device_ids: list[str] = Field(default_factory=list)
    affected_link_ids: list[str] = Field(default_factory=list)
    affected_segment_ids: list[str] = Field(default_factory=list)
    review_status: str = "unreviewed"
    request: dict[str, Any]
    response: dict[str, Any]
    agent_messages: dict[str, Any] = Field(default_factory=dict)
    findings: list[FindingRecord] = Field(default_factory=list)
    correlation_result: dict[str, Any] | None = None
    diagnostic_report: dict[str, Any] | None = None

"""Unified diagnosis request and orchestration response models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.models.agent_message import AgentMessage
from backend.models.connectivity import ConnectivityTelemetry
from backend.models.correlation import CorrelationResult
from backend.models.infrastructure import InfrastructureTelemetryBatch
from backend.models.report import DiagnosticReport
from backend.models.telemetry import TelemetryBatch


from backend.services.interoperability import validate_schema_version


class DiagnosisRequest(BaseModel):
    """Validated telemetry input for the complete multi-agent workflow."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    performance: TelemetryBatch
    infrastructure: InfrastructureTelemetryBatch
    connectivity: ConnectivityTelemetry

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return validate_schema_version(value)

    @model_validator(mode="after")
    def validate_shared_diagnosis_id(self) -> "DiagnosisRequest":
        diagnosis_ids = {
            self.performance.diagnosis_id,
            self.infrastructure.diagnosis_id,
            self.connectivity.diagnosis_id,
        }
        if len(diagnosis_ids) != 1:
            raise ValueError("all telemetry inputs must share the same diagnosis_id")
        return self

    @property
    def diagnosis_id(self) -> str:
        return self.performance.diagnosis_id


class AgentFailure(BaseModel):
    """Failure metadata; deliberately contains no fabricated agent findings."""

    model_config = ConfigDict(extra="forbid")

    stage: Literal[
        "performance",
        "infrastructure",
        "connectivity",
        "fault_correlation",
        "recommendation_reporting",
        "interoperability",
    ]
    error_type: str
    message: str


class DiagnosisResponse(BaseModel):
    """Workflow result, including completed stages when execution is partial."""

    model_config = ConfigDict(extra="forbid")

    diagnosis_id: str
    status: Literal["complete", "partial"]
    agent_messages: dict[str, AgentMessage] = Field(default_factory=dict)
    correlation_result: CorrelationResult | None = None
    diagnostic_report: DiagnosticReport | None = None
    failures: list[AgentFailure] = Field(default_factory=list)

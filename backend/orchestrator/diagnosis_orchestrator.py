"""Coordinates the five analysis agents into one diagnosis workflow."""

from typing import Any

from backend.agents.connectivity_agent import ConnectivityAnalysisAgent
from backend.agents.fault_correlation_agent import FaultCorrelationAgent
from backend.agents.infrastructure_agent import InfrastructureHealthAgent
from backend.agents.performance_agent import PerformanceAgent
from backend.agents.recommendation_reporting_agent import RecommendationReportingAgent
from pydantic import ValidationError

from backend.models.agent_message import AgentMessage
from backend.models.correlation import CorrelationResult
from backend.models.diagnosis import AgentFailure, DiagnosisRequest, DiagnosisResponse
from backend.models.report import DiagnosticReport
from backend.services.interoperability import InteroperabilityError


class MultiAgentOrchestrator:
    """Run each stage in order and preserve only validated agent outputs."""

    def __init__(
        self,
        *,
        performance_agent: Any | None = None,
        infrastructure_agent: Any | None = None,
        connectivity_agent: Any | None = None,
        fault_correlation_agent: Any | None = None,
        recommendation_reporting_agent: Any | None = None,
    ) -> None:
        self.performance_agent = (
            performance_agent if performance_agent is not None else PerformanceAgent()
        )
        self.infrastructure_agent = (
            infrastructure_agent
            if infrastructure_agent is not None
            else InfrastructureHealthAgent()
        )
        self.connectivity_agent = (
            connectivity_agent
            if connectivity_agent is not None
            else ConnectivityAnalysisAgent()
        )
        self.fault_correlation_agent = (
            fault_correlation_agent
            if fault_correlation_agent is not None
            else FaultCorrelationAgent()
        )
        self.recommendation_reporting_agent = (
            recommendation_reporting_agent
            if recommendation_reporting_agent is not None
            else RecommendationReportingAgent()
        )

    def run(self, request: DiagnosisRequest | dict[str, Any]) -> DiagnosisResponse:
        """Validate inputs, run agents, and return a complete or partial result."""
        diagnosis = (
            request
            if isinstance(request, DiagnosisRequest)
            else DiagnosisRequest.model_validate(request)
        )
        messages: dict[str, AgentMessage] = {}
        failures: list[AgentFailure] = []

        stages = (
            ("performance", self.performance_agent, diagnosis.performance),
            ("infrastructure", self.infrastructure_agent, diagnosis.infrastructure),
            ("connectivity", self.connectivity_agent, diagnosis.connectivity),
        )
        for stage, agent, telemetry in stages:
            try:
                output = agent.analyze(telemetry)
                message = AgentMessage.model_validate(output)
                if message.agent != stage or message.diagnosis_id != diagnosis.diagnosis_id:
                    raise ValueError("agent output identity does not match the request")
                messages[stage] = message
            except Exception as error:
                failures.append(self._failure(stage, error))

        if failures:
            return DiagnosisResponse(
                diagnosis_id=diagnosis.diagnosis_id,
                status="partial",
                agent_messages=messages,
                failures=failures,
            )

        try:
            correlation = self.fault_correlation_agent.analyze(
                {
                    "performance": messages["performance"],
                    "infrastructure": messages["infrastructure"],
                    "connectivity": messages["connectivity"],
                    "telemetry_gaps": self._telemetry_gaps(diagnosis),
                }
            )
            correlation = CorrelationResult.model_validate(correlation)
            if (
                correlation.agent != "fault_correlation"
                or correlation.diagnosis_id != diagnosis.diagnosis_id
            ):
                raise ValueError("correlation output identity does not match the request")
        except Exception as error:
            return DiagnosisResponse(
                diagnosis_id=diagnosis.diagnosis_id,
                status="partial",
                agent_messages=messages,
                failures=[self._failure("fault_correlation", error)],
            )

        try:
            report = self.recommendation_reporting_agent.analyze(correlation)
            report = DiagnosticReport.model_validate(report)
            if report.diagnosis_id != diagnosis.diagnosis_id:
                raise ValueError("report identity does not match the request")
        except Exception as error:
            return DiagnosisResponse(
                diagnosis_id=diagnosis.diagnosis_id,
                status="partial",
                agent_messages=messages,
                correlation_result=correlation,
                failures=[self._failure("recommendation_reporting", error)],
            )

        return DiagnosisResponse(
            diagnosis_id=diagnosis.diagnosis_id,
            status="complete",
            agent_messages=messages,
            correlation_result=correlation,
            diagnostic_report=report,
        )

    @staticmethod
    def _failure(stage: str, error: Exception) -> AgentFailure:
        error_type = type(error).__name__
        if isinstance(error, ValidationError):
            for err in error.errors():
                ctx_err = err.get("ctx", {}).get("error")
                if ctx_err and isinstance(ctx_err, InteroperabilityError):
                    error_type = type(ctx_err).__name__
                    break
        return AgentFailure(
            stage=stage,
            error_type=error_type,
            message="This stage failed; no findings were synthesized for it.",
        )

    @staticmethod
    def _telemetry_gaps(diagnosis: DiagnosisRequest) -> list[str]:
        """Describe absent required measurements without rejecting partial input."""
        gaps: list[str] = []
        performance_fields = (
            "latency_ms", "jitter_ms", "packet_loss_pct", "throughput_mbps",
            "link_utilization_pct",
        )
        infrastructure_fields = (
            "cpu_utilization_pct", "memory_utilization_pct", "interface_errors",
            "egress_queue_drops", "device_status",
        )
        for index, sample in enumerate(diagnosis.performance.samples):
            missing = [field for field in performance_fields if getattr(sample, field) is None]
            gaps.extend(f"performance.samples[{index}].{field} is missing" for field in missing)
        for index, sample in enumerate(diagnosis.infrastructure.samples):
            missing = [field for field in infrastructure_fields if getattr(sample, field) is None]
            gaps.extend(
                f"infrastructure.samples[{index}].{field} is missing"
                for field in missing
            )

        devices = {device.device_id: device for device in diagnosis.connectivity.devices}
        if not diagnosis.connectivity.links:
            gaps.append("connectivity.links is empty")
        for device in diagnosis.connectivity.devices:
            if device.reachability in (None, "unknown"):
                gaps.append(f"connectivity device {device.device_id} reachability is unknown")
        for link in diagnosis.connectivity.links:
            if link.status == "unknown":
                gaps.append(f"connectivity link {link.link_id} status is unknown")
            if (
                link.source_device_id not in devices
                or link.target_device_id not in devices
                or link.source_device_id == link.target_device_id
            ):
                gaps.append(f"connectivity link {link.link_id} has inconsistent endpoints")

        device_ids_by_section = {
            "performance": {sample.device_id for sample in diagnosis.performance.samples},
            "infrastructure": {
                sample.device_id for sample in diagnosis.infrastructure.samples
            },
            "connectivity": set(devices)
            | {
                endpoint
                for link in diagnosis.connectivity.links
                for endpoint in (link.source_device_id, link.target_device_id)
            },
        }
        for device_id in sorted(
            device_ids_by_section["performance"]
            | device_ids_by_section["infrastructure"]
        ):
            present_in = [
                section
                for section in ("performance", "infrastructure", "connectivity")
                if device_id in device_ids_by_section[section]
            ]
            missing_from = [
                section
                for section in ("performance", "infrastructure", "connectivity")
                if device_id not in device_ids_by_section[section]
            ]
            if missing_from:
                gaps.append(
                    f"Device ID mismatch: {device_id} is observed in "
                    f"{', '.join(present_in)} but absent from "
                    f"{', '.join(missing_from)}. Exact identifiers are used; "
                    "no device identity is inferred."
                )
        return gaps

"""Rule-based analysis of device and interface infrastructure health."""

from typing import Any

from backend.models.agent_message import AgentFinding, AgentMessage
from backend.models.infrastructure import (
    InfrastructureTelemetryBatch,
    InfrastructureTelemetrySample,
    InfrastructureThresholds,
)


_NUMERIC_METRICS = (
    (
        "cpu_utilization_pct",
        "CPU utilization",
        "%",
        "cpu_warning_pct",
        "cpu_critical_pct",
    ),
    (
        "memory_utilization_pct",
        "Memory utilization",
        "%",
        "memory_warning_pct",
        "memory_critical_pct",
    ),
    (
        "interface_errors",
        "Interface errors",
        "count",
        "interface_errors_warning",
        "interface_errors_critical",
    ),
    (
        "egress_queue_drops",
        "Egress queue drops",
        "count",
        "queue_drops_warning",
        "queue_drops_critical",
    ),
)


class InfrastructureHealthAgent:
    """Assess infrastructure metrics and return Agent 1-compatible JSON."""

    agent_name = "infrastructure"

    def __init__(self, thresholds: InfrastructureThresholds | None = None) -> None:
        self.thresholds = thresholds or InfrastructureThresholds()

    def analyze(
        self, telemetry: InfrastructureTelemetryBatch | dict[str, Any]
    ) -> AgentMessage:
        """Validate a JSON-compatible batch and assess supplied measurements."""
        batch = (
            telemetry
            if isinstance(telemetry, InfrastructureTelemetryBatch)
            else InfrastructureTelemetryBatch.model_validate(telemetry)
        )
        findings = [
            finding
            for sample in batch.samples
            for finding in self._analyze_sample(sample)
        ]
        critical_count = sum(finding.severity == "critical" for finding in findings)
        warning_count = sum(finding.severity == "warning" for finding in findings)
        return AgentMessage(
            diagnosis_id=batch.diagnosis_id,
            agent=self.agent_name,
            summary=(
                f"Analyzed {len(batch.samples)} infrastructure sample(s); "
                f"{critical_count} critical and {warning_count} warning finding(s)."
            ),
            samples_analyzed=len(batch.samples),
            findings=findings,
        )

    def _analyze_sample(
        self, sample: InfrastructureTelemetrySample
    ) -> list[AgentFinding]:
        findings = [
            self._numeric_finding(sample, metric, label, unit, warning_key, critical_key)
            for metric, label, unit, warning_key, critical_key in _NUMERIC_METRICS
            if getattr(sample, metric) is not None
        ]
        if sample.device_status is not None:
            status_severity = {
                "online": "info",
                "degraded": "warning",
                "offline": "critical",
            }[sample.device_status]
            findings.append(
                AgentFinding(
                    metric="Device status",
                    value=sample.device_status,
                    unit="status",
                    severity=status_severity,
                    device_id=sample.device_id,
                    interface_id=sample.interface_id,
                    observed_at=sample.observed_at,
                    assessment=f"Device reports {sample.device_status} status.",
                )
            )
        if getattr(sample, "dhcp_status", None) is not None:
            dhcp_severity = {
                "bound": "info",
                "renewing": "info",
                "unknown": "warning",
                "timeout": "critical",
                "failed": "critical",
            }.get(sample.dhcp_status, "warning")
            findings.append(
                AgentFinding(
                    metric="DHCP status",
                    value=sample.dhcp_status,
                    unit="status",
                    severity=dhcp_severity,
                    device_id=sample.device_id,
                    interface_id=sample.interface_id,
                    observed_at=sample.observed_at,
                    assessment=f"DHCP client reports {sample.dhcp_status} status.",
                )
            )
        if getattr(sample, "link_flaps", None) is not None:
            flaps = sample.link_flaps
            flap_severity = "critical" if flaps >= 5 else ("warning" if flaps >= 1 else "info")
            findings.append(
                AgentFinding(
                    metric="Link flaps",
                    value=flaps,
                    unit="count",
                    severity=flap_severity,
                    warning_threshold=1.0,
                    critical_threshold=5.0,
                    device_id=sample.device_id,
                    interface_id=sample.interface_id,
                    observed_at=sample.observed_at,
                    assessment=f"Interface reports {flaps} link flap event(s).",
                )
            )
        if getattr(sample, "interoperability_status", None) is not None:
            interop_severity = "critical" if sample.interoperability_status == "incompatible" else "info"
            findings.append(
                AgentFinding(
                    metric="Interoperability compatibility",
                    value=sample.interoperability_status,
                    unit="status",
                    severity=interop_severity,
                    device_id=sample.device_id,
                    interface_id=sample.interface_id,
                    observed_at=sample.observed_at,
                    assessment=f"Telemetry reports {sample.interoperability_status} interoperability state.",
                )
            )
        return findings

    def _numeric_finding(
        self,
        sample: InfrastructureTelemetrySample,
        metric: str,
        label: str,
        unit: str,
        warning_key: str,
        critical_key: str,
    ) -> AgentFinding:
        value = getattr(sample, metric)
        warning_threshold = getattr(self.thresholds, warning_key)
        critical_threshold = getattr(self.thresholds, critical_key)
        if value >= critical_threshold:
            severity = "critical"
            level = "critical"
            threshold = critical_threshold
        elif value >= warning_threshold:
            severity = "warning"
            level = "warning"
            threshold = warning_threshold
        else:
            severity = "info"
            level = "normal"
            threshold = warning_threshold

        return AgentFinding(
            metric=label,
            value=value,
            unit=unit,
            severity=severity,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            device_id=sample.device_id,
            interface_id=sample.interface_id,
            observed_at=sample.observed_at,
            assessment=(
                f"{label} is {level} at {value:g} {unit}; "
                f"prototype thresholds are {warning_threshold:g} {unit} warning "
                f"and {critical_threshold:g} {unit} critical "
                f"(current comparison threshold: {threshold:g} {unit})."
            ),
        )

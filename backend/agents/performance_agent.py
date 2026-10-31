"""Rule-based analysis of network performance telemetry."""

from typing import Any

from backend.models.agent_message import AgentFinding, AgentMessage
from backend.models.telemetry import TelemetryBatch, TelemetrySample


# Initial prototype thresholds. These are defaults, not universal SLAs.
_THRESHOLDS: dict[str, tuple[float, float, str]] = {
    "latency_ms": (100.0, 250.0, "ms"),
    "jitter_ms": (30.0, 50.0, "ms"),
    "packet_loss_pct": (1.0, 3.0, "%"),
    "link_utilization_pct": (80.0, 95.0, "%"),
    "dns_lookup_time_ms": (150.0, 1000.0, "ms"),
    "rssi_dbm": (-75.0, -82.0, "dBm"),
}

_METRIC_LABELS = {
    "latency_ms": "latency",
    "jitter_ms": "jitter",
    "packet_loss_pct": "packet loss",
    "throughput_mbps": "throughput",
    "link_utilization_pct": "link utilization",
    "rssi_dbm": "wifi signal strength",
    "dns_lookup_time_ms": "dns lookup time",
}


class PerformanceAgent:
    """Assess available performance metrics and return structured findings."""

    agent_name = "performance"

    def analyze(
        self, telemetry: TelemetryBatch | dict[str, Any]
    ) -> AgentMessage:
        """Validate a JSON-compatible batch and analyze each supplied metric."""
        batch = (
            telemetry
            if isinstance(telemetry, TelemetryBatch)
            else TelemetryBatch.model_validate(telemetry)
        )
        findings = [
            self._analyze_metric(sample, metric)
            for sample in batch.samples
            for metric in _METRIC_LABELS
            if getattr(sample, metric, None) is not None
        ]

        critical_count = sum(f.severity == "critical" for f in findings)
        warning_count = sum(f.severity == "warning" for f in findings)
        summary = (
            f"Analyzed {len(batch.samples)} telemetry sample(s); "
            f"{critical_count} critical and {warning_count} warning finding(s)."
        )
        return AgentMessage(
            diagnosis_id=batch.diagnosis_id,
            agent=self.agent_name,
            summary=summary,
            samples_analyzed=len(batch.samples),
            findings=findings,
        )

    @staticmethod
    def _analyze_metric(sample: TelemetrySample, metric: str) -> AgentFinding:
        value = getattr(sample, metric)
        label = _METRIC_LABELS[metric]
        configured = _THRESHOLDS.get(metric)

        if configured is None:
            severity = "info"
            warning_threshold = None
            critical_threshold = None
            assessment = (
                "Throughput recorded; a link capacity or expected-throughput "
                "baseline is needed to classify it."
            )
        elif metric == "rssi_dbm":
            warning_threshold, critical_threshold, unit = configured
            if value <= critical_threshold:
                severity = "critical"
                assessment = (
                    f"Wi-Fi signal strength is at or below the prototype critical "
                    f"threshold of {critical_threshold:g} {unit}."
                )
            elif value <= warning_threshold:
                severity = "warning"
                assessment = (
                    f"Wi-Fi signal strength is at or below the prototype warning "
                    f"threshold of {warning_threshold:g} {unit}."
                )
            else:
                severity = "info"
                assessment = (
                    f"Wi-Fi signal strength is above the prototype warning "
                    f"threshold of {warning_threshold:g} {unit}."
                )
        else:
            warning_threshold, critical_threshold, unit = configured
            if value >= critical_threshold:
                severity = "critical"
                assessment = (
                    f"{label.capitalize()} is at or above the prototype critical "
                    f"threshold of {critical_threshold:g} {unit}."
                )
            elif value >= warning_threshold:
                severity = "warning"
                assessment = (
                    f"{label.capitalize()} is at or above the prototype warning "
                    f"threshold of {warning_threshold:g} {unit}."
                )
            else:
                severity = "info"
                assessment = (
                    f"{label.capitalize()} is below the prototype warning "
                    f"threshold of {warning_threshold:g} {unit}."
                )

        unit = configured[2] if configured is not None else "Mbps"
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
            assessment=assessment,
        )

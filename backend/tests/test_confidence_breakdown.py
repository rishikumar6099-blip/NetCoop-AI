"""Unit tests for the Explainable Confidence Engine and ConfidenceBreakdown."""

from datetime import datetime, timedelta, timezone
import unittest

from pydantic import ValidationError

from backend.agents.fault_correlation_agent import FaultCorrelationAgent
from backend.agents.recommendation_reporting_agent import RecommendationReportingAgent
from backend.models.agent_message import AgentFinding, AgentMessage
from backend.models.correlation import (
    ConfidenceBreakdown,
    CorrelationInput,
    CorrelationResult,
    EvidenceConflict,
    EvidenceReference,
    RootCauseHypothesis,
)


def make_finding(
    metric: str,
    value: float | str,
    severity: str,
    *,
    device_id: str | None = None,
    observed_at: datetime | None = None,
    affected_device_ids: list[str] | None = None,
) -> AgentFinding:
    return AgentFinding(
        metric=metric,
        value=value,
        unit="count" if isinstance(value, int) else ("%" if isinstance(value, float) else "state"),
        severity=severity,
        assessment=f"{metric} reported {value}.",
        device_id=device_id,
        observed_at=observed_at,
        affected_device_ids=affected_device_ids or ([device_id] if device_id else []),
    )


def make_message(agent: str, findings: list[AgentFinding]) -> AgentMessage:
    return AgentMessage(
        schema_version="1.0",
        diagnosis_id="diag-conf-test",
        agent=agent,
        status="complete",
        summary=f"{agent} test message.",
        samples_analyzed=1,
        findings=findings,
    )


def make_input(
    perf: AgentMessage,
    infra: AgentMessage,
    conn: AgentMessage,
    telemetry_gaps: list[str] | None = None,
) -> CorrelationInput:
    return CorrelationInput(
        performance=perf,
        infrastructure=infra,
        connectivity=conn,
        telemetry_gaps=telemetry_gaps or [],
    )


class ConfidenceEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.correlation_agent = FaultCorrelationAgent()
        self.reporting_agent = RecommendationReportingAgent()

    def test_confidence_breakdown_model_validation(self) -> None:
        breakdown = ConfidenceBreakdown(
            base_score=0.20,
            domain_corroboration=0.24,
            device_specificity=0.06,
            severity_factor=0.12,
            semantic_match=0.08,
            telemetry_gap_penalty=0.05,
            temporal_skew_penalty=0.00,
            conflict_penalty=0.00,
            raw_score=0.65,
            final_score=0.65,
            rationale=["Base score: +0.20."],
        )
        self.assertEqual(breakdown.final_score, 0.65)
        self.assertEqual(breakdown.base_score, 0.20)
        self.assertEqual(breakdown.telemetry_gap_penalty, 0.05)

        with self.assertRaises(ValidationError):
            # Extra fields are forbidden
            ConfidenceBreakdown(
                base_score=0.20,
                domain_corroboration=0.24,
                device_specificity=0.06,
                severity_factor=0.12,
                semantic_match=0.08,
                telemetry_gap_penalty=0.00,
                temporal_skew_penalty=0.00,
                conflict_penalty=0.00,
                raw_score=0.70,
                final_score=0.70,
                unknown_field=123,
            )

    def test_corroboration_avoids_intra_agent_double_counting(self) -> None:
        # Performance reports 2 critical findings on R1; Infrastructure reports 1 critical finding on R1
        payload = make_input(
            make_message(
                "performance",
                [
                    make_finding("latency", 280, "critical", device_id="R1"),
                    make_finding("packet loss", 5.0, "critical", device_id="R1"),
                ],
            ),
            make_message(
                "infrastructure",
                [make_finding("CPU utilization", 97, "critical", device_id="R1")],
            ),
            make_message("connectivity", []),
        )
        result = self.correlation_agent.analyze(payload)
        top = result.hypotheses[0]
        breakdown = top.confidence_breakdown

        self.assertIsNotNone(breakdown)
        # Corroboration must count distinct domains (2: performance, infrastructure), NOT findings (3)
        self.assertEqual(breakdown.domain_corroboration, 0.24)
        self.assertIn("2 distinct agent domain(s)", "".join(breakdown.rationale))

    def test_severity_factor_requires_cross_domain_criticality(self) -> None:
        # Case A: Two critical findings from same agent (performance) + one warning from infrastructure
        payload_same_agent_critical = make_input(
            make_message(
                "performance",
                [
                    make_finding("latency", 280, "critical", device_id="R1"),
                    make_finding("packet loss", 5.0, "critical", device_id="R1"),
                ],
            ),
            make_message(
                "infrastructure",
                [make_finding("CPU utilization", 82, "warning", device_id="R1")],
            ),
            make_message("connectivity", []),
        )
        result_a = self.correlation_agent.analyze(payload_same_agent_critical)
        top_a = result_a.hypotheses[0]
        # Only 1 domain has critical severity -> severity factor is 0.06, NOT 0.12
        self.assertEqual(top_a.confidence_breakdown.severity_factor, 0.06)

        # Case B: Critical severity reported across 2 distinct domains
        payload_cross_domain_critical = make_input(
            make_message(
                "performance",
                [make_finding("latency", 280, "critical", device_id="R1")],
            ),
            make_message(
                "infrastructure",
                [make_finding("CPU utilization", 97, "critical", device_id="R1")],
            ),
            make_message("connectivity", []),
        )
        result_b = self.correlation_agent.analyze(payload_cross_domain_critical)
        top_b = result_b.hypotheses[0]
        # 2 domains report critical -> severity factor is 0.12
        self.assertEqual(top_b.confidence_breakdown.severity_factor, 0.12)

    def test_telemetry_gap_penalty_applied_and_itemized(self) -> None:
        payload_with_gaps = make_input(
            make_message(
                "performance",
                [make_finding("latency", 280, "critical", device_id="R1")],
            ),
            make_message(
                "infrastructure",
                [make_finding("CPU utilization", 97, "critical", device_id="R1")],
            ),
            make_message("connectivity", []),
            telemetry_gaps=[
                "Device ID mismatch: R1 is observed in performance but absent from connectivity.",
                "connectivity device R1 reachability is unknown",
                "connectivity link L1 to R2 status is unknown",  # Unrelated device
            ],
        )
        result = self.correlation_agent.analyze(payload_with_gaps)
        top = result.hypotheses[0]
        breakdown = top.confidence_breakdown

        self.assertIsNotNone(breakdown)
        # 2 relevant gaps targeting R1 -> penalty = 0.10
        self.assertEqual(breakdown.telemetry_gap_penalty, 0.10)
        self.assertIn("Missing telemetry penalty", "".join(breakdown.rationale))
        # Expected score: 0.20 (base) + 0.24 (domains) + 0.06 (dev) + 0.12 (sev) + 0.08 (semantic) - 0.10 (gap) = 0.60
        self.assertEqual(top.confidence, 0.60)
        self.assertEqual(breakdown.final_score, 0.60)

    def test_temporal_skew_penalty_and_uncertainty(self) -> None:
        t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        payload = make_input(
            make_message(
                "performance",
                [make_finding("latency", 280, "critical", device_id="R1", observed_at=t0)],
            ),
            make_message(
                "infrastructure",
                [make_finding("CPU utilization", 97, "critical", device_id="R1", observed_at=t0 + timedelta(minutes=10))],
            ),
            make_message("connectivity", []),
        )
        result = self.correlation_agent.analyze(payload)
        top = result.hypotheses[0]
        breakdown = top.confidence_breakdown

        self.assertIsNotNone(breakdown)
        self.assertEqual(breakdown.temporal_skew_penalty, 0.20)
        self.assertIn("temporal skew exceeds 300s window", "".join(breakdown.rationale))
        self.assertTrue(any("temporal alignment is weak" in u for u in top.uncertainties))

    def test_conflict_penalty_and_uncertainty(self) -> None:
        payload = make_input(
            make_message(
                "performance",
                [make_finding("latency", 280, "critical", device_id="R1")],
            ),
            make_message(
                "infrastructure",
                [
                    make_finding("CPU utilization", 97, "critical", device_id="R1"),
                    make_finding("Device status", "online", "info", device_id="R1"),
                ],
            ),
            make_message(
                "connectivity",
                [make_finding("Device reachability", "unreachable", "critical", device_id="R1", affected_device_ids=["R1"])],
            ),
        )
        result = self.correlation_agent.analyze(payload)
        top = result.hypotheses[0]
        breakdown = top.confidence_breakdown

        self.assertIsNotNone(breakdown)
        self.assertEqual(breakdown.conflict_penalty, 0.25)
        self.assertIn("Contradictory evidence penalty", "".join(breakdown.rationale))

    def test_report_propagates_confidence_breakdown(self) -> None:
        payload = make_input(
            make_message(
                "performance",
                [make_finding("packet loss", 4.0, "critical", device_id="SW1")],
            ),
            make_message(
                "infrastructure",
                [make_finding("Interface errors", 50, "critical", device_id="SW1")],
            ),
            make_message("connectivity", []),
        )
        corr_result = self.correlation_agent.analyze(payload)
        report = self.reporting_agent.analyze(corr_result)

        self.assertEqual(report.incident_status, "probable_cause")
        self.assertEqual(report.confidence_score, 0.70)
        self.assertIsNotNone(report.confidence_breakdown)
        self.assertEqual(report.confidence_breakdown.final_score, 0.70)
        self.assertEqual(report.confidence_breakdown.base_score, 0.20)
        self.assertEqual(report.confidence_breakdown.domain_corroboration, 0.24)
        self.assertEqual(report.confidence_breakdown.device_specificity, 0.06)
        self.assertEqual(report.confidence_breakdown.severity_factor, 0.12)
        self.assertEqual(report.confidence_breakdown.semantic_match, 0.08)

    def test_insufficient_evidence_and_healthy_telemetry_breakdown_behavior(self) -> None:
        # Weak findings only (< 0.60 confidence)
        payload = make_input(
            make_message(
                "performance",
                [make_finding("latency", 120, "warning", device_id="R1")],
            ),
            make_message(
                "infrastructure",
                [make_finding("CPU utilization", 82, "warning", device_id="R1")],
            ),
            make_message("connectivity", []),
        )
        corr_result = self.correlation_agent.analyze(payload)
        self.assertEqual(corr_result.status, "insufficient_evidence")
        # Hypothesis retains breakdown for post-mortem analysis
        self.assertIsNotNone(corr_result.hypotheses[0].confidence_breakdown)
        self.assertEqual(corr_result.hypotheses[0].confidence, 0.58)

        report = self.reporting_agent.analyze(corr_result)
        self.assertEqual(report.incident_status, "insufficient_evidence")
        self.assertIsNone(report.probable_root_cause)
        self.assertEqual(report.confidence_score, 0.58)
        self.assertEqual(report.confidence_category, "insufficient")
        self.assertIsNotNone(report.confidence_breakdown)
        self.assertEqual(report.confidence_breakdown.final_score, 0.58)

        # Healthy telemetry (no fault detected)
        healthy_payload = make_input(
            make_message(
                "performance",
                [
                    make_finding(metric, 1, "info", device_id="R1")
                    for metric in (
                        "latency", "jitter", "packet loss", "throughput",
                        "link utilization",
                    )
                ],
            ),
            make_message(
                "infrastructure",
                [
                    make_finding(metric, value, "info", device_id="R1")
                    for metric, value in (
                        ("CPU utilization", 20), ("Memory utilization", 40),
                        ("Interface errors", 0), ("Egress queue drops", 0),
                        ("Device status", "online"),
                    )
                ],
            ),
            make_message(
                "connectivity",
                [make_finding("Incident scope", "no confirmed impact", "info")],
            ),
        )
        healthy_corr = self.correlation_agent.analyze(healthy_payload)
        self.assertEqual(healthy_corr.status, "no_fault_detected")
        healthy_rep = self.reporting_agent.analyze(healthy_corr)
        self.assertEqual(healthy_rep.incident_status, "no_fault_detected")
        self.assertIsNone(healthy_rep.probable_root_cause)
        self.assertIsNone(healthy_rep.confidence_score)
        self.assertEqual(healthy_rep.confidence_category, "not_applicable")
        self.assertIsNone(healthy_rep.confidence_breakdown)


if __name__ == "__main__":
    unittest.main()

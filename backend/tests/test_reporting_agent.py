"""Unit tests for diagnostic reporting and recommendations."""

import unittest

from pydantic import ValidationError

from backend.agents.recommendation_reporting_agent import RecommendationReportingAgent
from backend.models.correlation import (
    CorrelationResult,
    EvidenceConflict,
    EvidenceReference,
    RootCauseHypothesis,
)


def reference(
    agent: str,
    finding_index: int,
    metric: str,
    value: float | str,
    *,
    device_id: str | None = None,
    affected_device_ids: list[str] | None = None,
    affected_link_ids: list[str] | None = None,
    affected_segment_ids: list[str] | None = None,
) -> EvidenceReference:
    return EvidenceReference(
        agent=agent,
        finding_index=finding_index,
        metric=metric,
        value=value,
        severity="critical",
        assessment=f"Observed {metric}: {value}.",
        device_id=device_id,
        affected_device_ids=affected_device_ids or [],
        affected_link_ids=affected_link_ids or [],
        affected_segment_ids=affected_segment_ids or [],
    )


def hypothesis(
    rank: int,
    cause: str,
    confidence: float,
    evidence: list[EvidenceReference],
) -> RootCauseHypothesis:
    return RootCauseHypothesis(
        rank=rank,
        cause=cause,
        explanation=f"{cause} may explain the observed network symptoms.",
        confidence=confidence,
        evidence=evidence,
        affected_device_ids=["R1"],
        uncertainties=["Correlation does not prove causation."],
    )


def correlation_result(
    hypotheses: list[RootCauseHypothesis],
    *,
    insufficient: bool = False,
    status: str | None = None,
    conflicts: list[EvidenceConflict] | None = None,
) -> CorrelationResult:
    return CorrelationResult(
        diagnosis_id="report-case-1",
        status=status or ("insufficient_evidence" if insufficient else "complete"),
        summary="Correlation completed.",
        hypotheses=hypotheses,
        alternative_explanations=[
            f"Rank {item.rank}: {item.explanation}" for item in hypotheses[1:]
        ],
        insufficient_evidence=insufficient,
        conflicts=conflicts or [],
        limitations=["Agent evidence does not establish causal order."],
    )


class RecommendationReportingAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = RecommendationReportingAgent()

    def strong_evidence(self) -> list[EvidenceReference]:
        return [
            reference("performance", 0, "latency", 280, device_id="R1"),
            reference("infrastructure", 1, "CPU utilization", 97, device_id="R1"),
            reference(
                "connectivity",
                2,
                "Network link state",
                "down",
                affected_device_ids=["R1", "R2"],
                affected_link_ids=["link-1"],
                affected_segment_ids=["segment-a"],
            ),
        ]

    def test_high_confidence_diagnosis_generates_evidence_based_report(self) -> None:
        result = correlation_result(
            [hypothesis(1, "device_resource_exhaustion", 0.86, self.strong_evidence())]
        )

        report = self.agent.analyze(result)

        self.assertEqual(report.incident_status, "probable_cause")
        self.assertEqual(report.confidence_category, "high")
        self.assertEqual(report.probable_root_cause, result.hypotheses[0].explanation)
        self.assertEqual(report.affected_device_ids, ["R1", "R2"])
        self.assertEqual(report.affected_link_ids, ["link-1"])
        self.assertEqual(report.affected_segment_ids, ["segment-a"])
        self.assertEqual(len(report.supporting_evidence), 3)
        self.assertEqual(
            report.evidence_sources,
            [
                "connectivity.findings[2]",
                "infrastructure.findings[1]",
                "performance.findings[0]",
            ],
        )
        self.assertTrue(report.recommended_actions)
        self.assertTrue(report.alternative_explanations)
        self.assertTrue(report.uncertainties)
        self.assertIn("Agent 4", report.limitations[-1])

    def test_low_confidence_diagnosis_is_labeled_low(self) -> None:
        result = correlation_result(
            [hypothesis(1, "device_resource_exhaustion", 0.52, self.strong_evidence())]
        )

        report = self.agent.analyze(result)

        self.assertEqual(report.confidence_score, 0.52)
        self.assertEqual(report.confidence_category, "low")
        self.assertEqual(report.incident_status, "probable_cause")

    def test_insufficient_evidence_is_explicit_and_does_not_name_a_cause(self) -> None:
        result = correlation_result([], insufficient=True)

        report = self.agent.analyze(result)

        self.assertEqual(report.incident_status, "insufficient_evidence")
        self.assertEqual(report.confidence_category, "insufficient")
        self.assertIsNone(report.confidence_score)
        self.assertIsNone(report.probable_root_cause)
        self.assertEqual(report.supporting_evidence, [])
        self.assertTrue(report.recommended_actions)
        self.assertIn("Collect", report.recommended_actions[0].action)

    def test_no_fault_result_is_distinct_from_insufficient_evidence(self) -> None:
        result = correlation_result([], status="no_fault_detected")

        report = self.agent.analyze(result)

        self.assertEqual(report.incident_status, "no_fault_detected")
        self.assertEqual(report.confidence_category, "not_applicable")
        self.assertIsNone(report.confidence_score)
        self.assertIsNone(report.probable_root_cause)
        self.assertEqual(report.recommended_actions[0].priority, "low")
        self.assertIn("routine monitoring", report.recommended_actions[0].action)

    def test_conflicts_and_their_evidence_are_preserved_in_report(self) -> None:
        source_refs = [
            reference("infrastructure", 0, "Device status", "online", device_id="R1"),
            reference(
                "connectivity", 0, "Device reachability", "unreachable",
                device_id="R1", affected_device_ids=["R1"],
            ),
        ]
        conflict = EvidenceConflict(
            description="The device is simultaneously reported online and unreachable.",
            evidence=source_refs,
            affected_device_ids=["R1"],
        )
        result = correlation_result(
            [], insufficient=True, conflicts=[conflict]
        )

        report = self.agent.analyze(result)

        self.assertEqual(report.conflicts, [conflict])
        self.assertEqual(
            set(report.evidence_sources),
            {"infrastructure.findings[0]", "connectivity.findings[0]"},
        )
        self.assertIn("Conflicting evidence", report.uncertainties[-1])

    def test_multiple_hypotheses_become_ranked_alternatives_and_actions(self) -> None:
        first = hypothesis(
            1, "device_resource_exhaustion", 0.84, self.strong_evidence()
        )
        second = hypothesis(
            2,
            "interface_or_queue_drops",
            0.71,
            [
                reference("performance", 3, "packet loss", 4, device_id="R1"),
                reference(
                    "infrastructure",
                    4,
                    "Egress queue drops",
                    12,
                    device_id="R1",
                    affected_link_ids=["link-2"],
                ),
            ],
        )
        result = correlation_result([first, second])

        report = self.agent.analyze(result)

        self.assertEqual(len(report.alternative_explanations), 1)
        self.assertEqual(report.alternative_hypotheses[0].rank, 2)
        self.assertEqual(len(report.recommended_actions), 2)
        self.assertEqual(report.recommended_actions[0].priority, "high")
        self.assertEqual(report.recommended_actions[1].priority, "medium")
        self.assertEqual(report.affected_link_ids, ["link-1"])

    def test_missing_or_malformed_correlation_results_are_rejected(self) -> None:
        missing = {"diagnosis_id": "missing"}
        malformed = {
            **correlation_result(
                [hypothesis(1, "device_resource_exhaustion", 0.86, self.strong_evidence())]
            ).model_dump(mode="json"),
            "hypotheses": [
                {
                    "rank": 1,
                    "cause": "device_resource_exhaustion",
                    "explanation": "Bad reference.",
                    "confidence": 1.5,
                    "evidence": [],
                }
            ],
        }
        inconsistent = correlation_result([], insufficient=False)

        for payload in (missing, malformed):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                self.agent.analyze(payload)
        with self.assertRaises(ValueError):
            self.agent.analyze(inconsistent)

    def test_new_cause_recommendations_are_specific(self) -> None:
        causes = (
            ("weak_wifi_signal", "AP placement"),
            ("ethernet_interface_fault", "cabling"),
            ("dns_dhcp_failure", "DNS daemon"),
            ("interoperability_failure", "protocol and message schemas"),
        )
        for cause_name, keyword in causes:
            with self.subTest(cause=cause_name):
                cr = correlation_result([hypothesis(1, cause_name, 0.85, self.strong_evidence())])
                report = self.agent.analyze(cr)
                self.assertEqual(report.recommended_actions[0].related_cause, cause_name)
                self.assertIn(keyword, report.recommended_actions[0].action)


if __name__ == "__main__":
    unittest.main()

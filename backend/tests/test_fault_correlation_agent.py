"""Unit tests for deterministic cross-agent fault correlation."""

import unittest
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError

from backend.agents.fault_correlation_agent import FaultCorrelationAgent
from backend.models.agent_message import AgentFinding, AgentMessage


def make_finding(
    metric: str,
    value: float | str,
    severity: str,
    *,
    device_id: str | None = None,
    affected_device_ids: list[str] | None = None,
    affected_link_ids: list[str] | None = None,
    affected_segment_ids: list[str] | None = None,
    observed_at: datetime | None = None,
) -> AgentFinding:
    return AgentFinding(
        metric=metric,
        value=value,
        unit="test",
        severity=severity,
        device_id=device_id,
        observed_at=observed_at,
        assessment=f"Observed {metric}: {value}.",
        affected_device_ids=affected_device_ids or [],
        affected_link_ids=affected_link_ids or [],
        affected_segment_ids=affected_segment_ids or [],
    )


def make_message(agent: str, findings: list[AgentFinding], diagnosis_id="case-1"):
    return AgentMessage(
        diagnosis_id=diagnosis_id,
        agent=agent,
        summary=f"{agent} findings",
        samples_analyzed=1,
        findings=findings,
    )


def make_input(performance, infrastructure, connectivity):
    return {
        "performance": performance.model_dump(mode="json"),
        "infrastructure": infrastructure.model_dump(mode="json"),
        "connectivity": connectivity.model_dump(mode="json"),
    }


class FaultCorrelationAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = FaultCorrelationAgent()

    def test_agreeing_evidence_produces_cited_ranked_hypothesis(self) -> None:
        payload = make_input(
            make_message(
                "performance", [make_finding("latency", 280, "critical", device_id="R1")]
            ),
            make_message(
                "infrastructure",
                [make_finding("CPU utilization", 97, "critical", device_id="R1")],
            ),
            make_message(
                "connectivity",
                [
                    make_finding(
                        "Connectivity pattern",
                        "multiple affected devices",
                        "critical",
                        affected_device_ids=["R1", "R2"],
                        affected_link_ids=["link-1"],
                        affected_segment_ids=["segment-a"],
                    )
                ],
            ),
        )

        result = self.agent.analyze(payload)
        top = result.hypotheses[0]

        self.assertEqual(result.status, "complete")
        self.assertEqual(top.rank, 1)
        self.assertEqual(top.cause, "device_resource_exhaustion")
        self.assertEqual(top.affected_device_ids, ["R1"])
        self.assertEqual(top.affected_link_ids, ["link-1"])
        self.assertEqual(top.affected_segment_ids, ["segment-a"])
        self.assertEqual(
            {reference.agent for reference in top.evidence},
            {"performance", "infrastructure", "connectivity"},
        )
        self.assertEqual(
            {(reference.agent, reference.finding_index) for reference in top.evidence},
            {("performance", 0), ("infrastructure", 0), ("connectivity", 0)},
        )
        self.assertGreaterEqual(top.confidence, 0.6)
        self.assertTrue(top.uncertainties)
        self.assertTrue(result.alternative_explanations)

    def test_warning_only_cross_agent_evidence_is_treated_as_weak(self) -> None:
        result = self.agent.analyze(
            make_input(
                make_message(
                    "performance", [make_finding("latency", 120, "warning", device_id="R1")]
                ),
                make_message(
                    "infrastructure",
                    [make_finding("CPU utilization", 82, "warning", device_id="R1")],
                ),
                make_message("connectivity", []),
            )
        )

        self.assertEqual(result.status, "insufficient_evidence")
        self.assertLess(result.hypotheses[0].confidence, 0.6)
        self.assertTrue(result.insufficient_evidence)

    def test_conflicting_observation_reduces_confidence_below_reliable_threshold(self) -> None:
        payload = make_input(
            make_message(
                "performance", [make_finding("latency", 280, "critical", device_id="R1")]
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
                [make_finding(
                    "Device reachability", "unreachable", "critical",
                    device_id="R1", affected_device_ids=["R1"],
                )],
            ),
        )

        result = self.agent.analyze(payload)

        self.assertEqual(result.status, "insufficient_evidence")
        self.assertTrue(result.conflicts)
        self.assertLess(result.hypotheses[0].confidence, 0.6)

    def test_distant_observation_timestamps_reduce_confidence(self) -> None:
        observed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        payload = make_input(
            make_message(
                "performance", [make_finding(
                    "latency", 280, "critical", device_id="R1", observed_at=observed_at,
                )]
            ),
            make_message(
                "infrastructure", [make_finding(
                    "CPU utilization", 97, "critical", device_id="R1",
                    observed_at=observed_at + timedelta(minutes=10),
                )]
            ),
            make_message("connectivity", []),
        )

        result = self.agent.analyze(payload)

        hypothesis = result.hypotheses[0]
        self.assertEqual(result.status, "insufficient_evidence")
        self.assertLess(hypothesis.confidence, 0.6)
        self.assertTrue(any("temporal alignment is weak" in item for item in hypothesis.uncertainties))
        self.assertEqual(
            {reference.observed_at for reference in hypothesis.evidence},
            {observed_at, observed_at + timedelta(minutes=10)},
        )

    def test_close_matching_timestamps_retain_strong_evidence_score(self) -> None:
        observed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = self.agent.analyze(
            make_input(
                make_message("performance", [make_finding(
                    "latency", 280, "critical", device_id="R1", observed_at=observed_at,
                )]),
                make_message("infrastructure", [make_finding(
                    "CPU utilization", 97, "critical", device_id="R1",
                    observed_at=observed_at + timedelta(seconds=60),
                )]),
                make_message("connectivity", [make_finding(
                    "Connectivity pattern", "affected", "critical",
                    affected_device_ids=["R1"],
                )]),
            )
        )

        self.assertGreaterEqual(result.hypotheses[0].confidence, 0.6)
        self.assertFalse(any(
            "temporal alignment is weak" in item
            for item in result.hypotheses[0].uncertainties
        ))

    def test_conflicting_device_state_is_reported(self) -> None:
        payload = make_input(
            make_message("performance", []),
            make_message(
                "infrastructure",
                [make_finding("Device status", "online", "info", device_id="R1")],
            ),
            make_message(
                "connectivity",
                [
                    make_finding(
                        "Device reachability",
                        "unreachable",
                        "critical",
                        device_id="R1",
                        affected_device_ids=["R1"],
                    )
                ],
            ),
        )

        result = self.agent.analyze(payload)

        self.assertEqual(result.status, "insufficient_evidence")
        self.assertTrue(result.insufficient_evidence)
        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(result.conflicts[0].affected_device_ids, ["R1"])
        self.assertEqual(len(result.conflicts[0].evidence), 2)

    def test_unmatched_findings_return_explicit_insufficient_evidence(self) -> None:
        payload = make_input(
            make_message(
                "performance", [make_finding("latency", 280, "critical", device_id="R1")]
            ),
            make_message(
                "infrastructure",
                [make_finding("CPU utilization", 97, "critical", device_id="R2")],
            ),
            make_message("connectivity", []),
        )

        result = self.agent.analyze(payload)

        self.assertEqual(result.status, "insufficient_evidence")
        self.assertTrue(result.insufficient_evidence)
        self.assertEqual(result.hypotheses, [])
        self.assertIn("Insufficient evidence", result.summary)

    def test_complete_healthy_findings_are_no_fault_detected(self) -> None:
        result = self.agent.analyze(
            make_input(
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
        )

        self.assertEqual(result.status, "no_fault_detected")
        self.assertFalse(result.insufficient_evidence)
        self.assertEqual(result.hypotheses, [])
        self.assertIn("No fault detected", result.summary)

    def test_multiple_supported_causes_are_ranked_as_alternatives(self) -> None:
        payload = make_input(
            make_message(
                "performance",
                [
                    make_finding("latency", 280, "critical", device_id="R1"),
                    make_finding("packet loss", 5, "critical", device_id="R1"),
                ],
            ),
            make_message(
                "infrastructure",
                [
                    make_finding("CPU utilization", 97, "critical", device_id="R1"),
                    make_finding("Egress queue drops", 12, "critical", device_id="R1"),
                ],
            ),
            make_message(
                "connectivity",
                [
                    make_finding(
                        "Network link state",
                        "down",
                        "critical",
                        affected_device_ids=["R1", "R2"],
                    )
                ],
            ),
        )

        result = self.agent.analyze(payload)

        self.assertGreaterEqual(len(result.hypotheses), 2)
        self.assertEqual(
            [hypothesis.rank for hypothesis in result.hypotheses],
            list(range(1, len(result.hypotheses) + 1)),
        )
        self.assertEqual(result.hypotheses[0].cause, "device_resource_exhaustion")
        self.assertTrue(result.alternative_explanations)
        self.assertTrue(result.hypotheses[0].alternative_explanations)

    def test_malformed_or_mismatched_agent_messages_are_rejected(self) -> None:
        valid = make_input(
            make_message("performance", []),
            make_message("infrastructure", []),
            make_message("connectivity", []),
        )
        wrong_agent = {**valid, "infrastructure": {**valid["infrastructure"], "agent": "other"}}
        mismatched_diagnosis = {
            **valid,
            "connectivity": {**valid["connectivity"], "diagnosis_id": "case-2"},
        }
        malformed_finding = {
            **valid,
            "performance": {
                **valid["performance"],
                "findings": [
                    {
                        "metric": "latency",
                        "value": 200,
                        "unit": "ms",
                        "severity": "urgent",
                        "assessment": "bad severity",
                    }
                ],
            },
        }

        for payload in (wrong_agent, mismatched_diagnosis, malformed_finding):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                self.agent.analyze(payload)

    def test_correlates_weak_wifi_signal(self) -> None:
        payload = make_input(
            make_message("performance", [
                make_finding("wifi signal strength", -85, "critical", device_id="AP1"),
                make_finding("packet loss", 5.0, "critical", device_id="AP1"),
            ]),
            make_message("infrastructure", [
                make_finding("Device status", "degraded", "warning", device_id="AP1"),
            ]),
            make_message("connectivity", []),
        )
        result = self.agent.analyze(payload)
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.hypotheses[0].cause, "weak_wifi_signal")
        self.assertIn("AP1", result.hypotheses[0].affected_device_ids)

    def test_correlates_ethernet_interface_fault(self) -> None:
        payload = make_input(
            make_message("performance", [
                make_finding("packet loss", 4.0, "critical", device_id="SW1"),
            ]),
            make_message("infrastructure", [
                make_finding("Interface errors", 50, "critical", device_id="SW1"),
            ]),
            make_message("connectivity", []),
        )
        result = self.agent.analyze(payload)
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.hypotheses[0].cause, "ethernet_interface_fault")

    def test_correlates_dns_dhcp_failure(self) -> None:
        payload = make_input(
            make_message("performance", [
                make_finding("dns lookup time", 4000, "critical", device_id="SRV1"),
            ]),
            make_message("infrastructure", [
                make_finding("DHCP status", "failed", "critical", device_id="SRV1"),
            ]),
            make_message("connectivity", []),
        )
        result = self.agent.analyze(payload)
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.hypotheses[0].cause, "dns_dhcp_failure")

    def test_correlates_interoperability_failure(self) -> None:
        payload = make_input(
            make_message("performance", [
                make_finding("packet loss", 3.0, "critical", device_id="GW1"),
            ]),
            make_message("infrastructure", [
                make_finding("Interoperability compatibility", "incompatible", "critical", device_id="GW1"),
            ]),
            make_message("connectivity", []),
        )
        result = self.agent.analyze(payload)
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.hypotheses[0].cause, "interoperability_failure")


if __name__ == "__main__":
    unittest.main()

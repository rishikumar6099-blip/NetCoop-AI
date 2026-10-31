"""End-to-end unit tests for the multi-agent diagnosis workflow."""

import unittest

from pydantic import ValidationError

from backend.models.diagnosis import DiagnosisRequest
from backend.orchestrator.diagnosis_orchestrator import MultiAgentOrchestrator


def make_request(
    *,
    performance_sample=None,
    infrastructure_sample=None,
    devices=None,
    links=None,
):
    diagnosis_id = "workflow-case-1"
    return {
        "performance": {
            "diagnosis_id": diagnosis_id,
            "samples": [
                performance_sample
                or {
                    "device_id": "R1",
                    "latency_ms": 20,
                    "jitter_ms": 2,
                    "packet_loss_pct": 0,
                    "throughput_mbps": 100,
                    "link_utilization_pct": 30,
                }
            ],
        },
        "infrastructure": {
            "diagnosis_id": diagnosis_id,
            "samples": [
                infrastructure_sample
                or {
                    "device_id": "R1",
                    "cpu_utilization_pct": 30,
                    "memory_utilization_pct": 45,
                    "interface_errors": 0,
                    "egress_queue_drops": 0,
                    "device_status": "online",
                }
            ],
        },
        "connectivity": {
            "diagnosis_id": diagnosis_id,
            "devices": devices
            or [
                {"device_id": "R1", "segment_id": "segment-a", "reachability": "reachable"},
                {"device_id": "S1", "segment_id": "segment-a", "reachability": "reachable"},
            ],
            "links": links
            or [
                {
                    "link_id": "link-1",
                    "source_device_id": "R1",
                    "target_device_id": "S1",
                    "status": "up",
                }
            ],
        },
    }


class FailingAgent:
    def analyze(self, _telemetry):
        raise RuntimeError("simulated agent failure")


class OrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = MultiAgentOrchestrator()

    def test_normal_network_completes_all_stages_without_claiming_a_cause(self) -> None:
        response = self.orchestrator.run(make_request())

        self.assertEqual(response.status, "complete")
        self.assertEqual(response.diagnosis_id, "workflow-case-1")
        self.assertEqual(
            set(response.agent_messages),
            {"performance", "infrastructure", "connectivity"},
        )
        self.assertTrue(
            all(
                message.diagnosis_id == response.diagnosis_id
                for message in response.agent_messages.values()
            )
        )
        self.assertEqual(response.correlation_result.status, "no_fault_detected")
        self.assertFalse(response.correlation_result.insufficient_evidence)
        self.assertFalse(
            any("Device ID mismatch" in item for item in response.correlation_result.limitations)
        )
        self.assertEqual(response.diagnostic_report.incident_status, "no_fault_detected")
        self.assertEqual(response.diagnostic_report.confidence_category, "not_applicable")
        self.assertEqual(response.correlation_result.hypotheses, [])
        self.assertIsNone(response.diagnostic_report.probable_root_cause)
        self.assertEqual(response.failures, [])

    def test_network_congestion_correlates_performance_and_infrastructure(self) -> None:
        response = self.orchestrator.run(
            make_request(
                performance_sample={
                    "device_id": "R1",
                    "latency_ms": 280,
                    "packet_loss_pct": 4,
                },
                infrastructure_sample={
                    "device_id": "R1",
                    "cpu_utilization_pct": 97,
                    "egress_queue_drops": 14,
                },
            )
        )

        self.assertEqual(response.status, "complete")
        self.assertFalse(response.diagnostic_report.confidence_category == "insufficient")
        self.assertIn("R1", response.diagnostic_report.affected_device_ids)
        self.assertTrue(response.diagnostic_report.probable_root_cause)
        self.assertEqual(
            response.correlation_result.hypotheses[0].cause,
            "device_resource_exhaustion",
        )

    def test_infrastructure_failure_is_reported(self) -> None:
        response = self.orchestrator.run(
            make_request(
                infrastructure_sample={
                    "device_id": "R1",
                    "device_status": "offline",
                },
                devices=[
                    {"device_id": "R1", "segment_id": "segment-a", "reachability": "unreachable"},
                    {"device_id": "S1", "segment_id": "segment-a", "reachability": "reachable"},
                ],
            )
        )

        causes = {item.cause for item in response.correlation_result.hypotheses}
        self.assertEqual(response.status, "complete")
        self.assertIn("device_unavailable", causes)
        self.assertIn("R1", response.diagnostic_report.affected_device_ids)

    def test_connectivity_failure_preserves_affected_link_and_segment(self) -> None:
        response = self.orchestrator.run(
            make_request(
                performance_sample={"device_id": "R1", "latency_ms": 280},
                links=[
                    {
                        "link_id": "link-1",
                        "source_device_id": "R1",
                        "target_device_id": "S1",
                        "status": "down",
                    }
                ],
            )
        )

        self.assertEqual(response.status, "complete")
        self.assertEqual(response.diagnostic_report.affected_link_ids, ["link-1"])
        self.assertEqual(
            response.diagnostic_report.affected_segment_ids, ["segment-a"]
        )
        self.assertTrue(response.diagnostic_report.supporting_evidence)
        self.assertTrue(
            any(
                "link-1" in evidence.affected_link_ids
                for evidence in response.diagnostic_report.supporting_evidence
            )
        )

    def test_conflicting_agent_findings_remain_visible_in_final_report(self) -> None:
        response = self.orchestrator.run(
            make_request(
                infrastructure_sample={"device_id": "R1", "device_status": "online"},
                devices=[
                    {"device_id": "R1", "segment_id": "segment-a", "reachability": "unreachable"},
                    {"device_id": "S1", "segment_id": "segment-a", "reachability": "reachable"},
                ],
            )
        )

        self.assertEqual(response.status, "complete")
        self.assertEqual(response.correlation_result.status, "insufficient_evidence")
        self.assertEqual(len(response.correlation_result.conflicts), 1)
        self.assertTrue(response.correlation_result.conflicts[0].evidence)
        self.assertEqual(
            response.diagnostic_report.incident_status, "insufficient_evidence"
        )
        self.assertEqual(
            response.diagnostic_report.conflicts,
            response.correlation_result.conflicts,
        )
        self.assertTrue(response.diagnostic_report.conflicts[0].evidence)

    def test_missing_telemetry_is_rejected_before_agents_run(self) -> None:
        payload = make_request()
        payload.pop("infrastructure")

        with self.assertRaises(ValidationError):
            self.orchestrator.run(payload)

    def test_malformed_or_incompatible_input_is_rejected(self) -> None:
        malformed = make_request()
        malformed["connectivity"]["links"][0]["status"] = "broken-ish"
        mismatched_id = make_request()
        mismatched_id["infrastructure"]["diagnosis_id"] = "other-case"

        for payload in (malformed, mismatched_id):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                DiagnosisRequest.model_validate(payload)

    def test_insufficient_evidence_returns_report_without_root_cause(self) -> None:
        response = self.orchestrator.run(
            make_request(performance_sample={"device_id": "R1", "throughput_mbps": 100})
        )

        self.assertTrue(response.diagnostic_report.limitations)
        self.assertEqual(
            response.diagnostic_report.confidence_category, "insufficient"
        )
        self.assertIsNone(response.diagnostic_report.probable_root_cause)

    def test_partial_healthy_telemetry_lists_missing_observations(self) -> None:
        response = self.orchestrator.run(
            make_request(
                performance_sample={"device_id": "R1", "latency_ms": 20},
                infrastructure_sample={"device_id": "R1", "cpu_utilization_pct": 30},
            )
        )

        self.assertEqual(response.correlation_result.status, "insufficient_evidence")
        self.assertEqual(
            response.diagnostic_report.incident_status, "insufficient_evidence"
        )
        self.assertIsNone(response.diagnostic_report.probable_root_cause)
        limitations = "\n".join(response.diagnostic_report.limitations)
        for field in (
            "performance.samples[0].jitter_ms",
            "performance.samples[0].link_utilization_pct",
            "infrastructure.samples[0].memory_utilization_pct",
            "infrastructure.samples[0].device_status",
        ):
            self.assertIn(field, limitations)

    def test_different_device_ids_are_visible_without_inventing_matches(self) -> None:
        response = self.orchestrator.run(
            make_request(
                performance_sample={"device_id": "R1", "latency_ms": 20},
                infrastructure_sample={"device_id": "R2", "cpu_utilization_pct": 30},
                devices=[
                    {"device_id": "R3", "reachability": "reachable"},
                    {"device_id": "R4", "reachability": "reachable"},
                ],
                links=[{
                    "link_id": "link-3-4",
                    "source_device_id": "R3",
                    "target_device_id": "R4",
                    "status": "up",
                }],
            )
        )

        self.assertEqual(response.status, "complete")
        self.assertEqual(response.correlation_result.status, "insufficient_evidence")
        self.assertIsNone(response.diagnostic_report.probable_root_cause)
        mismatch_messages = [
            item for item in response.diagnostic_report.limitations
            if "Device ID mismatch" in item
        ]
        self.assertEqual(len(mismatch_messages), 2)
        self.assertTrue(any("R1 is observed in performance" in item for item in mismatch_messages))
        self.assertTrue(any("R2 is observed in infrastructure" in item for item in mismatch_messages))
        self.assertTrue(all("no device identity is inferred" in item for item in mismatch_messages))

    def test_matching_device_evidence_survives_other_section_id_mismatch(self) -> None:
        response = self.orchestrator.run(
            make_request(
                performance_sample={
                    "device_id": "R1", "latency_ms": 280, "packet_loss_pct": 4,
                },
                infrastructure_sample={
                    "device_id": "R1", "cpu_utilization_pct": 97,
                },
                devices=[
                    {"device_id": "R2", "reachability": "reachable"},
                    {"device_id": "R3", "reachability": "reachable"},
                ],
                links=[{
                    "link_id": "link-2-3",
                    "source_device_id": "R2",
                    "target_device_id": "R3",
                    "status": "up",
                }],
            )
        )

        self.assertEqual(response.correlation_result.status, "complete")
        self.assertEqual(
            response.correlation_result.hypotheses[0].cause,
            "device_resource_exhaustion",
        )
        self.assertEqual(response.diagnostic_report.affected_device_ids, ["R1"])
        self.assertTrue(
            any("Device ID mismatch" in item for item in response.diagnostic_report.limitations)
        )

    def test_agent_failure_returns_partial_result_without_fabricated_findings(self) -> None:
        cases = (
            ("performance", {"performance_agent": FailingAgent()}),
            ("infrastructure", {"infrastructure_agent": FailingAgent()}),
            ("connectivity", {"connectivity_agent": FailingAgent()}),
            ("fault_correlation", {"fault_correlation_agent": FailingAgent()}),
            (
                "recommendation_reporting",
                {"recommendation_reporting_agent": FailingAgent()},
            ),
        )
        for stage, failing_agent in cases:
            with self.subTest(stage=stage):
                response = MultiAgentOrchestrator(**failing_agent).run(make_request())

                self.assertEqual(response.status, "partial")
                self.assertEqual(response.failures[0].stage, stage)
                self.assertEqual(response.failures[0].error_type, "RuntimeError")
                self.assertIsNone(response.diagnostic_report)
                expected_messages = {"performance", "infrastructure", "connectivity"}
                if stage in expected_messages:
                    expected_messages.remove(stage)
                self.assertEqual(set(response.agent_messages), expected_messages)
                if stage in {"performance", "infrastructure", "connectivity", "fault_correlation"}:
                    self.assertIsNone(response.correlation_result)
                else:
                    self.assertIsNotNone(response.correlation_result)

        first_stage_failure = MultiAgentOrchestrator(
            performance_agent=FailingAgent()
        ).run(make_request())
        self.assertIn("infrastructure", first_stage_failure.agent_messages)
        self.assertIn("connectivity", first_stage_failure.agent_messages)


if __name__ == "__main__":
    unittest.main()

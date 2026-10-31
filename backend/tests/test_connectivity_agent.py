"""Unit tests for connectivity telemetry and topology analysis."""

import unittest

from pydantic import ValidationError

from backend.agents.connectivity_agent import ConnectivityAnalysisAgent
from backend.models.connectivity import ConnectivityTelemetry


class ConnectivityAnalysisAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = ConnectivityAnalysisAgent()

    @staticmethod
    def complete_topology() -> dict:
        return {
            "diagnosis_id": "connectivity-1",
            "devices": [
                {"device_id": "router-a", "segment_id": "segment-a", "reachability": "reachable"},
                {"device_id": "switch-a", "segment_id": "segment-a", "reachability": "reachable"},
            ],
            "links": [
                {
                    "link_id": "link-a",
                    "source_device_id": "router-a",
                    "target_device_id": "switch-a",
                    "status": "up",
                }
            ],
        }

    @staticmethod
    def finding(message, metric: str):
        return next(item for item in message.findings if item.metric == metric)

    def test_normal_connectivity_reports_no_confirmed_impact(self) -> None:
        message = self.agent.analyze(self.complete_topology())
        scope = self.finding(message, "Incident scope")

        self.assertEqual(message.agent, "connectivity")
        self.assertEqual(message.schema_version, "1.0")
        self.assertEqual(scope.value, "no confirmed impact")
        self.assertEqual(scope.severity, "info")

    def test_disconnected_device_is_identified(self) -> None:
        payload = self.complete_topology()
        payload["devices"][1]["reachability"] = "unreachable"

        message = self.agent.analyze(payload)
        disconnected = self.finding(message, "Device reachability")
        scope = self.finding(message, "Incident scope")

        self.assertEqual(disconnected.device_id, "switch-a")
        self.assertEqual(disconnected.affected_device_ids, ["switch-a"])
        self.assertEqual(scope.value, "individual device")

    def test_broken_link_has_evidence_and_affected_identifiers(self) -> None:
        payload = self.complete_topology()
        payload["links"][0]["status"] = "down"

        message = self.agent.analyze(payload)
        broken_link = self.finding(message, "Network link state")

        self.assertEqual(broken_link.value, "down")
        self.assertEqual(broken_link.affected_link_ids, ["link-a"])
        self.assertEqual(broken_link.affected_device_ids, ["router-a", "switch-a"])
        self.assertTrue(broken_link.evidence)
        self.assertEqual(
            self.finding(message, "Incident scope").value, "network segment"
        )

    def test_multiple_affected_devices_identify_segment_scope(self) -> None:
        payload = self.complete_topology()
        payload["devices"][0]["reachability"] = "unreachable"
        payload["devices"][1]["reachability"] = "unreachable"
        payload["links"][0]["status"] = "down"

        message = self.agent.analyze(payload)
        segment = self.finding(message, "Affected network segment")
        scope = self.finding(message, "Incident scope")

        self.assertEqual(segment.value, "segment-a")
        self.assertEqual(segment.affected_device_ids, ["router-a", "switch-a"])
        self.assertEqual(segment.affected_segment_ids, ["segment-a"])
        self.assertEqual(scope.value, "network segment")

    def test_unreachable_devices_in_same_segment_are_correlated(self) -> None:
        payload = self.complete_topology()
        payload["devices"][0]["reachability"] = "unreachable"
        payload["devices"][1]["reachability"] = "unreachable"

        message = self.agent.analyze(payload)
        pattern = self.finding(message, "Connectivity pattern")

        self.assertEqual(
            pattern.value, "multiple unreachable devices in one segment"
        )
        self.assertEqual(pattern.affected_segment_ids, ["segment-a"])

    def test_affected_devices_in_multiple_segments_have_wider_scope(self) -> None:
        payload = self.complete_topology()
        payload["devices"][1]["segment_id"] = "segment-b"
        payload["devices"][0]["reachability"] = "unreachable"
        payload["devices"][1]["reachability"] = "unreachable"
        payload["links"][0]["status"] = "down"

        message = self.agent.analyze(payload)
        scope = self.finding(message, "Incident scope")

        self.assertEqual(scope.value, "wider network")
        self.assertEqual(scope.affected_segment_ids, ["segment-a", "segment-b"])

    def test_incomplete_link_reference_is_reported_without_inventing_device(self) -> None:
        payload = {
            "diagnosis_id": "partial-topology",
            "devices": [
                {"device_id": "router-a", "reachability": "reachable"}
            ],
            "links": [
                {
                    "link_id": "link-partial",
                    "source_device_id": "router-a",
                    "target_device_id": "missing-device",
                    "status": "down",
                }
            ],
        }

        message = self.agent.analyze(payload)
        consistency = self.finding(message, "Topology consistency")
        broken_link = self.finding(message, "Network link state")
        scope = self.finding(message, "Incident scope")

        self.assertEqual(consistency.affected_link_ids, ["link-partial"])
        self.assertNotIn("missing-device", consistency.affected_device_ids)
        self.assertEqual(broken_link.affected_device_ids, ["router-a"])
        self.assertEqual(scope.value, "undetermined")

    def test_invalid_topology_data_is_rejected(self) -> None:
        invalid_payloads = (
            {
                "diagnosis_id": "bad-status",
                "devices": [{"device_id": "router-a", "reachability": "maybe"}],
            },
            {
                "diagnosis_id": "duplicate-device",
                "devices": [
                    {"device_id": "router-a", "reachability": "reachable"},
                    {"device_id": "router-a", "reachability": "unreachable"},
                ],
            },
            {"diagnosis_id": "empty", "devices": [], "links": []},
            {
                "diagnosis_id": "missing-link-endpoint",
                "links": [{"link_id": "link-a", "source_device_id": "router-a"}],
            },
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                ConnectivityTelemetry.model_validate(payload)


if __name__ == "__main__":
    unittest.main()

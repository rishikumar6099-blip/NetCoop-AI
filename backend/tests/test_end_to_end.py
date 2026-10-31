"""HTTP-level validation of the complete diagnosis workflow."""

import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import main
from backend.orchestrator.diagnosis_orchestrator import MultiAgentOrchestrator


SCENARIO_FILE = Path(__file__).parents[1] / "data" / "diagnosis_scenarios.json"


def post_diagnosis(payload: object) -> tuple[int, dict]:
    """Submit JSON to the FastAPI POST route through its ASGI HTTP interface."""
    body = json.dumps(payload).encode("utf-8")
    sent_messages = []
    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        sent_messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/diagnose",
        "raw_path": b"/api/diagnose",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ],
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
        "state": {},
    }
    asyncio.run(main.app(scope, receive, send))

    status = next(
        message["status"]
        for message in sent_messages
        if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in sent_messages
        if message["type"] == "http.response.body"
    )
    return status, json.loads(response_body)


class FailingPerformanceAgent:
    def analyze(self, _telemetry):
        raise RuntimeError("intentional integration-test failure")


class EndToEndDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = {
            scenario["id"]: scenario
            for scenario in json.loads(SCENARIO_FILE.read_text(encoding="utf-8"))
        }

    @staticmethod
    def assert_reference_matches_message(testcase, reference, agent_messages):
        testcase.assertIn(reference["agent"], agent_messages)
        source_message = agent_messages[reference["agent"]]
        index = reference["finding_index"]
        testcase.assertGreaterEqual(index, 0)
        testcase.assertLess(index, len(source_message["findings"]))
        original = source_message["findings"][index]
        for field in (
            "metric",
            "value",
            "severity",
            "assessment",
            "device_id",
            "interface_id",
            "affected_device_ids",
            "affected_link_ids",
            "affected_segment_ids",
        ):
            testcase.assertEqual(reference.get(field), original.get(field), field)

    def assert_scenario(self, scenario_id: str) -> dict:
        scenario = self.scenarios[scenario_id]
        status, response = post_diagnosis(scenario["request"])
        expected = scenario["expected"]

        self.assertEqual(status, 200, response)
        self.assertEqual(response["status"], expected["workflow_status"])
        self.assertEqual(response["diagnosis_id"], scenario["request"]["performance"]["diagnosis_id"])
        self.assertEqual(
            set(response["agent_messages"]),
            {"performance", "infrastructure", "connectivity"},
        )
        for agent_name, message in response["agent_messages"].items():
            self.assertEqual(message["agent"], agent_name)
            self.assertEqual(message["diagnosis_id"], response["diagnosis_id"])
            self.assertIsInstance(message["findings"], list)

        correlation = response["correlation_result"]
        report = response["diagnostic_report"]
        self.assertIsNotNone(correlation)
        self.assertIsNotNone(report)
        self.assertEqual(correlation["agent"], "fault_correlation")
        self.assertEqual(correlation["diagnosis_id"], response["diagnosis_id"])
        self.assertEqual(report["diagnosis_id"], response["diagnosis_id"])
        self.assertEqual(report["incident_status"], expected["incident_status"])
        self.assertEqual(len(correlation["conflicts"]), expected["conflicts"])
        self.assertEqual(report["affected_device_ids"], expected["affected_devices"])
        self.assertEqual(report["affected_link_ids"], expected["affected_links"])
        self.assertEqual(report["affected_segment_ids"], expected["affected_segments"])
        self.assertEqual(response["failures"], [])

        self.assertIn(
            report["confidence_category"],
            {"high", "moderate", "low", "insufficient", "not_applicable"},
        )
        self.assertTrue(report["limitations"])
        self.assertTrue(report["recommended_actions"])
        self.assertIsInstance(report["uncertainties"], list)

        for hypothesis in correlation["hypotheses"]:
            self.assertGreaterEqual(hypothesis["confidence"], 0)
            self.assertLessEqual(hypothesis["confidence"], 1)
            self.assertTrue(hypothesis["evidence"])
            for reference in hypothesis["evidence"]:
                self.assert_reference_matches_message(
                    self, reference, response["agent_messages"]
                )
        for conflict in correlation["conflicts"]:
            for reference in conflict["evidence"]:
                self.assert_reference_matches_message(
                    self, reference, response["agent_messages"]
                )
        for reference in report["supporting_evidence"]:
            self.assert_reference_matches_message(
                self, reference, response["agent_messages"]
            )
        self.assertEqual(report["conflicts"], correlation["conflicts"])
        for conflict in report["conflicts"]:
            for reference in conflict["evidence"]:
                self.assert_reference_matches_message(
                    self, reference, response["agent_messages"]
                )
        for hypothesis in report["alternative_hypotheses"]:
            for reference in hypothesis["evidence"]:
                self.assert_reference_matches_message(
                    self, reference, response["agent_messages"]
                )
        for recommendation in report["recommended_actions"]:
            for reference in recommendation["evidence"]:
                self.assert_reference_matches_message(
                    self, reference, response["agent_messages"]
                )
        expected_sources = {
            f"{reference['agent']}.findings[{reference['finding_index']}]"
            for hypothesis in correlation["hypotheses"]
            for reference in hypothesis["evidence"]
        }
        expected_sources.update(
            f"{reference['agent']}.findings[{reference['finding_index']}]"
            for conflict in correlation["conflicts"]
            for reference in conflict["evidence"]
        )
        self.assertEqual(set(report["evidence_sources"]), expected_sources)

        if expected["root_cause"] is None:
            self.assertIsNone(report["probable_root_cause"])
            if expected["incident_status"] == "no_fault_detected":
                self.assertEqual(correlation["status"], "no_fault_detected")
                self.assertFalse(correlation["insufficient_evidence"])
                self.assertEqual(report["confidence_category"], "not_applicable")
                self.assertIn("routine monitoring", report["recommended_actions"][0]["action"])
            else:
                self.assertEqual(report["confidence_category"], "insufficient")
                self.assertTrue(correlation["insufficient_evidence"])
                self.assertIn("Collect", report["recommended_actions"][0]["action"])
        else:
            self.assertTrue(correlation["hypotheses"])
            self.assertEqual(correlation["hypotheses"][0]["cause"], expected["root_cause"])
            self.assertEqual(
                report["probable_root_cause"], correlation["hypotheses"][0]["explanation"]
            )
            self.assertEqual(
                report["confidence_score"], correlation["hypotheses"][0]["confidence"]
            )
            self.assertIn(report["confidence_category"], {"high", "moderate", "low"})
            self.assertTrue(report["supporting_evidence"])
            self.assertTrue(report["uncertainties"])
            score = report["confidence_score"]
            expected_category = (
                "high" if score >= 0.8 else "moderate" if score >= 0.6 else "low"
            )
            self.assertEqual(report["confidence_category"], expected_category)

        return response

    def test_normal_network_scenario(self) -> None:
        self.assert_scenario("normal_network")

    def test_network_congestion_scenario(self) -> None:
        response = self.assert_scenario("network_congestion")
        self.assertEqual(
            response["diagnostic_report"]["recommended_actions"][0]["related_cause"],
            "interface_or_queue_drops",
        )
        self.assertIn(
            "queue counters",
            response["diagnostic_report"]["recommended_actions"][0]["action"],
        )

    def test_router_infrastructure_overload_scenario(self) -> None:
        response = self.assert_scenario("router_infrastructure_overload")
        self.assertEqual(
            response["diagnostic_report"]["recommended_actions"][0]["related_cause"],
            "device_resource_exhaustion",
        )
        self.assertIn(
            "CPU and memory history",
            response["diagnostic_report"]["recommended_actions"][0]["action"],
        )

    def test_broken_connectivity_scenario(self) -> None:
        response = self.assert_scenario("broken_connectivity")
        self.assertIn("L-B4-B5", response["diagnostic_report"]["affected_link_ids"])
        self.assertEqual(
            response["diagnostic_report"]["recommended_actions"][0]["related_cause"],
            "connectivity_path_failure",
        )
        self.assertIn(
            "down link",
            response["diagnostic_report"]["recommended_actions"][0]["action"],
        )

    def test_conflicting_evidence_scenario(self) -> None:
        response = self.assert_scenario("conflicting_device_state")
        conflict = response["correlation_result"]["conflicts"][0]
        self.assertIn("RTR-X5", conflict["affected_device_ids"])
        self.assertIsNone(response["diagnostic_report"]["probable_root_cause"])

    def test_incomplete_telemetry_scenario(self) -> None:
        response = self.assert_scenario("incomplete_telemetry")
        self.assertTrue(
            any(
                finding["metric"] == "Topology completeness"
                for finding in response["agent_messages"]["connectivity"]["findings"]
            )
        )
        self.assertIsNone(response["diagnostic_report"]["probable_root_cause"])

    def test_link_congestion_scenario(self) -> None:
        response = self.assert_scenario("link_congestion")
        self.assertEqual(
            response["diagnostic_report"]["recommended_actions"][0]["related_cause"],
            "interface_or_queue_drops",
        )
        self.assertIn("queue counters", response["diagnostic_report"]["recommended_actions"][0]["action"])

    def test_weak_wifi_signal_scenario(self) -> None:
        response = self.assert_scenario("weak_wifi_signal")
        self.assertEqual(
            response["diagnostic_report"]["recommended_actions"][0]["related_cause"],
            "weak_wifi_signal",
        )
        self.assertIn("AP placement", response["diagnostic_report"]["recommended_actions"][0]["action"])
        self.assertIn("AP-W3", response["diagnostic_report"]["affected_device_ids"])

    def test_ethernet_interface_fault_scenario(self) -> None:
        response = self.assert_scenario("ethernet_interface_fault")
        self.assertEqual(
            response["diagnostic_report"]["recommended_actions"][0]["related_cause"],
            "ethernet_interface_fault",
        )
        self.assertIn("cabling", response["diagnostic_report"]["recommended_actions"][0]["action"])
        self.assertIn("SW-E4", response["diagnostic_report"]["affected_device_ids"])

    def test_dns_dhcp_failure_scenario(self) -> None:
        response = self.assert_scenario("dns_dhcp_failure")
        self.assertEqual(
            response["diagnostic_report"]["recommended_actions"][0]["related_cause"],
            "dns_dhcp_failure",
        )
        self.assertIn("DNS daemon", response["diagnostic_report"]["recommended_actions"][0]["action"])
        self.assertIn("SRV-D5", response["diagnostic_report"]["affected_device_ids"])

    def test_interoperability_failure_scenario(self) -> None:
        response = self.assert_scenario("interoperability_failure")
        self.assertEqual(
            response["diagnostic_report"]["recommended_actions"][0]["related_cause"],
            "interoperability_failure",
        )
        self.assertIn("protocol and message schemas", response["diagnostic_report"]["recommended_actions"][0]["action"])
        self.assertIn("GW-INT6", response["diagnostic_report"]["affected_device_ids"])

    def test_invalid_input_returns_http_422(self) -> None:
        payload = self.scenarios["normal_network"]["request"]
        missing = {key: value for key, value in payload.items() if key != "infrastructure"}
        malformed = json.loads(json.dumps(payload))
        malformed["performance"]["samples"][0]["latency_ms"] = -1

        for invalid_payload in (missing, malformed):
            with self.subTest(payload=invalid_payload):
                status, response = post_diagnosis(invalid_payload)
                self.assertEqual(status, 422)
                self.assertIn("detail", response)

    def test_agent_failure_returns_partial_without_fabricated_findings(self) -> None:
        failing_orchestrator = MultiAgentOrchestrator(
            performance_agent=FailingPerformanceAgent()
        )
        with patch.object(
            main, "MultiAgentOrchestrator", return_value=failing_orchestrator
        ):
            status, response = post_diagnosis(
                self.scenarios["normal_network"]["request"]
            )

        self.assertEqual(status, 200)
        self.assertEqual(response["status"], "partial")
        self.assertNotIn("performance", response["agent_messages"])
        self.assertIn("infrastructure", response["agent_messages"])
        self.assertIn("connectivity", response["agent_messages"])
        self.assertIsNone(response["correlation_result"])
        self.assertIsNone(response["diagnostic_report"])
        self.assertEqual(response["failures"][0]["stage"], "performance")


if __name__ == "__main__":
    unittest.main()

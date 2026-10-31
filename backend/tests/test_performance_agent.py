"""Unit tests for telemetry validation and the Performance Agent."""

import unittest

from pydantic import ValidationError

from backend.agents.performance_agent import PerformanceAgent
from backend.models.telemetry import TelemetryBatch


class PerformanceAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = PerformanceAgent()

    def test_analyzes_valid_telemetry_and_returns_json_message(self) -> None:
        payload = {
            "diagnosis_id": "case-001",
            "samples": [
                {
                    "device_id": "router-a",
                    "interface_id": "eth0",
                    "latency_ms": 270,
                    "jitter_ms": 35,
                    "packet_loss_pct": 4,
                    "throughput_mbps": 600,
                    "link_utilization_pct": 82,
                }
            ],
        }

        message = self.agent.analyze(payload)
        result = message.model_dump(mode="json")
        by_metric = {finding["metric"]: finding for finding in result["findings"]}

        self.assertEqual(result["agent"], "performance")
        self.assertEqual(result["diagnosis_id"], "case-001")
        self.assertEqual(result["samples_analyzed"], 1)
        self.assertEqual(by_metric["latency"]["severity"], "critical")
        self.assertEqual(by_metric["jitter"]["severity"], "warning")
        self.assertEqual(by_metric["packet loss"]["severity"], "critical")
        self.assertEqual(by_metric["throughput"]["severity"], "info")
        self.assertEqual(by_metric["link utilization"]["severity"], "warning")

    def test_rejects_packet_loss_outside_valid_range(self) -> None:
        payload = {
            "diagnosis_id": "case-invalid",
            "samples": [
                {"device_id": "router-a", "packet_loss_pct": 101}
            ],
        }

        with self.assertRaises(ValidationError):
            self.agent.analyze(payload)

    def test_rejects_sample_without_performance_metrics(self) -> None:
        with self.assertRaises(ValidationError):
            TelemetryBatch.model_validate(
                {"diagnosis_id": "case-empty", "samples": [{"device_id": "r1"}]}
            )


    def test_evaluates_wifi_rssi_thresholds(self) -> None:
        payload_critical = {
            "diagnosis_id": "wifi-case-crit",
            "samples": [{"device_id": "ap-1", "rssi_dbm": -85}],
        }
        msg = self.agent.analyze(payload_critical)
        self.assertEqual(msg.findings[0].severity, "critical")
        self.assertEqual(msg.findings[0].unit, "dBm")

        payload_warning = {
            "diagnosis_id": "wifi-case-warn",
            "samples": [{"device_id": "ap-1", "rssi_dbm": -78}],
        }
        msg = self.agent.analyze(payload_warning)
        self.assertEqual(msg.findings[0].severity, "warning")

        payload_info = {
            "diagnosis_id": "wifi-case-info",
            "samples": [{"device_id": "ap-1", "rssi_dbm": -65}],
        }
        msg = self.agent.analyze(payload_info)
        self.assertEqual(msg.findings[0].severity, "info")

    def test_evaluates_dns_lookup_thresholds(self) -> None:
        payload = {
            "diagnosis_id": "dns-case",
            "samples": [{"device_id": "srv-1", "dns_lookup_time_ms": 1200}],
        }
        msg = self.agent.analyze(payload)
        self.assertEqual(msg.findings[0].severity, "critical")
        self.assertEqual(msg.findings[0].unit, "ms")


if __name__ == "__main__":
    unittest.main()

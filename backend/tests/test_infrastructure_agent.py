"""Unit tests for infrastructure telemetry and Infrastructure Health Agent."""

import unittest

from pydantic import ValidationError

from backend.agents.infrastructure_agent import InfrastructureHealthAgent
from backend.models.infrastructure import InfrastructureThresholds


def make_payload(**sample_fields):
    return {
        "diagnosis_id": "infra-case-1",
        "samples": [{"device_id": "switch-a", **sample_fields}],
    }


class InfrastructureHealthAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = InfrastructureHealthAgent()

    def findings_by_metric(self, payload):
        message = self.agent.analyze(payload)
        return message, {finding.metric: finding for finding in message.findings}

    def test_normal_infrastructure_conditions_are_informational(self) -> None:
        message, findings = self.findings_by_metric(
            make_payload(
                cpu_utilization_pct=45,
                memory_utilization_pct=60,
                interface_errors=0,
                egress_queue_drops=0,
                device_status="online",
            )
        )

        self.assertEqual(message.agent, "infrastructure")
        self.assertEqual(message.schema_version, "1.0")
        self.assertEqual(set(findings), {
            "CPU utilization",
            "Memory utilization",
            "Interface errors",
            "Egress queue drops",
            "Device status",
        })
        self.assertTrue(all(finding.severity == "info" for finding in findings.values()))
        self.assertTrue(all(finding.device_id == "switch-a" for finding in findings.values()))

    def test_high_cpu_utilization_is_flagged(self) -> None:
        _, findings = self.findings_by_metric(make_payload(cpu_utilization_pct=97))

        self.assertEqual(findings["CPU utilization"].severity, "critical")
        self.assertEqual(findings["CPU utilization"].critical_threshold, 95)

    def test_high_memory_utilization_is_flagged(self) -> None:
        _, findings = self.findings_by_metric(
            make_payload(memory_utilization_pct=85)
        )

        self.assertEqual(findings["Memory utilization"].severity, "warning")
        self.assertEqual(findings["Memory utilization"].device_id, "switch-a")

    def test_interface_errors_and_queue_drops_are_flagged(self) -> None:
        _, findings = self.findings_by_metric(
            make_payload(interface_errors=10, egress_queue_drops=12)
        )

        self.assertEqual(findings["Interface errors"].severity, "critical")
        self.assertEqual(findings["Egress queue drops"].severity, "critical")

    def test_offline_device_is_critical(self) -> None:
        _, findings = self.findings_by_metric(make_payload(device_status="offline"))

        self.assertEqual(findings["Device status"].value, "offline")
        self.assertEqual(findings["Device status"].severity, "critical")

    def test_thresholds_are_configurable(self) -> None:
        thresholds = InfrastructureThresholds(cpu_warning_pct=70, cpu_critical_pct=90)
        agent = InfrastructureHealthAgent(thresholds=thresholds)

        message = agent.analyze(make_payload(cpu_utilization_pct=75))

        self.assertEqual(message.findings[0].severity, "warning")
        self.assertEqual(message.findings[0].warning_threshold, 70)

    def test_invalid_telemetry_is_rejected(self) -> None:
        invalid_payloads = (
            make_payload(cpu_utilization_pct=101),
            make_payload(interface_errors=-1),
            make_payload(device_status="unknown"),
            {"diagnosis_id": "empty", "samples": [{"device_id": "switch-a"}]},
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                self.agent.analyze(payload)


    def test_evaluates_dhcp_status(self) -> None:
        _, findings_failed = self.findings_by_metric(make_payload(dhcp_status="failed"))
        self.assertEqual(findings_failed["DHCP status"].severity, "critical")
        self.assertEqual(findings_failed["DHCP status"].value, "failed")

        _, findings_bound = self.findings_by_metric(make_payload(dhcp_status="bound"))
        self.assertEqual(findings_bound["DHCP status"].severity, "info")

    def test_evaluates_link_flaps(self) -> None:
        _, findings = self.findings_by_metric(make_payload(link_flaps=7))
        self.assertEqual(findings["Link flaps"].severity, "critical")
        self.assertEqual(findings["Link flaps"].critical_threshold, 5.0)

    def test_evaluates_interoperability_status(self) -> None:
        _, findings = self.findings_by_metric(make_payload(interoperability_status="incompatible"))
        self.assertEqual(findings["Interoperability compatibility"].severity, "critical")


if __name__ == "__main__":
    unittest.main()

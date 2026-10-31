"""Unit tests for telemetry normalization, unit conversion, schema versioning, and interoperability."""

import unittest
from pydantic import ValidationError

from backend.agents.performance_agent import PerformanceAgent
from backend.agents.infrastructure_agent import InfrastructureHealthAgent
from backend.models.diagnosis import DiagnosisRequest
from backend.models.telemetry import TelemetryBatch, TelemetrySample
from backend.models.infrastructure import InfrastructureTelemetryBatch, InfrastructureTelemetrySample
from backend.models.connectivity import ConnectivityTelemetry
from backend.models.agent_message import AgentMessage
from backend.orchestrator.diagnosis_orchestrator import MultiAgentOrchestrator
from backend.services.interoperability import (
    IncompatibleFieldError,
    IncompatibleSchemaVersionError,
    IncompatibleUnitError,
    normalize_metric_value_and_unit,
    normalize_sample_payload,
    validate_schema_version,
)


class IncompatibleAgent:
    """Simulates an external or legacy agent returning an incompatible schema version."""
    def analyze(self, telemetry):
        return {
            "schema_version": "2.0",
            "diagnosis_id": telemetry.diagnosis_id,
            "agent": "performance",
            "summary": "Incompatible schema output",
            "samples_analyzed": 1,
            "findings": [],
        }


class InteroperabilityServiceTests(unittest.TestCase):
    def test_schema_version_validation(self) -> None:
        self.assertEqual(validate_schema_version("1.0"), "1.0")
        self.assertEqual(validate_schema_version(None), "1.0")

        for bad_version in ("2.0", "0.9", "v1", "beta"):
            with self.subTest(version=bad_version):
                with self.assertRaises(IncompatibleSchemaVersionError) as ctx:
                    validate_schema_version(bad_version)
                self.assertIn("Incompatible schema version", str(ctx.exception))

    def test_unit_normalization_time(self) -> None:
        self.assertEqual(normalize_metric_value_and_unit("latency_ms", "250ms"), 250.0)
        self.assertEqual(normalize_metric_value_and_unit("latency_ms", "0.25s"), 250.0)
        self.assertEqual(normalize_metric_value_and_unit("latency_ms", 0.5, explicit_unit="s"), 500.0)
        self.assertEqual(normalize_metric_value_and_unit("latency_ms", "50000us"), 50.0)
        self.assertEqual(normalize_metric_value_and_unit("jitter_ms", "15 ms"), 15.0)

    def test_unit_normalization_throughput(self) -> None:
        self.assertEqual(normalize_metric_value_and_unit("throughput_mbps", "100Mbps"), 100.0)
        self.assertEqual(normalize_metric_value_and_unit("throughput_mbps", "1Gbps"), 1000.0)
        self.assertEqual(normalize_metric_value_and_unit("throughput_mbps", 2, explicit_unit="gbps"), 2000.0)
        self.assertEqual(normalize_metric_value_and_unit("throughput_mbps", "50000Kbps"), 50.0)
        self.assertEqual(normalize_metric_value_and_unit("throughput_mbps", "100000000bps"), 100.0)

    def test_unit_normalization_percentage(self) -> None:
        self.assertEqual(normalize_metric_value_and_unit("packet_loss_pct", "4.5%"), 4.5)
        self.assertEqual(normalize_metric_value_and_unit("packet_loss_pct", 0.05, explicit_unit="ratio"), 5.0)
        self.assertEqual(normalize_metric_value_and_unit("cpu_utilization_pct", "92 %"), 92.0)

    def test_unit_normalization_signal(self) -> None:
        self.assertEqual(normalize_metric_value_and_unit("rssi_dbm", "-82 dBm"), -82.0)
        self.assertEqual(normalize_metric_value_and_unit("rssi_dbm", "-75dBm"), -75.0)

    def test_incompatible_units_are_rejected(self) -> None:
        cases = (
            ("latency_ms", "50kg"),
            ("latency_ms", 100, "volts"),
            ("throughput_mbps", "100celsius"),
            ("packet_loss_pct", 5, "volts"),
            ("rssi_dbm", -70, "watts"),
            ("interface_errors", 10, "meters"),
        )
        for field, val, *unit in cases:
            explicit_u = unit[0] if unit else None
            with self.subTest(field=field, val=val, unit=explicit_u):
                with self.assertRaises(IncompatibleUnitError) as ctx:
                    normalize_metric_value_and_unit(field, val, explicit_unit=explicit_u)
                self.assertIn("Incompatible unit", str(ctx.exception))

    def test_field_alias_normalization(self) -> None:
        raw_perf = {
            "device_id": "r1",
            "latency": "120ms",
            "loss_pct": "3.5%",
            "bandwidth": "1Gbps",
            "rssi": "-78dBm",
        }
        normalized = normalize_sample_payload(raw_perf, "performance")
        self.assertEqual(normalized["device_id"], "r1")
        self.assertEqual(normalized["latency_ms"], 120.0)
        self.assertEqual(normalized["packet_loss_pct"], 3.5)
        self.assertEqual(normalized["throughput_mbps"], 1000.0)
        self.assertEqual(normalized["rssi_dbm"], -78.0)

        raw_infra = {
            "device_id": "sw1",
            "cpu_usage": "88%",
            "mem_pct": "75%",
            "crc_errors": 15,
            "queue_drops": 20,
            "status": "degraded",
        }
        norm_infra = normalize_sample_payload(raw_infra, "infrastructure")
        self.assertEqual(norm_infra["cpu_utilization_pct"], 88.0)
        self.assertEqual(norm_infra["memory_utilization_pct"], 75.0)
        self.assertEqual(norm_infra["interface_errors"], 15)
        self.assertEqual(norm_infra["egress_queue_drops"], 20)
        self.assertEqual(norm_infra["device_status"], "degraded")

    def test_conflicting_field_names_rejected(self) -> None:
        conflicting = {
            "device_id": "r1",
            "latency": "100ms",
            "latency_ms": 200,
        }
        with self.assertRaises(IncompatibleFieldError) as ctx:
            normalize_sample_payload(conflicting, "performance")
        self.assertIn("Conflicting field definitions", str(ctx.exception))


class ModelInteroperabilityTests(unittest.TestCase):
    def test_telemetry_sample_normalizes_aliases_and_units(self) -> None:
        sample = TelemetrySample.model_validate({
            "device_id": "RTR-TEST",
            "latency": "220ms",
            "packet_loss": "4.2%",
            "bandwidth": "500Mbps",
            "rssi": "-85 dBm",
            "dns_latency": "1200ms",
        })
        self.assertEqual(sample.latency_ms, 220.0)
        self.assertEqual(sample.packet_loss_pct, 4.2)
        self.assertEqual(sample.throughput_mbps, 500.0)
        self.assertEqual(sample.rssi_dbm, -85.0)
        self.assertEqual(sample.dns_lookup_time_ms, 1200.0)

    def test_telemetry_sample_rejects_incompatible_unit(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            TelemetrySample.model_validate({
                "device_id": "RTR-TEST",
                "latency": "500kg",
            })
        self.assertIn("Incompatible unit", str(ctx.exception))

    def test_infrastructure_sample_normalizes_aliases(self) -> None:
        sample = InfrastructureTelemetrySample.model_validate({
            "device_id": "SW-TEST",
            "cpu_usage": "96%",
            "memory_usage": "88%",
            "crc_errors": 45,
            "queue_drops": 12,
            "dhcp_state": "failed",
            "status": "degraded",
        })
        self.assertEqual(sample.cpu_utilization_pct, 96.0)
        self.assertEqual(sample.memory_utilization_pct, 88.0)
        self.assertEqual(sample.interface_errors, 45)
        self.assertEqual(sample.egress_queue_drops, 12)
        self.assertEqual(sample.dhcp_status, "failed")
        self.assertEqual(sample.device_status, "degraded")

    def test_diagnosis_request_rejects_incompatible_schema_version(self) -> None:
        req_data = {
            "schema_version": "2.0",
            "performance": {"diagnosis_id": "test-1", "samples": [{"device_id": "r1", "latency_ms": 20}]},
            "infrastructure": {"diagnosis_id": "test-1", "samples": [{"device_id": "r1", "cpu_utilization_pct": 20}]},
            "connectivity": {"diagnosis_id": "test-1", "devices": [{"device_id": "r1", "reachability": "reachable"}]},
        }
        with self.assertRaises(ValidationError) as ctx:
            DiagnosisRequest.model_validate(req_data)
        self.assertIn("Incompatible schema version", str(ctx.exception))

    def test_agent_message_rejects_incompatible_schema_version(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            AgentMessage.model_validate({
                "schema_version": "9.9",
                "diagnosis_id": "test-1",
                "agent": "performance",
                "summary": "Summary",
                "samples_analyzed": 1,
                "findings": [],
            })
        self.assertIn("Incompatible schema version", str(ctx.exception))


class OrchestratorInteroperabilityTests(unittest.TestCase):
    def test_orchestrator_handles_telemetry_with_aliases_and_string_units(self) -> None:
        req = {
            "performance": {
                "diagnosis_id": "diag-interop-1",
                "samples": [{
                    "device_id": "R1",
                    "latency": "18ms",
                    "jitter": "2ms",
                    "packet_loss": "0%",
                    "bandwidth": "1Gbps",
                    "link_utilization": "25%",
                }],
            },
            "infrastructure": {
                "diagnosis_id": "diag-interop-1",
                "samples": [{
                    "device_id": "R1",
                    "cpu_usage": "30%",
                    "memory_usage": "40%",
                    "crc_errors": 0,
                    "queue_drops": 0,
                    "status": "online",
                }],
            },
            "connectivity": {
                "diagnosis_id": "diag-interop-1",
                "devices": [
                    {"device_id": "R1", "segment_id": "core", "reachability": "reachable"},
                    {"device_id": "S1", "segment_id": "core", "reachability": "reachable"},
                ],
                "links": [
                    {"link_id": "L1", "source_device_id": "R1", "target_device_id": "S1", "status": "up"}
                ],
            },
        }
        orchestrator = MultiAgentOrchestrator()
        response = orchestrator.run(req)
        self.assertEqual(response.status, "complete")
        self.assertEqual(response.diagnostic_report.incident_status, "no_fault_detected")
        self.assertEqual(response.failures, [])

    def test_orchestrator_catches_incompatible_agent_schema_without_fabrication(self) -> None:
        orchestrator = MultiAgentOrchestrator(performance_agent=IncompatibleAgent())
        req = {
            "performance": {
                "diagnosis_id": "diag-interop-fail",
                "samples": [{"device_id": "R1", "latency_ms": 20}],
            },
            "infrastructure": {
                "diagnosis_id": "diag-interop-fail",
                "samples": [{"device_id": "R1", "cpu_utilization_pct": 30}],
            },
            "connectivity": {
                "diagnosis_id": "diag-interop-fail",
                "devices": [{"device_id": "R1", "reachability": "reachable"}],
            },
        }
        response = orchestrator.run(req)
        self.assertEqual(response.status, "partial")
        self.assertEqual(len(response.failures), 1)
        self.assertEqual(response.failures[0].stage, "performance")
        self.assertIn("IncompatibleSchemaVersionError", response.failures[0].error_type)
        self.assertNotIn("performance", response.agent_messages)
        self.assertIn("infrastructure", response.agent_messages)
        self.assertIsNone(response.correlation_result)
        self.assertIsNone(response.diagnostic_report)


if __name__ == "__main__":
    unittest.main()

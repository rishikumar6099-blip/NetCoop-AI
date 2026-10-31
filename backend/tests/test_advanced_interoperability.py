"""Comprehensive tests for advanced interoperability, connectivity aliases, schema rules, and validation endpoint."""

import json
import unittest

from pydantic import ValidationError

from backend.models.agent_message import AgentFinding, AgentMessage
from backend.models.connectivity import (
    ConnectivityTelemetry,
    TopologyDevice,
    TopologyLink,
)
from backend.models.correlation import EvidenceReference
from backend.services.interoperability import (
    AmbiguousFieldMappingError,
    IncompatibleFieldError,
    IncompatibleSchemaVersionError,
    IncompatibleUnitError,
    normalize_connectivity_payload,
    normalize_device_payload,
    normalize_link_payload,
    normalize_metric_value_and_unit,
    normalize_sample_payload,
    validate_evidence_traceability,
    validate_interoperability,
    validate_schema_version,
)
from backend.tests.test_history_storage import asgi_request


class AdvancedInteroperabilityTests(unittest.TestCase):
    def test_connectivity_device_field_aliases(self) -> None:
        # device_id aliases: "id", "hostname", "node_id", "dev_id"
        # segment_id aliases: "vlan", "subnet", "network_segment"
        # reachability aliases: "state", "status", "ping_status"
        payload_1 = {"id": "RTR-CORE", "vlan": "vlan-100", "state": "UP"}
        device_1 = TopologyDevice.model_validate(payload_1)
        self.assertEqual(device_1.device_id, "RTR-CORE")
        self.assertEqual(device_1.segment_id, "vlan-100")
        self.assertEqual(device_1.reachability, "reachable")

        payload_2 = {"hostname": "SW-DIST", "subnet": "10.0.1.0/24", "status": "offline"}
        device_2 = TopologyDevice.model_validate(payload_2)
        self.assertEqual(device_2.device_id, "SW-DIST")
        self.assertEqual(device_2.segment_id, "10.0.1.0/24")
        self.assertEqual(device_2.reachability, "unreachable")

    def test_connectivity_link_field_aliases(self) -> None:
        # link_id: "link", "id", "edge_id"
        # source_device_id: "src", "source", "from"
        # target_device_id: "dst", "dest", "to"
        # status: "state", "link_state"
        # medium: "type", "connection_type"
        payload = {
            "link": "L-101",
            "src": "RTR-CORE",
            "dst": "SW-DIST",
            "state": "ACTIVE",
            "type": "ethernet",
        }
        link = TopologyLink.model_validate(payload)
        self.assertEqual(link.link_id, "L-101")
        self.assertEqual(link.source_device_id, "RTR-CORE")
        self.assertEqual(link.target_device_id, "SW-DIST")
        self.assertEqual(link.status, "up")
        self.assertEqual(link.medium, "ethernet")

    def test_case_insensitive_link_and_reachability_states(self) -> None:
        # Reachability synonyms
        for up_val in ("UP", "online", "ACTIVE", "connected", "available", "yes", "true", "1"):
            d = TopologyDevice.model_validate({"device_id": "D1", "reachability": up_val})
            self.assertEqual(d.reachability, "reachable")

        for down_val in ("DOWN", "offline", "INACTIVE", "disconnected", "failed", "unreach", "0"):
            d = TopologyDevice.model_validate({"device_id": "D1", "reachability": down_val})
            self.assertEqual(d.reachability, "unreachable")

        # Link status synonyms
        for up_val in ("UP", "Online", "ACTIVE", "operational", "enabled"):
            l = TopologyLink.model_validate({
                "link_id": "L1", "source_device_id": "A", "target_device_id": "B", "status": up_val
            })
            self.assertEqual(l.status, "up")

        for down_val in ("DOWN", "offline", "INACTIVE", "disconnected", "failed", "disabled"):
            l = TopologyLink.model_validate({
                "link_id": "L1", "source_device_id": "A", "target_device_id": "B", "status": down_val
            })
            self.assertEqual(l.status, "down")

    def test_unknown_states_never_silently_interpreted_as_healthy(self) -> None:
        # Flapping or degraded or pending states must map to canonical "unknown", NEVER to "up" or "reachable"
        for val in ("flapping", "degraded", "pending", "unmonitored", "unknown", "none"):
            d = TopologyDevice.model_validate({"device_id": "D1", "reachability": val})
            self.assertEqual(d.reachability, "unknown")
            self.assertNotEqual(d.reachability, "reachable")

            l = TopologyLink.model_validate({
                "link_id": "L1", "source_device_id": "A", "target_device_id": "B", "status": val
            })
            self.assertEqual(l.status, "unknown")
            self.assertNotEqual(l.status, "up")

        # Completely invalid or unmapped states must NOT be coerced to healthy; they are rejected
        for bad_val in ("maybe", "broken-ish", "random_gibberish"):
            with self.assertRaises(ValidationError):
                TopologyDevice.model_validate({"device_id": "D1", "reachability": bad_val})
            with self.assertRaises(ValidationError):
                TopologyLink.model_validate({
                    "link_id": "L1", "source_device_id": "A", "target_device_id": "B", "status": bad_val
                })

    def test_connectivity_topology_level_aliases(self) -> None:
        # "nodes" -> "devices", "edges" -> "links"
        payload = {
            "diagnosis_id": "diag-top-1",
            "nodes": [
                {"id": "R1", "state": "UP"},
                {"id": "R2", "state": "UP"},
            ],
            "edges": [
                {"id": "E1", "from": "R1", "to": "R2", "state": "UP"}
            ],
        }
        telemetry = ConnectivityTelemetry.model_validate(payload)
        self.assertEqual(len(telemetry.devices), 2)
        self.assertEqual(len(telemetry.links), 1)
        self.assertEqual(telemetry.devices[0].device_id, "R1")
        self.assertEqual(telemetry.links[0].source_device_id, "R1")

    def test_ambiguous_field_mappings_are_rejected(self) -> None:
        # Conflicting device ID aliases
        with self.assertRaises(AmbiguousFieldMappingError):
            normalize_device_payload({"device_id": "R1", "id": "R2"})

        with self.assertRaises(ValidationError) as ctx:
            TopologyDevice.model_validate({"device_id": "R1", "id": "R2"})
        self.assertIn("Conflicting field definitions", str(ctx.exception))

        # Conflicting link source aliases
        with self.assertRaises(AmbiguousFieldMappingError):
            normalize_link_payload({
                "link_id": "L1", "source": "R1", "src": "R2", "target": "R3"
            })

        # Conflicting performance aliases
        with self.assertRaises(AmbiguousFieldMappingError):
            normalize_sample_payload({"latency": 100, "rtt": 200}, "performance")

        # Redundant identical values must NOT raise error
        device = TopologyDevice.model_validate({"device_id": "R1", "id": "R1"})
        self.assertEqual(device.device_id, "R1")

    def test_unit_conversions_and_incompatible_units(self) -> None:
        # Time conversions
        self.assertEqual(normalize_metric_value_and_unit("latency_ms", "250ms"), 250.0)
        self.assertEqual(normalize_metric_value_and_unit("latency_ms", "0.25s"), 250.0)
        self.assertEqual(normalize_metric_value_and_unit("latency_ms", "250000us"), 250.0)

        # Throughput conversions
        self.assertEqual(normalize_metric_value_and_unit("throughput_mbps", "100Mbps"), 100.0)
        self.assertEqual(normalize_metric_value_and_unit("throughput_mbps", "0.1Gbps"), 100.0)
        self.assertEqual(normalize_metric_value_and_unit("throughput_mbps", "100000Kbps"), 100.0)

        # Percentage conversions
        self.assertEqual(normalize_metric_value_and_unit("packet_loss_pct", "5%"), 5.0)
        self.assertEqual(normalize_metric_value_and_unit("packet_loss_pct", 0.05, explicit_unit="ratio"), 5.0)

        # Incompatible units
        with self.assertRaises(IncompatibleUnitError):
            normalize_metric_value_and_unit("latency_ms", 100, explicit_unit="kelvin")
        with self.assertRaises(IncompatibleUnitError):
            normalize_metric_value_and_unit("throughput_mbps", 100, explicit_unit="meters")
        with self.assertRaises(IncompatibleUnitError):
            normalize_metric_value_and_unit("packet_loss_pct", 5, explicit_unit="seconds")

    def test_schema_version_compatibility(self) -> None:
        # Supported: 1.0
        self.assertEqual(validate_schema_version("1.0"), "1.0")
        self.assertEqual(validate_schema_version(None), "1.0")

        # Unsupported versions
        with self.assertRaises(IncompatibleSchemaVersionError):
            validate_schema_version("2.0")
        with self.assertRaises(IncompatibleSchemaVersionError):
            validate_schema_version("0.9")
        with self.assertRaises(IncompatibleSchemaVersionError):
            validate_schema_version("")

    def test_missing_required_fields_and_malformed_telemetry(self) -> None:
        # Missing required device_id
        with self.assertRaises(ValidationError):
            TopologyDevice.model_validate({"segment_id": "seg-1"})

        # Missing required link endpoints
        with self.assertRaises(ValidationError):
            TopologyLink.model_validate({"link_id": "L1", "source_device_id": "R1"})

        # Unknown optional / extra forbidden fields
        with self.assertRaises(ValidationError):
            TopologyDevice.model_validate({"device_id": "R1", "unexpected_extra_field": 42})

    def test_interoperability_validation_service(self) -> None:
        # Compatible performance payload
        valid_perf = {
            "diagnosis_id": "test-perf-1",
            "samples": [{"device_id": "R1", "latency_ms": 12.5, "packet_loss_pct": 0.0}],
        }
        res_compat = validate_interoperability(valid_perf, "performance")
        self.assertEqual(res_compat["status"], "compatible")
        self.assertEqual(len(res_compat["errors"]), 0)

        # Payload requiring normalization (aliases and units)
        alias_perf = {
            "diagnosis_id": "test-perf-2",
            "samples": [{"device_id": "R1", "latency": "250ms", "loss_percent": 3.5}],
        }
        res_norm = validate_interoperability(alias_perf, "performance")
        self.assertEqual(res_norm["status"], "compatible_with_normalization")
        self.assertIn("latency", res_norm["recognized_aliases"])
        self.assertIn("loss_percent", res_norm["recognized_aliases"])
        self.assertGreater(len(res_norm["unit_conversions"]), 0)
        self.assertIsNotNone(res_norm["normalized_payload"])

        # Incompatible payload: invalid unit
        bad_unit_perf = {
            "diagnosis_id": "test-perf-3",
            "samples": [{"device_id": "R1", "latency_ms": 100, "latency_unit": "kelvin"}],
        }
        res_bad_unit = validate_interoperability(bad_unit_perf, "performance")
        self.assertEqual(res_bad_unit["status"], "incompatible")
        self.assertTrue(any(e["error_type"] == "IncompatibleUnitError" for e in res_bad_unit["errors"]))

        # Incompatible payload: unsupported schema version
        bad_ver = {
            "schema_version": "9.9",
            "diagnosis_id": "test-perf-4",
            "samples": [{"device_id": "R1", "latency_ms": 10}],
        }
        res_bad_ver = validate_interoperability(bad_ver, "performance")
        self.assertEqual(res_bad_ver["status"], "incompatible")
        self.assertTrue(any(e["error_type"] == "IncompatibleSchemaVersionError" for e in res_bad_ver["errors"]))

        # Incompatible payload: missing required fields
        missing_dev = {
            "diagnosis_id": "test-conn-1",
            "devices": [{"reachability": "reachable"}],
        }
        res_missing = validate_interoperability(missing_dev, "connectivity")
        self.assertEqual(res_missing["status"], "incompatible")
        self.assertIn("device_id", res_missing["missing_required_fields"])

    def test_interoperability_validation_api_endpoint(self) -> None:
        # POST /api/interop/validate
        req_payload = {
            "domain": "connectivity",
            "payload": {
                "diagnosis_id": "diag-api-test",
                "nodes": [
                    {"id": "AP-01", "state": "UP"},
                    {"id": "SW-01", "state": "ONLINE"},
                ],
                "edges": [
                    {"id": "LINK-1", "src": "AP-01", "dst": "SW-01", "state": "ACTIVE", "type": "wifi"}
                ],
            },
        }
        status, data = asgi_request("POST", "/api/interop/validate", req_payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "compatible_with_normalization")
        self.assertEqual(data["domain"], "connectivity")
        self.assertIn("nodes", data["recognized_aliases"])
        self.assertIn("edges", data["recognized_aliases"])
        self.assertIsNotNone(data["normalized_payload"])
        self.assertEqual(len(data["normalized_payload"]["devices"]), 2)
        self.assertEqual(data["normalized_payload"]["devices"][0]["device_id"], "AP-01")
        self.assertEqual(data["normalized_payload"]["devices"][0]["reachability"], "reachable")
        self.assertEqual(data["normalized_payload"]["links"][0]["medium"], "wifi")

    def test_agent_evidence_traceability(self) -> None:
        # Genuine agent findings
        f1 = AgentFinding(
            metric="latency", value=250.0, unit="ms", severity="critical", assessment="High latency."
        )
        f2 = AgentFinding(
            metric="packet loss", value=5.0, unit="%", severity="critical", assessment="Packet loss."
        )
        msg_perf = AgentMessage(
            schema_version="1.0",
            diagnosis_id="diag-trace-1",
            agent="performance",
            status="complete",
            summary="Perf test",
            samples_analyzed=1,
            findings=[f1, f2],
        )
        messages = {"performance": msg_perf}

        # Valid reference
        valid_ref = EvidenceReference(
            agent="performance",
            finding_index=1,
            metric="packet loss",
            value=5.0,
            severity="critical",
            assessment="Packet loss.",
        )
        errs = validate_evidence_traceability(messages, [valid_ref])
        self.assertEqual(errs, [])

        # Invalid reference: unknown agent
        unknown_agent_ref = EvidenceReference(
            agent="infrastructure",
            finding_index=0,
            metric="CPU utilization",
            value=90,
            severity="critical",
            assessment="CPU.",
        )
        errs_agent = validate_evidence_traceability(messages, [unknown_agent_ref])
        self.assertTrue(any("not found in agent messages" in e for e in errs_agent))

        # Invalid reference: index out of bounds
        out_of_bounds_ref = EvidenceReference(
            agent="performance",
            finding_index=99,
            metric="latency",
            value=250.0,
            severity="critical",
            assessment="High latency.",
        )
        errs_oob = validate_evidence_traceability(messages, [out_of_bounds_ref])
        self.assertTrue(any("out of bounds" in e for e in errs_oob))

        # Invalid reference: metric mismatch
        metric_mismatch_ref = EvidenceReference(
            agent="performance",
            finding_index=0,
            metric="jitter",
            value=250.0,
            severity="critical",
            assessment="Mismatch.",
        )
        errs_metric = validate_evidence_traceability(messages, [metric_mismatch_ref])
        self.assertTrue(any("Metric mismatch" in e for e in errs_metric))


if __name__ == "__main__":
    unittest.main()

"""Interoperability, schema compatibility, and unit normalization service."""

from copy import deepcopy
import re
from typing import Any

SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0"})

CANONICAL_UNITS = {
    "latency_ms": "ms",
    "jitter_ms": "ms",
    "dns_lookup_time_ms": "ms",
    "packet_loss_pct": "%",
    "link_utilization_pct": "%",
    "cpu_utilization_pct": "%",
    "memory_utilization_pct": "%",
    "throughput_mbps": "Mbps",
    "rssi_dbm": "dBm",
    "interface_errors": "count",
    "egress_queue_drops": "count",
    "link_flaps": "count",
    "device_status": "status",
    "dhcp_status": "status",
}

PERFORMANCE_FIELD_ALIASES = {
    "latency": "latency_ms",
    "latency_ms": "latency_ms",
    "rtt": "latency_ms",
    "rtt_ms": "latency_ms",
    "ping": "latency_ms",
    "ping_ms": "latency_ms",
    "round_trip_time_ms": "latency_ms",
    "jitter": "jitter_ms",
    "jitter_ms": "jitter_ms",
    "delay_variation": "jitter_ms",
    "packet_loss": "packet_loss_pct",
    "packet_loss_pct": "packet_loss_pct",
    "loss_pct": "packet_loss_pct",
    "loss_percent": "packet_loss_pct",
    "drop_rate": "packet_loss_pct",
    "throughput": "throughput_mbps",
    "throughput_mbps": "throughput_mbps",
    "bandwidth": "throughput_mbps",
    "bandwidth_mbps": "throughput_mbps",
    "bitrate_mbps": "throughput_mbps",
    "link_utilization": "link_utilization_pct",
    "link_utilization_pct": "link_utilization_pct",
    "utilization_pct": "link_utilization_pct",
    "interface_utilization": "link_utilization_pct",
    "rssi": "rssi_dbm",
    "rssi_dbm": "rssi_dbm",
    "signal_strength": "rssi_dbm",
    "signal_dbm": "rssi_dbm",
    "wifi_rssi": "rssi_dbm",
    "dns_lookup_time_ms": "dns_lookup_time_ms",
    "dns_latency": "dns_lookup_time_ms",
    "dns_latency_ms": "dns_lookup_time_ms",
    "dns_time_ms": "dns_lookup_time_ms",
    "dns_lookup_ms": "dns_lookup_time_ms",
    "dns_response_time_ms": "dns_lookup_time_ms",
}

INFRASTRUCTURE_FIELD_ALIASES = {
    "cpu_utilization_pct": "cpu_utilization_pct",
    "cpu_utilization": "cpu_utilization_pct",
    "cpu_percent": "cpu_utilization_pct",
    "cpu_pct": "cpu_utilization_pct",
    "cpu_usage": "cpu_utilization_pct",
    "memory_utilization_pct": "memory_utilization_pct",
    "memory_utilization": "memory_utilization_pct",
    "memory_percent": "memory_utilization_pct",
    "memory_pct": "memory_utilization_pct",
    "memory_usage": "memory_utilization_pct",
    "mem_pct": "memory_utilization_pct",
    "interface_errors": "interface_errors",
    "crc_errors": "interface_errors",
    "rx_errors": "interface_errors",
    "packet_errors": "interface_errors",
    "fcs_errors": "interface_errors",
    "egress_queue_drops": "egress_queue_drops",
    "queue_drops": "egress_queue_drops",
    "egress_drops": "egress_queue_drops",
    "tx_drops": "egress_queue_drops",
    "device_status": "device_status",
    "status": "device_status",
    "state": "device_status",
    "dhcp_status": "dhcp_status",
    "dhcp_state": "dhcp_status",
    "ip_status": "dhcp_status",
    "link_flaps": "link_flaps",
    "flaps": "link_flaps",
}

CONNECTIVITY_DEVICE_FIELD_ALIASES = {
    "device_id": "device_id",
    "device": "device_id",
    "dev_id": "device_id",
    "id": "device_id",
    "node_id": "device_id",
    "node": "device_id",
    "hostname": "device_id",
    "host": "device_id",
    "name": "device_id",
    "segment_id": "segment_id",
    "segment": "segment_id",
    "seg_id": "segment_id",
    "network_segment": "segment_id",
    "vlan": "segment_id",
    "vlan_id": "segment_id",
    "subnet": "segment_id",
    "zone": "segment_id",
    "reachability": "reachability",
    "reachable": "reachability",
    "status": "reachability",
    "state": "reachability",
    "reachability_status": "reachability",
    "operational_status": "reachability",
    "ping_status": "reachability",
}

CONNECTIVITY_LINK_FIELD_ALIASES = {
    "link_id": "link_id",
    "link": "link_id",
    "id": "link_id",
    "name": "link_id",
    "edge_id": "link_id",
    "connection_id": "link_id",
    "source_device_id": "source_device_id",
    "source": "source_device_id",
    "src": "source_device_id",
    "src_device": "source_device_id",
    "source_device": "source_device_id",
    "from": "source_device_id",
    "from_device": "source_device_id",
    "endpoint_a": "source_device_id",
    "node_a": "source_device_id",
    "a_side": "source_device_id",
    "target_device_id": "target_device_id",
    "target": "target_device_id",
    "dst": "target_device_id",
    "dest": "target_device_id",
    "dst_device": "target_device_id",
    "dest_device": "target_device_id",
    "target_device": "target_device_id",
    "to": "target_device_id",
    "to_device": "target_device_id",
    "endpoint_b": "target_device_id",
    "node_b": "target_device_id",
    "b_side": "target_device_id",
    "status": "status",
    "state": "status",
    "link_status": "status",
    "link_state": "status",
    "operational_status": "status",
    "oper_status": "status",
    "medium": "medium",
    "medium_type": "medium",
    "type": "medium",
    "link_type": "medium",
    "connection_type": "medium",
    "technology": "medium",
    "interface_type": "medium",
}

CONNECTIVITY_TOPOLOGY_ALIASES = {
    "devices": "devices",
    "nodes": "devices",
    "device_list": "devices",
    "hosts": "devices",
    "links": "links",
    "edges": "links",
    "connections": "links",
    "link_list": "links",
}

REACHABILITY_VALUE_MAP = {
    "reachable": {"reachable", "up", "online", "active", "connected", "available", "yes", "true", "1", "ok"},
    "unreachable": {"unreachable", "down", "offline", "inactive", "disconnected", "unavailable", "no", "false", "0", "failed", "unreach"},
    "unknown": {"unknown", "none", "null", "undefined", "unmonitored", "unverified", "pending", "degraded", "flapping"},
}

LINK_STATUS_VALUE_MAP = {
    "up": {"up", "online", "active", "connected", "operational", "enabled", "1", "true", "ok"},
    "down": {"down", "offline", "inactive", "disconnected", "failed", "disabled", "0", "false", "fault"},
    "unknown": {"unknown", "degraded", "flapping", "null", "none", "undefined", "pending", "unverified", "unmonitored"},
}

LINK_MEDIUM_VALUE_MAP = {
    "ethernet": {"ethernet", "eth", "copper", "rj45", "lan", "cat5", "cat6", "wired", "fastethernet", "gigabitethernet"},
    "wifi": {"wifi", "wi-fi", "wireless", "wlan", "802.11", "rf"},
    "fiber": {"fiber", "fibre", "optical", "sfp", "sfp+", "qsfp", "fdxi"},
    "unknown": {"unknown", "other", "null", "none", "undefined", ""},
}


class InteroperabilityError(ValueError):
    """Base exception for all interoperability, schema, and normalization errors."""


class IncompatibleSchemaVersionError(InteroperabilityError):
    """Raised when an incoming schema version is incompatible with canonical version."""


class IncompatibleUnitError(InteroperabilityError):
    """Raised when an incompatible or invalid measurement unit is provided."""


class IncompatibleFieldError(InteroperabilityError):
    """Raised when an unresolvable or contradictory field name is supplied."""


class AmbiguousFieldMappingError(IncompatibleFieldError):
    """Raised when conflicting aliases with contradictory values map to the same canonical field."""


class MissingRequiredFieldError(InteroperabilityError):
    """Raised when a required telemetry field is missing from the payload."""


def validate_schema_version(version: str | None) -> str:
    """Validate that the schema version is supported by the multi-agent system."""
    if version is None:
        return "1.0"
    v = str(version).strip()
    if v not in SUPPORTED_SCHEMA_VERSIONS:
        supported = ", ".join(sorted(SUPPORTED_SCHEMA_VERSIONS))
        raise IncompatibleSchemaVersionError(
            f"Incompatible schema version '{version}'. Supported versions: [{supported}]."
        )
    return v


_TIME_UNIT_PATTERN = re.compile(r"^([+-]?\d+(?:\.\d+)?)\s*([a-zA-Zµμ%/]+)?$")


def normalize_metric_value_and_unit(
    canonical_field: str, raw_val: Any, explicit_unit: str | None = None
) -> float | int | str:
    """Validate and convert raw values with units into canonical units."""
    if raw_val is None:
        return None

    unit = explicit_unit.strip().lower() if explicit_unit else None
    val = raw_val

    if isinstance(raw_val, str):
        val_str = raw_val.strip()
        match = _TIME_UNIT_PATTERN.match(val_str)
        if match:
            numeric_part, unit_part = match.groups()
            try:
                val = float(numeric_part)
                if unit_part:
                    unit = unit_part.lower()
            except ValueError:
                pass

    # Latency / Jitter / DNS Lookup (canonical: ms)
    if canonical_field in ("latency_ms", "jitter_ms", "dns_lookup_time_ms"):
        if unit in (None, "ms", "millisecond", "milliseconds"):
            return float(val)
        if unit in ("s", "sec", "second", "seconds"):
            return float(val) * 1000.0
        if unit in ("us", "µs", "μs", "microsecond", "microseconds"):
            return float(val) / 1000.0
        raise IncompatibleUnitError(
            f"Incompatible unit '{unit}' for '{canonical_field}'; expected time unit ('ms', 's', 'us')."
        )

    # Throughput (canonical: Mbps)
    if canonical_field == "throughput_mbps":
        if unit in (None, "mbps", "mbit/s", "mb/s", "m"):
            return float(val)
        if unit in ("gbps", "gbit/s", "gb/s", "g"):
            return float(val) * 1000.0
        if unit in ("kbps", "kbit/s", "kb/s", "k"):
            return float(val) / 1000.0
        if unit in ("bps", "bit/s"):
            return float(val) / 1_000_000.0
        raise IncompatibleUnitError(
            f"Incompatible unit '{unit}' for '{canonical_field}'; expected rate unit ('Mbps', 'Gbps', 'Kbps', 'bps')."
        )

    # Percentage metrics (canonical: %)
    if canonical_field in (
        "packet_loss_pct",
        "link_utilization_pct",
        "cpu_utilization_pct",
        "memory_utilization_pct",
    ):
        if unit in (None, "%", "pct", "percent"):
            return float(val)
        if unit in ("ratio", "fraction"):
            return float(val) * 100.0
        raise IncompatibleUnitError(
            f"Incompatible unit '{unit}' for '{canonical_field}'; expected percentage ('%')."
        )

    # Wi-Fi RSSI (canonical: dBm)
    if canonical_field == "rssi_dbm":
        if unit in (None, "dbm"):
            return float(val)
        raise IncompatibleUnitError(
            f"Incompatible unit '{unit}' for '{canonical_field}'; expected signal unit ('dBm')."
        )

    # Integer counters
    if canonical_field in ("interface_errors", "egress_queue_drops", "link_flaps"):
        if unit in (None, "count", "packets", "drops", "errors", "flaps"):
            return int(val)
        raise IncompatibleUnitError(
            f"Incompatible unit '{unit}' for '{canonical_field}'; expected count."
        )

    return val


def normalize_sample_payload(
    sample_data: Any, domain: str
) -> dict[str, Any] | Any:
    """Normalize aliases, units, and structure for a performance or infrastructure sample dict."""
    if not isinstance(sample_data, dict):
        return sample_data

    aliases = (
        PERFORMANCE_FIELD_ALIASES
        if domain == "performance"
        else INFRASTRUCTURE_FIELD_ALIASES
    )
    normalized: dict[str, Any] = {}
    original_keys: dict[str, str] = {}
    explicit_units: dict[str, str] = {}

    if "units" in sample_data and isinstance(sample_data["units"], dict):
        for k, u in sample_data["units"].items():
            canonical_k = aliases.get(k.lower(), k)
            explicit_units[canonical_k] = str(u)

    for key, val in sample_data.items():
        if key == "units":
            continue
        lower_key = key.lower()

        if lower_key.endswith("_unit"):
            base_field = lower_key[:-5]
            canonical_base = aliases.get(base_field, base_field)
            explicit_units[canonical_base] = str(val)
            continue

        if lower_key in aliases:
            canonical_name = aliases[lower_key]
            if canonical_name in normalized and normalized[canonical_name] != val:
                raise AmbiguousFieldMappingError(
                    f"Conflicting field definitions for '{canonical_name}' "
                    f"(supplied both '{original_keys[canonical_name]}' and '{key}')."
                )
            normalized[canonical_name] = val
            original_keys[canonical_name] = key
        else:
            normalized[key] = val

    for canonical_name in list(normalized.keys()):
        if canonical_name in CANONICAL_UNITS:
            raw_val = normalized[canonical_name]
            unit = explicit_units.get(canonical_name)
            normalized[canonical_name] = normalize_metric_value_and_unit(
                canonical_name, raw_val, explicit_unit=unit
            )

    return normalized


def normalize_device_payload(device_data: Any) -> dict[str, Any] | Any:
    """Normalize device field aliases and reachability states."""
    if not isinstance(device_data, dict):
        return device_data

    normalized: dict[str, Any] = {}
    original_keys: dict[str, str] = {}

    for key, val in device_data.items():
        lower_key = key.lower()
        if lower_key in CONNECTIVITY_DEVICE_FIELD_ALIASES:
            canonical_name = CONNECTIVITY_DEVICE_FIELD_ALIASES[lower_key]
            if canonical_name in normalized and normalized[canonical_name] != val:
                raise AmbiguousFieldMappingError(
                    f"Conflicting field definitions for '{canonical_name}' "
                    f"(supplied both '{original_keys[canonical_name]}' and '{key}')."
                )
            normalized[canonical_name] = val
            original_keys[canonical_name] = key
        else:
            normalized[key] = val

    if "reachability" in normalized and normalized["reachability"] is not None:
        raw_reach = str(normalized["reachability"]).strip().lower()
        if raw_reach in REACHABILITY_VALUE_MAP["reachable"]:
            normalized["reachability"] = "reachable"
        elif raw_reach in REACHABILITY_VALUE_MAP["unreachable"]:
            normalized["reachability"] = "unreachable"
        elif raw_reach in REACHABILITY_VALUE_MAP["unknown"]:
            normalized["reachability"] = "unknown"

    return normalized


def normalize_link_payload(link_data: Any) -> dict[str, Any] | Any:
    """Normalize link field aliases, operational status, and medium types."""
    if not isinstance(link_data, dict):
        return link_data

    normalized: dict[str, Any] = {}
    original_keys: dict[str, str] = {}

    for key, val in link_data.items():
        lower_key = key.lower()
        if lower_key in CONNECTIVITY_LINK_FIELD_ALIASES:
            canonical_name = CONNECTIVITY_LINK_FIELD_ALIASES[lower_key]
            if canonical_name in normalized and normalized[canonical_name] != val:
                raise AmbiguousFieldMappingError(
                    f"Conflicting field definitions for '{canonical_name}' "
                    f"(supplied both '{original_keys[canonical_name]}' and '{key}')."
                )
            normalized[canonical_name] = val
            original_keys[canonical_name] = key
        else:
            normalized[key] = val

    if "status" in normalized and normalized["status"] is not None:
        raw_status = str(normalized["status"]).strip().lower()
        if raw_status in LINK_STATUS_VALUE_MAP["up"]:
            normalized["status"] = "up"
        elif raw_status in LINK_STATUS_VALUE_MAP["down"]:
            normalized["status"] = "down"
        elif raw_status in LINK_STATUS_VALUE_MAP["unknown"]:
            normalized["status"] = "unknown"

    if "medium" in normalized and normalized["medium"] is not None:
        raw_med = str(normalized["medium"]).strip().lower()
        if raw_med in LINK_MEDIUM_VALUE_MAP["ethernet"]:
            normalized["medium"] = "ethernet"
        elif raw_med in LINK_MEDIUM_VALUE_MAP["wifi"]:
            normalized["medium"] = "wifi"
        elif raw_med in LINK_MEDIUM_VALUE_MAP["fiber"]:
            normalized["medium"] = "fiber"
        elif raw_med in LINK_MEDIUM_VALUE_MAP["unknown"]:
            normalized["medium"] = "unknown"

    return normalized


def normalize_connectivity_payload(payload: Any) -> dict[str, Any] | Any:
    """Normalize top-level topology keys, devices, and links."""
    if not isinstance(payload, dict):
        return payload

    normalized: dict[str, Any] = {}
    for key, val in payload.items():
        lower_key = key.lower()
        canonical_name = CONNECTIVITY_TOPOLOGY_ALIASES.get(lower_key, key)
        normalized[canonical_name] = val

    if "devices" in normalized and isinstance(normalized["devices"], list):
        normalized["devices"] = [
            normalize_device_payload(d) for d in normalized["devices"]
        ]
    if "links" in normalized and isinstance(normalized["links"], list):
        normalized["links"] = [
            normalize_link_payload(l) for l in normalized["links"]
        ]

    return normalized


def validate_evidence_traceability(
    agent_messages: dict[str, Any],
    evidence_references: list[Any],
) -> list[str]:
    """Verify that every evidence reference faithfully traces to a real finding in the originating agent message."""
    errors = []
    for ref in evidence_references:
        agent_name = getattr(ref, "agent", None) or (
            ref.get("agent") if isinstance(ref, dict) else None
        )
        finding_idx = getattr(ref, "finding_index", None) if not isinstance(ref, dict) else ref.get("finding_index")
        metric = getattr(ref, "metric", None) or (
            ref.get("metric") if isinstance(ref, dict) else None
        )
        val = getattr(ref, "value", None) if not isinstance(ref, dict) else ref.get("value")

        if not agent_name or agent_name not in agent_messages:
            errors.append(f"Referenced agent '{agent_name}' not found in agent messages.")
            continue

        msg = agent_messages[agent_name]
        findings = getattr(msg, "findings", None) or (
            msg.get("findings") if isinstance(msg, dict) else []
        )
        if finding_idx is None or finding_idx < 0 or finding_idx >= len(findings):
            errors.append(
                f"Finding index {finding_idx} out of bounds for agent '{agent_name}' (available: 0..{len(findings) - 1})."
            )
            continue

        source_finding = findings[finding_idx]
        src_metric = getattr(source_finding, "metric", None) or (
            source_finding.get("metric") if isinstance(source_finding, dict) else None
        )
        src_val = getattr(source_finding, "value", None) if not isinstance(source_finding, dict) else source_finding.get("value")

        if src_metric != metric:
            errors.append(
                f"Metric mismatch in reference {agent_name}[{finding_idx}]: expected '{src_metric}', got '{metric}'."
            )
        if str(src_val) != str(val):
            errors.append(
                f"Value mismatch in reference {agent_name}[{finding_idx}]: expected '{src_val}', got '{val}'."
            )
    return errors


def validate_interoperability(
    payload: dict[str, Any],
    domain: str,
    schema_version: str | None = None,
) -> dict[str, Any]:
    """Validate schema compliance, extract recognized aliases, report unit conversions, and return structured status."""
    from pydantic import ValidationError

    from backend.models.connectivity import ConnectivityTelemetry
    from backend.models.diagnosis import DiagnosisRequest
    from backend.models.infrastructure import InfrastructureTelemetryBatch
    from backend.models.telemetry import TelemetryBatch

    errors: list[dict[str, Any]] = []
    missing_fields: list[str] = []
    recognized_aliases: list[str] = []
    field_mappings: list[dict[str, Any]] = []
    unit_conversions: list[dict[str, Any]] = []

    # 1. Schema version check
    target_version = schema_version or payload.get("schema_version")
    try:
        valid_version = validate_schema_version(target_version)
    except IncompatibleSchemaVersionError as err:
        return {
            "status": "incompatible",
            "schema_version": str(target_version or "unknown"),
            "domain": domain,
            "recognized_aliases": [],
            "field_mappings": [],
            "unit_conversions": [],
            "missing_required_fields": [],
            "errors": [
                {
                    "error_type": "IncompatibleSchemaVersionError",
                    "field": "schema_version",
                    "message": str(err),
                }
            ],
            "normalized_payload": None,
        }

    # 2. Inspect aliases and conversions per domain
    def inspect_sample(sample: dict[str, Any], alias_map: dict[str, str]) -> None:
        for k, v in sample.items():
            lk = k.lower()
            if lk in alias_map and lk != alias_map[lk]:
                canonical_k = alias_map[lk]
                if k not in recognized_aliases:
                    recognized_aliases.append(k)
                field_mappings.append(
                    {
                        "original_field": k,
                        "canonical_field": canonical_k,
                        "original_value": v,
                        "normalized_value": v,
                    }
                )
            if isinstance(v, str) and lk in alias_map:
                canonical_k = alias_map[lk]
                match = _TIME_UNIT_PATTERN.match(v.strip())
                if match and match.group(2):
                    canonical_u = CANONICAL_UNITS.get(canonical_k, "standard")
                    try:
                        conv = normalize_metric_value_and_unit(canonical_k, v)
                        unit_conversions.append(
                            {
                                "field": canonical_k,
                                "original_value": v,
                                "original_unit": match.group(2),
                                "canonical_value": conv,
                                "canonical_unit": canonical_u,
                            }
                        )
                    except Exception:
                        pass

    norm_payload = deepcopy(payload)

    try:
        if domain == "performance":
            samples = norm_payload.get("samples", [])
            if isinstance(samples, list):
                for s in samples:
                    if isinstance(s, dict):
                        inspect_sample(s, PERFORMANCE_FIELD_ALIASES)
            norm_payload["samples"] = [
                normalize_sample_payload(s, "performance") for s in samples
            ]
            norm_payload = TelemetryBatch.model_validate(norm_payload).model_dump()

        elif domain == "infrastructure":
            samples = norm_payload.get("samples", [])
            if isinstance(samples, list):
                for s in samples:
                    if isinstance(s, dict):
                        inspect_sample(s, INFRASTRUCTURE_FIELD_ALIASES)
            norm_payload["samples"] = [
                normalize_sample_payload(s, "infrastructure") for s in samples
            ]
            norm_payload = InfrastructureTelemetryBatch.model_validate(norm_payload).model_dump()

        elif domain == "connectivity":
            for top_k, top_v in list(norm_payload.items()):
                if top_k.lower() in CONNECTIVITY_TOPOLOGY_ALIASES:
                    can_k = CONNECTIVITY_TOPOLOGY_ALIASES[top_k.lower()]
                    if top_k.lower() != can_k:
                        if top_k not in recognized_aliases:
                            recognized_aliases.append(top_k)
                        field_mappings.append(
                            {
                                "original_field": top_k,
                                "canonical_field": can_k,
                                "original_value": top_v,
                                "normalized_value": top_v,
                            }
                        )
            devices = norm_payload.get("devices") or norm_payload.get("nodes") or []
            if isinstance(devices, list):
                for d in devices:
                    if isinstance(d, dict):
                        inspect_sample(d, CONNECTIVITY_DEVICE_FIELD_ALIASES)
            links = norm_payload.get("links") or norm_payload.get("edges") or []
            if isinstance(links, list):
                for l in links:
                    if isinstance(l, dict):
                        inspect_sample(l, CONNECTIVITY_LINK_FIELD_ALIASES)
            norm_payload = normalize_connectivity_payload(norm_payload)
            norm_payload = ConnectivityTelemetry.model_validate(norm_payload).model_dump()

        elif domain == "diagnosis":
            perf = norm_payload.get("performance")
            if isinstance(perf, dict):
                for s in perf.get("samples", []):
                    if isinstance(s, dict):
                        inspect_sample(s, PERFORMANCE_FIELD_ALIASES)
            infra = norm_payload.get("infrastructure")
            if isinstance(infra, dict):
                for s in infra.get("samples", []):
                    if isinstance(s, dict):
                        inspect_sample(s, INFRASTRUCTURE_FIELD_ALIASES)
            conn = norm_payload.get("connectivity")
            if isinstance(conn, dict):
                for top_k, top_v in list(conn.items()):
                    if top_k.lower() in CONNECTIVITY_TOPOLOGY_ALIASES:
                        can_k = CONNECTIVITY_TOPOLOGY_ALIASES[top_k.lower()]
                        if top_k.lower() != can_k:
                            if top_k not in recognized_aliases:
                                recognized_aliases.append(top_k)
                            field_mappings.append(
                                {
                                    "original_field": top_k,
                                    "canonical_field": can_k,
                                    "original_value": top_v,
                                    "normalized_value": top_v,
                                }
                            )
                for d in conn.get("devices") or conn.get("nodes") or []:
                    if isinstance(d, dict):
                        inspect_sample(d, CONNECTIVITY_DEVICE_FIELD_ALIASES)
                for l in conn.get("links") or conn.get("edges") or []:
                    if isinstance(l, dict):
                        inspect_sample(l, CONNECTIVITY_LINK_FIELD_ALIASES)
            validated_diag = DiagnosisRequest.model_validate(norm_payload)
            norm_payload = validated_diag.model_dump()

        else:
            errors.append(
                {
                    "error_type": "InvalidDomainError",
                    "field": "domain",
                    "message": f"Unsupported telemetry domain '{domain}'.",
                }
            )

    except ValidationError as val_err:
        for err in val_err.errors():
            loc = ".".join(str(item) for item in err["loc"]) if err["loc"] else None
            err_type = err["type"]
            ctx_err = err.get("ctx", {}).get("error")
            err_cls = type(ctx_err).__name__ if ctx_err else ("MissingRequiredFieldError" if err_type == "missing" else "ValidationError")
            msg = err["msg"]
            if err_type == "missing":
                missing_field_name = str(err["loc"][-1])
                if missing_field_name not in missing_fields:
                    missing_fields.append(missing_field_name)
            errors.append(
                {
                    "error_type": err_cls,
                    "field": loc,
                    "message": msg,
                }
            )
    except InteroperabilityError as interop_err:
        errors.append(
            {
                "error_type": type(interop_err).__name__,
                "field": None,
                "message": str(interop_err),
            }
        )
    except Exception as exc:
        errors.append(
            {
                "error_type": type(exc).__name__,
                "field": None,
                "message": str(exc),
            }
        )

    if errors:
        status = "incompatible"
        result_payload = None
    elif recognized_aliases or unit_conversions:
        status = "compatible_with_normalization"
        result_payload = norm_payload
    else:
        status = "compatible"
        result_payload = norm_payload

    return {
        "status": status,
        "schema_version": valid_version,
        "domain": domain,
        "recognized_aliases": recognized_aliases,
        "field_mappings": field_mappings,
        "unit_conversions": unit_conversions,
        "missing_required_fields": missing_fields,
        "errors": errors,
        "normalized_payload": result_payload,
    }

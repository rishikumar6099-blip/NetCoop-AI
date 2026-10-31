"""Interoperability, schema compatibility, and unit normalization service."""

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


class InteroperabilityError(ValueError):
    """Base exception for all interoperability, schema, and normalization errors."""


class IncompatibleSchemaVersionError(InteroperabilityError):
    """Raised when an incoming schema version is incompatible with canonical version."""


class IncompatibleUnitError(InteroperabilityError):
    """Raised when an incompatible or invalid measurement unit is provided."""


class IncompatibleFieldError(InteroperabilityError):
    """Raised when an unresolvable or contradictory field name is supplied."""


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

    # Handle string with embedded unit, e.g. "250ms", "0.25s", "100Mbps", "95%", "-84 dBm"
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
    """Normalize aliases, units, and structure for a telemetry sample dict."""
    if not isinstance(sample_data, dict):
        return sample_data

    aliases = (
        PERFORMANCE_FIELD_ALIASES
        if domain == "performance"
        else INFRASTRUCTURE_FIELD_ALIASES
    )
    normalized: dict[str, Any] = {}
    explicit_units: dict[str, str] = {}

    # Extract any explicit units passed like latency_unit="s" or units={"latency": "s"}
    if "units" in sample_data and isinstance(sample_data["units"], dict):
        for k, u in sample_data["units"].items():
            canonical_k = aliases.get(k.lower(), k)
            explicit_units[canonical_k] = str(u)

    for key, val in sample_data.items():
        if key == "units":
            continue
        lower_key = key.lower()

        # Check for field_unit pattern, e.g. latency_unit
        if lower_key.endswith("_unit"):
            base_field = lower_key[:-5]
            canonical_base = aliases.get(base_field, base_field)
            explicit_units[canonical_base] = str(val)
            continue

        if lower_key in aliases:
            canonical_name = aliases[lower_key]
            if canonical_name in normalized and normalized[canonical_name] != val:
                raise IncompatibleFieldError(
                    f"Conflicting field definitions for '{canonical_name}' (supplied both '{key}' and '{canonical_name}')."
                )
            normalized[canonical_name] = val
        else:
            normalized[key] = val

    # Now apply unit normalizations
    for canonical_name in list(normalized.keys()):
        if canonical_name in CANONICAL_UNITS:
            raw_val = normalized[canonical_name]
            unit = explicit_units.get(canonical_name)
            normalized[canonical_name] = normalize_metric_value_and_unit(
                canonical_name, raw_val, explicit_unit=unit
            )

    return normalized

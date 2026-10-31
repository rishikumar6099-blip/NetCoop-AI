"""Evidence-based analysis of network connectivity and topology."""

from typing import Any

from backend.models.agent_message import AgentFinding, AgentMessage
from backend.models.connectivity import ConnectivityTelemetry, TopologyDevice, TopologyLink


class ConnectivityAnalysisAgent:
    """Identify reported connectivity failures without inventing topology."""

    agent_name = "connectivity"

    def analyze(
        self, telemetry: ConnectivityTelemetry | dict[str, Any]
    ) -> AgentMessage:
        """Validate a topology payload and return structured connectivity findings."""
        topology = (
            telemetry
            if isinstance(telemetry, ConnectivityTelemetry)
            else ConnectivityTelemetry.model_validate(telemetry)
        )
        devices = {device.device_id: device for device in topology.devices}
        findings: list[AgentFinding] = []
        affected_device_ids: set[str] = set()
        affected_link_ids: set[str] = set()
        evidence_by_device: dict[str, list[str]] = {}

        for device in topology.devices:
            if device.reachability == "unreachable":
                affected_device_ids.add(device.device_id)
                evidence = [f"Device {device.device_id} is reported unreachable."]
                evidence_by_device.setdefault(device.device_id, []).extend(evidence)
                findings.append(
                    AgentFinding(
                        metric="Device reachability",
                        value="unreachable",
                        unit="state",
                        severity="critical",
                        device_id=device.device_id,
                        assessment="Device is explicitly reported as unreachable.",
                        evidence=evidence,
                        affected_device_ids=[device.device_id],
                    )
                )

        for link in topology.links:
            known_endpoints = list(
                dict.fromkeys(
                    endpoint
                    for endpoint in (link.source_device_id, link.target_device_id)
                    if endpoint in devices
                )
            )
            unknown_endpoints = [
                endpoint
                for endpoint in (link.source_device_id, link.target_device_id)
                if endpoint not in devices
            ]

            if unknown_endpoints:
                findings.append(
                    AgentFinding(
                        metric="Topology consistency",
                        value="missing link endpoint",
                        unit="topology",
                        severity="warning",
                        assessment=(
                            f"Link {link.link_id} references endpoint(s) absent from "
                            "the supplied device list; no missing device is inferred."
                        ),
                        evidence=[
                            f"Link {link.link_id} references unknown endpoint "
                            f"{endpoint}."
                            for endpoint in unknown_endpoints
                        ],
                        affected_link_ids=[link.link_id],
                    )
                )

            if link.source_device_id == link.target_device_id:
                findings.append(
                    AgentFinding(
                        metric="Topology consistency",
                        value="self-referencing link",
                        unit="topology",
                        severity="warning",
                        assessment=(
                            f"Link {link.link_id} names the same source and target; "
                            "its impact scope cannot be established from this record."
                        ),
                        evidence=[
                            f"Link {link.link_id} has identical source and target "
                            f"{link.source_device_id}."
                        ],
                        affected_link_ids=[link.link_id],
                    )
                )

            if link.status != "down":
                continue

            affected_link_ids.add(link.link_id)
            affected_device_ids.update(known_endpoints)
            link_evidence = [
                f"Link {link.link_id} from {link.source_device_id} to "
                f"{link.target_device_id} is reported down."
            ]
            for endpoint in known_endpoints:
                evidence_by_device.setdefault(endpoint, []).extend(link_evidence)
            findings.append(
                AgentFinding(
                    metric="Network link state",
                    value="down",
                    unit="state",
                    severity="critical",
                    assessment=f"Link {link.link_id} is explicitly reported down.",
                    evidence=link_evidence,
                    affected_device_ids=known_endpoints,
                    affected_link_ids=[link.link_id],
                )
            )

            unreachable_endpoints = [
                endpoint
                for endpoint in known_endpoints
                if devices[endpoint].reachability == "unreachable"
            ]
            if unreachable_endpoints:
                findings.append(
                    AgentFinding(
                        metric="Connectivity pattern",
                        value="down link adjacent to unreachable device",
                        unit="pattern",
                        severity="critical",
                        assessment=(
                            "A reported down link is incident to a device also "
                            "reported unreachable."
                        ),
                        evidence=link_evidence
                        + [
                            f"Device {endpoint} is reported unreachable."
                            for endpoint in unreachable_endpoints
                        ],
                        affected_device_ids=known_endpoints,
                        affected_link_ids=[link.link_id],
                    )
                )

        unknown_device_states = [
            device
            for device in topology.devices
            if device.reachability in (None, "unknown")
        ]
        unknown_link_states = [
            link for link in topology.links if link.status == "unknown"
        ]
        if unknown_device_states or unknown_link_states:
            findings.append(
                AgentFinding(
                    metric="Topology completeness",
                    value="missing connectivity state",
                    unit="topology",
                    severity="warning",
                    assessment=(
                        "Some device or link states are missing or unknown; "
                        "incident scope may be incomplete."
                    ),
                    evidence=(
                        [
                            f"Device {device.device_id} has no confirmed reachability state."
                            for device in unknown_device_states
                        ]
                        + [
                            f"Link {link.link_id} has no confirmed up/down state."
                            for link in unknown_link_states
                        ]
                    ),
                )
            )

        device_segments = {
            device_id: devices[device_id].segment_id
            for device_id in affected_device_ids
            if devices[device_id].segment_id is not None
        }
        devices_by_segment: dict[str, list[str]] = {}
        for device_id, segment_id in device_segments.items():
            devices_by_segment.setdefault(segment_id, []).append(device_id)

        affected_segment_ids = sorted(devices_by_segment)
        for segment_id, segment_devices in sorted(devices_by_segment.items()):
            if len(segment_devices) < 2:
                continue
            evidence = [
                detail
                for device_id in segment_devices
                for detail in evidence_by_device.get(device_id, [])
            ]
            segment_links = sorted(
                link.link_id
                for link in topology.links
                if link.status == "down"
                and link.source_device_id in segment_devices
                and link.target_device_id in segment_devices
            )
            findings.append(
                AgentFinding(
                    metric="Affected network segment",
                    value=segment_id,
                    unit="segment",
                    severity="critical",
                    assessment=(
                        f"Multiple affected devices are explicitly assigned to "
                        f"segment {segment_id}."
                    ),
                    evidence=evidence,
                    affected_device_ids=sorted(segment_devices),
                    affected_link_ids=segment_links,
                    affected_segment_ids=[segment_id],
                )
            )
            unreachable_devices = [
                device_id
                for device_id in segment_devices
                if devices[device_id].reachability == "unreachable"
            ]
            if len(unreachable_devices) >= 2:
                findings.append(
                    AgentFinding(
                        metric="Connectivity pattern",
                        value="multiple unreachable devices in one segment",
                        unit="pattern",
                        severity="critical",
                        assessment=(
                            f"Multiple unreachable devices share segment {segment_id}; "
                            "the common segment is a plausible incident scope."
                        ),
                        evidence=[
                            f"Device {device_id} is reported unreachable in "
                            f"segment {segment_id}."
                            for device_id in unreachable_devices
                        ],
                        affected_device_ids=sorted(unreachable_devices),
                        affected_segment_ids=[segment_id],
                    )
                )

        incomplete = self._has_incomplete_topology(topology, devices)
        scope, scope_assessment = self._determine_scope(
            affected_device_ids,
            device_segments,
            incomplete,
            bool(affected_link_ids),
        )
        if scope == "wider network":
            scope_evidence = [
                f"Confirmed affected devices span segments: {', '.join(affected_segment_ids)}."
            ]
        elif scope == "network segment":
            scope_evidence = [
                f"At least two affected devices are mapped to segment {affected_segment_ids[0]}."
            ]
        elif scope == "individual device":
            only_device = next(iter(affected_device_ids))
            scope_evidence = evidence_by_device.get(only_device, [])
        elif scope == "no confirmed impact":
            scope_evidence = [
                "All supplied device and link states are reachable/up; no connectivity "
                "failure is confirmed."
            ]
        else:
            scope_evidence = [
                "The supplied topology does not provide enough consistent state to "
                "establish incident scope."
            ]
        findings.append(
            AgentFinding(
                metric="Incident scope",
                value=scope,
                unit="scope",
                severity="critical" if affected_device_ids or affected_link_ids else "info",
                assessment=scope_assessment,
                evidence=scope_evidence,
                affected_device_ids=sorted(affected_device_ids),
                affected_link_ids=sorted(affected_link_ids),
                affected_segment_ids=(
                    affected_segment_ids
                    if scope in ("network segment", "wider network")
                    else []
                ),
            )
        )

        return AgentMessage(
            diagnosis_id=topology.diagnosis_id,
            agent=self.agent_name,
            summary=(
                f"Analyzed {len(topology.devices)} device(s) and "
                f"{len(topology.links)} link(s); found "
                f"{len(affected_device_ids)} affected device(s), "
                f"{len(affected_link_ids)} broken link(s); scope: {scope}."
            ),
            samples_analyzed=len(topology.devices) + len(topology.links),
            findings=findings,
        )

    @staticmethod
    def _has_incomplete_topology(
        topology: ConnectivityTelemetry, devices: dict[str, TopologyDevice]
    ) -> bool:
        if any(device.reachability in (None, "unknown") for device in topology.devices):
            return True
        for link in topology.links:
            if link.status == "unknown":
                return True
            if (
                link.source_device_id not in devices
                or link.target_device_id not in devices
                or link.source_device_id == link.target_device_id
            ):
                return True
        return False

    @staticmethod
    def _determine_scope(
        affected_device_ids: set[str],
        device_segments: dict[str, str],
        incomplete: bool,
        has_broken_link: bool,
    ) -> tuple[str, str]:
        affected_segments = set(device_segments.values())
        if len(affected_segments) > 1:
            return (
                "wider network",
                "Connectivity failures are evidenced across multiple network segments.",
            )

        if (
            len(affected_segments) == 1
            and len(affected_device_ids) >= 2
            and len(device_segments) == len(affected_device_ids)
        ):
            return (
                "network segment",
                "Multiple affected devices are evidenced within one network segment.",
            )

        if len(affected_device_ids) == 1 and not incomplete:
            return (
                "individual device",
                "The confirmed connectivity impact is limited to one observed device.",
            )

        if not affected_device_ids and not has_broken_link and not incomplete:
            return (
                "no confirmed impact",
                "No connectivity failure is present in the complete supplied topology.",
            )

        return (
            "undetermined",
            "Incomplete or inconsistent topology prevents a reliable scope determination.",
        )

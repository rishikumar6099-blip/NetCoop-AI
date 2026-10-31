"""Deterministic correlation of performance, infrastructure, and connectivity findings."""

from datetime import timezone
from typing import Any

from backend.models.agent_message import AgentFinding, AgentMessage
from backend.models.correlation import (
    CorrelationInput,
    CorrelationResult,
    EvidenceConflict,
    EvidenceReference,
    RootCauseHypothesis,
)


_PERFORMANCE_METRICS = {
    "latency",
    "jitter",
    "packet loss",
    "wifi signal strength",
    "dns lookup time",
}
_RESOURCE_METRICS = {"cpu utilization", "memory utilization"}
_DROP_METRICS = {"interface errors", "egress queue drops"}
_CONNECTIVITY_METRICS = {
    "device reachability",
    "network link state",
    "connectivity pattern",
    "affected network segment",
}
_MAX_OBSERVATION_SKEW_SECONDS = 300


class FaultCorrelationAgent:
    """Rank evidence-supported root-cause hypotheses across three agent messages."""

    agent_name = "fault_correlation"

    def analyze(
        self, messages: CorrelationInput | dict[str, Any]
    ) -> CorrelationResult:
        """Validate agent messages, find corroborated patterns, and rank candidates."""
        correlation_input = (
            messages
            if isinstance(messages, CorrelationInput)
            else CorrelationInput.model_validate(messages)
        )
        indexed = {
            "performance": correlation_input.performance,
            "infrastructure": correlation_input.infrastructure,
            "connectivity": correlation_input.connectivity,
        }
        conflicts = self._find_conflicts(indexed)
        candidates: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}

        performance = self._abnormal_findings(indexed["performance"])
        infrastructure = self._abnormal_findings(indexed["infrastructure"])
        connectivity = self._abnormal_findings(indexed["connectivity"])

        for perf_ref, perf_finding in performance:
            perf_metric = self._normalize(perf_finding.metric)
            if perf_metric not in _PERFORMANCE_METRICS:
                continue
            perf_devices = self._device_ids(perf_finding)
            if not perf_devices:
                continue

            for infra_ref, infra_finding in infrastructure:
                infra_metric = self._normalize(infra_finding.metric)
                shared_devices = perf_devices & self._device_ids(infra_finding)
                if not shared_devices:
                    continue

                if perf_metric in _PERFORMANCE_METRICS and infra_metric in _RESOURCE_METRICS:
                    refs = [perf_ref, infra_ref]
                    extra_connectivity = self._corroborating_connectivity(
                        connectivity, shared_devices
                    )
                    refs.extend(reference for reference, _ in extra_connectivity)
                    self._add_candidate(
                        candidates,
                        cause="device_resource_exhaustion",
                        explanation=(
                            "High device CPU or memory utilization coincides with "
                            "performance degradation on the same device and may be "
                            "contributing to it."
                        ),
                        references=refs,
                        devices=shared_devices,
                        semantic_match=True,
                    )

                if perf_metric == "packet loss" and infra_metric in _DROP_METRICS:
                    if self._interfaces_conflict(perf_finding, infra_finding):
                        continue
                    if infra_metric == "interface errors":
                        has_queue_drops = any(
                            self._normalize(f.metric) == "egress queue drops"
                            and f.severity in {"warning", "critical"}
                            and (perf_devices & self._device_ids(f))
                            for _, f in infrastructure
                        )
                        if not has_queue_drops:
                            self._add_candidate(
                                candidates,
                                cause="ethernet_interface_fault",
                                explanation=(
                                    "Reported interface errors (CRC or framing errors) coincide "
                                    "with packet loss on the same interface while queue drops remain low, "
                                    "indicating a physical Ethernet, transceiver, or duplex fault."
                                ),
                                references=[perf_ref, infra_ref],
                                devices=shared_devices,
                                semantic_match=True,
                            )
                        else:
                            self._add_candidate(
                                candidates,
                                cause="interface_or_queue_drops",
                                explanation=(
                                    "Reported interface errors or egress queue drops coincide "
                                    "with packet loss on the same device and may be contributing."
                                ),
                                references=[perf_ref, infra_ref],
                                devices=shared_devices,
                                semantic_match=True,
                            )
                    else:
                        self._add_candidate(
                            candidates,
                            cause="interface_or_queue_drops",
                            explanation=(
                                "Reported interface errors or egress queue drops coincide "
                                "with packet loss on the same device and may be contributing."
                            ),
                            references=[perf_ref, infra_ref],
                            devices=shared_devices,
                            semantic_match=True,
                        )

            if perf_metric in _PERFORMANCE_METRICS:
                for conn_ref, conn_finding in connectivity:
                    if self._normalize(conn_finding.metric) not in _CONNECTIVITY_METRICS:
                        continue
                    shared_devices = perf_devices & self._device_ids(conn_finding)
                    if not shared_devices:
                        continue
                    connectivity_evidence = [conn_ref]
                    connectivity_evidence.extend(
                        self._scope_references(indexed["connectivity"], shared_devices)
                    )
                    self._add_candidate(
                        candidates,
                        cause="connectivity_path_failure",
                        explanation=(
                            "A reported reachability or link problem overlaps with "
                            "performance degradation on the same device."
                        ),
                        references=[perf_ref, *connectivity_evidence],
                        devices=shared_devices,
                        semantic_match=True,
                    )

        # Correlate weak Wi-Fi signal
        for perf_ref, perf_finding in performance:
            perf_metric = self._normalize(perf_finding.metric)
            if perf_metric == "wifi signal strength":
                perf_devices = self._device_ids(perf_finding)
                other_perf = [
                    ref for ref, f in performance
                    if ref != perf_ref
                    and (perf_devices & self._device_ids(f))
                    and self._normalize(f.metric) in {"packet loss", "latency", "jitter"}
                ]
                if other_perf:
                    refs = [perf_ref, other_perf[0]]
                    for infra_ref, infra_finding in infrastructure:
                        if perf_devices & self._device_ids(infra_finding):
                            refs.append(infra_ref)
                            break
                    extra_conn = self._corroborating_connectivity(connectivity, perf_devices)
                    refs.extend(r for r, _ in extra_conn)
                    self._add_candidate(
                        candidates,
                        cause="weak_wifi_signal",
                        explanation=(
                            "Weak Wi-Fi signal strength (low RSSI) coincides with performance "
                            "degradation on the wireless device/interface, indicating RF attenuation or coverage issues."
                        ),
                        references=refs,
                        devices=perf_devices,
                        semantic_match=True,
                    )

        # Correlate DNS / DHCP failure
        for perf_ref, perf_finding in performance:
            perf_metric = self._normalize(perf_finding.metric)
            if perf_metric == "dns lookup time":
                perf_devices = self._device_ids(perf_finding)
                corroborating = []
                for infra_ref, infra_finding in infrastructure:
                    if self._normalize(infra_finding.metric) == "dhcp status" and (perf_devices & self._device_ids(infra_finding)):
                        corroborating.append(infra_ref)
                if not corroborating:
                    for conn_ref, conn_finding in connectivity:
                        if perf_devices & self._device_ids(conn_finding):
                            corroborating.append(conn_ref)
                            break
                if not corroborating:
                    for other_ref, other_f in performance:
                        if other_ref != perf_ref and (perf_devices & self._device_ids(other_f)):
                            corroborating.append(other_ref)
                            break
                if corroborating:
                    self._add_candidate(
                        candidates,
                        cause="dns_dhcp_failure",
                        explanation=(
                            "Core network service degradation (DNS lookup timeout or latency) "
                            "occurs while underlying network reachability is operational, indicating a service-layer failure."
                        ),
                        references=[perf_ref, corroborating[0]],
                        devices=perf_devices,
                        semantic_match=True,
                    )

        for infra_ref, infra_finding in infrastructure:
            if self._normalize(infra_finding.metric) == "dhcp status" and str(infra_finding.value).lower() in {"failed", "timeout"}:
                infra_devices = self._device_ids(infra_finding)
                corroborating = []
                for perf_ref, perf_finding in performance:
                    if infra_devices & self._device_ids(perf_finding):
                        corroborating.append(perf_ref)
                        break
                if not corroborating:
                    for conn_ref, conn_finding in connectivity:
                        if infra_devices & self._device_ids(conn_finding):
                            corroborating.append(conn_ref)
                            break
                if corroborating:
                    self._add_candidate(
                        candidates,
                        cause="dns_dhcp_failure",
                        explanation=(
                            "DHCP client reported lease timeout or failure while "
                            "network connectivity remains operational, indicating a DHCP service disruption."
                        ),
                        references=[infra_ref, corroborating[0]],
                        devices=infra_devices,
                        semantic_match=True,
                    )

        # Correlate interoperability failure
        for infra_ref, infra_finding in infrastructure:
            if self._normalize(infra_finding.metric) == "interoperability compatibility" and str(infra_finding.value).lower() == "incompatible":
                infra_devices = self._device_ids(infra_finding)
                corroborating = []
                for other_ref, other_finding in performance + connectivity:
                    if infra_devices & self._device_ids(other_finding):
                        corroborating.append(other_ref)
                        break
                if not corroborating and len(infrastructure) > 1:
                    for other_ref, _ in infrastructure:
                        if other_ref != infra_ref:
                            corroborating.append(other_ref)
                            break
                if corroborating:
                    self._add_candidate(
                        candidates,
                        cause="interoperability_failure",
                        explanation=(
                            "An interoperability failure was detected due to incompatible schema version, "
                            "unrecognized message format, or incompatible unit between collaborating network components."
                        ),
                        references=[infra_ref, corroborating[0]],
                        devices=infra_devices,
                        semantic_match=True,
                    )

        for infra_ref, infra_finding in infrastructure:
            if (
                self._normalize(infra_finding.metric) != "device status"
                or str(infra_finding.value).lower() not in {"offline", "degraded"}
            ):
                continue
            infra_devices = self._device_ids(infra_finding)
            for conn_ref, conn_finding in connectivity:
                if (
                    self._normalize(conn_finding.metric) != "device reachability"
                    or str(conn_finding.value).lower() != "unreachable"
                ):
                    continue
                shared_devices = infra_devices & self._device_ids(conn_finding)
                if shared_devices:
                    self._add_candidate(
                        candidates,
                        cause="device_unavailable",
                        explanation=(
                            "Infrastructure health reports a device offline or degraded, "
                            "and Connectivity reports the same device unreachable."
                        ),
                        references=[infra_ref, conn_ref],
                        devices=shared_devices,
                        semantic_match=True,
                    )

        hypotheses = self._rank_candidates(candidates, conflicts)
        alternative_summaries = [
            f"Rank {hypothesis.rank}: {hypothesis.explanation}"
            for hypothesis in hypotheses[1:]
        ]
        if hypotheses and not alternative_summaries:
            alternative_summaries = [
                "No other evidence-supported cause was identified; other causes "
                "remain unassessed."
            ]
        hypotheses = [
            hypothesis.model_copy(
                update={"alternative_explanations": alternative_summaries}
            )
            for hypothesis in hypotheses
        ]
        insufficient_evidence = not hypotheses or hypotheses[0].confidence < 0.6
        if insufficient_evidence:
            if hypotheses:
                summary = (
                    "Insufficient evidence for a reliable diagnosis; tentative "
                    "hypotheses are included for review."
                )
            else:
                summary = (
                    "Insufficient evidence: no cross-agent root-cause pattern met the "
                    "correlation rules."
                )
            limitations = [
                "No matching abnormal findings with a shared affected device were available.",
                "Only warning or critical findings are considered for root-cause hypotheses.",
            ]
            if hypotheses:
                limitations[0] = (
                    "The leading hypothesis did not meet the prototype confidence "
                    "threshold for a reliable diagnosis."
                )
        else:
            summary = (
                f"Ranked {len(hypotheses)} evidence-supported root-cause hypothesis(s); "
                f"top candidate: {hypotheses[0].cause}."
            )
            limitations = [
                "Correlated observations indicate association, not proven causation.",
                "The input messages do not establish event timing or causal order.",
            ]

        if conflicts:
            limitations.append(
                "Conflicting source findings are listed and should be resolved before "
                "acting on affected hypotheses."
            )

        no_fault_detected = self._complete_healthy_input(
            correlation_input, indexed, conflicts
        )
        if no_fault_detected:
            status = "no_fault_detected"
            summary = (
                "No fault detected: the supplied performance, infrastructure, and "
                "connectivity telemetry is complete and contains no warning or "
                "critical findings."
            )
            limitations = [
                "No faults were detected in the supplied telemetry; unmeasured conditions "
                "and faults outside this observation window remain unassessed."
            ]
        else:
            status = "insufficient_evidence" if insufficient_evidence else "complete"

        limitations.extend(
            f"Input coverage issue: {gap}" for gap in correlation_input.telemetry_gaps
        )

        return CorrelationResult(
            diagnosis_id=correlation_input.performance.diagnosis_id,
            status=status,
            summary=summary,
            hypotheses=hypotheses,
            alternative_explanations=alternative_summaries,
            conflicts=conflicts,
            insufficient_evidence=(False if no_fault_detected else insufficient_evidence),
            limitations=limitations,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.strip().lower().split())

    @staticmethod
    def _device_ids(finding: AgentFinding) -> set[str]:
        devices = set(finding.affected_device_ids)
        if finding.device_id:
            devices.add(finding.device_id)
        return devices

    @staticmethod
    def _abnormal_findings(
        message: AgentMessage,
    ) -> list[tuple[EvidenceReference, AgentFinding]]:
        return [
            (
                EvidenceReference(
                    agent=message.agent,
                    finding_index=index,
                    metric=finding.metric,
                    value=finding.value,
                    severity=finding.severity,
                    assessment=finding.assessment,
                    device_id=finding.device_id,
                    interface_id=finding.interface_id,
                    observed_at=finding.observed_at,
                    affected_device_ids=finding.affected_device_ids,
                    affected_link_ids=finding.affected_link_ids,
                    affected_segment_ids=finding.affected_segment_ids,
                ),
                finding,
            )
            for index, finding in enumerate(message.findings)
            if finding.severity in {"warning", "critical"}
        ]

    @staticmethod
    def _interfaces_conflict(
        performance: AgentFinding, infrastructure: AgentFinding
    ) -> bool:
        return bool(
            performance.interface_id
            and infrastructure.interface_id
            and performance.interface_id != infrastructure.interface_id
        )

    @staticmethod
    def _corroborating_connectivity(
        connectivity: list[tuple[EvidenceReference, AgentFinding]],
        device_ids: set[str],
    ) -> list[tuple[EvidenceReference, AgentFinding]]:
        return [
            (reference, finding)
            for reference, finding in connectivity
            if FaultCorrelationAgent._normalize(finding.metric) in _CONNECTIVITY_METRICS
            and device_ids & FaultCorrelationAgent._device_ids(finding)
        ]

    @staticmethod
    def _scope_references(
        message: AgentMessage, device_ids: set[str]
    ) -> list[EvidenceReference]:
        """Return scope findings that explicitly cover a hypothesis device."""
        return [
            EvidenceReference(
                agent=message.agent,
                finding_index=index,
                metric=finding.metric,
                value=finding.value,
                severity=finding.severity,
                assessment=finding.assessment,
                device_id=finding.device_id,
                interface_id=finding.interface_id,
                observed_at=finding.observed_at,
                affected_device_ids=finding.affected_device_ids,
                affected_link_ids=finding.affected_link_ids,
                affected_segment_ids=finding.affected_segment_ids,
            )
            for index, finding in enumerate(message.findings)
            if FaultCorrelationAgent._normalize(finding.metric) == "incident scope"
            and device_ids & FaultCorrelationAgent._device_ids(finding)
        ]

    @classmethod
    def _complete_healthy_input(
        cls,
        correlation_input: CorrelationInput,
        messages: dict[str, AgentMessage],
        conflicts: list[EvidenceConflict],
    ) -> bool:
        """Recognize an explicitly complete, clean observation set as no-fault."""
        if correlation_input.telemetry_gaps or conflicts:
            return False
        if any(
            finding.severity in {"warning", "critical"}
            for message in messages.values()
            for finding in message.findings
        ):
            return False

        expected_metrics = {
            "performance": {
                "latency",
                "jitter",
                "packet loss",
                "throughput",
                "link utilization",
            },
            "infrastructure": {
                "cpu utilization",
                "memory utilization",
                "interface errors",
                "egress queue drops",
                "device status",
            },
        }
        for agent, required in expected_metrics.items():
            actual = {
                cls._normalize(finding.metric)
                for finding in messages[agent].findings
            }
            if not required.issubset(actual):
                return False

        connectivity_findings = messages["connectivity"].findings
        return (
            any(
                cls._normalize(finding.metric) == "incident scope"
                and cls._normalize(str(finding.value)) == "no confirmed impact"
                for finding in connectivity_findings
            )
            and not any(
                cls._normalize(finding.metric) == "topology completeness"
                for finding in connectivity_findings
            )
        )

    @staticmethod
    def _add_candidate(
        candidates: dict[tuple[str, tuple[str, ...]], dict[str, Any]],
        *,
        cause: str,
        explanation: str,
        references: list[EvidenceReference],
        devices: set[str],
        semantic_match: bool,
    ) -> None:
        device_key = tuple(sorted(devices))
        key = (cause, device_key)
        candidate = candidates.setdefault(
            key,
            {
                "cause": cause,
                "explanation": explanation,
                "references": {},
                "devices": set(),
                "semantic_match": semantic_match,
            },
        )
        for reference in references:
            candidate["references"][(reference.agent, reference.finding_index)] = reference
        candidate["devices"].update(devices)
        candidate["semantic_match"] = candidate["semantic_match"] or semantic_match

    @staticmethod
    def _rank_candidates(
        candidates: dict[tuple[str, tuple[str, ...]], dict[str, Any]],
        conflicts: list[EvidenceConflict],
    ) -> list[RootCauseHypothesis]:
        ranked = []
        for candidate in candidates.values():
            evidence = sorted(
                candidate["references"].values(),
                key=lambda ref: (ref.agent, ref.finding_index),
            )
            agents = {reference.agent for reference in evidence}
            critical_count = sum(reference.severity == "critical" for reference in evidence)
            confidence = 0.20 + 0.12 * len(agents)
            confidence += 0.06 if len(candidate["devices"]) == 1 else 0.0
            confidence += 0.12 if critical_count >= 2 else (0.06 if critical_count else 0.0)
            confidence += 0.08 if candidate["semantic_match"] else 0.0
            timestamp_skew = FaultCorrelationAgent._timestamp_skew_seconds(evidence)
            if timestamp_skew is not None and timestamp_skew > _MAX_OBSERVATION_SKEW_SECONDS:
                confidence -= 0.20
            related_conflicts = [
                conflict
                for conflict in conflicts
                if candidate["devices"] & set(conflict.affected_device_ids)
            ]
            confidence -= 0.25 * len(related_conflicts)
            confidence = max(0.0, min(round(confidence, 2), 0.9))
            ranked.append(
                {
                    "cause": candidate["cause"],
                    "explanation": candidate["explanation"],
                    "confidence": confidence,
                    "evidence": evidence,
                    "affected_device_ids": sorted(candidate["devices"]),
                }
            )

        ranked.sort(
            key=lambda item: (
                -item["confidence"],
                -len(item["evidence"]),
                item["cause"],
                item["affected_device_ids"],
            )
        )
        hypotheses = []
        for rank, item in enumerate(ranked, start=1):
            hypotheses.append(
                RootCauseHypothesis(
                    rank=rank,
                    cause=item["cause"],
                    explanation=item["explanation"],
                    confidence=item["confidence"],
                    evidence=item["evidence"],
                    affected_device_ids=item["affected_device_ids"],
                    affected_link_ids=sorted(
                        {
                            link_id
                            for reference in item["evidence"]
                            for link_id in reference.affected_link_ids
                        }
                    ),
                    affected_segment_ids=sorted(
                        {
                            segment_id
                            for reference in item["evidence"]
                            for segment_id in reference.affected_segment_ids
                        }
                    ),
                    uncertainties=[
                        "Confidence is a deterministic heuristic, not a calibrated probability.",
                        "Correlated findings alone do not prove causation.",
                    ]
                    + ([
                        "Supporting measurements span more than five minutes; temporal alignment is weak."
                    ] if timestamp_skew is not None and timestamp_skew > _MAX_OBSERVATION_SKEW_SECONDS else [])
                    + ([
                        "Some supporting findings have no observation timestamp, so temporal alignment could not be checked."
                    ] if any(reference.observed_at is None for reference in evidence) else [])
                    + [
                        conflict.description
                        for conflict in conflicts
                        if set(item["affected_device_ids"])
                        & set(conflict.affected_device_ids)
                    ],
                )
            )
        return hypotheses

    @staticmethod
    def _timestamp_skew_seconds(evidence: list[EvidenceReference]) -> float | None:
        """Return the span of supplied finding timestamps, if at least two exist."""
        timestamps = [
            reference.observed_at
            for reference in evidence
            if reference.observed_at is not None
        ]
        if len(timestamps) < 2:
            return None

        normalized = [
            stamp.replace(tzinfo=timezone.utc)
            if stamp.tzinfo is None
            else stamp.astimezone(timezone.utc)
            for stamp in timestamps
        ]
        return (max(normalized) - min(normalized)).total_seconds()

    @classmethod
    def _find_conflicts(
        cls, messages: dict[str, AgentMessage]
    ) -> list[EvidenceConflict]:
        conflicts = []
        infrastructure = messages["infrastructure"]
        connectivity = messages["connectivity"]
        for infra_index, infra_finding in enumerate(infrastructure.findings):
            if cls._normalize(infra_finding.metric) != "device status":
                continue
            infra_status = str(infra_finding.value).lower()
            if infra_status not in {"online", "offline"}:
                continue
            for conn_index, conn_finding in enumerate(connectivity.findings):
                if cls._normalize(conn_finding.metric) != "device reachability":
                    continue
                conn_status = str(conn_finding.value).lower()
                same_devices = cls._device_ids(infra_finding) & cls._device_ids(conn_finding)
                contradictory = (infra_status == "online" and conn_status == "unreachable") or (
                    infra_status == "offline" and conn_status == "reachable"
                )
                if contradictory and same_devices:
                    conflicts.append(
                        EvidenceConflict(
                            description=(
                                f"Infrastructure and Connectivity report contradictory "
                                f"states for device(s): {', '.join(sorted(same_devices))}."
                            ),
                            evidence=[
                                EvidenceReference(
                                    agent="infrastructure",
                                    finding_index=infra_index,
                                    metric=infra_finding.metric,
                                    value=infra_finding.value,
                                    severity=infra_finding.severity,
                                    assessment=infra_finding.assessment,
                                    device_id=infra_finding.device_id,
                                    interface_id=infra_finding.interface_id,
                                    observed_at=infra_finding.observed_at,
                                    affected_device_ids=infra_finding.affected_device_ids,
                                    affected_link_ids=infra_finding.affected_link_ids,
                                    affected_segment_ids=infra_finding.affected_segment_ids,
                                ),
                                EvidenceReference(
                                    agent="connectivity",
                                    finding_index=conn_index,
                                    metric=conn_finding.metric,
                                    value=conn_finding.value,
                                    severity=conn_finding.severity,
                                    assessment=conn_finding.assessment,
                                    device_id=conn_finding.device_id,
                                    interface_id=conn_finding.interface_id,
                                    observed_at=conn_finding.observed_at,
                                    affected_device_ids=conn_finding.affected_device_ids,
                                    affected_link_ids=conn_finding.affected_link_ids,
                                    affected_segment_ids=conn_finding.affected_segment_ids,
                                ),
                            ],
                            affected_device_ids=sorted(same_devices),
                        )
                    )
        return conflicts

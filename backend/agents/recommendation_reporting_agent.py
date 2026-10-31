"""Deterministic reporting and evidence-based recommendations."""

from typing import Any

from backend.models.correlation import CorrelationResult, RootCauseHypothesis
from backend.models.report import DiagnosticReport, Recommendation


_RECOMMENDATIONS = {
    "device_resource_exhaustion": (
        "Inspect CPU and memory history and active workloads on the cited device; "
        "verify capacity or workload impact before changing placement or limits."
    ),
    "interface_or_queue_drops": (
        "Inspect interface error and egress queue counters on the cited device and "
        "interface for the same measurement window; verify queue configuration before "
        "changing traffic handling."
    ),
    "connectivity_path_failure": (
        "Verify the cited down link or unreachable device and inspect the associated "
        "path and routing; restore only failures confirmed by direct checks."
    ),
    "device_unavailable": (
        "Check power and management reachability for the cited device, then compare "
        "its infrastructure status with connectivity probes before restarting or "
        "replacing equipment."
    ),
    "weak_wifi_signal": (
        "Inspect physical AP placement and client proximity, verify RSSI/SNR coverage, "
        "check for 2.4/5GHz RF interference, and consider roaming threshold adjustments "
        "or adding an access point before replacing hardware."
    ),
    "ethernet_interface_fault": (
        "Inspect physical Ethernet cabling, patch leads, and SFP/transceiver modules on "
        "the affected interface; test for cable faults with a cable tester, clean fiber connectors "
        "if optical, and verify speed/duplex autonegotiation consistency."
    ),
    "dns_dhcp_failure": (
        "Verify DNS daemon/server process status and UDP/TCP port 53 reachability; inspect DHCP "
        "pool capacity and relay agent configuration; check local resolver configurations "
        "and firewall rules blocking DHCP (ports 67/68) or DNS."
    ),
    "interoperability_failure": (
        "Verify communication protocol and message schemas between agent and telemetry endpoints; "
        "ensure canonical schema version 1.0 is implemented and harmonize field naming and "
        "measurement units before resubmitting."
    ),
}


class RecommendationReportingAgent:
    """Convert Agent 4's correlation result into a unified diagnostic report."""

    agent_name = "recommendation_reporting"

    def analyze(
        self, result: CorrelationResult | dict[str, Any]
    ) -> DiagnosticReport:
        """Validate a correlation result and prepare a report without new evidence."""
        correlation = (
            result
            if isinstance(result, CorrelationResult)
            else CorrelationResult.model_validate(result)
        )
        if correlation.insufficient_evidence != (
            correlation.status == "insufficient_evidence"
        ):
            raise ValueError(
                "correlation status and insufficient_evidence flag disagree"
            )
        if correlation.status == "complete" and not correlation.hypotheses:
            raise ValueError("complete correlation result must include a hypothesis")

        insufficient = correlation.insufficient_evidence
        no_fault = correlation.status == "no_fault_detected"
        primary = correlation.hypotheses[0] if correlation.hypotheses else None
        report_hypotheses = (
            correlation.hypotheses if insufficient else correlation.hypotheses[:1]
        )
        supporting_evidence = primary.evidence if primary and not insufficient else []
        identifiers = self._affected_identifiers(report_hypotheses)
        alternative_hypotheses = (
            correlation.hypotheses
            if insufficient
            else correlation.hypotheses[1:]
        )
        if alternative_hypotheses:
            alternative_explanations = [
                f"{hypothesis.cause}: {hypothesis.explanation}"
                for hypothesis in alternative_hypotheses
            ]
        else:
            alternative_explanations = list(correlation.alternative_explanations)
        if primary and not alternative_explanations:
            alternative_explanations = [
                "No other evidence-supported cause was identified; other causes "
                "remain unassessed."
            ]
        evidence_sources = self._source_labels(
            [
                reference
                for hypothesis in correlation.hypotheses
                for reference in hypothesis.evidence
            ]
            + [
                reference
                for conflict in correlation.conflicts
                for reference in conflict.evidence
            ]
        )
        recommendations = (
            [
                Recommendation(
                    priority="low",
                    action=(
                        "No corrective action is indicated by the supplied telemetry; "
                        "continue routine monitoring."
                    ),
                )
            ]
            if no_fault
            else self._recommendations(
                correlation.hypotheses, insufficient=insufficient
            )
        )
        limitations = list(correlation.limitations)
        limitations.append(
            "Confidence categories are thresholds over Agent 4's deterministic "
            "confidence heuristic, not calibrated probabilities."
        )
        uncertainties = list(
            dict.fromkeys(
                uncertainty
                for hypothesis in report_hypotheses
                for uncertainty in hypothesis.uncertainties
            )
        )
        if insufficient and not uncertainties:
            uncertainties.append(
                "The available correlation findings do not establish a reliable cause."
            )
        if correlation.conflicts:
            uncertainties.extend(
                f"Conflicting evidence: {conflict.description}"
                for conflict in correlation.conflicts
            )

        confidence_score = primary.confidence if primary else None
        confidence_breakdown = primary.confidence_breakdown if primary and not no_fault else None
        return DiagnosticReport(
            diagnosis_id=correlation.diagnosis_id,
            incident_status=("no_fault_detected" if no_fault else (
                "insufficient_evidence" if insufficient else "probable_cause"
            )),
            probable_root_cause=(
                primary.explanation if primary and not insufficient and not no_fault else None
            ),
            confidence_score=None if no_fault else confidence_score,
            confidence_category=(
                "not_applicable"
                if no_fault
                else self._confidence_category(confidence_score, insufficient)
            ),
            confidence_breakdown=confidence_breakdown,
            affected_device_ids=identifiers["devices"],
            affected_link_ids=identifiers["links"],
            affected_segment_ids=identifiers["segments"],
            supporting_evidence=supporting_evidence,
            conflicts=correlation.conflicts,
            alternative_explanations=alternative_explanations,
            alternative_hypotheses=alternative_hypotheses,
            recommended_actions=recommendations,
            evidence_sources=evidence_sources,
            uncertainties=uncertainties,
            limitations=limitations,
        )

    @staticmethod
    def _confidence_category(
        score: float | None, insufficient: bool
    ) -> str:
        if insufficient or score is None:
            return "insufficient"
        if score >= 0.8:
            return "high"
        if score >= 0.6:
            return "moderate"
        return "low"

    @staticmethod
    def _affected_identifiers(
        hypotheses: list[RootCauseHypothesis],
    ) -> dict[str, list[str]]:
        devices: set[str] = set()
        links: set[str] = set()
        segments: set[str] = set()
        for hypothesis in hypotheses:
            for reference in hypothesis.evidence:
                if reference.device_id:
                    devices.add(reference.device_id)
                devices.update(reference.affected_device_ids)
                links.update(reference.affected_link_ids)
                segments.update(reference.affected_segment_ids)
        return {
            "devices": sorted(devices),
            "links": sorted(links),
            "segments": sorted(segments),
        }

    @staticmethod
    def _source_labels(references) -> list[str]:
        labels = {
            f"{reference.agent}.findings[{reference.finding_index}]"
            for reference in references
        }
        return sorted(labels)

    @staticmethod
    def _recommendations(
        hypotheses: list[RootCauseHypothesis], *, insufficient: bool
    ) -> list[Recommendation]:
        if insufficient and not hypotheses:
            return [
                Recommendation(
                    priority="high",
                    action=(
                        "Collect performance, infrastructure, and connectivity findings "
                        "for the same devices and measurement period, then rerun correlation."
                    ),
                    related_cause=None,
                )
            ]

        recommendations = []
        for hypothesis in hypotheses:
            action = _RECOMMENDATIONS.get(hypothesis.cause)
            if action is None:
                action = (
                    "Verify the cited findings against the original telemetry before "
                    "taking corrective action; no cause-specific action is defined."
                )
            recommendations.append(
                Recommendation(
                    priority=(
                        "high"
                        if (
                            not insufficient
                            and hypothesis.rank == 1
                            and hypothesis.confidence >= 0.8
                        )
                        else "medium"
                    ),
                    action=action,
                    related_cause=hypothesis.cause,
                    evidence=hypothesis.evidence,
                )
            )
        if insufficient:
            recommendations.append(
                Recommendation(
                    priority="high",
                    action=(
                        "Collect aligned performance, infrastructure, and connectivity "
                        "observations for the implicated devices and rerun correlation."
                    ),
                    related_cause=None,
                )
            )
        return recommendations

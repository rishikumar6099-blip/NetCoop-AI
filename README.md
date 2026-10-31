# NetCoop AI

NetCoop AI is a hackathon prototype for multi-agent network fault diagnosis and interoperability. It accepts submitted performance, infrastructure and connectivity telemetry, analyzes each domain, correlates the resulting evidence, and returns a structured diagnostic report.

The project addresses a common troubleshooting problem: network symptoms and device health signals are often inspected separately, making it difficult to identify a likely shared cause or understand how strongly the evidence supports it. NetCoop AI coordinates five specialized, deterministic agents to make those findings reviewable in one workflow.

This prototype analyzes telemetry supplied in a diagnosis request. It does not continuously monitor campus devices, collect telemetry itself, or automatically remediate network faults. Dashboard charts and inventory examples are explicitly illustrative; results shown after a diagnosis are returned by the backend.

## Architecture

The backend contains five deterministic agents coordinated by a sequential orchestrator:

1. **Telemetry and Performance Agent** analyzes network transport metrics:
   - `latency_ms` (warning >=100.0 ms, critical >=250.0 ms)
   - `jitter_ms` (warning >=20.0 ms, critical >=50.0 ms)
   - `packet_loss_pct` (warning >=1.0%, critical >=5.0%)
   - `throughput_mbps` (recorded as informational baseline)
   - `link_utilization_pct` (warning >=80.0%, critical >=95.0%)
   - `rssi_dbm` (warning <=-75.0 dBm, critical <=-82.0 dBm for Wi-Fi signal quality)
   - `dns_lookup_time_ms` (warning >=150.0 ms, critical >=1000.0 ms for DNS resolution latency)
2. **Infrastructure Health Agent** analyzes device resources and link layer health:
   - `cpu_utilization_pct` (warning >=80.0%, critical >=95.0%)
   - `memory_utilization_pct` (warning >=80.0%, critical >=95.0%)
   - `interface_errors` (CRC / physical errors: warning >=1, critical >=10)
   - `egress_queue_drops` (buffer drops: warning >=1, critical >=10)
   - `device_status` (`online`, `offline` [critical], `degraded` [warning])
   - `dhcp_status` (`bound`, `failed` [critical], `timeout` [critical], `renewing`, `unknown`)
   - `link_flaps` (carrier transitions: warning >=1, critical >=5)
   - `interoperability_status` (`compatible`, `incompatible` [critical], `unknown`)
3. **Connectivity Analysis Agent** evaluates topology state and network graph integrity:
   - Devices: `device_id`, optional `segment_id`, `reachability` (`reachable`, `unreachable`, `unknown`)
   - Links: `link_id`, `source_device_id`, `target_device_id`, `status` (`up`, `down`, `unknown`), optional `medium` (`ethernet`, `wifi`, `fiber`, `unknown`)
   - Identifies explicitly unreachable devices, down links, isolated network segments, and calculates blast radius scope.
4. **Fault Correlation Agent** compares findings from Agents 1–3 using deterministic correlation rules:
   - Hypotheses ranked: `interface_or_queue_drops`, `device_resource_exhaustion`, `connectivity_path_failure`, `weak_wifi_signal`, `ethernet_interface_fault`, `dns_dhcp_failure`, and `interoperability_failure`.
   - Traceability: preserves exact cross-agent finding index pointers (`finding_index`), agent names, and affected device/link identifiers.
   - Conflict resolution: explicitly logs contradictions (e.g. reachable device reported offline) and penalizes confidence.
   - Honest uncertainty: flags missing corroboration or wide timestamp skews (> 5 minutes).
5. **Recommendation and Reporting Agent** converts Agent 4's correlation results into an actionable report:
   - Synthesizes incident status (`probable_cause`, `no_fault_detected`, or `insufficient_evidence`).
   - Categorizes confidence (`high`, `moderate`, `low`).
   - Generates targeted, actionable recommendations linked to evidence sources without fabricating new telemetry.

Agents 1–3 return structured `AgentMessage` objects. Agent 4 returns a structured `CorrelationResult`, and Agent 5 returns a structured `DiagnosticReport`. All message models require and validate `schema_version: "1.0"`.

### Sequential diagnosis flow

`POST /api/diagnose` validates the request, including one shared diagnosis ID across the three telemetry sections, then runs these stages in order:

1. Performance analysis.
2. Infrastructure analysis.
3. Connectivity analysis.
4. Correlation of the three validated agent messages.
5. Reporting from the correlation result.

All findings retain their diagnosis ID and relevant device, interface, link or segment identifiers. Evidence references identify a source agent and finding index, allowing a report reference to be checked against the original message.

If an agent fails, the endpoint returns workflow status `partial`, the messages from successful stages and failure metadata. Correlation and reporting are skipped if one of Agents 1–3 fails; the orchestrator does not synthesize replacement findings. A completed workflow can still have an incident status of `insufficient_evidence`.

## Telemetry input

The diagnosis request has exactly three top-level sections: `performance`, `infrastructure` and `connectivity`. Each section contains the same `diagnosis_id`.

```json
{
  "performance": {
    "diagnosis_id": "campus-check-001",
    "samples": [
      {
        "device_id": "RTR-01",
        "interface_id": "xe-0/0/0",
        "observed_at": "2026-10-31T10:00:00Z",
        "latency_ms": 185,
        "jitter_ms": 42,
        "packet_loss_pct": 2.4,
        "throughput_mbps": 890,
        "link_utilization_pct": 96
      }
    ]
  },
  "infrastructure": {
    "diagnosis_id": "campus-check-001",
    "samples": [
      {
        "device_id": "RTR-01",
        "interface_id": "xe-0/0/0",
        "observed_at": "2026-10-31T10:01:00Z",
        "cpu_utilization_pct": 54,
        "memory_utilization_pct": 61,
        "interface_errors": 0,
        "egress_queue_drops": 18,
        "device_status": "online"
      }
    ]
  },
  "connectivity": {
    "diagnosis_id": "campus-check-001",
    "devices": [
      {"device_id": "RTR-01", "segment_id": "engineering", "reachability": "reachable"},
      {"device_id": "SW-01", "segment_id": "engineering", "reachability": "reachable"}
    ],
    "links": [
      {
        "link_id": "L-01",
        "source_device_id": "RTR-01",
        "target_device_id": "SW-01",
        "status": "up"
      }
    ]
  }
}
```

Performance samples accept `device_id`, optional `interface_id` and `observed_at`, and any supplied values from `latency_ms`, `jitter_ms`, `packet_loss_pct`, `throughput_mbps`, `link_utilization_pct`, `rssi_dbm` (Wi-Fi signal strength in dBm), and `dns_lookup_time_ms` (DNS resolution latency in ms). Each sample must provide at least one metric.

Infrastructure samples accept `device_id`, optional `interface_id` and `observed_at`, plus any supplied values from `cpu_utilization_pct`, `memory_utilization_pct`, `interface_errors`, `egress_queue_drops`, `device_status` (`online`, `offline` or `degraded`), `dhcp_status` (`bound`, `failed`, `timeout`, `renewing`, or `unknown`), `link_flaps` (non-negative integer), and `interoperability_status` (`compatible`, `incompatible`, or `unknown`). Each sample must provide at least one measurement.

Connectivity devices accept `device_id`, optional `segment_id` and optional `reachability` (`reachable`, `unreachable` or `unknown`). Links accept `link_id`, `source_device_id`, `target_device_id`, `status` (`up`, `down` or `unknown`), and optional `medium` (`ethernet`, `wifi`, `fiber` or `unknown`). The topology must contain at least one device or link. Device and link IDs must be unique within the topology.

Each telemetry batch and request accepts an optional `schema_version` (defaults to `"1.0"`).

## Interoperability, Normalization and Schemas

To satisfy agent interoperability and facilitate communication across heterogeneous network monitoring agents and telemetry vendors, NetCoop AI includes a dedicated `InteroperabilityService` (`backend/services/interoperability.py`) and schema-level validation pipelines:

### 1. Schema versioning
- **Canonical Version**: `"1.0"`. All batch schemas (`TelemetryBatch`, `InfrastructureTelemetryBatch`, `ConnectivityTelemetry`), agent messages (`AgentMessage`), and requests/responses (`DiagnosisRequest`, `CorrelationResult`, `DiagnosticReport`) enforce version compatibility.
- **Incompatible Versions**: Any payload declaring an unsupported schema version raises `IncompatibleSchemaVersionError` with an explicit diagnostic message and allowed versions.

### 2. Telemetry field-name normalization
Heterogeneous agents and monitoring tools often use non-canonical metric names. NetCoop AI automatically resolves recognized field aliases before Pydantic model validation:

| Domain | Canonical Field | Recognized Aliases |
|---|---|---|
| **Performance** | `latency_ms` | `latency`, `rtt`, `ping_ms`, `round_trip_time` |
| **Performance** | `jitter_ms` | `jitter`, `delay_variation` |
| **Performance** | `packet_loss_pct` | `packet_loss`, `loss`, `loss_pct`, `drop_rate` |
| **Performance** | `throughput_mbps` | `throughput`, `bandwidth`, `bitrate` |
| **Performance** | `link_utilization_pct` | `link_utilization`, `utilization`, `link_load` |
| **Performance** | `rssi_dbm` | `rssi`, `wifi_rssi`, `signal_strength`, `wifi_signal` |
| **Performance** | `dns_lookup_time_ms` | `dns_lookup_time`, `dns_latency`, `dns_time`, `dns_resolution_ms` |
| **Infrastructure** | `cpu_utilization_pct` | `cpu`, `cpu_usage`, `cpu_util`, `cpu_pct` |
| **Infrastructure** | `memory_utilization_pct` | `memory`, `mem_usage`, `mem_util`, `memory_pct` |
| **Infrastructure** | `interface_errors` | `errors`, `crc_errors`, `rx_errors`, `tx_errors` |
| **Infrastructure** | `egress_queue_drops` | `queue_drops`, `egress_drops`, `buffer_drops`, `drops` |
| **Infrastructure** | `device_status` | `status`, `state`, `health_status` |
| **Infrastructure** | `dhcp_status` | `dhcp`, `dhcp_state`, `ip_assignment_status` |
| **Infrastructure** | `link_flaps` | `flaps`, `carrier_flaps`, `interface_flaps` |
| **Infrastructure** | `interoperability_status`| `interop_status`, `compatibility_status`, `schema_status` |

- **Conflict Detection**: If a sample supplies both the canonical name and an alias with differing values, NetCoop AI rejects the payload with `IncompatibleFieldError` rather than silently picking an arbitrary value.

### 3. Unit normalization and validation
Inputs frequently arrive with string unit suffixes or in differing scale factors. NetCoop AI parses, scales, and validates units deterministically:

- **Time Latency**: String suffixes `s` or `sec` are converted to milliseconds (`val * 1000`), `us` or `µs` to milliseconds (`val / 1000`), and `ms` parsed directly.
- **Throughput**: String suffixes `Gbps` are converted to Mbps (`val * 1000`), `Kbps` to Mbps (`val / 1000`), `bps` to Mbps (`val / 1,000,000`), and `Mbps` parsed directly.
- **Percentages**: Suffix `%` is stripped; floating-point ratios between `0.0` and `1.0` are converted to 0–100% scale.
- **Signal**: Suffix `dBm` is stripped for RSSI measurements.
- **Incompatible Units Rejection**: If an unsupported unit (e.g., `volts`, `celsius`, `kg`) is passed for a network metric, `IncompatibleUnitError` is raised, preventing invalid data from corrupting diagnostic models.

### 4. Interoperability error handling and failure isolation
- The exception hierarchy rooted at `InteroperabilityError` ensures that schema version errors, unit errors, and field conflicts produce readable error messages.
- If an agent receives malformed or incompatible messages during diagnosis, the orchestrator catches the failure, records it in the `failures` list (specifying the failed stage and error message), and proceeds safely without fabricating synthetic findings.

## API

Start the backend at `http://127.0.0.1:8000`. Available endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Backend process health check. |
| `POST` | `/api/performance` | Run the Performance Agent on one telemetry batch. |
| `POST` | `/api/infrastructure` | Run the Infrastructure Health Agent on one batch. |
| `POST` | `/api/connectivity` | Run Connectivity Analysis on one topology. |
| `POST` | `/api/diagnose` | Run the complete five-agent workflow. |

FastAPI's interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### Diagnosis response

A complete workflow response contains:

- `diagnosis_id` and workflow `status` (`complete` or `partial`).
- `agent_messages` for the completed performance, infrastructure and connectivity agents.
- `correlation_result` from Agent 4, including status (`complete`, `no_fault_detected` or `insufficient_evidence`), ranked hypotheses, alternatives, conflicts and limitations.
- `diagnostic_report` from Agent 5, including incident status, probable cause when supported, confidence, affected identifiers, evidence, recommendations and limitations.
- `failures`, empty when no stage failed.

Example response excerpt for the request above (other top-level fields are omitted):

```json
{
  "diagnosis_id": "campus-check-001",
  "status": "complete",
  "correlation_result": {
    "schema_version": "1.0",
    "diagnosis_id": "campus-check-001",
    "agent": "fault_correlation",
    "status": "complete",
    "summary": "Ranked 1 evidence-supported root-cause hypothesis(s); top candidate: interface_or_queue_drops.",
    "hypotheses": [
      {
        "rank": 1,
        "cause": "interface_or_queue_drops",
        "explanation": "Reported interface errors or egress queue drops coincide with packet loss on the same device and may be contributing.",
        "confidence": 0.64,
        "evidence": [
          {
            "agent": "performance",
            "finding_index": 2,
            "metric": "packet loss",
            "value": 2.4,
            "severity": "warning",
            "device_id": "RTR-01",
            "interface_id": "xe-0/0/0",
            "observed_at": "2026-10-31T10:00:00Z",
            "affected_device_ids": [],
            "affected_link_ids": [],
            "affected_segment_ids": []
          },
          {
            "agent": "infrastructure",
            "finding_index": 3,
            "metric": "Egress queue drops",
            "value": 18,
            "severity": "critical",
            "device_id": "RTR-01",
            "interface_id": "xe-0/0/0",
            "observed_at": "2026-10-31T10:01:00Z",
            "affected_device_ids": [],
            "affected_link_ids": [],
            "affected_segment_ids": []
          }
        ],
        "affected_device_ids": ["RTR-01"],
        "affected_link_ids": [],
        "affected_segment_ids": [],
        "alternative_explanations": ["No other evidence-supported cause was identified; other causes remain unassessed."],
        "uncertainties": [
          "Confidence is a deterministic heuristic, not a calibrated probability.",
          "Correlated findings alone do not prove causation."
        ]
      }
    ],
    "alternative_explanations": ["No other evidence-supported cause was identified; other causes remain unassessed."],
    "conflicts": [],
    "insufficient_evidence": false,
    "limitations": [
      "Correlated observations indicate association, not proven causation.",
      "The input messages do not establish event timing or causal order."
    ]
  },
  "diagnostic_report": {
    "schema_version": "1.0",
    "diagnosis_id": "campus-check-001",
    "incident_status": "probable_cause",
    "probable_root_cause": "Reported interface errors or egress queue drops coincide with packet loss on the same device and may be contributing.",
    "confidence_score": 0.64,
    "confidence_category": "moderate",
    "affected_device_ids": ["RTR-01"],
    "affected_link_ids": [],
    "affected_segment_ids": [],
    "conflicts": [],
    "alternative_explanations": ["No other evidence-supported cause was identified; other causes remain unassessed."],
    "alternative_hypotheses": [],
    "recommended_actions": [
      {
        "priority": "medium",
        "action": "Inspect interface error and egress queue counters on the cited device and interface for the same measurement window; verify queue configuration before changing traffic handling.",
        "related_cause": "interface_or_queue_drops"
      }
    ],
    "evidence_sources": ["infrastructure.findings[3]", "performance.findings[2]"],
    "uncertainties": [
      "Confidence is a deterministic heuristic, not a calibrated probability.",
      "Correlated findings alone do not prove causation."
    ],
    "limitations": [
      "Correlated observations indicate association, not proven causation.",
      "The input messages do not establish event timing or causal order.",
      "Confidence categories are thresholds over Agent 4's deterministic confidence heuristic, not calibrated probabilities."
    ]
  },
  "failures": []
}
```

The response excerpt omits `agent_messages` and some report fields for readability. The actual response includes the full source messages and complete repeated evidence references in the report and recommendations. `finding_index` is zero-based and refers to the matching `findings` array in `agent_messages`.

## Correlation, evidence and confidence

Agent 4 uses deterministic rules. Examples include matching performance degradation with resource pressure on the same device, packet loss with interface errors or queue drops on the same device, and performance issues with a reported connectivity problem. Device availability can also be corroborated when infrastructure and connectivity report a consistent offline/unreachable state. A hypothesis includes references to the original findings and carries the device, link and segment identifiers present in that evidence.

Contradictory infrastructure and connectivity states for the same exact device ID are returned as conflicts. Identifiers are matched exactly; the system does not assume that different names refer to one device. The orchestrator records a mismatch when a performance or infrastructure device ID is absent from another relevant section. Additional connectivity-only devices are allowed because a supplied topology can include devices without corresponding performance or infrastructure samples. Mismatch details are included in correlation and report limitations. Valid matching evidence can still support a diagnosis despite an unrelated mismatch.

Incomplete input is not treated as healthy. The orchestrator identifies missing performance and infrastructure measurements and unknown or incomplete topology states. `no_fault_detected` is reserved for complete supplied coverage with no warning or critical findings and no confirmed connectivity impact. If the evidence cannot establish a supported cause or complete healthy state, the result is `insufficient_evidence`; no root cause is claimed as probable.

Confidence is a deterministic prototype heuristic, not a calibrated probability. The current score starts at 0.20, adds 0.12 per contributing agent, 0.06 for a single shared device, up to 0.12 for critical evidence, and 0.08 for a semantic rule match. It subtracts 0.25 per related conflict and 0.20 when available evidence timestamps span more than five minutes, then clamps the result to 0–0.90. The report labels scores `high` at 0.80 or above, `moderate` at 0.60 or above, and `low` below 0.60; scores below 0.60 are not treated as reliable diagnoses. `insufficient_evidence` and `no_fault_detected` have their own categories. Correlation indicates association, not proven causation. If timestamps are absent, the report notes that temporal alignment could not be checked; topology observations currently do not include timestamps.

## Supported diagnostic scenarios

The reusable dataset in `backend/data/diagnosis_scenarios.json` contains reproducible end-to-end scenarios covering the mandatory hackathon requirements and extended fault modes:

### Hackathon core diagnostic scenarios:
1. **Normal network operation (`normal_network`)** — Complete healthy telemetry across performance, infrastructure, and connectivity domains returns `no_fault_detected` and no root cause.
2. **Link congestion (`link_congestion` / `network_congestion`)** — High link utilization and egress queue drops coinciding with packet loss support an `interface_or_queue_drops` hypothesis with moderate-to-high confidence.
3. **Weak Wi-Fi signal (`weak_wifi_signal`)** — Low Wi-Fi RSSI (<= -82 dBm), degraded access point status, and wireless packet loss support a `weak_wifi_signal` hypothesis.
4. **Ethernet/interface fault (`ethernet_interface_fault`)** — High physical CRC errors (`interface_errors`) with packet loss and zero queue drops on wired interfaces support an `ethernet_interface_fault` hypothesis.
5. **DNS/DHCP failure (`dns_dhcp_failure`)** — DNS lookup timeouts (>= 1000 ms) and DHCP status failure/timeout with operational reachability support a `dns_dhcp_failure` hypothesis.
6. **Interoperability failure (`interoperability_failure`)** — Incompatible schema status, protocol mismatches, or schema version errors support an `interoperability_failure` hypothesis.

### Extended robustness scenarios:
7. **Router infrastructure overload (`router_infrastructure_overload`)** — High CPU and memory utilization coinciding with elevated latency/jitter support `device_resource_exhaustion`.
8. **Broken connectivity (`broken_connectivity`)** — Physical link down or unreachable device coinciding with performance degradation supports `connectivity_path_failure`.
9. **Conflicting device state (`conflicting_device_state`)** — Infrastructure reports offline while connectivity reports reachable; the conflict is explicitly recorded and confidence is penalized, preventing fabricated root causes.
10. **Incomplete telemetry (`incomplete_telemetry`)** — Missing key metrics or unknown topology states safely return `insufficient_evidence`.

These are reproducible test inputs, not live network observations.

## Frontend and backend integration

The frontend is a React 19 application built with Vite, Tailwind CSS v4, Recharts and Lucide React. `/` renders the landing page; `/dashboard` renders the dashboard interface. The dashboard's overview charts, inventory figures and sample activity are labeled illustrative and do not poll devices. Its Run Diagnosis form collects user-submitted telemetry and calls the real backend endpoint.

The form builds the three-section JSON request above and assigns one diagnosis ID to all sections. `frontend/src/services/diagnosisApi.js` submits JSON to `/api/diagnose`, validates the response shape and distinguishes validation, connection, HTTP and unexpected-response errors. The Vite development server proxies `/api` and `/health` to `http://127.0.0.1:8000`; no CORS or separate API URL is needed for the default local setup. Actual request and response data are held in frontend state; failed requests are not replaced with demo results.

The frontend and backend run independently. Production deployment requires serving the frontend and making the API reachable at the configured base path; this repository's Vite proxy is for development.

## Local installation and execution

Requirements: Python 3.10 or newer, Node.js 20.19+ or 22.12+, and npm.

### Backend

From the repository root, create a virtual environment and install the declared dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

On macOS/Linux, use `python3 -m venv .venv` and `source .venv/bin/activate`, then run the same pip and uvicorn commands.

Check the API at `http://127.0.0.1:8000/health` or open `http://127.0.0.1:8000/docs`.

### Frontend

In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite. To create and preview a production build:

```powershell
npm run build
npm run preview
```

Keep the FastAPI server running while using Run Diagnosis in the Vite development app.

## Tests

The backend test suite uses Python's standard `unittest` framework and comprehensively covers all five agents, orchestrator workflow, interoperability normalization, conflict preservation, evidence tracing, confidence heuristics, and end-to-end API scenarios.

To run the complete test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

The test suite contains **85 passing tests** across seven test modules:
- `backend/tests/test_interoperability.py`: Schema version validation, telemetry field alias normalization, unit scale parsing and conversion, conflicting alias rejection, incompatible unit rejection, and orchestrator error isolation.
- `backend/tests/test_end_to_end.py`: End-to-end scenario validations for all six hackathon scenarios (`normal_network`, `link_congestion`, `weak_wifi_signal`, `ethernet_interface_fault`, `dns_dhcp_failure`, `interoperability_failure`) and extended scenarios through the live ASGI FastAPI application.
- `backend/tests/test_orchestrator.py`: Multi-agent pipeline execution, partial stage failure handling without fabricated findings, cross-agent evidence references, and missing telemetry coverage gap detection.
- `backend/tests/test_performance_agent.py`: Metric thresholds for latency, jitter, packet loss, utilization, Wi-Fi RSSI (`rssi_dbm`), and DNS resolution latency (`dns_lookup_time_ms`).
- `backend/tests/test_infrastructure_agent.py`: Resource utilization, CRC errors, egress queue drops, device status, DHCP lease status (`dhcp_status`), link flaps (`link_flaps`), and interoperability status.
- `backend/tests/test_fault_correlation_agent.py`: Multi-agent correlation rules, root-cause hypothesis ranking, evidence traceability, and contradiction detection.
- `backend/tests/test_reporting_agent.py`: Diagnostic report generation, evidence citations, alternative explanations, and prioritized actionable recommendations.

All scenario tests post to the FastAPI `/api/diagnose` route through an in-process ASGI interface and do not require external network devices or live services.

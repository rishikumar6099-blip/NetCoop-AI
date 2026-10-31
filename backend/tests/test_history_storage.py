"""Unit and integration tests for SQLite persistent diagnosis history."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from backend import main
from backend.models.agent_message import AgentFinding, AgentMessage
from backend.models.correlation import ConfidenceBreakdown
from backend.models.diagnosis import AgentFailure, DiagnosisRequest, DiagnosisResponse
from backend.models.report import DiagnosticReport, Recommendation
from backend.orchestrator.diagnosis_orchestrator import MultiAgentOrchestrator
from backend.storage.repository import DiagnosisRepository


SCENARIOS_PATH = Path(__file__).parents[1] / "data" / "diagnosis_scenarios.json"


def asgi_request(
    method: str, path: str, payload: object | None = None, query_string: str = ""
) -> tuple[int, dict]:
    """Execute an ASGI request directly against FastAPI app."""
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    sent_messages = []
    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        sent_messages.append(message)

    headers = [
        (b"host", b"testserver"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    if payload is not None:
        headers.append((b"content-type", b"application/json"))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string.encode("ascii"),
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
        "state": {},
    }
    asyncio.run(main.app(scope, receive, send))

    status = next(
        msg["status"] for msg in sent_messages if msg["type"] == "http.response.start"
    )
    resp_body = b"".join(
        msg.get("body", b"")
        for msg in sent_messages
        if msg["type"] == "http.response.body"
    )
    data = json.loads(resp_body) if resp_body else {}
    return status, data


class HistoryStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(SCENARIOS_PATH, encoding="utf-8") as f:
            scenarios = json.load(f)
        cls.scenarios = {s["id"]: s for s in scenarios}

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_history.db"
        self.repo = DiagnosisRepository(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _run_scenario(self, scenario_id: str) -> tuple[DiagnosisRequest, DiagnosisResponse]:
        req_data = self.scenarios[scenario_id]["request"]
        req = DiagnosisRequest.model_validate(req_data)
        res = MultiAgentOrchestrator().run(req)
        return req, res

    def test_create_and_retrieve_diagnosis_record(self) -> None:
        req, res = self._run_scenario("router_infrastructure_overload")
        saved_id = self.repo.save_diagnosis(req, res)
        self.assertEqual(saved_id, req.diagnosis_id)

        record = self.repo.get_diagnosis(saved_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["diagnosis_id"], req.diagnosis_id)
        self.assertEqual(record["status"], "complete")
        self.assertEqual(record["incident_status"], "probable_cause")
        self.assertIn("RTR-O3", record["affected_device_ids"])
        self.assertEqual(record["review_status"], "unreviewed")
        self.assertIn("performance", record["agent_messages"])
        self.assertIn("infrastructure", record["agent_messages"])
        self.assertIn("connectivity", record["agent_messages"])
        self.assertGreater(len(record["findings"]), 0)
        self.assertEqual(record["request"]["performance"]["diagnosis_id"], req.diagnosis_id)
        self.assertEqual(record["response"]["diagnosis_id"], req.diagnosis_id)

    def test_persistence_across_repository_reinstantiation(self) -> None:
        req, res = self._run_scenario("ethernet_interface_fault")
        self.repo.save_diagnosis(req, res)

        # Drop original repo reference and instantiate a fresh repository on same file
        del self.repo
        fresh_repo = DiagnosisRepository(self.db_path)

        record = fresh_repo.get_diagnosis(req.diagnosis_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["diagnosis_id"], req.diagnosis_id)
        self.assertEqual(record["probable_root_cause"], res.diagnostic_report.probable_root_cause)
        self.assertEqual(record["confidence_score"], 0.70)
        self.assertEqual(record["confidence_category"], "moderate")
        self.assertIsNotNone(record["confidence_breakdown"])
        self.assertEqual(record["confidence_breakdown"]["final_score"], 0.70)

    def test_pagination(self) -> None:
        base_req, base_res = self._run_scenario("normal_network")
        for i in range(5):
            copied_req = base_req.model_copy(
                update={"performance": base_req.performance.model_copy(update={"diagnosis_id": f"paginated-{i}"})}
            )
            copied_res = base_res.model_copy(update={"diagnosis_id": f"paginated-{i}"})
            t_iso = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i)).isoformat()
            self.repo.save_diagnosis(copied_req, copied_res, created_at=t_iso)

        self.assertEqual(self.repo.count_diagnoses(), 5)

        page_1 = self.repo.list_diagnoses(limit=2, offset=0)
        self.assertEqual(page_1["total"], 5)
        self.assertEqual(len(page_1["items"]), 2)
        self.assertEqual(page_1["items"][0]["diagnosis_id"], "paginated-4")
        self.assertEqual(page_1["items"][1]["diagnosis_id"], "paginated-3")

        page_2 = self.repo.list_diagnoses(limit=2, offset=2)
        self.assertEqual(len(page_2["items"]), 2)
        self.assertEqual(page_2["items"][0]["diagnosis_id"], "paginated-2")
        self.assertEqual(page_2["items"][1]["diagnosis_id"], "paginated-1")

        page_3 = self.repo.list_diagnoses(limit=2, offset=4)
        self.assertEqual(len(page_3["items"]), 1)
        self.assertEqual(page_3["items"][0]["diagnosis_id"], "paginated-0")

        # Invalid pagination arguments raise ValueError
        with self.assertRaises(ValueError):
            self.repo.list_diagnoses(limit=0)
        with self.assertRaises(ValueError):
            self.repo.list_diagnoses(limit=101)
        with self.assertRaises(ValueError):
            self.repo.list_diagnoses(offset=-1)

    def test_newest_first_sorting(self) -> None:
        base_req, base_res = self._run_scenario("normal_network")
        timestamps = [
            ("sort-old", "2026-01-01T10:00:00+00:00"),
            ("sort-mid", "2026-01-01T12:00:00+00:00"),
            ("sort-new", "2026-01-01T14:00:00+00:00"),
        ]
        for diag_id, ts in timestamps:
            copied_req = base_req.model_copy(
                update={"performance": base_req.performance.model_copy(update={"diagnosis_id": diag_id})}
            )
            copied_res = base_res.model_copy(update={"diagnosis_id": diag_id})
            self.repo.save_diagnosis(copied_req, copied_res, created_at=ts)

        history = self.repo.list_diagnoses(limit=10, offset=0)
        retrieved_ids = [item["diagnosis_id"] for item in history["items"]]
        self.assertEqual(retrieved_ids, ["sort-new", "sort-mid", "sort-old"])

    def test_unknown_diagnosis_id_returns_none_and_api_404(self) -> None:
        self.assertIsNone(self.repo.get_diagnosis("does-not-exist"))

        status, body = asgi_request("GET", "/api/diagnoses/does-not-exist")
        self.assertEqual(status, 404)
        self.assertIn("not found", body.get("detail", "").lower())

    def test_database_constraints(self) -> None:
        req, res = self._run_scenario("weak_wifi_signal")
        self.repo.save_diagnosis(req, res)

        # Primary key constraint violation when replace=False
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.save_diagnosis(req, res, replace=False)

    def test_foreign_key_behavior(self) -> None:
        # Direct insertion into child table with invalid foreign key must fail
        with self.assertRaises(sqlite3.IntegrityError):
            with self.repo._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO agent_messages (
                        diagnosis_id, agent, status, summary, samples_analyzed, message_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("unregistered-diag-id", "perf", "complete", "summary", 1, "{}"),
                )

        # Cascading delete: deleting diagnosis removes child messages and findings
        req, res = self._run_scenario("link_congestion")
        diag_id = self.repo.save_diagnosis(req, res)

        with self.repo._connection() as conn:
            msg_count = conn.execute(
                "SELECT COUNT(*) FROM agent_messages WHERE diagnosis_id = ?", (diag_id,)
            ).fetchone()[0]
            find_count = conn.execute(
                "SELECT COUNT(*) FROM agent_findings WHERE diagnosis_id = ?", (diag_id,)
            ).fetchone()[0]
        self.assertGreater(msg_count, 0)
        self.assertGreater(find_count, 0)

        # Delete parent
        deleted = self.repo.delete_diagnosis(diag_id)
        self.assertTrue(deleted)

        # Children must be cascade-deleted
        with self.repo._connection() as conn:
            msg_count_after = conn.execute(
                "SELECT COUNT(*) FROM agent_messages WHERE diagnosis_id = ?", (diag_id,)
            ).fetchone()[0]
            find_count_after = conn.execute(
                "SELECT COUNT(*) FROM agent_findings WHERE diagnosis_id = ?", (diag_id,)
            ).fetchone()[0]
        self.assertEqual(msg_count_after, 0)
        self.assertEqual(find_count_after, 0)

    def test_correct_serialization_of_confidence_breakdown(self) -> None:
        req, res = self._run_scenario("ethernet_interface_fault")
        diag_id = self.repo.save_diagnosis(req, res)

        record = self.repo.get_diagnosis(diag_id)
        breakdown = record["confidence_breakdown"]
        self.assertIsNotNone(breakdown)
        self.assertEqual(breakdown["base_score"], 0.20)
        self.assertEqual(breakdown["domain_corroboration"], 0.24)
        self.assertEqual(breakdown["device_specificity"], 0.06)
        self.assertEqual(breakdown["severity_factor"], 0.12)
        self.assertEqual(breakdown["semantic_match"], 0.08)
        self.assertEqual(breakdown["telemetry_gap_penalty"], 0.00)
        self.assertEqual(breakdown["temporal_skew_penalty"], 0.00)
        self.assertEqual(breakdown["conflict_penalty"], 0.00)
        self.assertEqual(breakdown["final_score"], 0.70)
        self.assertIsInstance(breakdown["rationale"], list)
        self.assertGreater(len(breakdown["rationale"]), 0)

    def test_partial_diagnosis_persistence(self) -> None:
        req_data = self.scenarios["normal_network"]["request"]
        req = DiagnosisRequest.model_validate(req_data)
        # Create a partial response simulating an agent stage failure
        partial_res = DiagnosisResponse(
            diagnosis_id=req.diagnosis_id,
            status="partial",
            agent_messages={
                "performance": AgentMessage(
                    schema_version="1.0",
                    diagnosis_id=req.diagnosis_id,
                    agent="performance",
                    status="complete",
                    summary="Performance agent completed.",
                    samples_analyzed=1,
                    findings=[],
                )
            },
            failures=[
                AgentFailure(
                    stage="infrastructure",
                    error_type="TimeoutError",
                    message="Infrastructure probe timed out.",
                )
            ],
        )

        diag_id = self.repo.save_diagnosis(req, partial_res)
        record = self.repo.get_diagnosis(diag_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["status"], "partial")
        self.assertEqual(len(record["response"]["failures"]), 1)
        self.assertEqual(record["response"]["failures"][0]["stage"], "infrastructure")
        self.assertIn("performance", record["agent_messages"])

    def test_existing_diagnosis_api_response_compatibility_and_history_endpoints(self) -> None:
        # Set NETCOOP_DB_PATH to our test database during API calls
        old_env = os.environ.get("NETCOOP_DB_PATH")
        os.environ["NETCOOP_DB_PATH"] = str(self.db_path)
        try:
            req_payload = self.scenarios["dns_dhcp_failure"]["request"]
            post_status, post_data = asgi_request("POST", "/api/diagnose", req_payload)
            self.assertEqual(post_status, 200)
            self.assertEqual(post_data["status"], "complete")
            self.assertEqual(post_data["diagnosis_id"], req_payload["performance"]["diagnosis_id"])
            self.assertIn("diagnostic_report", post_data)
            self.assertEqual(post_data["diagnostic_report"]["confidence_score"], 0.70)

            # Check GET /api/diagnoses returns the saved diagnosis
            hist_status, hist_data = asgi_request("GET", "/api/diagnoses", query_string="limit=10&offset=0")
            self.assertEqual(hist_status, 200)
            self.assertGreaterEqual(hist_data["total"], 1)
            found = next(
                (item for item in hist_data["items"] if item["diagnosis_id"] == post_data["diagnosis_id"]),
                None,
            )
            self.assertIsNotNone(found)
            self.assertEqual(found["incident_status"], "probable_cause")
            self.assertEqual(found["confidence_score"], 0.70)
            self.assertEqual(found["review_status"], "unreviewed")

            # Check GET /api/diagnoses/{diagnosis_id} returns full record
            rec_status, rec_data = asgi_request("GET", f"/api/diagnoses/{post_data['diagnosis_id']}")
            self.assertEqual(rec_status, 200)
            self.assertEqual(rec_data["diagnosis_id"], post_data["diagnosis_id"])
            self.assertEqual(rec_data["status"], "complete")
            self.assertIsNotNone(rec_data["confidence_breakdown"])
            self.assertEqual(rec_data["confidence_breakdown"]["final_score"], 0.70)

            # Check pagination validation: limit=0 rejected with 422
            val_status, _ = asgi_request("GET", "/api/diagnoses", query_string="limit=0")
            self.assertEqual(val_status, 422)

        finally:
            if old_env is not None:
                os.environ["NETCOOP_DB_PATH"] = old_env
            else:
                os.environ.pop("NETCOOP_DB_PATH", None)


if __name__ == "__main__":
    unittest.main()

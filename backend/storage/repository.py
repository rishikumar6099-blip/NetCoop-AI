"""Persistent SQLite repository for NetCoop AI diagnosis history."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Generator

from backend.models.diagnosis import DiagnosisRequest, DiagnosisResponse


def get_default_db_path() -> Path:
    """Resolve sensible default database path across project locations."""
    env_path = os.environ.get("NETCOOP_DB_PATH")
    if env_path:
        return Path(env_path) if env_path != ":memory:" else env_path
    cwd = Path.cwd()
    if (cwd / "backend" / "data").exists():
        return cwd / "backend" / "data" / "netcoop.db"
    elif (cwd / "data").exists():
        return cwd / "data" / "netcoop.db"
    return Path(__file__).resolve().parent.parent / "data" / "netcoop.db"


MIGRATIONS: dict[int, str] = {
    1: """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS diagnoses (
        diagnosis_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL,
        incident_status TEXT,
        probable_root_cause TEXT,
        confidence_score REAL,
        confidence_category TEXT,
        confidence_breakdown_json TEXT,
        affected_devices_json TEXT NOT NULL DEFAULT '[]',
        affected_links_json TEXT NOT NULL DEFAULT '[]',
        affected_segments_json TEXT NOT NULL DEFAULT '[]',
        review_status TEXT NOT NULL DEFAULT 'unreviewed',
        request_json TEXT NOT NULL,
        response_json TEXT NOT NULL,
        correlation_json TEXT,
        report_json TEXT
    );

    CREATE TABLE IF NOT EXISTS agent_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        diagnosis_id TEXT NOT NULL REFERENCES diagnoses(diagnosis_id) ON DELETE CASCADE,
        agent TEXT NOT NULL,
        status TEXT NOT NULL,
        summary TEXT NOT NULL,
        samples_analyzed INTEGER NOT NULL DEFAULT 0,
        message_json TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS agent_findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        diagnosis_id TEXT NOT NULL REFERENCES diagnoses(diagnosis_id) ON DELETE CASCADE,
        agent TEXT NOT NULL,
        finding_index INTEGER NOT NULL,
        metric TEXT NOT NULL,
        value TEXT NOT NULL,
        unit TEXT NOT NULL,
        severity TEXT NOT NULL,
        assessment TEXT NOT NULL,
        device_id TEXT,
        observed_at TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_diagnoses_created_at ON diagnoses(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_agent_messages_diag ON agent_messages(diagnosis_id);
    CREATE INDEX IF NOT EXISTS idx_agent_findings_diag ON agent_findings(diagnosis_id);
    """
}


class DiagnosisRepository:
    """Thread-safe SQLite repository with WAL mode, foreign keys, and migration versioning."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._keepalive: sqlite3.Connection | None = None
        if db_path is not None:
            raw_path = str(db_path)
            if raw_path == ":memory:":
                import uuid
                self.db_path = f"file:mem_{uuid.uuid4().hex}?mode=memory&cache=shared"
                self._is_uri = True
                self._is_memory = True
                self._keepalive = sqlite3.connect(self.db_path, uri=True)
                self._keepalive.execute("PRAGMA foreign_keys = ON;")
            elif raw_path.startswith("file:"):
                self.db_path = raw_path
                self._is_uri = True
                self._is_memory = "mode=memory" in raw_path
                if self._is_memory:
                    self._keepalive = sqlite3.connect(self.db_path, uri=True)
                    self._keepalive.execute("PRAGMA foreign_keys = ON;")
            else:
                self.db_path = raw_path
                self._is_uri = False
                self._is_memory = False
        else:
            resolved = get_default_db_path()
            self.db_path = str(resolved)
            self._is_uri = False
            self._is_memory = False

        self._initialize_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provide a managed sqlite3 connection with transaction safety and foreign keys."""
        conn = sqlite3.connect(self.db_path, uri=self._is_uri)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        if not self._is_memory:
            conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_db(self) -> None:
        """Create database schema if missing, preserving existing data."""
        if not self._is_memory and not self._is_uri:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            cursor = conn.execute("SELECT version FROM schema_migrations")
            applied = {row[0] for row in cursor.fetchall()}
            for version in sorted(MIGRATIONS.keys()):
                if version not in applied:
                    conn.executescript(MIGRATIONS[version])
                    conn.execute(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                        (version, datetime.now(timezone.utc).isoformat()),
                    )

    def save_diagnosis(
        self,
        request: DiagnosisRequest | dict[str, Any],
        response: DiagnosisResponse | dict[str, Any],
        created_at: str | None = None,
        replace: bool = False,
    ) -> str:
        """Persist a complete or partial diagnosis and all child findings."""
        req_obj = (
            request
            if isinstance(request, DiagnosisRequest)
            else DiagnosisRequest.model_validate(request)
        )
        res_obj = (
            response
            if isinstance(response, DiagnosisResponse)
            else DiagnosisResponse.model_validate(response)
        )

        diag_id = res_obj.diagnosis_id
        timestamp = created_at or datetime.now(timezone.utc).isoformat()
        status = res_obj.status

        incident_status = None
        probable_root_cause = None
        confidence_score = None
        confidence_category = None
        confidence_breakdown_json = None
        affected_devices: list[str] = []
        affected_links: list[str] = []
        affected_segments: list[str] = []
        report_json = None

        if res_obj.diagnostic_report:
            rep = res_obj.diagnostic_report
            incident_status = rep.incident_status
            probable_root_cause = rep.probable_root_cause
            confidence_score = rep.confidence_score
            confidence_category = rep.confidence_category
            if rep.confidence_breakdown:
                confidence_breakdown_json = rep.confidence_breakdown.model_dump_json()
            affected_devices = rep.affected_device_ids
            affected_links = rep.affected_link_ids
            affected_segments = rep.affected_segment_ids
            report_json = rep.model_dump_json()

        correlation_json = None
        if res_obj.correlation_result:
            correlation_json = res_obj.correlation_result.model_dump_json()
            if not confidence_breakdown_json and res_obj.correlation_result.hypotheses:
                top_hyp = res_obj.correlation_result.hypotheses[0]
                if top_hyp.confidence_breakdown:
                    confidence_breakdown_json = (
                        top_hyp.confidence_breakdown.model_dump_json()
                    )

        with self._connection() as conn:
            if replace:
                conn.execute(
                    "DELETE FROM diagnoses WHERE diagnosis_id = ?", (diag_id,)
                )

            conn.execute(
                """
                INSERT INTO diagnoses (
                    diagnosis_id, created_at, status, incident_status,
                    probable_root_cause, confidence_score, confidence_category,
                    confidence_breakdown_json, affected_devices_json,
                    affected_links_json, affected_segments_json, review_status,
                    request_json, response_json, correlation_json, report_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    diag_id,
                    timestamp,
                    status,
                    incident_status,
                    probable_root_cause,
                    confidence_score,
                    confidence_category,
                    confidence_breakdown_json,
                    json.dumps(affected_devices),
                    json.dumps(affected_links),
                    json.dumps(affected_segments),
                    "unreviewed",
                    req_obj.model_dump_json(),
                    res_obj.model_dump_json(),
                    correlation_json,
                    report_json,
                ),
            )

            for agent_name, agent_msg in res_obj.agent_messages.items():
                conn.execute(
                    """
                    INSERT INTO agent_messages (
                        diagnosis_id, agent, status, summary, samples_analyzed, message_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        diag_id,
                        agent_name,
                        agent_msg.status,
                        agent_msg.summary,
                        agent_msg.samples_analyzed,
                        agent_msg.model_dump_json(),
                    ),
                )

                for idx, finding in enumerate(agent_msg.findings):
                    conn.execute(
                        """
                        INSERT INTO agent_findings (
                            diagnosis_id, agent, finding_index, metric, value,
                            unit, severity, assessment, device_id, observed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            diag_id,
                            agent_name,
                            idx,
                            finding.metric,
                            str(finding.value),
                            finding.unit,
                            finding.severity,
                            finding.assessment,
                            finding.device_id,
                            (
                                finding.observed_at.isoformat()
                                if finding.observed_at
                                else None
                            ),
                        ),
                    )

        return diag_id

    def get_diagnosis(self, diagnosis_id: str) -> dict[str, Any] | None:
        """Fetch complete stored diagnosis by ID, or None if not found."""
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM diagnoses WHERE diagnosis_id = ?", (diagnosis_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            diag = dict(row)

            # Fetch agent messages
            msg_cursor = conn.execute(
                "SELECT * FROM agent_messages WHERE diagnosis_id = ? ORDER BY id ASC",
                (diagnosis_id,),
            )
            agent_messages = {}
            for msg_row in msg_cursor.fetchall():
                agent_messages[msg_row["agent"]] = json.loads(msg_row["message_json"])

            # Fetch agent findings
            finding_cursor = conn.execute(
                "SELECT * FROM agent_findings WHERE diagnosis_id = ? ORDER BY id ASC",
                (diagnosis_id,),
            )
            findings = [dict(f_row) for f_row in finding_cursor.fetchall()]

            breakdown = None
            if diag.get("confidence_breakdown_json"):
                breakdown = json.loads(diag["confidence_breakdown_json"])

            return {
                "diagnosis_id": diag["diagnosis_id"],
                "created_at": diag["created_at"],
                "status": diag["status"],
                "incident_status": diag["incident_status"],
                "probable_root_cause": diag["probable_root_cause"],
                "confidence_score": diag["confidence_score"],
                "confidence_category": diag["confidence_category"],
                "confidence_breakdown": breakdown,
                "affected_device_ids": json.loads(diag["affected_devices_json"]),
                "affected_link_ids": json.loads(diag["affected_links_json"]),
                "affected_segment_ids": json.loads(diag["affected_segments_json"]),
                "review_status": diag["review_status"],
                "request": json.loads(diag["request_json"]),
                "response": json.loads(diag["response_json"]),
                "agent_messages": agent_messages,
                "findings": findings,
                "correlation_result": (
                    json.loads(diag["correlation_json"])
                    if diag.get("correlation_json")
                    else None
                ),
                "diagnostic_report": (
                    json.loads(diag["report_json"])
                    if diag.get("report_json")
                    else None
                ),
            }

    def list_diagnoses(
        self, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        """Fetch newest-first paginated list of diagnosis summaries."""
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        with self._connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM diagnoses").fetchone()[0]
            cursor = conn.execute(
                """
                SELECT diagnosis_id, created_at, status, incident_status,
                       probable_root_cause, confidence_score, confidence_category,
                       affected_devices_json, review_status
                FROM diagnoses
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            items = []
            for row in cursor.fetchall():
                item = dict(row)
                items.append(
                    {
                        "diagnosis_id": item["diagnosis_id"],
                        "created_at": item["created_at"],
                        "status": item["status"],
                        "incident_status": item["incident_status"],
                        "probable_root_cause": item["probable_root_cause"],
                        "confidence_score": item["confidence_score"],
                        "confidence_category": item["confidence_category"],
                        "affected_device_ids": json.loads(
                            item["affected_devices_json"]
                        ),
                        "review_status": item["review_status"],
                    }
                )

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": items,
            }

    def delete_diagnosis(self, diagnosis_id: str) -> bool:
        """Delete a diagnosis and cascade to its messages and findings."""
        with self._connection() as conn:
            cursor = conn.execute(
                "DELETE FROM diagnoses WHERE diagnosis_id = ?", (diagnosis_id,)
            )
            return cursor.rowcount > 0

    def count_diagnoses(self) -> int:
        """Count total stored diagnoses."""
        with self._connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM diagnoses").fetchone()[0]

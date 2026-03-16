import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

from app.models.case import (
    AdapterRun,
    AdapterRunStatus,
    Case,
    CaseStatus,
    Evidence,
    Finding,
    FindingType,
    Note,
    Severity,
    Target,
    TargetType,
)


class Database:
    def __init__(self):
        self.conn: sqlite3.Connection | None = None
        self.db_path: str | None = None

    def initialize(self, db_path: str = "osint_platform.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT,
                status TEXT
            );
            CREATE TABLE IF NOT EXISTS targets (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                type TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT,
                notes TEXT,
                tags TEXT
            );
            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                adapter_name TEXT,
                finding_type TEXT,
                title TEXT,
                description TEXT,
                data TEXT,
                severity TEXT,
                source_url TEXT,
                source_name TEXT,
                collected_at TEXT,
                tags TEXT
            );
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                content TEXT,
                created_at TEXT,
                tags TEXT
            );
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                finding_id TEXT,
                file_path TEXT,
                description TEXT,
                collected_at TEXT
            );
            CREATE TABLE IF NOT EXISTS adapter_runs (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                adapter_name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                finding_count INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0.0,
                error_message TEXT DEFAULT ''
            );
        """)
        self.conn.commit()

    def save_case(self, case: Case):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO cases (id, name, description, tags, created_at, updated_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                case.id,
                case.name,
                case.description,
                json.dumps(case.tags),
                case.created_at.isoformat(),
                case.updated_at.isoformat(),
                case.status.value,
            ),
        )
        for target in case.targets:
            self.save_target(target, case.id)
        for finding in case.findings:
            self.save_finding(finding, case.id)
        for note in case.notes:
            self._save_note(note)
        for ev in case.evidence:
            self._save_evidence(ev)
        self.conn.commit()

    def _save_note(self, note: Note):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO notes (id, case_id, content, created_at, tags)
               VALUES (?, ?, ?, ?, ?)""",
            (note.id, note.case_id, note.content, note.created_at.isoformat(), json.dumps(note.tags)),
        )

    def _save_evidence(self, evidence: Evidence):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO evidence (id, case_id, finding_id, file_path, description, collected_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                evidence.id,
                evidence.case_id,
                evidence.finding_id,
                evidence.file_path,
                evidence.description,
                evidence.collected_at.isoformat(),
            ),
        )

    def save_target(self, target: Target, case_id: str):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO targets (id, case_id, type, value, created_at, notes, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                target.id,
                case_id,
                target.type.value,
                target.value,
                target.created_at.isoformat(),
                json.dumps(target.notes),
                json.dumps(target.tags),
            ),
        )
        self.conn.commit()

    def save_finding(self, finding: Finding, case_id: str):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO findings
               (id, case_id, target_id, adapter_name, finding_type, title, description,
                data, severity, source_url, source_name, collected_at, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                finding.id,
                case_id,
                finding.target_id,
                finding.adapter_name,
                finding.finding_type.value,
                finding.title,
                finding.description,
                json.dumps(finding.data),
                finding.severity.value,
                finding.source_url,
                finding.source_name,
                finding.collected_at.isoformat(),
                json.dumps(finding.tags),
            ),
        )
        self.conn.commit()

    def load_case(self, case_id: str) -> Case:
        cur = self.conn.cursor()
        row = cur.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if row is None:
            raise ValueError(f"Case {case_id} not found")
        return self._build_case(dict(row))

    def list_cases(self) -> list[Case]:
        cur = self.conn.cursor()
        rows = cur.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
        return [self._build_case(dict(r)) for r in rows]

    _CHILD_TABLES = ("targets", "findings", "notes", "evidence", "adapter_runs")

    def delete_case(self, case_id: str):
        cur = self.conn.cursor()
        for table in self._CHILD_TABLES:
            cur.execute(f"DELETE FROM {table} WHERE case_id = ?", (case_id,))  # noqa: S608
        cur.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        self.conn.commit()

    def get_findings_for_case(self, case_id: str) -> list[Finding]:
        cur = self.conn.cursor()
        rows = cur.execute("SELECT * FROM findings WHERE case_id = ?", (case_id,)).fetchall()
        return [self._row_to_finding(dict(r)) for r in rows]

    def update_case_timestamp(self, case_id: str) -> None:
        """Update only the updated_at column without rewriting the full case."""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE cases SET updated_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), case_id),
        )
        self.conn.commit()

    def save_adapter_run(self, run: AdapterRun) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO adapter_runs
               (id, case_id, target_id, adapter_name, status, started_at,
                completed_at, finding_count, duration_seconds, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run.id,
                run.case_id,
                run.target_id,
                run.adapter_name,
                run.status.value,
                run.started_at.isoformat(),
                run.completed_at.isoformat() if run.completed_at else None,
                run.finding_count,
                run.duration_seconds,
                run.error_message,
            ),
        )
        self.conn.commit()

    def get_adapter_runs_for_case(self, case_id: str) -> list[AdapterRun]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM adapter_runs WHERE case_id = ? ORDER BY started_at ASC", (case_id,)
        ).fetchall()
        return [self._row_to_adapter_run(dict(r)) for r in rows]

    @staticmethod
    def _row_to_adapter_run(row: dict) -> AdapterRun:
        completed_at = row.get("completed_at")
        return AdapterRun(
            id=row["id"],
            case_id=row["case_id"],
            target_id=row["target_id"],
            adapter_name=row["adapter_name"],
            status=AdapterRunStatus(row["status"]),
            started_at=row["started_at"],
            completed_at=completed_at if completed_at else None,
            finding_count=row["finding_count"] or 0,
            duration_seconds=row["duration_seconds"] or 0.0,
            error_message=row["error_message"] or "",
        )

    def _build_case(self, row: dict) -> Case:
        cur = self.conn.cursor()
        case_id = row["id"]

        target_rows = cur.execute("SELECT * FROM targets WHERE case_id = ?", (case_id,)).fetchall()
        targets = [self._row_to_target(dict(r)) for r in target_rows]

        finding_rows = cur.execute("SELECT * FROM findings WHERE case_id = ?", (case_id,)).fetchall()
        findings = [self._row_to_finding(dict(r)) for r in finding_rows]

        note_rows = cur.execute("SELECT * FROM notes WHERE case_id = ?", (case_id,)).fetchall()
        notes = [
            Note(
                id=r["id"],
                case_id=r["case_id"],
                content=r["content"],
                created_at=r["created_at"],
                tags=json.loads(r["tags"] or "[]"),
            )
            for r in note_rows
        ]

        evidence_rows = cur.execute("SELECT * FROM evidence WHERE case_id = ?", (case_id,)).fetchall()
        evidence = [
            Evidence(
                id=r["id"],
                case_id=r["case_id"],
                finding_id=r["finding_id"],
                file_path=r["file_path"],
                description=r["description"],
                collected_at=r["collected_at"],
            )
            for r in evidence_rows
        ]

        return Case(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            tags=json.loads(row["tags"] or "[]"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            status=CaseStatus(row["status"]),
            targets=targets,
            findings=findings,
            notes=notes,
            evidence=evidence,
            adapter_runs=self.get_adapter_runs_for_case(case_id),
        )

    def _row_to_target(self, row: dict) -> Target:
        return Target(
            id=row["id"],
            type=TargetType(row["type"]),
            value=row["value"],
            created_at=row["created_at"],
            notes=json.loads(row["notes"] or "[]"),
            tags=json.loads(row["tags"] or "[]"),
        )

    def _row_to_finding(self, row: dict) -> Finding:
        return Finding(
            id=row["id"],
            target_id=row["target_id"],
            adapter_name=row["adapter_name"],
            finding_type=FindingType(row["finding_type"]),
            title=row["title"],
            description=row["description"],
            data=json.loads(row["data"] or "{}"),
            severity=Severity(row["severity"]),
            source_url=row["source_url"] or "",
            source_name=row["source_name"] or "",
            collected_at=row["collected_at"],
            tags=json.loads(row["tags"] or "[]"),
        )

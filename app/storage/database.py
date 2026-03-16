import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

from app.models.case import (
    ArtifactLinkType,
    AdapterRun,
    AdapterRunStatus,
    Case,
    CaseStatus,
    Entity,
    EntityKind,
    EvidenceAttachment,
    EvidenceAttachmentType,
    Evidence,
    Finding,
    FindingDecisionState,
    FindingEvidenceLink,
    FindingReviewState,
    FindingType,
    LeadLifecycleState,
    LeadPriority,
    LeadProfile,
    MissionTaskLink,
    MissionIntake,
    Note,
    SavedSearch,
    SearchIntent,
    SearchProvider,
    SupportLinkOrigin,
    SourceReliability,
    Severity,
    Target,
    TargetType,
    WorkflowStage,
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
        self._ensure_schema()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                mission_intake_json TEXT,
                workflow_stage TEXT DEFAULT 'INTAKE',
                workflow_stage_note TEXT DEFAULT '',
                workflow_stage_updated_at TEXT,
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
                adapter_run_id TEXT,
                review_state TEXT DEFAULT 'NEW',
                analyst_note TEXT DEFAULT '',
                decision_state TEXT DEFAULT 'PENDING_REVIEW',
                decision_confidence REAL DEFAULT 0.5,
                decision_rationale TEXT DEFAULT '',
                decision_updated_at TEXT,
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
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                value TEXT NOT NULL,
                display_name TEXT,
                metadata TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                entity_id TEXT,
                finding_id TEXT,
                file_path TEXT,
                description TEXT,
                source_reliability TEXT DEFAULT 'UNVERIFIED',
                raw_json_data TEXT,
                normalized_summary TEXT,
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
            CREATE TABLE IF NOT EXISTS saved_searches (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                target_id TEXT,
                title TEXT NOT NULL,
                provider TEXT NOT NULL,
                intent TEXT NOT NULL,
                query TEXT NOT NULL,
                explanation TEXT,
                tags TEXT,
                analyst_note TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                canonical_value TEXT NOT NULL,
                display_label TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                priority TEXT NOT NULL,
                owner TEXT,
                confidence_score REAL,
                context_summary TEXT,
                blocker_note TEXT,
                why_it_matters TEXT,
                linked_target_ids TEXT,
                linked_entity_ids TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT,
                last_activity_at TEXT
            );
            CREATE TABLE IF NOT EXISTS mission_task_links (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                note TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS finding_evidence_links (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                finding_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                origin TEXT NOT NULL,
                support_confidence REAL DEFAULT 0.5,
                rationale TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS evidence_attachments (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                attachment_type TEXT NOT NULL,
                source_url TEXT,
                media_title TEXT,
                media_type TEXT,
                file_path TEXT,
                source_platform TEXT,
                provenance_note TEXT,
                metadata_json TEXT,
                captured_at TEXT,
                created_at TEXT,
                updated_at TEXT
            );
        """)
        self.conn.commit()

    def _ensure_schema(self) -> None:
        """Apply lightweight migrations for existing local databases."""
        cur = self.conn.cursor()

        case_columns = {
            row["name"]
            for row in cur.execute("PRAGMA table_info(cases)").fetchall()
        }
        if "mission_intake_json" not in case_columns:
            cur.execute("ALTER TABLE cases ADD COLUMN mission_intake_json TEXT")
        if "workflow_stage" not in case_columns:
            cur.execute("ALTER TABLE cases ADD COLUMN workflow_stage TEXT DEFAULT 'INTAKE'")
        if "workflow_stage_note" not in case_columns:
            cur.execute("ALTER TABLE cases ADD COLUMN workflow_stage_note TEXT DEFAULT ''")
        if "workflow_stage_updated_at" not in case_columns:
            cur.execute("ALTER TABLE cases ADD COLUMN workflow_stage_updated_at TEXT")

        default_intake_json = json.dumps(MissionIntake().model_dump(mode="json"))
        cur.execute(
            "UPDATE cases SET mission_intake_json = ? WHERE mission_intake_json IS NULL OR mission_intake_json = ''",
            (default_intake_json,),
        )
        cur.execute(
            "UPDATE cases SET workflow_stage = 'INTAKE' WHERE workflow_stage IS NULL OR workflow_stage = ''"
        )
        cur.execute(
            "UPDATE cases SET workflow_stage_note = '' WHERE workflow_stage_note IS NULL"
        )
        cur.execute(
            "UPDATE cases SET workflow_stage_updated_at = updated_at WHERE workflow_stage_updated_at IS NULL OR workflow_stage_updated_at = ''"
        )

        finding_columns = {
            row["name"]
            for row in cur.execute("PRAGMA table_info(findings)").fetchall()
        }
        if "adapter_run_id" not in finding_columns:
            cur.execute("ALTER TABLE findings ADD COLUMN adapter_run_id TEXT")
        if "review_state" not in finding_columns:
            cur.execute("ALTER TABLE findings ADD COLUMN review_state TEXT DEFAULT 'NEW'")
        if "analyst_note" not in finding_columns:
            cur.execute("ALTER TABLE findings ADD COLUMN analyst_note TEXT DEFAULT ''")
        if "decision_state" not in finding_columns:
            cur.execute(
                "ALTER TABLE findings ADD COLUMN decision_state TEXT DEFAULT 'PENDING_REVIEW'"
            )
        if "decision_confidence" not in finding_columns:
            cur.execute(
                "ALTER TABLE findings ADD COLUMN decision_confidence REAL DEFAULT 0.5"
            )
        if "decision_rationale" not in finding_columns:
            cur.execute("ALTER TABLE findings ADD COLUMN decision_rationale TEXT DEFAULT ''")
        if "decision_updated_at" not in finding_columns:
            cur.execute("ALTER TABLE findings ADD COLUMN decision_updated_at TEXT")

        evidence_columns = {
            row["name"]
            for row in cur.execute("PRAGMA table_info(evidence)").fetchall()
        }
        if "entity_id" not in evidence_columns:
            cur.execute("ALTER TABLE evidence ADD COLUMN entity_id TEXT")
        if "source_reliability" not in evidence_columns:
            cur.execute(
                "ALTER TABLE evidence ADD COLUMN source_reliability TEXT DEFAULT 'UNVERIFIED'"
            )
        if "raw_json_data" not in evidence_columns:
            cur.execute("ALTER TABLE evidence ADD COLUMN raw_json_data TEXT")
        if "normalized_summary" not in evidence_columns:
            cur.execute("ALTER TABLE evidence ADD COLUMN normalized_summary TEXT")

        cur.execute(
            "UPDATE evidence SET source_reliability = 'UNVERIFIED' WHERE source_reliability IS NULL OR source_reliability = ''"
        )
        cur.execute(
            "UPDATE evidence SET raw_json_data = '{}' WHERE raw_json_data IS NULL OR raw_json_data = ''"
        )
        cur.execute(
            "UPDATE evidence SET normalized_summary = '' WHERE normalized_summary IS NULL"
        )

        # Ensure pre-migration rows get explicit triage defaults.
        cur.execute(
            "UPDATE findings SET review_state = 'NEW' WHERE review_state IS NULL OR review_state = ''"
        )
        cur.execute(
            "UPDATE findings SET analyst_note = '' WHERE analyst_note IS NULL"
        )
        cur.execute(
            "UPDATE findings SET decision_state = 'PENDING_REVIEW' WHERE decision_state IS NULL OR decision_state = ''"
        )
        cur.execute(
            "UPDATE findings SET decision_confidence = 0.5 WHERE decision_confidence IS NULL"
        )
        cur.execute(
            "UPDATE findings SET decision_rationale = '' WHERE decision_rationale IS NULL"
        )
        cur.execute(
            "UPDATE findings SET decision_updated_at = collected_at WHERE decision_updated_at IS NULL OR decision_updated_at = ''"
        )

        attachment_table_exists = cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='evidence_attachments'"
        ).fetchone()
        if not attachment_table_exists:
            cur.execute(
                """
                CREATE TABLE evidence_attachments (
                    id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    attachment_type TEXT NOT NULL,
                    source_url TEXT,
                    media_title TEXT,
                    media_type TEXT,
                    file_path TEXT,
                    source_platform TEXT,
                    provenance_note TEXT,
                    metadata_json TEXT,
                    captured_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
        cur.execute(
            """
            UPDATE evidence_attachments
            SET metadata_json = '{}'
            WHERE metadata_json IS NULL OR metadata_json = ''
            """
        )

        self.conn.commit()

    def save_case(self, case: Case):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO cases
               (id, name, description, mission_intake_json, workflow_stage,
                workflow_stage_note, workflow_stage_updated_at, tags, created_at, updated_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                case.id,
                case.name,
                case.description,
                json.dumps(case.mission_intake.model_dump(mode="json")),
                case.workflow_stage.value,
                case.workflow_stage_note,
                case.workflow_stage_updated_at.isoformat(),
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
        for entity in case.entities:
            self.save_entity(entity)
        for ev in case.evidence:
            self._save_evidence(ev)
        for search in case.saved_searches:
            self.save_saved_search(search)
        for lead in case.leads:
            self.save_lead(lead)
        for link in case.task_links:
            self.save_mission_task_link(link)
        for link in case.finding_evidence_links:
            self.save_finding_evidence_link(link)
        for attachment in case.evidence_attachments:
            self.save_evidence_attachment(attachment)
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
            """INSERT OR REPLACE INTO evidence
               (id, case_id, entity_id, finding_id, file_path, description,
                source_reliability, raw_json_data, normalized_summary, collected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                evidence.id,
                evidence.case_id,
                evidence.entity_id,
                evidence.finding_id,
                evidence.file_path,
                evidence.description,
                evidence.source_reliability.value,
                json.dumps(evidence.raw_json_data),
                evidence.normalized_summary,
                evidence.collected_at.isoformat(),
            ),
        )

    def save_evidence(self, evidence: Evidence) -> None:
        self._save_evidence(evidence)
        self.conn.commit()

    def save_entity(self, entity: Entity) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO entities
               (id, case_id, kind, value, display_name, metadata, tags, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entity.id,
                entity.case_id,
                entity.kind.value,
                entity.value,
                entity.display_name,
                json.dumps(entity.metadata),
                json.dumps(entity.tags),
                entity.created_at.isoformat(),
                entity.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_entities_for_case(self, case_id: str) -> list[Entity]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM entities WHERE case_id = ? ORDER BY created_at DESC",
            (case_id,),
        ).fetchall()
        return [self._row_to_entity(dict(r)) for r in rows]

    def delete_entity(self, entity_id: str, case_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM entities WHERE id = ? AND case_id = ?",
            (entity_id, case_id),
        )
        self.conn.commit()

    def get_evidence_for_case(self, case_id: str) -> list[Evidence]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM evidence WHERE case_id = ? ORDER BY collected_at DESC",
            (case_id,),
        ).fetchall()
        return [self._row_to_evidence(dict(r)) for r in rows]

    def delete_evidence(self, evidence_id: str, case_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM evidence WHERE id = ? AND case_id = ?",
            (evidence_id, case_id),
        )
        self.conn.commit()

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
               (id, case_id, target_id, adapter_name, adapter_run_id, review_state, analyst_note,
                decision_state, decision_confidence, decision_rationale, decision_updated_at,
                finding_type, title, description,
                data, severity, source_url, source_name, collected_at, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                finding.id,
                case_id,
                finding.target_id,
                finding.adapter_name,
                finding.adapter_run_id,
                finding.review_state.value,
                finding.analyst_note,
                finding.decision_state.value,
                finding.decision_confidence,
                finding.decision_rationale,
                finding.decision_updated_at.isoformat(),
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

    def update_finding_triage(
        self,
        finding_id: str,
        review_state: FindingReviewState,
        analyst_note: str = "",
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """UPDATE findings
               SET review_state = ?, analyst_note = ?, decision_updated_at = ?
               WHERE id = ?""",
            (review_state.value, analyst_note, datetime.now(timezone.utc).isoformat(), finding_id),
        )
        self.conn.commit()

    def update_finding_decision(
        self,
        finding_id: str,
        decision_state: FindingDecisionState,
        decision_confidence: float,
        decision_rationale: str = "",
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """UPDATE findings
               SET decision_state = ?, decision_confidence = ?, decision_rationale = ?, decision_updated_at = ?
               WHERE id = ?""",
            (
                decision_state.value,
                decision_confidence,
                decision_rationale,
                datetime.now(timezone.utc).isoformat(),
                finding_id,
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

    _CHILD_TABLES = (
        "targets",
        "findings",
        "notes",
        "entities",
        "evidence",
        "adapter_runs",
        "saved_searches",
        "leads",
        "mission_task_links",
        "finding_evidence_links",
        "evidence_attachments",
    )

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

    def save_saved_search(self, search: SavedSearch) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO saved_searches
               (id, case_id, target_id, title, provider, intent, query, explanation,
                tags, analyst_note, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                search.id,
                search.case_id,
                search.target_id,
                search.title,
                search.provider.value,
                search.intent.value,
                search.query,
                search.explanation,
                json.dumps(search.tags),
                search.analyst_note,
                search.created_at.isoformat(),
                search.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_saved_searches_for_case(self, case_id: str) -> list[SavedSearch]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM saved_searches WHERE case_id = ? ORDER BY created_at DESC",
            (case_id,),
        ).fetchall()
        return [self._row_to_saved_search(dict(r)) for r in rows]

    def delete_saved_search(self, search_id: str, case_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM saved_searches WHERE id = ? AND case_id = ?",
            (search_id, case_id),
        )
        self.conn.commit()

    def save_lead(self, lead: LeadProfile) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO leads
               (id, case_id, kind, canonical_value, display_label, lifecycle_state, priority,
                owner, confidence_score, context_summary, blocker_note, why_it_matters,
                linked_target_ids, linked_entity_ids, tags, created_at, updated_at, last_activity_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                lead.id,
                lead.case_id,
                lead.kind,
                lead.canonical_value,
                lead.display_label,
                lead.lifecycle_state.value,
                lead.priority.value,
                lead.owner,
                lead.confidence_score,
                lead.context_summary,
                lead.blocker_note,
                lead.why_it_matters,
                json.dumps(lead.linked_target_ids),
                json.dumps(lead.linked_entity_ids),
                json.dumps(lead.tags),
                lead.created_at.isoformat(),
                lead.updated_at.isoformat(),
                lead.last_activity_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_leads_for_case(self, case_id: str) -> list[LeadProfile]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM leads WHERE case_id = ? ORDER BY updated_at DESC",
            (case_id,),
        ).fetchall()
        return [self._row_to_lead(dict(r)) for r in rows]

    def delete_lead(self, lead_id: str, case_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM leads WHERE id = ? AND case_id = ?", (lead_id, case_id))
        self.conn.commit()

    def save_mission_task_link(self, link: MissionTaskLink) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO mission_task_links
               (id, case_id, task_id, artifact_type, artifact_id, note, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                link.id,
                link.case_id,
                link.task_id,
                link.artifact_type.value,
                link.artifact_id,
                link.note,
                link.created_at.isoformat(),
                link.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_task_links_for_case(self, case_id: str) -> list[MissionTaskLink]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM mission_task_links WHERE case_id = ? ORDER BY created_at DESC",
            (case_id,),
        ).fetchall()
        return [self._row_to_task_link(dict(r)) for r in rows]

    def delete_task_link(self, link_id: str, case_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM mission_task_links WHERE id = ? AND case_id = ?", (link_id, case_id))
        self.conn.commit()

    def delete_task_links_by_task(self, case_id: str, task_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM mission_task_links WHERE case_id = ? AND task_id = ?",
            (case_id, task_id),
        )
        self.conn.commit()

    def save_finding_evidence_link(self, link: FindingEvidenceLink) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO finding_evidence_links
               (id, case_id, finding_id, evidence_id, origin, support_confidence, rationale, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                link.id,
                link.case_id,
                link.finding_id,
                link.evidence_id,
                link.origin.value,
                link.support_confidence,
                link.rationale,
                link.created_at.isoformat(),
                link.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_finding_evidence_links_for_case(self, case_id: str) -> list[FindingEvidenceLink]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM finding_evidence_links WHERE case_id = ? ORDER BY created_at DESC",
            (case_id,),
        ).fetchall()
        return [self._row_to_finding_evidence_link(dict(r)) for r in rows]

    def delete_finding_evidence_link(self, link_id: str, case_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM finding_evidence_links WHERE id = ? AND case_id = ?",
            (link_id, case_id),
        )
        self.conn.commit()

    def save_evidence_attachment(self, attachment: EvidenceAttachment) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO evidence_attachments
               (id, case_id, evidence_id, attachment_type, source_url, media_title, media_type,
                file_path, source_platform, provenance_note, metadata_json, captured_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                attachment.id,
                attachment.case_id,
                attachment.evidence_id,
                attachment.attachment_type.value,
                attachment.source_url,
                attachment.media_title,
                attachment.media_type,
                attachment.file_path,
                attachment.source_platform,
                attachment.provenance_note,
                json.dumps(attachment.metadata),
                attachment.captured_at.isoformat(),
                attachment.created_at.isoformat(),
                attachment.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_evidence_attachments_for_case(self, case_id: str) -> list[EvidenceAttachment]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM evidence_attachments WHERE case_id = ? ORDER BY captured_at DESC",
            (case_id,),
        ).fetchall()
        return [self._row_to_evidence_attachment(dict(r)) for r in rows]

    def get_evidence_attachments_for_evidence(
        self,
        case_id: str,
        evidence_id: str,
    ) -> list[EvidenceAttachment]:
        cur = self.conn.cursor()
        rows = cur.execute(
            """
            SELECT * FROM evidence_attachments
            WHERE case_id = ? AND evidence_id = ?
            ORDER BY captured_at DESC
            """,
            (case_id, evidence_id),
        ).fetchall()
        return [self._row_to_evidence_attachment(dict(r)) for r in rows]

    def delete_evidence_attachment(self, attachment_id: str, case_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM evidence_attachments WHERE id = ? AND case_id = ?",
            (attachment_id, case_id),
        )
        self.conn.commit()

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

    @staticmethod
    def _row_to_saved_search(row: dict) -> SavedSearch:
        return SavedSearch(
            id=row["id"],
            case_id=row["case_id"],
            target_id=row["target_id"],
            title=row["title"],
            provider=SearchProvider(row["provider"]),
            intent=SearchIntent(row["intent"]),
            query=row["query"],
            explanation=row["explanation"] or "",
            tags=json.loads(row["tags"] or "[]"),
            analyst_note=row["analyst_note"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_entity(row: dict) -> Entity:
        return Entity(
            id=row["id"],
            case_id=row["case_id"],
            kind=EntityKind(row["kind"]),
            value=row["value"],
            display_name=row["display_name"] or "",
            metadata=json.loads(row["metadata"] or "{}"),
            tags=json.loads(row["tags"] or "[]"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_evidence(row: dict) -> Evidence:
        return Evidence(
            id=row["id"],
            case_id=row["case_id"],
            entity_id=row.get("entity_id"),
            finding_id=row["finding_id"],
            file_path=row["file_path"] or "",
            description=row["description"] or "",
            source_reliability=SourceReliability(
                row.get("source_reliability") or "UNVERIFIED"
            ),
            raw_json_data=json.loads(row.get("raw_json_data") or "{}"),
            normalized_summary=row.get("normalized_summary") or "",
            collected_at=row["collected_at"],
        )

    @staticmethod
    def _row_to_lead(row: dict) -> LeadProfile:
        return LeadProfile(
            id=row["id"],
            case_id=row["case_id"],
            kind=row["kind"],
            canonical_value=row["canonical_value"],
            display_label=row["display_label"],
            lifecycle_state=LeadLifecycleState(row["lifecycle_state"]),
            priority=LeadPriority(row["priority"]),
            owner=row["owner"] or "",
            confidence_score=row["confidence_score"] if row["confidence_score"] is not None else 0.5,
            context_summary=row["context_summary"] or "",
            blocker_note=row["blocker_note"] or "",
            why_it_matters=row["why_it_matters"] or "",
            linked_target_ids=json.loads(row["linked_target_ids"] or "[]"),
            linked_entity_ids=json.loads(row["linked_entity_ids"] or "[]"),
            tags=json.loads(row["tags"] or "[]"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_activity_at=row["last_activity_at"] or row["updated_at"],
        )

    @staticmethod
    def _row_to_task_link(row: dict) -> MissionTaskLink:
        return MissionTaskLink(
            id=row["id"],
            case_id=row["case_id"],
            task_id=row["task_id"],
            artifact_type=ArtifactLinkType(row["artifact_type"]),
            artifact_id=row["artifact_id"],
            note=row["note"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_finding_evidence_link(row: dict) -> FindingEvidenceLink:
        return FindingEvidenceLink(
            id=row["id"],
            case_id=row["case_id"],
            finding_id=row["finding_id"],
            evidence_id=row["evidence_id"],
            origin=SupportLinkOrigin(row["origin"]),
            support_confidence=row.get("support_confidence") if row.get("support_confidence") is not None else 0.5,
            rationale=row.get("rationale") or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_evidence_attachment(row: dict) -> EvidenceAttachment:
        return EvidenceAttachment(
            id=row["id"],
            case_id=row["case_id"],
            evidence_id=row["evidence_id"],
            attachment_type=EvidenceAttachmentType(row["attachment_type"]),
            source_url=row.get("source_url") or "",
            media_title=row.get("media_title") or "",
            media_type=row.get("media_type") or "",
            file_path=row.get("file_path") or "",
            source_platform=row.get("source_platform") or "",
            provenance_note=row.get("provenance_note") or "",
            metadata=json.loads(row.get("metadata_json") or "{}"),
            captured_at=row.get("captured_at") or row.get("created_at") or datetime.now(timezone.utc).isoformat(),
            created_at=row.get("created_at") or row.get("captured_at") or datetime.now(timezone.utc).isoformat(),
            updated_at=row.get("updated_at") or row.get("created_at") or datetime.now(timezone.utc).isoformat(),
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
        evidence = [self._row_to_evidence(dict(r)) for r in evidence_rows]

        return Case(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            mission_intake=self._row_to_mission_intake(row),
            workflow_stage=WorkflowStage(row.get("workflow_stage") or "INTAKE"),
            workflow_stage_note=row.get("workflow_stage_note") or "",
            workflow_stage_updated_at=row.get("workflow_stage_updated_at") or row["updated_at"],
            tags=json.loads(row["tags"] or "[]"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            status=CaseStatus(row["status"]),
            targets=targets,
            findings=findings,
            notes=notes,
            entities=self.get_entities_for_case(case_id),
            evidence=evidence,
            saved_searches=self.get_saved_searches_for_case(case_id),
            leads=self.get_leads_for_case(case_id),
            task_links=self.get_task_links_for_case(case_id),
            finding_evidence_links=self.get_finding_evidence_links_for_case(case_id),
            evidence_attachments=self.get_evidence_attachments_for_case(case_id),
            adapter_runs=self.get_adapter_runs_for_case(case_id),
        )

    @staticmethod
    def _row_to_mission_intake(row: dict) -> MissionIntake:
        raw = row.get("mission_intake_json")
        if not raw:
            return MissionIntake()

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return MissionIntake()

        return MissionIntake.model_validate(payload)

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
            adapter_run_id=row.get("adapter_run_id"),
            review_state=FindingReviewState(row.get("review_state") or "NEW"),
            analyst_note=row.get("analyst_note") or "",
            decision_state=FindingDecisionState(row.get("decision_state") or "PENDING_REVIEW"),
            decision_confidence=row.get("decision_confidence") if row.get("decision_confidence") is not None else 0.5,
            decision_rationale=row.get("decision_rationale") or "",
            decision_updated_at=row.get("decision_updated_at") or row.get("collected_at"),
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

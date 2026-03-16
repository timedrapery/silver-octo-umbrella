"""Tests for database storage."""
import pytest
from datetime import datetime, timezone

from app.models.case import (
    AdapterRun,
    ArtifactLinkType,
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
    MissionPriority,
    Note,
    SavedSearch,
    SearchIntent,
    SearchProvider,
    SourceReliability,
    SupportLinkOrigin,
    Severity,
    Target,
    TargetType,
    WorkflowStage,
    MissionTask,
    LeadLifecycleState,
    LeadPriority,
    LeadProfile,
    MissionTaskLink,
)
from app.storage.database import Database


@pytest.fixture
def db(tmp_path):
    database = Database()
    database.initialize(str(tmp_path / "test.db"))
    return database


class TestDatabaseInitialization:
    def test_initialize_creates_tables(self, tmp_path):
        database = Database()
        database.initialize(str(tmp_path / "init_test.db"))
        cur = database.conn.cursor()
        tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in tables}
        assert "cases" in table_names
        assert "targets" in table_names
        assert "findings" in table_names
        assert "notes" in table_names
        assert "evidence" in table_names
        assert "entities" in table_names
        assert "saved_searches" in table_names
        assert "leads" in table_names
        assert "mission_task_links" in table_names
        assert "finding_evidence_links" in table_names
        assert "evidence_attachments" in table_names

    def test_initialize_default_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        database = Database()
        database.initialize()
        assert database.db_path == "osint_platform.db"

    def test_schema_migration_adds_triage_columns(self, tmp_path):
        import sqlite3

        db_path = tmp_path / "legacy.db"
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE cases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT,
                status TEXT
            );
            CREATE TABLE findings (
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
            """
        )
        conn.commit()
        conn.close()

        database = Database()
        database.initialize(str(db_path))
        cols = database.conn.execute("PRAGMA table_info(findings)").fetchall()
        names = {row["name"] for row in cols}
        assert "review_state" in names
        assert "analyst_note" in names
        assert "decision_state" in names
        assert "decision_confidence" in names
        assert "decision_rationale" in names
        assert "decision_updated_at" in names

    def test_schema_migration_adds_mission_and_stage_columns(self, tmp_path):
        import sqlite3

        db_path = tmp_path / "legacy_mission.db"
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE cases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT,
                status TEXT
            );
            CREATE TABLE findings (
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
            CREATE TABLE evidence (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                finding_id TEXT,
                file_path TEXT,
                description TEXT,
                collected_at TEXT
            );
            """
        )
        conn.commit()
        conn.close()

        database = Database()
        database.initialize(str(db_path))
        cols = database.conn.execute("PRAGMA table_info(cases)").fetchall()
        names = {row["name"] for row in cols}
        assert "mission_intake_json" in names
        assert "workflow_stage" in names
        assert "workflow_stage_note" in names
        assert "workflow_stage_updated_at" in names


class TestCaseCRUD:
    def test_save_and_load_case(self, db):
        case = Case(name="Test Case", description="A description")
        db.save_case(case)
        loaded = db.load_case(case.id)
        assert loaded.id == case.id
        assert loaded.name == "Test Case"
        assert loaded.description == "A description"

    def test_load_nonexistent_case_raises(self, db):
        with pytest.raises(ValueError):
            db.load_case("nonexistent-id")

    def test_list_cases_empty(self, db):
        cases = db.list_cases()
        assert cases == []

    def test_list_cases_multiple(self, db):
        c1 = Case(name="Case One")
        c2 = Case(name="Case Two")
        db.save_case(c1)
        db.save_case(c2)
        cases = db.list_cases()
        assert len(cases) == 2
        names = {c.name for c in cases}
        assert "Case One" in names
        assert "Case Two" in names

    def test_delete_case(self, db):
        case = Case(name="Delete Me")
        db.save_case(case)
        db.delete_case(case.id)
        with pytest.raises(ValueError):
            db.load_case(case.id)

    def test_save_case_with_targets(self, db):
        case = Case(name="With Targets")
        t = Target(type=TargetType.DOMAIN, value="example.com")
        case.targets.append(t)
        db.save_case(case)
        loaded = db.load_case(case.id)
        assert len(loaded.targets) == 1
        assert loaded.targets[0].value == "example.com"
        assert loaded.targets[0].type == TargetType.DOMAIN

    def test_save_case_idempotent(self, db):
        case = Case(name="Idempotent")
        db.save_case(case)
        case.description = "Updated"
        db.save_case(case)
        loaded = db.load_case(case.id)
        assert loaded.description == "Updated"

    def test_case_status_preserved(self, db):
        case = Case(name="Status Test", status=CaseStatus.CLOSED)
        db.save_case(case)
        loaded = db.load_case(case.id)
        assert loaded.status == CaseStatus.CLOSED

    def test_case_mission_and_stage_round_trip(self, db):
        case = Case(name="Mission Case")
        case.workflow_stage = WorkflowStage.REVIEW
        case.workflow_stage_note = "Ready for adjudication"
        case.mission_intake.mission_summary = "Investigate domain exposure"
        case.mission_intake.objectives = ["Map assets", "Validate risk"]
        case.mission_intake.hypotheses = ["Leaked credentials exist"]
        case.mission_intake.scope = "example.com assets"
        case.mission_intake.constraints = "No intrusive scanning"
        case.mission_intake.legal_operational_notes = "Public sources only"
        case.mission_intake.risk_notes = "Potential sensitive data"
        case.mission_intake.priority = MissionPriority.HIGH
        case.mission_intake.intake_notes = "Escalate if critical exposure found"
        case.mission_intake.tasks = []

        db.save_case(case)
        loaded = db.load_case(case.id)
        assert loaded.workflow_stage == WorkflowStage.REVIEW
        assert loaded.workflow_stage_note == "Ready for adjudication"
        assert loaded.mission_intake.mission_summary == "Investigate domain exposure"
        assert loaded.mission_intake.priority == MissionPriority.HIGH
        assert loaded.mission_intake.objectives == ["Map assets", "Validate risk"]


class TestFindingStorage:
    def test_save_and_get_findings(self, db):
        case = Case(name="Finding Test")
        db.save_case(case)
        t = Target(type=TargetType.DOMAIN, value="example.com")
        finding = Finding(
            target_id=t.id,
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="A Record",
            description="IPv4 address found",
            severity=Severity.INFO,
            data={"ip": "93.184.216.34"},
        )
        db.save_finding(finding, case.id)
        findings = db.get_findings_for_case(case.id)
        assert len(findings) == 1
        assert findings[0].title == "A Record"
        assert findings[0].severity == Severity.INFO
        assert findings[0].data == {"ip": "93.184.216.34"}

    def test_finding_adapter_run_id_round_trip(self, db):
        case = Case(name="Finding Traceability")
        db.save_case(case)
        finding = Finding(
            target_id="target-1",
            adapter_name="dns",
            adapter_run_id="run-123",
            finding_type=FindingType.DNS,
            title="A Record",
            description="desc",
            severity=Severity.INFO,
        )
        db.save_finding(finding, case.id)

        loaded = db.get_findings_for_case(case.id)
        assert len(loaded) == 1
        assert loaded[0].adapter_run_id == "run-123"

    def test_finding_triage_fields_round_trip(self, db):
        case = Case(name="Finding Triage")
        db.save_case(case)
        finding = Finding(
            target_id="target-1",
            adapter_name="http",
            finding_type=FindingType.HTTP,
            title="Missing header",
            description="desc",
            severity=Severity.MEDIUM,
            review_state=FindingReviewState.FLAGGED,
            analyst_note="Escalate to analyst",
            decision_state=FindingDecisionState.LOW_CONFIDENCE,
            decision_confidence=0.33,
            decision_rationale="Single weak source",
        )
        db.save_finding(finding, case.id)

        loaded = db.get_findings_for_case(case.id)
        assert loaded[0].review_state == FindingReviewState.FLAGGED
        assert loaded[0].analyst_note == "Escalate to analyst"
        assert loaded[0].decision_state == FindingDecisionState.LOW_CONFIDENCE
        assert loaded[0].decision_confidence == pytest.approx(0.33)
        assert loaded[0].decision_rationale == "Single weak source"

    def test_update_finding_triage(self, db):
        case = Case(name="Update Triage")
        db.save_case(case)
        finding = Finding(
            target_id="target-1",
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="A record",
            description="desc",
            severity=Severity.INFO,
        )
        db.save_finding(finding, case.id)

        db.update_finding_triage(
            finding.id,
            FindingReviewState.REVIEWED,
            "Validated and closed",
        )

        loaded = db.get_findings_for_case(case.id)
        assert loaded[0].review_state == FindingReviewState.REVIEWED
        assert loaded[0].analyst_note == "Validated and closed"

    def test_update_finding_decision(self, db):
        case = Case(name="Update Decision")
        db.save_case(case)
        finding = Finding(
            target_id="target-1",
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="A record",
            description="desc",
            severity=Severity.INFO,
        )
        db.save_finding(finding, case.id)

        db.update_finding_decision(
            finding.id,
            FindingDecisionState.CORRELATED,
            0.71,
            "Linked to verified evidence",
        )

        loaded = db.get_findings_for_case(case.id)
        assert loaded[0].decision_state == FindingDecisionState.CORRELATED
        assert loaded[0].decision_confidence == pytest.approx(0.71)
        assert loaded[0].decision_rationale == "Linked to verified evidence"

    def test_get_findings_empty(self, db):
        case = Case(name="No Findings")
        db.save_case(case)
        assert db.get_findings_for_case(case.id) == []

    def test_save_finding_with_all_severities(self, db):
        case = Case(name="Severity Test")
        db.save_case(case)
        t = Target(type=TargetType.DOMAIN, value="example.com")
        for sev in Severity:
            f = Finding(
                target_id=t.id,
                adapter_name="test",
                finding_type=FindingType.GENERIC,
                title=f"Finding {sev.value}",
                description="test",
                severity=sev,
            )
            db.save_finding(f, case.id)
        findings = db.get_findings_for_case(case.id)
        assert len(findings) == len(list(Severity))

    def test_delete_case_removes_findings(self, db):
        case = Case(name="Delete With Findings")
        db.save_case(case)
        t = Target(type=TargetType.DOMAIN, value="example.com")
        f = Finding(
            target_id=t.id,
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="Test",
            description="desc",
            severity=Severity.LOW,
        )
        db.save_finding(f, case.id)
        db.delete_case(case.id)
        findings = db.get_findings_for_case(case.id)
        assert findings == []


# ──────────────────────────── AdapterRun Storage ────────────────────────────

class TestAdapterRunStorage:
    def _make_run(self, case_id: str, target_id: str, adapter: str = "dns") -> AdapterRun:
        return AdapterRun(
            case_id=case_id,
            target_id=target_id,
            adapter_name=adapter,
            status=AdapterRunStatus.COMPLETE,
            finding_count=5,
            duration_seconds=1.23,
        )

    def test_save_and_retrieve_adapter_run(self, db):
        case = Case(name="Run Test")
        db.save_case(case)
        run = self._make_run(case.id, "t1")
        db.save_adapter_run(run)
        runs = db.get_adapter_runs_for_case(case.id)
        assert len(runs) == 1
        assert runs[0].adapter_name == "dns"
        assert runs[0].status == AdapterRunStatus.COMPLETE
        assert runs[0].finding_count == 5
        assert abs(runs[0].duration_seconds - 1.23) < 0.01

    def test_multiple_runs_for_case(self, db):
        case = Case(name="Multi Run")
        db.save_case(case)
        db.save_adapter_run(self._make_run(case.id, "t1", "dns"))
        db.save_adapter_run(self._make_run(case.id, "t1", "http"))
        runs = db.get_adapter_runs_for_case(case.id)
        assert len(runs) == 2
        names = {r.adapter_name for r in runs}
        assert "dns" in names
        assert "http" in names

    def test_failed_run_stores_error(self, db):
        case = Case(name="Failed Run")
        db.save_case(case)
        run = AdapterRun(
            case_id=case.id,
            target_id="t1",
            adapter_name="cert",
            status=AdapterRunStatus.FAILED,
            error_message="Connection timeout",
        )
        db.save_adapter_run(run)
        runs = db.get_adapter_runs_for_case(case.id)
        assert runs[0].status == AdapterRunStatus.FAILED
        assert runs[0].error_message == "Connection timeout"

    def test_case_loaded_with_adapter_runs(self, db):
        case = Case(name="Full Load")
        db.save_case(case)
        run = self._make_run(case.id, "t1")
        db.save_adapter_run(run)
        loaded = db.load_case(case.id)
        assert len(loaded.adapter_runs) == 1

    def test_delete_case_removes_adapter_runs(self, db):
        case = Case(name="Delete Runs")
        db.save_case(case)
        db.save_adapter_run(self._make_run(case.id, "t1"))
        db.delete_case(case.id)
        runs = db.get_adapter_runs_for_case(case.id)
        assert runs == []

    def test_update_case_timestamp(self, db):
        case = Case(name="Timestamp Test")
        db.save_case(case)
        before = case.updated_at
        db.update_case_timestamp(case.id)
        loaded = db.load_case(case.id)
        assert loaded.updated_at >= before


# ──────────────────────────── Notes Storage ─────────────────────────────────

class TestNotesStorage:
    def test_save_and_load_notes(self, db):
        case = Case(name="Note Case")
        note = Note(case_id=case.id, content="Test observation", tags=["recon"])
        case.notes = [note]
        db.save_case(case)
        loaded = db.load_case(case.id)
        assert len(loaded.notes) == 1
        assert loaded.notes[0].content == "Test observation"
        assert "recon" in loaded.notes[0].tags

    def test_multiple_notes_preserved(self, db):
        case = Case(name="Multi Note")
        case.notes = [
            Note(case_id=case.id, content="First"),
            Note(case_id=case.id, content="Second"),
        ]
        db.save_case(case)
        loaded = db.load_case(case.id)
        contents = {n.content for n in loaded.notes}
        assert "First" in contents
        assert "Second" in contents


class TestSavedSearchStorage:
    def test_save_and_load_saved_searches(self, db):
        case = Case(name="Search Case")
        search = SavedSearch(
            case_id=case.id,
            target_id="target-1",
            title="Credential Exposure Sweep",
            query='site:pastebin.com "example.com" "password"',
            explanation="Looks for leaked credentials mentioning the domain.",
            intent=SearchIntent.CREDENTIAL_MENTION,
            provider=SearchProvider.GOOGLE,
            tags=["credentials", "leak"],
            analyst_note="Run weekly and compare drift.",
        )
        case.saved_searches = [search]

        db.save_case(case)
        loaded = db.load_case(case.id)

        assert len(loaded.saved_searches) == 1
        loaded_search = loaded.saved_searches[0]
        assert loaded_search.title == "Credential Exposure Sweep"
        assert loaded_search.intent == SearchIntent.CREDENTIAL_MENTION
        assert loaded_search.provider == SearchProvider.GOOGLE
        assert loaded_search.tags == ["credentials", "leak"]
        assert loaded_search.analyst_note == "Run weekly and compare drift."

    def test_list_saved_searches_for_case(self, db):
        case = Case(name="List Searches")
        db.save_case(case)

        s1 = SavedSearch(
            case_id=case.id,
            title="One",
            query="site:example.com filetype:pdf",
            explanation="Find PDFs.",
        )
        s2 = SavedSearch(
            case_id=case.id,
            title="Two",
            query='"example.com" "admin"',
            explanation="Find admin references.",
        )
        db.save_saved_search(s1)
        db.save_saved_search(s2)

        searches = db.get_saved_searches_for_case(case.id)
        titles = {item.title for item in searches}
        assert len(searches) == 2
        assert "One" in titles
        assert "Two" in titles

    def test_delete_case_removes_saved_searches(self, db):
        case = Case(name="Delete Saved Searches")
        db.save_case(case)
        search = SavedSearch(
            case_id=case.id,
            title="Delete Me",
            query="site:example.com",
            explanation="Search test.",
        )
        db.save_saved_search(search)

        db.delete_case(case.id)
        assert db.get_saved_searches_for_case(case.id) == []


class TestIntelligenceLedgerStorage:
    def test_save_and_load_entities(self, db):
        case = Case(name="Entity Ledger")
        db.save_case(case)

        entity = Entity(
            case_id=case.id,
            kind=EntityKind.USERNAME,
            value="alice",
            display_name="Analyst Alice",
            metadata={"platform": "github"},
            tags=["identity"],
        )
        db.save_entity(entity)

        loaded = db.get_entities_for_case(case.id)
        assert len(loaded) == 1
        assert loaded[0].kind == EntityKind.USERNAME
        assert loaded[0].metadata["platform"] == "github"

    def test_save_and_load_evidence_provenance(self, db):
        case = Case(name="Evidence Ledger")
        db.save_case(case)

        evidence = Evidence(
            case_id=case.id,
            entity_id="entity-1",
            description="Provider raw record",
            source_reliability=SourceReliability.MEDIUM,
            raw_json_data={"provider": "social", "hit": True},
            normalized_summary="Social profile likely linked to target.",
        )
        db.save_evidence(evidence)

        loaded = db.get_evidence_for_case(case.id)
        assert len(loaded) == 1
        assert loaded[0].source_reliability == SourceReliability.MEDIUM
        assert loaded[0].raw_json_data["provider"] == "social"
        assert loaded[0].normalized_summary == "Social profile likely linked to target."

    def test_delete_entity_and_evidence(self, db):
        case = Case(name="Delete Ledger")
        db.save_case(case)

        entity = Entity(case_id=case.id, kind=EntityKind.IP, value="8.8.8.8")
        db.save_entity(entity)
        evidence = Evidence(case_id=case.id, entity_id=entity.id, description="IP evidence")
        db.save_evidence(evidence)

        db.delete_entity(entity.id, case.id)
        db.delete_evidence(evidence.id, case.id)

        assert db.get_entities_for_case(case.id) == []
        assert db.get_evidence_for_case(case.id) == []


class TestLeadWorkspaceStorage:
    def test_save_and_load_lead_profiles(self, db):
        case = Case(name="Lead Case")
        lead = LeadProfile(
            case_id=case.id,
            kind="EMAIL",
            canonical_value="lead@example.com",
            display_label="lead@example.com",
            lifecycle_state=LeadLifecycleState.ACTIVE,
            priority=LeadPriority.HIGH,
            owner="ops-1",
            confidence_score=0.7,
            linked_target_ids=["target-1"],
        )
        case.leads = [lead]
        db.save_case(case)

        loaded = db.load_case(case.id)
        assert len(loaded.leads) == 1
        assert loaded.leads[0].lifecycle_state == LeadLifecycleState.ACTIVE
        assert loaded.leads[0].priority == LeadPriority.HIGH

    def test_save_and_load_mission_task_links(self, db):
        case = Case(name="Task Link Case")
        task = MissionTask(title="Investigate lead")
        case.mission_intake.tasks = [task]
        link = MissionTaskLink(
            case_id=case.id,
            task_id=task.id,
            artifact_type=ArtifactLinkType.LEAD,
            artifact_id="lead-1",
            note="Critical subject",
        )
        case.task_links = [link]
        db.save_case(case)

        loaded = db.load_case(case.id)
        assert len(loaded.task_links) == 1
        assert loaded.task_links[0].artifact_type == ArtifactLinkType.LEAD
        assert loaded.task_links[0].note == "Critical subject"


class TestConvergenceStorage:
    def test_save_and_load_finding_evidence_links(self, db):
        case = Case(name="Convergence")
        finding = Finding(
            target_id="target-1",
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="A record",
            description="desc",
            severity=Severity.MEDIUM,
        )
        evidence = Evidence(case_id=case.id, description="Supporting artifact")
        case.findings = [finding]
        case.evidence = [evidence]
        link = FindingEvidenceLink(
            case_id=case.id,
            finding_id=finding.id,
            evidence_id=evidence.id,
            origin=SupportLinkOrigin.MANUAL_CORRELATION,
            support_confidence=0.67,
            rationale="Same source and indicator",
        )
        case.finding_evidence_links = [link]

        db.save_case(case)
        loaded = db.load_case(case.id)
        assert len(loaded.finding_evidence_links) == 1
        loaded_link = loaded.finding_evidence_links[0]
        assert loaded_link.finding_id == finding.id
        assert loaded_link.evidence_id == evidence.id
        assert loaded_link.origin == SupportLinkOrigin.MANUAL_CORRELATION
        assert loaded_link.support_confidence == pytest.approx(0.67)

    def test_save_and_load_evidence_attachments(self, db):
        case = Case(name="Attachment Case")
        evidence = Evidence(case_id=case.id, description="Public reference")
        attachment = EvidenceAttachment(
            case_id=case.id,
            evidence_id=evidence.id,
            attachment_type=EvidenceAttachmentType.PUBLIC_MEDIA,
            source_url="https://www.instagram.com/p/sample",
            media_title="Sample post",
            media_type="post",
            provenance_note="Collected from public profile",
            metadata={"capture_method": "url_submission"},
        )
        case.evidence = [evidence]
        case.evidence_attachments = [attachment]

        db.save_case(case)
        loaded = db.load_case(case.id)
        assert len(loaded.evidence_attachments) == 1
        loaded_attachment = loaded.evidence_attachments[0]
        assert loaded_attachment.evidence_id == evidence.id
        assert loaded_attachment.attachment_type == EvidenceAttachmentType.PUBLIC_MEDIA
        assert loaded_attachment.source_url.endswith("/sample")

    def test_attachment_migration_creates_table(self, tmp_path):
        import sqlite3

        db_path = tmp_path / "legacy_attachment.db"
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE cases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT,
                status TEXT
            );
            CREATE TABLE findings (
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
            CREATE TABLE evidence (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                finding_id TEXT,
                file_path TEXT,
                description TEXT,
                collected_at TEXT
            );
            """
        )
        conn.commit()
        conn.close()

        database = Database()
        database.initialize(str(db_path))
        rows = database.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='evidence_attachments'"
        ).fetchall()
        assert len(rows) == 1


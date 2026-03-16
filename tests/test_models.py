"""Tests for Pydantic data models."""
import pytest
from datetime import datetime

from app.models.case import (
    ArtifactLinkType,
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
    FindingSortBy,
    FindingType,
    InvestigationPreset,
    LeadLifecycleState,
    LeadPriority,
    LeadProfile,
    MissionTaskLink,
    Note,
    SavedSearch,
    SearchIntent,
    SearchProvider,
    SourceReliability,
    SupportLinkOrigin,
    Severity,
    Target,
    TargetType,
    MissionIntake,
    MissionPriority,
    MissionTask,
    WorkflowStage,
)


class TestTargetModel:
    def test_target_domain(self):
        t = Target(type=TargetType.DOMAIN, value="example.com")
        assert t.type == TargetType.DOMAIN
        assert t.value == "example.com"
        assert isinstance(t.id, str) and len(t.id) == 36
        assert isinstance(t.created_at, datetime)
        assert t.notes == []
        assert t.tags == []

    @pytest.mark.parametrize("tt", list(TargetType))
    def test_all_target_types(self, tt):
        t = Target(type=tt, value="test_value")
        assert t.type == tt

    def test_target_defaults(self):
        t1 = Target(type=TargetType.IP, value="1.2.3.4")
        t2 = Target(type=TargetType.IP, value="1.2.3.4")
        assert t1.id != t2.id  # unique IDs

    def test_target_with_tags_and_notes(self):
        t = Target(type=TargetType.EMAIL, value="a@b.com", tags=["recon"], notes=["note1"])
        assert "recon" in t.tags
        assert "note1" in t.notes


class TestFindingModel:
    @pytest.mark.parametrize("ft", list(FindingType))
    def test_all_finding_types(self, ft):
        f = Finding(
            target_id="tid",
            adapter_name="test",
            finding_type=ft,
            title="Test",
            description="desc",
            severity=Severity.INFO,
        )
        assert f.finding_type == ft

    @pytest.mark.parametrize("sev", list(Severity))
    def test_all_severities(self, sev):
        f = Finding(
            target_id="tid",
            adapter_name="test",
            finding_type=FindingType.GENERIC,
            title="Test",
            description="desc",
            severity=sev,
        )
        assert f.severity == sev

    def test_finding_defaults(self):
        f = Finding(
            target_id="tid",
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="A Record",
            description="desc",
            severity=Severity.LOW,
        )
        assert f.data == {}
        assert f.source_url == ""
        assert f.source_name == ""
        assert f.adapter_run_id is None
        assert f.review_state == FindingReviewState.NEW
        assert f.analyst_note == ""
        assert f.decision_state == FindingDecisionState.PENDING_REVIEW
        assert f.decision_confidence == 0.5
        assert f.decision_rationale == ""
        assert f.tags == []
        assert isinstance(f.collected_at, datetime)

    def test_review_state_values(self):
        for state in FindingReviewState:
            assert isinstance(state.value, str)

    def test_finding_sort_values(self):
        for sort_by in FindingSortBy:
            assert isinstance(sort_by.value, str)

    def test_finding_decision_values(self):
        for state in FindingDecisionState:
            assert isinstance(state.value, str)


class TestCaseModel:
    def test_create_case(self):
        case = Case(name="Test Case")
        assert case.name == "Test Case"
        assert case.description == ""
        assert case.targets == []
        assert case.findings == []
        assert case.notes == []
        assert case.evidence == []
        assert case.status == CaseStatus.OPEN
        assert case.workflow_stage == WorkflowStage.INTAKE
        assert case.workflow_stage_note == ""
        assert isinstance(case.mission_intake, MissionIntake)

    def test_add_targets_and_findings(self):
        case = Case(name="Case")
        t = Target(type=TargetType.DOMAIN, value="example.com")
        f = Finding(
            target_id=t.id,
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="A Record",
            description="desc",
            severity=Severity.INFO,
        )
        case.targets.append(t)
        case.findings.append(f)
        assert len(case.targets) == 1
        assert len(case.findings) == 1

    def test_mission_priority_values(self):
        for priority in MissionPriority:
            assert isinstance(priority.value, str)

    def test_workflow_stage_values(self):
        for stage in WorkflowStage:
            assert isinstance(stage.value, str)

    def test_mission_task_validation(self):
        task = MissionTask(title="Define hypotheses")
        assert task.completed is False
        with pytest.raises(ValueError):
            MissionTask(title="   ")

    def test_mission_intake_defaults(self):
        intake = MissionIntake()
        assert intake.mission_summary == ""
        assert intake.priority == MissionPriority.MEDIUM
        assert intake.tasks == []

    def test_case_serialization(self):
        case = Case(name="Serialization Test", description="desc")
        t = Target(type=TargetType.USERNAME, value="johndoe")
        case.targets.append(t)

        data = case.model_dump()
        assert data["name"] == "Serialization Test"
        assert len(data["targets"]) == 1
        assert data["targets"][0]["value"] == "johndoe"

    def test_case_deserialization(self):
        original = Case(name="Round Trip")
        t = Target(type=TargetType.IP, value="10.0.0.1")
        original.targets.append(t)

        data = original.model_dump(mode="json")
        restored = Case.model_validate(data)
        assert restored.id == original.id
        assert restored.targets[0].value == "10.0.0.1"

    def test_note_model(self):
        n = Note(case_id="cid", content="Important observation")
        assert n.case_id == "cid"
        assert n.content == "Important observation"
        assert isinstance(n.id, str)
        assert isinstance(n.created_at, datetime)

    def test_evidence_model(self):
        e = Evidence(case_id="cid", file_path="/tmp/screenshot.png", description="Screenshot")
        assert e.finding_id is None
        assert e.source_reliability == SourceReliability.UNVERIFIED
        assert e.raw_json_data == {}
        assert e.normalized_summary == ""
        e2 = Evidence(case_id="cid", finding_id="fid", file_path="/tmp/file.pdf", description="File")
        assert e2.finding_id == "fid"

    def test_evidence_attachment_model(self):
        attachment = EvidenceAttachment(
            case_id="cid",
            evidence_id="e-1",
            attachment_type=EvidenceAttachmentType.PUBLIC_MEDIA,
            source_url="https://www.youtube.com/watch?v=abc123",
            media_title="Sample clip",
            media_type="video",
            provenance_note="Captured from public URL",
            metadata={"capture_method": "url_submission"},
        )
        assert attachment.attachment_type == EvidenceAttachmentType.PUBLIC_MEDIA
        assert attachment.source_url.startswith("https://")
        assert attachment.metadata["capture_method"] == "url_submission"

    def test_evidence_attachment_type_values(self):
        for kind in EvidenceAttachmentType:
            assert isinstance(kind.value, str)

    def test_entity_model_validation(self):
        entity = Entity(case_id="cid", kind=EntityKind.EMAIL, value="user@example.com")
        assert entity.value == "user@example.com"

        with pytest.raises(ValueError):
            Entity(case_id="cid", kind=EntityKind.USERNAME, value="   ")

    def test_investigation_preset_values(self):
        for preset in InvestigationPreset:
            assert isinstance(preset.value, str)

    def test_saved_search_defaults(self):
        search = SavedSearch(
            case_id="case-1",
            title="Domain Discovery",
            query='"example.com" site:example.com',
            explanation="Searches for references to example.com on the domain.",
        )
        assert search.provider == SearchProvider.GOOGLE
        assert search.intent == SearchIntent.GENERAL_DISCOVERY
        assert search.tags == []
        assert search.analyst_note == ""

    def test_search_enum_values(self):
        for intent in SearchIntent:
            assert isinstance(intent.value, str)
        for provider in SearchProvider:
            assert isinstance(provider.value, str)

    def test_lead_profile_defaults(self):
        lead = LeadProfile(
            case_id="case-1",
            kind="EMAIL",
            canonical_value="analyst@example.com",
            display_label="analyst@example.com",
        )
        assert lead.lifecycle_state == LeadLifecycleState.NEW
        assert lead.priority == LeadPriority.MEDIUM
        assert lead.confidence_score == 0.5

    def test_lead_profile_confidence_validation(self):
        with pytest.raises(ValueError):
            LeadProfile(
                case_id="case-1",
                kind="USERNAME",
                canonical_value="octo",
                display_label="octo",
                confidence_score=1.2,
            )

    def test_mission_task_link_defaults(self):
        link = MissionTaskLink(
            case_id="case-1",
            task_id="task-1",
            artifact_type=ArtifactLinkType.LEAD,
            artifact_id="lead-1",
        )
        assert link.note == ""

    def test_finding_evidence_link_defaults(self):
        link = FindingEvidenceLink(
            case_id="case-1",
            finding_id="finding-1",
            evidence_id="evidence-1",
        )
        assert link.origin == SupportLinkOrigin.MANUAL_CORRELATION
        assert link.support_confidence == 0.5

    def test_finding_evidence_link_confidence_validation(self):
        with pytest.raises(ValueError):
            FindingEvidenceLink(
                case_id="case-1",
                finding_id="finding-1",
                evidence_id="evidence-1",
                support_confidence=1.5,
            )

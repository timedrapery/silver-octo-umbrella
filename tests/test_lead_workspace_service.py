from app.models.case import (
    ArtifactLinkType,
    Case,
    Entity,
    EntityKind,
    Evidence,
    Finding,
    FindingReviewState,
    FindingType,
    LeadLifecycleState,
    LeadPriority,
    SavedSearch,
    SearchIntent,
    Severity,
    SourceReliability,
    Target,
    TargetType,
)
from app.services.lead_workspace_service import LeadWorkspaceFilter, LeadWorkspaceService
from app.storage.database import Database


def _setup_db(tmp_path):
    db = Database()
    db.initialize(str(tmp_path / "lead_workspace.db"))
    return db


def test_refresh_case_leads_unifies_targets_and_entities(tmp_path):
    db = _setup_db(tmp_path)
    case = Case(name="Unified")
    case.targets = [
        Target(type=TargetType.EMAIL, value="analyst@example.com"),
        Target(type=TargetType.URL, value="https://example.com/contact"),
    ]
    case.entities = [
        Entity(case_id=case.id, kind=EntityKind.EMAIL, value="analyst@example.com"),
        Entity(case_id=case.id, kind=EntityKind.PHONE, value="+1 415 555 0101"),
    ]
    db.save_case(case)

    service = LeadWorkspaceService(db)
    leads = service.refresh_case_leads(case.id)

    assert len(leads) >= 3
    keys = {(lead.kind, lead.canonical_value) for lead in leads}
    assert ("EMAIL", "analyst@example.com") in keys
    assert ("DOMAIN", "example.com") in keys
    assert ("PHONE", "+1 415 555 0101") in keys



def test_lead_lifecycle_update_persists(tmp_path):
    db = _setup_db(tmp_path)
    case = Case(name="Lifecycle")
    case.targets = [Target(type=TargetType.USERNAME, value="octo_user")]
    db.save_case(case)

    service = LeadWorkspaceService(db)
    leads = service.refresh_case_leads(case.id)
    lead = leads[0]

    service.update_lead_profile(
        case.id,
        lead.id,
        lifecycle_state=LeadLifecycleState.ACTIVE,
        priority=LeadPriority.HIGH,
        owner="intel-ops",
        confidence_score=0.8,
        context_summary="Correlates with high-signal findings",
    )

    loaded = db.load_case(case.id)
    updated = next(item for item in loaded.leads if item.id == lead.id)
    assert updated.lifecycle_state == LeadLifecycleState.ACTIVE
    assert updated.priority == LeadPriority.HIGH
    assert updated.owner == "intel-ops"
    assert updated.confidence_score == 0.8



def test_lead_detail_aggregates_related_artifacts(tmp_path):
    db = _setup_db(tmp_path)
    case = Case(name="Artifacts")
    target = Target(type=TargetType.EMAIL, value="pivot@example.com")
    case.targets = [target]
    entity = Entity(case_id=case.id, kind=EntityKind.EMAIL, value="pivot@example.com")
    case.entities = [entity]
    case.saved_searches = [
        SavedSearch(
            case_id=case.id,
            target_id=target.id,
            title="Pivot Search",
            query='"pivot@example.com" breach',
            explanation="Email mention search",
            intent=SearchIntent.EMAIL_MENTION,
        )
    ]
    case.findings = [
        Finding(
            target_id=target.id,
            adapter_name="social",
            finding_type=FindingType.SOCIAL,
            title="Email mention",
            description="pivot@example.com appears in profile",
            severity=Severity.MEDIUM,
            review_state=FindingReviewState.NEW,
        )
    ]
    case.evidence = [
        Evidence(
            case_id=case.id,
            entity_id=entity.id,
            description="promoted evidence",
            source_reliability=SourceReliability.MEDIUM,
            normalized_summary="pivot@example.com confirmed in external source",
        )
    ]
    db.save_case(case)

    service = LeadWorkspaceService(db)
    leads = service.refresh_case_leads(case.id)
    email_lead = next(item for item in leads if item.kind == "EMAIL")

    detail = service.get_lead_detail(case.id, email_lead.id)
    assert len(detail.related_targets) == 1
    assert len(detail.related_entities) == 1
    assert len(detail.related_findings) == 1
    assert len(detail.related_evidence) == 1
    assert len(detail.related_searches) == 1



def test_blocker_readiness_explains_missing_coverage(tmp_path):
    db = _setup_db(tmp_path)
    case = Case(name="Blockers")
    case.targets = [Target(type=TargetType.EMAIL, value="urgent@example.com")]
    db.save_case(case)

    service = LeadWorkspaceService(db)
    leads = service.refresh_case_leads(case.id)
    lead = leads[0]
    service.update_lead_profile(case.id, lead.id, priority=LeadPriority.CRITICAL)

    detail = service.get_lead_detail(case.id, lead.id)
    assert detail.blocker_explanation.readiness in {"BLOCKED", "PARTIAL"}
    text = " ".join(detail.blocker_explanation.blockers + detail.blocker_explanation.readiness_notes).lower()
    assert "evidence" in text or "research" in text



def test_task_link_to_lead_is_durable(tmp_path):
    db = _setup_db(tmp_path)
    case = Case(name="Task Link")
    case.targets = [Target(type=TargetType.USERNAME, value="octo_user")]
    task = case.mission_intake.tasks
    if not task:
        from app.models.case import MissionTask

        case.mission_intake.tasks = [MissionTask(title="Investigate username")]
    db.save_case(case)

    service = LeadWorkspaceService(db)
    leads = service.refresh_case_leads(case.id)
    lead = leads[0]
    task_id = db.load_case(case.id).mission_intake.tasks[0].id

    link = service.link_task_to_artifact(
        case.id,
        task_id,
        ArtifactLinkType.LEAD,
        lead.id,
        note="Task is tied to main user handle",
    )

    loaded = db.load_case(case.id)
    assert any(item.id == link.id for item in loaded.task_links)

    filtered = service.list_case_leads(
        case.id,
        LeadWorkspaceFilter(type_kind=lead.kind),
    )
    assert filtered

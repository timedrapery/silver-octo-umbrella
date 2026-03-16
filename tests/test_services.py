"""Tests for services."""
import pytest

from app.core.adapters.base import BaseAdapter
from app.core.adapters.dns_adapter import DnsAdapter
from app.core.adapters.cert_adapter import CertAdapter
from app.core.adapters.http_adapter import HttpAdapter
from app.core.adapters.social_adapter import SocialAdapter
from app.core.adapters.subdomain_adapter import SubdomainAdapter
from app.core.adapters.metadata_adapter import MetadataAdapter
from app.models.case import (
    ArtifactLinkType,
    AdapterRun,
    AdapterRunStatus,
    Case,
    FindingDecisionState,
    FindingEvidenceLink,
    Entity,
    EntityKind,
    EvidenceAttachmentType,
    Evidence,
    Finding,
    FindingReviewState,
    FindingSortBy,
    FindingType,
    InvestigationPreset,
    LeadLifecycleState,
    LeadPriority,
    LeadProfile,
    MissionPriority,
    MissionTask,
    SavedSearch,
    SearchIntent,
    SearchProvider,
    SourceReliability,
    SupportLinkOrigin,
    Severity,
    Target,
    TargetType,
    WorkflowStage,
)
from app.services.case_service import CaseService
from app.services.entity_research_service import EntityResearchService
from app.services.findings_service import FindingFilter, FindingsService
from app.services.graph_service import GraphService
from app.services.intelligence_orchestrator import (
    ProviderExecutionMetric,
    ResearchEntityResult,
    ResearchEvidenceItem,
)
from app.services.investigation_service import InvestigationService
from app.services.normalization import (
    extract_entities,
    build_entity_map,
    extract_case_summary,
)
from app.services.report_service import ReportService
from app.storage.intelligence_repository import IntelligenceRepository
from app.storage.database import Database


@pytest.fixture
def db(tmp_path):
    database = Database()
    database.initialize(str(tmp_path / "test.db"))
    return database


@pytest.fixture
def case_service(db):
    return CaseService(db)


@pytest.fixture
def investigation_service():
    adapters = [DnsAdapter(), CertAdapter(), HttpAdapter(), SocialAdapter(), SubdomainAdapter(), MetadataAdapter()]
    return InvestigationService(adapters)


@pytest.fixture
def findings_service():
    return FindingsService()


class FailingDomainAdapter(BaseAdapter):
    name = "failing"
    description = "Always fails"
    supported_target_types = [TargetType.DOMAIN]

    async def run(self, target: Target) -> list[Finding]:
        raise RuntimeError("Simulated failure")


class HangingDomainAdapter(BaseAdapter):
    name = "hanging"
    description = "Sleeps beyond timeout"
    supported_target_types = [TargetType.DOMAIN]

    async def run(self, target: Target) -> list[Finding]:
        import asyncio

        await asyncio.sleep(0.2)
        return []


# ─────────────────────────── CaseService ────────────────────────────────────

class TestCaseService:
    def test_create_case(self, case_service):
        case = case_service.create_case("Test Case", "description")
        assert case.name == "Test Case"
        assert case.description == "description"
        assert isinstance(case.id, str)

    def test_create_case_no_description(self, case_service):
        case = case_service.create_case("Minimal Case")
        assert case.description == ""

    def test_get_case(self, case_service):
        created = case_service.create_case("Fetch Me")
        fetched = case_service.get_case(created.id)
        assert fetched.id == created.id
        assert fetched.name == "Fetch Me"

    def test_list_cases(self, case_service):
        case_service.create_case("Case A")
        case_service.create_case("Case B")
        cases = case_service.list_cases()
        names = [c.name for c in cases]
        assert "Case A" in names
        assert "Case B" in names

    def test_add_target(self, case_service):
        case = case_service.create_case("Target Test")
        target = case_service.add_target(case.id, TargetType.DOMAIN, "example.com")
        assert target.type == TargetType.DOMAIN
        assert target.value == "example.com"
        updated = case_service.get_case(case.id)
        assert len(updated.targets) == 1
        assert updated.targets[0].value == "example.com"

    def test_add_note(self, case_service):
        case = case_service.create_case("Note Test")
        note = case_service.add_note(case.id, "Interesting observation")
        assert note.content == "Interesting observation"
        assert note.case_id == case.id
        updated = case_service.get_case(case.id)
        assert len(updated.notes) == 1

    def test_delete_case(self, case_service):
        case = case_service.create_case("To Delete")
        case_service.delete_case(case.id)
        with pytest.raises(ValueError):
            case_service.get_case(case.id)

    def test_update_case(self, case_service):
        case = case_service.create_case("Update Me")
        case.description = "Updated description"
        case_service.update_case(case)
        updated = case_service.get_case(case.id)
        assert updated.description == "Updated description"

    def test_save_adapter_runs(self, case_service):
        case = case_service.create_case("Run Persistence")
        run = AdapterRun(
            case_id=case.id,
            target_id="target-1",
            adapter_name="dns",
            status=AdapterRunStatus.COMPLETE,
            finding_count=2,
            duration_seconds=0.5,
        )

        case_service.save_adapter_runs(case.id, [run])
        updated = case_service.get_case(case.id)
        assert len(updated.adapter_runs) == 1
        assert updated.adapter_runs[0].adapter_name == "dns"

    def test_update_finding_triage(self, case_service):
        case = case_service.create_case("Triage Update")
        finding = Finding(
            target_id="target-1",
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="A Record",
            description="desc",
            severity=Severity.INFO,
        )
        case_service.add_finding(case.id, finding)

        case_service.update_finding_triage(
            case.id,
            finding.id,
            FindingReviewState.FLAGGED,
            "Investigate possible exposure",
        )

        updated = case_service.get_case(case.id)
        assert updated.findings[0].review_state == FindingReviewState.FLAGGED
        assert updated.findings[0].analyst_note == "Investigate possible exposure"

    def test_case_triage_summary(self, case_service):
        case = case_service.create_case("Summary")
        findings = [
            Finding(
                target_id="target-1",
                adapter_name="dns",
                finding_type=FindingType.DNS,
                title="A",
                description="desc",
                severity=Severity.CRITICAL,
                review_state=FindingReviewState.NEW,
            ),
            Finding(
                target_id="target-2",
                adapter_name="http",
                finding_type=FindingType.HTTP,
                title="B",
                description="desc",
                severity=Severity.LOW,
                review_state=FindingReviewState.REVIEWED,
            ),
            Finding(
                target_id="target-3",
                adapter_name="social",
                finding_type=FindingType.SOCIAL,
                title="C",
                description="desc",
                severity=Severity.MEDIUM,
                review_state=FindingReviewState.FLAGGED,
            ),
        ]
        case_service.add_findings_batch(case.id, findings)
        summary = case_service.get_case_triage_summary(case.id)
        assert summary.total == 3
        assert summary.new == 1
        assert summary.reviewed == 1
        assert summary.flagged == 1
        assert summary.dismissed == 0
        assert summary.high_unreviewed == 1

    def test_update_finding_triage_rejects_unknown_finding(self, case_service):
        case = case_service.create_case("Unknown Finding")
        with pytest.raises(ValueError):
            case_service.update_finding_triage(
                case.id,
                "missing-finding",
                FindingReviewState.REVIEWED,
            )

    def test_saved_search_lifecycle(self, case_service):
        case = case_service.create_case("Search Lifecycle")
        created = case_service.create_saved_search(
            case_id=case.id,
            title="Surface Public Docs",
            query="site:example.com filetype:pdf",
            explanation="Finds publicly indexed PDF documents.",
            intent=SearchIntent.DOCUMENT_DISCOVERY,
            provider=SearchProvider.GOOGLE,
            tags=["docs"],
        )
        assert created.id

        created.title = "Surface Public Reports"
        case_service.update_saved_search(created)

        searches = case_service.list_saved_searches(case.id)
        assert len(searches) == 1
        assert searches[0].title == "Surface Public Reports"

        case_service.delete_saved_search(case.id, created.id)
        assert case_service.list_saved_searches(case.id) == []

    def test_case_search_summary(self, case_service):
        case = case_service.create_case("Search Summary")
        case_service.create_saved_search(
            case_id=case.id,
            target_id="target-1",
            title="One",
            query="site:example.com",
            explanation="General discovery.",
            intent=SearchIntent.GENERAL_DISCOVERY,
        )
        case_service.create_saved_search(
            case_id=case.id,
            title="Two",
            query='"example.com" "login"',
            explanation="Login surface check.",
            intent=SearchIntent.GENERAL_DISCOVERY,
        )

        summary = case_service.get_case_search_summary(case.id)
        assert summary.total == 2
        assert summary.linked_targets == 1
        assert summary.last_created_at is not None

    def test_case_entity_activity_summary(self, case_service, db):
        case = case_service.create_case("Entity Summary")
        db.save_entity(
            Entity(
                case_id=case.id,
                kind=EntityKind.EMAIL,
                value="analyst@example.com",
                display_name="analyst@example.com",
            )
        )
        db.save_evidence(
            Evidence(
                case_id=case.id,
                description="Social profile evidence",
                source_reliability=SourceReliability.MEDIUM,
                raw_json_data={"workflow": "entity_research", "provider": "social_provider"},
                normalized_summary="GitHub profile discovered",
            )
        )

        summary = case_service.get_case_entity_activity_summary(case.id)
        assert summary.total_entities == 1
        assert summary.research_evidence_total == 1
        assert summary.last_research_at is not None

    def test_update_mission_intake(self, case_service):
        case = case_service.create_case("Mission Intake")
        intake = case_service.update_mission_intake(
            case.id,
            mission_summary="Investigate credential exposure",
            objectives=["Map exposed assets", "Prioritize remediation"],
            hypotheses=["Leaked credentials are publicly indexed"],
            scope="example.com ecosystem",
            constraints="No authenticated access",
            legal_operational_notes="Public OSINT only",
            risk_notes="Potential PII exposure",
            priority=MissionPriority.HIGH,
            intake_notes="Coordinate with response lead",
        )

        assert intake.mission_summary == "Investigate credential exposure"
        assert intake.priority == MissionPriority.HIGH
        loaded = case_service.get_case(case.id)
        assert loaded.mission_intake.scope == "example.com ecosystem"
        assert loaded.mission_intake.objectives == ["Map exposed assets", "Prioritize remediation"]

    def test_workflow_stage_transition_valid(self, case_service):
        case = case_service.create_case("Workflow")
        case_service.update_workflow_stage(case.id, WorkflowStage.COLLECTION, "Intake complete")
        case_service.update_workflow_stage(case.id, WorkflowStage.REVIEW, "Collection complete")

        loaded = case_service.get_case(case.id)
        assert loaded.workflow_stage == WorkflowStage.REVIEW
        assert loaded.workflow_stage_note == "Collection complete"

    def test_workflow_stage_transition_invalid(self, case_service):
        case = case_service.create_case("Workflow Invalid")
        with pytest.raises(ValueError):
            case_service.update_workflow_stage(case.id, WorkflowStage.REPORTING, "Skipping ahead")

    def test_mission_task_lifecycle(self, case_service):
        case = case_service.create_case("Tasks")
        task = case_service.add_mission_task(case.id, "Define objective", "Initial intake")
        case_service.update_mission_task(case.id, task.id, completed=True)

        loaded = case_service.get_case(case.id)
        assert len(loaded.mission_intake.tasks) == 1
        assert loaded.mission_intake.tasks[0].completed is True

        case_service.delete_mission_task(case.id, task.id)
        loaded = case_service.get_case(case.id)
        assert loaded.mission_intake.tasks == []

    def test_dashboard_summary_and_guidance(self, case_service):
        case = case_service.create_case("Dashboard")
        case_service.update_mission_intake(
            case.id,
            mission_summary="Assess exposed infrastructure",
            objectives=["Collect infrastructure findings"],
        )
        case_service.add_mission_task(case.id, "Run baseline collection")
        case_service.update_workflow_stage(case.id, WorkflowStage.COLLECTION, "Ready to collect")

        finding = Finding(
            target_id="target-1",
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="Critical host exposure",
            description="desc",
            severity=Severity.CRITICAL,
            review_state=FindingReviewState.NEW,
        )
        case_service.add_findings_batch(case.id, [finding])

        dashboard = case_service.get_case_dashboard_summary(case.id)
        assert dashboard.workflow_stage == WorkflowStage.COLLECTION
        assert dashboard.signals.unresolved_high_risk == 1
        assert dashboard.signals.checklist_total == 1
        assert any("high-risk" in action.lower() for action in dashboard.recommended_actions)

    def test_dashboard_recommends_phone_and_email_pivots(self, case_service):
        case = case_service.create_case("Pivot Guidance")
        case_service.add_target(case.id, TargetType.URL, "https://example.com/contact +1 415 555 0101")
        case_service.add_note(case.id, "Primary contact analyst@example.com for OSINT pivot")
        case_service.update_workflow_stage(case.id, WorkflowStage.COLLECTION, "Begin lead expansion")

        dashboard = case_service.get_case_dashboard_summary(case.id)
        all_actions = " ".join(dashboard.recommended_actions).lower()
        assert "reverse phone lookup" in all_actions
        assert "email pivot" in all_actions or "email mention" in all_actions
        assert any("phone" in item.lower() for item in dashboard.featured_collection_actions)
        assert any("email" in item.lower() for item in dashboard.featured_collection_actions)

    def test_dashboard_onboarding_hint_for_empty_case(self, case_service):
        case = case_service.create_case("Empty Onboarding")
        dashboard = case_service.get_case_dashboard_summary(case.id)
        assert "start here" in dashboard.onboarding_hint.lower()

    def test_unified_lead_listing_and_profile_update(self, case_service):
        case = case_service.create_case("Unified Leads")
        case_service.add_target(case.id, TargetType.EMAIL, "analyst@example.com")
        case_service.add_target(case.id, TargetType.USERNAME, "octo_user")

        leads = case_service.list_unified_leads(case.id)
        assert len(leads) >= 2

        email_lead = next(item.lead for item in leads if item.lead.kind == "EMAIL")
        updated = case_service.update_lead_profile(
            case.id,
            email_lead.id,
            lifecycle_state=LeadLifecycleState.ACTIVE,
            priority=LeadPriority.HIGH,
            owner="analyst-1",
            confidence_score=0.75,
            context_summary="Primary contact lead",
        )
        assert updated.lifecycle_state == LeadLifecycleState.ACTIVE
        assert updated.priority == LeadPriority.HIGH

    def test_task_link_to_lead_via_case_service(self, case_service):
        case = case_service.create_case("Task Link Lead")
        case_service.add_target(case.id, TargetType.USERNAME, "octo_user")
        task = case_service.add_mission_task(case.id, "Validate username")

        lead = case_service.list_unified_leads(case.id)[0].lead
        link = case_service.link_task_to_artifact(
            case.id,
            task.id,
            ArtifactLinkType.LEAD,
            lead.id,
            "Core mission subject",
        )
        assert link.artifact_type == ArtifactLinkType.LEAD

        loaded = case_service.get_case(case.id)
        assert any(item.id == link.id for item in loaded.task_links)

    def test_correlate_finding_to_existing_evidence(self, case_service, db):
        case = case_service.create_case("Convergence Correlate")
        finding = Finding(
            target_id="target-1",
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="A Record",
            description="desc",
            severity=Severity.HIGH,
        )
        case_service.add_finding(case.id, finding)

        evidence = Evidence(
            case_id=case.id,
            description="Resolver log artifact",
            source_reliability=SourceReliability.HIGH,
        )
        db.save_evidence(evidence)

        link = case_service.correlate_finding_to_evidence(
            case.id,
            finding.id,
            evidence.id,
            rationale="Host and timestamp align",
            support_confidence=0.82,
            origin=SupportLinkOrigin.MANUAL_CORRELATION,
        )
        assert link.support_confidence == pytest.approx(0.82)

        support = case_service.get_finding_support(case.id, finding.id)
        assert len(support.linked_evidence) == 1
        assert support.linked_evidence[0].id == evidence.id

    def test_promote_finding_to_evidence_prevents_obvious_duplicate(self, case_service):
        case = case_service.create_case("Convergence Promote")
        finding = Finding(
            target_id="target-1",
            adapter_name="http",
            finding_type=FindingType.HTTP,
            title="Leaked endpoint",
            description="Exposed endpoint reveals debug metadata",
            severity=Severity.MEDIUM,
        )
        case_service.add_finding(case.id, finding)

        evidence_a, link_a, created_a = case_service.promote_finding_to_evidence(
            case.id,
            finding.id,
            rationale="Contains explicit endpoint details",
            support_confidence=0.7,
        )
        evidence_b, link_b, created_b = case_service.promote_finding_to_evidence(
            case.id,
            finding.id,
            rationale="Second attempt",
            support_confidence=0.71,
        )

        assert created_a is True
        assert created_b is False
        assert evidence_a.id == evidence_b.id
        assert link_a.evidence_id == link_b.evidence_id

    def test_update_finding_decision_via_case_service(self, case_service):
        case = case_service.create_case("Decision")
        finding = Finding(
            target_id="target-1",
            adapter_name="social",
            finding_type=FindingType.SOCIAL,
            title="Possible account",
            description="similar handle",
            severity=Severity.LOW,
        )
        case_service.add_finding(case.id, finding)

        updated = case_service.update_finding_decision(
            case.id,
            finding.id,
            decision_state=FindingDecisionState.NEEDS_MORE_SUPPORT,
            decision_confidence=0.34,
            decision_rationale="Single-source weak match",
        )
        assert updated.decision_state == FindingDecisionState.NEEDS_MORE_SUPPORT

        loaded = case_service.get_case(case.id)
        assert loaded.findings[0].decision_confidence == pytest.approx(0.34)
        assert loaded.findings[0].decision_rationale == "Single-source weak match"

    def test_dashboard_includes_convergence_signals(self, case_service, db):
        case = case_service.create_case("Convergence Dashboard")
        finding = Finding(
            target_id="target-1",
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="Unresolved host",
            description="desc",
            severity=Severity.HIGH,
        )
        case_service.add_finding(case.id, finding)
        evidence = Evidence(case_id=case.id, description="orphan evidence")
        db.save_evidence(evidence)

        dashboard = case_service.get_case_dashboard_summary(case.id)
        assert dashboard.signals.unsupported_findings >= 1
        assert dashboard.signals.unlinked_evidence >= 1
        assert any("correlate findings" in action.lower() for action in dashboard.recommended_actions)

    def test_attachment_and_public_media_capture_workflow(self, case_service, db):
        case = case_service.create_case("Attachment Capture")
        finding = Finding(
            target_id="target-1",
            adapter_name="social",
            finding_type=FindingType.SOCIAL,
            title="Public profile post",
            description="Potentially relevant public media",
            severity=Severity.MEDIUM,
        )
        case_service.add_finding(case.id, finding)

        evidence = Evidence(case_id=case.id, description="Initial evidence")
        db.save_evidence(evidence)

        attached = case_service.attach_file_to_evidence(
            case.id,
            evidence.id,
            "C:/captures/screenshot_01.png",
            provenance_note="Manual screenshot capture",
        )
        assert attached.attachment_type == EvidenceAttachmentType.SCREENSHOT

        captured_evidence, attachments, created_new = case_service.capture_public_media_evidence(
            case.id,
            "https://www.youtube.com/watch?v=abc123",
            finding_id=finding.id,
            media_title="Channel post",
            media_type="video",
            provenance_note="Submitted by analyst",
            screenshot_file_path="C:/captures/youtube_clip.png",
        )
        assert created_new is True
        assert captured_evidence.raw_json_data.get("workflow") == "public_media_capture"
        assert len(attachments) == 2
        assert any(item.attachment_type == EvidenceAttachmentType.PUBLIC_MEDIA for item in attachments)

        all_attachments = case_service.list_evidence_attachments(case.id)
        assert len(all_attachments) == 3
        assert any(item.source_platform == "youtube" for item in all_attachments)

    def test_dashboard_highlights_missing_attachments(self, case_service, db):
        case = case_service.create_case("Attachment Readiness")
        evidence = Evidence(case_id=case.id, description="Evidence without attachment")
        db.save_evidence(evidence)

        dashboard = case_service.get_case_dashboard_summary(case.id)
        assert dashboard.signals.evidence_without_attachments >= 1
        assert any("attachment" in action.lower() for action in dashboard.recommended_actions)


class FakeResearchOrchestrator:
    async def research_entity(self, request):
        return ResearchEntityResult(
            request=request,
            providers=[
                ProviderExecutionMetric(
                    provider_name="breach_provider",
                    duration_seconds=0.1,
                    success=True,
                    result_count=1,
                ),
                ProviderExecutionMetric(
                    provider_name="infrastructure_provider",
                    duration_seconds=0.1,
                    success=False,
                    result_count=0,
                    error_message="timed out",
                ),
                ProviderExecutionMetric(
                    provider_name="social_provider",
                    duration_seconds=0.1,
                    success=True,
                    result_count=1,
                ),
            ],
            evidence_items=[
                ResearchEvidenceItem(
                    provider_name="breach_provider",
                    data={
                        "indicator": request.entity_value,
                        "collection": "leak-index",
                        "confidence": "high",
                    },
                ),
                ResearchEvidenceItem(
                    provider_name="social_provider",
                    data={
                        "username": request.entity_value,
                        "platform": "github",
                        "url": f"https://github.com/{request.entity_value}",
                        "confidence": "medium",
                    },
                ),
            ],
        )


class TestEntityResearchService:
    @pytest.mark.asyncio
    async def test_research_and_promotion_dedup(self, db, case_service):
        case = case_service.create_case("Research Workflow")
        service = EntityResearchService(
            orchestrator=FakeResearchOrchestrator(),
            repository=IntelligenceRepository(db),
        )

        session = await service.research_entity(case.id, "octo_user", "USERNAME")
        assert session.total_results == 2
        assert session.partial_failure is True
        assert session.promoted_results == 0
        assert session.entity.kind == EntityKind.USERNAME

        promoted = service.promote_results(
            case_id=case.id,
            entity_id=session.entity.id,
            selected_results=session.results,
            source_reliability=SourceReliability.HIGH,
            analyst_note="Validated via manual review",
        )
        assert promoted.created == 2
        assert promoted.skipped_duplicates == 0

        second = service.promote_results(
            case_id=case.id,
            entity_id=session.entity.id,
            selected_results=session.results,
            source_reliability=SourceReliability.HIGH,
        )
        assert second.created == 0
        assert second.skipped_duplicates == 2


# ─────────────────────────── Deduplication ──────────────────────────────────

class TestDeduplication:
    def _make_finding(self, adapter_name: str, title: str, target_id: str = "t1") -> Finding:
        return Finding(
            target_id=target_id,
            adapter_name=adapter_name,
            finding_type=FindingType.DNS,
            title=title,
            description="desc",
            severity=Severity.INFO,
        )

    def test_add_findings_batch_no_duplicates(self, case_service):
        case = case_service.create_case("Dedup Test")
        findings = [
            self._make_finding("dns", "A Record"),
            self._make_finding("dns", "MX Record"),
        ]
        added, skipped = case_service.add_findings_batch(case.id, findings)
        assert len(added) == 2
        assert skipped == 0

    def test_add_findings_batch_skips_duplicates(self, case_service):
        case = case_service.create_case("Dedup Skip Test")
        f = self._make_finding("dns", "A Record: example.com")
        # Add once
        case_service.add_findings_batch(case.id, [f])
        # Add same finding again
        f2 = self._make_finding("dns", "A Record: example.com")
        added, skipped = case_service.add_findings_batch(case.id, [f2])
        assert len(added) == 0
        assert skipped == 1
        # Only 1 finding in DB
        loaded = case_service.get_case(case.id)
        assert len(loaded.findings) == 1

    def test_add_findings_batch_deduplicates_within_batch(self, case_service):
        case = case_service.create_case("Within Batch Dedup")
        # Two findings with the same key in the same batch
        findings = [
            self._make_finding("dns", "A Record"),
            self._make_finding("dns", "A Record"),  # duplicate
        ]
        added, skipped = case_service.add_findings_batch(case.id, findings)
        assert len(added) == 1
        assert skipped == 1

    def test_different_adapters_not_deduplicated(self, case_service):
        case = case_service.create_case("Different Adapters")
        findings = [
            self._make_finding("dns", "A Record"),
            self._make_finding("http", "A Record"),  # same title, different adapter
        ]
        added, skipped = case_service.add_findings_batch(case.id, findings)
        assert len(added) == 2
        assert skipped == 0

    def test_add_finding_compat_method(self, case_service):
        """add_finding (single) is a wrapper around add_findings_batch."""
        case = case_service.create_case("Single Finding")
        f = self._make_finding("dns", "NS Record")
        case_service.add_finding(case.id, f)
        loaded = case_service.get_case(case.id)
        assert len(loaded.findings) == 1


# ─────────────────────────── InvestigationService ───────────────────────────

class TestInvestigationService:
    async def test_run_adapters_domain(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        findings = await investigation_service.run_adapters(target)
        assert isinstance(findings, list)
        assert len(findings) > 0

    async def test_run_adapters_filtered(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        findings = await investigation_service.run_adapters(target, adapter_names=["dns"])
        assert all(f.adapter_name == "dns" for f in findings)

    async def test_run_adapters_username(self, investigation_service):
        target = Target(type=TargetType.USERNAME, value="johndoe")
        findings = await investigation_service.run_adapters(target)
        assert len(findings) > 0
        assert all(f.adapter_name == "social" for f in findings)

    async def test_run_preset_domain_intelligence(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        findings = await investigation_service.run_preset(target, InvestigationPreset.DOMAIN_INTELLIGENCE)
        assert len(findings) > 0
        adapter_names = {f.adapter_name for f in findings}
        assert "dns" in adapter_names

    async def test_run_preset_username_investigation(self, investigation_service):
        target = Target(type=TargetType.USERNAME, value="testuser")
        findings = await investigation_service.run_preset(target, InvestigationPreset.USERNAME_INVESTIGATION)
        assert len(findings) > 0
        assert all(f.adapter_name == "social" for f in findings)

    async def test_run_preset_infrastructure_mapping(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        findings = await investigation_service.run_preset(target, InvestigationPreset.INFRASTRUCTURE_MAPPING)
        adapter_names = {f.adapter_name for f in findings}
        assert "dns" in adapter_names
        assert "http" in adapter_names

    async def test_run_preset_document_metadata(self, investigation_service):
        target = Target(type=TargetType.DOCUMENT, value="/tmp/report.pdf")
        findings = await investigation_service.run_preset(target, InvestigationPreset.DOCUMENT_METADATA_AUDIT)
        assert len(findings) > 0
        assert all(f.adapter_name == "metadata" for f in findings)

    def test_get_active_adapters_domain(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        adapters = investigation_service.get_active_adapters(target)
        names = {a.name for a in adapters}
        assert "dns" in names
        assert "cert" in names
        assert "social" not in names

    def test_get_active_adapters_filtered(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        adapters = investigation_service.get_active_adapters(target, adapter_names=["dns"])
        assert len(adapters) == 1
        assert adapters[0].name == "dns"

    def test_get_active_adapters_no_match(self, investigation_service):
        target = Target(type=TargetType.USERNAME, value="johndoe")
        adapters = investigation_service.get_active_adapters(target, adapter_names=["dns"])
        assert adapters == []

    async def test_execute_investigation_records_run_metadata(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        execution = await investigation_service.execute_investigation(target, case_id="case-1")

        assert len(execution.adapter_runs) > 0
        assert len(execution.findings) > 0
        assert execution.successful_runs > 0
        assert execution.failed_runs == 0

        run_ids = {run.id for run in execution.adapter_runs}
        for run in execution.adapter_runs:
            assert run.status == AdapterRunStatus.COMPLETE
            assert run.duration_seconds >= 0
            assert run.case_id == "case-1"

        for finding in execution.findings:
            assert finding.adapter_run_id in run_ids

    async def test_execute_investigation_partial_failure_isolated(self):
        service = InvestigationService([DnsAdapter(), FailingDomainAdapter()])
        target = Target(type=TargetType.DOMAIN, value="example.com")

        execution = await service.execute_investigation(target, case_id="case-2")
        assert len(execution.adapter_runs) == 2
        assert execution.failed_runs == 1
        assert execution.successful_runs == 1
        assert len(execution.findings) > 0

        failed = [run for run in execution.adapter_runs if run.status == AdapterRunStatus.FAILED]
        assert len(failed) == 1
        assert failed[0].adapter_name == "failing"
        assert "Simulated failure" in failed[0].error_message

    async def test_execute_adapter_timeout_marks_failed_run(self):
        service = InvestigationService([HangingDomainAdapter()], adapter_timeout_seconds=0.05)
        target = Target(type=TargetType.DOMAIN, value="example.com")

        findings, run = await service.execute_adapter(
            service.get_active_adapters(target)[0],
            target,
            case_id="case-timeout",
        )

        assert findings == []
        assert run.status == AdapterRunStatus.FAILED
        assert "timed out" in run.error_message


class TestFindingsService:
    def _make_findings(self):
        return [
            Finding(
                target_id="t1",
                adapter_name="dns",
                finding_type=FindingType.DNS,
                title="A Record",
                description="ipv4",
                severity=Severity.HIGH,
                review_state=FindingReviewState.NEW,
                collected_at="2026-03-01T10:00:00+00:00",
            ),
            Finding(
                target_id="t2",
                adapter_name="http",
                finding_type=FindingType.HTTP,
                title="Missing Header",
                description="security header missing",
                severity=Severity.MEDIUM,
                review_state=FindingReviewState.REVIEWED,
                collected_at="2026-03-01T09:00:00+00:00",
            ),
            Finding(
                target_id="t1",
                adapter_name="social",
                finding_type=FindingType.SOCIAL,
                title="Profile Found",
                description="account discovered",
                severity=Severity.LOW,
                review_state=FindingReviewState.FLAGGED,
                collected_at="2026-03-01T08:00:00+00:00",
            ),
        ]

    def test_apply_filters_by_state_and_adapter(self, findings_service):
        findings = self._make_findings()
        finding_filter = FindingFilter(
            review_state=FindingReviewState.NEW,
            adapter_name="dns",
        )
        filtered = findings_service.apply_filters(findings, finding_filter)
        assert len(filtered) == 1
        assert filtered[0].title == "A Record"

    def test_apply_filters_text_query(self, findings_service):
        findings = self._make_findings()
        finding_filter = FindingFilter(text_query="header")
        filtered = findings_service.apply_filters(findings, finding_filter)
        assert len(filtered) == 1
        assert filtered[0].adapter_name == "http"

    def test_sort_by_severity(self, findings_service):
        findings = self._make_findings()
        sorted_findings = findings_service.sort_findings(
            findings,
            FindingSortBy.SEVERITY,
            target_labels={"t1": "alpha", "t2": "bravo"},
        )
        assert sorted_findings[0].severity == Severity.HIGH

    def test_sort_by_target(self, findings_service):
        findings = self._make_findings()
        sorted_findings = findings_service.sort_findings(
            findings,
            FindingSortBy.TARGET,
            target_labels={"t1": "zeta", "t2": "alpha"},
        )
        assert sorted_findings[0].target_id == "t2"

    def test_summarize_triage(self, findings_service):
        findings = self._make_findings()
        summary = findings_service.summarize_triage(findings)
        assert summary.total == 3
        assert summary.new == 1
        assert summary.reviewed == 1
        assert summary.flagged == 1
        assert summary.dismissed == 0
        assert summary.high_unreviewed == 1


# ─────────────────────────── Normalization ───────────────────────────────────

def _finding(ftype: FindingType, data: dict, *, target_id: str = "t1") -> Finding:
    return Finding(
        target_id=target_id,
        adapter_name="test",
        finding_type=ftype,
        title="test",
        description="desc",
        severity=Severity.INFO,
        data=data,
    )


class TestNormalization:
    def test_dns_a_record_extracts_ip(self):
        f = _finding(FindingType.DNS, {"record_type": "A", "value": "1.2.3.4"})
        entities = extract_entities(f)
        assert any(e.entity_type == "ip" and e.value == "1.2.3.4" for e in entities)

    def test_dns_ns_record_extracts_domains(self):
        f = _finding(FindingType.DNS, {"record_type": "NS", "value": ["ns1.example.com", "ns2.example.com"]})
        entities = extract_entities(f)
        values = [e.value for e in entities if e.entity_type == "domain"]
        assert "ns1.example.com" in values
        assert "ns2.example.com" in values

    def test_cert_extracts_sans_and_issuer(self):
        f = _finding(
            FindingType.CERTIFICATE,
            {"sans": ["www.example.com", "api.example.com"], "issuer": "Let's Encrypt"},
        )
        entities = extract_entities(f)
        subdomains = [e.value for e in entities if e.entity_type == "subdomain"]
        assert "www.example.com" in subdomains
        orgs = [e.value for e in entities if e.entity_type == "organization"]
        assert "Let's Encrypt" in orgs

    def test_subdomain_extracts_subdomain_and_ip(self):
        f = _finding(FindingType.SUBDOMAIN, {"subdomain": "dev.example.com", "ip": "10.0.0.1"})
        entities = extract_entities(f)
        assert any(e.entity_type == "subdomain" for e in entities)
        assert any(e.entity_type == "ip" for e in entities)

    def test_http_extracts_server_and_tech(self):
        f = _finding(FindingType.HTTP, {"server": "nginx/1.24", "technologies": ["React", "Node.js"]})
        entities = extract_entities(f)
        software = [e.value for e in entities if e.entity_type == "software"]
        assert "nginx/1.24" in software
        assert "React" in software
        assert "Node.js" in software

    def test_social_extracts_platform(self):
        f = _finding(FindingType.SOCIAL, {"platform": "GitHub"})
        entities = extract_entities(f)
        assert any(e.entity_type == "platform" and e.value == "GitHub" for e in entities)

    def test_metadata_extracts_person_and_org(self):
        f = _finding(FindingType.METADATA, {"author": "Alice", "company": "Acme Corp"})
        entities = extract_entities(f)
        persons = [e.value for e in entities if e.entity_type == "person"]
        orgs = [e.value for e in entities if e.entity_type == "organization"]
        assert "Alice" in persons
        assert "Acme Corp" in orgs

    def test_build_entity_map_deduplicates(self):
        """Same IP appearing in two findings should produce one entity node."""
        case = Case(name="Dedup Entity")
        f1 = _finding(FindingType.DNS, {"record_type": "A", "value": "1.1.1.1"})
        f2 = _finding(FindingType.SUBDOMAIN, {"subdomain": "www.example.com", "ip": "1.1.1.1"})
        case.findings = [f1, f2]
        entity_map = build_entity_map(case)
        assert "ip:1.1.1.1" in entity_map
        # Source IDs from both findings merged
        assert len(entity_map["ip:1.1.1.1"].source_finding_ids) == 2

    def test_extract_case_summary(self):
        case = Case(name="Summary")
        case.findings = [
            _finding(FindingType.DNS, {"record_type": "A", "value": "8.8.8.8"}),
            _finding(FindingType.SOCIAL, {"platform": "Twitter/X"}),
        ]
        summary = extract_case_summary(case)
        assert "8.8.8.8" in summary["ips"]
        assert "Twitter/X" in summary["platforms"]


# ─────────────────────────── GraphService ────────────────────────────────────

class TestGraphService:
    def _make_case_with_dns_findings(self) -> Case:
        case = Case(name="Graph Test")
        target = Target(type=TargetType.DOMAIN, value="example.com")
        case.targets = [target]
        case.findings = [
            Finding(
                target_id=target.id,
                adapter_name="dns",
                finding_type=FindingType.DNS,
                title="A Record",
                description="desc",
                severity=Severity.INFO,
                data={"record_type": "A", "value": "93.184.216.34"},
            ),
            Finding(
                target_id=target.id,
                adapter_name="subdomain",
                finding_type=FindingType.SUBDOMAIN,
                title="Subdomain: www.example.com",
                description="desc",
                severity=Severity.INFO,
                data={"subdomain": "www.example.com", "ip": "93.184.216.34"},
            ),
        ]
        return case

    def test_graph_has_case_and_target_nodes(self):
        gs = GraphService()
        case = self._make_case_with_dns_findings()
        G = gs.build_graph(case)
        assert f"case:{case.id}" in G.nodes
        assert f"target:{case.targets[0].id}" in G.nodes

    def test_graph_has_entity_nodes(self):
        gs = GraphService()
        case = self._make_case_with_dns_findings()
        G = gs.build_graph(case)
        node_ids = list(G.nodes)
        # The IP 93.184.216.34 should appear as a node (from both DNS and subdomain findings)
        assert "ip:93.184.216.34" in node_ids

    def test_graph_has_subdomain_node(self):
        gs = GraphService()
        case = self._make_case_with_dns_findings()
        G = gs.build_graph(case)
        assert "subdomain:www.example.com" in G.nodes

    def test_get_node_data_structure(self):
        gs = GraphService()
        case = self._make_case_with_dns_findings()
        data = gs.get_node_data(case)
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_empty_case_graph(self):
        gs = GraphService()
        case = Case(name="Empty")
        G = gs.build_graph(case)
        assert f"case:{case.id}" in G.nodes
        assert len(G.nodes) == 1


# ─────────────────────────── ReportService ───────────────────────────────────

class TestReportService:
    def _make_populated_case(self) -> Case:
        from app.models.case import Note
        case = Case(name="Report Test", description="Test case for report generation")
        target = Target(type=TargetType.DOMAIN, value="example.com")
        case.targets = [target]
        case.findings = [
            Finding(
                target_id=target.id,
                adapter_name="dns",
                finding_type=FindingType.DNS,
                title="A Record",
                description="IPv4 address",
                severity=Severity.INFO,
                review_state=FindingReviewState.FLAGGED,
                decision_state=FindingDecisionState.CORRELATED,
                decision_confidence=0.76,
                decision_rationale="Linked to promoted evidence",
                analyst_note="Critical infra mapping artifact",
                data={"record_type": "A", "value": "93.184.216.34"},
                source_url="https://example.com",
                source_name="DNS Lookup",
            ),
            Finding(
                target_id=target.id,
                adapter_name="http",
                finding_type=FindingType.HTTP,
                title="Missing Security Headers",
                description="Headers missing",
                severity=Severity.MEDIUM,
                review_state=FindingReviewState.DISMISSED,
                decision_state=FindingDecisionState.NOT_ACTIONABLE,
                decision_confidence=0.25,
                decision_rationale="Staging environment false positive",
                analyst_note="Accepted risk for staging system",
                data={},
            ),
        ]
        case.notes = [Note(case_id=case.id, content="Analyst observation: interesting target")]
        case.workflow_stage = WorkflowStage.REPORTING
        case.workflow_stage_note = "Drafting report package"
        case.mission_intake.mission_summary = "Assess exposure and reporting readiness"
        case.mission_intake.objectives = ["Collect findings", "Promote evidence"]
        case.mission_intake.hypotheses = ["Credential leaks are externally discoverable"]
        case.mission_intake.scope = "example.com external footprint"
        case.mission_intake.constraints = "No active exploitation"
        case.mission_intake.legal_operational_notes = "OSINT-only collection"
        case.mission_intake.risk_notes = "High impact if credentials are exposed"
        case.mission_intake.priority = MissionPriority.HIGH
        case.mission_intake.tasks = [
            MissionTask(title="Complete triage", completed=True),
            MissionTask(title="Finalize executive summary", completed=False),
        ]
        case.saved_searches = [
            SavedSearch(
                case_id=case.id,
                target_id=target.id,
                title="Credential Exposure Sweep",
                query='site:pastebin.com "example.com" "password"',
                explanation="Looks for possible credential leaks tied to the domain.",
                intent=SearchIntent.CREDENTIAL_MENTION,
                provider=SearchProvider.GOOGLE,
                analyst_note="Run before each escalation checkpoint.",
            )
        ]
        case.entities = [
            Entity(
                case_id=case.id,
                kind=EntityKind.USERNAME,
                value="octo_user",
                display_name="octo_user",
                metadata={"source": "entity_research"},
                tags=["entity_research"],
            ),
            Entity(
                case_id=case.id,
                kind=EntityKind.PHONE,
                value="+1 415 555 0101",
                display_name="+1 415 555 0101",
                metadata={"source": "entity_research"},
                tags=["entity_research"],
            ),
        ]
        case.evidence = [
            Evidence(
                case_id=case.id,
                entity_id=case.entities[0].id,
                finding_id=case.findings[0].id,
                description="social_provider: github profile found",
                source_reliability=SourceReliability.MEDIUM,
                raw_json_data={
                    "workflow": "entity_research",
                    "provider_name": "social_provider",
                },
                normalized_summary="GitHub profile reference identified",
            )
        ]
        case.finding_evidence_links = [
            FindingEvidenceLink(
                case_id=case.id,
                finding_id=case.findings[0].id,
                evidence_id=case.evidence[0].id,
                support_confidence=0.78,
                rationale="Provider output supports DNS signal",
            )
        ]
        case.leads = [
            LeadProfile(
                case_id=case.id,
                kind="USERNAME",
                canonical_value="octo_user",
                display_label="octo_user",
                lifecycle_state=LeadLifecycleState.ACTIVE,
                priority=LeadPriority.HIGH,
                confidence_score=0.8,
                context_summary="Observed in social and finding evidence",
                why_it_matters="Likely operator account used across services",
                linked_target_ids=[target.id],
                linked_entity_ids=[case.entities[0].id],
            )
        ]
        return case

    def test_generate_html(self, tmp_path):
        rs = ReportService()
        case = self._make_populated_case()
        out = str(tmp_path / "report.html")
        rs.generate_html(case, out)
        content = (tmp_path / "report.html").read_text(encoding="utf-8")
        assert "Report Test" in content
        assert "A Record" in content
        assert "Analyst Notes" in content
        assert "Analyst observation" in content
        assert "Discovered Entities" in content
        assert "93.184.216.34" in content
        assert "Flagged Findings" in content
        assert "Dismissed Findings" in content
        assert "Guided Search Activity" in content
        assert "Case Activity Timeline" in content
        assert "Entity Research Workspace Activity" in content
        assert "Promoted Research Evidence" in content
        assert "Credential Exposure Sweep" in content
        assert "site:pastebin.com" in content
        assert "Mission Framing" in content
        assert "Workflow Stage" in content
        assert "Operational Snapshot" in content
        assert "Subjects Of Interest" in content
        assert "Finding-Evidence Convergence" in content
        assert "Major Supported Findings" in content
        assert "Assess exposure and reporting readiness" in content
        assert "Phone Pivots" in content
        assert "Email Pivots" in content

    def test_generate_json(self, tmp_path):
        import json as _json
        rs = ReportService()
        case = self._make_populated_case()
        out = str(tmp_path / "report.json")
        rs.generate_json(case, out)
        data = _json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
        assert data["name"] == "Report Test"
        assert len(data["findings"]) == 2

    def test_generate_csv(self, tmp_path):
        import csv as _csv
        rs = ReportService()
        case = self._make_populated_case()
        out = str(tmp_path / "report.csv")
        rs.generate_csv(case, out)
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(_csv.DictReader(f))
        assert len(rows) == 2
        titles = [r["title"] for r in rows]
        assert "A Record" in titles
        assert "Missing Security Headers" in titles
        # Verify source_url column exists
        assert "source_url" in rows[0]
        assert "review_state" in rows[0]
        assert "analyst_note" in rows[0]
        assert "decision_state" in rows[0]
        assert "decision_confidence" in rows[0]

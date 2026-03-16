import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from app.models.case import (
    ArtifactLinkType,
    AdapterRun,
    Case,
    CaseStatus,
    Finding,
    FindingDecisionState,
    FindingEvidenceLink,
    FindingReviewState,
    Entity,
    EvidenceAttachment,
    EvidenceAttachmentType,
    Evidence,
    MissionIntake,
    MissionPriority,
    MissionTask,
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
    Target,
    TargetType,
    WorkflowStage,
)
from app.services.convergence_service import (
    ConvergenceSummary,
    EvidenceSupportView,
    FindingSupportView,
    ConvergenceService,
)
from app.services.findings_service import FindingsService, TriageSummary
from app.services.lead_workspace_service import (
    LeadDetail,
    LeadListItem,
    LeadWorkspaceFilter,
    LeadWorkspaceService,
)
from app.services.timeline_service import TimelineEvent, TimelineService
from app.storage.database import Database


class SearchActivitySummary:
    def __init__(
        self,
        total: int,
        linked_targets: int,
        last_created_at: datetime | None,
    ):
        self.total = total
        self.linked_targets = linked_targets
        self.last_created_at = last_created_at


class EntityActivitySummary:
    def __init__(
        self,
        total_entities: int,
        research_evidence_total: int,
        last_research_at: datetime | None,
    ):
        self.total_entities = total_entities
        self.research_evidence_total = research_evidence_total
        self.last_research_at = last_research_at


class DashboardSignalSummary:
    def __init__(
        self,
        timeline_health: str,
        recent_activity_count: int,
        unresolved_high_risk: int,
        flagged_findings: int,
        new_findings: int,
        reviewed_findings: int,
        saved_searches: int,
        researched_entities: int,
        evidence_total: int,
        evidence_recent_7d: int,
        correlated_findings: int,
        unsupported_findings: int,
        low_confidence_findings: int,
        unlinked_evidence: int,
        evidence_attachments_total: int,
        evidence_without_attachments: int,
        checklist_total: int,
        checklist_completed: int,
        reporting_readiness: str,
    ):
        self.timeline_health = timeline_health
        self.recent_activity_count = recent_activity_count
        self.unresolved_high_risk = unresolved_high_risk
        self.flagged_findings = flagged_findings
        self.new_findings = new_findings
        self.reviewed_findings = reviewed_findings
        self.saved_searches = saved_searches
        self.researched_entities = researched_entities
        self.evidence_total = evidence_total
        self.evidence_recent_7d = evidence_recent_7d
        self.correlated_findings = correlated_findings
        self.unsupported_findings = unsupported_findings
        self.low_confidence_findings = low_confidence_findings
        self.unlinked_evidence = unlinked_evidence
        self.evidence_attachments_total = evidence_attachments_total
        self.evidence_without_attachments = evidence_without_attachments
        self.checklist_total = checklist_total
        self.checklist_completed = checklist_completed
        self.reporting_readiness = reporting_readiness


class DashboardSummary:
    def __init__(
        self,
        case_id: str,
        mission_intake: MissionIntake,
        workflow_stage: WorkflowStage,
        workflow_stage_note: str,
        workflow_stage_updated_at: datetime,
        signals: DashboardSignalSummary,
        recent_activity: list[TimelineEvent],
        recommended_actions: list[str],
        featured_collection_actions: list[str],
        onboarding_hint: str,
    ):
        self.case_id = case_id
        self.mission_intake = mission_intake
        self.workflow_stage = workflow_stage
        self.workflow_stage_note = workflow_stage_note
        self.workflow_stage_updated_at = workflow_stage_updated_at
        self.signals = signals
        self.recent_activity = recent_activity
        self.recommended_actions = recommended_actions
        self.featured_collection_actions = featured_collection_actions
        self.onboarding_hint = onboarding_hint


_WORKFLOW_TRANSITIONS: dict[WorkflowStage, set[WorkflowStage]] = {
    WorkflowStage.INTAKE: {WorkflowStage.INTAKE, WorkflowStage.COLLECTION},
    WorkflowStage.COLLECTION: {WorkflowStage.INTAKE, WorkflowStage.COLLECTION, WorkflowStage.REVIEW},
    WorkflowStage.REVIEW: {WorkflowStage.COLLECTION, WorkflowStage.REVIEW, WorkflowStage.REPORTING},
    WorkflowStage.REPORTING: {WorkflowStage.REVIEW, WorkflowStage.REPORTING, WorkflowStage.ARCHIVE_READY},
    WorkflowStage.ARCHIVE_READY: {WorkflowStage.REPORTING, WorkflowStage.ARCHIVE_READY},
}

_PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)")


class CaseService:
    def __init__(self, db: Database):
        self.db = db
        self.findings_service = FindingsService()
        self.timeline_service = TimelineService()
        self.lead_workspace_service = LeadWorkspaceService(db)
        self.convergence_service = ConvergenceService(db)

    def create_case(self, name: str, description: str = "") -> Case:
        case = Case(name=name, description=description)
        self.db.save_case(case)
        return case

    def get_case(self, case_id: str) -> Case:
        return self.db.load_case(case_id)

    def list_cases(self) -> list[Case]:
        return self.db.list_cases()

    def update_case(self, case: Case):
        case.updated_at = datetime.now(timezone.utc)
        self.db.save_case(case)

    def delete_case(self, case_id: str):
        self.db.delete_case(case_id)

    def add_target(self, case_id: str, target_type: TargetType, value: str) -> Target:
        case = self.db.load_case(case_id)
        target = Target(type=target_type, value=value)
        case.targets.append(target)
        case.updated_at = datetime.now(timezone.utc)
        self.db.save_case(case)
        return target

    def add_note(self, case_id: str, content: str) -> Note:
        case = self.db.load_case(case_id)
        note = Note(case_id=case_id, content=content)
        case.notes.append(note)
        case.updated_at = datetime.now(timezone.utc)
        self.db.save_case(case)
        return note

    def add_finding(self, case_id: str, finding: Finding):
        """Add a single finding.  Prefer add_findings_batch for bulk inserts."""
        self.add_findings_batch(case_id, [finding])

    def add_findings_batch(
        self, case_id: str, findings: list[Finding]
    ) -> tuple[list[Finding], int]:
        """
        Add multiple findings to a case, skipping semantic duplicates.

        Two findings are considered duplicates when they share the same
        (adapter_name, finding_type, title) within the same case.

        Returns:
            (added_findings, skipped_count)
        """
        existing = self.db.get_findings_for_case(case_id)
        # Build a set of (adapter_name, finding_type, title) keys already stored
        existing_keys: set[tuple[str, str, str]] = {
            (f.adapter_name, f.finding_type.value, f.title) for f in existing
        }

        to_add: list[Finding] = []
        skipped = 0
        for f in findings:
            key = (f.adapter_name, f.finding_type.value, f.title)
            if key in existing_keys:
                skipped += 1
            else:
                to_add.append(f)
                existing_keys.add(key)  # prevent within-batch duplicates too

        for f in to_add:
            self.db.save_finding(f, case_id)

        if to_add:
            self.db.update_case_timestamp(case_id)

        return to_add, skipped

    def save_adapter_runs(self, case_id: str, runs: list[AdapterRun]) -> None:
        for run in runs:
            run.case_id = case_id
            self.db.save_adapter_run(run)

        if runs:
            self.db.update_case_timestamp(case_id)

    def update_finding_triage(
        self,
        case_id: str,
        finding_id: str,
        review_state: FindingReviewState,
        analyst_note: str = "",
    ) -> None:
        case = self.db.load_case(case_id)
        if not any(f.id == finding_id for f in case.findings):
            raise ValueError(f"Finding {finding_id} not found in case {case_id}")

        self.db.update_finding_triage(finding_id, review_state, analyst_note)
        self.db.update_case_timestamp(case_id)

    def update_finding_decision(
        self,
        case_id: str,
        finding_id: str,
        decision_state: FindingDecisionState,
        decision_confidence: float,
        decision_rationale: str = "",
    ) -> Finding:
        return self.convergence_service.update_finding_decision(
            case_id,
            finding_id,
            decision_state=decision_state,
            decision_confidence=decision_confidence,
            decision_rationale=decision_rationale,
        )

    def get_finding_support(self, case_id: str, finding_id: str) -> FindingSupportView:
        return self.convergence_service.get_finding_support(case_id, finding_id)

    def get_evidence_support(self, case_id: str, evidence_id: str) -> EvidenceSupportView:
        return self.convergence_service.get_evidence_support(case_id, evidence_id)

    def correlate_finding_to_evidence(
        self,
        case_id: str,
        finding_id: str,
        evidence_id: str,
        *,
        rationale: str = "",
        support_confidence: float = 0.5,
        origin: SupportLinkOrigin = SupportLinkOrigin.MANUAL_CORRELATION,
    ) -> FindingEvidenceLink:
        return self.convergence_service.correlate_finding_to_evidence(
            case_id,
            finding_id,
            evidence_id,
            rationale=rationale,
            support_confidence=support_confidence,
            origin=origin,
        )

    def promote_finding_to_evidence(
        self,
        case_id: str,
        finding_id: str,
        *,
        rationale: str = "",
        support_confidence: float = 0.6,
        source_reliability: SourceReliability = SourceReliability.MEDIUM,
    ) -> tuple[Evidence, FindingEvidenceLink, bool]:
        return self.convergence_service.promote_finding_to_evidence(
            case_id,
            finding_id,
            rationale=rationale,
            support_confidence=support_confidence,
            source_reliability=source_reliability,
        )

    def get_case_convergence_summary(self, case_id: str) -> ConvergenceSummary:
        return self.convergence_service.get_case_convergence_summary(case_id)

    def get_case_triage_summary(self, case_id: str) -> TriageSummary:
        findings = self.db.get_findings_for_case(case_id)
        return self.findings_service.summarize_triage(findings)

    def create_saved_search(
        self,
        case_id: str,
        title: str,
        query: str,
        explanation: str,
        intent: SearchIntent,
        provider: SearchProvider = SearchProvider.GOOGLE,
        target_id: str | None = None,
        tags: list[str] | None = None,
        analyst_note: str = "",
    ) -> SavedSearch:
        search = SavedSearch(
            case_id=case_id,
            target_id=target_id,
            title=title,
            provider=provider,
            intent=intent,
            query=query,
            explanation=explanation,
            tags=tags or [],
            analyst_note=analyst_note,
        )
        self.db.save_saved_search(search)
        self.db.update_case_timestamp(case_id)
        return search

    def update_saved_search(self, search: SavedSearch) -> None:
        case = self.db.load_case(search.case_id)
        if not any(existing.id == search.id for existing in case.saved_searches):
            raise ValueError(f"Saved search {search.id} not found in case {search.case_id}")

        search.updated_at = datetime.now(timezone.utc)
        self.db.save_saved_search(search)
        self.db.update_case_timestamp(search.case_id)

    def list_saved_searches(self, case_id: str) -> list[SavedSearch]:
        return self.db.get_saved_searches_for_case(case_id)

    def delete_saved_search(self, case_id: str, search_id: str) -> None:
        self.db.delete_saved_search(search_id, case_id)
        self.db.update_case_timestamp(case_id)

    def get_case_search_summary(self, case_id: str) -> SearchActivitySummary:
        saved_searches = self.db.get_saved_searches_for_case(case_id)
        linked_targets = sum(1 for search in saved_searches if search.target_id)
        last_created_at = saved_searches[0].created_at if saved_searches else None
        return SearchActivitySummary(
            total=len(saved_searches),
            linked_targets=linked_targets,
            last_created_at=last_created_at,
        )

    def list_entities(self, case_id: str) -> list[Entity]:
        return self.db.get_entities_for_case(case_id)

    def list_evidence(self, case_id: str) -> list[Evidence]:
        return self.db.get_evidence_for_case(case_id)

    def list_evidence_attachments(
        self,
        case_id: str,
        evidence_id: str | None = None,
    ) -> list[EvidenceAttachment]:
        if evidence_id:
            return self.db.get_evidence_attachments_for_evidence(case_id, evidence_id)
        return self.db.get_evidence_attachments_for_case(case_id)

    def add_evidence_attachment(
        self,
        case_id: str,
        evidence_id: str,
        *,
        attachment_type: EvidenceAttachmentType,
        file_path: str = "",
        source_url: str = "",
        media_title: str = "",
        media_type: str = "",
        provenance_note: str = "",
        metadata: dict | None = None,
    ) -> EvidenceAttachment:
        case = self.db.load_case(case_id)
        if not any(item.id == evidence_id for item in case.evidence):
            raise ValueError(f"Evidence {evidence_id} not found in case {case_id}")

        now = datetime.now(timezone.utc)
        url_value = source_url.strip()
        path_value = file_path.strip()
        existing = next(
            (
                item
                for item in case.evidence_attachments
                if item.evidence_id == evidence_id
                and item.attachment_type == attachment_type
                and item.source_url.strip() == url_value
                and item.file_path.strip() == path_value
            ),
            None,
        )
        if existing is not None:
            existing.media_title = media_title.strip()
            existing.media_type = media_type.strip()
            existing.source_platform = self._platform_from_url(url_value)
            existing.provenance_note = provenance_note.strip() or existing.provenance_note
            existing.metadata = metadata or existing.metadata
            existing.updated_at = now
            self.db.save_evidence_attachment(existing)
            self.db.update_case_timestamp(case_id)
            return existing

        attachment = EvidenceAttachment(
            case_id=case_id,
            evidence_id=evidence_id,
            attachment_type=attachment_type,
            file_path=path_value,
            source_url=url_value,
            media_title=media_title.strip(),
            media_type=media_type.strip(),
            source_platform=self._platform_from_url(url_value),
            provenance_note=provenance_note.strip(),
            metadata=metadata or {},
            captured_at=now,
            created_at=now,
            updated_at=now,
        )
        self.db.save_evidence_attachment(attachment)
        self.db.update_case_timestamp(case_id)
        return attachment

    def attach_file_to_evidence(
        self,
        case_id: str,
        evidence_id: str,
        file_path: str,
        provenance_note: str = "",
    ) -> EvidenceAttachment:
        cleaned_path = file_path.strip()
        suffix = Path(cleaned_path).suffix.lower()
        attachment_type = EvidenceAttachmentType.FILE
        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
            attachment_type = EvidenceAttachmentType.IMAGE
            if "screen" in Path(cleaned_path).name.lower():
                attachment_type = EvidenceAttachmentType.SCREENSHOT

        return self.add_evidence_attachment(
            case_id,
            evidence_id,
            attachment_type=attachment_type,
            file_path=cleaned_path,
            provenance_note=provenance_note,
            metadata={"capture_method": "local_file_attach"},
        )

    def capture_public_media_evidence(
        self,
        case_id: str,
        source_url: str,
        *,
        finding_id: str | None = None,
        evidence_id: str | None = None,
        media_title: str = "",
        media_type: str = "",
        provenance_note: str = "",
        screenshot_file_path: str = "",
        source_reliability: SourceReliability = SourceReliability.MEDIUM,
    ) -> tuple[Evidence, list[EvidenceAttachment], bool]:
        case = self.db.load_case(case_id)
        url_value = source_url.strip()
        if not url_value:
            raise ValueError("Source URL is required for public-media capture")

        target_evidence = next((item for item in case.evidence if item.id == evidence_id), None)
        created_new = False
        if target_evidence is None:
            platform = self._platform_from_url(url_value) or "public-web"
            title = media_title.strip() or url_value
            target_evidence = Evidence(
                case_id=case_id,
                finding_id=finding_id,
                description=f"Public media capture: {title}",
                source_reliability=source_reliability,
                normalized_summary=f"{platform} reference captured via URL",
                raw_json_data={
                    "workflow": "public_media_capture",
                    "source_url": url_value,
                    "source_platform": platform,
                    "media_title": media_title.strip(),
                    "media_type": media_type.strip(),
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            self.db.save_evidence(target_evidence)
            created_new = True

        attachments: list[EvidenceAttachment] = []
        attachments.append(
            self.add_evidence_attachment(
                case_id,
                target_evidence.id,
                attachment_type=EvidenceAttachmentType.PUBLIC_MEDIA,
                source_url=url_value,
                media_title=media_title,
                media_type=media_type,
                provenance_note=provenance_note,
                metadata={"capture_method": "url_submission"},
            )
        )

        if screenshot_file_path.strip():
            attachments.append(
                self.add_evidence_attachment(
                    case_id,
                    target_evidence.id,
                    attachment_type=EvidenceAttachmentType.SCREENSHOT,
                    file_path=screenshot_file_path.strip(),
                    source_url=url_value,
                    media_title=media_title,
                    media_type=media_type,
                    provenance_note=(provenance_note or "Screenshot captured during URL collection"),
                    metadata={"capture_method": "url_plus_screenshot"},
                )
            )

        self.db.update_case_timestamp(case_id)
        return target_evidence, attachments, created_new

    def get_case_entity_activity_summary(self, case_id: str) -> EntityActivitySummary:
        entities = self.db.get_entities_for_case(case_id)
        evidence = self.db.get_evidence_for_case(case_id)
        research_evidence = [
            item
            for item in evidence
            if item.raw_json_data.get("workflow") == "entity_research"
        ]
        last_research_at = research_evidence[0].collected_at if research_evidence else None
        return EntityActivitySummary(
            total_entities=len(entities),
            research_evidence_total=len(research_evidence),
            last_research_at=last_research_at,
        )

    def get_case_timeline(self, case_id: str, limit: int | None = None) -> list[TimelineEvent]:
        case = self.db.load_case(case_id)
        return self.timeline_service.build_case_timeline(case, limit=limit)

    def update_mission_intake(
        self,
        case_id: str,
        *,
        mission_summary: str | None = None,
        objectives: list[str] | None = None,
        hypotheses: list[str] | None = None,
        scope: str | None = None,
        constraints: str | None = None,
        legal_operational_notes: str | None = None,
        risk_notes: str | None = None,
        priority: MissionPriority | None = None,
        intake_notes: str | None = None,
    ) -> MissionIntake:
        case = self.db.load_case(case_id)
        intake = case.mission_intake

        if mission_summary is not None:
            intake.mission_summary = mission_summary.strip()
        if objectives is not None:
            intake.objectives = [item.strip() for item in objectives if item.strip()]
        if hypotheses is not None:
            intake.hypotheses = [item.strip() for item in hypotheses if item.strip()]
        if scope is not None:
            intake.scope = scope.strip()
        if constraints is not None:
            intake.constraints = constraints.strip()
        if legal_operational_notes is not None:
            intake.legal_operational_notes = legal_operational_notes.strip()
        if risk_notes is not None:
            intake.risk_notes = risk_notes.strip()
        if priority is not None:
            intake.priority = priority
        if intake_notes is not None:
            intake.intake_notes = intake_notes.strip()

        intake.updated_at = datetime.now(timezone.utc)
        case.mission_intake = intake
        case.updated_at = datetime.now(timezone.utc)
        self.db.save_case(case)
        return intake

    def add_mission_task(self, case_id: str, title: str, note: str = "") -> MissionTask:
        case = self.db.load_case(case_id)
        task = MissionTask(title=title.strip(), note=note.strip())
        case.mission_intake.tasks.append(task)
        case.mission_intake.updated_at = datetime.now(timezone.utc)
        case.updated_at = datetime.now(timezone.utc)
        self.db.save_case(case)
        return task

    def update_mission_task(
        self,
        case_id: str,
        task_id: str,
        *,
        completed: bool | None = None,
        title: str | None = None,
        note: str | None = None,
    ) -> MissionTask:
        case = self.db.load_case(case_id)
        for task in case.mission_intake.tasks:
            if task.id != task_id:
                continue

            if completed is not None:
                task.completed = completed
            if title is not None:
                task.title = title.strip()
            if note is not None:
                task.note = note.strip()
            task.updated_at = datetime.now(timezone.utc)

            case.mission_intake.updated_at = datetime.now(timezone.utc)
            case.updated_at = datetime.now(timezone.utc)
            self.db.save_case(case)
            return task

        raise ValueError(f"Mission task {task_id} not found in case {case_id}")

    def delete_mission_task(self, case_id: str, task_id: str) -> None:
        case = self.db.load_case(case_id)
        before = len(case.mission_intake.tasks)
        case.mission_intake.tasks = [task for task in case.mission_intake.tasks if task.id != task_id]
        if len(case.mission_intake.tasks) == before:
            raise ValueError(f"Mission task {task_id} not found in case {case_id}")

        self.db.delete_task_links_by_task(case_id, task_id)
        case.mission_intake.updated_at = datetime.now(timezone.utc)
        case.updated_at = datetime.now(timezone.utc)
        self.db.save_case(case)

    def refresh_case_leads(self, case_id: str) -> list[LeadProfile]:
        return self.lead_workspace_service.refresh_case_leads(case_id)

    def list_unified_leads(
        self,
        case_id: str,
        lead_filter: LeadWorkspaceFilter | None = None,
    ) -> list[LeadListItem]:
        return self.lead_workspace_service.list_case_leads(case_id, lead_filter)

    def get_lead_detail(self, case_id: str, lead_id: str) -> LeadDetail:
        return self.lead_workspace_service.get_lead_detail(case_id, lead_id)

    def update_lead_profile(
        self,
        case_id: str,
        lead_id: str,
        *,
        lifecycle_state: LeadLifecycleState | None = None,
        priority: LeadPriority | None = None,
        owner: str | None = None,
        confidence_score: float | None = None,
        context_summary: str | None = None,
        blocker_note: str | None = None,
        why_it_matters: str | None = None,
    ) -> LeadProfile:
        return self.lead_workspace_service.update_lead_profile(
            case_id,
            lead_id,
            lifecycle_state=lifecycle_state,
            priority=priority,
            owner=owner,
            confidence_score=confidence_score,
            context_summary=context_summary,
            blocker_note=blocker_note,
            why_it_matters=why_it_matters,
        )

    def link_task_to_artifact(
        self,
        case_id: str,
        task_id: str,
        artifact_type: ArtifactLinkType,
        artifact_id: str,
        note: str = "",
    ) -> MissionTaskLink:
        return self.lead_workspace_service.link_task_to_artifact(
            case_id,
            task_id,
            artifact_type,
            artifact_id,
            note,
        )

    def list_task_links(self, case_id: str) -> list[MissionTaskLink]:
        return self.lead_workspace_service.list_task_links_for_case(case_id)

    def delete_task_link(self, case_id: str, link_id: str) -> None:
        self.lead_workspace_service.delete_task_link(case_id, link_id)

    def update_workflow_stage(
        self,
        case_id: str,
        workflow_stage: WorkflowStage,
        stage_note: str = "",
    ) -> None:
        case = self.db.load_case(case_id)
        allowed = _WORKFLOW_TRANSITIONS.get(case.workflow_stage, {case.workflow_stage})
        if workflow_stage not in allowed:
            raise ValueError(
                f"Invalid stage transition from {case.workflow_stage.value} to {workflow_stage.value}"
            )

        case.workflow_stage = workflow_stage
        case.workflow_stage_note = stage_note.strip()
        case.workflow_stage_updated_at = datetime.now(timezone.utc)
        case.updated_at = datetime.now(timezone.utc)
        self.db.save_case(case)

    def get_case_dashboard_summary(self, case_id: str) -> DashboardSummary:
        self.lead_workspace_service.refresh_case_leads(case_id)
        case = self.db.load_case(case_id)
        triage = self.findings_service.summarize_triage(case.findings)
        convergence = self.convergence_service.get_case_convergence_summary(case_id)
        timeline = self.timeline_service.build_case_timeline(case, limit=40)
        now = datetime.now(timezone.utc)
        recent_window = now - timedelta(days=7)

        recent_activity = [event for event in timeline if event.occurred_at >= recent_window]
        unresolved_high_risk = sum(
            1
            for finding in case.findings
            if finding.severity.value in {"HIGH", "CRITICAL"}
            and finding.review_state in {FindingReviewState.NEW, FindingReviewState.FLAGGED}
        )
        flagged_findings = sum(
            1 for finding in case.findings if finding.review_state == FindingReviewState.FLAGGED
        )
        evidence_recent_7d = sum(1 for item in case.evidence if item.collected_at >= recent_window)
        evidence_attachments_total = len(case.evidence_attachments)
        evidence_with_attachments = {item.evidence_id for item in case.evidence_attachments}
        evidence_without_attachments = sum(
            1 for evidence in case.evidence if evidence.id not in evidence_with_attachments
        )

        timeline_health = "STALE"
        if len(recent_activity) >= 6:
            timeline_health = "ACTIVE"
        elif len(recent_activity) >= 2:
            timeline_health = "WARM"

        tasks = case.mission_intake.tasks
        checklist_completed = sum(1 for task in tasks if task.completed)
        reporting_readiness = "LOW"
        if case.mission_intake.mission_summary and case.findings and case.evidence:
            reporting_readiness = "MEDIUM"
        if (
            reporting_readiness == "MEDIUM"
            and triage.high_unreviewed == 0
            and flagged_findings == 0
            and convergence.low_confidence_findings == 0
            and convergence.unsupported_findings <= 1
        ):
            reporting_readiness = "HIGH"

        signals = DashboardSignalSummary(
            timeline_health=timeline_health,
            recent_activity_count=len(recent_activity),
            unresolved_high_risk=unresolved_high_risk,
            flagged_findings=flagged_findings,
            new_findings=triage.new,
            reviewed_findings=triage.reviewed,
            saved_searches=len(case.saved_searches),
            researched_entities=len(case.entities),
            evidence_total=len(case.evidence),
            evidence_recent_7d=evidence_recent_7d,
            correlated_findings=convergence.correlated_findings,
            unsupported_findings=convergence.unsupported_findings,
            low_confidence_findings=convergence.low_confidence_findings,
            unlinked_evidence=convergence.unlinked_evidence,
            evidence_attachments_total=evidence_attachments_total,
            evidence_without_attachments=evidence_without_attachments,
            checklist_total=len(tasks),
            checklist_completed=checklist_completed,
            reporting_readiness=reporting_readiness,
        )

        featured_actions = self._build_featured_collection_actions(case)
        onboarding_hint = self._build_onboarding_hint(case)

        return DashboardSummary(
            case_id=case.id,
            mission_intake=case.mission_intake,
            workflow_stage=case.workflow_stage,
            workflow_stage_note=case.workflow_stage_note,
            workflow_stage_updated_at=case.workflow_stage_updated_at,
            signals=signals,
            recent_activity=timeline[:8],
            recommended_actions=self._build_recommended_actions(case, signals),
            featured_collection_actions=featured_actions,
            onboarding_hint=onboarding_hint,
        )

    def _build_recommended_actions(
        self,
        case: Case,
        signals: DashboardSignalSummary,
    ) -> list[str]:
        actions: list[str] = []

        if not case.mission_intake.mission_summary:
            actions.append("Complete mission summary before expanding collection.")
        if not case.mission_intake.objectives:
            actions.append("Add at least one mission objective to define success criteria.")
        if not case.mission_intake.tasks:
            actions.append("Create mission checklist tasks to reduce operator drift.")

        if case.workflow_stage == WorkflowStage.INTAKE:
            actions.append("Move to COLLECTION after mission scope and constraints are confirmed.")
        if case.workflow_stage == WorkflowStage.COLLECTION and signals.saved_searches == 0:
            actions.append("Run guided searches to establish external lead coverage.")
        if case.workflow_stage == WorkflowStage.COLLECTION and signals.researched_entities == 0:
            actions.append("Run entity research on highest-priority identifiers.")

        phone_candidates = self._extract_phone_candidates(case)
        email_candidates = self._extract_email_candidates(case)
        researched_phones = {
            entity.value.lower()
            for entity in case.entities
            if entity.kind.value == "PHONE"
        }
        researched_emails = {
            entity.value.lower()
            for entity in case.entities
            if entity.kind.value == "EMAIL"
        }
        email_searches = [
            search for search in case.saved_searches if search.intent == SearchIntent.EMAIL_MENTION
        ]

        if phone_candidates and not researched_phones:
            actions.append("Run reverse phone lookup from Entity Research for detected phone leads.")
        if any(phone not in researched_phones for phone in phone_candidates):
            actions.append("Expand phone pivots: unresolved phone leads remain unresearched.")

        if email_candidates and not researched_emails:
            actions.append("Run email pivot research to check breaches, mentions, and profile overlap.")
        if email_candidates and not email_searches:
            actions.append("Create an Email Mention guided search to widen email coverage.")

        if signals.unresolved_high_risk > 0:
            actions.append("Triage unresolved high-risk findings before reporting progression.")
        if signals.flagged_findings > 0:
            actions.append("Resolve flagged findings with analyst notes or evidence linkage.")
        if signals.unsupported_findings > 0:
            actions.append(
                "Correlate findings to supporting evidence so claims are reporting-ready."
            )
        if signals.low_confidence_findings > 0:
            actions.append(
                "Low-confidence signals remain; add corroboration or mark as not actionable."
            )
        if signals.unlinked_evidence > 0:
            actions.append(
                "Evidence exists without finding links; map support to avoid orphaned artifacts."
            )
        if signals.evidence_without_attachments > 0 and signals.evidence_total > 0:
            actions.insert(
                0,
                "Add evidence attachments (screenshots/files/public URL references) to key evidence so provenance is report-ready.",
            )

        if case.workflow_stage == WorkflowStage.REPORTING and signals.reporting_readiness == "LOW":
            actions.append("Increase evidence depth and review maturity before report finalization.")
        if case.workflow_stage == WorkflowStage.ARCHIVE_READY and (
            signals.unresolved_high_risk > 0 or signals.new_findings > 0
        ):
            actions.append("Archive readiness blocked: unresolved high-risk or new findings remain.")

        if signals.timeline_health == "STALE":
            actions.append("Timeline is stale; perform at least one collection or review action.")

        actions.extend(self._lead_blocker_actions(case))

        if not actions:
            actions.append("Case is progressing well; continue current stage actions and monitor timeline health.")

        return actions[:10]

    def _lead_blocker_actions(self, case: Case) -> list[str]:
        actions: list[str] = []
        high_priority_leads = [
            lead
            for lead in case.leads
            if lead.priority in {LeadPriority.HIGH, LeadPriority.CRITICAL}
        ]
        if not high_priority_leads:
            return actions

        for lead in high_priority_leads[:3]:
            detail = self.lead_workspace_service.get_lead_detail(case.id, lead.id)
            if detail.blocker_explanation.readiness == "BLOCKED":
                actions.append(
                    f"Lead blocker: {lead.display_label} is blocked. Open Lead Workspace for drill-in actions."
                )
            if detail.blocker_explanation.readiness == "PARTIAL":
                actions.append(
                    f"Lead readiness: {lead.display_label} has incomplete corroboration context."
                )

        return actions

    def _build_featured_collection_actions(self, case: Case) -> list[str]:
        actions: list[str] = [
            "Reverse phone lookup: Entity Research -> select PHONE -> run lookup",
            "Email pivot: Entity Research PHONE/EMAIL plus Search Builder EMAIL_MENTION",
            "Username pivot: Entity Research USERNAME for cross-platform expansion",
            "Capture public-post/media evidence by URL and attach screenshot/file support",
        ]

        phone_candidates = self._extract_phone_candidates(case)
        if phone_candidates:
            actions.append(f"Detected phone lead: {phone_candidates[0]} (ready for reverse lookup)")

        email_candidates = self._extract_email_candidates(case)
        if email_candidates:
            actions.append(f"Detected email lead: {email_candidates[0]} (ready for pivot search)")

        return actions[:5]

    def _build_onboarding_hint(self, case: Case) -> str:
        if not case.targets and not case.mission_intake.mission_summary:
            return (
                "Start here: write a mission summary, add one target, then use Featured Collection Actions "
                "for phone/email pivots."
            )
        if not case.findings and not case.entities:
            return "Next: run collection (adapters or entity pivots) to generate first investigative signals."
        return "Use Recommended Next Actions to progress stage-by-stage without guesswork."

    def _extract_phone_candidates(self, case: Case) -> list[str]:
        values: list[str] = []
        for target in case.targets:
            values.extend(_PHONE_PATTERN.findall(target.value))
        for note in case.notes:
            values.extend(_PHONE_PATTERN.findall(note.content))

        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = " ".join(value.split()).strip()
            if not cleaned:
                continue
            key = re.sub(r"\D", "", cleaned)
            if len(key) < 7 or key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)
        return normalized

    def _extract_email_candidates(self, case: Case) -> list[str]:
        values: list[str] = []
        for target in case.targets:
            text = target.value.strip()
            if "@" in text:
                values.append(text)
        for note in case.notes:
            for token in note.content.split():
                if "@" in token and "." in token:
                    values.append(token.strip(" ,;()[]{}"))

        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(value)
        return deduped

    @staticmethod
    def _platform_from_url(source_url: str) -> str:
        if not source_url:
            return ""
        host = (urlparse(source_url).netloc or "").lower()
        if "youtube.com" in host or "youtu.be" in host:
            return "youtube"
        if "instagram.com" in host:
            return "instagram"
        if "snapchat.com" in host:
            return "snapchat"
        if "facebook.com" in host or "fb.com" in host:
            return "facebook"
        if "threads.net" in host:
            return "threads"
        if host.startswith("www."):
            return host[4:]
        return host

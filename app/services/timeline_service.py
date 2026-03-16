from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models.case import Case, FindingReviewState


class TimelineCategory(str, Enum):
    CASE = "CASE"
    TARGET = "TARGET"
    NOTE = "NOTE"
    SEARCH = "SEARCH"
    RUN = "RUN"
    FINDING = "FINDING"
    ENTITY = "ENTITY"
    EVIDENCE = "EVIDENCE"


class TimelineEvent(BaseModel):
    """Case timeline event used to keep investigation chronology auditable and readable.

    Operational value:
    - Unifies otherwise separate case subsystems into one narrative feed.
    - Supports rapid situational awareness during active investigations.
    - Improves continuity between workstation workflow and reporting output.
    """

    case_id: str
    occurred_at: datetime
    category: TimelineCategory
    event_type: str
    summary: str
    source_type: str
    source_id: str = ""
    metadata: dict = Field(default_factory=dict)


class TimelineService:
    def build_case_timeline(self, case: Case, limit: int | None = None) -> list[TimelineEvent]:
        events: list[TimelineEvent] = []

        events.append(
            TimelineEvent(
                case_id=case.id,
                occurred_at=case.created_at,
                category=TimelineCategory.CASE,
                event_type="CASE_CREATED",
                summary=f"Case created: {case.name}",
                source_type="case",
                source_id=case.id,
            )
        )

        if case.updated_at and case.updated_at != case.created_at:
            events.append(
                TimelineEvent(
                    case_id=case.id,
                    occurred_at=case.updated_at,
                    category=TimelineCategory.CASE,
                    event_type="CASE_UPDATED",
                    summary="Case metadata updated",
                    source_type="case",
                    source_id=case.id,
                )
            )

        if case.mission_intake.mission_summary:
            events.append(
                TimelineEvent(
                    case_id=case.id,
                    occurred_at=case.mission_intake.updated_at,
                    category=TimelineCategory.CASE,
                    event_type="MISSION_INTAKE_UPDATED",
                    summary="Mission intake updated",
                    source_type="mission_intake",
                    source_id=case.id,
                    metadata={
                        "priority": case.mission_intake.priority.value,
                        "objectives": len(case.mission_intake.objectives),
                        "tasks": len(case.mission_intake.tasks),
                    },
                )
            )

        events.append(
            TimelineEvent(
                case_id=case.id,
                occurred_at=case.workflow_stage_updated_at,
                category=TimelineCategory.CASE,
                event_type="WORKFLOW_STAGE_UPDATED",
                summary=f"Workflow stage set to {case.workflow_stage.value}",
                source_type="workflow_stage",
                source_id=case.id,
                metadata={"stage_note": case.workflow_stage_note},
            )
        )

        for target in case.targets:
            events.append(
                TimelineEvent(
                    case_id=case.id,
                    occurred_at=target.created_at,
                    category=TimelineCategory.TARGET,
                    event_type="TARGET_ADDED",
                    summary=f"Target added: [{target.type.value}] {target.value}",
                    source_type="target",
                    source_id=target.id,
                )
            )

        for note in case.notes:
            events.append(
                TimelineEvent(
                    case_id=case.id,
                    occurred_at=note.created_at,
                    category=TimelineCategory.NOTE,
                    event_type="NOTE_ADDED",
                    summary="Analyst note added",
                    source_type="note",
                    source_id=note.id,
                    metadata={"excerpt": note.content[:120]},
                )
            )

        for search in case.saved_searches:
            events.append(
                TimelineEvent(
                    case_id=case.id,
                    occurred_at=search.created_at,
                    category=TimelineCategory.SEARCH,
                    event_type="SEARCH_SAVED",
                    summary=f"Saved search: {search.title}",
                    source_type="saved_search",
                    source_id=search.id,
                    metadata={"intent": search.intent.value},
                )
            )
            if search.updated_at and search.updated_at != search.created_at:
                events.append(
                    TimelineEvent(
                        case_id=case.id,
                        occurred_at=search.updated_at,
                        category=TimelineCategory.SEARCH,
                        event_type="SEARCH_UPDATED",
                        summary=f"Updated search: {search.title}",
                        source_type="saved_search",
                        source_id=search.id,
                        metadata={"intent": search.intent.value},
                    )
                )

        for run in case.adapter_runs:
            run_time = run.completed_at or run.started_at
            summary = (
                f"Adapter run {run.status.value}: {run.adapter_name} "
                f"({run.finding_count} finding(s), {run.duration_seconds:.2f}s)"
            )
            if run.error_message:
                summary += f" - {run.error_message}"
            events.append(
                TimelineEvent(
                    case_id=case.id,
                    occurred_at=run_time,
                    category=TimelineCategory.RUN,
                    event_type="ADAPTER_RUN",
                    summary=summary,
                    source_type="adapter_run",
                    source_id=run.id,
                    metadata={"status": run.status.value, "adapter": run.adapter_name},
                )
            )

        for finding in case.findings:
            triage_suffix = ""
            if finding.review_state in {FindingReviewState.FLAGGED, FindingReviewState.DISMISSED}:
                triage_suffix = f" | state={finding.review_state.value}"
            events.append(
                TimelineEvent(
                    case_id=case.id,
                    occurred_at=finding.collected_at,
                    category=TimelineCategory.FINDING,
                    event_type="FINDING_COLLECTED",
                    summary=(
                        f"{finding.severity.value} finding from {finding.adapter_name}: "
                        f"{finding.title}{triage_suffix}"
                    ),
                    source_type="finding",
                    source_id=finding.id,
                    metadata={
                        "severity": finding.severity.value,
                        "review_state": finding.review_state.value,
                        "adapter": finding.adapter_name,
                    },
                )
            )

            if finding.decision_updated_at and finding.decision_updated_at != finding.collected_at:
                events.append(
                    TimelineEvent(
                        case_id=case.id,
                        occurred_at=finding.decision_updated_at,
                        category=TimelineCategory.FINDING,
                        event_type="FINDING_DECISION_UPDATED",
                        summary=(
                            f"Finding decision set to {finding.decision_state.value} "
                            f"(confidence {finding.decision_confidence:.2f})"
                        ),
                        source_type="finding",
                        source_id=finding.id,
                        metadata={
                            "decision_state": finding.decision_state.value,
                            "decision_confidence": finding.decision_confidence,
                        },
                    )
                )

        for entity in case.entities:
            if entity.metadata.get("source") == "entity_research":
                events.append(
                    TimelineEvent(
                        case_id=case.id,
                        occurred_at=entity.updated_at,
                        category=TimelineCategory.ENTITY,
                        event_type="ENTITY_RESEARCHED",
                        summary=f"Entity researched: [{entity.kind.value}] {entity.value}",
                        source_type="entity",
                        source_id=entity.id,
                    )
                )

        for evidence in case.evidence:
            workflow = str(evidence.raw_json_data.get("workflow", "")).lower()
            provider = evidence.raw_json_data.get("provider_name")
            promoted_at = evidence.raw_json_data.get("promoted_at")
            event_time = evidence.collected_at
            if isinstance(promoted_at, str):
                parsed = self._try_parse_iso(promoted_at)
                if parsed is not None:
                    event_time = parsed

            if workflow == "entity_research":
                provider_label = provider or "provider"
                events.append(
                    TimelineEvent(
                        case_id=case.id,
                        occurred_at=event_time,
                        category=TimelineCategory.EVIDENCE,
                        event_type="EVIDENCE_PROMOTED",
                        summary=f"Research evidence promoted from {provider_label}",
                        source_type="evidence",
                        source_id=evidence.id,
                        metadata={"reliability": evidence.source_reliability.value},
                    )
                )
            else:
                events.append(
                    TimelineEvent(
                        case_id=case.id,
                        occurred_at=event_time,
                        category=TimelineCategory.EVIDENCE,
                        event_type="EVIDENCE_ADDED",
                        summary=evidence.normalized_summary or evidence.description or "Evidence added",
                        source_type="evidence",
                        source_id=evidence.id,
                        metadata={"reliability": evidence.source_reliability.value},
                    )
                )

        for link in case.finding_evidence_links:
            events.append(
                TimelineEvent(
                    case_id=case.id,
                    occurred_at=link.updated_at,
                    category=TimelineCategory.EVIDENCE,
                    event_type="FINDING_EVIDENCE_CORRELATED",
                    summary=(
                        f"Finding/evidence correlation updated: {link.origin.value} "
                        f"(confidence {link.support_confidence:.2f})"
                    ),
                    source_type="finding_evidence_link",
                    source_id=link.id,
                    metadata={
                        "finding_id": link.finding_id,
                        "evidence_id": link.evidence_id,
                    },
                )
            )

        for attachment in case.evidence_attachments:
            event_type = "EVIDENCE_ATTACHMENT_ADDED"
            summary = f"Attachment added to evidence: {attachment.attachment_type.value}"
            if attachment.source_url:
                event_type = "PUBLIC_MEDIA_CAPTURED"
                summary = (
                    f"Public-media reference captured"
                    f" ({attachment.source_platform or 'public-web'})"
                )
            events.append(
                TimelineEvent(
                    case_id=case.id,
                    occurred_at=attachment.captured_at,
                    category=TimelineCategory.EVIDENCE,
                    event_type=event_type,
                    summary=summary,
                    source_type="evidence_attachment",
                    source_id=attachment.id,
                    metadata={
                        "evidence_id": attachment.evidence_id,
                        "attachment_type": attachment.attachment_type.value,
                    },
                )
            )

        events.sort(key=lambda event: (event.occurred_at, event.event_type), reverse=True)
        if limit is not None:
            return events[:limit]
        return events

    @staticmethod
    def _try_parse_iso(value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

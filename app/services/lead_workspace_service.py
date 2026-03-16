import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlparse

from app.models.case import (
    ArtifactLinkType,
    Case,
    Entity,
    FindingDecisionState,
    LeadLifecycleState,
    LeadPriority,
    LeadProfile,
    MissionTaskLink,
    SearchIntent,
    Target,
    TargetType,
    WorkflowStage,
)
from app.services.timeline_service import TimelineEvent, TimelineService
from app.storage.database import Database


@dataclass
class LeadWorkspaceFilter:
    type_kind: str | None = None
    lifecycle_state: LeadLifecycleState | None = None
    priority: LeadPriority | None = None
    recent_only: bool = False
    has_evidence: bool | None = None
    has_findings: bool | None = None
    has_searches: bool | None = None
    text_query: str = ""


@dataclass
class LeadListItem:
    lead: LeadProfile
    findings_count: int
    evidence_count: int
    searches_count: int
    runs_count: int
    recent_activity_count: int
    correlated_findings_count: int
    unsupported_findings_count: int
    low_confidence_findings_count: int
    attachments_count: int
    evidence_without_attachments_count: int
    freshness: str


@dataclass
class LeadBlockerExplanation:
    readiness: str
    blockers: list[str]
    readiness_notes: list[str]


@dataclass
class LeadDetail:
    lead: LeadProfile
    related_targets: list[Target]
    related_entities: list[Entity]
    related_findings: list
    related_evidence: list
    related_searches: list
    related_runs: list
    related_attachments: list
    related_timeline: list[TimelineEvent]
    task_links: list[MissionTaskLink]
    support_links: list
    blocker_explanation: LeadBlockerExplanation


class LeadWorkspaceService:
    """Service layer for unified lead navigation across targets, entities, and artifacts.

    Operational value:
    - Unifies subject navigation so analysts pivot from one lead surface.
    - Reduces context switching by aggregating cross-workflow artifacts per lead.
    - Keeps lifecycle/readiness logic testable and reusable outside GUI widgets.
    """

    def __init__(self, db: Database):
        self.db = db
        self.timeline_service = TimelineService()

    def refresh_case_leads(self, case_id: str) -> list[LeadProfile]:
        case = self.db.load_case(case_id)
        existing = {lead.id: lead for lead in self.db.get_leads_for_case(case_id)}
        existing_by_key = {self._lead_key(lead.kind, lead.canonical_value): lead for lead in existing.values()}

        source_map: dict[str, dict] = {}
        for target in case.targets:
            kind, canonical = self._canonicalize_target(target)
            if not canonical:
                continue
            key = self._lead_key(kind, canonical)
            bucket = source_map.setdefault(
                key,
                {
                    "kind": kind,
                    "canonical": canonical,
                    "display": canonical,
                    "target_ids": set(),
                    "entity_ids": set(),
                },
            )
            bucket["display"] = bucket.get("display") or target.value
            bucket["target_ids"].add(target.id)

        for entity in case.entities:
            kind, canonical = self._canonicalize_entity(entity)
            if not canonical:
                continue
            key = self._lead_key(kind, canonical)
            bucket = source_map.setdefault(
                key,
                {
                    "kind": kind,
                    "canonical": canonical,
                    "display": canonical,
                    "target_ids": set(),
                    "entity_ids": set(),
                },
            )
            bucket["display"] = entity.display_name or entity.value or bucket.get("display")
            bucket["entity_ids"].add(entity.id)

        synced_ids: set[str] = set()
        for key, payload in source_map.items():
            current = existing_by_key.get(key)
            now = datetime.now(timezone.utc)
            last_activity = self._estimate_last_activity(
                case,
                payload["target_ids"],
                payload["entity_ids"],
                payload["canonical"],
            )
            if current is None:
                current = LeadProfile(
                    case_id=case.id,
                    kind=payload["kind"],
                    canonical_value=payload["canonical"],
                    display_label=payload["display"],
                    lifecycle_state=LeadLifecycleState.NEW,
                    priority=LeadPriority.MEDIUM,
                    confidence_score=0.5,
                    linked_target_ids=sorted(payload["target_ids"]),
                    linked_entity_ids=sorted(payload["entity_ids"]),
                    created_at=now,
                    updated_at=now,
                    last_activity_at=last_activity,
                )
            else:
                current.display_label = payload["display"]
                current.linked_target_ids = sorted(payload["target_ids"])
                current.linked_entity_ids = sorted(payload["entity_ids"])
                current.updated_at = now
                current.last_activity_at = last_activity

            self.db.save_lead(current)
            synced_ids.add(current.id)

        for lead in self.db.get_leads_for_case(case_id):
            if lead.id not in synced_ids:
                self.db.delete_lead(lead.id, case_id)

        return self.db.get_leads_for_case(case_id)

    def list_case_leads(
        self,
        case_id: str,
        lead_filter: LeadWorkspaceFilter | None = None,
    ) -> list[LeadListItem]:
        self.refresh_case_leads(case_id)
        case = self.db.load_case(case_id)
        leads = list(case.leads)
        lead_filter = lead_filter or LeadWorkspaceFilter()

        items: list[LeadListItem] = []
        now = datetime.now(timezone.utc)
        for lead in leads:
            detail = self.get_lead_detail(case_id, lead.id)
            findings_count = len(detail.related_findings)
            evidence_count = len(detail.related_evidence)
            searches_count = len(detail.related_searches)
            runs_count = len(detail.related_runs)
            correlated_findings_count = len({link.finding_id for link in detail.support_links})
            unsupported_findings_count = sum(
                1
                for finding in detail.related_findings
                if finding.id not in {link.finding_id for link in detail.support_links}
                and finding.review_state.value != "DISMISSED"
            )
            low_confidence_findings_count = sum(
                1
                for finding in detail.related_findings
                if finding.decision_confidence < 0.45
                or finding.decision_state in {
                    FindingDecisionState.LOW_CONFIDENCE,
                    FindingDecisionState.NEEDS_MORE_SUPPORT,
                }
            )
            related_evidence_ids = {evidence.id for evidence in detail.related_evidence}
            evidence_with_attachments = {
                item.evidence_id for item in detail.related_attachments
            }
            evidence_without_attachments_count = sum(
                1
                for evidence_id in related_evidence_ids
                if evidence_id not in evidence_with_attachments
            )
            recent_activity_count = sum(
                1
                for event in detail.related_timeline
                if (now - event.occurred_at).days <= 7
            )
            freshness = self._freshness_label(lead.last_activity_at, now)

            item = LeadListItem(
                lead=lead,
                findings_count=findings_count,
                evidence_count=evidence_count,
                searches_count=searches_count,
                runs_count=runs_count,
                recent_activity_count=recent_activity_count,
                correlated_findings_count=correlated_findings_count,
                unsupported_findings_count=unsupported_findings_count,
                low_confidence_findings_count=low_confidence_findings_count,
                attachments_count=len(detail.related_attachments),
                evidence_without_attachments_count=evidence_without_attachments_count,
                freshness=freshness,
            )
            if self._passes_filter(item, lead_filter):
                items.append(item)

        items.sort(key=lambda entry: (entry.lead.priority.value, entry.lead.last_activity_at), reverse=True)
        return items

    def get_lead_detail(self, case_id: str, lead_id: str) -> LeadDetail:
        case = self.db.load_case(case_id)
        lead = next((item for item in case.leads if item.id == lead_id), None)
        if lead is None:
            raise ValueError(f"Lead {lead_id} not found in case {case_id}")

        target_ids = set(lead.linked_target_ids)
        entity_ids = set(lead.linked_entity_ids)
        canonical = lead.canonical_value.lower()

        related_targets = [target for target in case.targets if target.id in target_ids]
        related_entities = [entity for entity in case.entities if entity.id in entity_ids]

        related_findings = [
            finding
            for finding in case.findings
            if finding.target_id in target_ids
            or canonical in finding.title.lower()
            or canonical in finding.description.lower()
            or canonical in json.dumps(finding.data).lower()
        ]

        related_evidence = [
            evidence
            for evidence in case.evidence
            if evidence.entity_id in entity_ids
            or canonical in (evidence.normalized_summary or "").lower()
            or canonical in (evidence.description or "").lower()
        ]

        related_searches = [
            search
            for search in case.saved_searches
            if search.target_id in target_ids
            or canonical in search.query.lower()
            or canonical in search.title.lower()
        ]

        related_runs = [run for run in case.adapter_runs if run.target_id in target_ids]

        related_evidence_ids = {item.id for item in related_evidence}
        related_attachments = [
            attachment
            for attachment in case.evidence_attachments
            if attachment.evidence_id in related_evidence_ids
        ]

        timeline = self.timeline_service.build_case_timeline(case, limit=80)
        source_ids = target_ids | entity_ids | {item.id for item in related_findings} | {item.id for item in related_evidence}
        source_ids |= {item.id for item in related_searches} | {item.id for item in related_runs}
        related_timeline = [
            event
            for event in timeline
            if event.source_id in source_ids or canonical in event.summary.lower()
        ][:20]

        task_links = [
            link
            for link in case.task_links
            if (link.artifact_type == ArtifactLinkType.LEAD and link.artifact_id == lead.id)
            or (link.artifact_id in source_ids)
        ]

        support_links = [
            link
            for link in case.finding_evidence_links
            if link.finding_id in {item.id for item in related_findings}
            or link.evidence_id in {item.id for item in related_evidence}
        ]

        blocker_explanation = self._build_blocker_explanation(
            case,
            lead,
            related_findings,
            related_evidence,
            related_searches,
            related_entities,
            related_attachments,
            task_links,
            support_links,
        )

        return LeadDetail(
            lead=lead,
            related_targets=related_targets,
            related_entities=related_entities,
            related_findings=related_findings,
            related_evidence=related_evidence,
            related_searches=related_searches,
            related_runs=related_runs,
            related_attachments=related_attachments,
            related_timeline=related_timeline,
            task_links=task_links,
            support_links=support_links,
            blocker_explanation=blocker_explanation,
        )

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
        case = self.db.load_case(case_id)
        lead = next((item for item in case.leads if item.id == lead_id), None)
        if lead is None:
            raise ValueError(f"Lead {lead_id} not found in case {case_id}")

        if lifecycle_state is not None:
            lead.lifecycle_state = lifecycle_state
        if priority is not None:
            lead.priority = priority
        if owner is not None:
            lead.owner = owner.strip()
        if confidence_score is not None:
            lead.confidence_score = min(max(confidence_score, 0.0), 1.0)
        if context_summary is not None:
            lead.context_summary = context_summary.strip()
        if blocker_note is not None:
            lead.blocker_note = blocker_note.strip()
        if why_it_matters is not None:
            lead.why_it_matters = why_it_matters.strip()

        lead.updated_at = datetime.now(timezone.utc)
        self.db.save_lead(lead)
        self.db.update_case_timestamp(case_id)
        return lead

    def link_task_to_artifact(
        self,
        case_id: str,
        task_id: str,
        artifact_type: ArtifactLinkType,
        artifact_id: str,
        note: str = "",
    ) -> MissionTaskLink:
        case = self.db.load_case(case_id)
        if not any(task.id == task_id for task in case.mission_intake.tasks):
            raise ValueError(f"Mission task {task_id} not found in case {case_id}")

        existing = next(
            (
                link
                for link in case.task_links
                if link.task_id == task_id
                and link.artifact_type == artifact_type
                and link.artifact_id == artifact_id
            ),
            None,
        )
        if existing:
            existing.note = note.strip()
            existing.updated_at = datetime.now(timezone.utc)
            self.db.save_mission_task_link(existing)
            self.db.update_case_timestamp(case_id)
            return existing

        now = datetime.now(timezone.utc)
        link = MissionTaskLink(
            case_id=case_id,
            task_id=task_id,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            note=note.strip(),
            created_at=now,
            updated_at=now,
        )
        self.db.save_mission_task_link(link)
        self.db.update_case_timestamp(case_id)
        return link

    def list_task_links_for_case(self, case_id: str) -> list[MissionTaskLink]:
        return self.db.get_task_links_for_case(case_id)

    def delete_task_link(self, case_id: str, link_id: str) -> None:
        self.db.delete_task_link(link_id, case_id)
        self.db.update_case_timestamp(case_id)

    def _build_blocker_explanation(
        self,
        case: Case,
        lead: LeadProfile,
        related_findings: list,
        related_evidence: list,
        related_searches: list,
        related_entities: list,
        related_attachments: list,
        task_links: list[MissionTaskLink],
        support_links: list,
    ) -> LeadBlockerExplanation:
        blockers: list[str] = []
        readiness_notes: list[str] = []

        flagged = [finding for finding in related_findings if finding.review_state.value == "FLAGGED"]
        unresolved_high = [
            finding
            for finding in related_findings
            if finding.review_state.value in {"NEW", "FLAGGED"}
            and finding.severity.value in {"HIGH", "CRITICAL"}
        ]

        if lead.priority in {LeadPriority.HIGH, LeadPriority.CRITICAL} and not related_evidence:
            blockers.append("High-priority lead has no linked evidence yet.")

        if lead.kind in {"PHONE", "EMAIL", "USERNAME", "IP"} and not related_entities:
            blockers.append("No entity-research activity captured for this lead.")

        if unresolved_high:
            blockers.append("Unresolved high-risk findings are still tied to this lead.")

        if flagged:
            blockers.append("Flagged findings need adjudication or corroborating evidence.")

        unsupported_findings = [
            finding
            for finding in related_findings
            if finding.id not in {link.finding_id for link in support_links}
            and finding.review_state.value != "DISMISSED"
        ]
        if unsupported_findings:
            blockers.append("Lead has findings that are not linked to supporting evidence.")

        low_confidence_findings = [
            finding
            for finding in related_findings
            if finding.decision_confidence < 0.45
            or finding.decision_state in {
                FindingDecisionState.LOW_CONFIDENCE,
                FindingDecisionState.NEEDS_MORE_SUPPORT,
            }
        ]
        if low_confidence_findings:
            readiness_notes.append("Lead has low-confidence findings needing corroboration.")

        if not related_searches:
            readiness_notes.append("No guided searches linked to this lead yet.")

        if not task_links:
            readiness_notes.append("No mission task is currently linked to this lead.")

        if related_evidence and not support_links:
            readiness_notes.append(
                "Evidence exists but is not mapped to findings for this lead yet."
            )

        if related_evidence and not related_attachments:
            readiness_notes.append(
                "Evidence exists but has no screenshot/file/public-media attachments yet."
            )

        attached_evidence_ids = {item.evidence_id for item in related_attachments}
        if any(evidence.id not in attached_evidence_ids for evidence in related_evidence):
            readiness_notes.append(
                "Some evidence for this lead still lacks attachment support artifacts."
            )

        if lead.lifecycle_state == LeadLifecycleState.CORROBORATED and not related_evidence:
            readiness_notes.append("Lead is marked corroborated but lacks durable evidence linkage.")

        if case.workflow_stage in {WorkflowStage.REPORTING, WorkflowStage.ARCHIVE_READY} and not related_evidence:
            blockers.append("Reporting stage requires evidence for major leads.")

        readiness = "READY"
        if blockers:
            readiness = "BLOCKED"
        elif readiness_notes:
            readiness = "PARTIAL"

        if lead.blocker_note:
            readiness_notes.append(f"Analyst blocker note: {lead.blocker_note}")

        return LeadBlockerExplanation(
            readiness=readiness,
            blockers=blockers,
            readiness_notes=readiness_notes,
        )

    @staticmethod
    def _freshness_label(last_activity_at: datetime, now: datetime) -> str:
        age_days = (now - last_activity_at).days
        if age_days <= 1:
            return "fresh"
        if age_days <= 7:
            return "warm"
        return "stale"

    def _passes_filter(self, item: LeadListItem, lead_filter: LeadWorkspaceFilter) -> bool:
        lead = item.lead
        if lead_filter.type_kind and lead.kind != lead_filter.type_kind:
            return False
        if lead_filter.lifecycle_state and lead.lifecycle_state != lead_filter.lifecycle_state:
            return False
        if lead_filter.priority and lead.priority != lead_filter.priority:
            return False
        if lead_filter.recent_only and self._freshness_label(lead.last_activity_at, datetime.now(timezone.utc)) == "stale":
            return False
        if lead_filter.has_evidence is True and item.evidence_count == 0:
            return False
        if lead_filter.has_evidence is False and item.evidence_count > 0:
            return False
        if lead_filter.has_findings is True and item.findings_count == 0:
            return False
        if lead_filter.has_findings is False and item.findings_count > 0:
            return False
        if lead_filter.has_searches is True and item.searches_count == 0:
            return False
        if lead_filter.has_searches is False and item.searches_count > 0:
            return False

        query = lead_filter.text_query.strip().lower()
        if query:
            haystack = " ".join(
                [
                    lead.display_label,
                    lead.kind,
                    lead.context_summary,
                    lead.why_it_matters,
                    lead.owner,
                ]
            ).lower()
            if query not in haystack:
                return False

        return True

    @staticmethod
    def _lead_key(kind: str, canonical: str) -> str:
        return f"{kind}:{canonical}"

    @staticmethod
    def _canonicalize_entity(entity: Entity) -> tuple[str, str]:
        kind = entity.kind.value
        canonical = entity.value.strip().lower()
        return kind, canonical

    @staticmethod
    def _canonicalize_target(target: Target) -> tuple[str, str]:
        value = target.value.strip()
        if target.type == TargetType.URL:
            parsed = urlparse(value)
            host = parsed.netloc or parsed.path
            if host:
                return "DOMAIN", host.lower().split(":")[0]
            return "DOMAIN", value.lower()
        if target.type == TargetType.DOMAIN:
            return "DOMAIN", value.lower()
        if target.type == TargetType.EMAIL:
            return "EMAIL", value.lower()
        if target.type == TargetType.USERNAME:
            return "USERNAME", value.lower()
        if target.type == TargetType.IP:
            return "IP", value
        if target.type == TargetType.ORGANIZATION:
            return "ORGANIZATION", value.lower()
        if target.type == TargetType.DOCUMENT:
            return "DOCUMENT", value.lower()
        return "GENERIC", value.lower()

    def _estimate_last_activity(
        self,
        case: Case,
        target_ids: Iterable[str],
        entity_ids: Iterable[str],
        canonical_value: str,
    ) -> datetime:
        lower = canonical_value.lower()
        times: list[datetime] = [case.updated_at]

        target_id_set = set(target_ids)
        entity_id_set = set(entity_ids)

        for target in case.targets:
            if target.id in target_id_set:
                times.append(target.created_at)

        for entity in case.entities:
            if entity.id in entity_id_set:
                times.append(entity.updated_at)

        for finding in case.findings:
            if finding.target_id in target_id_set or lower in finding.title.lower() or lower in finding.description.lower():
                times.append(finding.collected_at)

        for evidence in case.evidence:
            if evidence.entity_id in entity_id_set:
                times.append(evidence.collected_at)

        for search in case.saved_searches:
            if search.target_id in target_id_set or lower in search.query.lower():
                times.append(search.updated_at)

        for run in case.adapter_runs:
            if run.target_id in target_id_set:
                times.append(run.completed_at or run.started_at)

        return max(times)

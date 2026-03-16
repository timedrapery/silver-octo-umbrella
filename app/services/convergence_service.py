from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.case import (
    Case,
    Evidence,
    Finding,
    FindingDecisionState,
    FindingEvidenceLink,
    SourceReliability,
    SupportLinkOrigin,
)
from app.storage.database import Database


@dataclass
class FindingSupportView:
    finding: Finding
    linked_evidence: list[Evidence]
    candidate_evidence: list[Evidence]
    support_links: list[FindingEvidenceLink]


@dataclass
class EvidenceSupportView:
    evidence: Evidence
    linked_findings: list[Finding]
    support_links: list[FindingEvidenceLink]


@dataclass
class ConvergenceSummary:
    total_findings: int
    correlated_findings: int
    unsupported_findings: int
    promoted_findings: int
    low_confidence_findings: int
    unlinked_evidence: int


class ConvergenceService:
    """Coordinates repeatable signal-support convergence between findings and evidence.

    Operational value:
    - Turns ad hoc triage notes into explicit, durable finding-to-evidence support links.
    - Makes analyst decisions and confidence revisit-able instead of implicit.
    - Enables readiness logic to reason about support maturity, not only artifact volume.
    """

    def __init__(self, db: Database):
        self.db = db

    def get_finding_support(self, case_id: str, finding_id: str) -> FindingSupportView:
        case = self.db.load_case(case_id)
        finding = self._find_finding(case, finding_id)
        links = [
            link
            for link in case.finding_evidence_links
            if link.finding_id == finding_id
        ]
        linked_evidence_map = {evidence.id: evidence for evidence in case.evidence}
        linked_evidence = [
            linked_evidence_map[link.evidence_id]
            for link in links
            if link.evidence_id in linked_evidence_map
        ]

        linked_ids = {item.id for item in linked_evidence}
        candidate_evidence = [
            evidence
            for evidence in case.evidence
            if evidence.id not in linked_ids
        ]
        return FindingSupportView(
            finding=finding,
            linked_evidence=linked_evidence,
            candidate_evidence=candidate_evidence,
            support_links=links,
        )

    def get_evidence_support(self, case_id: str, evidence_id: str) -> EvidenceSupportView:
        case = self.db.load_case(case_id)
        evidence = next((item for item in case.evidence if item.id == evidence_id), None)
        if evidence is None:
            raise ValueError(f"Evidence {evidence_id} not found in case {case_id}")

        links = [
            link
            for link in case.finding_evidence_links
            if link.evidence_id == evidence_id
        ]
        finding_map = {finding.id: finding for finding in case.findings}
        linked_findings = [
            finding_map[link.finding_id]
            for link in links
            if link.finding_id in finding_map
        ]
        return EvidenceSupportView(
            evidence=evidence,
            linked_findings=linked_findings,
            support_links=links,
        )

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
        case = self.db.load_case(case_id)
        finding = self._find_finding(case, finding_id)
        if not any(item.id == evidence_id for item in case.evidence):
            raise ValueError(f"Evidence {evidence_id} not found in case {case_id}")

        existing = next(
            (
                link
                for link in case.finding_evidence_links
                if link.finding_id == finding_id and link.evidence_id == evidence_id
            ),
            None,
        )
        if existing is not None:
            existing.support_confidence = min(max(support_confidence, 0.0), 1.0)
            existing.rationale = rationale.strip()
            existing.origin = origin
            existing.updated_at = datetime.now(timezone.utc)
            self.db.save_finding_evidence_link(existing)
            self.db.update_case_timestamp(case_id)
            self._sync_finding_decision_from_links(case_id, finding)
            return existing

        now = datetime.now(timezone.utc)
        link = FindingEvidenceLink(
            case_id=case_id,
            finding_id=finding_id,
            evidence_id=evidence_id,
            origin=origin,
            support_confidence=min(max(support_confidence, 0.0), 1.0),
            rationale=rationale.strip(),
            created_at=now,
            updated_at=now,
        )
        self.db.save_finding_evidence_link(link)
        self.db.update_case_timestamp(case_id)
        self._sync_finding_decision_from_links(case_id, finding)
        return link

    def promote_finding_to_evidence(
        self,
        case_id: str,
        finding_id: str,
        *,
        rationale: str = "",
        support_confidence: float = 0.6,
        source_reliability: SourceReliability = SourceReliability.MEDIUM,
    ) -> tuple[Evidence, FindingEvidenceLink, bool]:
        case = self.db.load_case(case_id)
        finding = self._find_finding(case, finding_id)

        duplicate = next(
            (
                evidence
                for evidence in case.evidence
                if evidence.raw_json_data.get("workflow") == "finding_promotion"
                and evidence.raw_json_data.get("promoted_from_finding_id") == finding_id
            ),
            None,
        )

        created_new = duplicate is None
        if duplicate is None:
            summary = finding.description.strip() or finding.title.strip()
            if rationale.strip():
                summary = f"{summary} | Rationale: {rationale.strip()}"
            evidence = Evidence(
                case_id=case_id,
                finding_id=finding.id,
                description=f"Promoted from finding: {finding.title}",
                source_reliability=source_reliability,
                normalized_summary=summary[:260],
                raw_json_data={
                    "workflow": "finding_promotion",
                    "promoted_from_finding_id": finding.id,
                    "finding_title": finding.title,
                    "finding_type": finding.finding_type.value,
                    "finding_severity": finding.severity.value,
                    "finding_review_state": finding.review_state.value,
                    "promoted_at": datetime.now(timezone.utc).isoformat(),
                    "promotion_rationale": rationale.strip(),
                },
            )
            self.db.save_evidence(evidence)
        else:
            evidence = duplicate

        link = self.correlate_finding_to_evidence(
            case_id,
            finding_id,
            evidence.id,
            rationale=rationale,
            support_confidence=support_confidence,
            origin=SupportLinkOrigin.FINDING_PROMOTION,
        )
        self.update_finding_decision(
            case_id,
            finding_id,
            decision_state=FindingDecisionState.PROMOTED,
            decision_confidence=max(support_confidence, 0.6),
            decision_rationale=rationale or "Finding promoted into durable evidence.",
        )
        return evidence, link, created_new

    def update_finding_decision(
        self,
        case_id: str,
        finding_id: str,
        *,
        decision_state: FindingDecisionState,
        decision_confidence: float,
        decision_rationale: str = "",
    ) -> Finding:
        case = self.db.load_case(case_id)
        finding = self._find_finding(case, finding_id)
        finding.decision_state = decision_state
        finding.decision_confidence = min(max(decision_confidence, 0.0), 1.0)
        finding.decision_rationale = decision_rationale.strip()
        finding.decision_updated_at = datetime.now(timezone.utc)

        self.db.update_finding_decision(
            finding_id,
            decision_state,
            finding.decision_confidence,
            finding.decision_rationale,
        )
        self.db.update_case_timestamp(case_id)
        return finding

    def get_case_convergence_summary(self, case_id: str) -> ConvergenceSummary:
        case = self.db.load_case(case_id)
        linked_finding_ids = {link.finding_id for link in case.finding_evidence_links}
        linked_evidence_ids = {link.evidence_id for link in case.finding_evidence_links}

        correlated_findings = len(linked_finding_ids)
        total_findings = len(case.findings)
        unsupported_findings = sum(
            1
            for finding in case.findings
            if finding.id not in linked_finding_ids
            and finding.review_state.value != "DISMISSED"
        )
        promoted_findings = sum(
            1
            for finding in case.findings
            if finding.decision_state == FindingDecisionState.PROMOTED
        )
        low_confidence_findings = sum(
            1
            for finding in case.findings
            if finding.decision_confidence < 0.45
            or finding.decision_state in {
                FindingDecisionState.LOW_CONFIDENCE,
                FindingDecisionState.NEEDS_MORE_SUPPORT,
            }
        )
        unlinked_evidence = sum(
            1
            for evidence in case.evidence
            if evidence.id not in linked_evidence_ids
        )
        return ConvergenceSummary(
            total_findings=total_findings,
            correlated_findings=correlated_findings,
            unsupported_findings=unsupported_findings,
            promoted_findings=promoted_findings,
            low_confidence_findings=low_confidence_findings,
            unlinked_evidence=unlinked_evidence,
        )

    def _sync_finding_decision_from_links(self, case_id: str, finding: Finding) -> None:
        support = self.get_finding_support(case_id, finding.id)
        if not support.support_links:
            return

        top_confidence = max(link.support_confidence for link in support.support_links)
        state = FindingDecisionState.CORRELATED
        if finding.decision_state == FindingDecisionState.PROMOTED:
            state = FindingDecisionState.PROMOTED

        self.db.update_finding_decision(
            finding.id,
            state,
            max(finding.decision_confidence, top_confidence),
            finding.decision_rationale or "Finding has supporting evidence links.",
        )
        self.db.update_case_timestamp(case_id)

    @staticmethod
    def _find_finding(case: Case, finding_id: str) -> Finding:
        finding = next((item for item in case.findings if item.id == finding_id), None)
        if finding is None:
            raise ValueError(f"Finding {finding_id} not found in case {case.id}")
        return finding

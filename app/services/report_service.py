import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.case import Case
from app.services.normalization import extract_case_summary
from app.services.timeline_service import TimelineService


class ReportService:
    def __init__(self):
        templates_dir = Path(__file__).parent.parent / "reports" / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "j2"]),
        )
        self.timeline_service = TimelineService()

    def generate_html(self, case: Case, output_path: str) -> None:
        template = self.env.get_template("report.html.j2")
        timeline_events = self.timeline_service.build_case_timeline(case, limit=40)
        html = template.render(
            case=case,
            entities=extract_case_summary(case),
            timeline_events=timeline_events,
            dashboard_snapshot=self._build_dashboard_snapshot(case, timeline_events),
            lead_snapshot=self._build_lead_snapshot(case),
            convergence_snapshot=self._build_convergence_snapshot(case),
            now=datetime.now(timezone.utc),
        )
        Path(output_path).write_text(html, encoding="utf-8")

    def _build_dashboard_snapshot(self, case: Case, timeline_events: list) -> dict:
        now = datetime.now(timezone.utc)
        recent_window = now.timestamp() - (7 * 24 * 60 * 60)

        recent_activity_count = sum(
            1
            for event in timeline_events
            if event.occurred_at.timestamp() >= recent_window
        )

        unresolved_high_risk = sum(
            1
            for finding in case.findings
            if finding.severity.value in {"HIGH", "CRITICAL"}
            and finding.review_state.value in {"NEW", "FLAGGED"}
        )
        flagged_findings = sum(
            1 for finding in case.findings if finding.review_state.value == "FLAGGED"
        )
        new_findings = sum(
            1 for finding in case.findings if finding.review_state.value == "NEW"
        )
        reviewed_findings = sum(
            1 for finding in case.findings if finding.review_state.value == "REVIEWED"
        )
        evidence_recent_7d = sum(
            1 for evidence in case.evidence if evidence.collected_at.timestamp() >= recent_window
        )
        phone_research_count = sum(1 for entity in case.entities if entity.kind.value == "PHONE")
        email_research_count = sum(1 for entity in case.entities if entity.kind.value == "EMAIL")
        email_search_count = sum(
            1 for search in case.saved_searches if search.intent.value == "EMAIL_MENTION"
        )

        checklist_total = len(case.mission_intake.tasks)
        checklist_completed = sum(1 for task in case.mission_intake.tasks if task.completed)
        reporting_readiness = "LOW"
        if case.mission_intake.mission_summary and case.findings and case.evidence:
            reporting_readiness = "MEDIUM"
        if reporting_readiness == "MEDIUM" and unresolved_high_risk == 0 and flagged_findings == 0:
            reporting_readiness = "HIGH"

        return {
            "timeline_health": (
                "ACTIVE" if recent_activity_count >= 6 else "WARM" if recent_activity_count >= 2 else "STALE"
            ),
            "recent_activity_count": recent_activity_count,
            "unresolved_high_risk": unresolved_high_risk,
            "flagged_findings": flagged_findings,
            "new_findings": new_findings,
            "reviewed_findings": reviewed_findings,
            "saved_searches": len(case.saved_searches),
            "researched_entities": len(case.entities),
            "evidence_total": len(case.evidence),
            "evidence_recent_7d": evidence_recent_7d,
            "checklist_total": checklist_total,
            "checklist_completed": checklist_completed,
            "reporting_readiness": reporting_readiness,
            "phone_research_count": phone_research_count,
            "email_research_count": email_research_count,
            "email_search_count": email_search_count,
        }

    @staticmethod
    def _build_lead_snapshot(case: Case) -> dict:
        leads = list(case.leads)
        high_value = [
            lead
            for lead in leads
            if lead.priority.value in {"HIGH", "CRITICAL"}
        ]
        corroborated = [
            lead
            for lead in leads
            if lead.lifecycle_state.value == "CORROBORATED"
        ]

        return {
            "total": len(leads),
            "high_value": len(high_value),
            "corroborated": len(corroborated),
            "active": len([lead for lead in leads if lead.lifecycle_state.value == "ACTIVE"]),
            "needs_review": len(
                [lead for lead in leads if lead.lifecycle_state.value == "NEEDS_REVIEW"]
            ),
            "deprioritized": len(
                [lead for lead in leads if lead.lifecycle_state.value == "DEPRIORITIZED"]
            ),
        }

    @staticmethod
    def _build_convergence_snapshot(case: Case) -> dict:
        linked_finding_ids = {link.finding_id for link in case.finding_evidence_links}
        linked_evidence_ids = {link.evidence_id for link in case.finding_evidence_links}
        evidence_with_attachments = {attachment.evidence_id for attachment in case.evidence_attachments}

        supported_findings = [finding for finding in case.findings if finding.id in linked_finding_ids]
        unsupported_findings = [
            finding
            for finding in case.findings
            if finding.id not in linked_finding_ids and finding.review_state.value != "DISMISSED"
        ]
        low_confidence_findings = [
            finding
            for finding in case.findings
            if finding.decision_confidence < 0.45
            or finding.decision_state.value in {"LOW_CONFIDENCE", "NEEDS_MORE_SUPPORT"}
        ]
        promoted_findings = [
            finding for finding in case.findings if finding.decision_state.value == "PROMOTED"
        ]
        unlinked_evidence = [
            evidence for evidence in case.evidence if evidence.id not in linked_evidence_ids
        ]
        evidence_without_attachments = [
            evidence for evidence in case.evidence if evidence.id not in evidence_with_attachments
        ]
        public_media_attachments = [
            attachment
            for attachment in case.evidence_attachments
            if attachment.attachment_type.value in {"PUBLIC_MEDIA", "URL_REFERENCE"}
        ]

        return {
            "total_links": len(case.finding_evidence_links),
            "supported_findings": len(supported_findings),
            "unsupported_findings": len(unsupported_findings),
            "low_confidence_findings": len(low_confidence_findings),
            "promoted_findings": len(promoted_findings),
            "unlinked_evidence": len(unlinked_evidence),
            "attachments_total": len(case.evidence_attachments),
            "evidence_without_attachments": len(evidence_without_attachments),
            "public_media_attachments": len(public_media_attachments),
        }

    def generate_json(self, case: Case, output_path: str) -> None:
        data = case.model_dump(mode="json")
        Path(output_path).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def generate_csv(self, case: Case, output_path: str) -> None:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id", "title", "finding_type", "severity",
                    "review_state", "decision_state", "decision_confidence", "decision_rationale",
                    "analyst_note", "adapter_name", "description",
                    "source_url", "collected_at",
                ],
            )
            writer.writeheader()
            for finding in case.findings:
                writer.writerow(
                    {
                        "id": finding.id,
                        "title": finding.title,
                        "finding_type": finding.finding_type.value,
                        "severity": finding.severity.value,
                        "review_state": finding.review_state.value,
                        "decision_state": finding.decision_state.value,
                        "decision_confidence": finding.decision_confidence,
                        "decision_rationale": finding.decision_rationale,
                        "analyst_note": finding.analyst_note,
                        "adapter_name": finding.adapter_name,
                        "description": finding.description,
                        "source_url": finding.source_url,
                        "collected_at": finding.collected_at.isoformat(),
                    }
                )

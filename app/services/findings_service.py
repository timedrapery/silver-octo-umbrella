from dataclasses import dataclass

from app.models.case import Finding, FindingReviewState, FindingSortBy, Severity, Target


@dataclass
class FindingFilter:
    review_state: FindingReviewState | None = None
    severity: Severity | None = None
    adapter_name: str | None = None
    target_id: str | None = None
    finding_type: str | None = None
    text_query: str = ""


@dataclass
class TriageSummary:
    total: int
    new: int
    reviewed: int
    flagged: int
    dismissed: int
    high_unreviewed: int


_SEVERITY_WEIGHT: dict[Severity, int] = {
    Severity.CRITICAL: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFO: 1,
}


class FindingsService:
    def apply_filters(
        self,
        findings: list[Finding],
        finding_filter: FindingFilter,
    ) -> list[Finding]:
        query = finding_filter.text_query.strip().lower()

        filtered: list[Finding] = []
        for finding in findings:
            if finding_filter.review_state and finding.review_state != finding_filter.review_state:
                continue
            if finding_filter.severity and finding.severity != finding_filter.severity:
                continue
            if finding_filter.adapter_name and finding.adapter_name != finding_filter.adapter_name:
                continue
            if finding_filter.target_id and finding.target_id != finding_filter.target_id:
                continue
            if finding_filter.finding_type and finding.finding_type.value != finding_filter.finding_type:
                continue

            if query:
                haystack = " ".join(
                    [
                        finding.title,
                        finding.description,
                        finding.adapter_name,
                        finding.finding_type.value,
                        finding.source_name,
                        finding.source_url,
                        finding.analyst_note,
                    ]
                ).lower()
                if query not in haystack:
                    continue

            filtered.append(finding)

        return filtered

    def sort_findings(
        self,
        findings: list[Finding],
        sort_by: FindingSortBy,
        target_labels: dict[str, str],
    ) -> list[Finding]:
        if sort_by == FindingSortBy.NEWEST:
            return sorted(findings, key=lambda finding: finding.collected_at, reverse=True)

        if sort_by == FindingSortBy.OLDEST:
            return sorted(findings, key=lambda finding: finding.collected_at)

        if sort_by == FindingSortBy.SEVERITY:
            return sorted(
                findings,
                key=lambda finding: (
                    _SEVERITY_WEIGHT.get(finding.severity, 0),
                    finding.collected_at,
                ),
                reverse=True,
            )

        if sort_by == FindingSortBy.ADAPTER:
            return sorted(
                findings,
                key=lambda finding: (finding.adapter_name.lower(), finding.collected_at),
            )

        if sort_by == FindingSortBy.TARGET:
            return sorted(
                findings,
                key=lambda finding: (
                    target_labels.get(finding.target_id, "").lower(),
                    finding.collected_at,
                ),
            )

        return list(findings)

    def summarize_triage(self, findings: list[Finding]) -> TriageSummary:
        total = len(findings)
        new = sum(1 for finding in findings if finding.review_state == FindingReviewState.NEW)
        reviewed = sum(
            1 for finding in findings if finding.review_state == FindingReviewState.REVIEWED
        )
        flagged = sum(1 for finding in findings if finding.review_state == FindingReviewState.FLAGGED)
        dismissed = sum(
            1 for finding in findings if finding.review_state == FindingReviewState.DISMISSED
        )
        high_unreviewed = sum(
            1
            for finding in findings
            if finding.review_state == FindingReviewState.NEW
            and finding.severity in {Severity.HIGH, Severity.CRITICAL}
        )

        return TriageSummary(
            total=total,
            new=new,
            reviewed=reviewed,
            flagged=flagged,
            dismissed=dismissed,
            high_unreviewed=high_unreviewed,
        )

    def unique_adapters(self, findings: list[Finding]) -> list[str]:
        return sorted({finding.adapter_name for finding in findings})

    def unique_finding_types(self, findings: list[Finding]) -> list[str]:
        return sorted({finding.finding_type.value for finding in findings})

    def target_label_map(self, targets: list[Target]) -> dict[str, str]:
        return {
            target.id: f"[{target.type.value}] {target.value}"
            for target in targets
        }

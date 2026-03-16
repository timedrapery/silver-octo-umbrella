from app.models.case import (
    Case,
    Evidence,
    Finding,
    FindingDecisionState,
    FindingType,
    Severity,
    SourceReliability,
    SupportLinkOrigin,
)
from app.services.convergence_service import ConvergenceService
from app.storage.database import Database


def _db(tmp_path):
    db = Database()
    db.initialize(str(tmp_path / "convergence.db"))
    return db


def test_correlate_and_bidirectional_support_views(tmp_path):
    db = _db(tmp_path)
    case = Case(name="Correlation")
    finding = Finding(
        target_id="target-1",
        adapter_name="dns",
        finding_type=FindingType.DNS,
        title="A record",
        description="desc",
        severity=Severity.HIGH,
    )
    evidence = Evidence(case_id=case.id, description="resolver screenshot")
    case.findings = [finding]
    case.evidence = [evidence]
    db.save_case(case)

    service = ConvergenceService(db)
    link = service.correlate_finding_to_evidence(
        case.id,
        finding.id,
        evidence.id,
        rationale="Same host and timestamp",
        support_confidence=0.81,
        origin=SupportLinkOrigin.MANUAL_CORRELATION,
    )

    assert link.support_confidence == 0.81
    finding_view = service.get_finding_support(case.id, finding.id)
    evidence_view = service.get_evidence_support(case.id, evidence.id)
    assert len(finding_view.linked_evidence) == 1
    assert len(evidence_view.linked_findings) == 1


def test_promote_finding_updates_decision_state(tmp_path):
    db = _db(tmp_path)
    case = Case(name="Promotion")
    finding = Finding(
        target_id="target-1",
        adapter_name="http",
        finding_type=FindingType.HTTP,
        title="Leaky endpoint",
        description="sensitive debug output",
        severity=Severity.MEDIUM,
    )
    case.findings = [finding]
    db.save_case(case)

    service = ConvergenceService(db)
    evidence, link, created = service.promote_finding_to_evidence(
        case.id,
        finding.id,
        rationale="Contains structured sensitive values",
        support_confidence=0.69,
        source_reliability=SourceReliability.MEDIUM,
    )

    assert created is True
    assert evidence.raw_json_data.get("promoted_from_finding_id") == finding.id
    assert link.origin == SupportLinkOrigin.FINDING_PROMOTION

    loaded = db.load_case(case.id)
    updated = loaded.findings[0]
    assert updated.decision_state == FindingDecisionState.PROMOTED
    assert updated.decision_confidence >= 0.6


def test_convergence_summary_counts(tmp_path):
    db = _db(tmp_path)
    case = Case(name="Summary")
    finding_a = Finding(
        target_id="target-1",
        adapter_name="dns",
        finding_type=FindingType.DNS,
        title="A record",
        description="desc",
        severity=Severity.HIGH,
    )
    finding_b = Finding(
        target_id="target-2",
        adapter_name="social",
        finding_type=FindingType.SOCIAL,
        title="Username mention",
        description="desc",
        severity=Severity.LOW,
        decision_state=FindingDecisionState.LOW_CONFIDENCE,
        decision_confidence=0.3,
    )
    evidence_a = Evidence(case_id=case.id, description="linked evidence")
    evidence_b = Evidence(case_id=case.id, description="orphan evidence")
    case.findings = [finding_a, finding_b]
    case.evidence = [evidence_a, evidence_b]
    db.save_case(case)

    service = ConvergenceService(db)
    service.correlate_finding_to_evidence(case.id, finding_a.id, evidence_a.id)

    summary = service.get_case_convergence_summary(case.id)
    assert summary.total_findings == 2
    assert summary.correlated_findings == 1
    assert summary.unsupported_findings == 1
    assert summary.low_confidence_findings == 1
    assert summary.unlinked_evidence == 1

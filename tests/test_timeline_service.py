from datetime import datetime, timedelta, timezone

from app.models.case import (
    AdapterRun,
    AdapterRunStatus,
    Case,
    Entity,
    EntityKind,
    Evidence,
    Finding,
    FindingReviewState,
    FindingType,
    Note,
    SavedSearch,
    SearchIntent,
    SearchProvider,
    Severity,
    SourceReliability,
    Target,
    TargetType,
)
from app.services.timeline_service import TimelineCategory, TimelineService


def _dt(offset_minutes: int) -> datetime:
    return datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc) + timedelta(minutes=offset_minutes)


def _build_case() -> Case:
    case = Case(
        name="Timeline Case",
        description="Chronology coverage",
        created_at=_dt(0),
        updated_at=_dt(20),
    )

    target = Target(type=TargetType.DOMAIN, value="example.com", created_at=_dt(1))
    case.targets = [target]

    case.notes = [
        Note(case_id=case.id, content="Initial triage complete", created_at=_dt(2)),
    ]

    case.saved_searches = [
        SavedSearch(
            case_id=case.id,
            target_id=target.id,
            title="Credential Sweep",
            query='site:pastebin.com "example.com"',
            explanation="Searches public leaks",
            intent=SearchIntent.CREDENTIAL_MENTION,
            provider=SearchProvider.GOOGLE,
            created_at=_dt(3),
            updated_at=_dt(4),
        )
    ]

    run = AdapterRun(
        case_id=case.id,
        target_id=target.id,
        adapter_name="dns",
        status=AdapterRunStatus.COMPLETE,
        started_at=_dt(5),
        completed_at=_dt(6),
        finding_count=1,
        duration_seconds=1.2,
    )
    case.adapter_runs = [run]

    case.findings = [
        Finding(
            target_id=target.id,
            adapter_name="dns",
            adapter_run_id=run.id,
            finding_type=FindingType.DNS,
            title="A Record",
            description="IPv4 record found",
            severity=Severity.MEDIUM,
            review_state=FindingReviewState.FLAGGED,
            collected_at=_dt(7),
        )
    ]

    entity = Entity(
        case_id=case.id,
        kind=EntityKind.USERNAME,
        value="octo_user",
        metadata={"source": "entity_research"},
        created_at=_dt(8),
        updated_at=_dt(9),
    )
    case.entities = [entity]

    case.evidence = [
        Evidence(
            case_id=case.id,
            entity_id=entity.id,
            description="social_provider: profile",
            source_reliability=SourceReliability.MEDIUM,
            raw_json_data={
                "workflow": "entity_research",
                "provider_name": "social_provider",
                "promoted_at": _dt(10).isoformat(),
            },
            normalized_summary="Profile reference promoted",
            collected_at=_dt(11),
        )
    ]

    return case


def test_timeline_builds_coherent_case_linked_events():
    service = TimelineService()
    case = _build_case()

    events = service.build_case_timeline(case)

    assert events
    assert all(event.case_id == case.id for event in events)

    categories = {event.category for event in events}
    assert TimelineCategory.SEARCH in categories
    assert TimelineCategory.RUN in categories
    assert TimelineCategory.FINDING in categories
    assert TimelineCategory.ENTITY in categories
    assert TimelineCategory.EVIDENCE in categories


def test_timeline_is_reverse_chronological_and_limited():
    service = TimelineService()
    case = _build_case()

    events = service.build_case_timeline(case, limit=5)

    assert len(events) == 5
    ordered = [event.occurred_at for event in events]
    assert ordered == sorted(ordered, reverse=True)


def test_timeline_includes_promotion_and_search_updates():
    service = TimelineService()
    case = _build_case()

    events = service.build_case_timeline(case)
    event_types = {event.event_type for event in events}

    assert "EVIDENCE_PROMOTED" in event_types
    assert "SEARCH_UPDATED" in event_types

"""Tests for intelligence repository CRUD behavior."""

from app.models.case import Case, Entity, EntityKind, Evidence, SourceReliability
from app.storage.database import Database
from app.storage.intelligence_repository import IntelligenceRepository


def test_repository_entity_and_evidence_crud(tmp_path):
    db = Database()
    db.initialize(str(tmp_path / "repo.db"))

    case = Case(name="Repo Ledger")
    db.save_case(case)

    repo = IntelligenceRepository(db)

    entity = Entity(case_id=case.id, kind=EntityKind.EMAIL, value="user@example.com")
    repo.create_entity(entity)

    entities = repo.list_entities(case.id)
    assert len(entities) == 1
    assert entities[0].value == "user@example.com"

    evidence = Evidence(
        case_id=case.id,
        entity_id=entity.id,
        source_reliability=SourceReliability.HIGH,
        raw_json_data={"provider": "breach_provider"},
        normalized_summary="High-confidence match found.",
    )
    repo.create_evidence(evidence)

    stored_evidence = repo.list_evidence(case.id)
    assert len(stored_evidence) == 1
    assert stored_evidence[0].source_reliability == SourceReliability.HIGH

    repo.delete_evidence(case.id, evidence.id)
    repo.delete_entity(case.id, entity.id)

    assert repo.list_entities(case.id) == []
    assert repo.list_evidence(case.id) == []

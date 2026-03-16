from datetime import datetime, timezone

from app.models.case import Entity, Evidence
from app.storage.database import Database


class IntelligenceRepository:
    """Repository for durable intelligence artifacts used in attribution workflows."""

    def __init__(self, db: Database):
        self.db = db

    def create_entity(self, entity: Entity) -> Entity:
        self.db.save_entity(entity)
        self.db.update_case_timestamp(entity.case_id)
        return entity

    def update_entity(self, entity: Entity) -> Entity:
        entity.updated_at = datetime.now(timezone.utc)
        self.db.save_entity(entity)
        self.db.update_case_timestamp(entity.case_id)
        return entity

    def list_entities(self, case_id: str) -> list[Entity]:
        return self.db.get_entities_for_case(case_id)

    def delete_entity(self, case_id: str, entity_id: str) -> None:
        self.db.delete_entity(entity_id, case_id)
        self.db.update_case_timestamp(case_id)

    def create_evidence(self, evidence: Evidence) -> Evidence:
        self.db.save_evidence(evidence)
        self.db.update_case_timestamp(evidence.case_id)
        return evidence

    def update_evidence(self, evidence: Evidence) -> Evidence:
        self.db.save_evidence(evidence)
        self.db.update_case_timestamp(evidence.case_id)
        return evidence

    def list_evidence(self, case_id: str) -> list[Evidence]:
        return self.db.get_evidence_for_case(case_id)

    def delete_evidence(self, case_id: str, evidence_id: str) -> None:
        self.db.delete_evidence(evidence_id, case_id)
        self.db.update_case_timestamp(case_id)

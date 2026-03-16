from datetime import datetime, timezone

from app.models.case import Case, CaseStatus, Finding, Note, Target, TargetType
from app.storage.database import Database


class CaseService:
    def __init__(self, db: Database):
        self.db = db

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
        case = self.db.load_case(case_id)
        case.findings.append(finding)
        case.updated_at = datetime.now(timezone.utc)
        self.db.save_case(case)

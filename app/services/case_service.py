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
        """Add a single finding.  Prefer add_findings_batch for bulk inserts."""
        self.add_findings_batch(case_id, [finding])

    def add_findings_batch(
        self, case_id: str, findings: list[Finding]
    ) -> tuple[list[Finding], int]:
        """
        Add multiple findings to a case, skipping semantic duplicates.

        Two findings are considered duplicates when they share the same
        (adapter_name, finding_type, title) within the same case.

        Returns:
            (added_findings, skipped_count)
        """
        existing = self.db.get_findings_for_case(case_id)
        # Build a set of (adapter_name, finding_type, title) keys already stored
        existing_keys: set[tuple[str, str, str]] = {
            (f.adapter_name, f.finding_type.value, f.title) for f in existing
        }

        to_add: list[Finding] = []
        skipped = 0
        for f in findings:
            key = (f.adapter_name, f.finding_type.value, f.title)
            if key in existing_keys:
                skipped += 1
            else:
                to_add.append(f)
                existing_keys.add(key)  # prevent within-batch duplicates too

        for f in to_add:
            self.db.save_finding(f, case_id)

        if to_add:
            self.db.update_case_timestamp(case_id)

        return to_add, skipped

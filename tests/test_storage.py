"""Tests for database storage."""
import pytest

from app.models.case import (
    Case,
    CaseStatus,
    Finding,
    FindingType,
    Severity,
    Target,
    TargetType,
)
from app.storage.database import Database


@pytest.fixture
def db(tmp_path):
    database = Database()
    database.initialize(str(tmp_path / "test.db"))
    return database


class TestDatabaseInitialization:
    def test_initialize_creates_tables(self, tmp_path):
        database = Database()
        database.initialize(str(tmp_path / "init_test.db"))
        cur = database.conn.cursor()
        tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in tables}
        assert "cases" in table_names
        assert "targets" in table_names
        assert "findings" in table_names
        assert "notes" in table_names
        assert "evidence" in table_names

    def test_initialize_default_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        database = Database()
        database.initialize()
        assert database.db_path == "osint_platform.db"


class TestCaseCRUD:
    def test_save_and_load_case(self, db):
        case = Case(name="Test Case", description="A description")
        db.save_case(case)
        loaded = db.load_case(case.id)
        assert loaded.id == case.id
        assert loaded.name == "Test Case"
        assert loaded.description == "A description"

    def test_load_nonexistent_case_raises(self, db):
        with pytest.raises(ValueError):
            db.load_case("nonexistent-id")

    def test_list_cases_empty(self, db):
        cases = db.list_cases()
        assert cases == []

    def test_list_cases_multiple(self, db):
        c1 = Case(name="Case One")
        c2 = Case(name="Case Two")
        db.save_case(c1)
        db.save_case(c2)
        cases = db.list_cases()
        assert len(cases) == 2
        names = {c.name for c in cases}
        assert "Case One" in names
        assert "Case Two" in names

    def test_delete_case(self, db):
        case = Case(name="Delete Me")
        db.save_case(case)
        db.delete_case(case.id)
        with pytest.raises(ValueError):
            db.load_case(case.id)

    def test_save_case_with_targets(self, db):
        case = Case(name="With Targets")
        t = Target(type=TargetType.DOMAIN, value="example.com")
        case.targets.append(t)
        db.save_case(case)
        loaded = db.load_case(case.id)
        assert len(loaded.targets) == 1
        assert loaded.targets[0].value == "example.com"
        assert loaded.targets[0].type == TargetType.DOMAIN

    def test_save_case_idempotent(self, db):
        case = Case(name="Idempotent")
        db.save_case(case)
        case.description = "Updated"
        db.save_case(case)
        loaded = db.load_case(case.id)
        assert loaded.description == "Updated"

    def test_case_status_preserved(self, db):
        case = Case(name="Status Test", status=CaseStatus.CLOSED)
        db.save_case(case)
        loaded = db.load_case(case.id)
        assert loaded.status == CaseStatus.CLOSED


class TestFindingStorage:
    def test_save_and_get_findings(self, db):
        case = Case(name="Finding Test")
        db.save_case(case)
        t = Target(type=TargetType.DOMAIN, value="example.com")
        finding = Finding(
            target_id=t.id,
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="A Record",
            description="IPv4 address found",
            severity=Severity.INFO,
            data={"ip": "93.184.216.34"},
        )
        db.save_finding(finding, case.id)
        findings = db.get_findings_for_case(case.id)
        assert len(findings) == 1
        assert findings[0].title == "A Record"
        assert findings[0].severity == Severity.INFO
        assert findings[0].data == {"ip": "93.184.216.34"}

    def test_get_findings_empty(self, db):
        case = Case(name="No Findings")
        db.save_case(case)
        assert db.get_findings_for_case(case.id) == []

    def test_save_finding_with_all_severities(self, db):
        case = Case(name="Severity Test")
        db.save_case(case)
        t = Target(type=TargetType.DOMAIN, value="example.com")
        for sev in Severity:
            f = Finding(
                target_id=t.id,
                adapter_name="test",
                finding_type=FindingType.GENERIC,
                title=f"Finding {sev.value}",
                description="test",
                severity=sev,
            )
            db.save_finding(f, case.id)
        findings = db.get_findings_for_case(case.id)
        assert len(findings) == len(list(Severity))

    def test_delete_case_removes_findings(self, db):
        case = Case(name="Delete With Findings")
        db.save_case(case)
        t = Target(type=TargetType.DOMAIN, value="example.com")
        f = Finding(
            target_id=t.id,
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="Test",
            description="desc",
            severity=Severity.LOW,
        )
        db.save_finding(f, case.id)
        db.delete_case(case.id)
        findings = db.get_findings_for_case(case.id)
        assert findings == []

"""Tests for Pydantic data models."""
import pytest
from datetime import datetime

from app.models.case import (
    Case,
    CaseStatus,
    Evidence,
    Finding,
    FindingType,
    InvestigationPreset,
    Note,
    Severity,
    Target,
    TargetType,
)


class TestTargetModel:
    def test_target_domain(self):
        t = Target(type=TargetType.DOMAIN, value="example.com")
        assert t.type == TargetType.DOMAIN
        assert t.value == "example.com"
        assert isinstance(t.id, str) and len(t.id) == 36
        assert isinstance(t.created_at, datetime)
        assert t.notes == []
        assert t.tags == []

    @pytest.mark.parametrize("tt", list(TargetType))
    def test_all_target_types(self, tt):
        t = Target(type=tt, value="test_value")
        assert t.type == tt

    def test_target_defaults(self):
        t1 = Target(type=TargetType.IP, value="1.2.3.4")
        t2 = Target(type=TargetType.IP, value="1.2.3.4")
        assert t1.id != t2.id  # unique IDs

    def test_target_with_tags_and_notes(self):
        t = Target(type=TargetType.EMAIL, value="a@b.com", tags=["recon"], notes=["note1"])
        assert "recon" in t.tags
        assert "note1" in t.notes


class TestFindingModel:
    @pytest.mark.parametrize("ft", list(FindingType))
    def test_all_finding_types(self, ft):
        f = Finding(
            target_id="tid",
            adapter_name="test",
            finding_type=ft,
            title="Test",
            description="desc",
            severity=Severity.INFO,
        )
        assert f.finding_type == ft

    @pytest.mark.parametrize("sev", list(Severity))
    def test_all_severities(self, sev):
        f = Finding(
            target_id="tid",
            adapter_name="test",
            finding_type=FindingType.GENERIC,
            title="Test",
            description="desc",
            severity=sev,
        )
        assert f.severity == sev

    def test_finding_defaults(self):
        f = Finding(
            target_id="tid",
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="A Record",
            description="desc",
            severity=Severity.LOW,
        )
        assert f.data == {}
        assert f.source_url == ""
        assert f.source_name == ""
        assert f.tags == []
        assert isinstance(f.collected_at, datetime)


class TestCaseModel:
    def test_create_case(self):
        case = Case(name="Test Case")
        assert case.name == "Test Case"
        assert case.description == ""
        assert case.targets == []
        assert case.findings == []
        assert case.notes == []
        assert case.evidence == []
        assert case.status == CaseStatus.OPEN

    def test_add_targets_and_findings(self):
        case = Case(name="Case")
        t = Target(type=TargetType.DOMAIN, value="example.com")
        f = Finding(
            target_id=t.id,
            adapter_name="dns",
            finding_type=FindingType.DNS,
            title="A Record",
            description="desc",
            severity=Severity.INFO,
        )
        case.targets.append(t)
        case.findings.append(f)
        assert len(case.targets) == 1
        assert len(case.findings) == 1

    def test_case_serialization(self):
        case = Case(name="Serialization Test", description="desc")
        t = Target(type=TargetType.USERNAME, value="johndoe")
        case.targets.append(t)

        data = case.model_dump()
        assert data["name"] == "Serialization Test"
        assert len(data["targets"]) == 1
        assert data["targets"][0]["value"] == "johndoe"

    def test_case_deserialization(self):
        original = Case(name="Round Trip")
        t = Target(type=TargetType.IP, value="10.0.0.1")
        original.targets.append(t)

        data = original.model_dump(mode="json")
        restored = Case.model_validate(data)
        assert restored.id == original.id
        assert restored.targets[0].value == "10.0.0.1"

    def test_note_model(self):
        n = Note(case_id="cid", content="Important observation")
        assert n.case_id == "cid"
        assert n.content == "Important observation"
        assert isinstance(n.id, str)
        assert isinstance(n.created_at, datetime)

    def test_evidence_model(self):
        e = Evidence(case_id="cid", file_path="/tmp/screenshot.png", description="Screenshot")
        assert e.finding_id is None
        e2 = Evidence(case_id="cid", finding_id="fid", file_path="/tmp/file.pdf", description="File")
        assert e2.finding_id == "fid"

    def test_investigation_preset_values(self):
        for preset in InvestigationPreset:
            assert isinstance(preset.value, str)

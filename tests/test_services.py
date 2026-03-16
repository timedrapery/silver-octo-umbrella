"""Tests for services."""
import pytest

from app.core.adapters.dns_adapter import DnsAdapter
from app.core.adapters.cert_adapter import CertAdapter
from app.core.adapters.http_adapter import HttpAdapter
from app.core.adapters.social_adapter import SocialAdapter
from app.core.adapters.subdomain_adapter import SubdomainAdapter
from app.core.adapters.metadata_adapter import MetadataAdapter
from app.models.case import Case, InvestigationPreset, Target, TargetType
from app.services.case_service import CaseService
from app.services.investigation_service import InvestigationService
from app.storage.database import Database


@pytest.fixture
def db(tmp_path):
    database = Database()
    database.initialize(str(tmp_path / "test.db"))
    return database


@pytest.fixture
def case_service(db):
    return CaseService(db)


@pytest.fixture
def investigation_service():
    adapters = [DnsAdapter(), CertAdapter(), HttpAdapter(), SocialAdapter(), SubdomainAdapter(), MetadataAdapter()]
    return InvestigationService(adapters)


class TestCaseService:
    def test_create_case(self, case_service):
        case = case_service.create_case("Test Case", "description")
        assert case.name == "Test Case"
        assert case.description == "description"
        assert isinstance(case.id, str)

    def test_create_case_no_description(self, case_service):
        case = case_service.create_case("Minimal Case")
        assert case.description == ""

    def test_get_case(self, case_service):
        created = case_service.create_case("Fetch Me")
        fetched = case_service.get_case(created.id)
        assert fetched.id == created.id
        assert fetched.name == "Fetch Me"

    def test_list_cases(self, case_service):
        case_service.create_case("Case A")
        case_service.create_case("Case B")
        cases = case_service.list_cases()
        names = [c.name for c in cases]
        assert "Case A" in names
        assert "Case B" in names

    def test_add_target(self, case_service):
        case = case_service.create_case("Target Test")
        target = case_service.add_target(case.id, TargetType.DOMAIN, "example.com")
        assert target.type == TargetType.DOMAIN
        assert target.value == "example.com"
        updated = case_service.get_case(case.id)
        assert len(updated.targets) == 1
        assert updated.targets[0].value == "example.com"

    def test_add_note(self, case_service):
        case = case_service.create_case("Note Test")
        note = case_service.add_note(case.id, "Interesting observation")
        assert note.content == "Interesting observation"
        assert note.case_id == case.id
        updated = case_service.get_case(case.id)
        assert len(updated.notes) == 1

    def test_delete_case(self, case_service):
        case = case_service.create_case("To Delete")
        case_service.delete_case(case.id)
        with pytest.raises(ValueError):
            case_service.get_case(case.id)

    def test_update_case(self, case_service):
        case = case_service.create_case("Update Me")
        case.description = "Updated description"
        case_service.update_case(case)
        updated = case_service.get_case(case.id)
        assert updated.description == "Updated description"


class TestInvestigationService:
    async def test_run_adapters_domain(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        findings = await investigation_service.run_adapters(target)
        assert isinstance(findings, list)
        assert len(findings) > 0

    async def test_run_adapters_filtered(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        findings = await investigation_service.run_adapters(target, adapter_names=["dns"])
        assert all(f.adapter_name == "dns" for f in findings)

    async def test_run_adapters_username(self, investigation_service):
        target = Target(type=TargetType.USERNAME, value="johndoe")
        findings = await investigation_service.run_adapters(target)
        assert len(findings) > 0
        assert all(f.adapter_name == "social" for f in findings)

    async def test_run_preset_domain_intelligence(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        findings = await investigation_service.run_preset(target, InvestigationPreset.DOMAIN_INTELLIGENCE)
        assert len(findings) > 0
        adapter_names = {f.adapter_name for f in findings}
        assert "dns" in adapter_names

    async def test_run_preset_username_investigation(self, investigation_service):
        target = Target(type=TargetType.USERNAME, value="testuser")
        findings = await investigation_service.run_preset(target, InvestigationPreset.USERNAME_INVESTIGATION)
        assert len(findings) > 0
        assert all(f.adapter_name == "social" for f in findings)

    async def test_run_preset_infrastructure_mapping(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        findings = await investigation_service.run_preset(target, InvestigationPreset.INFRASTRUCTURE_MAPPING)
        adapter_names = {f.adapter_name for f in findings}
        assert "dns" in adapter_names
        assert "http" in adapter_names

    async def test_run_preset_document_metadata(self, investigation_service):
        target = Target(type=TargetType.DOCUMENT, value="/tmp/report.pdf")
        findings = await investigation_service.run_preset(target, InvestigationPreset.DOCUMENT_METADATA_AUDIT)
        assert len(findings) > 0
        assert all(f.adapter_name == "metadata" for f in findings)

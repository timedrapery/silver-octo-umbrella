"""Tests for services."""
import pytest

from app.core.adapters.dns_adapter import DnsAdapter
from app.core.adapters.cert_adapter import CertAdapter
from app.core.adapters.http_adapter import HttpAdapter
from app.core.adapters.social_adapter import SocialAdapter
from app.core.adapters.subdomain_adapter import SubdomainAdapter
from app.core.adapters.metadata_adapter import MetadataAdapter
from app.models.case import Case, Finding, FindingType, InvestigationPreset, Severity, Target, TargetType
from app.services.case_service import CaseService
from app.services.graph_service import GraphService
from app.services.investigation_service import InvestigationService
from app.services.normalization import (
    Entity,
    extract_entities,
    build_entity_map,
    extract_case_summary,
)
from app.services.report_service import ReportService
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


# ─────────────────────────── CaseService ────────────────────────────────────

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


# ─────────────────────────── Deduplication ──────────────────────────────────

class TestDeduplication:
    def _make_finding(self, adapter_name: str, title: str, target_id: str = "t1") -> Finding:
        return Finding(
            target_id=target_id,
            adapter_name=adapter_name,
            finding_type=FindingType.DNS,
            title=title,
            description="desc",
            severity=Severity.INFO,
        )

    def test_add_findings_batch_no_duplicates(self, case_service):
        case = case_service.create_case("Dedup Test")
        findings = [
            self._make_finding("dns", "A Record"),
            self._make_finding("dns", "MX Record"),
        ]
        added, skipped = case_service.add_findings_batch(case.id, findings)
        assert len(added) == 2
        assert skipped == 0

    def test_add_findings_batch_skips_duplicates(self, case_service):
        case = case_service.create_case("Dedup Skip Test")
        f = self._make_finding("dns", "A Record: example.com")
        # Add once
        case_service.add_findings_batch(case.id, [f])
        # Add same finding again
        f2 = self._make_finding("dns", "A Record: example.com")
        added, skipped = case_service.add_findings_batch(case.id, [f2])
        assert len(added) == 0
        assert skipped == 1
        # Only 1 finding in DB
        loaded = case_service.get_case(case.id)
        assert len(loaded.findings) == 1

    def test_add_findings_batch_deduplicates_within_batch(self, case_service):
        case = case_service.create_case("Within Batch Dedup")
        # Two findings with the same key in the same batch
        findings = [
            self._make_finding("dns", "A Record"),
            self._make_finding("dns", "A Record"),  # duplicate
        ]
        added, skipped = case_service.add_findings_batch(case.id, findings)
        assert len(added) == 1
        assert skipped == 1

    def test_different_adapters_not_deduplicated(self, case_service):
        case = case_service.create_case("Different Adapters")
        findings = [
            self._make_finding("dns", "A Record"),
            self._make_finding("http", "A Record"),  # same title, different adapter
        ]
        added, skipped = case_service.add_findings_batch(case.id, findings)
        assert len(added) == 2
        assert skipped == 0

    def test_add_finding_compat_method(self, case_service):
        """add_finding (single) is a wrapper around add_findings_batch."""
        case = case_service.create_case("Single Finding")
        f = self._make_finding("dns", "NS Record")
        case_service.add_finding(case.id, f)
        loaded = case_service.get_case(case.id)
        assert len(loaded.findings) == 1


# ─────────────────────────── InvestigationService ───────────────────────────

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

    def test_get_active_adapters_domain(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        adapters = investigation_service.get_active_adapters(target)
        names = {a.name for a in adapters}
        assert "dns" in names
        assert "cert" in names
        assert "social" not in names

    def test_get_active_adapters_filtered(self, investigation_service):
        target = Target(type=TargetType.DOMAIN, value="example.com")
        adapters = investigation_service.get_active_adapters(target, adapter_names=["dns"])
        assert len(adapters) == 1
        assert adapters[0].name == "dns"

    def test_get_active_adapters_no_match(self, investigation_service):
        target = Target(type=TargetType.USERNAME, value="johndoe")
        adapters = investigation_service.get_active_adapters(target, adapter_names=["dns"])
        assert adapters == []


# ─────────────────────────── Normalization ───────────────────────────────────

def _finding(ftype: FindingType, data: dict, *, target_id: str = "t1") -> Finding:
    return Finding(
        target_id=target_id,
        adapter_name="test",
        finding_type=ftype,
        title="test",
        description="desc",
        severity=Severity.INFO,
        data=data,
    )


class TestNormalization:
    def test_dns_a_record_extracts_ip(self):
        f = _finding(FindingType.DNS, {"record_type": "A", "value": "1.2.3.4"})
        entities = extract_entities(f)
        assert any(e.entity_type == "ip" and e.value == "1.2.3.4" for e in entities)

    def test_dns_ns_record_extracts_domains(self):
        f = _finding(FindingType.DNS, {"record_type": "NS", "value": ["ns1.example.com", "ns2.example.com"]})
        entities = extract_entities(f)
        values = [e.value for e in entities if e.entity_type == "domain"]
        assert "ns1.example.com" in values
        assert "ns2.example.com" in values

    def test_cert_extracts_sans_and_issuer(self):
        f = _finding(
            FindingType.CERTIFICATE,
            {"sans": ["www.example.com", "api.example.com"], "issuer": "Let's Encrypt"},
        )
        entities = extract_entities(f)
        subdomains = [e.value for e in entities if e.entity_type == "subdomain"]
        assert "www.example.com" in subdomains
        orgs = [e.value for e in entities if e.entity_type == "organization"]
        assert "Let's Encrypt" in orgs

    def test_subdomain_extracts_subdomain_and_ip(self):
        f = _finding(FindingType.SUBDOMAIN, {"subdomain": "dev.example.com", "ip": "10.0.0.1"})
        entities = extract_entities(f)
        assert any(e.entity_type == "subdomain" for e in entities)
        assert any(e.entity_type == "ip" for e in entities)

    def test_http_extracts_server_and_tech(self):
        f = _finding(FindingType.HTTP, {"server": "nginx/1.24", "technologies": ["React", "Node.js"]})
        entities = extract_entities(f)
        software = [e.value for e in entities if e.entity_type == "software"]
        assert "nginx/1.24" in software
        assert "React" in software
        assert "Node.js" in software

    def test_social_extracts_platform(self):
        f = _finding(FindingType.SOCIAL, {"platform": "GitHub"})
        entities = extract_entities(f)
        assert any(e.entity_type == "platform" and e.value == "GitHub" for e in entities)

    def test_metadata_extracts_person_and_org(self):
        f = _finding(FindingType.METADATA, {"author": "Alice", "company": "Acme Corp"})
        entities = extract_entities(f)
        persons = [e.value for e in entities if e.entity_type == "person"]
        orgs = [e.value for e in entities if e.entity_type == "organization"]
        assert "Alice" in persons
        assert "Acme Corp" in orgs

    def test_build_entity_map_deduplicates(self):
        """Same IP appearing in two findings should produce one entity node."""
        case = Case(name="Dedup Entity")
        f1 = _finding(FindingType.DNS, {"record_type": "A", "value": "1.1.1.1"})
        f2 = _finding(FindingType.SUBDOMAIN, {"subdomain": "www.example.com", "ip": "1.1.1.1"})
        case.findings = [f1, f2]
        entity_map = build_entity_map(case)
        assert "ip:1.1.1.1" in entity_map
        # Source IDs from both findings merged
        assert len(entity_map["ip:1.1.1.1"].source_finding_ids) == 2

    def test_extract_case_summary(self):
        case = Case(name="Summary")
        case.findings = [
            _finding(FindingType.DNS, {"record_type": "A", "value": "8.8.8.8"}),
            _finding(FindingType.SOCIAL, {"platform": "Twitter/X"}),
        ]
        summary = extract_case_summary(case)
        assert "8.8.8.8" in summary["ips"]
        assert "Twitter/X" in summary["platforms"]


# ─────────────────────────── GraphService ────────────────────────────────────

class TestGraphService:
    def _make_case_with_dns_findings(self) -> Case:
        case = Case(name="Graph Test")
        target = Target(type=TargetType.DOMAIN, value="example.com")
        case.targets = [target]
        case.findings = [
            Finding(
                target_id=target.id,
                adapter_name="dns",
                finding_type=FindingType.DNS,
                title="A Record",
                description="desc",
                severity=Severity.INFO,
                data={"record_type": "A", "value": "93.184.216.34"},
            ),
            Finding(
                target_id=target.id,
                adapter_name="subdomain",
                finding_type=FindingType.SUBDOMAIN,
                title="Subdomain: www.example.com",
                description="desc",
                severity=Severity.INFO,
                data={"subdomain": "www.example.com", "ip": "93.184.216.34"},
            ),
        ]
        return case

    def test_graph_has_case_and_target_nodes(self):
        gs = GraphService()
        case = self._make_case_with_dns_findings()
        G = gs.build_graph(case)
        assert f"case:{case.id}" in G.nodes
        assert f"target:{case.targets[0].id}" in G.nodes

    def test_graph_has_entity_nodes(self):
        gs = GraphService()
        case = self._make_case_with_dns_findings()
        G = gs.build_graph(case)
        node_ids = list(G.nodes)
        # The IP 93.184.216.34 should appear as a node (from both DNS and subdomain findings)
        assert "ip:93.184.216.34" in node_ids

    def test_graph_has_subdomain_node(self):
        gs = GraphService()
        case = self._make_case_with_dns_findings()
        G = gs.build_graph(case)
        assert "subdomain:www.example.com" in G.nodes

    def test_get_node_data_structure(self):
        gs = GraphService()
        case = self._make_case_with_dns_findings()
        data = gs.get_node_data(case)
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_empty_case_graph(self):
        gs = GraphService()
        case = Case(name="Empty")
        G = gs.build_graph(case)
        assert f"case:{case.id}" in G.nodes
        assert len(G.nodes) == 1


# ─────────────────────────── ReportService ───────────────────────────────────

class TestReportService:
    def _make_populated_case(self) -> Case:
        from app.models.case import Note
        case = Case(name="Report Test", description="Test case for report generation")
        target = Target(type=TargetType.DOMAIN, value="example.com")
        case.targets = [target]
        case.findings = [
            Finding(
                target_id=target.id,
                adapter_name="dns",
                finding_type=FindingType.DNS,
                title="A Record",
                description="IPv4 address",
                severity=Severity.INFO,
                data={"record_type": "A", "value": "93.184.216.34"},
                source_url="https://example.com",
                source_name="DNS Lookup",
            ),
            Finding(
                target_id=target.id,
                adapter_name="http",
                finding_type=FindingType.HTTP,
                title="Missing Security Headers",
                description="Headers missing",
                severity=Severity.MEDIUM,
                data={},
            ),
        ]
        case.notes = [Note(case_id=case.id, content="Analyst observation: interesting target")]
        return case

    def test_generate_html(self, tmp_path):
        rs = ReportService()
        case = self._make_populated_case()
        out = str(tmp_path / "report.html")
        rs.generate_html(case, out)
        content = (tmp_path / "report.html").read_text(encoding="utf-8")
        assert "Report Test" in content
        assert "A Record" in content
        assert "Analyst Notes" in content
        assert "Analyst observation" in content
        assert "Discovered Entities" in content
        assert "93.184.216.34" in content

    def test_generate_json(self, tmp_path):
        import json as _json
        rs = ReportService()
        case = self._make_populated_case()
        out = str(tmp_path / "report.json")
        rs.generate_json(case, out)
        data = _json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
        assert data["name"] == "Report Test"
        assert len(data["findings"]) == 2

    def test_generate_csv(self, tmp_path):
        import csv as _csv
        rs = ReportService()
        case = self._make_populated_case()
        out = str(tmp_path / "report.csv")
        rs.generate_csv(case, out)
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(_csv.DictReader(f))
        assert len(rows) == 2
        titles = [r["title"] for r in rows]
        assert "A Record" in titles
        assert "Missing Security Headers" in titles
        # Verify source_url column exists
        assert "source_url" in rows[0]

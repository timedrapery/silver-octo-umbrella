"""Tests for OSINT adapters."""
import pytest

from app.core.adapters.base import BaseAdapter
from app.core.adapters.cert_adapter import CertAdapter
from app.core.adapters.dns_adapter import DnsAdapter
from app.core.adapters.http_adapter import HttpAdapter
from app.core.adapters.metadata_adapter import MetadataAdapter
from app.core.adapters.social_adapter import SocialAdapter
from app.core.adapters.subdomain_adapter import SubdomainAdapter
from app.models.case import Finding, FindingType, Target, TargetType


def _make_target(tt: TargetType, value: str) -> Target:
    return Target(type=tt, value=value)


class TestDnsAdapter:
    def test_can_handle_domain(self):
        adapter = DnsAdapter()
        assert adapter.can_handle(_make_target(TargetType.DOMAIN, "example.com"))

    def test_can_handle_url(self):
        adapter = DnsAdapter()
        assert adapter.can_handle(_make_target(TargetType.URL, "https://example.com"))

    def test_cannot_handle_username(self):
        adapter = DnsAdapter()
        assert not adapter.can_handle(_make_target(TargetType.USERNAME, "john"))

    async def test_run_returns_findings(self):
        adapter = DnsAdapter()
        t = _make_target(TargetType.DOMAIN, "example.com")
        findings = await adapter.run(t)
        assert isinstance(findings, list)
        assert len(findings) >= 3
        for f in findings:
            assert isinstance(f, Finding)
            assert f.finding_type == FindingType.DNS
            assert f.target_id == t.id

    async def test_run_url_target(self):
        adapter = DnsAdapter()
        t = _make_target(TargetType.URL, "https://example.com/page")
        findings = await adapter.run(t)
        assert len(findings) >= 1


class TestCertAdapter:
    def test_can_handle_domain(self):
        assert CertAdapter().can_handle(_make_target(TargetType.DOMAIN, "example.com"))

    def test_cannot_handle_ip(self):
        assert not CertAdapter().can_handle(_make_target(TargetType.IP, "1.2.3.4"))

    async def test_run_returns_findings(self):
        adapter = CertAdapter()
        t = _make_target(TargetType.DOMAIN, "example.com")
        findings = await adapter.run(t)
        assert isinstance(findings, list)
        assert len(findings) >= 2
        for f in findings:
            assert f.finding_type == FindingType.CERTIFICATE
            assert f.target_id == t.id


class TestHttpAdapter:
    def test_can_handle_domain(self):
        assert HttpAdapter().can_handle(_make_target(TargetType.DOMAIN, "example.com"))

    def test_can_handle_ip(self):
        assert HttpAdapter().can_handle(_make_target(TargetType.IP, "1.2.3.4"))

    def test_can_handle_url(self):
        assert HttpAdapter().can_handle(_make_target(TargetType.URL, "https://example.com"))

    def test_cannot_handle_username(self):
        assert not HttpAdapter().can_handle(_make_target(TargetType.USERNAME, "bob"))

    async def test_run_returns_findings(self):
        adapter = HttpAdapter()
        t = _make_target(TargetType.DOMAIN, "example.com")
        findings = await adapter.run(t)
        assert isinstance(findings, list)
        assert len(findings) >= 2
        for f in findings:
            assert f.finding_type == FindingType.HTTP


class TestSocialAdapter:
    def test_can_handle_username(self):
        assert SocialAdapter().can_handle(_make_target(TargetType.USERNAME, "johndoe"))

    def test_can_handle_email(self):
        assert SocialAdapter().can_handle(_make_target(TargetType.EMAIL, "j@example.com"))

    def test_cannot_handle_domain(self):
        assert not SocialAdapter().can_handle(_make_target(TargetType.DOMAIN, "example.com"))

    async def test_run_returns_findings(self):
        adapter = SocialAdapter()
        t = _make_target(TargetType.USERNAME, "johndoe")
        findings = await adapter.run(t)
        assert isinstance(findings, list)
        assert len(findings) >= 3
        for f in findings:
            assert f.finding_type == FindingType.SOCIAL


class TestSubdomainAdapter:
    def test_can_handle_domain(self):
        assert SubdomainAdapter().can_handle(_make_target(TargetType.DOMAIN, "example.com"))

    def test_cannot_handle_url(self):
        assert not SubdomainAdapter().can_handle(_make_target(TargetType.URL, "https://x.com"))

    async def test_run_returns_findings(self):
        adapter = SubdomainAdapter()
        t = _make_target(TargetType.DOMAIN, "example.com")
        findings = await adapter.run(t)
        assert isinstance(findings, list)
        assert len(findings) >= 5
        for f in findings:
            assert f.finding_type == FindingType.SUBDOMAIN
            assert "example.com" in f.data.get("subdomain", "")


class TestMetadataAdapter:
    def test_can_handle_document(self):
        assert MetadataAdapter().can_handle(_make_target(TargetType.DOCUMENT, "/tmp/file.pdf"))

    def test_can_handle_url(self):
        assert MetadataAdapter().can_handle(_make_target(TargetType.URL, "https://example.com/doc.pdf"))

    def test_cannot_handle_domain(self):
        assert not MetadataAdapter().can_handle(_make_target(TargetType.DOMAIN, "example.com"))

    async def test_run_returns_findings(self):
        adapter = MetadataAdapter()
        t = _make_target(TargetType.DOCUMENT, "/tmp/test.pdf")
        findings = await adapter.run(t)
        assert isinstance(findings, list)
        assert len(findings) >= 2
        for f in findings:
            assert f.finding_type == FindingType.METADATA

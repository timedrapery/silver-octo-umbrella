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

        async def fake_resolve(_client, _domain, record_type):
            payloads = {
                "A": [{"value": "93.184.216.34", "ttl": 300}],
                "AAAA": [{"value": "2606:2800:220:1:248:1893:25c8:1946", "ttl": 300}],
                "MX": [{"value": "10 mail.example.com", "ttl": 300}],
                "NS": [{"value": "ns1.example.com", "ttl": 300}],
                "TXT": [{"value": "v=spf1 include:_spf.example.com ~all", "ttl": 300}],
            }
            return payloads[record_type]

        adapter._resolve_record_type = fake_resolve
        findings = await adapter.run(t)
        assert isinstance(findings, list)
        assert len(findings) == 5
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

        adapter._fetch_live_certificate = lambda _domain: {
            "common_name": "example.com",
            "issuer": "Example CA",
            "not_before": "2024-01-01T00:00:00+00:00",
            "not_after": "2025-01-01T00:00:00+00:00",
            "serial_number": "1234",
            "sans": ["example.com", "www.example.com"],
        }

        async def fake_history(_domain):
            return {
                "certificate_count": 3,
                "unique_name_count": 2,
                "names": ["example.com", "www.example.com"],
            }

        adapter._fetch_certificate_history = fake_history
        findings = await adapter.run(t)
        assert isinstance(findings, list)
        assert len(findings) == 3
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
        class FakeResponse:
            def __init__(self, url, status_code, headers=None, text=""):
                self.url = url
                self.status_code = status_code
                self.headers = headers or {}
                self.text = text

            def raise_for_status(self):
                return None

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url):
                if url == "https://example.com":
                    return FakeResponse(
                        url,
                        200,
                        headers={"server": "nginx", "x-powered-by": "Next.js"},
                        text="<html><body><div id='__next'></div></body></html>",
                    )
                return FakeResponse(url, 404)

        import app.core.adapters.http_adapter as http_module

        original_client = http_module.httpx.AsyncClient
        http_module.httpx.AsyncClient = FakeClient
        adapter = HttpAdapter()
        t = _make_target(TargetType.DOMAIN, "example.com")
        try:
            findings = await adapter.run(t)
            assert isinstance(findings, list)
            assert len(findings) == 4
            for f in findings:
                assert f.finding_type == FindingType.HTTP
        finally:
            http_module.httpx.AsyncClient = original_client


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

        async def fake_profiles(_client, username):
            return [
                {
                    "platform": "GitHub",
                    "url": f"https://github.com/{username}",
                    "description": f"GitHub account {username} found.",
                },
                {
                    "platform": "GitLab",
                    "url": f"https://gitlab.com/{username}",
                    "description": f"GitLab account {username} found.",
                },
            ]

        async def fake_gravatar(_client, _email):
            return None

        adapter._lookup_username_profiles = fake_profiles
        adapter._lookup_gravatar = fake_gravatar
        findings = await adapter.run(t)
        assert isinstance(findings, list)
        assert len(findings) == 2
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

        async def fake_fetch(domain):
            return [f"www.{domain}", f"admin.{domain}", f"api.{domain}"]

        adapter._fetch_subdomains = fake_fetch
        adapter._resolve_addresses = lambda hostname: ["93.184.216.34"] if hostname != "admin.example.com" else []
        findings = await adapter.run(t)
        assert isinstance(findings, list)
        assert len(findings) == 3
        for f in findings:
            assert f.finding_type == FindingType.SUBDOMAIN
            subdomain = f.data.get("subdomain", "")
            assert subdomain.endswith(".example.com") or subdomain == "example.com"


class TestMetadataAdapter:
    def test_can_handle_document(self):
        assert MetadataAdapter().can_handle(_make_target(TargetType.DOCUMENT, "/tmp/file.pdf"))

    def test_can_handle_url(self):
        assert MetadataAdapter().can_handle(_make_target(TargetType.URL, "https://example.com/doc.pdf"))

    def test_cannot_handle_domain(self):
        assert not MetadataAdapter().can_handle(_make_target(TargetType.DOMAIN, "example.com"))

    async def test_run_returns_findings(self, tmp_path):
        adapter = MetadataAdapter()
        document = tmp_path / "test.pdf"
        document.write_text("test document", encoding="utf-8")
        t = _make_target(TargetType.DOCUMENT, str(document))
        findings = await adapter.run(t)
        assert isinstance(findings, list)
        assert len(findings) >= 2
        for f in findings:
            assert f.finding_type == FindingType.METADATA

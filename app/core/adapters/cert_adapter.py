import asyncio
import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class CertAdapter(BaseAdapter):
    name = "cert"
    description = "Certificate transparency log analysis"
    supported_target_types = [TargetType.DOMAIN, TargetType.URL]

    async def run(self, target: Target) -> list[Finding]:
        domain = self._normalize_domain(target.value)
        findings: list[Finding] = []

        certificate = await asyncio.to_thread(self._fetch_live_certificate, domain)
        findings.append(
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.CERTIFICATE,
                title=f"TLS Certificate: {domain}",
                description=(
                    f"Live TLS certificate for {domain} issued by {certificate['issuer']} "
                    f"valid from {certificate['not_before']} to {certificate['not_after']}."
                ),
                data=certificate,
                severity=Severity.INFO,
                source_name="Live TLS Handshake",
                source_url=f"https://{domain}",
            )
        )

        sans = certificate.get("sans", [])
        if sans:
            findings.append(
                Finding(
                    target_id=target.id,
                    adapter_name=self.name,
                    finding_type=FindingType.CERTIFICATE,
                    title=f"Subject Alternative Names: {domain}",
                    description=f"Certificate covers {len(sans)} SANs: {', '.join(sans)}",
                    data={"sans": sans, "count": len(sans)},
                    severity=Severity.LOW,
                    source_name="Live TLS Handshake",
                    source_url=f"https://{domain}",
                )
            )

        history = await self._fetch_certificate_history(domain)
        if history:
            findings.append(
                Finding(
                    target_id=target.id,
                    adapter_name=self.name,
                    finding_type=FindingType.CERTIFICATE,
                    title=f"Historical Certificates: {domain}",
                    description=(
                        f"Observed {history['certificate_count']} certificate transparency entries "
                        f"covering {history['unique_name_count']} unique names."
                    ),
                    data=history,
                    severity=Severity.INFO,
                    source_name="crt.sh",
                    source_url=f"https://crt.sh/?q={quote(domain)}",
                )
            )

        return findings

    @staticmethod
    def _normalize_domain(raw_value: str) -> str:
        value = raw_value.replace("https://", "").replace("http://", "")
        return value.split("/")[0].strip().rstrip(".")

    @staticmethod
    def _fetch_live_certificate(domain: str) -> dict:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=8) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as tls_socket:
                cert = tls_socket.getpeercert()

        issuer = ", ".join(value for entry in cert.get("issuer", []) for _, value in entry)
        subject = cert.get("subject", [])
        common_name = domain
        for entry in subject:
            for key, value in entry:
                if key == "commonName":
                    common_name = value

        san_entries = [value for key, value in cert.get("subjectAltName", []) if key == "DNS"]
        not_before = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notBefore"]), tz=timezone.utc)
        not_after = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), tz=timezone.utc)
        return {
            "common_name": common_name,
            "issuer": issuer,
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
            "serial_number": cert.get("serialNumber", ""),
            "sans": san_entries,
        }

    async def _fetch_certificate_history(self, domain: str) -> dict:
        url = f"https://crt.sh/?q={quote(domain)}&output=json"
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0)) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

        names: set[str] = set()
        for item in payload:
            name_value = str(item.get("name_value", "")).strip()
            for candidate in name_value.splitlines():
                candidate = candidate.strip().lstrip("*.")
                if candidate:
                    names.add(candidate)
        return {
            "certificate_count": len(payload),
            "unique_name_count": len(names),
            "names": sorted(names)[:25],
        }

import asyncio
import socket
from urllib.parse import quote

import httpx

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class SubdomainAdapter(BaseAdapter):
    name = "subdomain"
    description = "Subdomain enumeration"
    supported_target_types = [TargetType.DOMAIN]

    async def run(self, target: Target) -> list[Finding]:
        domain = target.value
        subdomains = await self._fetch_subdomains(domain)
        findings = []
        for subdomain in subdomains:
            addresses = await asyncio.to_thread(self._resolve_addresses, subdomain)
            severity = Severity.LOW if any(token in subdomain for token in ("admin", "vpn", "remote", "portal", "staging", "dev")) else Severity.INFO
            findings.append(
                Finding(
                    target_id=target.id,
                    adapter_name=self.name,
                    finding_type=FindingType.SUBDOMAIN,
                    title=f"Subdomain: {subdomain}",
                    description=self._describe_subdomain(subdomain, addresses),
                    data={
                        "subdomain": subdomain,
                        "addresses": addresses,
                        "status": "active" if addresses else "observed_in_ct",
                    },
                    severity=severity,
                    source_name="crt.sh",
                    source_url=f"https://crt.sh/?q={quote(domain)}",
                )
            )
        return findings

    async def _fetch_subdomains(self, domain: str) -> list[str]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0)) as client:
            response = await client.get(f"https://crt.sh/?q={quote(domain)}&output=json")
            response.raise_for_status()
            payload = response.json()

        candidates: set[str] = set()
        suffix = f".{domain.lower()}"
        for item in payload:
            name_value = str(item.get("name_value", "")).strip()
            for entry in name_value.splitlines():
                normalized = entry.strip().lower().lstrip("*.")
                if normalized == domain.lower() or normalized.endswith(suffix):
                    candidates.add(normalized)
        return sorted(candidates)[:25]

    @staticmethod
    def _resolve_addresses(hostname: str) -> list[str]:
        try:
            records = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        except socket.gaierror:
            return []

        addresses = {record[4][0] for record in records if record[4]}
        return sorted(addresses)

    @staticmethod
    def _describe_subdomain(subdomain: str, addresses: list[str]) -> str:
        if addresses:
            return f"Observed subdomain {subdomain} in certificate transparency and resolved it to {', '.join(addresses)}"
        return f"Observed subdomain {subdomain} in certificate transparency logs but DNS resolution did not complete"

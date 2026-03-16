import asyncio
import random

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class SubdomainAdapter(BaseAdapter):
    name = "subdomain"
    description = "Subdomain enumeration"
    supported_target_types = [TargetType.DOMAIN]

    async def run(self, target: Target) -> list[Finding]:
        await asyncio.sleep(random.uniform(0.5, 2.0))
        domain = target.value

        prefixes = [
            "www", "mail", "api", "dev", "staging", "cdn", "static",
            "blog", "shop", "admin", "vpn", "remote", "ftp", "smtp",
            "ns1", "ns2", "autodiscover", "webmail", "portal",
        ]

        count = random.randint(5, 10)
        selected = random.sample(prefixes, count)

        ips = [
            "93.184.216.34", "104.21.45.123", "172.67.189.45",
            "185.199.108.153", "151.101.1.195", "13.32.99.100",
        ]

        findings = []
        for sub in selected:
            subdomain = f"{sub}.{domain}"
            ip = random.choice(ips)
            severity = Severity.LOW if sub in ("admin", "vpn", "remote", "portal") else Severity.INFO
            findings.append(
                Finding(
                    target_id=target.id,
                    adapter_name=self.name,
                    finding_type=FindingType.SUBDOMAIN,
                    title=f"Subdomain: {subdomain}",
                    description=f"Active subdomain discovered: {subdomain} resolves to {ip}",
                    data={"subdomain": subdomain, "ip": ip, "status": "active"},
                    severity=severity,
                    source_name="Subdomain Enumeration",
                    source_url=f"https://{subdomain}",
                )
            )
        return findings

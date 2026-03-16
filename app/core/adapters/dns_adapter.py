import asyncio
import random

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class DnsAdapter(BaseAdapter):
    name = "dns"
    description = "DNS record enumeration"
    supported_target_types = [TargetType.DOMAIN, TargetType.URL]

    async def run(self, target: Target) -> list[Finding]:
        await asyncio.sleep(random.uniform(0.5, 2.0))
        domain = target.value.replace("https://", "").replace("http://", "").split("/")[0]

        records = [
            {
                "record_type": "A",
                "title": f"A Record: {domain}",
                "description": f"IPv4 address resolved for {domain}: 93.184.216.34",
                "data": {"record_type": "A", "value": "93.184.216.34", "ttl": 3600},
                "severity": Severity.INFO,
            },
            {
                "record_type": "MX",
                "title": f"MX Record: {domain}",
                "description": f"Mail exchange server for {domain}: mail.{domain} (priority 10)",
                "data": {"record_type": "MX", "value": f"mail.{domain}", "priority": 10, "ttl": 3600},
                "severity": Severity.INFO,
            },
            {
                "record_type": "TXT",
                "title": f"TXT Record: SPF Policy",
                "description": f"SPF record found for {domain}: v=spf1 include:_spf.google.com ~all",
                "data": {"record_type": "TXT", "value": "v=spf1 include:_spf.google.com ~all"},
                "severity": Severity.LOW,
            },
            {
                "record_type": "NS",
                "title": f"NS Record: {domain}",
                "description": f"Name servers for {domain}: ns1.{domain}, ns2.{domain}",
                "data": {"record_type": "NS", "value": [f"ns1.{domain}", f"ns2.{domain}"]},
                "severity": Severity.INFO,
            },
            {
                "record_type": "AAAA",
                "title": f"AAAA Record: {domain}",
                "description": f"IPv6 address resolved for {domain}: 2606:2800:220:1:248:1893:25c8:1946",
                "data": {"record_type": "AAAA", "value": "2606:2800:220:1:248:1893:25c8:1946"},
                "severity": Severity.INFO,
            },
        ]

        count = random.randint(3, 5)
        findings = []
        for rec in records[:count]:
            findings.append(
                Finding(
                    target_id=target.id,
                    adapter_name=self.name,
                    finding_type=FindingType.DNS,
                    title=rec["title"],
                    description=rec["description"],
                    data=rec["data"],
                    severity=rec["severity"],
                    source_name="DNS Lookup",
                )
            )
        return findings

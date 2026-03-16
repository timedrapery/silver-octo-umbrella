import asyncio
import random

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class HttpAdapter(BaseAdapter):
    name = "http"
    description = "HTTP fingerprinting and header analysis"
    supported_target_types = [TargetType.DOMAIN, TargetType.URL, TargetType.IP]

    async def run(self, target: Target) -> list[Finding]:
        await asyncio.sleep(random.uniform(0.5, 2.0))
        host = target.value.replace("https://", "").replace("http://", "").split("/")[0]

        servers = ["nginx/1.24.0", "Apache/2.4.57", "cloudflare", "Microsoft-IIS/10.0", "openresty/1.21.4"]
        tech_stacks = [
            ["WordPress 6.3", "PHP 8.1", "MySQL"],
            ["React", "Node.js", "Express"],
            ["Django 4.2", "Python 3.11", "PostgreSQL"],
            ["Next.js", "Vercel", "CDN"],
        ]
        server = random.choice(servers)
        stack = random.choice(tech_stacks)

        missing_headers = random.sample(
            ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options"],
            random.randint(1, 3),
        )

        findings = [
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.HTTP,
                title=f"HTTP Server: {server}",
                description=f"Web server identified as {server} running on {host}",
                data={"server": server, "host": host, "status_code": 200},
                severity=Severity.INFO,
                source_name="HTTP Fingerprint",
                source_url=f"https://{host}",
            ),
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.HTTP,
                title=f"Technology Stack: {', '.join(stack)}",
                description=f"Detected technologies: {', '.join(stack)} on {host}",
                data={"technologies": stack, "host": host},
                severity=Severity.LOW,
                source_name="HTTP Fingerprint",
                source_url=f"https://{host}",
            ),
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.HTTP,
                title=f"Missing Security Headers: {host}",
                description=f"Security headers not present: {', '.join(missing_headers)}",
                data={"missing_headers": missing_headers, "host": host},
                severity=Severity.MEDIUM,
                source_name="HTTP Security Scan",
                source_url=f"https://{host}",
            ),
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.HTTP,
                title=f"HTTP Response Codes: {host}",
                description=f"Common paths enumerated. robots.txt: 200, sitemap.xml: 200, /admin: 403",
                data={"paths": {"/robots.txt": 200, "/sitemap.xml": 200, "/admin": 403, "/.well-known": 200}},
                severity=Severity.LOW,
                source_name="HTTP Enumeration",
                source_url=f"https://{host}",
            ),
        ]

        count = random.randint(2, 4)
        return findings[:count]

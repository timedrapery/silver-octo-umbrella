import asyncio
import random
from datetime import datetime, timedelta, timezone

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class CertAdapter(BaseAdapter):
    name = "cert"
    description = "Certificate transparency log analysis"
    supported_target_types = [TargetType.DOMAIN, TargetType.URL]

    async def run(self, target: Target) -> list[Finding]:
        await asyncio.sleep(random.uniform(0.5, 2.0))
        domain = target.value.replace("https://", "").replace("http://", "").split("/")[0]

        issued = datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365))
        expiry = issued + timedelta(days=397)
        issuers = ["Let's Encrypt", "DigiCert", "Sectigo", "GlobalSign"]
        issuer = random.choice(issuers)

        san_subdomains = ["www", "mail", "api", "cdn", "dev", "staging"]
        sans = [f"{s}.{domain}" for s in random.sample(san_subdomains, random.randint(2, 4))]
        sans.insert(0, domain)

        records = [
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.CERTIFICATE,
                title=f"TLS Certificate: {domain}",
                description=(
                    f"Certificate issued by {issuer} for {domain}. "
                    f"Valid from {issued.strftime('%Y-%m-%d')} to {expiry.strftime('%Y-%m-%d')}."
                ),
                data={
                    "common_name": domain,
                    "issuer": issuer,
                    "not_before": issued.isoformat(),
                    "not_after": expiry.isoformat(),
                    "serial_number": hex(random.getrandbits(128)),
                },
                severity=Severity.INFO,
                source_name="Certificate Transparency",
                source_url=f"https://crt.sh/?q={domain}",
            ),
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.CERTIFICATE,
                title=f"Subject Alternative Names: {domain}",
                description=f"Certificate covers {len(sans)} SANs: {', '.join(sans)}",
                data={"sans": sans, "count": len(sans)},
                severity=Severity.LOW,
                source_name="Certificate Transparency",
                source_url=f"https://crt.sh/?q={domain}",
            ),
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.CERTIFICATE,
                title=f"Historical Certificates: {domain}",
                description=f"Found {random.randint(3, 12)} historical certificates in CT logs for {domain}",
                data={"certificate_count": random.randint(3, 12), "oldest_year": random.randint(2015, 2020)},
                severity=Severity.INFO,
                source_name="Certificate Transparency",
                source_url=f"https://crt.sh/?q={domain}",
            ),
        ]

        count = random.randint(2, 3)
        return records[:count]

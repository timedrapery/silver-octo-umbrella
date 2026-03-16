import httpx

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class DnsAdapter(BaseAdapter):
    name = "dns"
    description = "DNS record enumeration"
    supported_target_types = [TargetType.DOMAIN, TargetType.URL]
    _DOH_ENDPOINT = "https://dns.google/resolve"

    async def run(self, target: Target) -> list[Finding]:
        findings = []
        domain = self._normalize_domain(target.value)
        record_types = ["A", "AAAA", "MX", "NS", "TXT"]
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            for record_type in record_types:
                answers = await self._resolve_record_type(client, domain, record_type)
                for answer in answers:
                    findings.append(
                        Finding(
                            target_id=target.id,
                            adapter_name=self.name,
                            finding_type=FindingType.DNS,
                            title=f"{record_type} Record: {domain}",
                            description=self._describe_record(domain, record_type, answer),
                            data={
                                "record_type": record_type,
                                "value": answer["value"],
                                "ttl": answer.get("ttl", 0),
                            },
                            severity=self._severity_for_record(record_type, answer["value"]),
                            source_name="Google DNS-over-HTTPS",
                            source_url=f"{self._DOH_ENDPOINT}?name={domain}&type={record_type}",
                        )
                    )
        return findings

    @staticmethod
    def _normalize_domain(raw_value: str) -> str:
        value = raw_value.replace("https://", "").replace("http://", "")
        return value.split("/")[0].strip().rstrip(".")

    async def _resolve_record_type(
        self,
        client: httpx.AsyncClient,
        domain: str,
        record_type: str,
    ) -> list[dict]:
        response = await client.get(
            self._DOH_ENDPOINT,
            params={"name": domain, "type": record_type},
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        answers = payload.get("Answer") or []
        normalized: list[dict] = []
        for answer in answers:
            data = str(answer.get("data", "")).strip()
            if not data:
                continue
            normalized.append({"value": data.rstrip("."), "ttl": int(answer.get("TTL", 0))})
        return normalized

    @staticmethod
    def _describe_record(domain: str, record_type: str, answer: dict) -> str:
        return f"{record_type} record for {domain}: {answer['value']} (TTL {answer.get('ttl', 0)})"

    @staticmethod
    def _severity_for_record(record_type: str, value: str) -> Severity:
        if record_type == "TXT" and ("spf1" in value.lower() or "dmarc" in value.lower()):
            return Severity.LOW
        return Severity.INFO

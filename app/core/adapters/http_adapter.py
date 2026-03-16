from urllib.parse import urlparse

import httpx

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class HttpAdapter(BaseAdapter):
    name = "http"
    description = "HTTP fingerprinting and header analysis"
    supported_target_types = [TargetType.DOMAIN, TargetType.URL, TargetType.IP]
    _SECURITY_HEADERS = [
        "strict-transport-security",
        "content-security-policy",
        "x-frame-options",
        "x-content-type-options",
    ]
    _ENUM_PATHS = ["/robots.txt", "/sitemap.xml", "/admin", "/.well-known/"]

    async def run(self, target: Target) -> list[Finding]:
        base_url = self._normalize_base_url(target.value)
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0), follow_redirects=True) as client:
            response = await client.get(base_url)
            response.raise_for_status()
            findings = self._build_primary_findings(target, base_url, response)
            findings.append(await self._build_path_finding(client, target, base_url))
            return findings

    @staticmethod
    def _normalize_base_url(raw_value: str) -> str:
        if raw_value.startswith(("http://", "https://")):
            return raw_value.rstrip("/")
        return f"https://{raw_value.strip().rstrip('/')}"

    def _build_primary_findings(self, target: Target, base_url: str, response: httpx.Response) -> list[Finding]:
        parsed = urlparse(str(response.url))
        host = parsed.netloc or parsed.path
        headers = {key.lower(): value for key, value in response.headers.items()}
        missing_headers = [header for header in self._SECURITY_HEADERS if header not in headers]
        technology_markers = self._detect_technologies(headers, response.text)

        findings = [
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.HTTP,
                title=f"HTTP Endpoint: {host}",
                description=f"Collected HTTP response from {response.url} with status {response.status_code}",
                data={
                    "host": host,
                    "status_code": response.status_code,
                    "final_url": str(response.url),
                    "server": headers.get("server", ""),
                },
                severity=Severity.INFO,
                source_name="HTTP Fingerprint",
                source_url=str(response.url),
            )
        ]

        if technology_markers:
            findings.append(
                Finding(
                    target_id=target.id,
                    adapter_name=self.name,
                    finding_type=FindingType.HTTP,
                    title=f"Technology Markers: {host}",
                    description=f"Observed HTTP technology markers: {', '.join(technology_markers)}",
                    data={"technologies": technology_markers, "host": host},
                    severity=Severity.LOW,
                    source_name="HTTP Fingerprint",
                    source_url=str(response.url),
                )
            )

        if missing_headers:
            findings.append(
                Finding(
                    target_id=target.id,
                    adapter_name=self.name,
                    finding_type=FindingType.HTTP,
                    title=f"Missing Security Headers: {host}",
                    description=f"Security headers not present: {', '.join(missing_headers)}",
                    data={"missing_headers": missing_headers, "host": host},
                    severity=Severity.MEDIUM,
                    source_name="HTTP Security Scan",
                    source_url=str(response.url),
                )
            )
        return findings

    async def _build_path_finding(
        self,
        client: httpx.AsyncClient,
        target: Target,
        base_url: str,
    ) -> Finding:
        path_statuses: dict[str, int | str] = {}
        for path in self._ENUM_PATHS:
            url = f"{base_url.rstrip('/')}{path}"
            try:
                response = await client.get(url)
                path_statuses[path] = response.status_code
            except httpx.HTTPError as exc:
                path_statuses[path] = f"error: {exc.__class__.__name__}"

        host = urlparse(base_url).netloc or base_url
        return Finding(
            target_id=target.id,
            adapter_name=self.name,
            finding_type=FindingType.HTTP,
            title=f"HTTP Path Enumeration: {host}",
            description=(
                "Collected response status codes for common discovery paths: "
                + ", ".join(f"{path}={status}" for path, status in path_statuses.items())
            ),
            data={"paths": path_statuses, "host": host},
            severity=Severity.LOW,
            source_name="HTTP Enumeration",
            source_url=base_url,
        )

    @staticmethod
    def _detect_technologies(headers: dict[str, str], body: str) -> list[str]:
        markers: list[str] = []
        if headers.get("server"):
            markers.append(headers["server"])
        if headers.get("x-powered-by"):
            markers.append(headers["x-powered-by"])
        lower_body = body.lower()
        if "wp-content" in lower_body:
            markers.append("WordPress")
        if "__next" in lower_body:
            markers.append("Next.js")
        if "react" in lower_body and "react" not in " ".join(markers).lower():
            markers.append("React")
        return markers

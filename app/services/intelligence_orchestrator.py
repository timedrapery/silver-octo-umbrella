import asyncio
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, Field, field_validator

from app.services.managed_network_client import ManagedNetworkClient


class ResearchEntityRequest(BaseModel):
    """Typed research request for phone, email, IP, or username investigations."""

    entity_type: Literal["PHONE", "EMAIL", "IP", "USERNAME"]
    entity_value: str

    @field_validator("entity_value")
    @classmethod
    def validate_entity_value(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Entity value is required")
        return cleaned

    @field_validator("entity_value")
    @classmethod
    def validate_by_entity_type(cls, value: str, info):
        if info.data.get("entity_type") == "PHONE":
            normalized = re.sub(r"[^\d+]", "", value)
            digits = re.sub(r"\D", "", normalized)
            if len(digits) < 7:
                raise ValueError("Invalid phone number")
        if info.data.get("entity_type") == "EMAIL":
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
                raise ValueError("Invalid email address")
        return value


class ProviderExecutionMetric(BaseModel):
    provider_name: str
    duration_seconds: float
    success: bool
    result_count: int
    error_message: str = ""


class ResearchEvidenceItem(BaseModel):
    provider_name: str
    data: dict = Field(default_factory=dict)


class ResearchEntityResult(BaseModel):
    request: ResearchEntityRequest
    providers: list[ProviderExecutionMetric]
    evidence_items: list[ResearchEvidenceItem]


class ResearchProviderAdapter(ABC):
    name: str

    @abstractmethod
    async def query(
        self,
        request: ResearchEntityRequest,
        network: ManagedNetworkClient,
    ) -> list[dict]:
        """Return normalized provider records for the target request."""


class BreachProviderAdapter(ResearchProviderAdapter):
    name = "breach_provider"
    _HIBP_ENDPOINT_TEMPLATE = "https://haveibeenpwned.com/api/v3/breachedaccount/{account}"
    _HIBP_USER_AGENT = "silver-octo-umbrella/1.0"

    async def query(
        self,
        request: ResearchEntityRequest,
        network: ManagedNetworkClient,
    ) -> list[dict]:
        if request.entity_type != "EMAIL":
            return []

        endpoint = os.getenv("BREACH_PROVIDER_ENDPOINT", "").strip()
        if endpoint:
            response = await network.request_json(
                "GET",
                endpoint,
                params={"q": request.entity_value},
            )
            if isinstance(response.json_data, list):
                return [dict(item) for item in response.json_data if isinstance(item, dict)]

        hibp_api_key = os.getenv("HIBP_API_KEY", "").strip()
        if not hibp_api_key:
            raise RuntimeError("HIBP_API_KEY is not configured for breach provider")

        encoded_account = quote(request.entity_value, safe="")
        response = await network.request_json(
            "GET",
            self._HIBP_ENDPOINT_TEMPLATE.format(account=encoded_account),
            headers={
                "hibp-api-key": hibp_api_key,
                "user-agent": self._HIBP_USER_AGENT,
                "accept": "application/json",
            },
            params={"truncateResponse": "false"},
        )

        if response.status_code == 404:
            return []
        if response.status_code in (401, 403):
            raise RuntimeError("HIBP authentication failed")
        if response.status_code == 429:
            raise RuntimeError("HIBP rate limit exceeded")
        if response.status_code >= 400:
            raise RuntimeError(f"HIBP request failed with status {response.status_code}")

        if isinstance(response.json_data, list):
            return [
                self._normalize_hibp_record(record, request.entity_value)
                for record in response.json_data
                if isinstance(record, dict)
            ]
        return []

    @staticmethod
    def _normalize_hibp_record(record: dict, email: str) -> dict:
        return {
            "indicator": email,
            "provider": "haveibeenpwned",
            "breach_name": record.get("Name", ""),
            "breach_title": record.get("Title", ""),
            "domain": record.get("Domain", ""),
            "breach_date": record.get("BreachDate", ""),
            "added_date": record.get("AddedDate", ""),
            "pwn_count": record.get("PwnCount", 0),
            "data_classes": record.get("DataClasses", []),
            "verified": record.get("IsVerified", False),
            "fabricated": record.get("IsFabricated", False),
            "sensitive": record.get("IsSensitive", False),
        }


class InfrastructureProviderAdapter(ResearchProviderAdapter):
    name = "infrastructure_provider"

    async def query(
        self,
        request: ResearchEntityRequest,
        network: ManagedNetworkClient,
    ) -> list[dict]:
        endpoint = os.getenv("INFRA_PROVIDER_ENDPOINT", "").strip()
        if endpoint:
            response = await network.request_json(
                "GET",
                endpoint,
                params={"q": request.entity_value},
            )
            if isinstance(response.json_data, list):
                return [dict(item) for item in response.json_data if isinstance(item, dict)]
        if request.entity_type == "IP":
            response = await network.request_json(
                "GET",
                f"https://ipwho.is/{request.entity_value}",
            )
            if isinstance(response.json_data, dict) and response.json_data.get("success", True):
                return [dict(response.json_data)]
        return []


class SocialProviderAdapter(ResearchProviderAdapter):
    name = "social_provider"

    async def query(
        self,
        request: ResearchEntityRequest,
        network: ManagedNetworkClient,
    ) -> list[dict]:
        endpoint = os.getenv("SOCIAL_PROVIDER_ENDPOINT", "").strip()
        if endpoint:
            response = await network.request_json(
                "GET",
                endpoint,
                params={"q": request.entity_value},
            )
            if isinstance(response.json_data, list):
                return [dict(item) for item in response.json_data if isinstance(item, dict)]
        if request.entity_type == "EMAIL":
            lookup_value = request.entity_value.split("@", 1)[0]
        else:
            lookup_value = request.entity_value
        if request.entity_type == "USERNAME":
            github = await network.request_json("GET", f"https://api.github.com/users/{lookup_value}")
            if isinstance(github.json_data, dict) and github.status_code == 200:
                return [
                    {
                        "username": lookup_value,
                        "platform": "github",
                        "url": github.json_data.get("html_url", f"https://github.com/{lookup_value}"),
                        "followers": github.json_data.get("followers", 0),
                        "public_repos": github.json_data.get("public_repos", 0),
                    }
                ]
        if request.entity_type == "EMAIL":
            github = await network.request_json("GET", f"https://api.github.com/users/{lookup_value}")
            if isinstance(github.json_data, dict) and github.status_code == 200:
                return [
                    {
                        "email": request.entity_value,
                        "derived_username": lookup_value,
                        "platform": "github",
                        "url": github.json_data.get("html_url", f"https://github.com/{lookup_value}"),
                    }
                ]
        return []


class MultiSourceOrchestrator:
    """Runs provider collection concurrently while preserving provenance and resilience.

    Intelligence value:
    - Provider-level metrics reveal data coverage and failure hotspots.
    - Partial-failure tolerance keeps workflows productive during API instability.
    - Structured result contracts make evidence ingestion deterministic and auditable.
    """

    def __init__(
        self,
        providers: list[ResearchProviderAdapter] | None = None,
        provider_timeout_seconds: float | None = None,
    ):
        self.providers = providers or [
            BreachProviderAdapter(),
            InfrastructureProviderAdapter(),
            SocialProviderAdapter(),
        ]
        configured_timeout = provider_timeout_seconds
        if configured_timeout is None:
            configured_timeout = float(os.getenv("ORCHESTRATOR_PROVIDER_TIMEOUT_SECONDS", "12"))
        self.provider_timeout_seconds = max(float(configured_timeout), 0.1)

    async def research_entity(self, request: ResearchEntityRequest) -> ResearchEntityResult:
        if len(self.providers) < 3:
            raise ValueError("At least three providers are required for multi-source orchestration")

        async with ManagedNetworkClient() as network:
            tasks = [self._run_provider(provider, request, network) for provider in self.providers[:3]]
            outcomes = await asyncio.gather(*tasks, return_exceptions=False)

        provider_metrics: list[ProviderExecutionMetric] = []
        evidence_items: list[ResearchEvidenceItem] = []
        for metric, items in outcomes:
            provider_metrics.append(metric)
            evidence_items.extend(items)

        return ResearchEntityResult(
            request=request,
            providers=provider_metrics,
            evidence_items=evidence_items,
        )

    async def _run_provider(
        self,
        provider: ResearchProviderAdapter,
        request: ResearchEntityRequest,
        network: ManagedNetworkClient,
    ) -> tuple[ProviderExecutionMetric, list[ResearchEvidenceItem]]:
        started = time.monotonic()
        try:
            records = await asyncio.wait_for(
                provider.query(request, network),
                timeout=self.provider_timeout_seconds,
            )
            duration = time.monotonic() - started
            metric = ProviderExecutionMetric(
                provider_name=provider.name,
                duration_seconds=duration,
                success=True,
                result_count=len(records),
            )
            items = [
                ResearchEvidenceItem(provider_name=provider.name, data=record)
                for record in records
            ]
            return metric, items
        except asyncio.TimeoutError:
            duration = time.monotonic() - started
            metric = ProviderExecutionMetric(
                provider_name=provider.name,
                duration_seconds=duration,
                success=False,
                result_count=0,
                error_message=(
                    f"provider timed out after {self.provider_timeout_seconds:.1f}s"
                ),
            )
            return metric, []
        except Exception as exc:
            duration = time.monotonic() - started
            metric = ProviderExecutionMetric(
                provider_name=provider.name,
                duration_seconds=duration,
                success=False,
                result_count=0,
                error_message=str(exc),
            )
            return metric, []


def build_research_request(entity_value: str) -> ResearchEntityRequest:
    """Infer entity type from value and return a validated request model."""
    value = entity_value.strip()

    phone_candidate = re.sub(r"[^\d+]", "", value)
    phone_digits = re.sub(r"\D", "", phone_candidate)
    if len(phone_digits) >= 7 and any(ch.isdigit() for ch in value):
        return ResearchEntityRequest(entity_type="PHONE", entity_value=value)

    if "@" in value:
        return ResearchEntityRequest(entity_type="EMAIL", entity_value=value)

    ip_parts = value.split(".")
    if len(ip_parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts):
        return ResearchEntityRequest(entity_type="IP", entity_value=value)

    return ResearchEntityRequest(entity_type="USERNAME", entity_value=value)

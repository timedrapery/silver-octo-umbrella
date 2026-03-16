"""Tests for managed orchestration and typed research workflows."""

import asyncio
import time

import pytest

from app.services.intelligence_orchestrator import (
    MultiSourceOrchestrator,
    ResearchEntityRequest,
    ResearchProviderAdapter,
    build_research_request,
)
from app.services.managed_network_client import ManagedNetworkClient


class SlowProvider(ResearchProviderAdapter):
    def __init__(self, name: str, delay: float = 0.08):
        self.name = name
        self.delay = delay

    async def query(
        self,
        request: ResearchEntityRequest,
        network: ManagedNetworkClient,
    ) -> list[dict]:
        await asyncio.sleep(self.delay)
        return [{"entity": request.entity_value, "provider": self.name}]


class FailingProvider(ResearchProviderAdapter):
    name = "failing_provider"

    async def query(
        self,
        request: ResearchEntityRequest,
        network: ManagedNetworkClient,
    ) -> list[dict]:
        await asyncio.sleep(0.03)
        raise RuntimeError("provider down")


class HangingProvider(ResearchProviderAdapter):
    name = "hanging_provider"

    async def query(
        self,
        request: ResearchEntityRequest,
        network: ManagedNetworkClient,
    ) -> list[dict]:
        await asyncio.sleep(0.25)
        return [{"entity": request.entity_value}]


class TestResearchRequestTyping:
    def test_phone_request_validation(self):
        request = ResearchEntityRequest(entity_type="PHONE", entity_value="+1 415 555 0101")
        assert request.entity_type == "PHONE"

    def test_invalid_phone_rejected(self):
        with pytest.raises(Exception):
            ResearchEntityRequest(entity_type="PHONE", entity_value="12")

    def test_email_request_validation(self):
        request = ResearchEntityRequest(entity_type="EMAIL", entity_value="analyst@example.com")
        assert request.entity_type == "EMAIL"

    def test_invalid_email_rejected(self):
        with pytest.raises(Exception):
            ResearchEntityRequest(entity_type="EMAIL", entity_value="not-an-email")

    def test_request_builder_infers_types(self):
        assert build_research_request("+1 (415) 555-0101").entity_type == "PHONE"
        assert build_research_request("user@example.com").entity_type == "EMAIL"
        assert build_research_request("8.8.8.8").entity_type == "IP"
        assert build_research_request("octo_user").entity_type == "USERNAME"


class TestMultiSourceOrchestration:
    @pytest.mark.asyncio
    async def test_runs_three_providers_concurrently(self):
        orchestrator = MultiSourceOrchestrator(
            providers=[
                SlowProvider("p1", delay=0.1),
                SlowProvider("p2", delay=0.1),
                SlowProvider("p3", delay=0.1),
            ]
        )
        request = ResearchEntityRequest(entity_type="USERNAME", entity_value="alice")

        started = time.monotonic()
        result = await orchestrator.research_entity(request)
        elapsed = time.monotonic() - started

        assert len(result.providers) == 3
        assert len(result.evidence_items) == 3
        assert all(metric.success for metric in result.providers)
        # Concurrent execution should stay well below cumulative serial latency.
        assert elapsed < 1.2

    @pytest.mark.asyncio
    async def test_partial_failure_does_not_abort(self):
        orchestrator = MultiSourceOrchestrator(
            providers=[
                SlowProvider("ok_1", delay=0.05),
                FailingProvider(),
                SlowProvider("ok_2", delay=0.05),
            ]
        )
        request = ResearchEntityRequest(entity_type="IP", entity_value="1.1.1.1")

        result = await orchestrator.research_entity(request)

        assert len(result.providers) == 3
        failures = [metric for metric in result.providers if not metric.success]
        successes = [metric for metric in result.providers if metric.success]
        assert len(failures) == 1
        assert failures[0].provider_name == "failing_provider"
        assert "provider down" in failures[0].error_message
        assert len(successes) == 2
        assert len(result.evidence_items) == 2

    @pytest.mark.asyncio
    async def test_provider_timeout_isolated_from_other_results(self):
        orchestrator = MultiSourceOrchestrator(
            providers=[
                SlowProvider("ok_1", delay=0.02),
                HangingProvider(),
                SlowProvider("ok_2", delay=0.02),
            ],
            provider_timeout_seconds=0.05,
        )
        request = ResearchEntityRequest(entity_type="USERNAME", entity_value="alice")

        result = await orchestrator.research_entity(request)

        assert len(result.providers) == 3
        timeout_metric = next(metric for metric in result.providers if metric.provider_name == "hanging_provider")
        assert timeout_metric.success is False
        assert "timed out" in timeout_metric.error_message
        assert len(result.evidence_items) == 2

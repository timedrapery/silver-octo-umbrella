import asyncio
import logging

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, InvestigationPreset, Target, TargetType

logger = logging.getLogger(__name__)

PRESET_ADAPTERS: dict[InvestigationPreset, list[str]] = {
    InvestigationPreset.DOMAIN_INTELLIGENCE: ["dns", "cert", "http", "subdomain"],
    InvestigationPreset.ORGANIZATION_FOOTPRINT: ["dns", "cert", "http", "subdomain", "social"],
    InvestigationPreset.USERNAME_INVESTIGATION: ["social"],
    InvestigationPreset.DOCUMENT_METADATA_AUDIT: ["metadata"],
    InvestigationPreset.INFRASTRUCTURE_MAPPING: ["dns", "http", "subdomain"],
}


class InvestigationService:
    def __init__(self, adapters: list[BaseAdapter]):
        self._adapters: dict[str, BaseAdapter] = {a.name: a for a in adapters}

    async def run_adapters(
        self, target: Target, adapter_names: list[str] | None = None
    ) -> list[Finding]:
        candidates = list(self._adapters.values())
        if adapter_names is not None:
            candidates = [a for a in candidates if a.name in adapter_names]

        active = [a for a in candidates if a.can_handle(target)]
        tasks = [a.run(target) for a in active]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        findings: list[Finding] = []
        for adapter, result in zip(active, results):
            if isinstance(result, BaseException):
                logger.warning("Adapter %r failed: %s", adapter.name, result)
            else:
                findings.extend(result)
        return findings

    async def run_preset(self, target: Target, preset: InvestigationPreset) -> list[Finding]:
        adapter_names = PRESET_ADAPTERS.get(preset, [])
        return await self.run_adapters(target, adapter_names=adapter_names)

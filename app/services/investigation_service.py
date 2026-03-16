import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.adapters.base import BaseAdapter
from app.models.case import AdapterRun, AdapterRunStatus, Finding, InvestigationPreset, Target

logger = logging.getLogger(__name__)


@dataclass
class InvestigationExecution:
    findings: list[Finding]
    adapter_runs: list[AdapterRun]

    @property
    def failed_runs(self) -> int:
        return sum(1 for run in self.adapter_runs if run.status == AdapterRunStatus.FAILED)

    @property
    def successful_runs(self) -> int:
        return sum(1 for run in self.adapter_runs if run.status == AdapterRunStatus.COMPLETE)

PRESET_ADAPTERS: dict[InvestigationPreset, list[str]] = {
    InvestigationPreset.DOMAIN_INTELLIGENCE: ["dns", "cert", "http", "subdomain"],
    InvestigationPreset.ORGANIZATION_FOOTPRINT: ["dns", "cert", "http", "subdomain", "social"],
    InvestigationPreset.USERNAME_INVESTIGATION: ["social"],
    InvestigationPreset.DOCUMENT_METADATA_AUDIT: ["metadata"],
    InvestigationPreset.INFRASTRUCTURE_MAPPING: ["dns", "http", "subdomain"],
}


class InvestigationService:
    def __init__(self, adapters: list[BaseAdapter], adapter_timeout_seconds: float | None = None):
        self._adapters: dict[str, BaseAdapter] = {a.name: a for a in adapters}
        configured_timeout = adapter_timeout_seconds
        if configured_timeout is None:
            configured_timeout = float(os.getenv("INVESTIGATION_ADAPTER_TIMEOUT_SECONDS", "20"))
        self.adapter_timeout_seconds = max(float(configured_timeout), 0.1)

    def get_active_adapters(
        self, target: Target, adapter_names: list[str] | None = None
    ) -> list[BaseAdapter]:
        """Return adapters that can handle this target, optionally filtered by name."""
        candidates = list(self._adapters.values())
        if adapter_names is not None:
            candidates = [a for a in candidates if a.name in adapter_names]
        return [a for a in candidates if a.can_handle(target)]

    async def execute_adapter(
        self,
        adapter: BaseAdapter,
        target: Target,
        case_id: str | None = None,
    ) -> tuple[list[Finding], AdapterRun]:
        started_at = datetime.now(timezone.utc)
        t0 = time.monotonic()
        findings: list[Finding] = []
        status = AdapterRunStatus.COMPLETE
        error_message = ""

        try:
            findings = await asyncio.wait_for(
                adapter.run(target),
                timeout=self.adapter_timeout_seconds,
            )
        except asyncio.TimeoutError:
            status = AdapterRunStatus.FAILED
            error_message = (
                f"adapter timed out after {self.adapter_timeout_seconds:.1f}s"
            )
            logger.warning("Adapter %r timed out after %.1fs", adapter.name, self.adapter_timeout_seconds)
        except Exception as exc:
            status = AdapterRunStatus.FAILED
            error_message = str(exc)
            logger.warning("Adapter %r failed: %s", adapter.name, exc)

        completed_at = datetime.now(timezone.utc)
        duration_seconds = time.monotonic() - t0
        run = AdapterRun(
            case_id=case_id or "",
            target_id=target.id,
            adapter_name=adapter.name,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            finding_count=len(findings),
            duration_seconds=duration_seconds,
            error_message=error_message,
        )

        for finding in findings:
            finding.adapter_run_id = run.id

        return findings, run

    async def execute_investigation(
        self,
        target: Target,
        adapter_names: list[str] | None = None,
        case_id: str | None = None,
    ) -> InvestigationExecution:
        active = self.get_active_adapters(target, adapter_names)
        findings: list[Finding] = []
        runs: list[AdapterRun] = []

        for adapter in active:
            adapter_findings, adapter_run = await self.execute_adapter(
                adapter,
                target,
                case_id=case_id,
            )
            findings.extend(adapter_findings)
            runs.append(adapter_run)

        return InvestigationExecution(findings=findings, adapter_runs=runs)

    async def run_adapters(
        self, target: Target, adapter_names: list[str] | None = None
    ) -> list[Finding]:
        """Run all compatible adapters and collect findings."""
        execution = await self.execute_investigation(target, adapter_names=adapter_names)
        return execution.findings

    async def run_preset(self, target: Target, preset: InvestigationPreset) -> list[Finding]:
        adapter_names = PRESET_ADAPTERS.get(preset, [])
        return await self.run_adapters(target, adapter_names=adapter_names)

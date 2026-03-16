import asyncio
import logging
import time

from PySide6.QtCore import QThread, Signal

from app.models.case import Finding, InvestigationPreset, Target
from app.services.investigation_service import InvestigationService, PRESET_ADAPTERS

logger = logging.getLogger(__name__)


class InvestigationWorker(QThread):
    finding_found = Signal(object)   # Finding
    progress = Signal(int, str)      # (percent, message)
    finished = Signal(list)          # list[Finding]
    error = Signal(str)

    def __init__(
        self,
        investigation_service: InvestigationService,
        target: Target,
        preset: InvestigationPreset | None = None,
        adapter_names: list[str] | None = None,
    ):
        super().__init__()
        self.investigation_service = investigation_service
        self.target = target
        self.preset = preset
        self.adapter_names = adapter_names

    def run(self) -> None:
        try:
            asyncio.run(self._run_investigation())
        except Exception as exc:
            self.error.emit(str(exc))

    async def _run_investigation(self) -> None:
        self.progress.emit(5, "Resolving adapters…")

        # Determine which adapter names to use
        if self.preset is not None:
            effective_names = PRESET_ADAPTERS.get(self.preset, [])
        else:
            effective_names = self.adapter_names

        adapters = self.investigation_service.get_active_adapters(
            self.target, effective_names
        )

        if not adapters:
            self.progress.emit(100, "No adapters match this target type.")
            self.finished.emit([])
            return

        total = len(adapters)
        all_findings: list[Finding] = []

        for idx, adapter in enumerate(adapters):
            base_pct = 10 + int(idx / total * 85)
            self.progress.emit(base_pct, f"Running {adapter.name}…")
            t0 = time.monotonic()
            try:
                findings = await adapter.run(self.target)
                duration = time.monotonic() - t0
                all_findings.extend(findings)
                for f in findings:
                    self.finding_found.emit(f)
                done_pct = 10 + int((idx + 1) / total * 85)
                self.progress.emit(
                    done_pct,
                    f"{adapter.name}: {len(findings)} finding(s) in {duration:.1f}s",
                )
            except Exception as exc:
                duration = time.monotonic() - t0
                logger.warning("Adapter %r failed after %.1fs: %s", adapter.name, duration, exc)
                done_pct = 10 + int((idx + 1) / total * 85)
                self.progress.emit(done_pct, f"{adapter.name}: failed — {exc}")

        self.progress.emit(
            100, f"Done — {len(all_findings)} finding(s) from {total} adapter(s)"
        )
        self.finished.emit(all_findings)

import asyncio

from PySide6.QtCore import QThread, Signal

from app.models.case import Finding, InvestigationPreset, Target
from app.services.investigation_service import InvestigationService


class InvestigationWorker(QThread):
    finding_found = Signal(object)
    progress = Signal(int, str)
    finished = Signal(list)
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

    def run(self):
        try:
            asyncio.run(self._run_investigation())
        except Exception as exc:
            self.error.emit(str(exc))

    async def _run_investigation(self):
        self.progress.emit(10, "Starting investigation...")
        try:
            if self.preset is not None:
                self.progress.emit(30, f"Running preset: {self.preset.value}")
                findings = await self.investigation_service.run_preset(self.target, self.preset)
            else:
                self.progress.emit(30, "Running selected adapters...")
                findings = await self.investigation_service.run_adapters(
                    self.target, adapter_names=self.adapter_names
                )

            total = len(findings)
            for i, finding in enumerate(findings):
                self.finding_found.emit(finding)
                pct = 30 + int((i + 1) / max(total, 1) * 65)
                self.progress.emit(pct, f"Found: {finding.title}")

            self.progress.emit(100, f"Complete — {total} findings")
            self.finished.emit(findings)
        except Exception as exc:
            self.error.emit(str(exc))

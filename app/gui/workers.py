import asyncio

from PySide6.QtCore import QThread, Signal

from app.models.case import AdapterRunStatus, Finding, InvestigationPreset, Target
from app.services.investigation_service import InvestigationService, PRESET_ADAPTERS


class InvestigationWorker(QThread):
    finding_found = Signal(object)   # Finding
    progress = Signal(int, str)      # (percent, message)
    finished = Signal(object)        # dict[str, list]
    error = Signal(str)

    def __init__(
        self,
        investigation_service: InvestigationService,
        target: Target,
        preset: InvestigationPreset | None = None,
        adapter_names: list[str] | None = None,
        case_id: str | None = None,
    ):
        super().__init__()
        self.investigation_service = investigation_service
        self.target = target
        self.preset = preset
        self.adapter_names = adapter_names
        self.case_id = case_id

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
            self.finished.emit({"findings": [], "adapter_runs": []})
            return

        total = len(adapters)
        all_findings: list[Finding] = []
        all_runs = []

        for idx, adapter in enumerate(adapters):
            base_pct = 10 + int(idx / total * 85)
            self.progress.emit(base_pct, f"Running {adapter.name}…")
            findings, run = await self.investigation_service.execute_adapter(
                adapter,
                self.target,
                case_id=self.case_id,
            )
            all_findings.extend(findings)
            all_runs.append(run)

            for finding in findings:
                self.finding_found.emit(finding)

            done_pct = 10 + int((idx + 1) / total * 85)
            if run.status == AdapterRunStatus.FAILED:
                self.progress.emit(done_pct, f"{adapter.name}: failed — {run.error_message}")
            else:
                self.progress.emit(
                    done_pct,
                    f"{adapter.name}: {len(findings)} finding(s) in {run.duration_seconds:.1f}s",
                )

        self.progress.emit(
            100, f"Done — {len(all_findings)} finding(s) from {total} adapter(s)"
        )
        self.finished.emit({"findings": all_findings, "adapter_runs": all_runs})

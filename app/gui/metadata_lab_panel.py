import asyncio
import time
from datetime import datetime, timezone

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.adapters.metadata_adapter import MetadataAdapter
from app.models.case import AdapterRun, AdapterRunStatus, Case, Target, TargetType
from app.services.case_service import CaseService
from app.services.metadata_analysis_service import MetadataAnalysisService


class MetadataExtractionWorker(QThread):
    finished = Signal(object, object, object)
    error = Signal(str)

    def __init__(self, adapter: MetadataAdapter, target: Target):
        super().__init__()
        self.adapter = adapter
        self.target = target

    def run(self) -> None:
        try:
            started = time.monotonic()
            started_at = datetime.now(timezone.utc)
            findings = asyncio.run(self.adapter.run(self.target))
            completed_at = datetime.now(timezone.utc)
            run = AdapterRun(
                case_id="",
                target_id=self.target.id,
                adapter_name=self.adapter.name,
                status=AdapterRunStatus.COMPLETE,
                started_at=started_at,
                completed_at=completed_at,
                finding_count=len(findings),
                duration_seconds=time.monotonic() - started,
                error_message="",
            )
            self.finished.emit(self.target, findings, run)
        except Exception as exc:
            self.error.emit(str(exc))


class MetadataLabPanel(QWidget):
    status_changed = Signal(str)
    case_updated = Signal(object)

    def __init__(self, case_service: CaseService, parent=None):
        super().__init__(parent)
        self.case_service = case_service
        self.current_case: Case | None = None
        self.adapter = MetadataAdapter()
        self.analysis_service = MetadataAnalysisService()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        request_group = QGroupBox("Metadata Lab")
        request_layout = QGridLayout(request_group)

        self.target_type_combo = QComboBox()
        self.target_type_combo.addItem("Document", TargetType.DOCUMENT)
        self.target_type_combo.addItem("URL", TargetType.URL)

        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Enter document path or URL")

        self.extract_btn = QPushButton("Extract Metadata")
        self.extract_btn.clicked.connect(self._on_extract)

        self.summary_label = QLabel("Ready")
        self.summary_label.setStyleSheet("padding: 4px 8px; border: 1px solid #444; border-radius: 4px;")

        request_layout.addWidget(QLabel("Source Type"), 0, 0)
        request_layout.addWidget(self.target_type_combo, 0, 1)
        request_layout.addWidget(QLabel("Source"), 0, 2)
        request_layout.addWidget(self.target_input, 0, 3)
        request_layout.addWidget(self.extract_btn, 0, 4)
        request_layout.addWidget(self.summary_label, 1, 0, 1, 5)

        layout.addWidget(request_group)

        self.findings_table = QTableWidget(0, 4)
        self.findings_table.setHorizontalHeaderLabels(["Title", "Type", "Severity", "Source"])
        self.findings_table.horizontalHeader().setStretchLastSection(True)
        self.findings_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.findings_table)

        analysis_group = QGroupBox("Investigator View")
        analysis_layout = QHBoxLayout(analysis_group)

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setPlaceholderText(
            "Run extraction to view source context, identity/timeline/geo signals, risk flags, and IOCs."
        )

        self.raw_data_text = QTextEdit()
        self.raw_data_text.setReadOnly(True)
        self.raw_data_text.setPlaceholderText("Raw metadata payloads")

        analysis_layout.addWidget(self.analysis_text, 2)
        analysis_layout.addWidget(self.raw_data_text, 1)
        layout.addWidget(analysis_group)

    def load_case(self, case: Case) -> None:
        self.current_case = case
        metadata_findings = [f for f in case.findings if f.adapter_name == "metadata"]
        self._render_findings(metadata_findings)
        self.summary_label.setText(f"Case metadata findings: {len(metadata_findings)}")

    def _on_extract(self) -> None:
        if self.current_case is None:
            self.status_changed.emit("Select a case before using Metadata Lab")
            return

        source = self.target_input.text().strip()
        if not source:
            self.status_changed.emit("Enter a document path or URL")
            return

        target = Target(type=self.target_type_combo.currentData(), value=source)
        self.extract_btn.setEnabled(False)
        self.status_changed.emit("Running metadata extraction...")

        self.worker = MetadataExtractionWorker(self.adapter, target)
        self.worker.finished.connect(self._on_extract_finished)
        self.worker.error.connect(self._on_extract_error)
        self.worker.start()

    def _on_extract_finished(self, target: Target, findings: list, run: AdapterRun) -> None:
        self.extract_btn.setEnabled(True)
        if self.current_case is None:
            self.status_changed.emit("Extraction completed but no active case is loaded")
            return

        added, skipped = self.case_service.add_findings_batch(self.current_case.id, findings)
        run.case_id = self.current_case.id
        self.case_service.save_adapter_runs(self.current_case.id, [run])

        refreshed = self.case_service.get_case(self.current_case.id)
        self.current_case = refreshed
        metadata_findings = [f for f in refreshed.findings if f.adapter_name == "metadata"]
        self._render_findings(metadata_findings)

        analysis = self.analysis_service.summarize(added if added else findings)
        self.analysis_text.setPlainText(self.analysis_service.format_analysis(analysis))

        raw_chunks = []
        source_findings = added if added else findings
        for finding in source_findings:
            raw_chunks.append(f"{finding.title}\n{finding.data}\n")
        self.raw_data_text.setPlainText("\n".join(raw_chunks))

        self.summary_label.setText(
            f"Extraction complete: {len(findings)} findings ({len(added)} added, {skipped} duplicate)"
        )
        self.status_changed.emit("Metadata extraction complete")
        self.case_updated.emit(refreshed)

    def _on_extract_error(self, message: str) -> None:
        self.extract_btn.setEnabled(True)
        self.status_changed.emit(f"Metadata extraction failed: {message}")
        self.summary_label.setText(f"Error: {message}")

    def _render_findings(self, findings: list) -> None:
        self.findings_table.setRowCount(0)
        for finding in findings:
            row = self.findings_table.rowCount()
            self.findings_table.insertRow(row)
            self.findings_table.setItem(row, 0, QTableWidgetItem(finding.title))
            self.findings_table.setItem(row, 1, QTableWidgetItem(finding.finding_type.value))
            self.findings_table.setItem(row, 2, QTableWidgetItem(finding.severity.value))
            source = finding.source_name or finding.source_url or "-"
            self.findings_table.setItem(row, 3, QTableWidgetItem(source))

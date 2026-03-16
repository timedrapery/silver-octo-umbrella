import asyncio

from PySide6.QtCore import QThread, Qt, Signal
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

from app.models.case import Case, SourceReliability
from app.services.case_service import CaseService
from app.services.entity_research_service import EntityResearchService, EntityResearchSession, ReviewResultItem


class EntityResearchWorker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        service: EntityResearchService,
        case_id: str,
        entity_value: str,
        entity_type: str | None,
    ):
        super().__init__()
        self.service = service
        self.case_id = case_id
        self.entity_value = entity_value
        self.entity_type = entity_type

    def run(self) -> None:
        try:
            result = asyncio.run(
                self.service.research_entity(
                    self.case_id,
                    self.entity_value,
                    self.entity_type,
                )
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class EntityResearchPanel(QWidget):
    status_changed = Signal(str)
    case_updated = Signal(object)

    def __init__(
        self,
        case_service: CaseService,
        entity_research_service: EntityResearchService,
        parent=None,
    ):
        super().__init__(parent)
        self.case_service = case_service
        self.entity_research_service = entity_research_service
        self.current_case: Case | None = None
        self.current_session: EntityResearchSession | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        summary_row = QHBoxLayout()
        self.entity_count_label = QLabel("Researched Entities: 0")
        self.evidence_count_label = QLabel("Research Evidence: 0")
        self.last_research_label = QLabel("Last Research: -")
        for label in [
            self.entity_count_label,
            self.evidence_count_label,
            self.last_research_label,
        ]:
            label.setStyleSheet("padding: 4px 8px; border: 1px solid #444; border-radius: 4px;")
            summary_row.addWidget(label)
        summary_row.addStretch()
        layout.addLayout(summary_row)

        request_group = QGroupBox("Entity Research Request")
        request_layout = QGridLayout(request_group)

        self.entity_type_combo = QComboBox()
        self.entity_type_combo.addItem("Auto", None)
        self.entity_type_combo.addItem("PHONE", "PHONE")
        self.entity_type_combo.addItem("EMAIL", "EMAIL")
        self.entity_type_combo.addItem("IP", "IP")
        self.entity_type_combo.addItem("USERNAME", "USERNAME")

        self.entity_input = QLineEdit()
        self.entity_input.setPlaceholderText("Enter phone, email, IP, or username")

        self.research_btn = QPushButton("Research Entity")
        self.research_btn.clicked.connect(self._on_research)

        request_layout.addWidget(QLabel("Entity Type"), 0, 0)
        request_layout.addWidget(self.entity_type_combo, 0, 1)
        request_layout.addWidget(QLabel("Entity Value"), 0, 2)
        request_layout.addWidget(self.entity_input, 0, 3)
        request_layout.addWidget(self.research_btn, 0, 4)

        quick_row = QHBoxLayout()
        self.phone_pivot_btn = QPushButton("Reverse Phone Lookup")
        self.email_pivot_btn = QPushButton("Email Pivot")
        self.username_pivot_btn = QPushButton("Username Pivot")
        self.phone_pivot_btn.clicked.connect(lambda: self._select_quick_pivot("PHONE"))
        self.email_pivot_btn.clicked.connect(lambda: self._select_quick_pivot("EMAIL"))
        self.username_pivot_btn.clicked.connect(lambda: self._select_quick_pivot("USERNAME"))
        quick_row.addWidget(self.phone_pivot_btn)
        quick_row.addWidget(self.email_pivot_btn)
        quick_row.addWidget(self.username_pivot_btn)
        quick_row.addStretch()
        request_layout.addLayout(quick_row, 1, 0, 1, 5)

        helper = QLabel(
            "Tip: Start with phone or email pivots for high-value lead expansion, then promote reliable results to evidence."
        )
        helper.setStyleSheet("color: #9ca3af; font-size: 12px;")
        request_layout.addWidget(helper, 2, 0, 1, 5)
        layout.addWidget(request_group)

        provider_group = QGroupBox("Provider Execution Summary")
        provider_layout = QVBoxLayout(provider_group)
        self.provider_table = QTableWidget(0, 5)
        self.provider_table.setHorizontalHeaderLabels(["Provider", "Success", "Results", "Duration", "Error"])
        self.provider_table.horizontalHeader().setStretchLastSection(True)
        self.provider_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        provider_layout.addWidget(self.provider_table)
        layout.addWidget(provider_group)

        review_group = QGroupBox("Structured Result Review")
        review_layout = QVBoxLayout(review_group)
        self.results_table = QTableWidget(0, 7)
        self.results_table.setHorizontalHeaderLabels(
            ["Promote", "Provider", "Summary", "Key Fields", "Occurred At", "Provenance", "Status"]
        )
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        review_layout.addWidget(self.results_table)
        layout.addWidget(review_group)

        promote_group = QGroupBox("Evidence Promotion")
        promote_layout = QVBoxLayout(promote_group)

        control_row = QHBoxLayout()
        self.reliability_combo = QComboBox()
        for value in SourceReliability:
            self.reliability_combo.addItem(value.value, value)
        self.reliability_combo.setCurrentText(SourceReliability.MEDIUM.value)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        self.clear_selection_btn = QPushButton("Clear Selection")
        self.clear_selection_btn.clicked.connect(self._clear_selection)
        self.promote_btn = QPushButton("Promote Selected")
        self.promote_btn.clicked.connect(self._promote_selected)

        control_row.addWidget(QLabel("Reliability"))
        control_row.addWidget(self.reliability_combo)
        control_row.addWidget(self.select_all_btn)
        control_row.addWidget(self.clear_selection_btn)
        control_row.addWidget(self.promote_btn)
        control_row.addStretch()

        self.analyst_note_input = QTextEdit()
        self.analyst_note_input.setPlaceholderText(
            "Optional analyst note attached to promoted evidence (e.g., validation context)."
        )
        self.analyst_note_input.setMaximumHeight(70)

        promote_layout.addLayout(control_row)
        promote_layout.addWidget(self.analyst_note_input)
        layout.addWidget(promote_group)

    def load_case(self, case: Case) -> None:
        self.current_case = case
        self.current_session = None
        self.provider_table.setRowCount(0)
        self.results_table.setRowCount(0)
        self._refresh_summary(case.id)

    def _refresh_summary(self, case_id: str) -> None:
        summary = self.case_service.get_case_entity_activity_summary(case_id)
        self.entity_count_label.setText(f"Researched Entities: {summary.total_entities}")
        self.evidence_count_label.setText(f"Research Evidence: {summary.research_evidence_total}")
        last = summary.last_research_at.strftime("%Y-%m-%d %H:%M") if summary.last_research_at else "-"
        self.last_research_label.setText(f"Last Research: {last}")

    def _on_research(self) -> None:
        if self.current_case is None:
            self.status_changed.emit("Select a case before running entity research")
            return

        entity_value = self.entity_input.text().strip()
        if not entity_value:
            self.status_changed.emit("Enter an entity value to research")
            return

        self.research_btn.setEnabled(False)
        self.status_changed.emit("Running entity research across providers...")

        self.research_worker = EntityResearchWorker(
            service=self.entity_research_service,
            case_id=self.current_case.id,
            entity_value=entity_value,
            entity_type=self.entity_type_combo.currentData(),
        )
        self.research_worker.finished.connect(self._on_research_finished)
        self.research_worker.error.connect(self._on_research_error)
        self.research_worker.start()

    def _on_research_finished(self, session: EntityResearchSession) -> None:
        self.research_btn.setEnabled(True)
        self.current_session = session

        self.provider_table.setRowCount(0)
        for metric in session.provider_metrics:
            row = self.provider_table.rowCount()
            self.provider_table.insertRow(row)
            self.provider_table.setItem(row, 0, QTableWidgetItem(metric.provider_name))
            self.provider_table.setItem(row, 1, QTableWidgetItem("yes" if metric.success else "no"))
            self.provider_table.setItem(row, 2, QTableWidgetItem(str(metric.result_count)))
            self.provider_table.setItem(row, 3, QTableWidgetItem(f"{metric.duration_seconds:.2f}s"))
            self.provider_table.setItem(row, 4, QTableWidgetItem(metric.error_message or "-"))

        self.results_table.setRowCount(0)
        for idx, item in enumerate(session.results):
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)

            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            check_item.setCheckState(Qt.CheckState.Unchecked)
            check_item.setData(Qt.ItemDataRole.UserRole, idx)
            self.results_table.setItem(row, 0, check_item)

            key_fields = ", ".join(f"{k}={v}" for k, v in item.key_fields.items()) or "-"
            status = "Already promoted" if item.promoted else "New"

            self.results_table.setItem(row, 1, QTableWidgetItem(item.provider_name))
            self.results_table.setItem(row, 2, QTableWidgetItem(item.summary))
            self.results_table.setItem(row, 3, QTableWidgetItem(key_fields))
            self.results_table.setItem(row, 4, QTableWidgetItem(item.occurred_at or "-"))
            self.results_table.setItem(row, 5, QTableWidgetItem(item.provenance or "-"))
            self.results_table.setItem(row, 6, QTableWidgetItem(status))

        msg = (
            f"Research complete: {session.total_results} result(s), "
            f"{session.promoted_results} already promoted"
        )
        if session.partial_failure:
            msg += " (partial provider failures detected)"
        self.status_changed.emit(msg)
        self._refresh_summary(session.case_id)

    def _on_research_error(self, message: str) -> None:
        self.research_btn.setEnabled(True)
        self.status_changed.emit(f"Entity research failed: {message}")

    def _select_quick_pivot(self, entity_type: str) -> None:
        idx = self.entity_type_combo.findData(entity_type)
        if idx >= 0:
            self.entity_type_combo.setCurrentIndex(idx)
        if entity_type == "PHONE":
            self.entity_input.setPlaceholderText("Enter phone for reverse lookup (example: +1 415 555 0101)")
        elif entity_type == "EMAIL":
            self.entity_input.setPlaceholderText("Enter email for breach/profile pivot")
        elif entity_type == "USERNAME":
            self.entity_input.setPlaceholderText("Enter username for cross-platform pivot")

    def seed_pivot(self, entity_type: str, value: str) -> None:
        """Prefill a pivot request so external workspace actions can reduce context switching."""
        self._select_quick_pivot(entity_type)
        self.entity_input.setText(value)

    def _selected_results(self) -> list[ReviewResultItem]:
        if self.current_session is None:
            return []

        selected: list[ReviewResultItem] = []
        for row in range(self.results_table.rowCount()):
            item = self.results_table.item(row, 0)
            if item is None or item.checkState() != Qt.CheckState.Checked:
                continue
            idx = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(idx, int) and 0 <= idx < len(self.current_session.results):
                selected.append(self.current_session.results[idx])
        return selected

    def _promote_selected(self) -> None:
        if self.current_case is None or self.current_session is None:
            self.status_changed.emit("Run research before promoting evidence")
            return

        selected = self._selected_results()
        if not selected:
            self.status_changed.emit("Select at least one review item to promote")
            return

        reliability = self.reliability_combo.currentData()
        note = self.analyst_note_input.toPlainText().strip()
        outcome = self.entity_research_service.promote_results(
            case_id=self.current_case.id,
            entity_id=self.current_session.entity.id,
            selected_results=selected,
            source_reliability=reliability,
            analyst_note=note,
        )

        self.status_changed.emit(
            f"Promotion complete: {outcome.created} created, {outcome.skipped_duplicates} duplicates skipped"
        )

        refreshed_case = self.case_service.get_case(self.current_case.id)
        self.load_case(refreshed_case)
        self.case_updated.emit(refreshed_case)

    def _select_all(self) -> None:
        for row in range(self.results_table.rowCount()):
            item = self.results_table.item(row, 0)
            if item is not None:
                item.setCheckState(Qt.CheckState.Checked)

    def _clear_selection(self) -> None:
        for row in range(self.results_table.rowCount()):
            item = self.results_table.item(row, 0)
            if item is not None:
                item.setCheckState(Qt.CheckState.Unchecked)

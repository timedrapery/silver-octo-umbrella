import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.case import Case, Finding, FindingReviewState, FindingSortBy, Severity
from app.services.findings_service import FindingFilter, FindingsService
from app.models.case import FindingDecisionState

SEVERITY_COLORS = {
    "INFO": "#6b7280",
    "LOW": "#3b82f6",
    "MEDIUM": "#f59e0b",
    "HIGH": "#ef4444",
    "CRITICAL": "#dc2626",
}

REVIEW_STATE_COLORS = {
    "NEW": "#6366f1",
    "REVIEWED": "#22c55e",
    "FLAGGED": "#ef4444",
    "DISMISSED": "#94a3b8",
}


class FindingsPanel(QWidget):
    triage_update_requested = Signal(str, str, str)  # finding_id, review_state, analyst_note
    decision_update_requested = Signal(str, str, float, str)  # finding_id, decision_state, confidence, rationale
    correlate_requested = Signal(str, str, str, float)  # finding_id, evidence_id, rationale, confidence
    promote_requested = Signal(str, str, float)  # finding_id, rationale, confidence
    attachment_requested = Signal(str, str, str)  # evidence_id, file_path, provenance_note
    public_media_capture_requested = Signal(
        str,
        str,
        str,
        str,
        str,
        str,
        str,
    )  # finding_id, evidence_id, url, media_title, media_type, provenance_note, screenshot_path

    def __init__(self, findings_service: FindingsService, parent=None):
        super().__init__(parent)
        self.findings_service = findings_service
        self.case: Case | None = None
        self.findings: list[Finding] = []
        self.filtered_findings: list[Finding] = []
        self.target_labels: dict[str, str] = {}
        self.evidence_labels: dict[str, str] = {}
        self._selected_finding_id: str | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        summary_row = QGridLayout()
        self.summary_labels = {
            "total": QLabel("Total: 0"),
            "new": QLabel("New: 0"),
            "reviewed": QLabel("Reviewed: 0"),
            "flagged": QLabel("Flagged: 0"),
            "dismissed": QLabel("Dismissed: 0"),
            "high_unreviewed": QLabel("High/Critical New: 0"),
        }
        for idx, key in enumerate(
            ["total", "new", "reviewed", "flagged", "dismissed", "high_unreviewed"]
        ):
            label = self.summary_labels[key]
            label.setStyleSheet("padding: 4px 8px; border: 1px solid #444; border-radius: 4px;")
            summary_row.addWidget(label, 0, idx)
        layout.addLayout(summary_row)

        filter_row = QHBoxLayout()

        self.review_filter = QComboBox()
        self.review_filter.addItem("All States", None)
        for state in FindingReviewState:
            self.review_filter.addItem(state.value, state.value)
        self.review_filter.currentIndexChanged.connect(self._apply_filters)

        self.severity_filter = QComboBox()
        self.severity_filter.addItem("All Severities", None)
        for severity in Severity:
            self.severity_filter.addItem(severity.value, severity.value)
        self.severity_filter.currentIndexChanged.connect(self._apply_filters)

        self.adapter_filter = QComboBox()
        self.adapter_filter.addItem("All Adapters", None)
        self.adapter_filter.currentIndexChanged.connect(self._apply_filters)

        self.target_filter = QComboBox()
        self.target_filter.addItem("All Targets", None)
        self.target_filter.currentIndexChanged.connect(self._apply_filters)

        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types", None)
        self.type_filter.currentIndexChanged.connect(self._apply_filters)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Newest", FindingSortBy.NEWEST.value)
        self.sort_combo.addItem("Oldest", FindingSortBy.OLDEST.value)
        self.sort_combo.addItem("Severity", FindingSortBy.SEVERITY.value)
        self.sort_combo.addItem("Adapter", FindingSortBy.ADAPTER.value)
        self.sort_combo.addItem("Target", FindingSortBy.TARGET.value)
        self.sort_combo.currentIndexChanged.connect(self._apply_filters)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search title, description, source, note...")
        self.search_input.textChanged.connect(self._apply_filters)

        filter_row.addWidget(QLabel("State"))
        filter_row.addWidget(self.review_filter)
        filter_row.addWidget(QLabel("Severity"))
        filter_row.addWidget(self.severity_filter)
        filter_row.addWidget(QLabel("Adapter"))
        filter_row.addWidget(self.adapter_filter)
        filter_row.addWidget(QLabel("Target"))
        filter_row.addWidget(self.target_filter)
        filter_row.addWidget(QLabel("Type"))
        filter_row.addWidget(self.type_filter)
        filter_row.addWidget(QLabel("Sort"))
        filter_row.addWidget(self.sort_combo)
        filter_row.addWidget(self.search_input, 1)

        layout.addLayout(filter_row)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Severity",
                "State",
                "Type",
                "Title",
                "Adapter",
                "Target",
                "Collected",
                "Source",
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.currentRowChanged.connect(self._on_row_selected)
        splitter.addWidget(self.table)

        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)

        triage_actions = QHBoxLayout()
        self.new_btn = QPushButton("Mark New")
        self.reviewed_btn = QPushButton("Mark Reviewed")
        self.flag_btn = QPushButton("Flag")
        self.dismiss_btn = QPushButton("Dismiss")

        self.new_btn.clicked.connect(lambda: self._request_triage_update(FindingReviewState.NEW))
        self.reviewed_btn.clicked.connect(
            lambda: self._request_triage_update(FindingReviewState.REVIEWED)
        )
        self.flag_btn.clicked.connect(lambda: self._request_triage_update(FindingReviewState.FLAGGED))
        self.dismiss_btn.clicked.connect(
            lambda: self._request_triage_update(FindingReviewState.DISMISSED)
        )

        triage_actions.addWidget(self.new_btn)
        triage_actions.addWidget(self.reviewed_btn)
        triage_actions.addWidget(self.flag_btn)
        triage_actions.addWidget(self.dismiss_btn)
        triage_actions.addStretch()
        detail_layout.addLayout(triage_actions)

        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setMinimumHeight(180)
        detail_layout.addWidget(self.detail_view)

        decision_row = QHBoxLayout()
        self.decision_state_combo = QComboBox()
        for state in FindingDecisionState:
            self.decision_state_combo.addItem(state.value, state)
        self.decision_confidence_input = QLineEdit()
        self.decision_confidence_input.setPlaceholderText("Decision confidence (0.0 - 1.0)")
        self.decision_rationale_input = QLineEdit()
        self.decision_rationale_input.setPlaceholderText("Why this decision fits the current support")
        self.save_decision_btn = QPushButton("Save Decision")
        self.save_decision_btn.clicked.connect(self._save_decision)
        decision_row.addWidget(QLabel("Decision"))
        decision_row.addWidget(self.decision_state_combo)
        decision_row.addWidget(self.decision_confidence_input)
        decision_row.addWidget(self.decision_rationale_input, 1)
        decision_row.addWidget(self.save_decision_btn)
        detail_layout.addLayout(decision_row)

        convergence_hint = QLabel(
            "Correlation links a finding to supporting evidence. Promotion turns a finding into durable evidence."
        )
        convergence_hint.setStyleSheet("color: #9ca3af; font-size: 12px;")
        detail_layout.addWidget(convergence_hint)

        correlation_row = QHBoxLayout()
        self.evidence_combo = QComboBox()
        self.evidence_combo.addItem("Select supporting evidence", None)
        self.correlation_rationale_input = QLineEdit()
        self.correlation_rationale_input.setPlaceholderText("Why this evidence supports the finding")
        self.correlation_confidence_input = QLineEdit()
        self.correlation_confidence_input.setPlaceholderText("Support confidence (0.0 - 1.0)")
        self.correlate_btn = QPushButton("Correlate")
        self.promote_btn = QPushButton("Promote To Evidence")
        self.correlate_btn.clicked.connect(self._correlate_selected)
        self.promote_btn.clicked.connect(self._promote_selected)
        correlation_row.addWidget(self.evidence_combo)
        correlation_row.addWidget(self.correlation_rationale_input, 1)
        correlation_row.addWidget(self.correlation_confidence_input)
        correlation_row.addWidget(self.correlate_btn)
        correlation_row.addWidget(self.promote_btn)
        detail_layout.addLayout(correlation_row)

        capture_hint = QLabel(
            "Add screenshot/files to selected evidence, or capture public-media references by URL."
        )
        capture_hint.setStyleSheet("color: #9ca3af; font-size: 12px;")
        detail_layout.addWidget(capture_hint)

        attachment_row = QHBoxLayout()
        self.attachment_path_input = QLineEdit()
        self.attachment_path_input.setPlaceholderText("Local screenshot/file path")
        self.pick_attachment_btn = QPushButton("Browse")
        self.pick_attachment_btn.clicked.connect(self._choose_attachment_file)
        self.attach_file_btn = QPushButton("Attach File")
        self.attach_file_btn.clicked.connect(self._attach_file_selected)
        attachment_row.addWidget(self.attachment_path_input, 1)
        attachment_row.addWidget(self.pick_attachment_btn)
        attachment_row.addWidget(self.attach_file_btn)
        detail_layout.addLayout(attachment_row)

        public_row = QHBoxLayout()
        self.public_url_input = QLineEdit()
        self.public_url_input.setPlaceholderText("Public post/media URL")
        self.public_title_input = QLineEdit()
        self.public_title_input.setPlaceholderText("Media title (optional)")
        self.public_type_input = QLineEdit()
        self.public_type_input.setPlaceholderText("media/post/video/image")
        self.public_provenance_input = QLineEdit()
        self.public_provenance_input.setPlaceholderText("Provenance note")
        self.capture_public_btn = QPushButton("Capture URL")
        self.capture_public_btn.clicked.connect(self._capture_public_url_selected)
        public_row.addWidget(self.public_url_input, 2)
        public_row.addWidget(self.public_title_input)
        public_row.addWidget(self.public_type_input)
        public_row.addWidget(self.public_provenance_input)
        public_row.addWidget(self.capture_public_btn)
        detail_layout.addLayout(public_row)

        self.support_summary_label = QLabel("Support Summary: select a finding to review linked evidence")
        self.support_summary_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        detail_layout.addWidget(self.support_summary_label)

        note_row = QHBoxLayout()
        self.analyst_note_input = QLineEdit()
        self.analyst_note_input.setPlaceholderText("Analyst note for selected finding...")
        self.save_note_btn = QPushButton("Save Note")
        self.save_note_btn.clicked.connect(self._save_note)
        note_row.addWidget(self.analyst_note_input, 1)
        note_row.addWidget(self.save_note_btn)
        detail_layout.addLayout(note_row)

        splitter.addWidget(detail_container)
        layout.addWidget(splitter)

    def load_case(self, case: Case):
        self.case = case
        self.findings = list(case.findings)
        self.target_labels = self.findings_service.target_label_map(case.targets)
        self.evidence_labels = {
            evidence.id: (evidence.normalized_summary or evidence.description or "Evidence item")[:90]
            for evidence in case.evidence
        }
        self._refresh_filter_options()
        self._refresh_evidence_options()
        self._apply_filters()

    def load_findings(self, findings: list[Finding]):
        self.findings = list(findings)
        self.target_labels = {}
        self.evidence_labels = {}
        self._refresh_filter_options()
        self._refresh_evidence_options()
        self._apply_filters()

    def _refresh_evidence_options(self) -> None:
        current = self.evidence_combo.currentData() if hasattr(self, "evidence_combo") else None
        if not hasattr(self, "evidence_combo"):
            return
        self.evidence_combo.blockSignals(True)
        self.evidence_combo.clear()
        self.evidence_combo.addItem("Select supporting evidence", None)
        for evidence_id, label in self.evidence_labels.items():
            self.evidence_combo.addItem(label, evidence_id)
        idx = self.evidence_combo.findData(current)
        self.evidence_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.evidence_combo.blockSignals(False)

    def _refresh_filter_options(self) -> None:
        self.adapter_filter.blockSignals(True)
        self.target_filter.blockSignals(True)
        self.type_filter.blockSignals(True)

        selected_adapter = self.adapter_filter.currentData()
        selected_target = self.target_filter.currentData()
        selected_type = self.type_filter.currentData()

        self.adapter_filter.clear()
        self.adapter_filter.addItem("All Adapters", None)
        for adapter in self.findings_service.unique_adapters(self.findings):
            self.adapter_filter.addItem(adapter, adapter)

        self.target_filter.clear()
        self.target_filter.addItem("All Targets", None)
        for target_id, label in sorted(self.target_labels.items(), key=lambda item: item[1].lower()):
            self.target_filter.addItem(label, target_id)

        self.type_filter.clear()
        self.type_filter.addItem("All Types", None)
        for finding_type in self.findings_service.unique_finding_types(self.findings):
            self.type_filter.addItem(finding_type, finding_type)

        self._restore_combo_selection(self.adapter_filter, selected_adapter)
        self._restore_combo_selection(self.target_filter, selected_target)
        self._restore_combo_selection(self.type_filter, selected_type)

        self.adapter_filter.blockSignals(False)
        self.target_filter.blockSignals(False)
        self.type_filter.blockSignals(False)

    @staticmethod
    def _restore_combo_selection(combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _apply_filters(self):
        review_state = self.review_filter.currentData()
        severity = self.severity_filter.currentData()
        sort_by_value = self.sort_combo.currentData()

        filter_request = FindingFilter(
            review_state=FindingReviewState(review_state) if review_state else None,
            severity=Severity(severity) if severity else None,
            adapter_name=self.adapter_filter.currentData(),
            target_id=self.target_filter.currentData(),
            finding_type=self.type_filter.currentData(),
            text_query=self.search_input.text(),
        )

        filtered = self.findings_service.apply_filters(self.findings, filter_request)
        sort_by = FindingSortBy(sort_by_value)
        self.filtered_findings = self.findings_service.sort_findings(
            filtered,
            sort_by,
            self.target_labels,
        )

        self._render_summary(self.findings_service.summarize_triage(self.findings))
        self._render_table()
        self._reselect_finding()

    def _render_summary(self, summary):
        self.summary_labels["total"].setText(f"Total: {summary.total}")
        self.summary_labels["new"].setText(f"New: {summary.new}")
        self.summary_labels["reviewed"].setText(f"Reviewed: {summary.reviewed}")
        self.summary_labels["flagged"].setText(f"Flagged: {summary.flagged}")
        self.summary_labels["dismissed"].setText(f"Dismissed: {summary.dismissed}")
        self.summary_labels["high_unreviewed"].setText(
            f"High/Critical New: {summary.high_unreviewed}"
        )

    def _render_table(self):
        self.table.setRowCount(0)
        for finding in self.filtered_findings:
            row = self.table.rowCount()
            self.table.insertRow(row)

            severity_item = QTableWidgetItem(finding.severity.value)
            severity_item.setForeground(Qt.GlobalColor.white)
            severity_item.setBackground(
                QColor(SEVERITY_COLORS.get(finding.severity.value, "#ffffff"))
            )

            state_item = QTableWidgetItem(finding.review_state.value)
            state_item.setForeground(Qt.GlobalColor.white)
            state_item.setBackground(
                QColor(REVIEW_STATE_COLORS.get(finding.review_state.value, "#ffffff"))
            )

            self.table.setItem(row, 0, severity_item)
            self.table.setItem(row, 1, state_item)
            self.table.setItem(row, 2, QTableWidgetItem(finding.finding_type.value))
            self.table.setItem(row, 3, QTableWidgetItem(finding.title))
            self.table.setItem(row, 4, QTableWidgetItem(finding.adapter_name))
            self.table.setItem(
                row,
                5,
                QTableWidgetItem(self.target_labels.get(finding.target_id, finding.target_id)),
            )
            self.table.setItem(
                row,
                6,
                QTableWidgetItem(finding.collected_at.strftime("%Y-%m-%d %H:%M")),
            )
            self.table.setItem(row, 7, QTableWidgetItem(finding.source_name or "-"))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, finding.id)

    def _reselect_finding(self) -> None:
        if not self._selected_finding_id:
            if self.filtered_findings:
                self.table.selectRow(0)
            else:
                self.detail_view.clear()
            return

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == self._selected_finding_id:
                self.table.selectRow(row)
                return

        if self.filtered_findings:
            self.table.selectRow(0)
        else:
            self.detail_view.clear()

    def _on_row_selected(self, row: int):
        if row < 0:
            return

        item = self.table.item(row, 0)
        if item is None:
            return

        finding_id = item.data(Qt.ItemDataRole.UserRole)
        finding = self._finding_by_id(finding_id)
        if finding is None:
            return

        self._selected_finding_id = finding.id
        self.analyst_note_input.setText(finding.analyst_note)
        decision_idx = self.decision_state_combo.findData(finding.decision_state)
        self.decision_state_combo.setCurrentIndex(decision_idx if decision_idx >= 0 else 0)
        self.decision_confidence_input.setText(f"{finding.decision_confidence:.2f}")
        self.decision_rationale_input.setText(finding.decision_rationale)

        target_label = self.target_labels.get(finding.target_id, finding.target_id)
        detail = (
            f"Title: {finding.title}\n"
            f"Review State: {finding.review_state.value}\n"
            f"Decision State: {finding.decision_state.value}\n"
            f"Decision Confidence: {finding.decision_confidence:.2f}\n"
            f"Decision Rationale: {finding.decision_rationale or 'N/A'}\n"
            f"Severity: {finding.severity.value}\n"
            f"Type: {finding.finding_type.value}\n"
            f"Adapter: {finding.adapter_name}\n"
            f"Adapter Run ID: {finding.adapter_run_id or 'N/A'}\n"
            f"Target: {target_label}\n"
            f"Collected: {finding.collected_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Source Name: {finding.source_name or 'N/A'}\n"
            f"Source URL: {finding.source_url or 'N/A'}\n"
            f"Analyst Note: {finding.analyst_note or 'N/A'}\n\n"
            f"Description:\n{finding.description}\n\n"
            f"Data:\n{json.dumps(finding.data, indent=2)}"
        )
        self.detail_view.setPlainText(detail)
        self._update_support_summary(finding)

    def _update_support_summary(self, finding: Finding) -> None:
        if self.case is None:
            return
        links = [
            link
            for link in self.case.finding_evidence_links
            if link.finding_id == finding.id
        ]
        if not links:
            self.support_summary_label.setText(
                "Support Summary: no linked evidence yet. Correlate existing evidence or promote this finding."
            )
            return

        avg_conf = sum(link.support_confidence for link in links) / len(links)
        linked_evidence_ids = {link.evidence_id for link in links}
        attachment_count = sum(
            1
            for attachment in self.case.evidence_attachments
            if attachment.evidence_id in linked_evidence_ids
        )
        self.support_summary_label.setText(
            f"Support Summary: {len(links)} linked evidence item(s), avg support confidence {avg_conf:.2f}, attachments {attachment_count}."
        )

    def _choose_attachment_file(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Select evidence attachment")
        if selected:
            self.attachment_path_input.setText(selected)

    def _finding_by_id(self, finding_id: str | None) -> Finding | None:
        if not finding_id:
            return None
        for finding in self.findings:
            if finding.id == finding_id:
                return finding
        return None

    def _request_triage_update(self, state: FindingReviewState) -> None:
        finding = self._finding_by_id(self._selected_finding_id)
        if finding is None:
            return

        note = self.analyst_note_input.text().strip()
        self.triage_update_requested.emit(finding.id, state.value, note)
        self._apply_local_update(finding.id, state, note)

    def _save_note(self) -> None:
        finding = self._finding_by_id(self._selected_finding_id)
        if finding is None:
            return

        note = self.analyst_note_input.text().strip()
        self.triage_update_requested.emit(finding.id, finding.review_state.value, note)
        self._apply_local_update(finding.id, finding.review_state, note)

    def _apply_local_update(
        self,
        finding_id: str,
        review_state: FindingReviewState,
        analyst_note: str,
    ) -> None:
        finding = self._finding_by_id(finding_id)
        if finding is None:
            return

        finding.review_state = review_state
        finding.analyst_note = analyst_note
        self._apply_filters()

    def _save_decision(self) -> None:
        finding = self._finding_by_id(self._selected_finding_id)
        if finding is None:
            return

        try:
            confidence = float(self.decision_confidence_input.text().strip() or "0.5")
        except ValueError:
            return

        rationale = self.decision_rationale_input.text().strip()
        state = self.decision_state_combo.currentData()
        self.decision_update_requested.emit(finding.id, state.value, confidence, rationale)

        finding.decision_state = state
        finding.decision_confidence = min(max(confidence, 0.0), 1.0)
        finding.decision_rationale = rationale
        self._apply_filters()

    def _correlate_selected(self) -> None:
        finding = self._finding_by_id(self._selected_finding_id)
        if finding is None:
            return
        evidence_id = self.evidence_combo.currentData()
        if not isinstance(evidence_id, str):
            return
        try:
            confidence = float(self.correlation_confidence_input.text().strip() or "0.5")
        except ValueError:
            return

        rationale = self.correlation_rationale_input.text().strip()
        self.correlate_requested.emit(finding.id, evidence_id, rationale, confidence)

    def _promote_selected(self) -> None:
        finding = self._finding_by_id(self._selected_finding_id)
        if finding is None:
            return
        try:
            confidence = float(self.correlation_confidence_input.text().strip() or "0.6")
        except ValueError:
            return

        rationale = self.correlation_rationale_input.text().strip()
        self.promote_requested.emit(finding.id, rationale, confidence)

    def _attach_file_selected(self) -> None:
        evidence_id = self.evidence_combo.currentData()
        file_path = self.attachment_path_input.text().strip()
        if not isinstance(evidence_id, str) or not file_path:
            return
        provenance = self.public_provenance_input.text().strip()
        self.attachment_requested.emit(evidence_id, file_path, provenance)

    def _capture_public_url_selected(self) -> None:
        finding = self._finding_by_id(self._selected_finding_id)
        if finding is None:
            return
        url = self.public_url_input.text().strip()
        if not url:
            return

        evidence_id = self.evidence_combo.currentData()
        evidence_ref = evidence_id if isinstance(evidence_id, str) else ""
        self.public_media_capture_requested.emit(
            finding.id,
            evidence_ref,
            url,
            self.public_title_input.text().strip(),
            self.public_type_input.text().strip(),
            self.public_provenance_input.text().strip(),
            self.attachment_path_input.text().strip(),
        )

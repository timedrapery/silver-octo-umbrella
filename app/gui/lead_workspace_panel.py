from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.case import (
    ArtifactLinkType,
    Case,
    LeadLifecycleState,
    LeadPriority,
)
from app.services.case_service import CaseService
from app.services.lead_workspace_service import LeadWorkspaceFilter, LeadListItem


class LeadWorkspacePanel(QWidget):
    """Unified lead workspace for mission-centered pivots and lifecycle management.

    Product value:
    - Merges target and entity perspectives into one lead operating surface.
    - Keeps pivot context nearby so analysts move faster with fewer tab switches.
    - Makes lifecycle and readiness explicit for each subject of interest.
    """

    status_changed = Signal(str)
    case_updated = Signal(object)
    research_pivot_requested = Signal(str, str)
    email_pivot_requested = Signal(str)
    username_pivot_requested = Signal(str)
    tab_open_requested = Signal(str)

    def __init__(self, case_service: CaseService, parent=None):
        super().__init__(parent)
        self.case_service = case_service
        self.current_case: Case | None = None
        self._lead_items: list[LeadListItem] = []
        self._selected_lead_id: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        intro = QLabel(
            "Leads are people, accounts, phones, emails, domains, and IPs that matter to this case. "
            "Use this workspace to track status and pivot to evidence, findings, searches, and research."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addWidget(intro)

        filters = QGroupBox("Lead Filters")
        filter_layout = QGridLayout(filters)

        self.kind_filter = QComboBox()
        self.kind_filter.addItem("All Types", None)
        self.kind_filter.currentIndexChanged.connect(self._refresh_leads)

        self.state_filter = QComboBox()
        self.state_filter.addItem("All States", None)
        for state in LeadLifecycleState:
            self.state_filter.addItem(state.value, state)
        self.state_filter.currentIndexChanged.connect(self._refresh_leads)

        self.priority_filter = QComboBox()
        self.priority_filter.addItem("All Priorities", None)
        for priority in LeadPriority:
            self.priority_filter.addItem(priority.value, priority)
        self.priority_filter.currentIndexChanged.connect(self._refresh_leads)

        self.recent_filter = QCheckBox("Recent activity only")
        self.recent_filter.stateChanged.connect(self._refresh_leads)

        self.has_evidence_filter = QComboBox()
        self.has_evidence_filter.addItem("Evidence: Any", None)
        self.has_evidence_filter.addItem("Evidence: Yes", True)
        self.has_evidence_filter.addItem("Evidence: No", False)
        self.has_evidence_filter.currentIndexChanged.connect(self._refresh_leads)

        self.has_findings_filter = QComboBox()
        self.has_findings_filter.addItem("Findings: Any", None)
        self.has_findings_filter.addItem("Findings: Yes", True)
        self.has_findings_filter.addItem("Findings: No", False)
        self.has_findings_filter.currentIndexChanged.connect(self._refresh_leads)

        self.has_searches_filter = QComboBox()
        self.has_searches_filter.addItem("Searches: Any", None)
        self.has_searches_filter.addItem("Searches: Yes", True)
        self.has_searches_filter.addItem("Searches: No", False)
        self.has_searches_filter.currentIndexChanged.connect(self._refresh_leads)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search lead label, type, owner, context...")
        self.search_input.textChanged.connect(self._refresh_leads)

        filter_layout.addWidget(self.kind_filter, 0, 0)
        filter_layout.addWidget(self.state_filter, 0, 1)
        filter_layout.addWidget(self.priority_filter, 0, 2)
        filter_layout.addWidget(self.recent_filter, 0, 3)
        filter_layout.addWidget(self.has_evidence_filter, 1, 0)
        filter_layout.addWidget(self.has_findings_filter, 1, 1)
        filter_layout.addWidget(self.has_searches_filter, 1, 2)
        filter_layout.addWidget(self.search_input, 1, 3)
        layout.addWidget(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        lead_list_widget = QWidget()
        lead_list_layout = QVBoxLayout(lead_list_widget)

        self.lead_table = QTableWidget(0, 15)
        self.lead_table.setHorizontalHeaderLabels(
            [
                "Lead",
                "Type",
                "State",
                "Priority",
                "Confidence",
                "Freshness",
                "Findings",
                "Evidence",
                "Searches",
                "Runs",
                "Correlated",
                "Needs Support",
                "Low Confidence",
                "Attachments",
                "Missing Attachments",
            ]
        )
        self.lead_table.horizontalHeader().setStretchLastSection(True)
        self.lead_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.lead_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.lead_table.currentCellChanged.connect(self._on_lead_selected)
        lead_list_layout.addWidget(self.lead_table)

        self.empty_label = QLabel(
            "No leads yet. Add targets or run entity research and this workspace will unify them here."
        )
        self.empty_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        lead_list_layout.addWidget(self.empty_label)

        splitter.addWidget(lead_list_widget)

        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)

        self.selected_lead_label = QLabel("Selected Lead: -")
        self.selected_lead_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        detail_layout.addWidget(self.selected_lead_label)

        self.readiness_label = QLabel("Readiness: -")
        self.readiness_label.setStyleSheet("color: #9ca3af;")
        detail_layout.addWidget(self.readiness_label)

        edit_group = QGroupBox("Lead Profile")
        edit_layout = QFormLayout(edit_group)

        self.state_combo = QComboBox()
        for state in LeadLifecycleState:
            self.state_combo.addItem(state.value, state)

        self.priority_combo = QComboBox()
        for priority in LeadPriority:
            self.priority_combo.addItem(priority.value, priority)

        self.owner_input = QLineEdit()
        self.confidence_input = QLineEdit()
        self.confidence_input.setPlaceholderText("0.0 - 1.0")
        self.context_input = QLineEdit()
        self.context_input.setPlaceholderText("What is currently known about this lead")
        self.blocker_input = QLineEdit()
        self.blocker_input.setPlaceholderText("Optional analyst blocker note")
        self.why_input = QLineEdit()
        self.why_input.setPlaceholderText("Why this lead matters")

        self.save_profile_btn = QPushButton("Save Lead Profile")
        self.save_profile_btn.clicked.connect(self._save_profile)

        edit_layout.addRow("Lifecycle", self.state_combo)
        edit_layout.addRow("Priority", self.priority_combo)
        edit_layout.addRow("Owner", self.owner_input)
        edit_layout.addRow("Confidence", self.confidence_input)
        edit_layout.addRow("Context", self.context_input)
        edit_layout.addRow("Blocker Note", self.blocker_input)
        edit_layout.addRow("Why It Matters", self.why_input)
        edit_layout.addRow(self.save_profile_btn)
        detail_layout.addWidget(edit_group)

        task_group = QGroupBox("Task Linkage")
        task_layout = QVBoxLayout(task_group)
        task_row = QHBoxLayout()
        self.task_combo = QComboBox()
        self.task_note_input = QLineEdit()
        self.task_note_input.setPlaceholderText("Why this task is linked to the lead")
        self.link_task_btn = QPushButton("Link Task To Lead")
        self.link_task_btn.clicked.connect(self._link_task)
        task_row.addWidget(self.task_combo)
        task_row.addWidget(self.task_note_input, 1)
        task_row.addWidget(self.link_task_btn)
        task_layout.addLayout(task_row)
        self.task_links_list = QListWidget()
        self.task_links_list.setMaximumHeight(90)
        task_layout.addWidget(self.task_links_list)
        detail_layout.addWidget(task_group)

        quick_group = QGroupBox("Quick Actions")
        quick_layout = QHBoxLayout(quick_group)
        self.phone_btn = QPushButton("Reverse Phone Lookup")
        self.phone_btn.clicked.connect(lambda: self._quick_pivot("PHONE"))
        self.email_btn = QPushButton("Email Pivot Search")
        self.email_btn.clicked.connect(lambda: self._quick_pivot("EMAIL"))
        self.username_btn = QPushButton("Username Pivot")
        self.username_btn.clicked.connect(lambda: self._quick_pivot("USERNAME"))
        self.findings_btn = QPushButton("Open Findings")
        self.findings_btn.clicked.connect(lambda: self.tab_open_requested.emit("Findings"))
        self.timeline_btn = QPushButton("Open Timeline")
        self.timeline_btn.clicked.connect(lambda: self.tab_open_requested.emit("Timeline"))
        quick_layout.addWidget(self.phone_btn)
        quick_layout.addWidget(self.email_btn)
        quick_layout.addWidget(self.username_btn)
        quick_layout.addWidget(self.findings_btn)
        quick_layout.addWidget(self.timeline_btn)
        detail_layout.addWidget(quick_group)

        pivot_group = QGroupBox("Pivot Drill-In")
        pivot_layout = QVBoxLayout(pivot_group)
        self.blockers_view = QTextEdit()
        self.blockers_view.setReadOnly(True)
        self.blockers_view.setMaximumHeight(90)
        self.related_summary = QListWidget()
        self.related_summary.setMaximumHeight(180)
        pivot_layout.addWidget(QLabel("Blockers and Readiness"))
        pivot_layout.addWidget(self.blockers_view)
        pivot_layout.addWidget(QLabel("Related Artifacts"))
        pivot_layout.addWidget(self.related_summary)
        detail_layout.addWidget(pivot_group)

        splitter.addWidget(detail_widget)
        splitter.setSizes([620, 620])

    def load_case(self, case: Case) -> None:
        self.case_service.refresh_case_leads(case.id)
        self.current_case = self.case_service.get_case(case.id)
        self._refresh_kind_filter(self.current_case)
        self._refresh_task_combo(self.current_case)
        self._refresh_leads()

    def _refresh_kind_filter(self, case: Case) -> None:
        previous = self.kind_filter.currentData()
        self.kind_filter.blockSignals(True)
        self.kind_filter.clear()
        self.kind_filter.addItem("All Types", None)
        kinds = sorted({lead.kind for lead in case.leads})
        for kind in kinds:
            self.kind_filter.addItem(kind, kind)
        idx = self.kind_filter.findData(previous)
        self.kind_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.kind_filter.blockSignals(False)

    def _refresh_task_combo(self, case: Case) -> None:
        previous = self.task_combo.currentData()
        self.task_combo.clear()
        self.task_combo.addItem("Select mission task", None)
        for task in case.mission_intake.tasks:
            done = "DONE" if task.completed else "OPEN"
            self.task_combo.addItem(f"[{done}] {task.title}", task.id)
        idx = self.task_combo.findData(previous)
        self.task_combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _current_filter(self) -> LeadWorkspaceFilter:
        return LeadWorkspaceFilter(
            type_kind=self.kind_filter.currentData(),
            lifecycle_state=self.state_filter.currentData(),
            priority=self.priority_filter.currentData(),
            recent_only=self.recent_filter.isChecked(),
            has_evidence=self.has_evidence_filter.currentData(),
            has_findings=self.has_findings_filter.currentData(),
            has_searches=self.has_searches_filter.currentData(),
            text_query=self.search_input.text(),
        )

    def _refresh_leads(self) -> None:
        if self.current_case is None:
            return

        refreshed = self.case_service.get_case(self.current_case.id)
        self.current_case = refreshed
        self._lead_items = self.case_service.list_unified_leads(
            self.current_case.id,
            self._current_filter(),
        )

        self.lead_table.setRowCount(0)
        for item in self._lead_items:
            row = self.lead_table.rowCount()
            self.lead_table.insertRow(row)
            self.lead_table.setItem(row, 0, QTableWidgetItem(item.lead.display_label))
            self.lead_table.setItem(row, 1, QTableWidgetItem(item.lead.kind))
            self.lead_table.setItem(row, 2, QTableWidgetItem(item.lead.lifecycle_state.value))
            self.lead_table.setItem(row, 3, QTableWidgetItem(item.lead.priority.value))
            self.lead_table.setItem(row, 4, QTableWidgetItem(f"{item.lead.confidence_score:.2f}"))
            self.lead_table.setItem(row, 5, QTableWidgetItem(item.freshness))
            self.lead_table.setItem(row, 6, QTableWidgetItem(str(item.findings_count)))
            self.lead_table.setItem(row, 7, QTableWidgetItem(str(item.evidence_count)))
            self.lead_table.setItem(row, 8, QTableWidgetItem(str(item.searches_count)))
            self.lead_table.setItem(row, 9, QTableWidgetItem(str(item.runs_count)))
            self.lead_table.setItem(row, 10, QTableWidgetItem(str(item.correlated_findings_count)))
            self.lead_table.setItem(row, 11, QTableWidgetItem(str(item.unsupported_findings_count)))
            self.lead_table.setItem(row, 12, QTableWidgetItem(str(item.low_confidence_findings_count)))
            self.lead_table.setItem(row, 13, QTableWidgetItem(str(item.attachments_count)))
            self.lead_table.setItem(row, 14, QTableWidgetItem(str(item.evidence_without_attachments_count)))
            self.lead_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, item.lead.id)

        self.empty_label.setVisible(not self._lead_items)
        if self._lead_items:
            self.lead_table.selectRow(0)
        else:
            self._clear_detail()

    def _on_lead_selected(self, row: int, _column: int, _prev_row: int, _prev_column: int) -> None:
        if row < 0 or row >= self.lead_table.rowCount() or self.current_case is None:
            return
        lead_id = self.lead_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not isinstance(lead_id, str):
            return
        self._selected_lead_id = lead_id
        self._load_detail(lead_id)

    def _load_detail(self, lead_id: str) -> None:
        if self.current_case is None:
            return

        detail = self.case_service.get_lead_detail(self.current_case.id, lead_id)
        lead = detail.lead
        self.selected_lead_label.setText(f"Selected Lead: {lead.display_label} [{lead.kind}]")
        self.readiness_label.setText(f"Readiness: {detail.blocker_explanation.readiness}")

        self.state_combo.setCurrentIndex(self.state_combo.findData(lead.lifecycle_state))
        self.priority_combo.setCurrentIndex(self.priority_combo.findData(lead.priority))
        self.owner_input.setText(lead.owner)
        self.confidence_input.setText(f"{lead.confidence_score:.2f}")
        self.context_input.setText(lead.context_summary)
        self.blocker_input.setText(lead.blocker_note)
        self.why_input.setText(lead.why_it_matters)

        blocker_lines: list[str] = []
        if detail.blocker_explanation.blockers:
            blocker_lines.append("Blockers:")
            blocker_lines.extend([f"- {line}" for line in detail.blocker_explanation.blockers])
        if detail.blocker_explanation.readiness_notes:
            blocker_lines.append("Readiness Notes:")
            blocker_lines.extend([f"- {line}" for line in detail.blocker_explanation.readiness_notes])
        self.blockers_view.setPlainText("\n".join(blocker_lines) if blocker_lines else "No blockers detected.")

        self.related_summary.clear()
        self.related_summary.addItem(f"Targets: {len(detail.related_targets)}")
        self.related_summary.addItem(f"Entities: {len(detail.related_entities)}")
        self.related_summary.addItem(f"Findings: {len(detail.related_findings)}")
        self.related_summary.addItem(f"Evidence: {len(detail.related_evidence)}")
        self.related_summary.addItem(f"Attachments: {len(detail.related_attachments)}")
        self.related_summary.addItem(f"Support Links: {len(detail.support_links)}")
        self.related_summary.addItem(f"Saved Searches: {len(detail.related_searches)}")
        self.related_summary.addItem(f"Adapter Runs: {len(detail.related_runs)}")
        self.related_summary.addItem(f"Timeline Events: {len(detail.related_timeline)}")

        unsupported = [
            finding
            for finding in detail.related_findings
            if finding.id not in {link.finding_id for link in detail.support_links}
            and finding.review_state.value != "DISMISSED"
        ]
        low_confidence = [
            finding
            for finding in detail.related_findings
            if finding.decision_confidence < 0.45
        ]
        self.related_summary.addItem(f"Unsupported Findings: {len(unsupported)}")
        self.related_summary.addItem(f"Low-Confidence Findings: {len(low_confidence)}")

        if detail.related_findings:
            self.related_summary.addItem(self._artifact_preview("Finding", detail.related_findings[0].title))
        if detail.related_evidence:
            sample = detail.related_evidence[0].normalized_summary or detail.related_evidence[0].description
            self.related_summary.addItem(self._artifact_preview("Evidence", sample))
        if detail.related_searches:
            self.related_summary.addItem(self._artifact_preview("Search", detail.related_searches[0].title))

        self.task_links_list.clear()
        for link in detail.task_links:
            text = f"Task {link.task_id[:8]} -> {link.artifact_type.value} ({link.note or 'no note'})"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, link.id)
            self.task_links_list.addItem(item)

    @staticmethod
    def _artifact_preview(prefix: str, value: str) -> str:
        trimmed = value if len(value) <= 80 else value[:77] + "..."
        return f"{prefix}: {trimmed}"

    def _save_profile(self) -> None:
        if self.current_case is None or not self._selected_lead_id:
            return

        try:
            confidence = float(self.confidence_input.text().strip() or "0.5")
        except ValueError:
            QMessageBox.warning(self, "Invalid confidence", "Confidence must be a number between 0 and 1.")
            return

        self.case_service.update_lead_profile(
            self.current_case.id,
            self._selected_lead_id,
            lifecycle_state=self.state_combo.currentData(),
            priority=self.priority_combo.currentData(),
            owner=self.owner_input.text(),
            confidence_score=confidence,
            context_summary=self.context_input.text(),
            blocker_note=self.blocker_input.text(),
            why_it_matters=self.why_input.text(),
        )

        self.current_case = self.case_service.get_case(self.current_case.id)
        self._refresh_leads()
        self.case_updated.emit(self.current_case)
        self.status_changed.emit("Lead profile updated")

    def _link_task(self) -> None:
        if self.current_case is None or not self._selected_lead_id:
            return

        task_id = self.task_combo.currentData()
        if not isinstance(task_id, str):
            QMessageBox.information(self, "Task required", "Select a mission task to link.")
            return

        self.case_service.link_task_to_artifact(
            self.current_case.id,
            task_id,
            ArtifactLinkType.LEAD,
            self._selected_lead_id,
            self.task_note_input.text(),
        )
        self.task_note_input.clear()
        self.current_case = self.case_service.get_case(self.current_case.id)
        self._load_detail(self._selected_lead_id)
        self.case_updated.emit(self.current_case)
        self.status_changed.emit("Task linked to lead")

    def _quick_pivot(self, requested_type: str) -> None:
        if self.current_case is None or not self._selected_lead_id:
            return

        detail = self.case_service.get_lead_detail(self.current_case.id, self._selected_lead_id)
        lead = detail.lead

        if requested_type == "PHONE":
            self.tab_open_requested.emit("Entity Research")
            self.research_pivot_requested.emit("PHONE", lead.display_label)
            return

        if requested_type == "EMAIL":
            self.tab_open_requested.emit("Search Builder")
            self.email_pivot_requested.emit(lead.display_label)
            return

        if requested_type == "USERNAME":
            self.tab_open_requested.emit("Search Builder")
            self.username_pivot_requested.emit(lead.display_label)
            return

        self.status_changed.emit("Unsupported pivot action")

    def _clear_detail(self) -> None:
        self.selected_lead_label.setText("Selected Lead: -")
        self.readiness_label.setText("Readiness: -")
        self.blockers_view.clear()
        self.related_summary.clear()
        self.task_links_list.clear()

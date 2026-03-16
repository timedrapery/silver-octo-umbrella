from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal

from app.gui.widgets.target_input import TargetInputWidget
from app.models.case import Case, CaseStatus, MissionPriority, WorkflowStage
from app.services.case_service import CaseService


class CasePanel(QWidget):
    case_selected = Signal(object)  # Case
    case_updated = Signal(object)  # Case

    def __init__(self, case_service: CaseService, parent=None):
        super().__init__(parent)
        self.case_service = case_service
        self.current_case: Case | None = None
        self._build_ui()
        self.refresh_cases()

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(splitter)

        # Left: case list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.case_list = QListWidget()
        self.case_list.currentRowChanged.connect(self._on_case_selected)
        left_layout.addWidget(QLabel("Cases"))
        left_layout.addWidget(self.case_list)

        btn_row = QHBoxLayout()
        self.new_btn = QPushButton("New Case")
        self.new_btn.clicked.connect(self._on_new_case)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._on_delete_case)
        btn_row.addWidget(self.new_btn)
        btn_row.addWidget(self.delete_btn)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left)

        # Right: case detail
        right = QWidget()
        right_layout = QVBoxLayout(right)

        info_group = QGroupBox("Case Details")
        info_layout = QVBoxLayout(info_group)
        self.name_label = QLabel("—")
        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #e2e8f0;")
        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        self.triage_label = QLabel("Findings: 0 | New: 0 | Reviewed: 0 | Flagged: 0 | Dismissed: 0")
        self.triage_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.search_label = QLabel("Saved Searches: 0 | Linked Targets: 0 | Last Search: -")
        self.search_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.entity_label = QLabel("Researched Entities: 0 | Research Evidence: 0 | Last Research: -")
        self.entity_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.desc_label)
        info_layout.addWidget(self.triage_label)
        info_layout.addWidget(self.search_label)
        info_layout.addWidget(self.entity_label)
        right_layout.addWidget(info_group)

        mission_group = QGroupBox("Mission Intake")
        mission_layout = QVBoxLayout(mission_group)
        self.mission_summary_input = QTextEdit()
        self.mission_summary_input.setPlaceholderText("Mission summary and objective framing...")
        self.mission_summary_input.setMaximumHeight(68)
        self.objectives_input = QTextEdit()
        self.objectives_input.setPlaceholderText("Objectives (one per line)")
        self.objectives_input.setMaximumHeight(58)
        self.hypotheses_input = QTextEdit()
        self.hypotheses_input.setPlaceholderText("Hypotheses (one per line)")
        self.hypotheses_input.setMaximumHeight(58)
        self.scope_input = QLineEdit()
        self.scope_input.setPlaceholderText("Scope")
        self.constraints_input = QLineEdit()
        self.constraints_input.setPlaceholderText("Constraints")
        self.legal_notes_input = QLineEdit()
        self.legal_notes_input.setPlaceholderText("Legal and operational notes")
        self.risk_notes_input = QLineEdit()
        self.risk_notes_input.setPlaceholderText("Risk notes")
        self.intake_notes_input = QLineEdit()
        self.intake_notes_input.setPlaceholderText("Intake notes")
        self.priority_combo = QComboBox()
        for priority in MissionPriority:
            self.priority_combo.addItem(priority.value, priority)
        self.save_mission_btn = QPushButton("Save Intake")
        self.save_mission_btn.clicked.connect(self._on_save_mission_intake)

        mission_layout.addWidget(QLabel("Mission Summary"))
        mission_layout.addWidget(self.mission_summary_input)
        mission_layout.addWidget(QLabel("Objectives"))
        mission_layout.addWidget(self.objectives_input)
        mission_layout.addWidget(QLabel("Hypotheses"))
        mission_layout.addWidget(self.hypotheses_input)
        mission_layout.addWidget(self.scope_input)
        mission_layout.addWidget(self.constraints_input)
        mission_layout.addWidget(self.legal_notes_input)
        mission_layout.addWidget(self.risk_notes_input)
        mission_layout.addWidget(self.intake_notes_input)

        mission_meta_row = QHBoxLayout()
        mission_meta_row.addWidget(QLabel("Priority"))
        mission_meta_row.addWidget(self.priority_combo)
        mission_meta_row.addStretch()
        mission_meta_row.addWidget(self.save_mission_btn)
        mission_layout.addLayout(mission_meta_row)
        right_layout.addWidget(mission_group)

        workflow_group = QGroupBox("Workflow Stage")
        workflow_layout = QVBoxLayout(workflow_group)
        workflow_row = QHBoxLayout()
        self.workflow_stage_combo = QComboBox()
        for stage in WorkflowStage:
            self.workflow_stage_combo.addItem(stage.value, stage)
        self.workflow_note_input = QLineEdit()
        self.workflow_note_input.setPlaceholderText("Stage note")
        self.update_stage_btn = QPushButton("Update Stage")
        self.update_stage_btn.clicked.connect(self._on_update_stage)
        workflow_row.addWidget(self.workflow_stage_combo)
        workflow_row.addWidget(self.workflow_note_input, 1)
        workflow_row.addWidget(self.update_stage_btn)
        workflow_layout.addLayout(workflow_row)
        self.workflow_updated_label = QLabel("Last stage update: -")
        self.workflow_updated_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        workflow_layout.addWidget(self.workflow_updated_label)
        right_layout.addWidget(workflow_group)

        dashboard_group = QGroupBox("Case Dashboard")
        dashboard_layout = QVBoxLayout(dashboard_group)
        self.dashboard_signal_label = QLabel(
            "Timeline: - | High-Risk Open: 0 | Flagged: 0 | New: 0 | Reviewed: 0"
        )
        self.dashboard_signal_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.dashboard_activity_label = QLabel(
            "Recent Activity: 0 | Saved Searches: 0 | Entities: 0 | Evidence: 0 | Attachments: 0"
        )
        self.dashboard_activity_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.dashboard_convergence_label = QLabel(
            "Correlated Findings: 0 | Unsupported: 0 | Low Confidence: 0 | Unlinked Evidence: 0 | Evidence Missing Attachments: 0"
        )
        self.dashboard_convergence_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.dashboard_readiness_label = QLabel(
            "Reporting Readiness: LOW | Checklist: 0/0 complete"
        )
        self.dashboard_readiness_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        dashboard_layout.addWidget(self.dashboard_signal_label)
        dashboard_layout.addWidget(self.dashboard_activity_label)
        dashboard_layout.addWidget(self.dashboard_convergence_label)
        dashboard_layout.addWidget(self.dashboard_readiness_label)

        self.onboarding_hint_label = QLabel("Start by creating a case and adding your first target.")
        self.onboarding_hint_label.setWordWrap(True)
        self.onboarding_hint_label.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        dashboard_layout.addWidget(self.onboarding_hint_label)

        dashboard_layout.addWidget(QLabel("Featured Collection Actions"))
        self.featured_actions_list = QListWidget()
        self.featured_actions_list.setMaximumHeight(92)
        dashboard_layout.addWidget(self.featured_actions_list)

        dashboard_layout.addWidget(QLabel("Recommended Next Actions"))
        self.recommendation_list = QListWidget()
        self.recommendation_list.setMaximumHeight(108)
        dashboard_layout.addWidget(self.recommendation_list)
        right_layout.addWidget(dashboard_group)

        checklist_group = QGroupBox("Mission Checklist")
        checklist_layout = QVBoxLayout(checklist_group)
        self.task_table = QTableWidget(0, 3)
        self.task_table.setHorizontalHeaderLabels(["Done", "Task", "Note"])
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.task_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        checklist_layout.addWidget(self.task_table)

        task_btn_row = QHBoxLayout()
        self.add_task_btn = QPushButton("Add Task")
        self.add_task_btn.clicked.connect(self._on_add_task)
        self.toggle_task_btn = QPushButton("Toggle Done")
        self.toggle_task_btn.clicked.connect(self._on_toggle_task)
        self.delete_task_btn = QPushButton("Delete Task")
        self.delete_task_btn.clicked.connect(self._on_delete_task)
        task_btn_row.addWidget(self.add_task_btn)
        task_btn_row.addWidget(self.toggle_task_btn)
        task_btn_row.addWidget(self.delete_task_btn)
        task_btn_row.addStretch()
        checklist_layout.addLayout(task_btn_row)
        right_layout.addWidget(checklist_group)

        targets_group = QGroupBox("Targets")
        tgt_layout = QVBoxLayout(targets_group)
        self.targets_list = QListWidget()
        self.targets_list.setMaximumHeight(120)
        tgt_layout.addWidget(self.targets_list)
        self.target_input = TargetInputWidget()
        self.target_input.target_added.connect(self._on_add_target)
        tgt_layout.addWidget(self.target_input)
        right_layout.addWidget(targets_group)

        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout(notes_group)
        self.notes_list = QListWidget()
        self.notes_list.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_list)
        note_row = QHBoxLayout()
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("Add a note...")
        self.add_note_btn = QPushButton("Add")
        self.add_note_btn.clicked.connect(self._on_add_note)
        note_row.addWidget(self.note_input, 1)
        note_row.addWidget(self.add_note_btn)
        notes_layout.addLayout(note_row)
        right_layout.addWidget(notes_group)

        evidence_group = QGroupBox("Promoted Evidence")
        evidence_layout = QVBoxLayout(evidence_group)
        self.evidence_list = QListWidget()
        self.evidence_list.setMaximumHeight(110)
        evidence_layout.addWidget(self.evidence_list)
        right_layout.addWidget(evidence_group)

        timeline_group = QGroupBox("Recent Activity")
        timeline_layout = QVBoxLayout(timeline_group)
        self.timeline_list = QListWidget()
        self.timeline_list.setMaximumHeight(130)
        timeline_layout.addWidget(self.timeline_list)
        right_layout.addWidget(timeline_group)
        right_layout.addStretch()

        splitter.addWidget(right)
        splitter.setSizes([200, 600])

    def refresh_cases(self):
        self.case_list.clear()
        for case in self.case_service.list_cases():
            self.case_list.addItem(case.name)
        self._cases = self.case_service.list_cases()

    def _on_case_selected(self, row: int):
        if row < 0 or row >= len(self._cases):
            return
        self.current_case = self._cases[row]
        self._populate_detail(self.current_case)
        self.case_selected.emit(self.current_case)

    def _populate_detail(self, case: Case):
        self.name_label.setText(case.name)
        self.desc_label.setText(case.description)
        dashboard = self.case_service.get_case_dashboard_summary(case.id)
        summary = self.case_service.get_case_triage_summary(case.id)
        self.triage_label.setText(
            "Findings: "
            f"{summary.total} | New: {summary.new} | Reviewed: {summary.reviewed} | "
            f"Flagged: {summary.flagged} | Dismissed: {summary.dismissed} | "
            f"High/Critical New: {summary.high_unreviewed}"
        )
        search_summary = self.case_service.get_case_search_summary(case.id)
        last_search = (
            search_summary.last_created_at.strftime("%Y-%m-%d %H:%M")
            if search_summary.last_created_at
            else "-"
        )
        self.search_label.setText(
            "Saved Searches: "
            f"{search_summary.total} | Linked Targets: {search_summary.linked_targets} | "
            f"Last Search: {last_search}"
        )
        entity_summary = self.case_service.get_case_entity_activity_summary(case.id)
        last_research = (
            entity_summary.last_research_at.strftime("%Y-%m-%d %H:%M")
            if entity_summary.last_research_at
            else "-"
        )
        self.entity_label.setText(
            "Researched Entities: "
            f"{entity_summary.total_entities} | Research Evidence: {entity_summary.research_evidence_total} | "
            f"Last Research: {last_research}"
        )

        mission = dashboard.mission_intake
        self.mission_summary_input.setPlainText(mission.mission_summary)
        self.objectives_input.setPlainText("\n".join(mission.objectives))
        self.hypotheses_input.setPlainText("\n".join(mission.hypotheses))
        self.scope_input.setText(mission.scope)
        self.constraints_input.setText(mission.constraints)
        self.legal_notes_input.setText(mission.legal_operational_notes)
        self.risk_notes_input.setText(mission.risk_notes)
        self.intake_notes_input.setText(mission.intake_notes)
        priority_idx = self.priority_combo.findData(mission.priority)
        self.priority_combo.setCurrentIndex(priority_idx if priority_idx >= 0 else 0)

        stage_idx = self.workflow_stage_combo.findData(case.workflow_stage)
        self.workflow_stage_combo.setCurrentIndex(stage_idx if stage_idx >= 0 else 0)
        self.workflow_note_input.setText(case.workflow_stage_note)
        self.workflow_updated_label.setText(
            f"Last stage update: {case.workflow_stage_updated_at.strftime('%Y-%m-%d %H:%M')}"
        )

        self.dashboard_signal_label.setText(
            "Timeline: "
            f"{dashboard.signals.timeline_health} | High-Risk Open: {dashboard.signals.unresolved_high_risk} | "
            f"Flagged: {dashboard.signals.flagged_findings} | New: {dashboard.signals.new_findings} | "
            f"Reviewed: {dashboard.signals.reviewed_findings}"
        )
        self.dashboard_activity_label.setText(
            "Recent Activity: "
            f"{dashboard.signals.recent_activity_count} | Saved Searches: {dashboard.signals.saved_searches} | "
            f"Entities: {dashboard.signals.researched_entities} | Evidence: {dashboard.signals.evidence_total} "
            f"(+{dashboard.signals.evidence_recent_7d} in 7d) | Attachments: {dashboard.signals.evidence_attachments_total}"
        )
        self.dashboard_convergence_label.setText(
            "Correlated Findings: "
            f"{dashboard.signals.correlated_findings} | Unsupported: {dashboard.signals.unsupported_findings} | "
            f"Low Confidence: {dashboard.signals.low_confidence_findings} | "
            f"Unlinked Evidence: {dashboard.signals.unlinked_evidence} | "
            f"Evidence Missing Attachments: {dashboard.signals.evidence_without_attachments}"
        )
        self.dashboard_readiness_label.setText(
            "Reporting Readiness: "
            f"{dashboard.signals.reporting_readiness} | Checklist: "
            f"{dashboard.signals.checklist_completed}/{dashboard.signals.checklist_total} complete"
        )
        self.onboarding_hint_label.setText(dashboard.onboarding_hint)

        self.featured_actions_list.clear()
        for action in dashboard.featured_collection_actions:
            self.featured_actions_list.addItem(action)

        self.recommendation_list.clear()
        for action in dashboard.recommended_actions:
            self.recommendation_list.addItem(action)

        self.task_table.setRowCount(0)
        for task in mission.tasks:
            row = self.task_table.rowCount()
            self.task_table.insertRow(row)
            done_text = "yes" if task.completed else "no"
            self.task_table.setItem(row, 0, QTableWidgetItem(done_text))
            self.task_table.setItem(row, 1, QTableWidgetItem(task.title))
            self.task_table.setItem(row, 2, QTableWidgetItem(task.note or "-"))
            self.task_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, task.id)

        self.targets_list.clear()
        for t in case.targets:
            self.targets_list.addItem(f"[{t.type.value}] {t.value}")
        self.notes_list.clear()
        for n in case.notes:
            self.notes_list.addItem(n.content[:80])
        self.evidence_list.clear()
        for item in case.evidence[:25]:
            label = item.normalized_summary or item.description or "Evidence item"
            self.evidence_list.addItem(label[:120])

        self.timeline_list.clear()
        for event in dashboard.recent_activity:
            ts = event.occurred_at.strftime("%m-%d %H:%M")
            self.timeline_list.addItem(f"[{ts}] {event.summary[:92]}")

    def _on_new_case(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Case", "Case name:")
        if ok and name.strip():
            desc, ok2 = QInputDialog.getText(self, "New Case", "Description (optional):")
            self.case_service.create_case(name.strip(), desc.strip() if ok2 else "")
            self.refresh_cases()

    def _on_delete_case(self):
        if self.current_case is None:
            return
        reply = QMessageBox.question(self, "Delete", f"Delete case '{self.current_case.name}'?")
        if reply == QMessageBox.StandardButton.Yes:
            self.case_service.delete_case(self.current_case.id)
            self.current_case = None
            self.refresh_cases()

    @staticmethod
    def _split_lines(text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _on_save_mission_intake(self):
        if self.current_case is None:
            return

        self.case_service.update_mission_intake(
            self.current_case.id,
            mission_summary=self.mission_summary_input.toPlainText(),
            objectives=self._split_lines(self.objectives_input.toPlainText()),
            hypotheses=self._split_lines(self.hypotheses_input.toPlainText()),
            scope=self.scope_input.text(),
            constraints=self.constraints_input.text(),
            legal_operational_notes=self.legal_notes_input.text(),
            risk_notes=self.risk_notes_input.text(),
            priority=self.priority_combo.currentData(),
            intake_notes=self.intake_notes_input.text(),
        )

        self.current_case = self.case_service.get_case(self.current_case.id)
        self._populate_detail(self.current_case)
        self.case_updated.emit(self.current_case)

    def _on_update_stage(self):
        if self.current_case is None:
            return

        try:
            self.case_service.update_workflow_stage(
                self.current_case.id,
                workflow_stage=self.workflow_stage_combo.currentData(),
                stage_note=self.workflow_note_input.text(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid stage transition", str(exc))
            return

        self.current_case = self.case_service.get_case(self.current_case.id)
        self._populate_detail(self.current_case)
        self.case_updated.emit(self.current_case)

    def _selected_task_id(self) -> str | None:
        row = self.task_table.currentRow()
        if row < 0:
            return None
        item = self.task_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) else None

    def _on_add_task(self):
        if self.current_case is None:
            return

        from PySide6.QtWidgets import QInputDialog

        title, ok = QInputDialog.getText(self, "Add Mission Task", "Task title:")
        if not ok or not title.strip():
            return

        note, _ = QInputDialog.getText(self, "Add Mission Task", "Task note (optional):")
        self.case_service.add_mission_task(self.current_case.id, title=title, note=note)
        self.current_case = self.case_service.get_case(self.current_case.id)
        self._populate_detail(self.current_case)
        self.case_updated.emit(self.current_case)

    def _on_toggle_task(self):
        if self.current_case is None:
            return

        task_id = self._selected_task_id()
        if task_id is None:
            return

        task = next(
            (item for item in self.current_case.mission_intake.tasks if item.id == task_id),
            None,
        )
        if task is None:
            return

        self.case_service.update_mission_task(
            self.current_case.id,
            task_id,
            completed=not task.completed,
        )
        self.current_case = self.case_service.get_case(self.current_case.id)
        self._populate_detail(self.current_case)
        self.case_updated.emit(self.current_case)

    def _on_delete_task(self):
        if self.current_case is None:
            return

        task_id = self._selected_task_id()
        if task_id is None:
            return

        self.case_service.delete_mission_task(self.current_case.id, task_id)
        self.current_case = self.case_service.get_case(self.current_case.id)
        self._populate_detail(self.current_case)
        self.case_updated.emit(self.current_case)

    def _on_add_target(self, target_type, value):
        if self.current_case is None:
            return
        self.case_service.add_target(self.current_case.id, target_type, value)
        self.current_case = self.case_service.get_case(self.current_case.id)
        self._populate_detail(self.current_case)
        self.case_updated.emit(self.current_case)

    def _on_add_note(self):
        if self.current_case is None:
            return
        content = self.note_input.text().strip()
        if content:
            self.case_service.add_note(self.current_case.id, content)
            self.note_input.clear()
            self.current_case = self.case_service.get_case(self.current_case.id)
            self._populate_detail(self.current_case)
            self.case_updated.emit(self.current_case)

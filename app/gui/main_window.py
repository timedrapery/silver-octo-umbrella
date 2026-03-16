from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenuBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.core.adapters.cert_adapter import CertAdapter
from app.core.adapters.dns_adapter import DnsAdapter
from app.core.adapters.http_adapter import HttpAdapter
from app.core.adapters.metadata_adapter import MetadataAdapter
from app.core.adapters.social_adapter import SocialAdapter
from app.core.adapters.subdomain_adapter import SubdomainAdapter
from app.gui.case_panel import CasePanel
from app.gui.entity_research_panel import EntityResearchPanel
from app.gui.findings_panel import FindingsPanel
from app.gui.graph_panel import GraphPanel
from app.gui.lead_workspace_panel import LeadWorkspacePanel
from app.gui.metadata_lab_panel import MetadataLabPanel
from app.gui.report_panel import ReportPanel
from app.gui.search_builder_panel import SearchBuilderPanel
from app.gui.timeline_panel import TimelinePanel
from app.gui.widgets.progress_widget import ProgressWidget
from app.gui.workers import InvestigationWorker
from app.models.case import (
    AdapterRunStatus,
    Case,
    Finding,
    FindingDecisionState,
    FindingReviewState,
    InvestigationPreset,
    Target,
    TargetType,
)
from app.services.case_service import CaseService
from app.services.entity_research_service import EntityResearchService
from app.services.findings_service import FindingsService
from app.services.graph_service import GraphService
from app.services.intelligence_orchestrator import MultiSourceOrchestrator
from app.services.investigation_service import InvestigationService
from app.services.report_service import ReportService
from app.services.search_builder_service import SearchBuilderService
from app.storage.intelligence_repository import IntelligenceRepository
from app.storage.database import Database

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #121722;
    color: #d9e2ef;
    font-family: "Trebuchet MS", "Segoe UI", sans-serif;
    font-size: 13px;
}
QMenuBar {
    background: #0f1420;
    color: #d9e2ef;
    border-bottom: 1px solid #2b374a;
}
QMenuBar::item {
    padding: 5px 10px;
    border-radius: 4px;
}
QMenuBar::item:selected { background: #1d2838; }
QMenu {
    background: #101824;
    color: #d9e2ef;
    border: 1px solid #2b374a;
}
QMenu::item:selected { background: #2d7a96; }
QTabWidget::pane {
    border: 1px solid #2b374a;
    background: #161d2a;
    border-radius: 8px;
}
QTabBar::tab {
    background: #1a2231;
    color: #8ea0b8;
    padding: 9px 16px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #2d7a96;
    color: #f7fbff;
    font-weight: 600;
}
QListWidget {
    background: #171f2d;
    border: 1px solid #2b374a;
    border-radius: 8px;
    padding: 4px;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background: #2d7a96;
    color: #f7fbff;
}
QPushButton {
    background: #1d2838;
    color: #d9e2ef;
    border: 1px solid #314157;
    padding: 7px 14px;
    border-radius: 7px;
}
QPushButton:hover {
    background: #263348;
    border-color: #3f5673;
}
QPushButton#startBtn {
    background: #2d7a96;
    color: #f7fbff;
    font-weight: 700;
    padding: 11px;
    border: 1px solid #3f97b8;
}
QPushButton#startBtn:hover { background: #3b90b0; }
QLineEdit, QComboBox, QTextEdit {
    background: #171f2d;
    color: #d9e2ef;
    border: 1px solid #314157;
    border-radius: 6px;
    padding: 6px 8px;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #4ca0bf;
}
QGroupBox {
    border: 1px solid #2b374a;
    border-radius: 8px;
    margin-top: 9px;
    color: #9cb0c9;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QTableWidget {
    background: #171f2d;
    border: 1px solid #2b374a;
    gridline-color: #283446;
    alternate-background-color: #1a2433;
}
QTableWidget::item:selected {
    background: #2d7a96;
    color: #f7fbff;
}
QHeaderView::section {
    background: #202b3b;
    color: #d9e2ef;
    padding: 6px;
    border: 0;
    border-bottom: 1px solid #314157;
}
QProgressBar {
    background: #171f2d;
    border: 1px solid #314157;
    border-radius: 5px;
    text-align: center;
}
QProgressBar::chunk {
    background: #2d7a96;
    border-radius: 4px;
}
QSplitter::handle { background: #2b374a; }
QStatusBar {
    background: #0f1420;
    color: #8ea0b8;
    border-top: 1px solid #2b374a;
}
QScrollBar:vertical {
    background: #131b28;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #30435c;
    border-radius: 5px;
}
QCheckBox { color: #d9e2ef; }
QRadioButton { color: #d9e2ef; }
"""


class MainWindow(QMainWindow):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_case: Case | None = None
        self._setup_services()
        self._build_ui()
        self.setStyleSheet(DARK_STYLE)
        self.setWindowTitle("OSINT Research Platform")
        self.resize(1400, 880)

    def _setup_services(self):
        self.case_service = CaseService(self.db)
        self.findings_service = FindingsService()
        self.search_builder_service = SearchBuilderService()
        self.intelligence_repository = IntelligenceRepository(self.db)
        self.entity_research_service = EntityResearchService(
            orchestrator=MultiSourceOrchestrator(),
            repository=self.intelligence_repository,
        )
        self.investigation_service = InvestigationService([
            DnsAdapter(), CertAdapter(), HttpAdapter(),
            SocialAdapter(), SubdomainAdapter(), MetadataAdapter(),
        ])
        self.graph_service = GraphService()
        self.report_service = ReportService()

    def _build_ui(self):
        self._build_menu()
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(230)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(8, 8, 8, 8)
        sb_layout.setSpacing(8)
        sb_label = QLabel("Cases")
        sb_label.setStyleSheet("font-weight: 700; color: #4ca0bf; padding: 4px 6px;")
        self.sidebar_list = QListWidget()
        self.sidebar_list.currentRowChanged.connect(self._on_sidebar_case_changed)
        new_case_btn = QPushButton("+ New Case")
        new_case_btn.clicked.connect(self._on_new_case_sidebar)
        sb_layout.addWidget(sb_label)
        sb_layout.addWidget(self.sidebar_list)
        sb_layout.addWidget(new_case_btn)
        splitter.addWidget(sidebar)

        # Tabs
        self.tabs = QTabWidget()
        self.case_panel = CasePanel(self.case_service)
        self.case_panel.case_selected.connect(self._on_case_selected)
        self.case_panel.case_updated.connect(self._on_case_updated)
        self.findings_panel = FindingsPanel(self.findings_service)
        self.findings_panel.triage_update_requested.connect(self._on_finding_triage_update)
        self.findings_panel.decision_update_requested.connect(self._on_finding_decision_update)
        self.findings_panel.correlate_requested.connect(self._on_finding_correlate)
        self.findings_panel.promote_requested.connect(self._on_finding_promote)
        self.findings_panel.attachment_requested.connect(self._on_evidence_attachment)
        self.findings_panel.public_media_capture_requested.connect(self._on_public_media_capture)
        self.search_builder_panel = SearchBuilderPanel(
            self.case_service,
            self.search_builder_service,
        )
        self.entity_research_panel = EntityResearchPanel(
            self.case_service,
            self.entity_research_service,
        )
        self.entity_research_panel.status_changed.connect(self.status_bar.showMessage)
        self.entity_research_panel.case_updated.connect(self._on_case_selected)
        self.search_builder_panel.status_changed.connect(self.status_bar.showMessage)
        self.lead_workspace_panel = LeadWorkspacePanel(self.case_service)
        self.lead_workspace_panel.status_changed.connect(self.status_bar.showMessage)
        self.lead_workspace_panel.case_updated.connect(self._on_case_updated)
        self.lead_workspace_panel.research_pivot_requested.connect(self._on_research_pivot_requested)
        self.lead_workspace_panel.email_pivot_requested.connect(self._on_email_pivot_requested)
        self.lead_workspace_panel.username_pivot_requested.connect(self._on_username_pivot_requested)
        self.lead_workspace_panel.tab_open_requested.connect(self._open_tab_by_name)
        self.graph_panel = GraphPanel(self.graph_service)
        self.timeline_panel = TimelinePanel(self.case_service)
        self.metadata_lab_panel = MetadataLabPanel(self.case_service)
        self.metadata_lab_panel.status_changed.connect(self.status_bar.showMessage)
        self.metadata_lab_panel.case_updated.connect(self._on_case_updated)
        self.report_panel = ReportPanel(self.report_service)

        self.tabs.addTab(self.case_panel, "Cases")
        self.tabs.addTab(self._build_investigation_tab(), "Investigation")
        self.tabs.addTab(self.lead_workspace_panel, "Lead Workspace")
        self.tabs.addTab(self.search_builder_panel, "Search Builder")
        self.tabs.addTab(self.entity_research_panel, "Entity Research")
        self.tabs.addTab(self.metadata_lab_panel, "Metadata Lab")
        self.tabs.addTab(self.timeline_panel, "Timeline")
        self.tabs.addTab(self.findings_panel, "Findings")
        self.tabs.addTab(self.graph_panel, "Graph")
        self.tabs.addTab(self.report_panel, "Reports")
        splitter.addWidget(self.tabs)
        splitter.setSizes([240, 1160])

        self._refresh_sidebar()

    def _build_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction("New Case", self._on_new_case_sidebar)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        menu_bar.addMenu("View")
        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction("Quick Start", self._show_quick_start)

    def _show_quick_start(self):
        QMessageBox.information(
            self,
            "Quick Start",
            (
                "1) Create a case in the sidebar.\n"
                "2) Add mission summary and objectives in the Cases tab.\n"
                "3) Add targets, then use Featured Collection Actions for phone/email pivots.\n"
                "4) Run Investigation and Entity Research tabs.\n"
                "5) Use Recommended Next Actions to progress stage-by-stage."
            ),
        )

    def _build_investigation_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Target group
        target_group = QGroupBox("Target")
        tgt_layout = QHBoxLayout(target_group)
        self.inv_type_combo = QComboBox()
        for t in TargetType:
            self.inv_type_combo.addItem(t.value, t)
        self.inv_value_input = QLineEdit()
        self.inv_value_input.setPlaceholderText("Enter target value (e.g. example.com)")
        tgt_layout.addWidget(QLabel("Type:"))
        tgt_layout.addWidget(self.inv_type_combo)
        tgt_layout.addWidget(QLabel("Value:"))
        tgt_layout.addWidget(self.inv_value_input, 1)
        layout.addWidget(target_group)

        # Presets group
        presets_group = QGroupBox("Investigation Presets")
        presets_layout = QHBoxLayout(presets_group)
        preset_defs = [
            ("Domain Intel", InvestigationPreset.DOMAIN_INTELLIGENCE),
            ("Org Footprint", InvestigationPreset.ORGANIZATION_FOOTPRINT),
            ("Username", InvestigationPreset.USERNAME_INVESTIGATION),
            ("Infra Mapping", InvestigationPreset.INFRASTRUCTURE_MAPPING),
        ]
        for label, preset in preset_defs:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, p=preset: self._run_preset(p))
            presets_layout.addWidget(btn)
        layout.addWidget(presets_group)

        # Adapters group
        adapters_group = QGroupBox("Adapters")
        adapters_layout = QHBoxLayout(adapters_group)
        self.adapter_checks: dict[str, QCheckBox] = {}
        for name in ["dns", "cert", "http", "social", "subdomain", "metadata"]:
            cb = QCheckBox(name)
            cb.setChecked(True)
            self.adapter_checks[name] = cb
            adapters_layout.addWidget(cb)
        layout.addWidget(adapters_group)

        # Progress
        self.progress_widget = ProgressWidget()
        layout.addWidget(self.progress_widget)

        # Start button
        self.start_btn = QPushButton("▶  Start Investigation")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.clicked.connect(self._run_investigation)
        layout.addWidget(self.start_btn)

        # Results table
        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(["Severity", "Type", "Title", "Adapter", "Description"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.results_table)

        return widget

    def _refresh_sidebar(self):
        self.sidebar_list.clear()
        self._sidebar_cases = self.case_service.list_cases()
        for c in self._sidebar_cases:
            self.sidebar_list.addItem(c.name)
        if not self._sidebar_cases:
            self.status_bar.showMessage("Welcome: create your first case to start mission intake and guided collection.")

    def _on_sidebar_case_changed(self, row: int):
        if row < 0 or row >= len(self._sidebar_cases):
            return
        case = self._sidebar_cases[row]
        self._on_case_selected(case)

    def _on_case_selected(self, case: Case):
        self.case_service.refresh_case_leads(case.id)
        case = self.case_service.get_case(case.id)
        self.current_case = case
        self.graph_panel.load_case(case)
        self.report_panel.load_case(case)
        self.lead_workspace_panel.load_case(case)
        self.search_builder_panel.load_case(case)
        self.entity_research_panel.load_case(case)
        self.metadata_lab_panel.load_case(case)
        self.timeline_panel.load_case(case)
        self.findings_panel.load_case(case)
        self.status_bar.showMessage(f"Active case: {case.name}")

    def _on_case_updated(self, case: Case):
        self._refresh_sidebar()
        self._on_case_selected(case)

    def _on_finding_triage_update(self, finding_id: str, state_value: str, analyst_note: str):
        if self.current_case is None:
            return

        self.case_service.update_finding_triage(
            case_id=self.current_case.id,
            finding_id=finding_id,
            review_state=FindingReviewState(state_value),
            analyst_note=analyst_note,
        )

        self.current_case = self.case_service.get_case(self.current_case.id)
        self.findings_panel.load_case(self.current_case)
        self.report_panel.load_case(self.current_case)
        self.lead_workspace_panel.load_case(self.current_case)
        self.search_builder_panel.load_case(self.current_case)
        self.entity_research_panel.load_case(self.current_case)
        self.timeline_panel.load_case(self.current_case)
        self.case_panel._populate_detail(self.current_case)
        self.status_bar.showMessage(f"Finding triage updated: {state_value}")

    def _on_finding_decision_update(
        self,
        finding_id: str,
        decision_state_value: str,
        confidence: float,
        rationale: str,
    ):
        if self.current_case is None:
            return

        self.case_service.update_finding_decision(
            self.current_case.id,
            finding_id,
            decision_state=FindingDecisionState(decision_state_value),
            decision_confidence=confidence,
            decision_rationale=rationale,
        )
        self._reload_case_after_convergence_update(
            f"Finding decision updated: {decision_state_value}"
        )

    def _on_finding_correlate(
        self,
        finding_id: str,
        evidence_id: str,
        rationale: str,
        confidence: float,
    ):
        if self.current_case is None:
            return

        self.case_service.correlate_finding_to_evidence(
            self.current_case.id,
            finding_id,
            evidence_id,
            rationale=rationale,
            support_confidence=confidence,
        )
        self._reload_case_after_convergence_update("Finding correlated to evidence")

    def _on_finding_promote(self, finding_id: str, rationale: str, confidence: float):
        if self.current_case is None:
            return

        evidence, _, created = self.case_service.promote_finding_to_evidence(
            self.current_case.id,
            finding_id,
            rationale=rationale,
            support_confidence=confidence,
        )
        if created:
            msg = f"Finding promoted to evidence: {evidence.id[:8]}"
        else:
            msg = "Finding already promoted; linked to existing evidence"
        self._reload_case_after_convergence_update(msg)

    def _on_evidence_attachment(self, evidence_id: str, file_path: str, provenance_note: str):
        if self.current_case is None:
            return

        self.case_service.attach_file_to_evidence(
            self.current_case.id,
            evidence_id,
            file_path,
            provenance_note=provenance_note,
        )
        self._reload_case_after_convergence_update("Evidence attachment saved")

    def _on_public_media_capture(
        self,
        finding_id: str,
        evidence_id: str,
        source_url: str,
        media_title: str,
        media_type: str,
        provenance_note: str,
        screenshot_path: str,
    ):
        if self.current_case is None:
            return

        self.case_service.capture_public_media_evidence(
            self.current_case.id,
            source_url,
            finding_id=finding_id,
            evidence_id=evidence_id or None,
            media_title=media_title,
            media_type=media_type,
            provenance_note=provenance_note,
            screenshot_file_path=screenshot_path,
        )
        self._reload_case_after_convergence_update("Public-media evidence capture saved")

    def _reload_case_after_convergence_update(self, status_message: str) -> None:
        if self.current_case is None:
            return

        self.current_case = self.case_service.get_case(self.current_case.id)
        self.findings_panel.load_case(self.current_case)
        self.report_panel.load_case(self.current_case)
        self.lead_workspace_panel.load_case(self.current_case)
        self.search_builder_panel.load_case(self.current_case)
        self.entity_research_panel.load_case(self.current_case)
        self.timeline_panel.load_case(self.current_case)
        self.case_panel._populate_detail(self.current_case)
        self.status_bar.showMessage(status_message)

    def _populate_case_detail(self, case: Case) -> None:
        """Refresh the case detail view inside CasePanel for the given case."""
        self.case_panel._populate_detail(case)

    def _on_new_case_sidebar(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Case", "Case name:")
        if ok and name.strip():
            self.case_service.create_case(name.strip())
            self._refresh_sidebar()
            self.case_panel.refresh_cases()

    def _run_investigation(self):
        target_type = self.inv_type_combo.currentData()
        value = self.inv_value_input.text().strip()
        if not value:
            self.status_bar.showMessage("Please enter a target value.")
            return

        # Persist the target to the active case so findings reference a real target ID
        if self.current_case is not None:
            existing = next(
                (
                    t for t in self.current_case.targets
                    if t.type == target_type and t.value == value
                ),
                None,
            )
            if existing:
                target = existing
            else:
                target = self.case_service.add_target(self.current_case.id, target_type, value)
                self.current_case = self.case_service.get_case(self.current_case.id)
                self.case_panel.refresh_cases()
                self._populate_case_detail(self.current_case)
        else:
            # No active case — run without persisting
            target = Target(type=target_type, value=value)

        selected = [n for n, cb in self.adapter_checks.items() if cb.isChecked()]
        self._start_worker(target, adapter_names=selected)

    def _run_preset(self, preset: InvestigationPreset):
        target_type = self.inv_type_combo.currentData()
        value = self.inv_value_input.text().strip()
        if not value:
            self.status_bar.showMessage("Please enter a target value.")
            return

        if self.current_case is not None:
            existing = next(
                (
                    t for t in self.current_case.targets
                    if t.type == target_type and t.value == value
                ),
                None,
            )
            if existing:
                target = existing
            else:
                target = self.case_service.add_target(self.current_case.id, target_type, value)
                self.current_case = self.case_service.get_case(self.current_case.id)
                self.case_panel.refresh_cases()
                self._populate_case_detail(self.current_case)
        else:
            target = Target(type=target_type, value=value)

        self._start_worker(target, preset=preset)

    def _start_worker(self, target: Target, preset=None, adapter_names=None):
        self.results_table.setRowCount(0)
        self.progress_widget.reset()
        self.start_btn.setEnabled(False)

        self.worker = InvestigationWorker(
            self.investigation_service,
            target,
            preset=preset,
            adapter_names=adapter_names,
            case_id=self.current_case.id if self.current_case is not None else None,
        )
        self.worker.finding_found.connect(self._on_finding)
        self.worker.progress.connect(lambda pct, msg: self.progress_widget.update(pct, msg))
        self.worker.finished.connect(self._on_investigation_finished)
        self.worker.error.connect(lambda msg: self.status_bar.showMessage(f"Error: {msg}"))
        self.worker.finished.connect(lambda _: self.start_btn.setEnabled(True))
        self.worker.start()

    def _on_finding(self, finding: Finding):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(finding.severity.value))
        self.results_table.setItem(row, 1, QTableWidgetItem(finding.finding_type.value))
        self.results_table.setItem(row, 2, QTableWidgetItem(finding.title))
        self.results_table.setItem(row, 3, QTableWidgetItem(finding.adapter_name))
        self.results_table.setItem(row, 4, QTableWidgetItem(finding.description[:80]))

    def _on_investigation_finished(self, result: dict):
        findings: list[Finding] = result.get("findings", [])
        adapter_runs = result.get("adapter_runs", [])
        failed_runs = sum(1 for run in adapter_runs if run.status == AdapterRunStatus.FAILED)
        successful_runs = sum(1 for run in adapter_runs if run.status == AdapterRunStatus.COMPLETE)

        if self.current_case is not None:
            self.case_service.save_adapter_runs(self.current_case.id, adapter_runs)
            added, skipped = self.case_service.add_findings_batch(self.current_case.id, findings)
            msg = (
                f"Investigation complete — {len(added)} new finding(s), "
                f"{successful_runs}/{len(adapter_runs)} adapter(s) succeeded"
            )
            if failed_runs:
                msg += f"  ({failed_runs} failed)"
            if skipped:
                msg += f"  ({skipped} duplicate(s) skipped)"
            self.status_bar.showMessage(msg)
            # Reload case and refresh all dependent panels
            self.current_case = self.case_service.get_case(self.current_case.id)
            self.search_builder_panel.load_case(self.current_case)
            self.entity_research_panel.load_case(self.current_case)
            self.lead_workspace_panel.load_case(self.current_case)
            self.findings_panel.load_case(self.current_case)
            self.graph_panel.load_case(self.current_case)
            self.timeline_panel.load_case(self.current_case)
            self.report_panel.load_case(self.current_case)
            self.case_panel._populate_detail(self.current_case)
        else:
            msg = (
                f"Investigation complete — {len(findings)} finding(s), "
                f"{successful_runs}/{len(adapter_runs)} adapter(s) succeeded"
            )
            if failed_runs:
                msg += f"  ({failed_runs} failed)"
            self.status_bar.showMessage(
                msg + "  (select a case to save)"
            )

    def _open_tab_by_name(self, tab_name: str) -> None:
        for idx in range(self.tabs.count()):
            if self.tabs.tabText(idx) == tab_name:
                self.tabs.setCurrentIndex(idx)
                return

    def _on_research_pivot_requested(self, entity_type: str, value: str) -> None:
        self._open_tab_by_name("Entity Research")
        self.entity_research_panel.seed_pivot(entity_type, value)

    def _on_email_pivot_requested(self, value: str) -> None:
        self._open_tab_by_name("Search Builder")
        self.search_builder_panel.seed_email_pivot(value)

    def _on_username_pivot_requested(self, value: str) -> None:
        self._open_tab_by_name("Search Builder")
        self.search_builder_panel.seed_username_pivot(value)

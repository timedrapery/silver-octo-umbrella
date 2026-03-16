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
from app.gui.findings_panel import FindingsPanel
from app.gui.graph_panel import GraphPanel
from app.gui.report_panel import ReportPanel
from app.gui.widgets.progress_widget import ProgressWidget
from app.gui.workers import InvestigationWorker
from app.models.case import Case, Finding, InvestigationPreset, Target, TargetType
from app.services.case_service import CaseService
from app.services.graph_service import GraphService
from app.services.investigation_service import InvestigationService
from app.services.report_service import ReportService
from app.storage.database import Database

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #e2e8f0;
    font-family: "Segoe UI", "SF Pro", sans-serif;
}
QMenuBar { background: #2d2d3f; color: #e2e8f0; }
QMenuBar::item:selected { background: #7c6af7; }
QMenu { background: #2d2d3f; color: #e2e8f0; border: 1px solid #444; }
QMenu::item:selected { background: #7c6af7; }
QTabWidget::pane { border: 1px solid #444; background: #1e1e2e; }
QTabBar::tab { background: #2d2d3f; color: #a0aec0; padding: 8px 16px; border-radius: 4px 4px 0 0; }
QTabBar::tab:selected { background: #7c6af7; color: white; }
QListWidget { background: #2d2d3f; border: 1px solid #444; border-radius: 6px; }
QListWidget::item:selected { background: #7c6af7; }
QPushButton {
    background: #2d2d3f; color: #e2e8f0; border: 1px solid #555;
    padding: 6px 14px; border-radius: 6px;
}
QPushButton:hover { background: #3d3d5f; }
QPushButton#startBtn { background: #7c6af7; color: white; font-weight: bold; padding: 10px; }
QPushButton#startBtn:hover { background: #9b8bff; }
QLineEdit, QComboBox, QTextEdit {
    background: #2d2d3f; color: #e2e8f0; border: 1px solid #555;
    border-radius: 4px; padding: 4px 8px;
}
QGroupBox { border: 1px solid #444; border-radius: 6px; margin-top: 8px; color: #a0aec0; padding-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; }
QTableWidget { background: #2d2d3f; border: 1px solid #444; gridline-color: #444; }
QHeaderView::section { background: #3d3d5f; color: #e2e8f0; padding: 4px; }
QProgressBar { background: #2d2d3f; border: 1px solid #555; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background: #7c6af7; border-radius: 4px; }
QSplitter::handle { background: #444; }
QStatusBar { background: #2d2d3f; color: #9ca3af; }
QScrollBar:vertical { background: #2d2d3f; width: 8px; }
QScrollBar::handle:vertical { background: #555; border-radius: 4px; }
QCheckBox { color: #e2e8f0; }
QRadioButton { color: #e2e8f0; }
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
        self.resize(1200, 800)

    def _setup_services(self):
        self.case_service = CaseService(self.db)
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
        sidebar.setFixedWidth(200)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(4, 4, 4, 4)
        sb_label = QLabel("Cases")
        sb_label.setStyleSheet("font-weight: bold; color: #7c6af7; padding: 4px;")
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
        self.findings_panel = FindingsPanel()
        self.graph_panel = GraphPanel(self.graph_service)
        self.report_panel = ReportPanel(self.report_service)

        self.tabs.addTab(self.case_panel, "Cases")
        self.tabs.addTab(self._build_investigation_tab(), "Investigation")
        self.tabs.addTab(self.findings_panel, "Findings")
        self.tabs.addTab(self.graph_panel, "Graph")
        self.tabs.addTab(self.report_panel, "Reports")
        splitter.addWidget(self.tabs)
        splitter.setSizes([200, 1000])

        self._refresh_sidebar()

    def _build_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction("New Case", self._on_new_case_sidebar)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        menu_bar.addMenu("View")
        menu_bar.addMenu("Help")

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

    def _on_sidebar_case_changed(self, row: int):
        if row < 0 or row >= len(self._sidebar_cases):
            return
        case = self._sidebar_cases[row]
        self._on_case_selected(case)

    def _on_case_selected(self, case: Case):
        self.current_case = case
        self.graph_panel.load_case(case)
        self.report_panel.load_case(case)
        self.findings_panel.load_findings(case.findings)
        self.status_bar.showMessage(f"Active case: {case.name}")

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
            self.investigation_service, target, preset=preset, adapter_names=adapter_names
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

    def _on_investigation_finished(self, findings: list[Finding]):
        if self.current_case is not None:
            added, skipped = self.case_service.add_findings_batch(self.current_case.id, findings)
            msg = f"Investigation complete — {len(added)} new finding(s)"
            if skipped:
                msg += f"  ({skipped} duplicate(s) skipped)"
            self.status_bar.showMessage(msg)
            # Reload case and refresh all dependent panels
            self.current_case = self.case_service.get_case(self.current_case.id)
            self.findings_panel.load_findings(self.current_case.findings)
            self.graph_panel.load_case(self.current_case)
            self.report_panel.load_case(self.current_case)
        else:
            self.status_bar.showMessage(
                f"Investigation complete — {len(findings)} finding(s)  (select a case to save)"
            )

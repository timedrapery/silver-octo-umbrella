from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.models.case import Case, Finding, Severity

SEVERITY_COLORS = {
    "INFO": "#6b7280",
    "LOW": "#3b82f6",
    "MEDIUM": "#f59e0b",
    "HIGH": "#ef4444",
    "CRITICAL": "#dc2626",
}


class FindingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.findings: list[Finding] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Filter bar
        filter_row = QHBoxLayout()
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types")
        for ft in ["DNS", "CERTIFICATE", "HTTP", "SOCIAL", "SUBDOMAIN", "METADATA", "GENERIC"]:
            self.type_filter.addItem(ft)
        self.type_filter.currentTextChanged.connect(self._apply_filters)

        self.severity_filter = QComboBox()
        self.severity_filter.addItem("All Severities")
        for s in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            self.severity_filter.addItem(s)
        self.severity_filter.currentTextChanged.connect(self._apply_filters)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search findings...")
        self.search_input.textChanged.connect(self._apply_filters)

        filter_row.addWidget(QLabel("Type:"))
        filter_row.addWidget(self.type_filter)
        filter_row.addWidget(QLabel("Severity:"))
        filter_row.addWidget(self.severity_filter)
        filter_row.addWidget(self.search_input, 1)
        layout.addLayout(filter_row)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Severity", "Type", "Title", "Adapter", "Collected At"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.currentRowChanged.connect(self._on_row_selected)
        splitter.addWidget(self.table)

        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setMaximumHeight(200)
        splitter.addWidget(self.detail_view)

        layout.addWidget(splitter)

    def load_findings(self, findings: list[Finding]):
        self.findings = findings
        self._apply_filters()

    def _apply_filters(self):
        type_f = self.type_filter.currentText()
        sev_f = self.severity_filter.currentText()
        search = self.search_input.text().lower()

        filtered = [
            f for f in self.findings
            if (type_f == "All Types" or f.finding_type.value == type_f)
            and (sev_f == "All Severities" or f.severity.value == sev_f)
            and (not search or search in f.title.lower() or search in f.description.lower())
        ]

        self.table.setRowCount(0)
        for finding in filtered:
            row = self.table.rowCount()
            self.table.insertRow(row)
            sev_item = QTableWidgetItem(finding.severity.value)
            color = SEVERITY_COLORS.get(finding.severity.value, "#ffffff")
            sev_item.setForeground(Qt.GlobalColor.white)
            sev_item.setBackground(QColor(color))
            self.table.setItem(row, 0, sev_item)
            self.table.setItem(row, 1, QTableWidgetItem(finding.finding_type.value))
            self.table.setItem(row, 2, QTableWidgetItem(finding.title))
            self.table.setItem(row, 3, QTableWidgetItem(finding.adapter_name))
            self.table.setItem(row, 4, QTableWidgetItem(finding.collected_at.strftime("%Y-%m-%d %H:%M")))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, finding)

    def _on_row_selected(self, row: int):
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        finding: Finding = item.data(Qt.ItemDataRole.UserRole)
        if finding:
            import json
            detail = (
                f"Title: {finding.title}\n"
                f"Type: {finding.finding_type.value}\n"
                f"Severity: {finding.severity.value}\n"
                f"Adapter: {finding.adapter_name}\n"
                f"Source: {finding.source_url}\n"
                f"Description:\n{finding.description}\n\n"
                f"Data:\n{json.dumps(finding.data, indent=2)}"
            )
            self.detail_view.setPlainText(detail)

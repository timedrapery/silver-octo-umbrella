import os
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app.models.case import Case
from app.services.report_service import ReportService


class ReportPanel(QWidget):
    def __init__(self, report_service: ReportService, parent=None):
        super().__init__(parent)
        self.report_service = report_service
        self.current_case: Case | None = None
        self._last_path: str = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        fmt_group = QGroupBox("Report Format")
        fmt_layout = QHBoxLayout(fmt_group)
        self.btn_group = QButtonGroup(self)
        self.html_radio = QRadioButton("HTML")
        self.json_radio = QRadioButton("JSON")
        self.csv_radio = QRadioButton("CSV")
        self.html_radio.setChecked(True)
        for rb in (self.html_radio, self.json_radio, self.csv_radio):
            self.btn_group.addButton(rb)
            fmt_layout.addWidget(rb)
        layout.addWidget(fmt_group)

        btn_row = QHBoxLayout()
        self.gen_btn = QPushButton("Generate Report")
        self.gen_btn.clicked.connect(self._on_generate)
        self.open_btn = QPushButton("Open Report")
        self.open_btn.clicked.connect(self._on_open)
        btn_row.addWidget(self.gen_btn)
        btn_row.addWidget(self.open_btn)
        layout.addLayout(btn_row)

        self.path_label = QLabel("No report generated yet.")
        self.path_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addWidget(self.path_label)
        layout.addStretch()

    def load_case(self, case: Case):
        self.current_case = case

    def _on_generate(self):
        if self.current_case is None:
            return
        if self.html_radio.isChecked():
            ext, suffix = "HTML Files (*.html)", ".html"
        elif self.json_radio.isChecked():
            ext, suffix = "JSON Files (*.json)", ".json"
        else:
            ext, suffix = "CSV Files (*.csv)", ".csv"

        path, _ = QFileDialog.getSaveFileName(self, "Save Report", f"report_{self.current_case.id[:8]}{suffix}", ext)
        if not path:
            return

        if self.html_radio.isChecked():
            self.report_service.generate_html(self.current_case, path)
        elif self.json_radio.isChecked():
            self.report_service.generate_json(self.current_case, path)
        else:
            self.report_service.generate_csv(self.current_case, path)

        self._last_path = path
        self.path_label.setText(f"Saved: {path}")

    def _on_open(self):
        if self._last_path and Path(self._last_path).exists():
            if os.name == "nt":
                os.startfile(self._last_path)  # noqa: S606
            else:
                subprocess.run(["xdg-open", self._last_path], check=False)

from pathlib import Path
import tempfile

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

from app.models.case import Case
from app.services.graph_service import GraphService


class GraphPanel(QWidget):
    def __init__(self, graph_service: GraphService, parent=None):
        super().__init__(parent)
        self.graph_service = graph_service
        self.current_case: Case | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Graph")
        self.refresh_btn.clicked.connect(self._refresh)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()

        legend = QHBoxLayout()
        for label, color in [("Case", "#7c6af7"), ("Target", "#4ade80"), ("Finding", "#f97316")]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 18px;")
            text = QLabel(label)
            text.setStyleSheet("color: #e2e8f0;")
            legend.addWidget(dot)
            legend.addWidget(text)
        legend.addStretch()

        layout.addLayout(toolbar)
        layout.addLayout(legend)

        if HAS_WEBENGINE:
            self.web_view = QWebEngineView()
            layout.addWidget(self.web_view)
        else:
            placeholder = QLabel("Install PySide6-WebEngine for graph visualization.")
            placeholder.setStyleSheet("color: #9ca3af;")
            self.web_view = None
            layout.addWidget(placeholder)

    def load_case(self, case: Case):
        self.current_case = case

    def _refresh(self):
        if self.current_case is None or self.web_view is None:
            return
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            tmp_path = f.name
        self.graph_service.generate_pyvis_html(self.current_case, tmp_path)
        self.web_view.load(__import__("PySide6.QtCore", fromlist=["QUrl"]).QUrl.fromLocalFile(tmp_path))

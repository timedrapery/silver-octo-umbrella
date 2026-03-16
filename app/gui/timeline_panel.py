from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.case import Case
from app.services.case_service import CaseService
from app.services.timeline_service import TimelineCategory, TimelineEvent


class TimelinePanel(QWidget):
    def __init__(self, case_service: CaseService, parent=None):
        super().__init__(parent)
        self.case_service = case_service
        self.current_case: Case | None = None
        self.events: list[TimelineEvent] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()
        self.total_label = QLabel("Events: 0")
        self.recent_label = QLabel("Most Recent: -")
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories", None)
        for category in TimelineCategory:
            self.category_filter.addItem(category.value, category.value)
        self.category_filter.currentIndexChanged.connect(self._render_events)

        for label in [self.total_label, self.recent_label]:
            label.setStyleSheet("padding: 4px 8px; border: 1px solid #444; border-radius: 4px;")
            top_row.addWidget(label)

        top_row.addWidget(QLabel("Category"))
        top_row.addWidget(self.category_filter)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time", "Category", "Type", "Summary"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.currentCellChanged.connect(self._on_row_selected)
        layout.addWidget(self.table)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(160)
        layout.addWidget(self.detail)

    def load_case(self, case: Case) -> None:
        self.current_case = case
        self.events = self.case_service.get_case_timeline(case.id)
        self._render_events()

    def _render_events(self) -> None:
        selected_category = self.category_filter.currentData()
        filtered = self.events
        if selected_category:
            filtered = [event for event in self.events if event.category.value == selected_category]

        self.table.setRowCount(0)
        for event in filtered:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(event.occurred_at.strftime("%Y-%m-%d %H:%M:%S")))
            self.table.setItem(row, 1, QTableWidgetItem(event.category.value))
            self.table.setItem(row, 2, QTableWidgetItem(event.event_type))
            self.table.setItem(row, 3, QTableWidgetItem(event.summary))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, event.model_dump(mode="json"))

        self.total_label.setText(f"Events: {len(filtered)}")
        recent = filtered[0].occurred_at.strftime("%Y-%m-%d %H:%M") if filtered else "-"
        self.recent_label.setText(f"Most Recent: {recent}")

        if filtered:
            self.table.selectRow(0)
        else:
            self.detail.setPlainText("")

    def _on_row_selected(self, row: int, _column: int, _prev_row: int, _prev_col: int) -> None:
        if row < 0:
            return

        item = self.table.item(row, 0)
        if item is None:
            return

        payload = item.data(Qt.ItemDataRole.UserRole) or {}
        metadata = payload.get("metadata") or {}

        details = [
            f"Time: {payload.get('occurred_at', '-')}",
            f"Category: {payload.get('category', '-')}",
            f"Type: {payload.get('event_type', '-')}",
            f"Summary: {payload.get('summary', '-')}",
            f"Source: {payload.get('source_type', '-')}/{payload.get('source_id', '-')}",
        ]

        if metadata:
            details.append("Metadata:")
            for key, value in metadata.items():
                details.append(f"  - {key}: {value}")

        self.detail.setPlainText("\n".join(details))

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal

from app.gui.widgets.target_input import TargetInputWidget
from app.models.case import Case, CaseStatus
from app.services.case_service import CaseService


class CasePanel(QWidget):
    case_selected = Signal(object)  # Case

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
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.desc_label)
        right_layout.addWidget(info_group)

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
        self.targets_list.clear()
        for t in case.targets:
            self.targets_list.addItem(f"[{t.type.value}] {t.value}")
        self.notes_list.clear()
        for n in case.notes:
            self.notes_list.addItem(n.content[:80])

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

    def _on_add_target(self, target_type, value):
        if self.current_case is None:
            return
        self.case_service.add_target(self.current_case.id, target_type, value)
        self.current_case = self.case_service.get_case(self.current_case.id)
        self._populate_detail(self.current_case)

    def _on_add_note(self):
        if self.current_case is None:
            return
        content = self.note_input.text().strip()
        if content:
            self.case_service.add_note(self.current_case.id, content)
            self.note_input.clear()
            self.current_case = self.case_service.get_case(self.current_case.id)
            self._populate_detail(self.current_case)

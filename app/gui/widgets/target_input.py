from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPushButton, QWidget

from app.models.case import TargetType


class TargetInputWidget(QWidget):
    target_added = Signal(object, str)  # TargetType, value

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.type_combo = QComboBox()
        for t in TargetType:
            self.type_combo.addItem(t.value, t)

        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Enter target value...")

        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._on_add)

        layout.addWidget(self.type_combo)
        layout.addWidget(self.value_input, 1)
        layout.addWidget(self.add_btn)

    def _on_add(self):
        target_type = self.type_combo.currentData()
        value = self.value_input.text().strip()
        if value:
            self.target_added.emit(target_type, value)
            self.value_input.clear()

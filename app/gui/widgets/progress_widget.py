from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget


class ProgressWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #9ca3af; font-size: 12px;")

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

    def update(self, value: int, message: str = ""):
        self.progress_bar.setValue(value)
        if message:
            self.status_label.setText(message)

    def reset(self):
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")

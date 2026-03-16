from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from app.models.case import Finding, Severity

SEVERITY_COLORS = {
    Severity.INFO: "#6b7280",
    Severity.LOW: "#3b82f6",
    Severity.MEDIUM: "#f59e0b",
    Severity.HIGH: "#ef4444",
    Severity.CRITICAL: "#dc2626",
}


class FindingCard(QFrame):
    def __init__(self, finding: Finding, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("QFrame { background: #2d2d3f; border-radius: 6px; padding: 4px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        color = SEVERITY_COLORS.get(finding.severity, "#6b7280")
        badge = QLabel(finding.severity.value)
        badge.setStyleSheet(
            f"background: {color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;"
        )
        badge.setFixedHeight(20)

        type_label = QLabel(finding.finding_type.value)
        type_label.setStyleSheet("color: #a0aec0; font-size: 11px;")

        header.addWidget(badge)
        header.addWidget(type_label)
        header.addStretch()

        title_label = QLabel(finding.title)
        title_label.setStyleSheet("color: #e2e8f0; font-weight: bold;")
        title_label.setWordWrap(True)

        desc_label = QLabel(finding.description)
        desc_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        desc_label.setWordWrap(True)

        layout.addLayout(header)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)

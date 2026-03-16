import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication

from app.gui.main_window import MainWindow
from app.storage.database import Database
from app.services.case_service import CaseService


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("OSINT Research Platform")
    app.setOrganizationName("OSINT Tools")

    db = Database()
    db.initialize()

    window = MainWindow(db)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

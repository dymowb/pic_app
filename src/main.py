"""
pic_app — entry point.

Run with:
    python src/main.py
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("pic_app")
    app.setApplicationDisplayName("pic_app — Duplicate Photo Finder")
    app.setOrganizationName("pic_app")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

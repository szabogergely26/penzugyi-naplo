# about_dialog.py
# --------------------


import platform
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

APP_NAME = "Pénzügyi Napló"
APP_VERSION = "4.5"
BUILD_INFO = "Fejlesztés kezdete:\n2025. november"



class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Névjegy")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        title = QLabel(f"<h2>{APP_NAME}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel(f"Verzió: {APP_VERSION}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        build = QLabel(BUILD_INFO)
        build.setAlignment(Qt.AlignmentFlag.AlignCenter)


        sysinfo = QLabel(
            f"Python: {platform.python_version()}\nSQLite: {sqlite3.sqlite_version}"
        )
        sysinfo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        


        btn_close = QPushButton("Bezár")
        btn_close.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(version)
        layout.addSpacing(10)
        layout.addWidget(build)
        layout.addSpacing(10)
        layout.addWidget(sysinfo)
        layout.addSpacing(25)
        
        layout.addWidget(btn_close)

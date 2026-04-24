# version_info.py
# --------------------

import platform
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


APP_NAME = "Pénzügyi Napló"
APP_VERSION = "4.5"
APP_CHANNEL = "Stabil kiadás verzió"
BUILD_INFO = "2025. november – 2026. április"

VERSION_DESCRIPTION = """
<b>Fejlesztői verzió</b><br><br>

<b>Normál / PROD mód:</b><br>
Készre csiszolt funkciók, de még hosszabb távú tesztelés alatt állnak.<br><br>

<b>Fejlesztői mód:</b><br>
Friss újdonságok, kísérleti vagy félkész funkciók.
Hibák előfordulhatnak. Érzékeny adatok kezelésére nem ajánlott.<br><br>

<b>Stabil verzió</b><br><br>

<b>Normál / PROD mód:</b><br>
Hibátlan funkciók, hosszú távú használatra javasolt. Stabil.<br><br>

<b>Fejlesztői mód:</b><br>
Jövőbeni funkciók, még előfordulhatnak hibák.
"""


class VersionInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Verzió infók")
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(APP_NAME)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setTextFormat(Qt.TextFormat.PlainText)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        version = QLabel(f"Verzió: {APP_VERSION}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("font-size: 14px;")

        channel = QLabel(APP_CHANNEL)
        channel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        channel.setStyleSheet("font-size: 13px; font-weight: bold;")

        build = QLabel(f"Build időszak: <b>{BUILD_INFO}</b>")
        build.setAlignment(Qt.AlignmentFlag.AlignCenter)
        build.setStyleSheet("font-size: 13px;")

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)

        description = QLabel(VERSION_DESCRIPTION)
        description.setWordWrap(True)
        description.setTextFormat(Qt.TextFormat.RichText)
        description.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        description.setStyleSheet("font-size: 13px;")

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)

        sysinfo = QLabel(
            f"Python verzió: {platform.python_version()}\n"
            f"SQLite verzió: {sqlite3.sqlite_version}"
        )
        sysinfo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sysinfo.setStyleSheet("font-size: 12px;")

        btn_close = QPushButton("Bezár")
        btn_close.setFixedWidth(120)
        btn_close.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(channel)
        layout.addWidget(build)
        layout.addWidget(line)
        layout.addWidget(description)
        layout.addWidget(line2)
        layout.addWidget(sysinfo)
        layout.addSpacing(8)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLabel {
                color: #222;
            }
            QPushButton {
                padding: 6px 12px;
                min-height: 28px;
            }
        """)
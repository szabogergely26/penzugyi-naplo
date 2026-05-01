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
<b>Stabil verzió</b><br><br>

<b>Normál / PROD mód:</b><br>
Normál mód: Készre csiszolt, hosszabb távú használatra szánt funkciók.
A stabil ág célja a megbízható napi használat.<br><br>

PROD mód: Fejlesztés alatt álló funkciók kipróbálása.
Fejlesztés alatt álló funkciók stabilizálása.<br><br>

<b>Fejlesztői mód:</b><br>
Tesztelésre és jövőbeni funkciók kipróbálására szolgál.
Éles vagy érzékeny adatok kezelésére továbbra is a normál mód javasolt.<br><br><br>


<b>Modern Home téma:</b><br>
A stabil kiadásban is elérhető az új, kártyásabb kezdőoldali megjelenés.
A téma a Beállítások oldalon választható ki.<br><br>


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
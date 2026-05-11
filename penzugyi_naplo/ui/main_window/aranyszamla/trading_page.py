# /ui/main_window/aranyszamla/tranding_page.py
# ----------------------------------------------

# Kereskedés oldal: vétel/eladás lista placeholder

"""
Aranyszámla kereskedés oldal.

Feladata:
- később itt jelennek meg a nemesfémes műveletek
- vétel / eladás logika
- gramm, árfolyam, összeg adatok listázása

Kezdetben:
- egyszerű placeholder oldal
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class AranyszamlaTradingPage(QWidget):
    """Az Aranyszámla modul kereskedés oldala."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("aranyszamlaTradingPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(16)

        title = QLabel("Kereskedés")
        title.setObjectName("aranyszamlaPageTitle")

        placeholder = QLabel(
            "Itt jelennek majd meg az arany vétel / eladás műveletek.\n\n"
            "Később innen indulhat a vásárlás és eladás varázsló."
        )
        placeholder.setObjectName("aranyszamlaPlaceholderText")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(placeholder, 1)
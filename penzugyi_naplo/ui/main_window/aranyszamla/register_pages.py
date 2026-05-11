# penzugyi_naplo/ui/main_window/aranyszamla/register_pages.py
# ----------------------------------------------------------

"""
Aranyszámla modul oldalainak regisztrálása.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


def register_aranyszamla_pages(window) -> None:
    """
    Ideiglenes Aranyszámla kezdőoldal regisztrálása.
    """

    page = QWidget(window.page_stack)
    layout = QVBoxLayout(page)

    title = QLabel("Aranyszámla", page)
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setObjectName("pageTitle")

    subtitle = QLabel("Vétel / Eladás / Árfolyamok később kerülnek kialakításra.", page)
    subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

    layout.addStretch(1)
    layout.addWidget(title)
    layout.addWidget(subtitle)
    layout.addStretch(1)

    window.add_page("aranyszamla_home", page)
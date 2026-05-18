# penzugyi_naplo/ui/main_window/aranyszamla/register_pages.py

"""
Aranyszámla modul oldalainak regisztrálása.

Ez a modul felel azért, hogy az Aranyszámla nézet saját oldalai
bekerüljenek a MainWindow központi page_stack rendszerébe.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


def register_aranyszamla_pages(window) -> None:
    """
    Aranyszámla oldalak regisztrálása a főablakba.

    Első körben csak egy placeholder kezdőoldalt adunk hozzá.
    Később ide kerülhetnek:
    - Aranyszámla kezdőoldal
    - Vétel / Eladás oldal
    - Árfolyamok oldal
    - Diagramok oldal
    """
    page = QWidget()
    page.setObjectName("aranyszamlaHomePage")

    layout = QVBoxLayout(page)
    layout.setContentsMargins(32, 32, 32, 32)
    layout.setSpacing(16)

    title = QLabel("Aranyszámla")
    title.setObjectName("pageTitle")
    title.setAlignment(Qt.AlignmentFlag.AlignLeft)

    subtitle = QLabel(
        "Itt jelenik majd meg az Aranyszámla modul: vétel, eladás, "
        "árfolyamok és diagramok."
    )
    subtitle.setObjectName("pageSubtitle")
    subtitle.setWordWrap(True)

    layout.addWidget(title)
    layout.addWidget(subtitle)
    layout.addStretch(1)

    window.add_page("aranyszamla_home", page)
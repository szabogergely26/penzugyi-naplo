# /ui/main_window/aranyszamla/home_page.py
# -------------------------------------------

# Aranyszámla kezdő oldal: aranykupac + gramm + érték

"""
Aranyszámla kezdőoldal.

Feladata:
- az Aranyszámla modul nyitóképernyőjének megjelenítése
- aranykupac / aranytartalék jellegű vizuális blokk
- összes gramm és becsült érték megjelenítése

Később:
- valós adatok bekötése adatbázisból
- érték számítása aktuális árfolyam alapján
- finom animáció / látványelemek

"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class AranyszamlaHomePage(QWidget):
    """Az Aranyszámla modul kezdőoldala."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("aranyszamlaHomePage")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 32)
        main_layout.setSpacing(24)

        title = QLabel("Aranyszámla")
        title.setObjectName("aranyszamlaPageTitle")

        subtitle = QLabel("A nemesfém megtakarításod áttekintése")
        subtitle.setObjectName("aranyszamlaPageSubtitle")

        hero_card = QFrame()
        hero_card.setObjectName("aranyszamlaHeroCard")
        hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(36, 36, 36, 36)
        hero_layout.setSpacing(22)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        gold_icon = QLabel("🪙")
        gold_icon.setObjectName("aranyszamlaGoldIcon")
        gold_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        gold_title = QLabel("Aranytartalék")
        gold_title.setObjectName("aranyszamlaGoldTitle")
        gold_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        grams_label = QLabel("Összes készlet")
        grams_label.setObjectName("aranyszamlaInfoLabel")
        grams_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        grams_value = QLabel("0,000 g")
        grams_value.setObjectName("aranyszamlaMainValue")
        grams_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        estimated_label = QLabel("Becsült érték")
        estimated_label.setObjectName("aranyszamlaInfoLabel")
        estimated_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        estimated_value = QLabel("0 Ft")
        estimated_value.setObjectName("aranyszamlaSecondaryValue")
        estimated_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hero_layout.addWidget(gold_icon)
        hero_layout.addWidget(gold_title)
        hero_layout.addSpacing(8)
        hero_layout.addWidget(grams_label)
        hero_layout.addWidget(grams_value)
        hero_layout.addSpacing(12)
        hero_layout.addWidget(estimated_label)
        hero_layout.addWidget(estimated_value)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(hero_card, 1)
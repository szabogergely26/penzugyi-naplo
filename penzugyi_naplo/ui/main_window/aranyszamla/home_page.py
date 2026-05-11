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

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
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

        subtitle = QLabel("Arany megtakarításod egyszerű áttekintése")
        subtitle.setObjectName("aranyszamlaPageSubtitle")

        hero_card = QFrame()
        hero_card.setObjectName("aranyszamlaHeroCard")
        hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(42, 38, 42, 38)
        hero_layout.setSpacing(36)

        visual_box = QFrame()
        visual_box.setObjectName("aranyszamlaVisualBox")

        visual_layout = QVBoxLayout(visual_box)
        visual_layout.setContentsMargins(24, 24, 24, 24)
        visual_layout.setSpacing(12)
        visual_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        gold_icon = QLabel("🪙")
        gold_icon.setObjectName("aranyszamlaGoldIcon")
        gold_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        gold_caption = QLabel("Aranytartalék")
        gold_caption.setObjectName("aranyszamlaGoldCaption")
        gold_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)

        visual_layout.addStretch(1)
        visual_layout.addWidget(gold_icon)
        visual_layout.addWidget(gold_caption)
        visual_layout.addStretch(1)

        info_box = QFrame()
        info_box.setObjectName("aranyszamlaInfoBox")

        info_layout = QVBoxLayout(info_box)
        info_layout.setContentsMargins(28, 28, 28, 28)
        info_layout.setSpacing(18)

        section_title = QLabel("Jelenlegi állapot")
        section_title.setObjectName("aranyszamlaSectionTitle")

        grams_label = QLabel("Összes arany")
        grams_label.setObjectName("aranyszamlaInfoLabel")

        self.grams_value = QLabel("0,000 g")
        self.grams_value.setObjectName("aranyszamlaMainValue")

        estimated_label = QLabel("Becsült érték")
        estimated_label.setObjectName("aranyszamlaInfoLabel")

        self.estimated_value = QLabel("0 Ft")
        self.estimated_value.setObjectName("aranyszamlaSecondaryValue")

        hint = QLabel(
            "Az érték később a rögzített vásárlások, eladások és az aktuális "
            "aranyár alapján számolható."
        )
        hint.setObjectName("aranyszamlaHintText")
        hint.setWordWrap(True)

        info_layout.addWidget(section_title)
        info_layout.addSpacing(8)
        info_layout.addWidget(grams_label)
        info_layout.addWidget(self.grams_value)
        info_layout.addSpacing(10)
        info_layout.addWidget(estimated_label)
        info_layout.addWidget(self.estimated_value)
        info_layout.addStretch(1)
        info_layout.addWidget(hint)

        hero_layout.addWidget(visual_box, 2)
        hero_layout.addWidget(info_box, 3)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(hero_card, 1)
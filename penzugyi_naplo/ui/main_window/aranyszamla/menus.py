# penzugyi_naplo/ui/main_window/aranyszamla/menus.py
# --------------------------------------------------

"""
Aranyszámla modul menü- és ribbon-felépítése.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


def build_aranyszamla_menubar(window) -> None:
    """
    Aranyszámla modul klasszikus menüsorának felépítése.
    """

    menubar = window.menuBar()
    menubar.clear()

    file_menu = menubar.addMenu("Fájl")
    file_menu.addAction(window.act_gold_buy)
    file_menu.addAction(window.act_gold_sell)

    data_menu = menubar.addMenu("Adatok")
    data_menu.addAction(window.act_gold_rates)

    view_menu = menubar.addMenu("Nézet")
    view_menu.addAction("Áttekintés")

    help_menu = menubar.addMenu("Súgó")
    help_menu.addAction("Aranyszámla súgó")


def build_aranyszamla_ribbon(window) -> None:
    """
    Aranyszámla modul ideiglenes ribbonja.

    Később ezt érdemes ugyanarra a RibbonBar szerkezetre igazítani,
    mint amit a Likviditás modul használ.
    """

    ribbon = QWidget(window._right_panel)
    ribbon.setObjectName("ribbonBar")

    layout = QVBoxLayout(ribbon)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    title = QLabel("Aranyszámla", ribbon)
    title.setAlignment(Qt.AlignmentFlag.AlignLeft)

    btn_buy = QPushButton("Vétel", ribbon)
    btn_sell = QPushButton("Eladás", ribbon)
    btn_rates = QPushButton("Árfolyamok", ribbon)

    layout.addWidget(title)
    layout.addWidget(btn_buy)
    layout.addWidget(btn_sell)
    layout.addWidget(btn_rates)

    window.ribbon = ribbon
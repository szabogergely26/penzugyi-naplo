# penzugyi_naplo/ui/main_window/aranyszamla/actions.py
# --------------------------------------------------

"""
Aranyszámla modul action-jeinek létrehozása.

Első körben csak váz, hogy a MainWindow modulfüggő menü/ribbon
felépítése később tisztán tudjon dolgozni.
"""

from __future__ import annotations

from PySide6.QtGui import QAction


def create_aranyszamla_actions(window) -> None:
    """
    Aranyszámla modulhoz tartozó QAction objektumok létrehozása.

    A window paraméter maga a MainWindow példány.
    """

    window.act_gold_buy = QAction("Vétel", window)
    window.act_gold_sell = QAction("Eladás", window)
    window.act_gold_rates = QAction("Árfolyamok", window)
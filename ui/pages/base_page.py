# - ui/pages/base_page.py
# ------------------------------


"""
Közös alap oldal osztály (BasePage) az összes UI oldal számára
(ui/pages/base_page.py).

Egységes year-kontraktust ad: MainWindow évváltáskor set_year(year)-t hív.
Az oldalak felülírhatják a set_year()-t és ennek alapján frissíthetik a nézetüket.

Topology (UI):
    MainWindow
      └─ QStackedWidget (pages)
           └─ BasePage  ← this (ősosztály)
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget


class BasePage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._active_year: int | None = None

    def set_year(self, year: int) -> None:
        """MainWindow hívja évváltáskor. Oldal szinten felülírható."""
        self._active_year = year

    def active_year(self) -> int | None:
        return self._active_year

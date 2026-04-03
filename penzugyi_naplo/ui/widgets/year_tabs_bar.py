# pénzügyi_napló/ui/widgets/year_tabs_bar.py
# - Egyszerű év választó "tab" sáv a bal oldalon.

"""
Bal oldali év-választó tab sáv (YearTabsBar) az év-alapú navigációhoz.

Felelősség:
    - évek megjelenítése és aktív év kezelése
    - kattintásra kiválasztás és jelzés: yearChanged(int)

Nem felelőssége:
    - oldalak újratöltése / DB műveletek (ezt a hívó kezeli)

UI/Theme:
    - QSS-re épít (objectName/property), Office/modern megjelenés stílusból jön
    - aktív állapot: setProperty("active", ...) + polish/unpolish

Megjegyzés:
    - set_years() jelenleg tudatosan nincs implementálva (NotImplementedError).
"""


# ------ Importok --------

from __future__ import annotations

from typing import Iterable, List, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# - Importok vége -


class YearTabsBar(QWidget):
    yearChanged = Signal(int)

    def __init__(self, years: Iterable[int], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._years: List[int] = list(years)
        self._buttons: dict[int, QPushButton] = {}
        self._active_year: Optional[int] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Bal oldali "tabs"
        for y in self._years:
            btn = QPushButton(str(y))
            btn.setObjectName("yearTabButton")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)  # egyszerre csak 1 legyen aktív
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.clicked.connect(
                lambda checked, year=y: self.set_active_year(year, emit=True)
            )
            layout.addWidget(btn)
            self._buttons[y] = btn

        layout.addStretch(1)

        # Opció: jobb oldali hely későbbi elemeknek (pl. gyors kereső, szűrő ikon)
        # self._right_area = QWidget(self)
        # layout.addWidget(self._right_area)

        # Alap kiválasztás: első év
        if self._years:
            self.set_active_year(self._years[0], emit=False)

    def active_year(self) -> Optional[int]:
        return self._active_year

    def set_active_year(self, year: int, *, emit: bool = True) -> None:
        if year not in self._buttons:
            return

        self._active_year = year
        self._buttons[year].setChecked(True)

        # Objektumnév / property a QSS-hez (aktív tab kiemelés)
        for y, b in self._buttons.items():
            b.setProperty("active", y == year)
            b.style().unpolish(b)
            b.style().polish(b)

        if emit:
            self.yearChanged.emit(year)

    def set_years(self, years: Iterable[int]) -> None:
        """
        Később, ha dinamikus évlista kell (pl. DB-ből), bővíthető:
        - egyszerűség kedvéért most nem implementáljuk az újraépítést.
        """
        self._years = list(years)
        # (ha kell, újraépítjük a gombokat)
        raise NotImplementedError("Dynamic year list not implemented yet.")

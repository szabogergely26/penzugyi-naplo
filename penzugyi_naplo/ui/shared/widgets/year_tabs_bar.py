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
    allYearsSelected = Signal()

    def __init__(self, years: Iterable[int], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._years: List[int] = list(years)
        self._buttons: dict[int, QPushButton] = {}
        self._active_year: Optional[int] = None

        self._all_years_active = False
        self._all_years_button: Optional[QPushButton] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # "Minden év" tab
        self._all_years_button = QPushButton("Minden év")
        self._all_years_button.setObjectName("yearTabButton")
        self._all_years_button.setCheckable(True)
        self._all_years_button.setAutoExclusive(True)
        self._all_years_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._all_years_button.clicked.connect(
            lambda checked: self.set_all_years_active(emit=True)
        )
        layout.addWidget(self._all_years_button)


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
        self._all_years_active = False

        if self._all_years_button is not None:
            self._all_years_button.setChecked(False)
            self._all_years_button.setProperty("active", False)
            self._all_years_button.style().unpolish(self._all_years_button)
            self._all_years_button.style().polish(self._all_years_button)

        self._buttons[year].setChecked(True)

        # Objektumnév / property a QSS-hez (aktív tab kiemelés)
        for y, b in self._buttons.items():
            b.setProperty("active", y == year)
            b.style().unpolish(b)
            b.style().polish(b)

        if emit:
            self.yearChanged.emit(year)
    
    def set_all_years_active(self, *, emit: bool = True) -> None:
        """
        A "Minden év" nézet aktívvá tétele.

        Ilyenkor nincs konkrét aktív év, a hívó oldalnak minden év
        tranzakcióját kell megjelenítenie.
        """
        self._active_year = None
        self._all_years_active = True

        if self._all_years_button is not None:
            self._all_years_button.setChecked(True)
            self._all_years_button.setProperty("active", True)
            self._all_years_button.style().unpolish(self._all_years_button)
            self._all_years_button.style().polish(self._all_years_button)

        for _, button in self._buttons.items():
            button.setProperty("active", False)
            button.style().unpolish(button)
            button.style().polish(button)

        if emit:
            self.allYearsSelected.emit()

    def set_years(self, years: Iterable[int]) -> None:
        """
        Évlista dinamikus újraépítése.

        Import / restore / reset után használható, amikor új évek kerülnek
        az adatbázisba.
        """
        new_years = list(years)

        layout = self.layout()

        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()

                if widget is not None:
                    widget.deleteLater()

        self._years = new_years
        self._buttons.clear()
        self._active_year = None
        self._all_years_active = False
        self._all_years_button = None

        if layout is None:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 8, 12, 8)
            layout.setSpacing(8)



        # "Minden év" tab
        self._all_years_button = QPushButton("Minden év")
        self._all_years_button.setObjectName("yearTabButton")
        self._all_years_button.setCheckable(True)
        self._all_years_button.setAutoExclusive(True)
        self._all_years_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._all_years_button.clicked.connect(
            lambda checked: self.set_all_years_active(emit=True)    
        )
        layout.addWidget(self._all_years_button)











        for y in self._years:
            btn = QPushButton(str(y))
            btn.setObjectName("yearTabButton")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.clicked.connect(
                lambda checked, year=y: self.set_active_year(year, emit=True)
            )
            layout.addWidget(btn)
            self._buttons[y] = btn

        layout.addStretch(1)

        if self._years:
            self.set_active_year(self._years[0], emit=False)
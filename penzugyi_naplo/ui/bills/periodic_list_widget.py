# - penzugyi_naplo/ui/bills/periodic_list_widget.py
# ---------------------------------------------------

"""
    Időszakos sorok:
    Időszak | Összeg


Időszakos tételek listázó widget (Időszak | Összeg)


BillCard belső tartalmaként használjuk (periodic típus). Csak UI render, nincs DB/üzleti logika.

Topology (UI):
    MainWindow
      └─ BillsPage (ui/bills/bills_page.py)
           └─ BillCard (ui/bills/bill_card.py)
                ├─ MonthlyGridWidget (ui/bills/monthly_grid_widget.py)
                └─ PeriodicListWidget  ← aktuális

"""


# -------- Importok -------

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from penzugyi_naplo.ui.bills.bill_models import PeriodicAmount

# - Importek vége ------


class PeriodicListWidget(QWidget):
    def __init__(
        self, items: list[PeriodicAmount], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("periodicList")

        lay = QGridLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(6)

        lay.addWidget(self._cell("Időszak", header=True), 0, 0)
        lay.addWidget(self._cell("Összeg", header=True, align=Qt.AlignRight), 0, 1)

        for idx, it in enumerate(items, start=1):
            period = f"{it.start} – {it.end}"
            lay.addWidget(self._cell(period), idx, 0)
            lay.addWidget(
                self._cell(self._fmt_huf(it.amount), align=Qt.AlignRight), idx, 1
            )

    def _cell(
        self, text: str, *, header: bool = False, align: Qt.AlignmentFlag = Qt.AlignLeft
    ) -> QLabel:
        lab = QLabel(text)
        lab.setProperty("cell", True)
        if header:
            lab.setProperty("cellHeader", True)
        lab.setAlignment(align | Qt.AlignVCenter)
        lab.setWordWrap(False)
        return lab

    @staticmethod
    def _fmt_huf(amount: float) -> str:
        s = f"{amount:,.0f}".replace(",", " ")
        return f"{s} Ft"

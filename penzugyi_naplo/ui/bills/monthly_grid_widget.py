# - penzugyi_naplo/ui/bills/monthly_grid_widget.py
# ---------------------------------------------------


"""
Havi rács widget számlákhoz: 2 oszlopos megjelenítés (Hónap | Fizetett összeg)
(ui/bills/monthly_grid_widget.py).

BillCard belső tartalmaként használjuk (monthly típus). Csak UI render, nincs DB/üzleti logika.


MainWindow
 └── BillsPage (ui/bills/bills_page.py)
       └── BillCard (ui/bills/bill_card.py)
             ├── MonthlyGridWidget      ← EZ
             └── PeriodicListWidget


Ez a widget adja a kártyán belüli megjelenést:

Január     12 000
Február    12 000
Március    15 000

"""


# ------- Importok -------

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from penzugyi_naplo.ui.bills.bill_models import MonthlyAmount

# --- Importok vége ------


HU_MONTHS = [
    "Január",
    "Február",
    "Március",
    "Április",
    "Május",
    "Június",
    "Július",
    "Augusztus",
    "Szeptember",
    "Október",
    "November",
    "December",
]


class MonthlyGridWidget(QWidget):
    monthClicked = Signal(int)  # entry_id

    def __init__(
        self, items: list[MonthlyAmount], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("monthlyGrid")

        self._items_by_month: dict[int, MonthlyAmount] = {
            i.month: i for i in items
        }

        lay = QGridLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(6)

        # fejléc
        

        # 12 hónap
        for idx, month_name in enumerate(HU_MONTHS, start=1):
            r = idx - 1

            lay.addWidget(self._cell(month_name, month=idx), r, 0)

            amt_item = self._items_by_month.get(idx)
            amt = amt_item.amount if amt_item else 0.0
            
            has_value = amt_item is not None and amt > 0
            status_icon = "✔" if has_value else "○"
            amount_text = self._fmt_huf(amt) if has_value else "—"
            right_text = f"{amount_text}   {status_icon}"

            lay.addWidget(
                self._cell(
                    right_text,
                    align=Qt.AlignmentFlag.AlignRight,
                    month=idx,
                ),
                r,
                1,
            )

            lay.setColumnStretch(0, 1)
            lay.setColumnStretch(1, 0)



    def _cell(
        self,
        text: str,
        *,
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
        month: int | None = None,
    ) -> QLabel:
        lab = QLabel(text)
        lab.setProperty("cell", True)
        lab.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
        lab.setWordWrap(False)


        if month is not None:
            item = self._items_by_month.get(month)
            if item and item.entry_id is not None:
                lab.setCursor(Qt.CursorShape.PointingHandCursor)
                lab.mousePressEvent = lambda e, m=month: self._on_click(m)

        return lab

    def _on_click(self, month: int) -> None:
        item = self._items_by_month.get(month)
        if item and item.entry_id is not None:
            self.monthClicked.emit(item.entry_id)

    @staticmethod
    def _fmt_huf(amount: float) -> str:
        s = f"{amount:,.0f}".replace(",", " ")
        return f"{s} Ft"
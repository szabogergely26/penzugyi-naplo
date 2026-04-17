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

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from penzugyi_naplo.ui.bills.bill_models import PeriodicAmount


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


class PeriodicListWidget(QWidget):
    def __init__(
        self, items: list[PeriodicAmount], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("periodicList")

        self._items_by_month: dict[int, PeriodicAmount] = {
            it.month: it for it in items if 1 <= it.month <= 12
        }

        lay = QGridLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(6)

        row = 0
        for month in range(1, 13):
            item = self._items_by_month.get(month)

            month_name = HU_MONTHS[month - 1]
            status = "✓" if item and item.is_paid else "-"

            lay.addWidget(self._cell(month_name, strong=True), row, 0)
            lay.addWidget(
                self._cell(
                    status,
                    align=Qt.AlignmentFlag.AlignRight,
                    paid=bool(item and item.is_paid),
                ),
                row,
                1,
            )
            row += 1

            if item and item.is_paid:
                period = f"Időszak: {self._fmt_period(item.start, item.end)}"
                amount = f"Összeg: {self._fmt_huf(item.amount)}"
                invoice = f"Számla: {item.invoice_number or '-'}"

                lay.addWidget(self._cell(period, meta=True), row, 0, 1, 2)
                row += 1
                lay.addWidget(self._cell(amount, meta=True), row, 0, 1, 2)
                row += 1
                lay.addWidget(self._cell(invoice, meta=True), row, 0, 1, 2)
                row += 1

    def _cell(
        self,
        text: str,
        *,
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
        strong: bool = False,
        meta: bool = False,
        paid: bool = False,
    ) -> QLabel:
        lab = QLabel(text)
        lab.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
        lab.setWordWrap(False)

        if strong:
            lab.setProperty("periodicMonthTitle", True)
        elif meta:
            lab.setProperty("periodicMeta", True)
        else:
            lab.setProperty("cell", True)

        if paid:
            lab.setProperty("paid", True)

        return lab

    @staticmethod
    def _fmt_huf(amount: float | None) -> str:
        if amount is None:
            return "-"
        s = f"{amount:,.0f}".replace(",", " ")
        return f"{s} Ft"

    def _fmt_period(self, start: str | None, end: str | None) -> str:
        if not start or not end:
            return "-"
        return f"{self._fmt_date(start)} – {self._fmt_date(end)}"

    def _fmt_date(self, value: str) -> str:
        try:
            d = datetime.strptime(value, "%Y-%m-%d")
            return d.strftime("%Y.%m.%d")
        except Exception:
            return value
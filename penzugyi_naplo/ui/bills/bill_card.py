# - ui/bills/bill_card.py
# ---------------------------------------------------

"""

ui/bills/bill_card.py

Ha ezt keresed:
- számla kártya rajzolása
- kártya kattintására itt történik művelet
- Részletek ablak a számlákhoz: bill_details_dialog.py
- az adat a DB-ből nem itt van

------------------------------------------------------------------------

Számla-kártya UI komponens (Card view)
(ui/bills/bill_card.py).

Felelősség:
    - egyetlen számla vizuális megjelenítése kártya formában
    - kattintható felület biztosítása (clicked.emit(bill_id))

Input:
    - BillCardModel

Render:
    - cím (számla neve)
    - tartalom típustól függően:
        - MonthlyGridWidget
        - PeriodicListWidget

Stílus:
    - objectName='billCard'
    - 'inactive' property QSS hook

Nem felelőssége:
    - üzleti logika
    - adatlekérdezés
    - DB műveletek
"""


# -------- Importok -------

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from penzugyi_naplo.ui.bills.bill_models import BillCardModel
from penzugyi_naplo.ui.bills.monthly_grid_widget import MonthlyGridWidget
from penzugyi_naplo.ui.bills.periodic_list_widget import PeriodicListWidget

# ------ Importok vége ------


class BillCard(QFrame):
    clicked = Signal(int)  # bill_id

    def __init__(self, model: BillCardModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model = model

        self.setObjectName("billCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        # self.setCursor(Qt.CursorShape.PointingHandCursor)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        self.lbl_title = QLabel(model.name)
        self.lbl_title.setObjectName("billCardTitle")
        self.lbl_title.setWordWrap(False)

        root.addWidget(self.lbl_title)

        # “címsor alatt több hely”
        root.addSpacing(10)

        # belső tartalom típustól függően
        if model.kind == "monthly":
            inner = MonthlyGridWidget(model.monthly or [], self)
            inner.monthClicked.connect(self._open_month_transaction)
        else:
            inner = PeriodicListWidget(model.periodic or [], self)

        inner.setProperty("inner", True)
        root.addWidget(inner)

        if not model.is_active:
            self.setProperty("inactive", True)
            self.style().unpolish(self)
            self.style().polish(self)


        # --- Grafics Style ---
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)



    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        from .bill_details_dialog import BillDetailsDialog

        dlg = BillDetailsDialog(
            self.model,
            parent=self,
            db=getattr(self.window(), "db", None),
        )

        bills_page = self.parent()
        while bills_page is not None and not hasattr(bills_page, "reload"):
            bills_page = bills_page.parent()

        if bills_page is not None:
            dlg.billDeleted.connect(bills_page.reload)

        dlg.exec()
        return
    

    def _open_month_transaction(self, entry_id: int) -> None:
        from penzugyi_naplo.ui.likviditas.dialogs.transaction_details_dialog import (
            TransactionDetailsDialog,
        )

        dlg = TransactionDetailsDialog(
            parent=self,
            db=getattr(self.window(), "db", None),
            txn_id=entry_id,
        )
        dlg.exec()
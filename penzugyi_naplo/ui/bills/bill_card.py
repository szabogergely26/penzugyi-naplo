# - ui/bills/bill_card.py
# ---------------------------------------------------

"""
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
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

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
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(0)

        self.lbl_title = QLabel(model.name)
        self.lbl_title.setObjectName("billCardTitle")
        self.lbl_title.setWordWrap(False)

        root.addWidget(self.lbl_title)

        # “címsor alatt több hely”
        root.addSpacing(10)

        # belső tartalom típustól függően
        if model.kind == "monthly":
            inner = MonthlyGridWidget(model.monthly or [], self)
        else:
            inner = PeriodicListWidget(model.periodic or [], self)

        inner.setProperty("inner", True)
        root.addWidget(inner)

        if not model.is_active:
            self.setProperty("inactive", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.model.id)
        super().mousePressEvent(event)

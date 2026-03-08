# - ui/widgets/transactions_filter_bar.py
# -------------------------------------------

"""
Tranzakciók szűrősáv (UI komponens)
(ui/widgets/transactions_filter_bar.py).

Input:
    - keresőszöveg + all_years checkbox állapot

Output (signals):
    - searchRequested(text, all_years)
    - clearRequested()

Megjegyzés:
    - az all_years opció később Settings-ből is jöhet; a widget csak megjeleníti és emitálja

Topology (UI):
    MainWindow
      └─ TransactionsPage (ui/pages/transactions_page.py)
           └─ TransactionsFilterBar  ← this
"""


# - Importok -

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

# - Importok vége -


class TransactionsFilterBar(QWidget):
    """
    Tranzakciók felső sáv:
    - keresőmező
    - "Keresés minden évben" checkbox (először itt, később átkerülhet Settings-be)
    - Keresés / Törlés gombok

    Jelek:
    - searchRequested(text: str, all_years: bool)
    - clearRequested()
    """

    searchRequested = Signal(str, bool)
    clearRequested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText("Keresés név / kategória / megjegyzés szerint…")
        self.edit.returnPressed.connect(self._emit_search)

        self.chk_all_years = QCheckBox("Keresés minden évben", self)
        self.chk_all_years.setChecked(True)

        self.btn_search = QPushButton("Keresés", self)
        self.btn_search.clicked.connect(self._emit_search)

        self.btn_clear = QPushButton("Törlés", self)
        self.btn_clear.clicked.connect(self._on_clear)

        layout.addWidget(QLabel("Szűrő:"), 0)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.chk_all_years, 0)
        layout.addWidget(self.btn_search, 0)
        layout.addWidget(self.btn_clear, 0)

    def _emit_search(self) -> None:
        text = self.edit.text().strip()
        self.searchRequested.emit(text, self.chk_all_years.isChecked())

    def _on_clear(self) -> None:
        self.edit.clear()
        self.clearRequested.emit()

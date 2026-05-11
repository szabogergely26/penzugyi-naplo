# /ui/main_window/aranyszamla/trading_page.py
# -------------------------------------------

"""
Aranyszámla kereskedés oldal.

Feladata:
- arany vétel / eladás műveletek listázása
- később adatbázisból tölti be a gold_transactions rekordokat
- a ribbon gombjai innen indíthatják majd a Vétel / Eladás varázslót
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class AranyszamlaTradingPage(QWidget):
    """Az Aranyszámla modul kereskedés oldala."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("aranyszamlaTradingPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(18)

        title = QLabel("Kereskedés")
        title.setObjectName("aranyszamlaPageTitle")

        subtitle = QLabel("Arany vétel és eladás műveletek")
        subtitle.setObjectName("aranyszamlaPageSubtitle")

        table_card = QFrame()
        table_card.setObjectName("aranyszamlaTableCard")

        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(18, 18, 18, 18)
        table_layout.setSpacing(12)

        table_title = QLabel("Műveletek listája")
        table_title.setObjectName("aranyszamlaSectionTitle")

        self.table = QTableWidget()
        self.table.setObjectName("aranyszamlaTradingTable")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            [
                "Dátum",
                "Típus",
                "Gramm",
                "Árfolyam",
                "Összeg",
                "Megjegyzés",
            ]
        )

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        self.empty_label = QLabel("Nincs még rögzített arany vétel vagy eladás.")
        self.empty_label.setObjectName("aranyszamlaEmptyText")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        table_layout.addWidget(table_title)
        table_layout.addWidget(self.table, 1)
        table_layout.addWidget(self.empty_label)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(table_card, 1)

        self.load_demo_empty_state()

    def load_demo_empty_state(self) -> None:
        """
        Kezdeti üres állapot.

        Később ezt váltja majd:
        - adatbázisból lekérdezés
        - sorok betöltése a gold_transactions táblából
        """

        self.table.setRowCount(0)
        self.empty_label.setVisible(True)

    def add_demo_row(
        self,
        trade_date: str,
        trade_type: str,
        grams: str,
        unit_price: str,
        total: str,
        note: str = "",
    ) -> None:
        """
        Ideiglenes segédfüggvény tesztsor hozzáadásához.

        Később törölhető, amikor már DB-ből töltjük a listát.
        """

        row = self.table.rowCount()
        self.table.insertRow(row)

        values = [
            trade_date,
            trade_type,
            grams,
            unit_price,
            total,
            note,
        ]

        for column, value in enumerate(values):
            item = QTableWidgetItem(value)

            if column in {2, 3, 4}:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
            else:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )

            self.table.setItem(row, column, item)

        self.empty_label.setVisible(False)
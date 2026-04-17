#   ui/bills/bill_details_dialog.py
# -----------------------------------

# --- Importok:


from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .bill_models import BillCardModel


class BillDetailsDialog(QDialog):
    def __init__(self, model: BillCardModel, parent=None) -> None:
        super().__init__(parent)
        self.model = model

        self.setWindowTitle(f"Számla részletek – {model.name}")
        self.resize(920, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel(f"{model.name} – részletek")
        title.setObjectName("billDetailsTitle")
        root.addWidget(title)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Hónap",
            "Időszak",
            "Összeg",
            "Megjegyzés",
        ])

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        root.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_close = QPushButton("Bezárás")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)

        root.addLayout(btn_row)

        self._load_rows()

    def _load_rows(self) -> None:
        rows = self._build_rows()

        self.table.setRowCount(len(rows))

        for row_idx, row in enumerate(rows):
            item_date = QTableWidgetItem(row["date"])
            item_period = QTableWidgetItem(row["period"])
            item_amount = QTableWidgetItem(row["amount"])
            item_note = QTableWidgetItem(row["note"])

            item_amount.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            self.table.setItem(row_idx, 0, item_date)
            self.table.setItem(row_idx, 1, item_period)
            self.table.setItem(row_idx, 2, item_amount)
            self.table.setItem(row_idx, 3, item_note)




    def _build_rows(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []

        if self.model.kind == "monthly":
            for item in self.model.monthly or []:
                rows.append(
                    {
                        "date": "",  # nincs konkrét dátum
                        "period": f"{item.month}. hónap",
                        "amount": self._fmt_amount(item.amount),
                        "note": "",
                    }
                )

        elif self.model.kind == "periodic":
            for item in self.model.periodic or []:
                # időszak
                if item.start and item.end:
                    period_text = f"{item.start} – {item.end}"
                else:
                    period_text = ""

                # megjegyzés (számlaszám + státusz)
                note_parts = []

                if item.invoice_number:
                    note_parts.append(f"Számla: {item.invoice_number}")

                if item.is_paid:
                    note_parts.append("Fizetve")
                else:
                    note_parts.append("Nincs fizetve")

                note_text = " | ".join(note_parts)

                rows.append(
                    {
                        "date": f"{item.month}. hónap",
                        "period": period_text,
                        "amount": self._fmt_amount(item.amount or 0),
                        "note": note_text,
                    }
                )

        return rows




    @staticmethod
    def _fmt_amount(value: object) -> str:
        try:
            return f"{float(value):,.0f} Ft".replace(",", " ")
        except Exception:
            return "0 Ft"
#   ui/bills/invoice_edit_dialog.py
# -----------------------------------

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class InvoiceEditDialog(QDialog):
    """
    Kis dialógus egy meglévő tranzakció számla sorszámának szerkesztéséhez.
    Csak ezt az egy mezőt módosítja, semmi mást.
    """

    def __init__(
        self,
        entry_id: int,
        current_invoice_number: str | None,
        parent=None,
        db=None,
    ) -> None:
        super().__init__(parent)
        self.entry_id = entry_id
        self.db = db
        self.new_invoice_number: str | None = current_invoice_number

        self.setWindowTitle("Számla sorszám szerkesztése")
        self.resize(360, 120)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        label = QLabel("Számla sorszám:")
        root.addWidget(label)

        self.edit = QLineEdit()
        self.edit.setText(current_invoice_number or "")
        self.edit.setPlaceholderText("pl. 12548416")
        root.addWidget(self.edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Mégse")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("Mentés")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)

        root.addLayout(btn_row)

    def _save(self) -> None:
        value = self.edit.text().strip() or None

        if self.db is not None:
            ok = self.db.update_invoice_number(self.entry_id, value)
            if not ok:
                # Nem dobunk QMessageBox-ot itt, hogy egyszerű maradjon;
                # ha kell, később bővíthető hibaüzenettel.
                self.reject()
                return

        self.new_invoice_number = value
        self.accept()
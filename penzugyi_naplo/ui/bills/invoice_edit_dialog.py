#   ui/bills/invoice_edit_dialog.py
# -----------------------------------

"""
Meglévő számlabefizetés (monthly típus, pl. KalászNet, Telekom) utólagos
szerkesztésére szolgáló dialógus.

Szerkeszthető mezők:
    - Fizetés dátuma (csak akkor, ha editable_date=True)
    - Összeg
    - Számla sorszáma
    - Korrekció / jóváírás jelölő

Mentés előtt megerősítést kér, mert már rögzített, éles adatot módosít.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class InvoiceEditDialog(QDialog):
    """
    Egy már rögzített számlabefizetés szerkesztése.

    A dialógus maga nem dönt a mentés sikerességéről érdemben — a tényleges
    DB-műveletet a db.update_bill_entry() végzi, ide csak az eredményt adja
    vissza (True/False).
    """

    def __init__(
        self,
        entry_id: int,
        current_invoice_number: str | None,
        current_amount: float = 0,
        current_date: str | None = None,
        current_is_correction: bool = False,
        editable_date: bool = True,
        parent=None,
        db=None,
    ) -> None:
        super().__init__(parent)
        self.entry_id = entry_id
        self.db = db
        self._editable_date = editable_date

        self.setWindowTitle("Számlatétel szerkesztése")
        self.resize(380, 220)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        warning = QLabel(
            "Figyelem: már rögzített, korábbi adatot szerkesztesz."
        )
        warning.setObjectName("invoiceEditWarning")
        warning.setWordWrap(True)
        root.addWidget(warning)

        # --- Dátum (csak monthly típusnál szerkeszthető) ---
        self.edit_date: QLineEdit | None = None
        if editable_date:
            root.addWidget(QLabel("Fizetés dátuma (YYYY-MM-DD):"))
            self.edit_date = QLineEdit()
            self.edit_date.setText(
                current_date or datetime.now().strftime("%Y-%m-%d")
            )
            self.edit_date.setPlaceholderText("Pl.: 2026-03-03")
            root.addWidget(self.edit_date)

        # --- Összeg ---
        root.addWidget(QLabel("Összeg (HUF):"))
        self.edit_amount = QLineEdit()
        self.edit_amount.setText(_format_amount_for_edit(current_amount))
        self.edit_amount.setPlaceholderText("Csak pozitív szám (pl. 7170)")
        root.addWidget(self.edit_amount)

        # --- Számla sorszám ---
        root.addWidget(QLabel("Számla sorszám:"))
        self.edit_invoice = QLineEdit()
        self.edit_invoice.setText(current_invoice_number or "")
        self.edit_invoice.setPlaceholderText("pl. VG2026/82096")
        root.addWidget(self.edit_invoice)

        # --- Korrekció / jóváírás ---
        self.chk_is_correction = QCheckBox("Ez korrekció / jóváírás (nem önálló számla)")
        self.chk_is_correction.setChecked(bool(current_is_correction))
        root.addWidget(self.chk_is_correction)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Mégse")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("Mentés")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._confirm_and_save)
        btn_row.addWidget(btn_save)

        root.addLayout(btn_row)

    def _confirm_and_save(self) -> None:
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setWindowTitle("Módosítás megerősítése")
        confirm.setText("Biztos szerkeszteni akarod a már rögzített adatokat?")
        confirm.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        confirm.setDefaultButton(QMessageBox.StandardButton.No)

        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return

        self._save()

    def _save(self) -> None:
        amount_text = self.edit_amount.text().strip().replace(" ", "")

        try:
            amount = float(amount_text)
        except ValueError:
            QMessageBox.warning(
                self, "Hibás összeg", "Az összeg mezőbe csak számot lehet írni."
            )
            return

        if amount < 0:
            QMessageBox.warning(
                self, "Hibás összeg", "Az összeg nem lehet negatív."
            )
            return

        date_value = (
            self.edit_date.text().strip()
            if self.edit_date is not None
            else None
        )

        if self._editable_date and not date_value:
            QMessageBox.warning(
                self, "Hiányzó dátum", "A fizetés dátuma nem lehet üres."
            )
            return

        invoice_number = self.edit_invoice.text().strip() or None
        is_correction = self.chk_is_correction.isChecked()

        if self.db is None:
            self.reject()
            return

        ok = self.db.update_bill_entry(
            self.entry_id,
            date_str=date_value or datetime.now().strftime("%Y-%m-%d"),
            amount=amount,
            invoice_number=invoice_number,
            is_correction=is_correction,
        )

        if not ok:
            QMessageBox.critical(
                self, "Hiba", "A mentés nem sikerült. Ellenőrizd az adatokat."
            )
            return

        self.accept()


def _format_amount_for_edit(value: float | int | str | None) -> str:
    try:
        return str(int(round(float(value or 0))))
    except (TypeError, ValueError):
        return "0"
# - ui/dialogs/transaction_edit_dialog.py
# ---------------------------------------------------

"""
Tranzakció szerkesztő párbeszédablak
(ui/dialogs/transaction_edit_dialog.py).

Felelősség:
    - meglévő tranzakció adatainak szerkesztése és validált input visszaadása a hívónak
    - kategória lista megjelenítése (categories: [(id, name)])

Kontraktus:
    - a tx_type HU szövegként tér vissza: "Bevétel" / "Kiadás"
    - normalizálás a DB rétegben történik (_map_hu_to_type)

Topology (UI):
    MainWindow
      └─ TransactionsPage (ui/pages/transactions_page.py)
           └─ TransactionEditDialog  ← aktuális fájl
"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
)


class TransactionEditDialog(QDialog):
    def __init__(self, parent, *, tx: dict, categories: list[tuple[int, str]]):
        super().__init__(parent)
        self.setWindowTitle("Tranzakció szerkesztése")

        self.ed_date = QLineEdit(str(tx.get("tx_date") or ""))
        self.ed_desc = QLineEdit(str(tx.get("description") or ""))
        self.ed_name = QLineEdit(str(tx.get("name") or ""))

        # FONTOS: a te DB-d _map_hu_to_type(tx_type) függvényt hív,
        # ezért itt HU szöveget adunk vissza: "Bevétel" / "Kiadás".
        self.cb_type = QComboBox()
        self.cb_type.addItem("Bevétel", "Bevétel")
        self.cb_type.addItem("Kiadás", "Kiadás")
        self.cb_type.setCurrentIndex(0 if tx.get("tx_type") == "income" else 1)

        self.sp_amount = QDoubleSpinBox()
        self.sp_amount.setMaximum(1e12)
        self.sp_amount.setDecimals(0)
        self.sp_amount.setValue(float(tx.get("amount") or 0.0))

        self.cb_cat = QComboBox()
        for cid, cname in categories:
            self.cb_cat.addItem(cname, cid)

        cur_cid = int(tx.get("category_id") or 0)
        for i in range(self.cb_cat.count()):
            if int(self.cb_cat.itemData(i)) == cur_cid:
                self.cb_cat.setCurrentIndex(i)
                break

        layout = QFormLayout(self)
        layout.addRow("Dátum (YYYY-MM-DD)", self.ed_date)
        layout.addRow("Típus", self.cb_type)
        layout.addRow("Kategória", self.cb_cat)
        layout.addRow("Összeg", self.sp_amount)
        layout.addRow("Leírás", self.ed_desc)
        layout.addRow("Név", self.ed_name)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def data(self) -> dict:
        return {
            "date_str": self.ed_date.text().strip(),
            "category_id": int(self.cb_cat.currentData()),
            "amount": float(self.sp_amount.value()),
            "description": self.ed_desc.text().strip(),
            "tx_type": str(self.cb_type.currentData()),  # "Bevétel" / "Kiadás"
            "name": self.ed_name.text().strip(),
        }

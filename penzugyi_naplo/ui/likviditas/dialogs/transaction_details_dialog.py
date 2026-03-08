# - penzugyi_naplo/dialogs/transaction_details_dialog.py
# --------------------------------------------------------

"""
Tranzakció részletező modális ablak
(ui/dialogs/transaction_details_dialog.py).

Egy kiválasztott tranzakció tételes bontását jeleníti meg (Dátum | Név | Kategória | Egységár | Db | Ár).
Szükség esetén szerkesztési lehetőséget biztosít az egyes tételekhez.

Csak megjelenítés + interakció, az adatforrás a TransactionDatabase.

Topology (UI):
    MainWindow
      └─ TransactionsPage (ui/pages/transactions_page.py)
           └─ TransactionDetailsDialog  ← this
                └─ _ItemEditDialog (belső szerkesztő)
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class TransactionDetailsDialog(QDialog):
    """
    Tranzakció részletek (read-only) dialógus.

    Input:
      - db: TransactionDatabase
      - txn_id: int

    Megjelenítés:
      - transaction_items sorok táblázatban
      - alul összesen
    """

    def __init__(self, parent, *, db, txn_id: int):
        super().__init__(parent)
        self.db = db
        self.txn_id = int(txn_id)

        self.setWindowTitle("Részletek")
        self.resize(820, 420)

        root = QVBoxLayout(self)

        self.lbl_header = QLabel("")
        root.addWidget(self.lbl_header)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Dátum", "Név", "Kategória", "Egységár", "Db", "Ár"]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table)

        bottom = QHBoxLayout()
        self.lbl_total = QLabel("Összesen: 0")
        bottom.addWidget(self.lbl_total)
        bottom.addStretch(1)

        self.btn_edit = QPushButton("Szerkesztés")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._on_edit_item)
        bottom.addWidget(self.btn_edit)

        btn_close = QPushButton("Bezárás")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)

        root.addLayout(bottom)

        self.table.itemSelectionChanged.connect(self._update_buttons)

        self._load()
        print("DETAILS DB:", getattr(self.db, "db_name", "<no db_name>"))

    def _update_buttons(self) -> None:
        self.btn_edit.setEnabled(self.table.currentRow() >= 0)

    def _fmt_int(self, v) -> str:
        if v is None:
            return ""
        try:
            return f"{float(v):,.0f}".replace(",", " ")
        except Exception:
            return str(v)

    def _to_float_or_none(self, s: str):
        s = (s or "").strip()
        if not s:
            return None
        try:
            return float(s.replace(" ", "").replace(",", "."))
        except Exception:
            return None

    def _load(self) -> None:
        header = self.db.get_transaction_header(self.txn_id)
        if not header:
            self.lbl_header.setText("Hiba: tranzakció nem található.")
            return

        self.lbl_header.setText(
            f"Dátum: {header['tx_date']}    Név: {header['name']}    "
            f"Kategória: {header['category_name']}    Fő összeg: {self._fmt_int(header['amount'])}"
        )

        items = self.db.get_transaction_items(self.txn_id)

        self.table.setRowCount(0)
        total = 0.0

        for r in items:
            row = self.table.rowCount()
            self.table.insertRow(row)

            it_date = QTableWidgetItem(str(r["item_date"] or ""))
            it_date.setData(
                Qt.ItemDataRole.UserRole, int(r["id"])
            )  # <-- ide kerül az item_id
            self.table.setItem(row, 0, it_date)

            self.table.setItem(row, 1, QTableWidgetItem(str(r["item_name"] or "")))
            self.table.setItem(row, 2, QTableWidgetItem(str(r["category_name"] or "")))

            unit_price = r["unit_price"]
            qty = r["quantity"]
            amount = float(r["amount"] or 0.0)
            total += amount

            # fallback: ha régi rekordoknál nincs egységár és db=1, akkor egységár = összeg
            if (unit_price is None or unit_price == 0) and (
                qty is None or float(qty) == 1.0
            ):
                unit_price = amount

            self.table.setItem(
                row,
                3,
                QTableWidgetItem(
                    "" if unit_price is None else self._fmt_int(unit_price)
                ),
            )
            self.table.setItem(
                row, 4, QTableWidgetItem("" if qty is None else f"{float(qty):g}")
            )
            self.table.setItem(row, 5, QTableWidgetItem(self._fmt_int(amount)))

        self.lbl_total.setText(f"Összesen: {self._fmt_int(total)}")

    def _on_edit_item(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return

        it0 = self.table.item(row, 0)
        if not it0:
            return

        item_id = it0.data(Qt.ItemDataRole.UserRole)
        if item_id is None:
            return

        db_row = self.db.get_transaction_item(int(item_id))
        if not db_row:
            QMessageBox.warning(self, "Hiba", "A tétel nem található az adatbázisban.")
            return

        item = dict(db_row)

        dlg = _ItemEditDialog(self, item=item)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        data = dlg.data()

        # ---- parse + okos számolás ----
        item_date = data["item_date"]
        item_name = data["item_name"]
        category_name = data["category_name"]

        unit_price = self._to_float_or_none(data["unit_price"])
        quantity = self._to_float_or_none(data["quantity"])
        amount = self._to_float_or_none(data["amount"])

        # Ha az összeg üres, de van egységár+db -> számoljuk
        if amount is None:
            if unit_price is not None and quantity is not None:
                amount = float(unit_price) * float(quantity)
            else:
                QMessageBox.warning(
                    self,
                    "Hiányzó összeg",
                    "Adj meg 'Összeg'-et, vagy töltsd ki az 'Egységár' és 'Db' mezőket.",
                )
                return

        if not item_date or not item_name:
            QMessageBox.warning(self, "Hiányzó adat", "A Dátum és a Név kötelező.")
            return

        try:
            self.db.update_transaction_item(
                int(item_id),
                item_date=item_date,
                item_name=item_name,
                category_name=category_name,
                unit_price=unit_price,
                quantity=quantity,
                amount=float(amount),
            )
        except Exception as e:
            QMessageBox.critical(self, "Mentési hiba", f"Nem sikerült menteni:\n{e}")
            return

        self._load()


class _ItemEditDialog(QDialog):
    def __init__(self, parent, *, item: dict):
        super().__init__(parent)
        self.setWindowTitle("Tétel szerkesztése")
        self.resize(520, 220)

        self._item = item

        root = QVBoxLayout(self)

        # egyszerű inputok (minimalista)
        self.ed_date = QLineEdit(str(item.get("item_date", "") or ""))
        self.ed_name = QLineEdit(str(item.get("item_name", "") or ""))
        self.ed_cat = QLineEdit(str(item.get("category_name", "") or ""))

        self.ed_unit = QLineEdit(
            "" if item.get("unit_price") is None else str(item.get("unit_price"))
        )
        self.ed_qty = QLineEdit(
            "" if item.get("quantity") is None else str(item.get("quantity"))
        )
        self.ed_amt = QLineEdit(str(item.get("amount", "") or ""))

        # számolás: Egységár * Db -> Összeg
        self._recalc_guard = False

        # form szerű layout gyorsan
        def row(lbl: str, w: QLineEdit):
            lay = QHBoxLayout()
            lay.addWidget(QLabel(lbl))
            lay.addWidget(w, 1)
            root.addLayout(lay)

        row("Dátum (YYYY-MM-DD):", self.ed_date)
        row("Név:", self.ed_name)
        row("Kategória:", self.ed_cat)
        row("Egységár:", self.ed_unit)
        row("Db:", self.ed_qty)
        row("Összeg:", self.ed_amt)

        # élő számolás (ne írja felül, ha nincs elég adat)
        self.ed_unit.textChanged.connect(self._on_unit_or_qty_changed)
        self.ed_qty.textChanged.connect(self._on_unit_or_qty_changed)

        # ha valaki az összeget írja át, és van Db, visszaszámoljuk az egységárat (opcionális, de hasznos)
        self.ed_amt.editingFinished.connect(self._on_amount_finished)

        btns = QHBoxLayout()
        btns.addStretch(1)

        b_cancel = QPushButton("Mégse")
        b_ok = QPushButton("Mentés")

        b_cancel.clicked.connect(self.reject)
        b_ok.clicked.connect(self.accept)

        # --- Default viselkedés ---
        b_ok.setDefault(True)
        b_ok.setAutoDefault(True)

        b_cancel.setDefault(False)
        b_cancel.setAutoDefault(False)

        # --- Billentyűk (biztosíték) ---
        b_ok.setShortcut("Return")  # Enter
        b_cancel.setShortcut("Escape")  # Esc

        btns.addWidget(b_cancel)
        btns.addWidget(b_ok)
        root.addLayout(btns)

        # Induláskor ne a gombon legyen fókusz
        self.ed_name.setFocus()

    def _to_float_or_none(self, s: str):
        s = (s or "").strip()
        if not s:
            return None
        try:
            return float(s.replace(" ", "").replace(",", "."))
        except Exception:
            return None

    def _on_unit_or_qty_changed(self) -> None:
        if self._recalc_guard:
            return

        unit = self._to_float_or_none(self.ed_unit.text())
        qty = self._to_float_or_none(self.ed_qty.text())
        if unit is None or qty is None:
            return

        self._recalc_guard = True
        try:
            amt = float(unit) * float(qty)
            # egyszerű megjelenítés, nem lokál formázás (a DB úgyis float)
            self.ed_amt.setText(f"{amt:g}")
        finally:
            self._recalc_guard = False

    def _on_amount_finished(self) -> None:
        if self._recalc_guard:
            return

        amt = self._to_float_or_none(self.ed_amt.text())
        qty = self._to_float_or_none(self.ed_qty.text())
        unit = self._to_float_or_none(self.ed_unit.text())

        # Ha egységár üres, de összeg+db megvan -> számoljuk vissza az egységárat
        if unit is None and amt is not None and qty not in (None, 0):
            self._recalc_guard = True
            try:
                self.ed_unit.setText(f"{(float(amt) / float(qty)):g}")
            finally:
                self._recalc_guard = False

    def data(self) -> dict:
        return {
            "item_date": self.ed_date.text().strip(),
            "item_name": self.ed_name.text().strip(),
            "category_name": (self.ed_cat.text().strip() or None),
            "unit_price": self.ed_unit.text().strip(),
            "quantity": self.ed_qty.text().strip(),
            "amount": self.ed_amt.text().strip(),
        }

# penzugyi_naplo/ui/dialog_transaction_editor.py
# ------------------------------------------------


"""
Modális dialógus meglévő tranzakció szerkesztéséhez
(penzugyi_naplo/ui/dialog_transaction_editor.py).

Felelősség:
    - egy tranzakció adatainak betöltése és szerkesztése
    - mezők validálása (dátum, pozitív összeg, kategória)
    - update_transaction() hívás a TransactionDatabase-en

Modell elv (B-modell):
    - az amount mindig pozitív
    - a típus ('income' | 'expense') külön mezőben tárolódik
    - a dialógusban megjelenő összeg ezért mindig pozitív

Kapcsolat:
    - parent.db → TransactionDatabase
    - mentés után a hívó oldal (pl. TransactionsPage) frissíti a listát

Nem felelőssége:
    - tranzakciólista újratöltése
    - diagramok frissítése
    - SQL közvetlen kezelése

"""


# --- Importok ---

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from core.utils import format_number_hu, is_valid_date, parse_amount

# - Importok vége -


# --- kód kezdete ---


class TransactionEditor(QDialog):
    """Modális ablak egy létező tranzakció szerkesztéséhez."""

    def __init__(self, parent, txn_data) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tranzakció Szerkesztése")
        self.setMinimumWidth(400)

        self.parent_window = parent
        self.db = parent.db
        self.locale = parent.locale

        # txn_data: (id, date, category_name, amount, description, type, category_id)
        self.txn_id = txn_data[0]
        #  self.original_type = txn_data[5]  # 'Bevétel' vagy 'Kiadás'  --- már nem kell --

        self.root_layout = QVBoxLayout(self)

        self.tx_type = self._norm_type(txn_data[5])  # 'income' vagy 'expense'

        # --- Form layout ---
        form_layout = QGridLayout()

        # 1) Dátum
        form_layout.addWidget(QLabel("Dátum (YYY-MM-DD):"), 0, 0)
        self.input_date = QLineEdit(str(txn_data[1]))
        form_layout.addWidget(self.input_date, 0, 1)

        # 2) Kategória
        form_layout.addWidget(QLabel("Kategória:"), 1, 0)
        self.combo_category = QComboBox()
        self._load_categories(self.tx_type, current_name=str(txn_data[2]))
        form_layout.addWidget(self.combo_category, 1, 1)

        # 3) Összeg (abszolút érték, formázva)
        form_layout.addWidget(QLabel("Összeg (HUF):"), 2, 0)
        formatted_amount = format_number_hu(abs(float(txn_data[3])))
        self.input_amount = QLineEdit(formatted_amount)
        self.input_amount.setStyleSheet("font-weight: bold;")
        form_layout.addWidget(self.input_amount, 2, 1)

        # 4) Leírás
        form_layout.addWidget(QLabel("Leírás/Név:"), 3, 0)
        self.input_description = QLineEdit(str(txn_data[4] or ""))
        form_layout.addWidget(self.input_description, 3, 1)

        self.layout.addLayout(form_layout)

        # --- Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_changes)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)

    def _load_categories(self, t_type: str, current_name: str) -> None:
        """Betölti a kategóriákat a ComboBox-ba és kiválasztja az aktuálisat."""
        conn = self.db.get_db_connection()
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT id, name FROM categories WHERE tx_type = ?",
            (t_type,),
        ).fetchall()
        conn.close()

        self.category_map: dict[str, int] = {}

        self.combo_category.clear()
        for row in rows:
            try:
                cat_id = int(row["id"])
                name = str(row["name"])
            except Exception:
                cat_id = int(row[0])
                name = str(row[1])

            self.combo_category.addItem(name)
            self.category_map[name] = cat_id

        idx = self.combo_category.findText(current_name)
        if idx >= 0:
            self.combo_category.setCurrentIndex(idx)

    def _norm_type(self, t: str) -> str:
        t = (t or "").strip().lower()
        if t in ("kiadás", "kiadas", "expense"):
            return "expense"
        if t in ("bevétel", "bevetel", "income"):
            return "income"
        return "expense"

    def save_changes(self) -> None:
        """Mentés: validálás + DB frissítés + főablak frissítése."""
        # 1) Dátum validálás
        date = is_valid_date(self.input_date.text().strip())
        if not date:
            QMessageBox.critical(
                self,
                "Hiba",
                "Érvénytelen dátum formátum! Kérjük, YYYY-M-D vagy YYYY-MM-DD formátumot használjon.",
            )
            return

        # 2) Összeg validálás (pozitív kell legyen a mezőben)
        amount_str = self.input_amount.text().strip()
        try:
            gs = self.locale.groupSeparator()
            dp = self.locale.decimalPoint()
            amount = parse_amount(amount_str, group_sep=gs, decimal_point=dp)
            if amount <= 0:
                QMessageBox.warning(self, "Hiba", "Kérjük, adjon meg pozitív összeget.")
                return
        except ValueError:
            QMessageBox.warning(
                self, "Hiba", "Érvénytelen összeg formátum. Csak számokat használjon."
            )
            return

        # 3) Kategória
        selected_name = self.combo_category.currentText()
        category_id = self.category_map.get(selected_name)
        if category_id is None:
            QMessageBox.warning(self, "Hiba", "Érvénytelen kategória kiválasztva.")
            return

        # 4) Előjel visszaállítása az eredeti típus alapján
        final_amount = abs(amount)

        # 5) DB update
        ok = self.db.update_transaction(
            self.txn_id,
            date,
            category_id,
            final_amount,
            self.input_description.text().strip(),
            tx_type=self.tx_type,
        )

        if ok:
            QMessageBox.information(
                self, "Siker", "A tranzakció sikeresen frissítve lett."
            )
            self.parent_window.load_transactions()
            super().accept()
        else:
            QMessageBox.critical(
                self, "Hiba", "Adatbázis hiba történt a frissítés során."
            )

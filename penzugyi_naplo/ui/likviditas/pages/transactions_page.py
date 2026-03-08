# - penzugyi_naplo/ui/pages/transactions_page.py
# -------------------------------------------------

"""
Tranzakciók oldal (lista + keresés + műveletek)
(ui/pages/transactions_page.py).

Fő funkciók:
    - tranzakciók listázása táblázatban
    - keresés kategória / név / leírás alapján (debounce: QTimer)
    - szerkesztés és törlés UI-ból

Szűrés:
    - év / all_years állapot MainWindow felől (set_filter / set_year)

Adatforrás:
    - TransactionDatabase.get_transactions_filtered()

Interakciók:
    - szerkesztés: TransactionEditDialog (ui/dialogs/transaction_edit_dialog.py)
    - részletek: TransactionDetailsDialog (ui/dialogs/transaction_details_dialog.py)
    - törlés: megerősítéssel

Megjegyzés (B-modell):
    - DB-ben amount mindig pozitív
    - UI-ban a kiadás megjelenhet negatív előjellel (csak megjelenítés)

Topology (UI):
    MainWindow
      └─ TransactionsPage  ← this
           ├─ TransactionEditDialog (ui/dialogs/transaction_edit_dialog.py)
           └─ TransactionDetailsDialog (ui/dialogs/transaction_details_dialog.py)
"""


# -- Importok --

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
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
    QWidget,
)

from penzugyi_naplo.ui.likviditas.dialogs.transaction_details_dialog import (
    TransactionDetailsDialog,
)
from penzugyi_naplo.ui.likviditas.dialogs.transaction_edit_dialog import (
    TransactionEditDialog,
)

# -Importok vége -


class SortKeyItem(QTableWidgetItem):
    """QTableWidgetItem, ami UserRole sort-kulcs alapján rendez."""

    def __init__(self, text: str, sort_key):
        super().__init__(text)
        self.setData(Qt.ItemDataRole.UserRole, sort_key)

    def __lt__(self, other: "QTableWidgetItem") -> bool:
        a = self.data(Qt.ItemDataRole.UserRole)
        b = other.data(Qt.ItemDataRole.UserRole)
        if a is not None and b is not None:
            return a < b
        return super().__lt__(other)


class TransactionsPage(QWidget):
    """
    Egységes, egyszerű Tranzakciók oldal:
    - 1 db keresősáv felül
    - 1 db táblázat
    - DB-ből tölt: db.get_transactions_filtered(...)
    """

    def __init__(self, parent: QWidget | None = None, db: Any | None = None) -> None:
        super().__init__(parent)
        self.db = db

        # Szűrő alapértékek (hogy ne legyen _year AttributeError)
        self._all_years = True
        self._year = None

        self._filter_year = None
        self._filter_all_years = True

        # Logger (fájl)
        log_dir = Path(__file__).resolve().parents[2] / "logs"  # projekt_root/logs
        log_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = log_dir / "app.log"

        self._logger = logging.getLogger("penzugyi.TransactionsPage")
        if not self._logger.handlers:
            self._logger.setLevel(logging.INFO)
            fh = logging.FileHandler(self._log_path, encoding="utf-8")
            fh.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            )
            self._logger.addHandler(fh)

        # --- UI: felső sáv ---
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Keresés (kategória / leírás)...")

        self.btn_search = QPushButton("Keresés", self)
        self.btn_clear = QPushButton("Törlés", self)

        top = QHBoxLayout()
        top.addWidget(QLabel("Szűrő:", self))
        top.addWidget(self.search_edit, 1)
        top.addWidget(self.btn_search)
        top.addWidget(self.btn_clear)

        # --- UI: táblázat: Oszlopok láthatósága ---
        self.table = QTableWidget(self)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            [
                "Dátum",
                "Név",
                "Kategória",
                "Egységár",
                "Db",
                "Összesen",
                "Leírás",
                "Típus",
                "Műveletek",
            ]
        )

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        # header ELŐBB
        header = self.table.horizontalHeader()

        # méretezések
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Dátum
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Név
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Kategória
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Egységár
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Db
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Összesen
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # Leírás
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Típus
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Műveletek

        # --- Rendezés (fejléc-katt) ---
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)

        header.setSectionsMovable(False)
        header.setHighlightSections(False)

        self.table.setSortingEnabled(True)

        # alap nyíl (az alap rendezést a reload() végén állítod be)
        header.setSortIndicator(0, Qt.SortOrder.DescendingOrder)

        # --- Layout (csak 1!) ---
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        root.addLayout(top)
        root.addWidget(self.table, 1)

        # --- Keresősáv időzítő ---
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_timer.timeout.connect(self.reload)

        # --- Signals ---
        self.search_edit.textChanged.connect(self._schedule_search)
        self.btn_clear.clicked.connect(self.on_clear)

        # első töltés
        self.reload()

        # DEBUG:
        print("TP: tables:", self.findChildren(QTableWidget))
        print("TP: headers:", self.findChildren(QHeaderView))

        print("DB PATH:", getattr(self.db, "db_name", "<no db_name>"))

        self._logger.info("TransactionsPage init OK, log file: %s", self._log_path)

        self.table.cellDoubleClicked.connect(self._on_table_double_clicked)

    # --- Metódusok:

    def set_filter(self, *, year: int | None, all_years: bool) -> None:
        self._filter_year = year
        self._filter_all_years = all_years

    def _on_table_double_clicked(self, row: int, col: int) -> None:
        # ugyanazt csináljuk, mint a Részletek gomb
        w = self.table.cellWidget(row, 8)  # Műveletek oszlop
        if not w:
            return

        for i in range(w.layout().count()):
            btn = w.layout().itemAt(i).widget()
            if isinstance(btn, QPushButton) and btn.text() == "Részletek":
                btn.click()
                return

    def bind_db(self, db: Any) -> None:
        """Ha MainWindow később adja át a DB-t."""
        self.db = db
        self.reload()

    def on_clear(self) -> None:
        self.search_edit.clear()
        self.reload()

    def reload(self) -> None:
        """Táblázat újratöltése DB-ből."""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        if not self.db:
            self.table.setRowCount(0)
            self.table.clearContents()
            return

        # Keresés: közvetlenül a search_edit-ből, nincs _search_text_or_none()
        q = self.search_edit.text().strip()
        query = q if q else None

        # 1) Lekérdezés
        try:
            rows = self.db.get_transactions_filtered(
                year=self._year,
                all_years=self._filter_all_years,
                query=query,
            )
        except Exception as e:
            self._logger.error("reload() DB hiba: %r\n%s", e, traceback.format_exc())
            self.table.setRowCount(0)
            self.table.clearContents()
            return

        # 2) Takarítás
        self.table.setRowCount(0)
        self.table.clearContents()

        # 3) Sorok száma
        self.table.setRowCount(len(rows))

        # 4) Feltöltés
        for r, tx in enumerate(rows):
            tx_id = int(tx["id"])

            try:
                has_details = int(tx["has_details"] or 0)
            except Exception:
                has_details = 0

            # get_transactions_filtered -> egységes kulcsok: tx_date, tx_type, name
            tx_date = str(tx["tx_date"] or "")
            tx_type = str(tx["tx_type"] or "")

            category = str(tx["category_name"] or "")

            # Név: name előnyben, fallback description
            name_val = str(tx["name"] or "").strip()
            name = name_val if name_val else str(tx["description"] or "")

            desc = str(tx["description"] or "")

            # ÚJ: db (előbb, hogy az egységár fallback tudjon számolni vele)
            q_raw = tx["quantity"]
            try:
                quantity = int(q_raw) if q_raw is not None else 1
            except Exception:
                quantity = 1
            if quantity < 1:
                quantity = 1

            # ÚJ: egységár fallback javítva (unit_price > 0 -> azt mutatjuk, különben amount/qty vagy amount)
            total = float(tx["amount"] or 0.0)
            up_raw = tx["unit_price"]

            if up_raw is not None and float(up_raw) > 0:
                unit_price = float(up_raw)
            else:
                unit_price = (
                    (total / quantity) if (quantity > 1 and total > 0) else total
                )

            # Összesen: kompatibilitás miatt továbbra is amount mezőt használjuk
            total = float(tx["amount"] or 0.0)
            shown_total = total if tx_type == "income" else -total  # kiadás mínuszban

            # Oszlopok:
            # 0 Dátum | 1 Név | 2 Kategória | 3 Egységár | 4 Db | 5 Összesen | 6 Leírás | 7 Típus | 8 Műveletek

            self.table.setItem(r, 0, SortKeyItem(tx_date, tx_date))  # Dátum
            self.table.setItem(r, 1, QTableWidgetItem(name))  # Név (maradhat)
            self.table.setItem(
                r, 2, SortKeyItem(category, category.casefold())
            )  # Kategória

            unit_text = f"{unit_price:,.0f}".replace(",", " ")
            self.table.setItem(r, 3, SortKeyItem(unit_text, float(unit_price)))

            qty_text = str(quantity)
            self.table.setItem(r, 4, SortKeyItem(qty_text, float(quantity)))

            total_text = f"{shown_total:,.0f}".replace(",", " ")
            self.table.setItem(r, 5, SortKeyItem(total_text, float(shown_total)))

            self.table.setItem(r, 6, QTableWidgetItem(desc))
            type_text = "Bevétel" if tx_type == "income" else "Kiadás"
            type_key = 0 if tx_type == "income" else 1  # Bevétel előre
            self.table.setItem(r, 7, SortKeyItem(type_text, type_key))

            self.table.setCellWidget(r, 8, self._make_action_cell(tx_id, has_details))

        self.table.setSortingEnabled(True)

        # Alap rendezés: Dátum ↓ (0. oszlop)
        self.table.sortItems(0, Qt.SortOrder.DescendingOrder)
        self.table.horizontalHeader().setSortIndicator(0, Qt.SortOrder.DescendingOrder)

    def set_year(self, year: int) -> None:
        self._year = int(year)
        self._filter_all_years = False
        self.reload()

    def _schedule_search(self, _text: str) -> None:
        self._search_timer.start()

    def _make_action_cell(self, tx_id: int, has_details: int = 0) -> QWidget:
        w = QWidget(self.table)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        btn_edit = QPushButton("Szerkesztés", w)
        btn_del = QPushButton("Törlés", w)

        btn_edit.setProperty("tx_id", tx_id)
        btn_del.setProperty("tx_id", tx_id)

        btn_edit.clicked.connect(self._on_edit_clicked)
        btn_del.clicked.connect(self._on_delete_clicked)

        lay.addWidget(btn_edit)

        if has_details:
            btn_det = QPushButton("Részletek", w)
            btn_det.setProperty("tx_id", tx_id)
            btn_det.clicked.connect(self._on_details_clicked)
            lay.addWidget(btn_det)

        lay.addWidget(btn_del)
        return w

    def _on_edit_clicked(self) -> None:
        btn = self.sender()
        if btn is None:
            return
        tx_id = int(btn.property("tx_id"))
        self.on_edit_tx(tx_id)

    def _on_delete_clicked(self) -> None:
        btn = self.sender()
        if btn is None:
            return
        tx_id = int(btn.property("tx_id"))

        ret = QMessageBox.question(
            self,
            "Törlés megerősítése",
            f"Biztosan törlöd ezt a tranzakciót? (ID: {tx_id})",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        self.on_delete_tx(tx_id)

    def on_edit_tx(self, tx_id: int) -> None:
        if not self.db:
            return

        row = self.db.get_transaction_by_id(tx_id)
        if not row:
            print("EDIT", tx_id, "not found")
            return

        tx = dict(row)

        # Kategóriák betöltése
        cats_rows = self.db.get_all_categories()
        categories = [(int(c["id"]), str(c["name"])) for c in cats_rows]
        print("CATS SAMPLE:", dict(cats_rows[0]) if cats_rows else "NO CATS")

        dlg = TransactionEditDialog(
            self,
            tx=tx,
            categories=categories,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        data = dlg.data()

        ok = self.db.update_transaction(
            tx_id,
            data["date_str"],
            data["category_id"],
            data["amount"],
            data["description"],
            tx_type=data["tx_type"],  # HU string: "Bevétel"/"Kiadás"
            name=data["name"],  # ÚJ mező
        )
        print("EDIT SAVE", tx_id, "ok=", ok)
        if ok:
            self.reload()

    def on_details_tx(self, tx_id: int) -> None:
        if not self.db:
            return

        dlg = TransactionDetailsDialog(parent=self, db=self.db, txn_id=tx_id)
        dlg.exec()

        # ha a részletek módosíthatják a total-t, akkor frissítsünk
        self.reload()

    def on_delete_tx(self, tx_id: int) -> None:
        if not self.db:
            return

        # itt megerősítő dialog (QMessageBox)
        # ha igen:
        ok = self.db.delete_transaction(tx_id)
        if ok:
            self.reload()

    def _on_details_clicked(self) -> None:
        btn = self.sender()
        if btn is None:
            return

        tx_id = int(btn.property("tx_id"))

        if not self.db:
            return

        dlg = TransactionDetailsDialog(
            parent=self,
            db=self.db,
            txn_id=tx_id,
        )
        dlg.exec()

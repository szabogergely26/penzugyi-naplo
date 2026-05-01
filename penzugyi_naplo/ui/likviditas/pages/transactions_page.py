# - penzugyi_naplo/ui/likviditas/pages/transactions_page.py
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


from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
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




# Segédfüggvények:

# ------ szinezés -------

def get_transaction_type_text(tx_type: str, is_bill: int) -> str:
    """A Típus oszlop megjelenített szövege."""
    if tx_type == "income":
        return "Bevétel"
    if tx_type == "expense" and int(is_bill or 0) == 1:
        return "Számlabefizetés"
    return "Kiadás"


def get_transaction_type_sort_key(type_text: str) -> int:
    """Rendezési kulcs a Típus oszlophoz."""
    if type_text == "Bevétel":
        return 0
    if type_text == "Kiadás":
        return 1
    return 2


def get_transaction_type_color(tx_type: str, is_bill: int) -> QColor:
    """A Típus oszlop betűszíne az üzleti logika alapján."""
    if tx_type == "income":
        return QColor(40, 140, 70)    # Bevétel
    if tx_type == "expense" and int(is_bill or 0) == 1:
        return QColor(140, 90, 180)   # Számlabefizetés
    return QColor(170, 60, 60)        # Kiadás








# ---- Segédfüggvények vége --------




class TransactionsPage(QWidget):
    """
    Egységes, egyszerű Tranzakciók oldal:
    - 1 db keresősáv felül
    - 1 db táblázat
    - DB-ből tölt: db.get_transactions_filtered(...)
    """

    def __init__(self, parent: QWidget | None = None, db: Any | None = None) -> None:
        super().__init__(parent)

        self.log = getattr(parent, "log", None)
        if self.log:
            self.log.d("AKTIV TRANSACTIONS_PAGE: ui/likviditas/pages/transactions_page.py")

        self.db = db

        # Szűrő alapértékek (hogy ne legyen _year AttributeError)
        self._all_years = True
        self._year = None

        self._filter_year = None
        self._filter_all_years = True

       

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
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            [
                "",
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

        self.table.setColumnWidth(0, 20)    # Jelzés (0.oszlop) szélessége
        

        # header ELŐBB
        header = self.table.horizontalHeader()

        # méretezések – importált régi adatokhoz is stabil
        header.setSectionResizeMode(0, QHeaderView.Fixed)        # Jelzés
        header.setSectionResizeMode(1, QHeaderView.Fixed)        # Dátum
        header.setSectionResizeMode(2, QHeaderView.Interactive)  # Név
        header.setSectionResizeMode(3, QHeaderView.Fixed)        # Kategória
        header.setSectionResizeMode(4, QHeaderView.Fixed)        # Egységár
        header.setSectionResizeMode(5, QHeaderView.Fixed)        # Db
        header.setSectionResizeMode(6, QHeaderView.Fixed)        # Összesen
        header.setSectionResizeMode(7, QHeaderView.Interactive)  # Leírás
        header.setSectionResizeMode(8, QHeaderView.Fixed)        # Típus
        header.setSectionResizeMode(9, QHeaderView.Fixed)        # Műveletek

        self.table.setColumnWidth(0, 28)     # Jelzés
        self.table.setColumnWidth(1, 105)    # Dátum
        self.table.setColumnWidth(2, 260)    # Név
        self.table.setColumnWidth(3, 120)    # Kategória
        self.table.setColumnWidth(4, 90)     # Egységár
        self.table.setColumnWidth(5, 55)     # Db
        self.table.setColumnWidth(6, 115)    # Összesen
        self.table.setColumnWidth(7, 330)    # Leírás
        self.table.setColumnWidth(8, 125)     # Típus
        self.table.setColumnWidth(9, 200)    # Műveletek

        # --- Rendezés (fejléc-katt) ---
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)

        header.setSectionsMovable(False)
        header.setHighlightSections(False)

        self.table.setSortingEnabled(True)

        # alap nyíl (az alap rendezést a reload() végén állítod be)
        header.setSortIndicator(1, Qt.SortOrder.DescendingOrder)

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

      

        

        self.table.cellDoubleClicked.connect(self._on_table_double_clicked)

    # --- Metódusok:

    def set_filter(self, *, year: int | None, all_years: bool) -> None:
        self._filter_year = year
        self._filter_all_years = all_years

    def _on_table_double_clicked(self, row: int, col: int) -> None:
        if col == 9:
            return
        
        item = self.table.item(row,0)
        if item is None:
            return
        
        has_details = bool(item.data(Qt.ItemDataRole.UserRole + 1))
        if not has_details:
            return

        tx_id = item.data(Qt.ItemDataRole.UserRole)
        if tx_id is None:
            return

        self.on_details_tx(int(tx_id))

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
        except Exception:
            if self.log:
                self.log.exception("TransactionsPage.reload() DB hiba")
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
            # Oszlopok:
            # 0 Jelzés | 1 Dátum | 2 Név | 3 Kategória | 4 Egységár | 5 Db | 6 Összesen | 7 Leírás | 8 Típus | 9 Műveletek

            detail_text = "⊞" if has_details else ""
            detail_item = QTableWidgetItem(detail_text)
            detail_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            detail_item.setData(Qt.ItemDataRole.UserRole, tx_id)
            detail_item.setData(Qt.ItemDataRole.UserRole + 1, bool(has_details))

            font = detail_item.font()
            font.setBold(False)
            font.setPointSize(font.pointSize() + 4)   # +3 vagy +4 általában jó
            detail_item.setFont(font)

            if has_details:
                detail_item.setToolTip("Tételrészletek elérhetők")
                

            self.table.setItem(r, 0, detail_item)

            self.table.setItem(r, 1, SortKeyItem(tx_date, tx_date))  # Dátum
            self.table.setItem(r, 2, QTableWidgetItem(name))         # Név
            self.table.setItem(
                r, 3, SortKeyItem(category, category.casefold())
            )  # Kategória


            unit_text = f"{unit_price:,.0f}".replace(",", " ")
            self.table.setItem(r, 4, SortKeyItem(unit_text, float(unit_price)))

            qty_text = str(quantity)
            self.table.setItem(r, 5, SortKeyItem(qty_text, float(quantity)))

            total_text = f"{shown_total:,.0f}".replace(",", " ")
            self.table.setItem(r, 6, SortKeyItem(total_text, float(shown_total)))

            self.table.setItem(r, 7, QTableWidgetItem(desc))

            is_bill = int(tx["is_bill"] or 0)

            type_text = get_transaction_type_text(tx_type, is_bill)
            type_key = get_transaction_type_sort_key(type_text)

            type_item = SortKeyItem(type_text, type_key)
            type_item.setForeground(get_transaction_type_color(tx_type, is_bill))

            

            self.table.setItem(r, 8, type_item)

            if has_details:
                for col in range(0, 9):  # csak az item-es oszlopok
                    item = self.table.item(r, col)
                    if item is not None:
                        item.setBackground(QColor(100, 160, 220, 35))

            self.table.setCellWidget(r, 9, self._make_action_cell(tx_id))

        self.table.setSortingEnabled(True)

        # Alap rendezés: Dátum ↓ (0. oszlop)
        self.table.sortItems(1, Qt.SortOrder.DescendingOrder)
        self.table.horizontalHeader().setSortIndicator(1, Qt.SortOrder.DescendingOrder)

    def set_year(self, year: int) -> None:
        self._year = int(year)
        self._filter_all_years = False
        self.reload()

    def _schedule_search(self, _text: str) -> None:
        self._search_timer.start()

    def _make_action_cell(self, tx_id: int) -> QWidget:
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
            
            if self.log:
                self.log.warning("EDIT", tx_id, "not found")
            return

        tx = dict(row)

        # Kategóriák betöltése
        cats_rows = self.db.get_all_categories()
        categories = [(int(c["id"]), str(c["name"])) for c in cats_rows]
        
        if self.log:
            self.log.d("CATS SAMPLE:", dict(cats_rows[0]) if cats_rows else "NO CATS")

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
        
        # DEBUG:
        if self.log:
            if ok:
                self.log.info("EDIT SAVE", tx_id, "ok=", ok)
            else:
                self.log.warning("EDIT SAVE", tx_id, "ok=", ok)

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

    

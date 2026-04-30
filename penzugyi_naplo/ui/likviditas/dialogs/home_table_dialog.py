# ui/likviditas/dialogs/home_table_dialogs.py
# ----------------------------------------------

"""
Táblázatos havi összesítő dialógus
(ui/likviditas/dialogs/home_table_dialog.py).

Felelősség:
    - az aktív év havi összesítő adatainak táblázatos megjelenítése
    - tervezett és tényleges bevételek / kiadások / megtakarítások áttekintése
    - a szerkeszthető tervadatok visszaírása az adatbázisba

UI:
    - QDialog alapú külön ablak
    - QTableWidget 12 sorral, a hónapokhoz igazítva
    - 10 oszlopos táblázat pénzügyi összesítő adatokkal
    - fix ablakméret: 1300 × 460 px

Kapcsolódás:
    - HomePage.open_table_dialog() nyitja meg
    - adatforrás: AppContext / TransactionDatabase
"""



from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from shiboken6 import isValid

MONTHS_HU = [
    "Január","Február","Március","Április","Május","Június",
    "Július","Augusztus","Szeptember","Október","November","December",
]


def fmt_huf(x: float) -> str:
    return f"{int(round(x)):,}".replace(",", " ")


def parse_huf(text: str) -> float:
    t = (text or "").strip().replace("Ft", "").replace(" ", "")
    try:
        return float(t.replace(",", "."))
    except ValueError:
        return 0.0


class HomeTableDialog(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)

        self.ctx = ctx
        self._year = ctx.state.active_year
        self._updating = False

        self.setWindowTitle(f"Havi összesítő – {self._year}")
        self.setFixedSize(1300, 460)     # x; y

        layout = QVBoxLayout(self)

        title = QLabel("Havi összesítő (szerkeszthető)")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.table = QTableWidget(12, 10)   # sorszám, oszlopszám
        layout.addWidget(self.table, 1)

        self._setup_table()
        self.reload()

    # ------------------------

    def _setup_table(self):
        headers = [
            "Hónap",
            "Terv Bevétel",
            "Valós Bevétel",
            "Δ Bev",
            "Terv Kiadás",
            "Fix",
            "Valós Kiadás",
            "Δ Kiadás",
            "Terv Megtakarítás",
            "Valós Megtakarítás",
        ]

        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Fixed)

        widths = [120, 130, 130, 110, 130, 110, 130, 110, 140, 160]
        for i, w in enumerate(widths):
            self.table.setColumnWidth(i, w)

        for i, month in enumerate(MONTHS_HU):
            item = QTableWidgetItem(month)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, item)

        self.table.itemChanged.connect(self._on_item_changed)

    # ------------------------

    def _make_item(self, val: float, editable: bool):
        it = QTableWidgetItem(fmt_huf(val))
        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        if not editable:
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)

        return it

    # ------------------------

    def reload(self):
        if not isValid(self.table):
            return

        self._updating = True

        try:
            actual = self.ctx.db.get_monthly_income_expense_bills(self._year)
            plans = self.ctx.db.get_year_plans(self._year)

            for month in range(1, 13):
                r = month - 1

                p_income, p_exp, p_fixed = plans.get(month, (0, 0, 0))
                income, exp_core, bills = actual.get(month, (0, 0, 0))

                actual_exp = exp_core + bills

                d_income = income - p_income
                d_exp = actual_exp - (p_exp + p_fixed)

                p_sav = p_income - (p_exp + p_fixed)
                a_sav = income - actual_exp

                self.table.setItem(r, 1, self._make_item(p_income, True))
                self.table.setItem(r, 2, self._make_item(income, False))
                self.table.setItem(r, 3, self._make_item(d_income, False))

                self.table.setItem(r, 4, self._make_item(p_exp, True))
                self.table.setItem(r, 5, self._make_item(p_fixed, True))
                self.table.setItem(r, 6, self._make_item(actual_exp, False))
                self.table.setItem(r, 7, self._make_item(d_exp, False))

                self.table.setItem(r, 8, self._make_item(p_sav, False))
                self.table.setItem(r, 9, self._make_item(a_sav, False))

        finally:
            self._updating = False

    # ------------------------

    def _on_item_changed(self, item):
        if self._updating:
            return

        row = item.row()
        col = item.column()
        month = row + 1

        value = parse_huf(item.text())

        if col == 1:
            self.ctx.db.upsert_month_plan(self._year, month, planned_income=value)
        elif col == 4:
            self.ctx.db.upsert_month_plan(self._year, month, planned_expense=value)
        elif col == 5:
            self.ctx.db.upsert_month_plan(self._year, month, planned_fixed_expense=value)

        self.reload()
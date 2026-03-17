# # - ui/likviditas/pages/home_page.py
# -------------------------------------


"""
Kezdőoldal / Dashboard oldal
(ui/pages/home_page.py).

Felelősség:
    - havi bontású pénzügyi összesítések megjelenítése
    - bevételek, kiadások, számlák és megtakarítás számítása

Év-kezelés:
    - aktív év a MainWindow-tól érkezik
    - set_year() -> reload()

Adatforrás:
    - TransactionDatabase (havi/éves összesítések)

UI:
    - havi táblázatos nézet (Jan–Dec fix sorrend)
    - belső tabok: "Kezdőoldal" / "Számlák"

Topology (UI):
    MainWindow
      └─ HomePage  ← this
           ├─ HomeSummaryPanel (ui/home_summary_panel.py)
           └─ QTableWidget (havi dashboard)

"""


# --- Importok ---

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from penzugyi_naplo.core.app_context import AppContext
from penzugyi_naplo.ui.likviditas.widgets.home_summary_panel import HomeSummaryPanel

# - Importok vége - #



@dataclass
class HomeSummaryRow:
    month_label: str
    planned_income: float
    actual_income: float
    income_diff: float
    planned_expense: float
    planned_fixed_expense: float
    actual_expense: float
    expense_diff: float
    planned_savings: float
    actual_savings: float







# - Konstansok, segédfüggvények - #


MONTHS_HU = [
    "Január",
    "Február",
    "Március",
    "Április",
    "Május",
    "Június",
    "Július",
    "Augusztus",
    "Szeptember",
    "Október",
    "November",
    "December",
]


def fmt_huf(x: float) -> str:
    s = f"{int(round(x)):,}".replace(",", " ")
    return s


def parse_huf(text: str) -> float:
    """
    Engedjük: '12 000', '12000', '12 000 Ft'
    """
    t = (text or "").strip()
    if not t:
        return 0.0
    t = t.replace("Ft", "").replace("ft", "").replace(" ", "")
    t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return 0.0













# - HomePage osztály -


class HomePage(QWidget):
    """
    Kezdőoldal (dashboard):
    - Havi bontás: Bevételek / Kiadások
    - Aktív év szerint frissül (MainWindow set_year hívja)
    """

    def __init__(self, ctx: AppContext, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.dev_mode = self.ctx.dev_mode
        self._year = int(self.ctx.state.active_year)

        self._updating = False

        # --- UI felépítése ---
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Kezdőoldal")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        subtitle = QLabel("Havi összesítők az aktív év tranzakcióiból.")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        content = QFrame()
        content.setObjectName("homeContent")
        content.setFrameShape(QFrame.NoFrame)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)


        headers = self._get_headers()



        # --- Havi dashboard tábla ---

        self.table = QTableWidget(12, len(headers), content)
        self.table.setObjectName("homeTable")

        # fejlécek
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)

        # viselkedés / megjelenés
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)

        # --- NE legyen rendezhető (Jan–Dec fix) ---
        self.table.setSortingEnabled(False)
        hdr = self.table.horizontalHeader()
        hdr.setSectionsClickable(False)
        hdr.setSortIndicatorShown(False)

        # 0. oszlop: hónapnevek (nem szerkeszthető)
        for i, month_name in enumerate(MONTHS_HU):
            it = QTableWidgetItem(month_name)
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, it)

        # szerkesztés: csak dupla katt / billentyű
        self.table.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
        )
        self.table.itemChanged.connect(self._on_item_changed)

        # fejléc + fix oszlopszélességek
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)

        


        for c in range(self.table.columnCount()):
            hdr.setSectionResizeMode(c, QHeaderView.Fixed)

        # Oszlopszélességek beállítása

        widths = self._get_column_widths()

        for c in range(self.table.columnCount()):
            w = widths[c] if c < len(widths) else 110
            self.table.setColumnWidth(c, w)





        # --- Belső tabok a Kezdőoldalon ---
        self.tabs = QTabWidget(content)
        self.tabs.setObjectName("homeTabs")


       





        # 1) Kezdőoldal TAB
        tab_dashboard = QWidget()
        dash_layout = QVBoxLayout(tab_dashboard)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_layout.setSpacing(12)

        # ---- FELSŐ SZÁMÍTOTT PANEL ----
        self.summary = HomeSummaryPanel(self)
        dash_layout.addWidget(self.summary)

        
        # kis térköz
        dash_layout.addSpacing(8)

        # --- Havi dashboard card ---
        table_card = QFrame()
        table_card.setObjectName("homeTableCard")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(12, 12, 12, 12)
        table_card_layout.setSpacing(8)

        table_title = QLabel("Havi összesítő")
        table_title.setObjectName("sectionTitle")
        table_card_layout.addWidget(table_title)

        # tábla viselkedés
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.table.setMinimumHeight(0)

        table_card_layout.addWidget(self.table)

        dash_layout.addWidget(table_card, 0)
        dash_layout.addStretch(1)




       








        # 2) Számlák TAB
        tab_bills = QWidget()
        bills_layout = QVBoxLayout(tab_bills)
        bills_layout.setContentsMargins(0, 0, 0, 0)
        bills_layout.setSpacing(12)

        # Felül: számlainfók "kártya"
        info_card = QFrame()
        info_card.setObjectName("bankInfoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(6)

        info_title = QLabel("Raiffeisen Bank számlainfók")
        info_title.setObjectName("sectionTitle")

        self.lbl_total_balance = QLabel("Teljes egyenleg: –")
        self.lbl_metal_balance = QLabel("Nemesfém egyenleg: –")
        self.lbl_cash_balance = QLabel("Készpénz: –")

        info_layout.addWidget(info_title)
        info_layout.addWidget(self.lbl_total_balance)
        info_layout.addWidget(self.lbl_metal_balance)
        info_layout.addWidget(self.lbl_cash_balance)

        bills_layout.addWidget(info_card)

        # Alul: ide jön majd a számlák listája/táblája (később)
        placeholder = QLabel("Számlák listája (hamarosan)")
        placeholder.setObjectName("mutedText")
        bills_layout.addWidget(placeholder, 1)

        # Tabok felvétele
        self.tabs.addTab(tab_dashboard, "Kezdőoldal")
        self.tabs.addTab(tab_bills, "Számlák")

        # TabWidget a content-be
        content_layout.addWidget(self.tabs)

        # --- összerakás ---
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(content, 1)

        self.reload()

        self.table.resizeRowsToContents()
        self._update_table_height()





        self._updating = False



    def _get_headers(self) -> list[str]:

     # --- Dashboard tábla ---
        # Oszlopok: (átnevezhető, de sorrend maradjon !!)

        if not self.dev_mode:          # normál mód
            return [
                "Hónap",
                "Tervezett Bevétel",
                "Valós Bevétel",
                "Eltérések",
                "Tervezett Kiadások",
                "Fix Ter. Kiad.",
                "Valós Kiadások",
                "Eltérések",
                "Terv. Megtakarítás",
                "Valós Megtakarítás",
            ]

            

        return [                        # dev_mode
            "Hónap",
            "Terv Bev",
            "Valós Bev",
            "Δ Bev",
            "Terv Kiad",
            "Valós Kiad",
            "Δ Kiad",
            "Megtakarítás",
        ]

            
    def _get_column_widths(self) -> list[int]:
        if not self.dev_mode:           # normál mód
            return [120, 150, 150, 130, 150, 110, 150, 130, 160, 160]

                                        # dev_mode
        return [120, 130, 130, 110, 130, 130, 110, 150]







    def _make_item(self, val: float, editable: bool) -> QTableWidgetItem:
        it = QTableWidgetItem(fmt_huf(val))
        it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        flags = it.flags()
        if editable:
            it.setFlags(flags | Qt.ItemIsEditable)
        else:
            it.setFlags(flags & ~Qt.ItemIsEditable)

        return it
            



    def _build_summary_rows(self) -> list[HomeSummaryRow]:
        rows: list[HomeSummaryRow] = []

        actual = self.ctx.db.get_monthly_income_expense_bills(self._year)
        plans = self.ctx.db.get_year_plans(self._year)

        for month in range(1, 13):
            p_income, p_expense, p_fixed = plans.get(month, (0.0, 0.0, 0.0))
            income, expense_core, bills = actual.get(month, (0.0, 0.0, 0.0))

            actual_expense = float(expense_core) + float(bills)

            income_diff = float(income) - float(p_income)
            planned_total_expense = float(p_expense) + float(p_fixed)
            expense_diff = float(actual_expense) - float(planned_total_expense)

            planned_savings = float(p_income) - float(planned_total_expense)
            actual_savings = float(income) - float(actual_expense)

            rows.append(
                HomeSummaryRow(
                    month_label=MONTHS_HU[month - 1],
                    planned_income=float(p_income),
                    actual_income=float(income),
                    income_diff=float(income_diff),
                    planned_expense=float(p_expense),
                    planned_fixed_expense=float(p_fixed),
                    actual_expense=float(actual_expense),
                    expense_diff=float(expense_diff),
                    planned_savings=float(planned_savings),
                    actual_savings=float(actual_savings),
                )
            )

        return rows


        

































    def _update_table_height(self) -> None:
        header_h = self.table.horizontalHeader().height()
        rows_h = sum(self.table.rowHeight(r) for r in range(self.table.rowCount()))
        frame_h = self.table.frameWidth() * 2
        extra = 8
        self.table.setFixedHeight(header_h + rows_h + frame_h + extra)


    def set_year(self, year: int) -> None:
        self._year = int(year)
        self.reload()

    
    
    
    
    
    def reload(self) -> None:
        if not isValid(self.table):
            return

        self._updating = True
        try:
            rows = self._build_summary_rows()

            if not self.dev_mode:
                self._render_normal_rows(rows)
            else:
                self._render_dev_rows(rows)

            cash, bank, sec, metal, total = self.ctx.db.get_dashboard_balances()

            self.summary.set_balances(
                cash_balance=cash,
                bank_balance=bank,
                securities_balance=sec,
                metal_balance=metal,
            )

        finally:
            self._updating = False




    # Normál mód:
    def _render_normal_rows(self, rows: list[HomeSummaryRow]) -> None:
        for r, row in enumerate(rows):
            self.table.setItem(r, 1, self._make_item(row.planned_income, True))
            self.table.setItem(r, 2, self._make_item(row.actual_income, False))
            self.table.setItem(r, 3, self._make_item(row.income_diff, False))

            self.table.setItem(r, 4, self._make_item(row.planned_expense, True))
            self.table.setItem(r, 5, self._make_item(row.planned_fixed_expense, True))
            self.table.setItem(r, 6, self._make_item(row.actual_expense, False))
            self.table.setItem(r, 7, self._make_item(row.expense_diff, False))

            self.table.setItem(r, 8, self._make_item(row.planned_savings, False))
            self.table.setItem(r, 9, self._make_item(row.actual_savings, False))


    # DEV mód:
    def _render_dev_rows(self, rows: list[HomeSummaryRow]) -> None:
        for r, row in enumerate(rows):
            self.table.setItem(r, 1, self._make_item(row.planned_income, True))
            self.table.setItem(r, 2, self._make_item(row.actual_income, False))
            self.table.setItem(r, 3, self._make_item(row.income_diff, False))

            self.table.setItem(r, 4, self._make_item(row.planned_expense, True))
            self.table.setItem(r, 5, self._make_item(row.actual_expense, False))
            self.table.setItem(r, 6, self._make_item(row.expense_diff, False))
            self.table.setItem(r, 7, self._make_item(row.actual_savings, False))




























    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return

        row = item.row()
        col = item.column()
        month = row + 1
        value = parse_huf(item.text())

        if not self.dev_mode:
            if col not in (1, 4, 5):
                return

            if col == 1:
                self.ctx.db.upsert_month_plan(self._year, month, planned_income=value)
            elif col == 4:
                self.ctx.db.upsert_month_plan(self._year, month, planned_expense=value)
            else:
                self.ctx.db.upsert_month_plan(
                    self._year,
                    month,
                    planned_fixed_expense=value,
                )
        else:
            if col not in (1, 4):
                return

            if col == 1:
                self.ctx.db.upsert_month_plan(self._year, month, planned_income=value)
            else:
                self.ctx.db.upsert_month_plan(self._year, month, planned_expense=value)

        self.reload()

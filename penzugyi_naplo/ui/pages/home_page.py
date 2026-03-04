# - ui/pages/home_page.py
# ---------------------------


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
    from ui.main_window import MainWindow

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

from penzugyi_naplo.ui.widgets.home_summary_panel import HomeSummaryPanel

# - Importok vége - #


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

    def __init__(
        self, main_window: MainWindow, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.main = main_window
        self._year = int(
            getattr(getattr(main_window, "state", None), "active_year", 2026)
        )

        self._updating = False

        # --- UI felépítése ---
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Kezdőoldal")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
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

        # --- Dashboard tábla ---
        # Oszlopok: (átnevezhető, de sorrend maradjon !!)

        headers = [
            "Hónap",
            "Tervezett bevétel",
            "Tényleges bevétel",
            "Bevétel eltérések",
            "Tervezett kiadás",
            "Fix terv",
            "Tényleges kiadás",
            "Kiadás eltérések",
            "Tervezett megtakarítás",
            "Tényleges megtakarítás",
        ]

        # Táblázat méretezése:

        # --- Havi dashboard tábla ---

        self.table = QTableWidget(12, len(headers), content)
        self.table.setObjectName("homeMonthlyTable")

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
        widths = [120, 150, 150, 130, 150, 110, 150, 130, 160, 160]
        for c in range(self.table.columnCount()):
            w = widths[c] if c < len(widths) else 110  # fallback, ha bővül a tábla
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

        # Havi tábla
        dash_layout.addWidget(self.table, 1)

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
        self._updating = False

    def set_year(self, year: int) -> None:
        self._year = int(year)
        self.reload()

    def reload(self) -> None:
        """
        Terv–Tény dashboard:
        - Tény: transactions-ből (get_monthly_income_expense_bills)
        - Terv: plans-ből (get_year_plans)
        - Számolt: Δ + megtakarítás
        """

        if not isValid(self.table):
            return

        self._updating = True
        try:
            # Tények (income, expense_core, bills)
            actual = self.main.db.get_monthly_income_expense_bills(self._year)

            # Tervek (month -> (planned_income, planned_expense, planned_fixed_expense))
            # Ha még nincs meg DB-ben, ezt a metódust a TransactionDatabase-be kell felvenni.
            plans = self.main.db.get_year_plans(self._year)

            for month in range(1, 13):
                r = month - 1

                # --- tervek ---
                p_income, p_expense, p_fixed = plans.get(month, (0.0, 0.0, 0.0))

                # --- tények ---
                income, expense_core, bills = actual.get(month, (0.0, 0.0, 0.0))
                a_expense = float(expense_core) + float(bills)

                # --- számolt ---
                d_income = float(income) - float(p_income)

                p_total_exp = float(p_expense) + float(p_fixed)
                d_expense = float(a_expense) - float(p_total_exp)

                p_sav = float(p_income) - float(p_total_exp)
                a_sav = float(income) - float(a_expense)

                def make_item(val: float, editable: bool) -> QTableWidgetItem:
                    it = QTableWidgetItem(fmt_huf(val))
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    flags = it.flags()
                    if editable:
                        it.setFlags(flags | Qt.ItemIsEditable)
                    else:
                        it.setFlags(flags & ~Qt.ItemIsEditable)
                    return it

                # Oszlopok:
                # 0 Hónap (már be van töltve initben)
                # 1 Bev terv (edit)
                # 2 Bev tény
                # 3 Δ bev
                # 4 Kiad terv (edit)
                # 5 Fix terv (edit)
                # 6 Kiad tény
                # 7 Δ kiad
                # 8 Megt terv
                # 9 Megt tény

                self.table.setItem(r, 1, make_item(p_income, True))
                self.table.setItem(r, 2, make_item(income, False))
                self.table.setItem(r, 3, make_item(d_income, False))

                self.table.setItem(r, 4, make_item(p_expense, True))
                self.table.setItem(r, 5, make_item(p_fixed, True))
                self.table.setItem(r, 6, make_item(a_expense, False))
                self.table.setItem(r, 7, make_item(d_expense, False))

                self.table.setItem(r, 8, make_item(p_sav, False))
                self.table.setItem(r, 9, make_item(a_sav, False))

            # ---- Dashboard felső panel frissítése ----
            bank, sec, metal, total = self.main.db.get_dashboard_balances()

            self.summary.set_balances(
                bank_balance=bank,
                securities_balance=sec,
                metal_balance=metal,
                cash_balance=0.0,  # ha nincs külön
            )

        finally:
            self._updating = False

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return

        row = item.row()
        col = item.column()
        month = row + 1

        # csak terv oszlopok: 1=bev terv, 4=kiad terv, 5=fix terv
        if col not in (1, 4, 5):
            return

        value = parse_huf(item.text())

        if col == 1:
            self.main.db.upsert_month_plan(self._year, month, planned_income=value)
        elif col == 4:
            self.main.db.upsert_month_plan(self._year, month, planned_expense=value)
        else:  # col == 5
            self.main.db.upsert_month_plan(
                self._year, month, planned_fixed_expense=value
            )

        # frissítés: Δ és megtakarítás újraszámolása
        self.reload()

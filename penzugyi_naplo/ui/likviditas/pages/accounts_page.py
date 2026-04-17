"""penzugyi_naplo/ui/pages/accounts_page.py

"Pénztárcák / számlaegyenlegek" oldal.

Cél (most, v1):
  - Megmutatni a dashboard jellegű egyenlegeket:
      * Folyószámla (bevétel - kiadás)
      * Értékpapírok (kézi értékfelvitel, legutolsó)
      * Nemesfém (kézi értékfelvitel, legutolsó)
      * Összesen
  - Kézi érték rögzítése 'account_valuations' táblába (securities / metals)

Megjegyzés:
  - A "Számlák" nálad bills (kötelezők, szolgáltatók).
  - Ez az oldal inkább Accounts/Wallets jellegű (egyenlegek/értékek).
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from penzugyi_naplo.config import is_dev_mode
from penzugyi_naplo.ui.shared.pages.base_page import BasePage

if TYPE_CHECKING:
    from penzugyi_naplo.db.transaction_database import TransactionDatabase


def _hline(parent: QWidget | None = None) -> QFrame:
    line = QFrame(parent)
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line


def _vline(parent: QWidget | None = None) -> QFrame:
    line = QFrame(parent)
    line.setFrameShape(QFrame.VLine)
    line.setFrameShadow(QFrame.Sunken)
    return line


class AccountsPage(BasePage):
    """Egyszerű Accounts/Wallets oldal."""

    def __init__(self, parent: Optional[QWidget] = None, *, db: Optional["TransactionDatabase"] = None, ) -> None:
        super().__init__(parent)
        self._db: Optional["TransactionDatabase"] = db

        self._year = None
        
        self._dev_mode = is_dev_mode()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Pénztárcák / Egyenlegek", self)
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(title)

        root.addWidget(_hline(self))

        self.lbl_cash = self._make_kpi("Kézpénz")
        self.lbl_current_account = self._make_kpi("Folyószámla")
        self.lbl_securities = self._make_kpi("Értékpapírok")
        self.lbl_metals = self._make_kpi("Nemesfémek")
        self.lbl_total = self._make_kpi("Összesen", emphasized=True)

        # --- teljes KPI wrapper ---
        kpi_wrap = QWidget(self)
        kpi_wrap_lay = QHBoxLayout(kpi_wrap)
        kpi_wrap_lay.setContentsMargins(0, 0, 0, 0)
        kpi_wrap_lay.setSpacing(10)

        # --- 1) Kézpénz blokk ---
        cash_block = QWidget(kpi_wrap)
        cash_block_lay = QVBoxLayout(cash_block)
        cash_block_lay.setContentsMargins(0, 0, 0, 0)
        cash_block_lay.setSpacing(4)

        cash_block_lay.addSpacing(
            22
        )  # hogy függőlegesen kb. a többi KPI sorához igazodjon
        cash_block_lay.addWidget(self.lbl_cash[0])

        # --- 2) Bank blokk ---
        bank_block = QWidget(kpi_wrap)
        bank_block_lay = QVBoxLayout(bank_block)
        bank_block_lay.setContentsMargins(0, 0, 0, 0)
        bank_block_lay.setSpacing(4)

        lbl_bank = QLabel("Bank:", bank_block)
        lbl_bank.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        lbl_bank.setStyleSheet("font-weight: 600;")
        bank_block_lay.addWidget(lbl_bank)

        bank_row = QWidget(bank_block)
        bank_row_lay = QHBoxLayout(bank_row)
        bank_row_lay.setContentsMargins(0, 0, 0, 0)
        bank_row_lay.setSpacing(8)

        bank_row_lay.addWidget(self.lbl_current_account[0])
        bank_row_lay.addWidget(self.lbl_securities[0])

        bank_block_lay.addWidget(bank_row)

        # --- 3) Nemesfémek blokk ---
        metals_block = QWidget(kpi_wrap)
        metals_block_lay = QVBoxLayout(metals_block)
        metals_block_lay.setContentsMargins(0, 0, 0, 0)
        metals_block_lay.setSpacing(4)

        metals_block_lay.addSpacing(22)
        metals_block_lay.addWidget(self.lbl_metals[0])

        # --- 4) Összesen blokk ---
        total_block = QWidget(kpi_wrap)
        total_block_lay = QVBoxLayout(total_block)
        total_block_lay.setContentsMargins(0, 0, 0, 0)
        total_block_lay.setSpacing(4)

        total_block_lay.addSpacing(22)
        total_block_lay.addWidget(self.lbl_total[0])

        # --- összeállítás ---

        kpi_wrap_lay.addWidget(cash_block)
        kpi_wrap_lay.addSpacing(8)

        kpi_wrap_lay.addWidget(_vline(kpi_wrap))
        kpi_wrap_lay.addSpacing(8)

        kpi_wrap_lay.addWidget(bank_block)
        kpi_wrap_lay.addSpacing(10)

        kpi_wrap_lay.addWidget(_vline(kpi_wrap))
        kpi_wrap_lay.addSpacing(10)

        kpi_wrap_lay.addWidget(metals_block)
        kpi_wrap_lay.addSpacing(10)

        kpi_wrap_lay.addWidget(_vline(kpi_wrap))
        kpi_wrap_lay.addSpacing(10)

        kpi_wrap_lay.addWidget(total_block)
        kpi_wrap_lay.addStretch(1)

        root.addWidget(kpi_wrap)

        # a KPI dobozok ne nyúljanak túl szélesre
        self.lbl_cash[0].setMaximumWidth(110)
        self.lbl_current_account[0].setMaximumWidth(120)
        self.lbl_metals[0].setMaximumWidth(120)
        self.lbl_securities[0].setMaximumWidth(120)
        self.lbl_total[0].setMaximumWidth(120)

        # --- Kézi értékfelvitel (securities/metals) ---
        box = QGroupBox("Kézi érték rögzítése", self)
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.cmb_type = QComboBox(box)
        self.cmb_type.addItem("Kézpénz", "cash")
        self.cmb_type.addItem("Folyószámla", "current_account")
        self.cmb_type.addItem("Értékpapírok", "securities")
        self.cmb_type.addItem("Nemesfémek", "metals")

        self.dt_date = QDateEdit(box)
        self.dt_date.setCalendarPopup(True)
        self.dt_date.setDisplayFormat("yyyy-MM-dd")
        self.dt_date.setDate(date.today())

        self.sp_value = QDoubleSpinBox(box)
        self.sp_value.setDecimals(0)
        self.sp_value.setRange(0.0, 10_000_000_000.0)
        self.sp_value.setSingleStep(1000.0)
        self.sp_value.setSuffix(" Ft")

        self.btn_save = QPushButton("Mentés", box)
        self.btn_save.clicked.connect(self._on_save)

        # - méret beállítások:
        self.cmb_type.setMaximumWidth(220)
        self.dt_date.setMaximumWidth(160)
        self.sp_value.setMaximumWidth(180)
        self.btn_save.setMaximumWidth(120)

        row_btn = QWidget(box)
        row_btn_lay = QHBoxLayout(row_btn)
        row_btn_lay.setContentsMargins(0, 0, 0, 0)

        row_btn_lay.addWidget(self.btn_save)
        row_btn_lay.addStretch(1)

        form.addRow("Típus:", self.cmb_type)
        form.addRow("Dátum:", self.dt_date)
        form.addRow("Érték:", self.sp_value)
        form.addRow("", row_btn)
        root.addWidget(box)

        # --- Előzmények (utolsó N rekord) ---
        hist_box = QGroupBox("Előzmények (utolsó 30)", self)
        hist_lay = QVBoxLayout(hist_box)
        self.tbl = QTableWidget(hist_box)
        self.tbl.setColumnCount(3)
        self.tbl.setHorizontalHeaderLabels(["Dátum", "Típus", "Érték"])
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        hist_lay.addWidget(self.tbl)
        root.addWidget(hist_box, 1)

        root.addStretch(0)

        self.reload()

    def _make_kpi(
        self,
        title: str,
        *,
        emphasized: bool = False,
    ) -> tuple[QGroupBox, QLabel]:
        box = QGroupBox(title, self)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 8, 10, 8)

        if emphasized:
            box.setStyleSheet("""
                QGroupBox {
                    font-weight: 700;
                }
             """)

        value = QLabel("—", box)
        value.setObjectName("kpiValue")
        value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        font = value.font()
        if emphasized:
            font.setBold(True)
            font.setPointSize(font.pointSize() + 1)
        value.setFont(font)

        lay.addWidget(value)
        return box, value

    def bind_db(self, db: "TransactionDatabase") -> None:
        self._db = db

    def reload(self) -> None:
        """MainWindow hívhatja set_page-nél vagy DB csere után."""
        
        if not self._db:
            self._set_kpis(None, None, None, None, None)
            self.tbl.setRowCount(0)
            return
        
        year = self._year

        # Készpénz (utolsó)
        cash_row = self._db.get_latest_wallet_balance("cash", year=year)
        current_account_row = self._db.get_latest_wallet_balance("current_account", year=year)

        cash = float(cash_row["value"]) if cash_row else None
        current_account = (
            float(current_account_row["value"]) if current_account_row else None
        )

        # Értékpapírok / Nemesfém (utolsó)
        sec_row = self._db.get_latest_account_valuation("securities", year=year)
        met_row = self._db.get_latest_account_valuation("metals", year=year)
        sec = float(sec_row["value"]) if sec_row else None
        met = float(met_row["value"]) if met_row else None

        total = sum(v for v in (cash, current_account, sec, met) if v is not None)
        self._set_kpis(cash, current_account, sec, met, total)
        self._load_history()

    def _set_kpis(
        self,
        cash: float | None,
        current_account: float | None,
        securities: float | None,
        metals: float | None,
        total: float | None,
    ) -> None:

        def fmt(v: float | None) -> str:
            if v is None:
                return "—"
            return f"{v:,.0f} Ft".replace(",", " ")

        self.lbl_cash[1].setText(fmt(cash))

        self.lbl_current_account[1].setText(fmt(current_account))

        self.lbl_securities[1].setText(fmt(securities))
        self.lbl_metals[1].setText(fmt(metals))
        self.lbl_total[1].setText(fmt(total))

    def _load_history(self) -> None:
        if not self._db:
            return

        rows = self._db.list_accounts_history(limit=30)
        self.tbl.setRowCount(len(rows))

        def type_label(t: str) -> str:
            if t == "cash":
                return "Készpénz"
            if t == "current_account":
                return "Folyószámla"
            if t == "securities":
                return "Értékpapírok"
            if t == "metals":
                return "Nemesfémek"
            return t

        for r, rec in enumerate(rows):
            self.tbl.setItem(r, 0, QTableWidgetItem(str(rec["date"])))
            self.tbl.setItem(
                r, 1, QTableWidgetItem(type_label(str(rec["account_type"])))
            )

            val = float(rec["value"] or 0.0)
            it = QTableWidgetItem(f"{val:,.0f} Ft".replace(",", " "))
            it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.tbl.setItem(r, 2, it)

        self.tbl.resizeColumnsToContents()
        self.tbl.horizontalHeader().setStretchLastSection(True)

    def _on_save(self) -> None:
        if not self._db:
            return

        t = str(self.cmb_type.currentData())
        d = self.dt_date.date().toPython()  # datetime.date
        date_iso = d.isoformat()
        value = float(self.sp_value.value())

        # 0 érték mentése is lehet valid (lenullázás), ezért nem tiltjuk

        if t in ("cash", "current_account"):
            # készpénz külön táblába
            self._db.set_wallet_balance(date_iso, t, value)
        else:
            # securities / metals
            self._db.add_account_valuation(date_iso, t, value)

        self.sp_value.setValue(0.0)
        self.reload()



    def set_year(self, year: int) -> None:
        self._year = int(year)
        self.reload()
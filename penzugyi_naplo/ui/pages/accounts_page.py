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
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from penzugyi_naplo.ui.pages.base_page import BasePage

if TYPE_CHECKING:
    from penzugyi_naplo.db.transaction_database import TransactionDatabase


def _hline(parent: QWidget | None = None) -> QFrame:
    line = QFrame(parent)
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line


class AccountsPage(BasePage):
    """Egyszerű Accounts/Wallets oldal."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        db: Optional["TransactionDatabase"] = None,
    ) -> None:
        super().__init__(parent)
        self._db: Optional["TransactionDatabase"] = db

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Pénztárcák / Egyenlegek", self)
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(title)

        root.addWidget(_hline(self))

        # --- Összesítő kártyák (4 mező) ---
        self._cards = QWidget(self)
        cards_lay = QGridLayout(self._cards)
        cards_lay.setContentsMargins(0, 0, 0, 0)
        cards_lay.setHorizontalSpacing(12)
        cards_lay.setVerticalSpacing(12)

        self.lbl_cash = self._make_kpi("Készpénz (utolsó)")
        self.lbl_securities = self._make_kpi("Értékpapírok (utolsó)")
        self.lbl_metals = self._make_kpi("Nemesfém (utolsó)")
        self.lbl_total = self._make_kpi("Összesen")

        cards_lay.addWidget(self.lbl_cash[0], 0, 0)
        cards_lay.addWidget(self.lbl_securities[0], 0, 1)
        cards_lay.addWidget(self.lbl_metals[0], 1, 0)
        cards_lay.addWidget(self.lbl_total[0], 1, 1)

        # --- Kézi értékfelvitel (securities/metals) ---
        box = QGroupBox("Kézi érték rögzítése", self)
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.cmb_type = QComboBox(box)
        self.cmb_type.addItem("Készpénz", "cash")
        self.cmb_type.addItem("Értékpapírok", "securities")
        self.cmb_type.addItem("Nemesfém", "metals")

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

        row_btn = QWidget(box)
        row_btn_lay = QHBoxLayout(row_btn)
        row_btn_lay.setContentsMargins(0, 0, 0, 0)
        row_btn_lay.addStretch(1)
        row_btn_lay.addWidget(self.btn_save)

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

    def _make_kpi(self, title: str) -> tuple[QGroupBox, QLabel]:
        box = QGroupBox(title, self)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(12, 10, 12, 10)
        value = QLabel("—", box)
        value.setObjectName("kpiValue")
        value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lay.addWidget(value)
        return box, value

    def bind_db(self, db: "TransactionDatabase") -> None:
        self._db = db

    def reload(self) -> None:
        """MainWindow hívhatja set_page-nél vagy DB csere után."""
        if not self._db:
            self._set_kpis(None, None, None, None)
            self.tbl.setRowCount(0)
            return

        # Készpénz (utolsó)
        cash_row = self._db.get_latest_wallet_balance("cash")
        cash = float(cash_row["value"]) if cash_row else None

        # Értékpapírok / Nemesfém (utolsó)
        sec_row = self._db.get_latest_account_valuation("securities")
        met_row = self._db.get_latest_account_valuation("metals")
        sec = float(sec_row["value"]) if sec_row else None
        met = float(met_row["value"]) if met_row else None

        total = None
        if cash is not None or sec is not None or met is not None:
            total = float(cash or 0.0) + float(sec or 0.0) + float(met or 0.0)

        self._set_kpis(cash, sec, met, total)
        self._load_history()

    def _set_kpis(
        self,
        cash: float | None,
        securities: float | None,
        metals: float | None,
        total: float | None,
    ) -> None:
        def fmt(v: float | None) -> str:
            if v is None:
                return "—"
            return f"{v:,.0f} Ft".replace(",", " ")

        # FIGYELEM: itt már lbl_cash kell, nem lbl_bank
        self.lbl_cash[1].setText(fmt(cash))
        self.lbl_securities[1].setText(fmt(securities))
        self.lbl_metals[1].setText(fmt(metals))
        self.lbl_total[1].setText(fmt(total))

    def _load_history(self) -> None:
        if not self._db:
            return

        rows = self._db.list_account_valuations(limit=30)
        self.tbl.setRowCount(len(rows))

        def type_label(t: str) -> str:
            return (
                "Értékpapírok"
                if t == "securities"
                else "Nemesfém"
                if t == "metals"
                else t
            )

        for r, rec in enumerate(rows):
            self.tbl.setItem(r, 0, QTableWidgetItem(str(rec["date"])))
            self.tbl.setItem(
                r, 1, QTableWidgetItem(type_label(str(rec["account_type"])))
            )
            val = float(rec["value"] or 0.0)
            it = QTableWidgetItem(f"{val:,.0f} Ft".replace(",", " "))
            it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
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

        if t == "cash":
            # készpénz külön táblába
            self._db.set_wallet_balance(date_iso, "cash", value)
        else:
            # securities / metals
            self._db.add_account_valuation(date_iso, t, value)

        self.sp_value.setValue(0.0)
        self.reload()

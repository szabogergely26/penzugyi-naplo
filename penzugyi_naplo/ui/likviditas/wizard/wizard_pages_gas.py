# penzugyi_naplo/ui/likviditas/wizard/wizard_pages_gas.py
# --------------------------------------------------------------
# Likviditás / Tranzakciórögzítő varázsló — MVMNext Gáz oldalak
# --------------------------------------------------------------

"""
Az MVMNext Gáz számlabefizetés külön, 3 oldalra bontott flow-ja
(a Villany flow változatlanul a PageAmount-on marad, lásd wizard_pages_bill.py).

Azért külön oldalak, mert egy lapon (a korábbi közös PageAmount-on) túl sok
mező zsúfolódott össze, ami nagyobb ablakméretnél is rendezetlennek tűnt.

- PageGasAmount (id 7): Összeg, Számla sorszáma + korrekció jelölő,
  Elszámolási időszak (kezdet-vég), Elszámolt hónap dátuma
- PageGasMeter (id 8): Fogyasztás (m³, MJ) — mindkettő opcionális
- PageGasSummary (id 9): visszaigazolás a fentiekről + kategória/szolgáltató
  név, mentés ("Mentés" gomb, ez a final page)

A PageGasSummary mindig az initializePage()-ben állítja össze a kijelzett
szöveget, hogy Vissza + módosítás + újra Előre esetén is friss adatot mutasson.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWizardPage,
)

from penzugyi_naplo.core.utils import is_valid_date, parse_amount

from .wizard_helpers import create_transaction_wizard_page_layout


class PageGasAmount(QWizardPage):
    """Gáz 1. oldal: összeg, számla sorszáma, elszámolási időszak, elszámolt hónap."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Gáz számla összege")
        self.setSubTitle("Add meg a kifizetett összeget és a számla adatait.")

        layout, self.side_title_label, self.side_subtitle_label = create_transaction_wizard_page_layout(
            self,
            "🔥",
            "Gáz számla",
            "Összeg, számla sorszáma és elszámolási időszak.",
        )

        layout.addWidget(QLabel("Kifizetett összeg (HUF):"))
        self.input_amount = QLineEdit()
        self.input_amount.setPlaceholderText("Csak pozitív szám (pl. 20000)")
        layout.addWidget(self.input_amount)

        self.lbl_invoice_number = QLabel("Számla sorszáma:")
        self.input_invoice_number = QLineEdit()
        self.input_invoice_number.setPlaceholderText("Pl.: 1234567890")
        layout.addWidget(self.lbl_invoice_number)
        layout.addWidget(self.input_invoice_number)

        self.chk_is_correction = QCheckBox("Ez korrekció / jóváírás (nem önálló számla)")
        self.chk_is_correction.setObjectName("transactionWizardCorrectionCheckbox")
        layout.addWidget(self.chk_is_correction)

        self.lbl_period_start = QLabel("Elszámolási időszak kezdete (YYYY-MM-DD):")
        self.input_period_start = QLineEdit()
        self.input_period_start.setPlaceholderText("Pl.: 2025-03-15")
        layout.addWidget(self.lbl_period_start)
        layout.addWidget(self.input_period_start)

        self.lbl_period_end = QLabel("Elszámolási időszak vége (YYYY-MM-DD):")
        self.input_period_end = QLineEdit()
        self.input_period_end.setPlaceholderText("Pl.: 2025-04-15")
        layout.addWidget(self.lbl_period_end)
        layout.addWidget(self.input_period_end)

        self.lbl_date = QLabel("Elszámolt hónap dátuma (YYYY-MM-DD):")
        self.input_date = QLineEdit()
        self.input_date.setText(datetime.now().strftime("%Y-%m-%d"))
        layout.addWidget(self.lbl_date)
        layout.addWidget(self.input_date)

        layout.addStretch(1)

    def initializePage(self) -> None:
        super().initializePage()
        # minden belépéskor friss dátummal induljon, ha még üres
        if not self.input_date.text().strip():
            self.input_date.setText(datetime.now().strftime("%Y-%m-%d"))

    def validatePage(self) -> bool:
        amount_str = self.input_amount.text().strip()
        try:
            loc = QLocale.system()
            gs = loc.groupSeparator()
            dp = loc.decimalPoint()
            amount = parse_amount(amount_str, group_sep=gs, decimal_point=dp)
            if amount <= 0:
                QMessageBox.warning(self, "Hiba", "Kérjük, adjon meg pozitív összeget.")
                return False
        except ValueError:
            QMessageBox.warning(
                self, "Hiba", "Érvénytelen összeg formátum. Csak számokat használjon."
            )
            return False

        payment_date = is_valid_date(self.input_date.text().strip())
        if not payment_date:
            QMessageBox.warning(
                self,
                "Hiba",
                "Érvénytelen elszámolt hónap dátum! Használj YYYY-M-D vagy YYYY-MM-DD formátumot.",
            )
            return False

        period_start = is_valid_date(self.input_period_start.text().strip())
        if not period_start:
            QMessageBox.warning(
                self,
                "Hiba",
                "Érvénytelen időszak kezdete! Használj YYYY-M-D vagy YYYY-MM-DD formátumot.",
            )
            return False

        period_end = is_valid_date(self.input_period_end.text().strip())
        if not period_end:
            QMessageBox.warning(
                self,
                "Hiba",
                "Érvénytelen időszak vége! Használj YYYY-M-D vagy YYYY-MM-DD formátumot.",
            )
            return False

        if period_start > period_end:
            QMessageBox.warning(
                self,
                "Hiba",
                "Az időszak kezdete nem lehet későbbi, mint az időszak vége.",
            )
            return False

        return True

    def get_amount(self) -> float:
        amount_str = self.input_amount.text().strip()
        loc = QLocale.system()
        gs = loc.groupSeparator()
        dp = loc.decimalPoint()
        return abs(parse_amount(amount_str, group_sep=gs, decimal_point=dp))

    def get_bill_date_raw(self) -> str:
        return self.input_date.text().strip()

    def get_period_start_raw(self) -> str:
        return self.input_period_start.text().strip()

    def get_period_end_raw(self) -> str:
        return self.input_period_end.text().strip()

    def get_invoice_number_raw(self) -> str:
        return self.input_invoice_number.text().strip()

    def get_is_correction(self) -> bool:
        return self.chk_is_correction.isChecked()

    def reset_gas_fields(self) -> None:
        self.input_amount.clear()
        self.input_invoice_number.clear()
        self.chk_is_correction.setChecked(False)
        self.input_period_start.clear()
        self.input_period_end.clear()
        self.input_date.setText(datetime.now().strftime("%Y-%m-%d"))

    def nextId(self) -> int:
        return 8


class PageGasMeter(QWizardPage):
    """Gáz 2. oldal: fogyasztás mérőóra-értéke (m³ és/vagy MJ), mindkettő opcionális."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Gáz fogyasztás")
        self.setSubTitle("Add meg a mérőóra fogyasztási adatait (nem kötelező).")

        layout, self.side_title_label, self.side_subtitle_label = create_transaction_wizard_page_layout(
            self,
            "📟",
            "Fogyasztás",
            "A mérőóra fogyasztási adatai, ha ismertek.",
        )

        label = QLabel("Cím: fogyasztás")
        label.setObjectName("transactionWizardSectionTitle")
        layout.addWidget(label)

        self.lbl_meter_m3 = QLabel("Fogyasztás (m³):")
        self.input_meter_m3 = QLineEdit()
        self.input_meter_m3.setPlaceholderText("Pl.: 53 (nem kötelező)")
        layout.addWidget(self.lbl_meter_m3)
        layout.addWidget(self.input_meter_m3)

        self.lbl_meter_mj = QLabel("Fogyasztás (MJ):")
        self.input_meter_mj = QLineEdit()
        self.input_meter_mj.setPlaceholderText("Pl.: 1871 (nem kötelező)")
        layout.addWidget(self.lbl_meter_mj)
        layout.addWidget(self.input_meter_mj)

        layout.addStretch(1)

    def validatePage(self) -> bool:
        m3_raw = self.input_meter_m3.text().strip()
        if m3_raw:
            try:
                float(m3_raw.replace(",", "."))
            except ValueError:
                QMessageBox.warning(
                    self, "Hiba", "A fogyasztás (m³) mező érvénytelen számot tartalmaz."
                )
                return False

        mj_raw = self.input_meter_mj.text().strip()
        if mj_raw:
            try:
                float(mj_raw.replace(",", "."))
            except ValueError:
                QMessageBox.warning(
                    self, "Hiba", "A fogyasztás (MJ) mező érvénytelen számot tartalmaz."
                )
                return False

        return True

    def get_meter_m3_raw(self) -> str:
        return self.input_meter_m3.text().strip()

    def get_meter_mj_raw(self) -> str:
        return self.input_meter_mj.text().strip()

    def reset_gas_fields(self) -> None:
        self.input_meter_m3.clear()
        self.input_meter_mj.clear()

    def nextId(self) -> int:
        return 9


class PageGasSummary(QWizardPage):
    """
    Gáz 3. oldal: összesítő / visszaigazolás mentés előtt.

    Mindig initializePage()-ben állítja össze a szöveget, hogy Vissza +
    módosítás + újra Előre esetén is friss adatot mutasson.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Összesítés")
        self.setSubTitle("Ellenőrizd az adatokat mentés előtt.")
        self.setFinalPage(True)

        layout, self.side_title_label, self.side_subtitle_label = create_transaction_wizard_page_layout(
            self,
            "✅",
            "Összesítés",
            "Ellenőrizd az adatokat, majd mentsd el a számlát.",
        )

        self.summary_layout = QVBoxLayout()
        self.summary_layout.setSpacing(6)
        layout.addLayout(self.summary_layout)
        layout.addStretch(1)

        self._summary_labels: list[QLabel] = []

    def _clear_summary(self) -> None:
        for lbl in self._summary_labels:
            self.summary_layout.removeWidget(lbl)
            lbl.deleteLater()
        self._summary_labels = []

    def _add_summary_row(self, label_text: str, value_text: str) -> None:
        row = QLabel(f"{label_text} {value_text}")
        row.setObjectName("transactionWizardSummaryRow")
        row.setWordWrap(True)
        self.summary_layout.addWidget(row)
        self._summary_labels.append(row)

    def initializePage(self) -> None:
        super().initializePage()
        self._clear_summary()

        wiz = self.wizard()
        if wiz is None:
            return

        gas_amount_page = wiz.page(7)
        gas_meter_page = wiz.page(8)

        target_name = "MVMNext – Gáz"

        amount = 0.0
        if hasattr(gas_amount_page, "get_amount"):
            try:
                amount = gas_amount_page.get_amount()
            except Exception:
                amount = 0.0

        invoice_number = ""
        if hasattr(gas_amount_page, "get_invoice_number_raw"):
            invoice_number = gas_amount_page.get_invoice_number_raw()

        is_correction = False
        if hasattr(gas_amount_page, "get_is_correction"):
            is_correction = gas_amount_page.get_is_correction()

        period_start = ""
        period_end = ""
        if hasattr(gas_amount_page, "get_period_start_raw"):
            period_start = gas_amount_page.get_period_start_raw()
        if hasattr(gas_amount_page, "get_period_end_raw"):
            period_end = gas_amount_page.get_period_end_raw()

        bill_date = ""
        if hasattr(gas_amount_page, "get_bill_date_raw"):
            bill_date = gas_amount_page.get_bill_date_raw()

        meter_m3 = ""
        meter_mj = ""
        if hasattr(gas_meter_page, "get_meter_m3_raw"):
            meter_m3 = gas_meter_page.get_meter_m3_raw()
        if hasattr(gas_meter_page, "get_meter_mj_raw"):
            meter_mj = gas_meter_page.get_meter_mj_raw()

        amount_text = f"{amount:,.0f}".replace(",", " ") + " Ft"

        self._add_summary_row("Kategória:", target_name)
        self._add_summary_row("Kifizetett összeg:", amount_text)
        self._add_summary_row("Számla sorszáma:", invoice_number or "—")
        if is_correction:
            self._add_summary_row("Megjegyzés:", "Korrekció / jóváírás")
        self._add_summary_row(
            "Elszámolási időszak:", f"{period_start or '—'} – {period_end or '—'}"
        )
        self._add_summary_row("Elszámolt hónap dátuma:", bill_date or "—")

        if meter_m3 or meter_mj:
            if meter_m3 and meter_mj:
                meter_text = f"{meter_m3} m³ ({meter_mj} MJ)"
            elif meter_m3:
                meter_text = f"{meter_m3} m³"
            else:
                meter_text = f"{meter_mj} MJ"
            self._add_summary_row("Fogyasztás:", meter_text)

    def nextId(self) -> int:
        return -1
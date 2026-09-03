# penzugyi_naplo/ui/likviditas/wizard/wizard_transaction.py
# --------------------------------------------------------------
# Likviditás / Tranzakciórögzítő varázsló
# --------------------------------------------------------------

"""
Új tranzakció rögzítésére szolgáló varázsló (QWizard).

Feladata:
- normál bevétel / kiadás rögzítése
- részletezett tételek kezelése
- számlabefizetéses flow kezelése

Megjegyzések:
- az amount B-modell szerint mindig pozitív
- a wizard a MainWindow.db API-n keresztül ment
- közvetlen SQL-t nem tartalmaz

Ez a fájl csak a TransactionWizard fő osztályt tartalmazza (oldalak
összekötése + mentési logika az accept()-ben). Az egyes oldalak külön
fájlokban vannak:
- wizard_helpers.py: parsing és layout segédfüggvények
- wizard_pages_common.py: nem-bill oldalak (típus, kategória, split, részletek)
- wizard_pages_bill.py: bill-specifikus oldalak (szolgáltató, MVM típus, összeg)
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QMessageBox, QWizard

from penzugyi_naplo.core.utils import is_valid_date

from .wizard_helpers import bill_requires_period, parse_details_line
from .wizard_pages_bill import PageAmount, PageBillMvmType, PageBillProvider
from .wizard_pages_common import (
    PageCategorySelection,
    PageDetails,
    PageSplitDecision,
    PageTypeSelection,
)
from .wizard_pages_gas import PageGasAmount, PageGasMeter, PageGasSummary


class TransactionWizard(QWizard):
    """Az új tranzakció rögzítése varázsló."""

    def __init__(self, db, main_window, parent=None) -> None:
        super().__init__(parent)

        self.db = db
        self.main_window = main_window

        self.setWindowTitle("Új Tranzakció Rögzítése")
        self.setMinimumWidth(860)
        self.setMinimumHeight(580)
        self.setObjectName("transactionWizard")

        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)

        self.setButtonText(QWizard.WizardButton.BackButton, "Vissza")
        self.setButtonText(QWizard.WizardButton.NextButton, "Tovább")
        self.setButtonText(QWizard.WizardButton.FinishButton, "Mentés")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Mégse")

        # Oldalak (id-k: 0,1,2,3,4,5,6,7,8,9)
        self.setPage(0, PageTypeSelection())
        self.setPage(1, PageCategorySelection())
        self.setPage(2, PageSplitDecision())
        self.setPage(3, PageAmount())
        self.setPage(4, PageDetails())
        self.setPage(5, PageBillProvider())
        self.setPage(6, PageBillMvmType())
        self.setPage(7, PageGasAmount())
        self.setPage(8, PageGasMeter())
        self.setPage(9, PageGasSummary())

    def accept(self) -> None:
        raw_mode = self.page(0).get_type()  # 'income' / 'expense' / 'bill'
        provider = (self.field("bill_provider") or "").strip()

        # Stabil fallback:
        # ha a bill_provider ki van töltve, akkor ez biztosan bill ág
        mode = "bill" if provider and provider != "Válassz szolgáltatót..." else raw_mode

        has_details = bool(self.field("has_details"))

        # Alapértékek
        category_id = None
        target_name = None
        name = ""
        description = ""
        date_raw = ""
        amount = 0.0
        period_start = None
        period_end = None
        invoice_number = ""
        is_correction = False
        meter_m3: float | None = None
        meter_mj: float | None = None

        # -------------------------------------------------
        # BILL ÁG
        # -------------------------------------------------
        if mode == "bill":
            t_type = "expense"
            is_gaz = provider == "MVMNext" and self.page(6).is_gas()

            if provider == "MVMNext":
                target_name = "MVMNext – Gáz" if is_gaz else "MVMNext – Villany"

            elif provider.startswith("KalászNet"):
                target_name = "Internet (KalászNet)"

            else:
                target_name = "Telekom"

            # category_id lookup DB-ből
            if hasattr(self.db, "get_category_id_by_name"):
                category_id = self.db.get_category_id_by_name(target_name)

            if category_id is None:
                QMessageBox.critical(
                    self,
                    "Hiba",
                    f"Nem található a számla kategória az adatbázisban: {target_name}\n"
                    "Ellenőrizd, hogy a DB seed (bill kategóriák) lefutott-e.",
                )
                return

            name = target_name
            description = "Számlabefizetés"
            has_details = False

            if is_gaz:
                # -----------------------------------------------------
                # GÁZ: külön oldalakról olvasunk (page 7: összeg/sorszám/
                # időszak, page 8: fogyasztás)
                # -----------------------------------------------------
                gas_amount_page = self.page(7)
                gas_meter_page = self.page(8)

                if not gas_amount_page.validatePage():
                    return
                if not gas_meter_page.validatePage():
                    return

                date_raw = gas_amount_page.get_bill_date_raw()
                amount = gas_amount_page.get_amount()
                invoice_number = gas_amount_page.get_invoice_number_raw()
                is_correction = gas_amount_page.get_is_correction()

                meter_m3_raw = gas_meter_page.get_meter_m3_raw()
                if meter_m3_raw:
                    try:
                        meter_m3 = float(meter_m3_raw.replace(",", "."))
                    except ValueError:
                        QMessageBox.critical(
                            self,
                            "Hiba",
                            "A fogyasztás (m³) mező érvénytelen számot tartalmaz.",
                        )
                        return

                meter_mj_raw = gas_meter_page.get_meter_mj_raw()
                if meter_mj_raw:
                    try:
                        meter_mj = float(meter_mj_raw.replace(",", "."))
                    except ValueError:
                        QMessageBox.critical(
                            self,
                            "Hiba",
                            "A fogyasztás (MJ) mező érvénytelen számot tartalmaz.",
                        )
                        return

                period_start_raw = gas_amount_page.get_period_start_raw()
                period_end_raw = gas_amount_page.get_period_end_raw()

                period_start = is_valid_date(period_start_raw)
                period_end = is_valid_date(period_end_raw)

                if not period_start or not period_end:
                    QMessageBox.critical(
                        self,
                        "Hiba",
                        "Az időszak kezdete vagy vége érvénytelen.",
                    )
                    return

                if period_start > period_end:
                    QMessageBox.critical(
                        self,
                        "Hiba",
                        "Az időszak kezdete nem lehet későbbi, mint az időszak vége.",
                    )
                    return

            else:
                # -----------------------------------------------------
                # VILLANY / KALÁSZNET / TELEKOM: marad a közös PageAmount
                # -----------------------------------------------------
                amount_page = self.page(3)

                if not amount_page.validatePage():
                    return

                date_raw = amount_page.get_bill_date_raw()
                amount = amount_page.get_amount()
                invoice_number = amount_page.get_invoice_number_raw()
                is_correction = amount_page.get_is_correction()

                if bill_requires_period(provider):
                    period_start_raw = amount_page.get_period_start_raw()
                    period_end_raw = amount_page.get_period_end_raw()

                    period_start = is_valid_date(period_start_raw)
                    period_end = is_valid_date(period_end_raw)

                    if not period_start or not period_end:
                        QMessageBox.critical(
                            self,
                            "Hiba",
                            "Az időszak kezdete vagy vége érvénytelen.",
                        )
                        return

                    if period_start > period_end:
                        QMessageBox.critical(
                            self,
                            "Hiba",
                            "Az időszak kezdete nem lehet későbbi, mint az időszak vége.",
                        )
                        return

        # -------------------------------------------------
        # NORMÁL ÁG (BEVÉTEL / KIADÁS)
        # -------------------------------------------------
        else:
            t_type = mode
            category_id, name, description, date_raw = self.page(1).get_data()

            if has_details:
                amount = float(self.field("details_total") or 0.0)
            else:
                if not self.page(3).validatePage():
                    return
                amount = self.page(3).get_amount()

            period_start = None
            period_end = None

        # -------------------------------------------------
        # KÖZÖS VALIDÁLÁS
        # -------------------------------------------------
        date = is_valid_date(date_raw)
        if not date:
            QMessageBox.critical(
                self,
                "Hiba",
                "Érvénytelen dátum formátum! Kérjük, YYYY-M-D vagy YYYY-MM-DD formátumot használjon.",
            )
            return

        amount = abs(amount)

        if category_id is None:
            if mode == "bill":
                QMessageBox.critical(
                    self,
                    "Hiba",
                    f"Bill ágban nem sikerült kategóriát találni ehhez: {target_name}",
                )
            else:
                QMessageBox.warning(self, "Hiba", "Kérjük, válasszon kategóriát.")
            return

        name = (name or "").strip()
        description = (description or "").strip()

        if not name and description:
            name = description

        if not name and not description:
            QMessageBox.warning(
                self, "Hiba", "Kérjük, adjon meg legalább Nevet vagy Leírást."
            )
            return

        # -------------------------------------------------
        # MENTÉS
        # -------------------------------------------------

        data = {
            "date": date,
            "type": t_type,
            "amount": amount,
            "category_id": category_id,
            "name": name,
            "description": description,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "has_details": int(bool(has_details)),
            "period_start": period_start,
            "period_end": period_end,
            "invoice_number": invoice_number,
            "is_correction": is_correction,
            "meter_m3": meter_m3,
            "meter_mj": meter_mj,
        }

        print(
            "BILL SAVE DEBUG:",
            provider,
            target_name,
            invoice_number,
            is_correction,
            period_start,
            period_end,
        )

        print("BILL SAVE DATA:", data)
        print("BILL SAVE DB:", getattr(self.db, "db_name", None))

        try:
            tx_id = self.db.save_transaction(data)
            print("BILL SAVED TX_ID:", tx_id)
        except Exception as e:
            print("BILL SAVE ERROR:", repr(e))
            raise

        # Részletek mentése csak a nem-bill ágban, ha has_details=True
        if (mode != "bill") and has_details:
            details_text = (self.field("details_text") or "").strip()
            loc = QLocale.system()

            for line in details_text.splitlines():
                line = (line or "").strip()
                if not line:
                    continue
                try:
                    item_name, unit_price, quantity, item_amount = parse_details_line(
                        line, loc=loc
                    )
                except Exception:
                    continue

                self.db.add_transaction_item(
                    tx_id,
                    item_date=date,
                    item_name=item_name,
                    category_name=None,
                    unit_price=float(unit_price),
                    quantity=float(quantity),
                    amount=float(item_amount),
                )

        msg = (
            "Számla sikeresen rögzítve!"
            if mode == "bill"
            else "Tranzakció sikeresen rögzítve!"
        )

        QMessageBox.information(self, "Siker", msg)

        # Mentés után frissítjük az érintett oldalakat,
        # de nem váltunk automatikusan másik oldalra.
        #
        # Így ha a felhasználó a Számlák oldalról indított számlabefizetést,
        # akkor mentés után ott is marad, csak a lista frissül.
        if hasattr(self.main_window, "transactions_page"):
            self.main_window.transactions_page.reload()

        if hasattr(self.main_window, "bills_page"):
            self.main_window.bills_page.reload()

        super().accept()

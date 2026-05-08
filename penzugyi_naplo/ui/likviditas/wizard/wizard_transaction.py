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

"""


# ----- Importok -------

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from penzugyi_naplo.core.utils import is_valid_date, parse_amount


# ------ Importok vége -----------


if TYPE_CHECKING:
    from penzugyi_naplo.ui.main_window import MainWindow



# ------------ Segéd függvények: -------------------------



# ---------------------------------------------------------------------------
# Részletek sor parszolás
#
# Támogatott formátumok (soronként):
#   1) tételnév;egységár*db      pl.: rágó;349*3
#   2) tételnév;egységár         pl.: kávé;450        (db=1)
#
# Megjegyzés: a régi (tételnév;összeg) bevitel továbbra is működik,
#             mert db=1 esetén az egységár == összeg.
# ---------------------------------------------------------------------------


_MULT_RE = re.compile(r"\s*[xX×\*]\s*")


def parse_details_line(line: str, *, loc: QLocale) -> tuple[str, float, float, float]:
    """Egy details sor parszolása.

    Returns: (item_name, unit_price, quantity, amount)
    Raises: ValueError, ha nem parszolható.
    """
    raw = (line or "").strip()
    if not raw or ";" not in raw:
        raise ValueError("Hiányzó ';' vagy üres sor")

    item_name, rhs = raw.split(";", 1)
    item_name = item_name.strip()
    rhs = rhs.strip()
    if not item_name or not rhs:
        raise ValueError("Hiányzó tételnév vagy érték")

    gs = loc.groupSeparator()
    dp = loc.decimalPoint()

    # Egységár * db (x, ×, * mind jó)
    if _MULT_RE.search(rhs):
        parts = _MULT_RE.split(rhs, maxsplit=1)
        if len(parts) != 2:
            raise ValueError("Rossz '*'/x szintaxis")
        unit_str, qty_str = parts[0].strip(), parts[1].strip()
        if not unit_str or not qty_str:
            raise ValueError("Hiányzó egységár vagy darabszám")

        unit_price = abs(parse_amount(unit_str, group_sep=gs, decimal_point=dp))
        quantity = abs(parse_amount(qty_str, group_sep=gs, decimal_point=dp))
        if quantity == 0:
            raise ValueError("Db nem lehet 0")
        amount = float(unit_price) * float(quantity)
        return (item_name, float(unit_price), float(quantity), float(amount))

    # Egyszerű: tételnév;egységár  (db=1)
    unit_price = abs(parse_amount(rhs, group_sep=gs, decimal_point=dp))
    quantity = 1.0
    amount = float(unit_price)
    return (item_name, float(unit_price), float(quantity), float(amount))


def bill_requires_period(provider: str) -> bool:
    """Csak az MVMNext igényel időszak kezdete/vége mezőket."""
    return (provider or "").strip() == "MVMNext"


# ---------------- Segédfüggvények vége .............................



class PageTypeSelection(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Tranzakció Típusa")
        self.setSubTitle(
            "Válassza ki a tranzakció típusát: Bevétel, Kiadás vagy Számlabefizetés."
        )

        layout = QVBoxLayout(self)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["Kiadás", "Bevétel", "Számlabefizetés"])

        layout.addWidget(QLabel("Típus:"))
        layout.addWidget(self.combo_type)
        layout.addStretch()

    def get_type(self) -> str:
        t = self.combo_type.currentText()
        if t == "Bevétel":
            return "income"
        if t == "Számlabefizetés":
            return "bill"
        return "expense"

    def nextId(self) -> int:
        # A következő wizard oldal indexe a QWizard-ben
        return 5 if self.get_type() == "bill" else 1


class PageCategorySelection(QWizardPage):
    """
    Kategóriaválasztó oldal: kategória + név + leírás + dátum.
    Kategóriákat a kiválasztott tranzakciótípus alapján tölti be.

    Megjegyzés a 'unknown' hibákhoz:
      - wizard.page(0) type checker szerint QWizardPage, ezért castoljuk PageTypeSelection-re.
      - wizard.parent() is QObject, ezért castoljuk MainWindow-ra.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Kategória kiválasztása")
        self.setSubTitle("Melyik kategóriához tartozik a tétel és mi a leírása?")

        layout = QGridLayout(self)

        self.category_map: dict[str, int] = {}

        # Név
        layout.addWidget(QLabel("Név:"), 0, 0)
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Pl.: Havi bérlet, Lidl, Fizetés")
        layout.addWidget(self.input_name, 0, 1)

        # Leírás
        layout.addWidget(QLabel("Leírás:"), 1, 0)
        self.input_description = QLineEdit()
        self.input_description.setPlaceholderText("Opcionális megjegyzés / részletek")
        layout.addWidget(self.input_description, 1, 1)

        # Kategória
        layout.addWidget(QLabel("Kategória:"), 2, 0)
        self.combo_category = QComboBox()
        layout.addWidget(self.combo_category, 2, 1)

        # Dátum
        layout.addWidget(QLabel("Dátum (YYYY-MM-DD):"), 3, 0)
        self.input_date = QLineEdit()
        self.input_date.setText(datetime.now().strftime("%Y-%m-%d"))
        layout.addWidget(self.input_date, 3, 1)

        layout.addWidget(
            QLabel(
                "Megjegyzés: A dátum formátuma YYYY-MM-DD legyen (Pl.: 2025-2-7 is működik)."
            ),
            4,
            0,
            1,
            2,
        )

        layout.setRowStretch(5, 1)

    def initializePage(self) -> None:
        """
        Betölti az adatbázisból a kategóriákat a kiválasztott típus alapján.
        A wizard parent-je a MainWindow (onnan érjük el a db-t).
        """
        wizard = self.wizard()
        if wizard is None:
            return

        parent_obj = wizard.parent()
        if parent_obj is None:
            return

        mw = cast("MainWindow", parent_obj)

        # 1) Típus lekérése: a 0. oldal nálad PageTypeSelection
        #    (cast a type checker miatt)
        type_page = wizard.page(0)
        # Ha véletlen nem az, akkor biztonságos fallback:
        current_type = "expense"
        if type_page is not None and hasattr(type_page, "get_type"):
            current_type = cast(object, type_page).get_type()  # type: ignore[attr-defined]

        # 2) Kategóriák betöltése: először DB API, ha van; különben fallback SQL
        categories: list[tuple[int, str]] = []

        # 2/A - Preferált: DB API (ha létezik)
        if hasattr(mw, "db") and hasattr(mw.db, "get_categories_for_type"):
            rows = mw.db.get_categories_for_type(current_type)
            # elvárt: [(id:int, name:str), ...]
            categories = [(int(cid), str(name)) for cid, name in rows]

        # 2/B - Fallback: nyers SQL (ha van get_db_connection)
        elif hasattr(mw, "db") and hasattr(mw.db, "get_db_connection"):
            conn = mw.db.get_db_connection()
            cursor = conn.cursor()
            rows = cursor.execute(
                "SELECT id, name FROM categories WHERE tx_type = ?",
                (current_type,),
            ).fetchall()
            conn.close()

            for row in rows:
                # sqlite3.Row vagy tuple is lehet; mindkettőt kezeljük
                try:
                    cat_id = row["id"]
                    name = row["name"]
                except Exception:
                    cat_id, name = row[0], row[1]
                categories.append((int(cat_id), str(name)))

        # 3) UI frissítés
        self.combo_category.clear()
        self.category_map.clear()

        for cat_id, name in categories:
            self.combo_category.addItem(name)
            self.category_map[name] = int(cat_id)

    def get_data(self):
        selected_cat = self.combo_category.currentText()
        return (
            self.category_map.get(selected_cat),
            self.input_name.text().strip(),
            self.input_description.text().strip(),
            self.input_date.text().strip(),
        )

    def nextId(self) -> int:
        return 2





class PageSplitDecision(QWizardPage):
    """
    Tétel típusa oldal: döntés, hogy a tétel bontott-e (részletezős) vagy sima (egy tétel).
    Field: 'has_details' (bool)
    """

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Tétel típusa")
        self.setSubTitle("Egy tételként rögzíted, vagy több részletből áll?")

        layout = QVBoxLayout(self)

        info = QLabel(
            "• Egy tétel: egy összeg kerül rögzítésre.\n"
            "• Részletezés: több tételt rögzítesz, és azok összege adja a végösszeget."
        )
        info.setWordWrap(True)

        self.rb_single = QRadioButton("Egy tétel (nincs bontás)")
        self.rb_details = QRadioButton("Több tételből áll (részletezés)")

        self.rb_single.setChecked(True)

        self.group = QButtonGroup(self)
        self.group.addButton(self.rb_single, 0)
        self.group.addButton(self.rb_details, 1)

        layout.addWidget(info)
        layout.addSpacing(8)
        layout.addWidget(self.rb_single)
        layout.addWidget(self.rb_details)
        layout.addStretch(1)

        self.registerField("has_details", self.rb_details, "checked", "toggled")

    def nextId(self) -> int:
        has_details = bool(self.field("has_details"))
        return 4 if has_details else 3


class PageBillProvider(QWizardPage):
    """
    Számlabefizetés oldal (Számlabefizetés ág): szolgáltató választás.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Számlabefizetés")
        self.setSubTitle("Válassza ki a célszámlát / szolgáltatót.")

        layout = QVBoxLayout(self)

        self.combo = QComboBox()
        self.combo.addItems([
                "Válassz szolgáltatót...",
                "KalászNet (Internet)",
                "Telekom",
                "MVMNext",
            ])

        layout.addWidget(QLabel("Célszámla:"))
        layout.addWidget(self.combo)
        layout.addStretch(1)

        self.registerField(
            "bill_provider*", 
            self.combo, 
            "currentText", 
            self.combo.currentTextChanged,
        )

        self.combo.currentIndexChanged.connect(lambda _i: self.completeChanged.emit())

    def isComplete(self) -> bool:
        return self.combo.currentIndex() > 0

    def nextId(self) -> int:
        return 6 if self.combo.currentText() == "MVMNext" else 3  # Amount


class PageBillMvmType(QWizardPage):
    """
    MVMNext oldal (csak MVMNext-nél): Villany / Gáz.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("MVMNext")
        self.setSubTitle("Válassza ki: Villany vagy Gáz.")

        layout = QVBoxLayout(self)

        self.rb_villany = QRadioButton("Villany")
        self.rb_gaz = QRadioButton("Gáz")
        self.rb_villany.setChecked(True)

        self.group = QButtonGroup(self)
        self.group.addButton(self.rb_villany, 0)
        self.group.addButton(self.rb_gaz, 1)

        layout.addWidget(self.rb_villany)
        layout.addWidget(self.rb_gaz)
        layout.addStretch(1)

    def is_gas(self) -> bool:
        return self.rb_gaz.isChecked()

    def nextId(self) -> int:
        return 3  # Amount


class PageAmount(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Összeg Rögzítése")
        self.setSubTitle("Adja meg a tranzakció értékét (csak pozitív számot).")
        self.setFinalPage(True)

        layout = QVBoxLayout(self)

        # ---- Bill mód mezők (alapesetben rejtve) ----

        self.lbl_date = QLabel("Fizetés dátuma (YYYY-MM-DD):")
        self.input_date = QLineEdit()
        self.input_date.setText(datetime.now().strftime("%Y-%m-%d"))

        self.lbl_period_start = QLabel("Időszak kezdete (YYYY-MM-DD):")
        self.input_period_start = QLineEdit()
        self.input_period_start.setPlaceholderText("Pl.: 2025-03-15")

        self.lbl_period_end = QLabel("Időszak vége (YYYY-MM-DD):")
        self.input_period_end = QLineEdit()
        self.input_period_end.setPlaceholderText("Pl.: 2025-04-15")

        self.lbl_invoice_number = QLabel("Számla sorszáma:")
        self.input_invoice_number = QLineEdit()
        self.input_invoice_number.setPlaceholderText("Pl.: 1234567890")




        layout.addWidget(self.lbl_invoice_number)
        layout.addWidget(self.input_invoice_number)

        layout.addWidget(self.lbl_date)
        layout.addWidget(self.input_date)
        layout.addWidget(self.lbl_period_start)
        layout.addWidget(self.input_period_start)
        layout.addWidget(self.lbl_period_end)
        layout.addWidget(self.input_period_end)

        # ---- közös mező ----

        self.input_amount = QLineEdit()
        self.input_amount.setPlaceholderText("Csak pozitív szám (pl. 20000)")

        layout.addWidget(QLabel("Összeg (HUF):"))
        layout.addWidget(self.input_amount)
        layout.addStretch()

   
    def initializePage(self) -> None:
        super().initializePage()

        wiz = self.wizard()
        mode = None
        provider = ""

        if (
            wiz is not None
            and wiz.page(0) is not None
            and hasattr(wiz.page(0), "get_type")
        ):
            mode = wiz.page(0).get_type()

        if wiz is not None:
            provider = (wiz.field("bill_provider") or "").strip()

        is_bill = mode == "bill"
        needs_period = is_bill and bill_requires_period(provider)

        self.lbl_date.setVisible(is_bill)
        self.input_date.setVisible(is_bill)

        self.lbl_period_start.setVisible(needs_period)
        self.input_period_start.setVisible(needs_period)
        self.lbl_period_end.setVisible(needs_period)
        self.input_period_end.setVisible(needs_period)

        self.lbl_invoice_number.setVisible(needs_period)
        self.input_invoice_number.setVisible(needs_period)

        if is_bill:
            self.input_date.setText(datetime.now().strftime("%Y-%m-%d"))
            self.input_amount.clear()
            self.input_invoice_number.clear()

            if needs_period:
                self.input_period_start.clear()
                self.input_period_end.clear()
            else:
                self.input_period_start.clear()
                self.input_period_end.clear()



    def reset_bill_fields(self) -> None:
        self.input_invoice_number.clear()
        self.input_date.setText(datetime.now().strftime("%Y-%m-%d"))
        self.input_period_start.clear()
        self.input_period_end.clear()
        self.input_amount.clear()



    def validatePage(self) -> bool:
        wiz = self.wizard()
        mode = None
        provider = ""

        if (
            wiz is not None
            and wiz.page(0) is not None
            and hasattr(wiz.page(0), "get_type")
        ):
            mode = wiz.page(0).get_type()

        if wiz is not None:
            provider = (wiz.field("bill_provider") or "").strip()

        if mode == "bill":
            payment_date = is_valid_date(self.input_date.text().strip())
            if not payment_date:
                QMessageBox.warning(
                    self,
                    "Hiba",
                    "Érvénytelen fizetési dátum! Használj YYYY-M-D vagy YYYY-MM-DD formátumot.",
                )
                return False

            if bill_requires_period(provider):
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

        amount_str = self.input_amount.text().strip()
        try:
            loc = QLocale.system()
            gs = loc.groupSeparator()
            dp = loc.decimalPoint()

            amount = parse_amount(amount_str, group_sep=gs, decimal_point=dp)
            if amount <= 0:
                QMessageBox.warning(self, "Hiba", "Kérjük, adjon meg pozitív összeget.")
                return False

            return True
        except ValueError:
            QMessageBox.warning(
                self, "Hiba", "Érvénytelen összeg formátum. Csak számokat használjon."
            )
            return False






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

    def nextId(self) -> int:
        return -1
    
    def get_invoice_number_raw(self) -> str:
        return self.input_invoice_number.text().strip()

# Itt már a core.utils.is_valid_date-et használjuk.
# Fontos: ez az osztály feltételezi, hogy ugyanabban a fájlban már létezik:

# - PageTypeSelection
# - PageCategorySelection
# - PageAmount


class TransactionWizard(QWizard):
    """Az új tranzakció rögzítése varázsló."""

    def __init__(self, db, main_window, parent=None) -> None:
        super().__init__(parent)

        self.db = db
        self.main_window = main_window

        self.setWindowTitle("Új Tranzakció Rögzítése")

        # Oldalak (id-k: 0,1,2,3)
        self.setPage(0, PageTypeSelection())
        self.setPage(1, PageCategorySelection())
        self.setPage(2, PageSplitDecision())
        self.setPage(3, PageAmount())
        self.setPage(4, PageDetails())
        self.setPage(5, PageBillProvider())
        self.setPage(6, PageBillMvmType())

   
    def accept(self) -> None:
        raw_mode = self.page(0).get_type()  # 'income' / 'expense' / 'bill'
        provider = (self.field("bill_provider") or "").strip()

        # Stabil fallback:
        # ha a bill_provider ki van töltve, akkor ez biztosan bill ág
        if provider and provider != "Válassz szolgáltatót...":
            mode = "bill"
        else:
            mode = raw_mode


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

        # -------------------------------------------------
        # BILL ÁG
        # -------------------------------------------------
        if mode == "bill":
            t_type = "expense"


            if provider == "MVMNext":
                is_gaz = self.page(6).is_gas()
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

            amount_page = self.page(3)

           
            date_raw = amount_page.get_bill_date_raw()

            name = target_name
            description = "Számlabefizetés"
            has_details = False
            amount = amount_page.get_amount()

            if bill_requires_period(provider):
                invoice_number = amount_page.get_invoice_number_raw()

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
        }


        print(
            "BILL SAVE DEBUG:",
            provider,
            target_name,
            invoice_number,
            period_start,
            period_end,
        )
        
        tx_id = self.db.save_transaction(data)

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
        self.main_window.set_page("transactions")
        super().accept()






class PageDetails(QWizardPage):
    """
    Tételek rögzítése oldal: több tétel rögzítése (ideiglenes egyszerű UI).
    Formátum (soronként):
      - tételnév;egységár*db      (pl. rágó;349*3)
      - tételnév;egységár         (pl. kávé;450)  -> db=1
    Eredmény:
      - details_total (float) mezőbe eltárolja az összeget.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Részletek rögzítése")
        self.setSubTitle(
            "Soronként add meg: tételnév;egységár*db  (pl. rágó;349*3)  vagy tételnév;egységár  (db=1)."
        )

        layout = QVBoxLayout(self)

        self.txt = QTextEdit()
        self.txt.setPlaceholderText(
            "pl.\nburgonyás pogácsa;185*2\norbit gyümölcsös;349*3\nkávé;450"
        )
        layout.addWidget(self.txt)

        self.lbl_sum = QLabel("Összesen: 0 HUF")
        layout.addWidget(self.lbl_sum)

        # wizard field: details_total (float)
        # QTextEdit-nél nincs direct "text" property field-nek, ezért kézzel kezeljük.
        self._details_total: float = 0.0

        self.txt.textChanged.connect(self._recalc_total)
        self.txt.textChanged.connect(self._sync_hidden_text)

        # --- Wizard field trükk ---
        self._hidden_total = QLineEdit(self)
        self._hidden_total.setVisible(False)
        self._hidden_total.setText("0")

        # total megy a hidden_total-on
        self.registerField(
            "details_total", 
            self._hidden_total, 
            "text", "textChanged"
        )

        self._hidden_text = QLineEdit(self)
        self._hidden_text.setVisible(False)
        self._hidden_text.setText("")

        # text megy a hidden_text-en (CSAK EGYSZER!)
        self.registerField("details_text", self._hidden_text, "text", "textChanged")

    def _sync_hidden_text(self) -> None:
        self._hidden_text.setText(self.txt.toPlainText())

    def _recalc_total(self) -> None:
        total = 0.0
        lines = self.txt.toPlainText().splitlines()
        loc = QLocale.system()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                _, _, _, amount = parse_details_line(line, loc=loc)
                total += float(amount)
            except Exception:
                # rossz sor: kihagyjuk, majd validatePage jelez
                pass

        self._details_total = float(total)
        self.lbl_sum.setText(f"Összesen: {int(round(total))} HUF")

        self._hidden_total.setText(str(self._details_total))

        self._hidden_text.setText(self.txt.toPlainText())

    def validatePage(self) -> bool:
        # minimum: legyen legalább 1 érvényes sor és total > 0
        self._recalc_total()
        if self._details_total <= 0:
            QMessageBox.warning(
                self,
                "Hiba",
                "Nincs érvényes részlet sor.\n\n"
                "Formátum:\n"
                "  tételnév;egységár*db   (pl. rágó;349*3)\n"
                "  tételnév;egységár      (pl. kávé;450)",
            )
            return False

        # Hibás sorok részletes jelzése
        loc = QLocale.system()
        for idx, raw in enumerate(self.txt.toPlainText().splitlines(), start=1):
            raw = (raw or "").strip()
            if not raw:
                continue
            try:
                parse_details_line(raw, loc=loc)
            except Exception:
                QMessageBox.warning(
                    self,
                    "Hibás sor",
                    "Hibás részlet sor a(z) %d. sorban.\n\n"
                    "Használható formátumok:\n"
                    "  tételnév;egységár*db   (pl. rágó;349*3)\n"
                    "  tételnév;egységár      (pl. kávé;450)" % idx,
                )
                return False
        return True

    def nextId(self) -> int:
        # Részletezés után mehet az Amount oldalra? Itt a kulcs döntés:
        # - Ha azt akarod, hogy részletezés esetén az Amount oldalt kihagyjuk,
        #   akkor közvetlenül a Finish-re / utolsó oldalra kell menni.
        # Javaslat: részletezés esetén az Amount oldalt kihagyjuk, és az összeget a details_total adja.

        return -1  # finish

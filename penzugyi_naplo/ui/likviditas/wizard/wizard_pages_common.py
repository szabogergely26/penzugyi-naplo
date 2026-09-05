# penzugyi_naplo/ui/likviditas/wizard/wizard_pages_common.py
# --------------------------------------------------------------
# Likviditás / Tranzakciórögzítő varázsló — közös oldalak
# --------------------------------------------------------------

"""
A tranzakció-varázsló azon oldalai, amik NEM a számlabefizetés (bill) flow
részei, hanem a normál bevétel/kiadás rögzítést szolgálják:

- PageTypeSelection: Bevétel / Kiadás / Számlabefizetés választás
- PageCategorySelection: kategória + név + leírás + dátum
- PageSplitDecision: egy tétel vagy részletezett bontás
- PageDetails: részletezett tételek soronkénti bevitele

A bill-specifikus oldalak (PageBillProvider, PageBillMvmType, PageAmount)
a wizard_pages_bill.py-ban vannak.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QTextEdit,
    QWizardPage,
)

from .wizard_helpers import create_transaction_wizard_page_layout, parse_details_line

if TYPE_CHECKING:
    from penzugyi_naplo.ui.main_window import MainWindow


class PageTypeSelection(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Tranzakció típusa")
        self.setSubTitle(
            "Válaszd ki, milyen pénzmozgást szeretnél rögzíteni."
        )

        layout, self.side_title_label, self.side_subtitle_label = create_transaction_wizard_page_layout(
            self,
            "💰",
            "Új tranzakció",
            "Bevétel, kiadás vagy számlabefizetés rögzítése.",
        )

        info_label = QLabel("Mit szeretnél rögzíteni?")
        info_label.setObjectName("transactionWizardSectionTitle")
        layout.addWidget(info_label)

        self.rb_income = QRadioButton("Bevétel")
        self.rb_expense = QRadioButton("Kiadás")
        self.rb_bill = QRadioButton("Számlabefizetés")

        self.rb_income.setObjectName("transactionWizardPlainRadio")
        self.rb_expense.setObjectName("transactionWizardPlainRadio")
        self.rb_bill.setObjectName("transactionWizardPlainRadio")

        self.rb_income.setChecked(True)

        self.group = QButtonGroup(self)
        self.group.addButton(self.rb_income, 0)
        self.group.addButton(self.rb_expense, 1)
        self.group.addButton(self.rb_bill, 2)

        income_desc = QLabel(
            "Beérkező összeg rögzítése, például fizetés, támogatás vagy más bevétel."
        )
        income_desc.setObjectName("transactionWizardOptionDescription")
        income_desc.setWordWrap(True)

        expense_desc = QLabel(
            "Kimenő összeg rögzítése, például vásárlás, étkezés vagy egyéb kiadás."
        )
        expense_desc.setObjectName("transactionWizardOptionDescription")
        expense_desc.setWordWrap(True)

        bill_desc = QLabel(
            "Közüzemi vagy szolgáltatói számla befizetése, például Telekom, KalászNet vagy MVMNext."
        )
        bill_desc.setObjectName("transactionWizardOptionDescription")
        bill_desc.setWordWrap(True)

        layout.addWidget(self.rb_income)
        layout.addWidget(income_desc)

        layout.addSpacing(8)
        layout.addWidget(self.rb_expense)
        layout.addWidget(expense_desc)

        layout.addSpacing(8)
        layout.addWidget(self.rb_bill)
        layout.addWidget(bill_desc)

        layout.addStretch(1)

    def get_type(self) -> str:
        if self.rb_income.isChecked():
            return "income"

        if self.rb_bill.isChecked():
            return "bill"

        return "expense"

    def nextId(self) -> int:
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

        layout, self.side_title_label, self.side_subtitle_label = create_transaction_wizard_page_layout(
            self,
            "🧾",
            "Tranzakció adatai",
            "Add meg a név, kategória és dátum adatait.",
        )

        self.category_map: dict[str, int] = {}

        layout.addWidget(QLabel("Név"))
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Pl.: Havi bérlet, Lidl, Fizetés")
        layout.addWidget(self.input_name)

        layout.addWidget(QLabel("Leírás"))
        self.input_description = QLineEdit()
        self.input_description.setPlaceholderText("Opcionális megjegyzés / részletek")
        layout.addWidget(self.input_description)

        layout.addWidget(QLabel("Kategória"))
        self.combo_category = QComboBox()
        layout.addWidget(self.combo_category)

        layout.addWidget(QLabel("Dátum"))
        self.input_date = QLineEdit()
        self.input_date.setText(datetime.now().strftime("%Y-%m-%d"))
        layout.addWidget(self.input_date)

        hint = QLabel(
            "A dátum formátuma YYYY-MM-DD legyen. Például: 2026-06-11."
        )
        hint.setObjectName("transactionWizardHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch(1)

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

        if current_type == "income":
            self.setTitle("Bevétel hozzáadása")
            self.setSubTitle("Add meg a bevétel nevét, kategóriáját és dátumát.")
            self.side_title_label.setText("Bevétel")
            self.side_subtitle_label.setText("Pénz érkezése valamelyik saját egyenleghez.")

        elif current_type == "expense":
            self.setTitle("Kiadás hozzáadása")
            self.setSubTitle("Add meg a kiadás nevét, kategóriáját és dátumát.")
            self.side_title_label.setText("Kiadás")
            self.side_subtitle_label.setText("Külső célra elköltött összeg rögzítése.")

        else:
            self.setTitle("Tranzakció hozzáadása")
            self.setSubTitle("Add meg a tranzakció adatait.")
            self.side_title_label.setText("Tranzakció")
            self.side_subtitle_label.setText("Pénzmozgás rögzítése a naplóban.")


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
        wizard = self.wizard()

        if (
            wizard is not None
            and wizard.page(0) is not None
            and hasattr(wizard.page(0), "get_type")
        ):
            current_type = wizard.page(0).get_type()

            # Bevételnél nincs részletezés, egyből az összeg oldalra megyünk.
            if current_type == "income":
                return 3

        # Kiadásnál marad a részletezés döntés oldal.
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

        layout, self.side_title_label, self.side_subtitle_label = create_transaction_wizard_page_layout(
            self,
            "🧩",
            "Tétel típusa",
            "Döntsd el, hogy egyszerű vagy részletezett tételt rögzítesz.",
        )

        info = QLabel(
            "• Egy tétel: egy összeg kerül rögzítésre.\n"
            "• Részletezés: több tételt rögzítesz, és azok összege adja a végösszeget."
        )
        info.setObjectName("transactionWizardHint")
        info.setWordWrap(True)

        self.rb_single = QRadioButton("Egy tétel\n    Nincs bontás, csak egy végösszeg.")
        self.rb_details = QRadioButton(
            "Több tételből áll\n"
            "    Részletezett bevitel, például: burgonya;500*2"
        )

        self.rb_single.setObjectName("transactionWizardRadio")
        self.rb_details.setObjectName("transactionWizardRadio")

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
            "Soronként add meg: tételnév;egységár*db vagy tételnév;egységár."
        )

        layout, self.side_title_label, self.side_subtitle_label = create_transaction_wizard_page_layout(
            self,
            "📝",
            "Részletezés",
            "Több tételből álló kiadás vagy bevétel bontása.",
        )

        hint = QLabel(
            "Formátum példák:\n"
            "• burgonyás pogácsa;185*2\n"
            "• orbit gyümölcsös;349*3\n"
            "• kávé;450"
        )
        hint.setObjectName("transactionWizardHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.txt = QTextEdit()
        self.txt.setPlaceholderText(
            "pl.\nburgonyás pogácsa;185*2\norbit gyümölcsös;349*3\nkávé;450"
        )
        layout.addWidget(self.txt)

        self.lbl_sum = QLabel("Összesen: 0 HUF")
        self.lbl_sum.setObjectName("transactionWizardSectionTitle")
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
            "text",
            "textChanged",
        )

        self._hidden_text = QLineEdit(self)
        self._hidden_text.setVisible(False)
        self._hidden_text.setText("")

        # text megy a hidden_text-en
        self.registerField("details_text", self._hidden_text, "text", "textChanged")

    def _sync_hidden_text(self) -> None:
        self._hidden_text.setText(self.txt.toPlainText())

    def _format_total_label(self, total: float) -> str:
        """A részletek összegének magyaros megjelenítése."""
        rounded_total = int(round(total))
        formatted_total = f"{rounded_total:,}".replace(",", " ")
        return f"Összesen: {formatted_total} Ft"

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
        self.lbl_sum.setText(self._format_total_label(total))

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
                    f"Hibás részlet sor a(z) {idx}. sorban.\n\n"
                    "Használható formátumok:\n"
                    "  tételnév;egységár*db   (pl. rágó;349*3)\n"
                    "  tételnév;egységár      (pl. kávé;450)",
                )
                return False
        return True

    def nextId(self) -> int:
        # Részletezés után mehet az Amount oldalra? Itt a kulcs döntés:
        # - Ha azt akarod, hogy részletezés esetén az Amount oldalt kihagyjuk,
        #   akkor közvetlenül a Finish-re / utolsó oldalra kell menni.
        # Javaslat: részletezés esetén az Amount oldalt kihagyjuk, és az összeget a details_total adja.

        return -1  # finish
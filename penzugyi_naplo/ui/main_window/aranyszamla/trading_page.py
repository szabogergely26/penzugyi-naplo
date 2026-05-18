# /ui/main_window/aranyszamla/trading_page.py
# -------------------------------------------

"""
Fájl: penzugyi_naplo/ui/main_window/aranyszamla/trading_page.py

Feladat:
    Az Aranyszámla / Kereskedés oldal megjelenítése.

Felelősség:
    - gold_transactions tábla adatainak megjelenítése
    - vétel / eladás sorok listázása
    - számok olvasható, magyaros formázása

Megjegyzés:
    Ez első körben csak olvasó nézet.
    Új aranytranzakció rögzítése későbbi lépés lesz.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    
)

from penzugyi_naplo.db.gold_database import (
    delete_gold_transaction,
    list_gold_transactions,
)


class GoldTradingPage(QWidget):
    """
    Aranyszámla / Kereskedés oldal.

    Ez az oldal jeleníti meg az adatbázisban tárolt aranyszámla tranzakciókat.
    Első körben csak lista/táblázat nézetet adunk hozzá.
    """

    def __init__(self, db_path: str | Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Eltároljuk az adatbázis útvonalát.
        # Ha induláskor még nincs megadva, később set_db_path() hívással beállítható.
        self.db_path = Path(db_path) if db_path else None

        # Felépítjük az oldal felületét.
        self._build_ui()

        # Ha már ismert az adatbázis útvonal, rögtön betöltjük az adatokat.
        if self.db_path:
            self.load_transactions()

    def _build_ui(self) -> None:
        """
        Létrehozza az oldal vizuális elemeit.
        """

        # Fő függőleges layout az oldalhoz.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Oldalcím.
        title_label = QLabel("Kereskedés")
        title_label.setObjectName("goldPageTitle")
        layout.addWidget(title_label)

        # Rövid magyarázó szöveg.
        info_label = QLabel(
            "Itt jelennek meg az aranyszámlához rögzített vételi és eladási adatok."
        )
        info_label.setObjectName("goldPageInfo")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

       
        # Aranytranzakciók táblázata.
        self.table = QTableWidget()
        self.table.setObjectName("goldTransactionsTable")

        # A táblázat oszlopai.
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [
                "Dátum",
                "Mennyiség",
                "Árfolyam",
                "Összeg",
                "Megjegyzés",
                "Típus",
                "Művelet",
            ]
        )

        # A táblázat csak megjelenítésre szolgál, ne legyen kézzel szerkeszthető.
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Teljes sort lehessen kijelölni.
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Egyszerre csak egy sor legyen kijelölhető.
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Szebb táblázatnézet.
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        # Fix, kiszámítható oszlopszélességek.
        # Most nem használunk Stretch-et, mert az üres Megjegyzés oszlop széthúzta a táblát.
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        self.table.setColumnWidth(0, 110)  # Dátum
        self.table.setColumnWidth(1, 120)  # Mennyiség
        self.table.setColumnWidth(2, 120)  # Árfolyam
        self.table.setColumnWidth(3, 110)  # Összeg
        self.table.setColumnWidth(4, 260)  # Megjegyzés
        self.table.setColumnWidth(5, 90)   # Típus
        self.table.setColumnWidth(6, 90)   # Művelet

        # A táblázatot hozzáadjuk az oldal layoutjához.
        # Enélkül külön ablakban jelenhet meg, amikor show() hívást kap.
        layout.addWidget(self.table)

        # Üres állapot szöveg.
        self.empty_label = QLabel("Még nincs rögzített aranyszámla tranzakció.")
        self.empty_label.setObjectName("goldEmptyLabel")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

    def set_db_path(self, db_path: str | Path) -> None:
        """
        Beállítja az adatbázis útvonalát, majd újratölti az adatokat.

        Erre akkor van szükség, ha az oldal példányosításakor még nem ismert a db_path.
        """

        # Az útvonalat Path objektummá alakítjuk, hogy egységesen kezelhető legyen.
        self.db_path = Path(db_path)

        # Újratöltjük a táblázatot az új adatbázis útvonal alapján.
        self.load_transactions()



    def refresh(self) -> None:
        """
        Frissíti az Aranyszámla / Kereskedés táblázatot.
        """

        self.load_transactions()










    def load_transactions(self) -> None:
        """
        Betölti a gold_transactions tábla sorait a táblázatba.
        """

        # Ha nincs adatbázis útvonal, nem próbálunk adatot betölteni.
        if not self.db_path:
            self._show_empty_state("Nincs beállítva adatbázis útvonal.")
            return

        # Lekérjük az aranyszámla tranzakciókat az adatbázisból.
        transactions = list_gold_transactions(self.db_path)

        # Kiürítjük a táblázatot, hogy tiszta állapotból töltsük újra.
        self.table.setRowCount(0)

        # Ha nincs adat, üres állapotot jelenítünk meg.
        if not transactions:
            self._show_empty_state("Még nincs rögzített aranyszámla tranzakció.")
            return

        # Van adat, ezért a táblázat látszódjon, az üres szöveg ne.
        self.empty_label.setVisible(False)

        # Soronként betöltjük a tranzakciókat.
        for row_index, transaction in enumerate(transactions):
            self.table.insertRow(row_index)

            # A lekért sor lehet dict-szerű vagy objektum-szerű.
            # Ez a segédfüggvény mindkét esetet kezeli.
            transaction_id = self._get_value(transaction, "id")
            trade_date = self._get_value(transaction, "trade_date")
            trade_type = self._get_value(transaction, "trade_type")
            grams = self._get_value(transaction, "grams")
            unit_price_huf = self._get_value(transaction, "unit_price_huf")
            total_huf = self._get_value(transaction, "total_huf")
            note = self._get_value(transaction, "note") or ""

            # Cellák feltöltése.
            self._set_item(row_index, 0, str(trade_date or ""))
            self._set_item(row_index, 1, self._format_grams(grams), align_right=True)
            self._set_item(row_index, 2, self._format_huf_per_gram(unit_price_huf), align_right=True)
            self._set_item(row_index, 3, self._format_huf(total_huf), align_right=True)
            self._set_item(row_index, 4, str(note))
            self._set_item(row_index, 5, self._format_trade_type(str(trade_type or "")))

            self._add_delete_button(row_index, int(transaction_id))



    def _show_empty_state(self, message: str) -> None:
        """
        Megjeleníti az üres állapotot.
        """

        # A táblázatot kiürítjük.
        self.table.setRowCount(0)

        # Az üres állapot szövegét frissítjük.
        self.empty_label.setText(message)

        # Üres állapot szöveg megjelenítése.
        self.empty_label.setVisible(True)

    def _set_item(
        self,
        row: int,
        column: int,
        text: str,
        *,
        align_right: bool = False,
    ) -> None:
        """
        Beállít egy cellát a táblázatban.
        """

        # Létrehozzuk a táblázat cellaelemét.
        item = QTableWidgetItem(text)

        # Számoknál jobbra igazítunk, mert így olvashatóbb a táblázat.
        if align_right:
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        else:
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

        # Cellába helyezzük az elemet.
        self.table.setItem(row, column, item)



    def _add_delete_button(self, row: int, transaction_id: int) -> None:
        """
        Törlés gombot tesz a megadott táblázatsor végére.
        """

        delete_button = QPushButton("Törlés")
        delete_button.setObjectName("goldDeleteButton")

        delete_button.clicked.connect(
            lambda checked=False, tx_id=transaction_id: self._confirm_delete(tx_id)
        )

        self.table.setCellWidget(row, 6, delete_button)


    def _confirm_delete(self, transaction_id: int) -> None:
        """
        Megerősítést kér, majd törli az aranyszámla tranzakciót.
        """

        answer = QMessageBox.question(
            self,
            "Aranyszámla tranzakció törlése",
            "Biztosan törölni szeretnéd ezt az aranyszámla tranzakciót?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        if not self.db_path:
            QMessageBox.warning(
                self,
                "Törlés sikertelen",
                "Nincs beállítva adatbázis útvonal.",
            )
            return

        delete_gold_transaction(str(self.db_path), transaction_id)

        self.load_transactions()
















    def _get_value(self, source: object, key: str) -> object:
        """
        Értéket olvas ki dict-ből vagy objektumból.

        Erre azért van szükség, mert a database réteg visszaadhat dict-et,
        sqlite Row-t vagy saját adatszerkezetet is.
        """

        # Dict esetén kulcs alapján olvasunk.
        if isinstance(source, dict):
            return source.get(key)

        # sqlite3.Row esetén is működhet a kulcsos elérés.
        try:
            return source[key]  # type: ignore[index]
        except (KeyError, IndexError, TypeError):
            pass

        # Objektum esetén attribútumként próbáljuk lekérni.
        return getattr(source, key, None)

    def _format_trade_type(self, value: str) -> str:
        """
        A belső trade_type értéket magyar felirattá alakítja.
        """

        if value == "buy":
            return "Vétel"

        if value == "sell":
            return "Eladás"

        return value

    def _format_grams(self, value: object) -> str:
        """
        Gramm mennyiség formázása.
        """

        if value is None:
            return ""

        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)

        return f"{number:,.4f} g".replace(",", " ")

    def _format_huf(self, value: object) -> str:
        """
        Forint összeg formázása.
        """

        if value is None:
            return ""

        try:
            number = int(value)
        except (TypeError, ValueError):
            return str(value)

        return f"{number:,} Ft".replace(",", " ")

    def _format_huf_per_gram(self, value: object) -> str:
        """
        Ft/g árfolyam formázása.
        """

        if value is None:
            return ""

        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)

        return f"{number:,.0f} Ft/g".replace(",", " ")
    

    
"""
penzugyi_naplo/ui/importers/ods_import_pages.py

ODS import varázsló oldalai.

Felelősség:
    - az ODS import varázsló külön képernyőinek / oldalainak felépítése
    - fájlválasztás UI
    - munkalap és sorbeállítás UI
    - import előnézet megjelenítése
    - végső összegzés megjelenítése

    
Architektúra szerep:
    Ez a modul csak UI elemeket tartalmaz.
    A tényleges ODS olvasás, fejlécfelismerés és importálás továbbra is
    az importer / wizard vezérlő réteg feladata.

Kapcsolódás:
    - penzugyi_naplo/ui/importers/ods_transaction_import_wizard.py
    - penzugyi_naplo/importers/ods_transaction_importer.py




Fontos:
    Ez a fájl csak UI elemeket tartalmaz.
    A tényleges ODS feldolgozás továbbra is az importer modul feladata.
"""


# - Importok:

from __future__ import annotations


from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWizardPage,
    QComboBox,
    QMessageBox,
    QLineEdit,
    QFileDialog,
    QHBoxLayout,
    QGridLayout,
    QFrame
)


from penzugyi_naplo.importers.ods_transaction_importer import OdsTransactionImporter

if TYPE_CHECKING:
    from penzugyi_naplo.ui.importers.ods_transaction_import_wizard import (
        OdsTransactionImportWizard,
    )



class IntroPage(QWizardPage):
    """
    Bevezető oldal.

    Itt még nem történik fájlbeolvasás.
    Csak elmagyarázza, hogy a varázsló mit fog csinálni.
    """

    def __init__(self, wizard: "OdsTransactionImportWizard"):
        super().__init__(wizard)

        self.wizard_ref = wizard

        self.setTitle("ODS tranzakció import")
        self.setSubTitle("A varázsló végigvezet az import előnézet elkészítésén.")

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Ez a varázsló ODS táblázatból készít tranzakció előnézetet.\n\n"
            "A folyamat közben még nem kerül semmi az adatbázisba.\n"
            "A tényleges importálás csak az utolsó oldalon, az Importálás gombbal indul.\n\n"
            "Lépések:\n"
            "  1. ODS fájl kiválasztása\n"
            "  2. Munkalap kiválasztása\n"
            "  3. Fejlécsor és adatsor ellenőrzése\n"
            "  4. Előnézet átnézése\n"
            "  5. Importálás megerősítése"
        )
        info_label.setWordWrap(True)

        layout.addWidget(info_label)
        layout.addStretch(1)






class FileSelectPage(QWizardPage):
    """
    ODS fájl kiválasztó oldal.

    Feladata:
        - ODS fájl tallózása
        - OdsTransactionImporter létrehozása
        - munkalapok előzetes beolvasása

    Fontos:
        Itt még nem készül tranzakció-előnézet.
        Csak azt ellenőrizzük, hogy a fájl megnyitható-e,
        és van-e benne legalább egy munkalap.
    """

    def __init__(self, wizard: "OdsTransactionImportWizard"):
        super().__init__(wizard)

        self.wizard_ref = wizard

        self.setTitle("ODS fájl kiválasztása")
        self.setSubTitle("Válaszd ki azt az ODS fájlt, amelyből import előnézetet szeretnél készíteni.")

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Tallózd ki a régi pénzügyi táblázatot vagy más ODS fájlt.\n\n"
            "A fájl kiválasztása után a varázsló ellenőrzi, hogy az ODS megnyitható-e, "
            "és tartalmaz-e munkalapokat."
        )
        info_label.setWordWrap(True)

        file_row = QHBoxLayout()

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Nincs kiválasztott ODS fájl...")
        self.file_path_edit.setReadOnly(True)

        self.choose_file_btn = QPushButton("Tallózás…")
        self.choose_file_btn.clicked.connect(self.choose_file)

        file_row.addWidget(self.file_path_edit, 1)
        file_row.addWidget(self.choose_file_btn)

        self.status_label = QLabel("Még nincs kiválasztott fájl.")
        self.status_label.setWordWrap(True)

        layout.addWidget(info_label)
        layout.addSpacing(12)
        layout.addLayout(file_row)
        layout.addSpacing(8)
        layout.addWidget(self.status_label)
        layout.addStretch(1)



    # - metódusok:

    def isComplete(self) -> bool:
        """
        Akkor engedjük tovább a varázslót, ha van kiválasztott
        és sikeresen megnyitott ODS importer.
        """
        return self.wizard_ref.importer is not None

    def choose_file(self) -> None:
        """
        ODS fájl kiválasztása és előzetes beolvasása.

        Ha a fájl jó:
            - eltesszük az útvonalat a wizard közös állapotába
            - létrehozzuk az OdsTransactionImporter példányt
            - beolvassuk a munkalaplistát
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "ODS fájl kiválasztása",
            str(Path.home()),
            "LibreOffice Calc fájlok (*.ods);;Minden fájl (*)",
        )

        if not file_path:
            return

        try:
            importer = OdsTransactionImporter(file_path)
            sheets = importer.list_sheets()

        except Exception as exc:
            self.wizard_ref.importer = None
            self.wizard_ref.file_path = None

            self.file_path_edit.setText("")
            self.status_label.setText("Nem sikerült beolvasni az ODS fájlt.")

            QMessageBox.critical(
                self,
                "ODS import hiba",
                f"Nem sikerült beolvasni az ODS fájlt:\n\n{exc}",
            )

            self.completeChanged.emit()
            return

        if not sheets:
            self.wizard_ref.importer = None
            self.wizard_ref.file_path = None

            self.file_path_edit.setText("")
            self.status_label.setText("A kiválasztott ODS fájlban nincs munkalap.")

            QMessageBox.warning(
                self,
                "Nincs munkalap",
                "A kiválasztott ODS fájlban nem található munkalap.",
            )

            self.completeChanged.emit()
            return

        self.wizard_ref.importer = importer
        self.wizard_ref.file_path = file_path

        # Később a SheetSelectPage újra lekéri a munkalapokat az importerből.
        # Itt csak azt ellenőrizzük, hogy egyáltalán van-e mit kiválasztani.
        file_name = Path(file_path).name

        self.file_path_edit.setText(file_path)
        self.status_label.setText(
            f"ODS fájl beolvasva: {file_name}\n"
            f"Talált munkalapok száma: {len(sheets)}"
        )

        self.completeChanged.emit()






class SheetSelectPage(QWizardPage):
    """
    Munkalapválasztó oldal.

    Feladata:
        - az előző oldalon betöltött ODS importerből lekéri a munkalapokat
        - megjeleníti őket egy lenyíló listában
        - a kiválasztott munkalap nevét eltárolja a wizard közös állapotába

    Fontos:
        Itt még nem készül adatbázis-import.
        Ez az oldal csak kiválasztja, melyik munkalappal dolgozzon tovább a wizard.
    """

    def __init__(self, wizard: "OdsTransactionImportWizard"):
        super().__init__(wizard)

        self.wizard_ref = wizard

        self.setTitle("Munkalap kiválasztása")
        self.setSubTitle("Válaszd ki, melyik munkalapból készüljön import előnézet.")

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Az ODS fájl több munkalapot is tartalmazhat.\n\n"
            "Itt válaszd ki azt a munkalapot, amelyikben a tranzakciós adatok vannak."
        )
        info_label.setWordWrap(True)

        self.sheet_combo = QComboBox()
        self.sheet_combo.currentIndexChanged.connect(self._on_sheet_changed)

        self.status_label = QLabel("Még nincs betöltött munkalaplista.")
        self.status_label.setWordWrap(True)

        layout.addWidget(info_label)
        layout.addSpacing(12)
        layout.addWidget(QLabel("Munkalap:"))
        layout.addWidget(self.sheet_combo)
        layout.addSpacing(8)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

    def initializePage(self) -> None:
        """
        Az oldal megnyitásakor frissítjük a munkalaplistát.

        Ez azért itt történik, mert a fájlt az előző oldalon választjuk ki.
        Mire ideérünk, a wizard_ref.importer már létezhet.
        """
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()

        self.wizard_ref.selected_sheet_name = None

        importer = self.wizard_ref.importer

        if importer is None:
            self.status_label.setText(
                "Nincs betöltött ODS importer. Menj vissza, és válassz ki egy fájlt."
            )
            self.sheet_combo.blockSignals(False)
            self.completeChanged.emit()
            return

        try:
            sheets = importer.list_sheets()

        except Exception as exc:
            self.status_label.setText("Nem sikerült lekérni a munkalapokat.")
            self.sheet_combo.blockSignals(False)

            QMessageBox.critical(
                self,
                "Munkalaplista hiba",
                f"Nem sikerült lekérni az ODS munkalapokat:\n\n{exc}",
            )

            self.completeChanged.emit()
            return

        if not sheets:
            self.status_label.setText("A kiválasztott ODS fájlban nincs munkalap.")
            self.sheet_combo.blockSignals(False)
            self.completeChanged.emit()
            return

        for sheet in sheets:
            label = f"{sheet.name}  —  sorok: {sheet.row_count}, oszlopok: {sheet.column_count}"
            self.sheet_combo.addItem(label, sheet.name)

        # Első munkalap előválasztása.
        self.sheet_combo.setCurrentIndex(0)

        selected_name = self.sheet_combo.currentData()
        self.wizard_ref.selected_sheet_name = str(selected_name) if selected_name else None

        self.status_label.setText(
            f"Talált munkalapok száma: {len(sheets)}\n"
            f"Kiválasztva: {self.wizard_ref.selected_sheet_name}"
        )

        self.sheet_combo.blockSignals(False)
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        """
        Akkor engedjük tovább a varázslót, ha van kiválasztott munkalap.
        """
        return bool(self.wizard_ref.selected_sheet_name)

    def _on_sheet_changed(self) -> None:
        """
        A kiválasztott munkalap nevének eltárolása.

        A lenyíló listában a látható szöveg tartalmazhat sor/oszlopszámot,
        ezért a valódi munkalapnevet a combo item data részében tároljuk.
        """
        selected_name = self.sheet_combo.currentData()

        if selected_name:
            self.wizard_ref.selected_sheet_name = str(selected_name)
            self.status_label.setText(
                f"Kiválasztott munkalap: {self.wizard_ref.selected_sheet_name}"
            )
        else:
            self.wizard_ref.selected_sheet_name = None
            self.status_label.setText("Nincs kiválasztott munkalap.")

        self.completeChanged.emit()





class RowSetupPage(QWizardPage):
    """
    Fejlécsor és adatsor kezdés beállító oldal.

    Feladata:
        - megmutatni a kiválasztott munkalap első néhány sorát
        - megadni, melyik sor a fejléc
        - megadni, honnan kezdődnek a tényleges adatsorok

    Fontos:
        Ez az oldal még nem készít tranzakció-importot.
        Csak előkészíti a következő előnézeti oldalt.
    """

    def __init__(self, wizard: "OdsTransactionImportWizard"):
        super().__init__(wizard)

        self.wizard_ref = wizard
        self.raw_rows: list[list[object]] = []

        

        self.setTitle("Fejlécsor és adatsorok beállítása")
        self.setSubTitle("")

        layout = QVBoxLayout(self)

        # Témafüggetlen figyelmeztető szöveg.
        # Ez nem dekoráció, hanem funkcionális figyelmeztetés:
        # ezen az oldalon kell jól beállítani a fejlécsort és az adatok kezdősorát.
        self.warning_label = QLabel(
            "<span style='color: #b00020; font-weight: 600;'>"
            "Ellenőrizd, melyik sor tartalmazza az oszlopneveket, "
            "és honnan indulnak az adatok."
            "</span>"
        )
        self.warning_label.setTextFormat(Qt.RichText)
        self.warning_label.setWordWrap(True)

        # Magyarázó blokk.
        # Csak a kulcsmondatok félkövérek, hogy ne legyen túl harsány az oldal.
        self.info_label = QLabel(
            "Ez az oldal a kiválasztott munkalap nyers táblázatrészletét mutatja.<br><br>"

            "<b>Itt csak azt állítod be</b>, hogy melyik sor legyen a fejlécsor, "
            "és melyik sortól kezdődjenek a tényleges tranzakciós adatok.<br><br>"

            "<span style='color: #b00020; font-weight: 600;'>"
            "A szoftver megpróbálja automatikusan felismerni az oszlopfejléceket.<br>"
            "Ha a felismerés hibás, ezen az oldalon kézzel javíthatod a fejlécsort "
            "és az adatok kezdősorát."
            "</span><br><br>"

            "<b>A feldolgozott import-előnézet</b> a következő oldalon jelenik meg."
        )
        self.info_label.setTextFormat(Qt.RichText)
        self.info_label.setWordWrap(True)




        self.header_row_spin = QSpinBox()
        self.header_row_spin.setMinimum(1)
        self.header_row_spin.setMaximum(5000)
        self.header_row_spin.setValue(1)
        self.header_row_spin.valueChanged.connect(self._on_rows_changed)

        self.data_start_row_spin = QSpinBox()
        self.data_start_row_spin.setMinimum(1)
        self.data_start_row_spin.setMaximum(5000)
        self.data_start_row_spin.setValue(2)
        self.data_start_row_spin.valueChanged.connect(self._on_rows_changed)

        
        # Összefoglaló + sorbeállítások egy közös dobozban.
        # Bal oldalon a munkalap és a betöltött sorok, jobb oldalon a két beállítható érték.
        self.summary_box = QFrame()
        self.summary_box.setObjectName("odsImportSummaryBox")

        summary_layout = QGridLayout(self.summary_box)
        summary_layout.setContentsMargins(12, 8, 12, 8)
        summary_layout.setHorizontalSpacing(36)
        summary_layout.setVerticalSpacing(6)

        self.sheet_info_label = QLabel("<b>Kiválasztott munkalap:</b> -")
        self.loaded_rows_label = QLabel("<b>Betöltött minta sorok száma:</b> -")

        header_text_label = QLabel("<b>Fejlécsor:</b>")
        data_start_text_label = QLabel("<b>Adatok kezdete:</b>")

        for label in (
            self.sheet_info_label,
            self.loaded_rows_label,
            header_text_label,
            data_start_text_label,
        ):
            label.setTextFormat(Qt.RichText)

        summary_layout.addWidget(self.sheet_info_label, 0, 0)
        summary_layout.addWidget(header_text_label, 0, 1, alignment=Qt.AlignRight)
        summary_layout.addWidget(self.header_row_spin, 0, 2)

        summary_layout.addWidget(self.loaded_rows_label, 1, 0)
        summary_layout.addWidget(data_start_text_label, 1, 1, alignment=Qt.AlignRight)
        summary_layout.addWidget(self.data_start_row_spin, 1, 2)

        summary_layout.setColumnStretch(0, 1)
        summary_layout.setColumnStretch(1, 0)
        summary_layout.setColumnStretch(2, 0)

        self.status_label = QLabel(
            "Ez még a nyers ODS-minta. "
            "A feldolgozott import-előnézet a következő oldalon jelenik meg."
        )
        self.status_label.setWordWrap(True)



       
        self.status_label = QLabel(
            "Ez még a nyers ODS-minta.\n"
            "A feldolgozott import-előnézet a következő oldalon jelenik meg."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(44)



        self.sample_table = QTableWidget()
        self.sample_table.setAlternatingRowColors(True)

        layout.addWidget(self.warning_label)
        layout.addSpacing(6)
        layout.addWidget(self.info_label)
        layout.addSpacing(8)
        layout.addWidget(self.summary_box)
        layout.addSpacing(6)
        layout.addWidget(self.status_label)
        layout.addWidget(self.sample_table, 1)





    def initializePage(self) -> None:
        """
        Az oldal megnyitásakor betöltjük a kiválasztott munkalap nyers sorait.

        Ez azért itt történik, mert a munkalapot az előző oldalon választjuk ki.
        """
        importer = self.wizard_ref.importer
        sheet_name = self.wizard_ref.selected_sheet_name

        self.raw_rows = []
        self.sample_table.clear()
        self.sample_table.setRowCount(0)
        self.sample_table.setColumnCount(0)

        if importer is None or not sheet_name:
            self.status_label.setText(
                "Nincs kiválasztott munkalap. Menj vissza, és válassz munkalapot."
            )
            self.completeChanged.emit()
            return

        try:
            # Csak mintát olvasunk, nem teljes importot.
            # Így gyors marad az oldal akkor is, ha a munkalap nagy.
            self.raw_rows = importer.read_sheet_rows(
                sheet_name=sheet_name,
                max_rows=80,
            )

        except Exception as exc:
            self.status_label.setText("Nem sikerült beolvasni a munkalap sorait.")

            QMessageBox.critical(
                self,
                "Sor-előnézet hiba",
                f"Nem sikerült beolvasni a munkalap sorait:\n\n{exc}",
            )

            self.completeChanged.emit()
            return

        if not self.raw_rows:
            self.status_label.setText("A kiválasztott munkalapon nincs beolvasható sor.")
            self.completeChanged.emit()
            return

        self._load_reasonable_defaults()
        self._refresh_sample_table()
        self._save_values_to_wizard()

        self.sheet_info_label.setText(f"<b>Kiválasztott munkalap:</b> {sheet_name}")
        self.loaded_rows_label.setText(
            f"<b>Betöltött minta sorok száma:</b> {len(self.raw_rows)}"
        )

        self.status_label.setText(
            "Ez még a nyers ODS-minta. "
            "A feldolgozott import-előnézet a következő oldalon jelenik meg."
        )

        self.completeChanged.emit()

    def isComplete(self) -> bool:
        """
        Akkor engedjük tovább a varázslót, ha a fejlécsor és az adatsor kezdete érvényes.
        """
        return self.data_start_row_spin.value() > self.header_row_spin.value()

    def _load_reasonable_defaults(self) -> None:
        """
        Alapértelmezett sorértékek beállítása.

        Első körben egyszerű szabály:
            - fejlécsor: a wizardban tárolt érték, alapból 1
            - adatok kezdete: fejlécsor + 1

        Később ide jöhet automatikus felismerés is:
            - dátum / összeg / megnevezés oszlopok keresése
            - Magyarázat_2024 típusú munkalapoknál 18. sor javaslása
        """
        
        guessed_header_row = self._guess_header_row_from_raw_rows()

        if guessed_header_row is not None:
            header_row = guessed_header_row
            data_start_row = header_row + 1
        else:
            header_row = max(1, int(self.wizard_ref.header_row))
            data_start_row = max(header_row + 1, int(self.wizard_ref.data_start_row))



        self.header_row_spin.blockSignals(True)
        self.data_start_row_spin.blockSignals(True)

        self.header_row_spin.setValue(header_row)
        self.data_start_row_spin.setValue(data_start_row)

        self.header_row_spin.blockSignals(False)
        self.data_start_row_spin.blockSignals(False)


    def _guess_header_row_from_raw_rows(self) -> int | None:
        """
        Fejlécsor automatikus tippelése a nyers ODS sorok alapján.

        Egyszerű pontozás:
            - végignézzük a betöltött mintasorokat
            - minden sor szöveges celláit kisbetűsítve összefűzzük
            - ismert oszlopnév-részletekre pontot adunk
            - a legtöbb pontot kapó sort javasoljuk fejlécsornak

        Fontos:
            Ez csak javaslat.
            A felhasználó továbbra is kézzel átállíthatja a spinboxot.
        """
        if not self.raw_rows:
            return None
        



        # Ezek azok a szavak/részletek, amelyek a régi ODS-ben
        # jó eséllyel fejlécsorra utalnak.

        header_keywords = {
            "dátum": 3,
            "időpont": 3,
            "nap": 1,
            "megnevezés": 3,
            "termék": 2,
            "szolgáltatás": 2,
            "munkabér": 2,
            "kiadás": 2,
            "ár": 3,
            "összeg": 3,
            "ár összesen": 4,
            "típus": 3,
            "tipus": 3,
            "típusa": 3,
            "megjegyzés": 2,
            "kategória": 2,
        }

        best_row_number: int | None = None
        best_score = 0

        for row_index, raw_row in enumerate(self.raw_rows):
            # A felhasználónak 1-től számozott sorokat mutatunk.
            row_number = row_index + 1

            # Egy sor összes celláját egy közös, kereshető szöveggé alakítjuk.
            row_text = " ".join(str(value).strip().lower() for value in raw_row if value)

            if not row_text:
                continue

            score = 0

            for keyword, points in header_keywords.items():
                if keyword in row_text:
                    score += points

            # Kis extra pont, ha a sorban több szöveges cella is van.
            # Ez segít megkülönböztetni a valódi fejlécsort az egycellás címektől.
            non_empty_cells = [value for value in raw_row if str(value).strip()]
            if len(non_empty_cells) >= 4:
                score += 2

            if score > best_score:
                best_score = score
                best_row_number = row_number

        # Ne találgassunk túl bátran.
        # Ha nincs legalább pár erős találat, inkább maradjon a kézi alapérték.
        if best_score < 6:
            return None

        return best_row_number















    def _on_rows_changed(self) -> None:
        """
        Sorbeállítások változásának kezelése.

        A módosított értékeket eltesszük a wizard közös állapotába,
        majd frissítjük az oldalon látható állapotüzenetet.
        """
        self._save_values_to_wizard()

        if self.data_start_row_spin.value() <= self.header_row_spin.value():
            self.status_label.setText(
                "Hiba: az adatok kezdősorának nagyobbnak kell lennie, mint a fejlécsor.\n"
                "Ez még a nyers ODS-minta oldala."
            )
        else:
            self.status_label.setText(
                "Nyers ODS-minta. "
                "A feldolgozott import-előnézet a következő oldalon jelenik meg."
            )

        self.completeChanged.emit()

    def _save_values_to_wizard(self) -> None:
        """
        A beállított sorértékek eltárolása a wizard közös állapotába.
        """
        self.wizard_ref.header_row = int(self.header_row_spin.value())
        self.wizard_ref.data_start_row = int(self.data_start_row_spin.value())

    def _refresh_sample_table(self) -> None:
        """
        Nyers munkalapminta betöltése a táblázatba.

        A bal szélső oszlop a tényleges sorszámot mutatja,
        hogy könnyebb legyen kiválasztani a fejlécsort és az adatok kezdősorát.
        """
        if not self.raw_rows:
            return

        max_columns = max((len(row) for row in self.raw_rows), default=0)

        self.sample_table.setRowCount(len(self.raw_rows))
        self.sample_table.setColumnCount(max_columns + 1)

        headers = ["Sor"] + [f"Oszlop {index + 1}" for index in range(max_columns)]
        self.sample_table.setHorizontalHeaderLabels(headers)

        for row_index, raw_row in enumerate(self.raw_rows):
            source_row_number = row_index + 1

            self.sample_table.setItem(
                row_index,
                0,
                QTableWidgetItem(str(source_row_number)),
            )

            for col_index in range(max_columns):
                value = raw_row[col_index] if col_index < len(raw_row) else ""

                self.sample_table.setItem(
                    row_index,
                    col_index + 1,
                    QTableWidgetItem(str(value)),
                )

        self.sample_table.resizeColumnsToContents()




class PreviewPage(QWizardPage):
    """
    Import előnézeti oldal.

    Feladata:
        - a kiválasztott ODS munkalapból tranzakció-előnézet készítése
        - az előnézeti sorok megjelenítése táblázatban
        - érvényes / hibás sorok számának kijelzése

    Fontos:
        Ez az oldal még nem ment adatbázisba.
        Csak a wizard.preview_rows listát tölti fel.
    """

    def __init__(self, wizard: "OdsTransactionImportWizard"):
        super().__init__(wizard)

        self.wizard_ref = wizard

        self.setTitle("Import előnézet")
        self.setSubTitle("Ellenőrizd, hogyan kerülnek értelmezésre az ODS sorai.")

        layout = QVBoxLayout(self)

        self.info_label = QLabel(
            "Az előnézet megmutatja, hogy a program milyen tranzakciókat "
            "készítene a kiválasztott munkalapból.\n\n"
            "Itt még nem történik adatbázisba mentés."
        )
        self.info_label.setWordWrap(True)

        self.status_label = QLabel("Az előnézet még nem készült el.")
        self.status_label.setWordWrap(True)

        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)

        layout.addWidget(self.info_label)
        layout.addSpacing(8)
        layout.addWidget(self.status_label)
        layout.addWidget(self.preview_table, 1)

    def initializePage(self) -> None:
        """
        Az oldal megnyitásakor elkészítjük az import előnézetet.

        Ehhez a wizard közös állapotából használjuk:
            - importer
            - selected_sheet_name
            - header_row
            - data_start_row
        """
        importer = self.wizard_ref.importer
        sheet_name = self.wizard_ref.selected_sheet_name
        header_row = int(self.wizard_ref.header_row)
        data_start_row = int(self.wizard_ref.data_start_row)

        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)

        self.wizard_ref.preview_rows = []


        if importer is None or not sheet_name:
            self.status_label.setText(
                "Nincs kiválasztott ODS fájl vagy munkalap. Menj vissza, és ellenőrizd a beállításokat."
            )
            self.completeChanged.emit()
            return

        try:
            preview_result = self._create_preview_rows(
                importer=importer,
                sheet_name=sheet_name,
                header_row=header_row,
                data_start_row=data_start_row,
            )

            preview_rows = self._normalize_preview_rows(preview_result)

        except Exception as exc:
            self.status_label.setText("Nem sikerült elkészíteni az import előnézetet.")

            QMessageBox.critical(
                self,
                "Előnézet hiba",
                f"Nem sikerült elkészíteni az import előnézetet:\n\n{exc}",
            )

            self.completeChanged.emit()
            return

        self.wizard_ref.preview_rows = preview_rows

        if preview_rows:
            first_row = preview_rows[0]
            print("### PREVIEW FIRST ROW TYPE:", type(first_row))
            print("### PREVIEW FIRST ROW DICT:", self._preview_row_to_dict(first_row))






        self._refresh_preview_table(preview_rows)

        valid_count = sum(1 for row in preview_rows if getattr(row, "is_valid", False))
        invalid_count = len(preview_rows) - valid_count

        self.status_label.setText(
            f"Kiválasztott munkalap: {sheet_name}\n"
            f"Fejlécsor: {header_row}, adatok kezdete: {data_start_row}\n"
            f"Előnézeti sorok száma: {len(preview_rows)}\n"
            f"Importálható: {valid_count}, hibás / kihagyandó: {invalid_count}"
        )

        self.completeChanged.emit()

    def isComplete(self) -> bool:
        """
        Akkor engedjük tovább a varázslót, ha legalább egy importálható sor van.
        """
        return any(
            getattr(row, "is_valid", False)
            for row in self.wizard_ref.preview_rows
        )

    def _create_preview_rows(
        self,
        importer: OdsTransactionImporter,
        sheet_name: str,
        header_row: int,
        data_start_row: int,
    ):
        """
        Tranzakció-előnézet elkészítése az importer segítségével.

        Megjegyzés:
            Itt az importer metódusneve lehet, hogy nálad más.
            Ha hibát dob, csak ezt az egy metódushívást kell igazítani
            az ods_transaction_importer.py tényleges függvénynevéhez.
        """
    


        column_map, preview_rows = importer.build_preview(
            sheet_name=sheet_name,
            header_row=header_row,
            data_start_row=data_start_row,
        )

        self.wizard_ref.column_map = column_map

        return preview_rows



    def _normalize_preview_rows(self, preview_result: object) -> list[object]:
        """
        Az importer előnézeti eredményének egységesítése.

        Azért kell, mert a build_preview() nem biztos, hogy közvetlenül
        list[PreviewTransaction] értéket ad vissza.

        Kezelt formák:
            - list[PreviewTransaction]
            - tuple/list csomag: (valid_rows, invalid_rows)
            - objektum .rows / .preview_rows attribútummal
        """
        if isinstance(preview_result, list):
            return preview_result

        if isinstance(preview_result, tuple):
            rows: list[object] = []

            for item in preview_result:
                if isinstance(item, list):
                    rows.extend(item)
                else:
                    rows.append(item)

            return rows

        for attr_name in ("rows", "preview_rows", "transactions"):
            value = getattr(preview_result, attr_name, None)

            if isinstance(value, list):
                return value

        return []
























    def _refresh_preview_table(self, preview_rows: list[object]) -> None:
        """
        Előnézeti sorok betöltése a táblázatba.

        A táblázat óvatosan, getattr-rel olvassa a mezőket,
        hogy kisebb PreviewTransaction mezőnév-változásoknál se omoljon össze.
        """
        headers = [
            "Állapot",
            "Forrássor",
            "Dátum",
            "Megnevezés",
            "Összeg",
            "Típus",
            "Kategória",
            "Megjegyzés",
            "Hiba / állapot",
        ]
        
        self.preview_table.setColumnCount(len(headers))
        self.preview_table.setHorizontalHeaderLabels(headers)
        self.preview_table.setRowCount(len(preview_rows))

        for row_index, preview_row in enumerate(preview_rows):
            row_data = self._preview_row_to_dict(preview_row)

            is_valid = bool(row_data.get("is_valid", False))

            values = [
                "Importálható" if is_valid else "Hibás",
                row_data.get("source_row", ""),
                row_data.get("tx_date", ""),
                row_data.get("description", ""),
                row_data.get("amount", ""),
                row_data.get("tx_type", ""),
                row_data.get("category", ""),
                "",
                row_data.get("status", ""),
            ]

            for column_index, value in enumerate(values):
                self.preview_table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(str(value)),
                )

        self.preview_table.resizeColumnsToContents()

    def _preview_row_to_dict(self, preview_row: object) -> dict[str, object]:
        """
        PreviewTransaction objektum biztonságos szótárrá alakítása.

        Kezeli:
            - dataclass alapú PreviewTransaction
            - sima objektum __dict__ mezőkkel
        """
        if is_dataclass(preview_row):
            return asdict(preview_row)

        if hasattr(preview_row, "__dict__"):
            return dict(vars(preview_row))

        return {}







#class FinishPage(QWizardPage):



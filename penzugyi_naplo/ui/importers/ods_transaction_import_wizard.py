# ui/importers/ods_transaction_import_wizard.py

"""
ODS tranzakció import varázsló
(ui/importers/ods_transaction_import_wizard.py).

Felelősség:
    - ODS fájl kiválasztása
    - munkalap kiválasztása
    - fejlécsorok számának megadása
    - import előnézet megjelenítése
    - importálható tranzakciók átadása a hívó félnek

Nem felelőssége:
    - ODS fájl tényleges feldolgozási logikája
    - adatbázisba írás
    - számlák / aranyszámla importálása
"""

from __future__ import annotations

from PySide6.QtWidgets import QWizard

from penzugyi_naplo.importers.ods_transaction_importer import (
    OdsTransactionImporter,
    PreviewTransaction,
)



from penzugyi_naplo.ui.importers.ods_import_pages import (
    FileSelectPage,
    IntroPage,
    PreviewPage,
    RowSetupPage,
    SheetSelectPage,
)


class OdsTransactionImportWizard(QWizard):
    """
    ODS tranzakció import előnézeti dialógus.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("ODS tranzakció import")
        self.resize(1100, 650)

        # Közös wizard állapot:
        # Ezeket az oldalak használják egymás után.
        self.file_path: str | None = None
        self.importer: OdsTransactionImporter | None = None
        self.preview_rows: list[PreviewTransaction] = []

        # A későbbi oldalak innen tudják, melyik munkalapot választotta a felhasználó.
        self.selected_sheet_name: str | None = None

        # A fejlécsor és az adatok kezdősora.
        # Ezeket a következő oldalak használják majd az előnézet készítéséhez.
        self.header_row: int = 1
        self.data_start_row: int = 2
        

        # Első körben csak azokat az oldalakat adjuk hozzá,
        # amelyek már ténylegesen léteznek.
        self.addPage(IntroPage(self))
        self.addPage(FileSelectPage(self))
        self.addPage(SheetSelectPage(self))
        self.addPage(RowSetupPage(self))
        self.addPage(PreviewPage(self))


        


   




    # ------------------------------------------------------------------
    # Publikus API
    # ------------------------------------------------------------------

    def get_importable_transactions(self) -> list[PreviewTransaction]:
        """
        Csak az érvényes előnézeti tranzakciókat adja vissza.
        """
        return [row for row in self.preview_rows if row.is_valid]

        
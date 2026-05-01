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

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from penzugyi_naplo.importers.ods_transaction_importer import (
    OdsTransactionImporter,
    PreviewTransaction,
)


class OdsTransactionImportWizard(QDialog):
    """
    ODS tranzakció import előnézeti dialógus.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("ODS tranzakció import")
        self.resize(1100, 650)

        self.importer: OdsTransactionImporter | None = None
        self.preview_rows: list[PreviewTransaction] = []

        self.file_path_label = QLabel("Nincs kiválasztott fájl")
        self.file_path_label.setWordWrap(True)

        self.choose_file_btn = QPushButton("ODS fájl kiválasztása…")
        self.choose_file_btn.clicked.connect(self.choose_file)

        self.sheet_combo = QComboBox()
        self.sheet_combo.currentIndexChanged.connect(self.reload_preview)

        self.header_row_spin = QSpinBox()
        self.header_row_spin.setMinimum(1)
        self.header_row_spin.setMaximum(5600)
        self.header_row_spin.setValue(1)
        self.header_row_spin.valueChanged.connect(self.reload_preview)

        self.data_start_row_spin = QSpinBox()
        self.data_start_row_spin.setMinimum(1)
        self.data_start_row_spin.setMaximum(5000)
        self.data_start_row_spin.setValue(2)
        self.data_start_row_spin.valueChanged.connect(self.reload_preview)

        self.status_label = QLabel("Válassz ki egy ODS fájlt az import előnézethez.")

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(8)
        self.preview_table.setHorizontalHeaderLabels(
            [
                "Importál?",
                "Dátum",
                "Típus",
                "Kategória",
                "Összeg",
                "Leírás",
                "Forrás sor",
                "Állapot",
            ]
        )

        self.import_btn = QPushButton("Import")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.accept)

        self.close_btn = QPushButton("Bezárás")
        self.close_btn.clicked.connect(self.reject)

        self._build_layout()

    # ------------------------------------------------------------------
    # Publikus API
    # ------------------------------------------------------------------

    def get_importable_transactions(self) -> list[PreviewTransaction]:
        """
        Csak az érvényes előnézeti tranzakciókat adja vissza.
        """
        return [row for row in self.preview_rows if row.is_valid]

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)

        file_row = QHBoxLayout()
        file_row.addWidget(self.choose_file_btn)
        file_row.addWidget(self.file_path_label, 1)

        options_row = QHBoxLayout()
        options_row.addWidget(QLabel("Munkalap:"))
        options_row.addWidget(self.sheet_combo, 1)

        options_row.addWidget(QLabel("Fejléc sora:"))
        options_row.addWidget(self.header_row_spin)

        options_row.addWidget(QLabel("Adatok kezdősora:"))
        options_row.addWidget(self.data_start_row_spin)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.import_btn)
        button_row.addWidget(self.close_btn)

        layout.addLayout(file_row)
        layout.addLayout(options_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.preview_table, 1)
        layout.addLayout(button_row)

    def choose_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "ODS fájl kiválasztása",
            str(Path.home()),
            "LibreOffice Calc fájlok (*.ods);;Minden fájl (*)",
        )

        if not file_path:
            return

        try:
            self.importer = OdsTransactionImporter(file_path)
            self.file_path_label.setText(file_path)

            self.sheet_combo.blockSignals(True)
            self.sheet_combo.clear()

            sheets = self.importer.list_sheets()
            for sheet in sheets:
                self.sheet_combo.addItem(sheet.name)

            self.sheet_combo.blockSignals(False)

            if sheets:
                preferred_index = 0

                for index, sheet in enumerate(sheets):
                    name = sheet.name.lower()

                    if "tranz" in name or "transaction" in name:
                        preferred_index = index
                        break

                self.sheet_combo.setCurrentIndex(preferred_index)

            self.reload_preview()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "ODS import hiba",
                f"Nem sikerült beolvasni az ODS fájlt:\n\n{exc}",
            )





    def reload_preview(self) -> None:
        if self.importer is None:
            return

        sheet_name = self.sheet_combo.currentText()
        if not sheet_name:
            return

        header_row = self.header_row_spin.value()
        data_start_row = self.data_start_row_spin.value()

        try:
            column_map, preview_rows = self.importer.build_preview(
                sheet_name=sheet_name,
                header_row=header_row,
                data_start_row=data_start_row,
                max_preview_rows=1000,
            )

            self.preview_rows = preview_rows
            self._fill_preview_table(preview_rows)

            valid_count = sum(1 for row in preview_rows if row.is_valid)
            invalid_count = len(preview_rows) - valid_count

            self.status_label.setText(
                f"Beolvasott sorok: {len(preview_rows)} | "
                f"Importálható: {valid_count} | "
                f"Hibás / kihagyandó: {invalid_count}"
            )

            self.import_btn.setEnabled(valid_count > 0)

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Előnézet hiba",
                f"Nem sikerült elkészíteni az import előnézetet:\n\n{exc}",
            )

    def _fill_preview_table(self, rows: list[PreviewTransaction]) -> None:
        self.preview_table.setRowCount(len(rows))

        for row_index, preview in enumerate(rows):
            self._set_item(row_index, 0, "✓" if preview.is_valid else "✗")
            self._set_item(row_index, 1, preview.tx_date or "")
            self._set_item(row_index, 2, self._human_type(preview.tx_type))
            self._set_item(row_index, 3, preview.category or "")
            self._set_item(row_index, 4, self._format_amount(preview.amount))
            self._set_item(row_index, 5, preview.description or "")
            self._set_item(row_index, 6, str(preview.source_row))
            self._set_item(row_index, 7, preview.status)

        self.preview_table.resizeColumnsToContents()

    def _set_item(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
        self.preview_table.setItem(row, column, item)

    def _human_type(self, tx_type: str | None) -> str:
        if tx_type == "income":
            return "Bevétel"
        if tx_type == "expense":
            return "Kiadás"
        return ""

    def _format_amount(self, amount: float | None) -> str:
        if amount is None:
            return ""

        return f"{amount:,.0f} Ft".replace(",", " ")
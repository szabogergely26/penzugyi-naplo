# importers/ods_transaction_importer.py

"""
ODS tranzakció importáló segédmodul.

Felelősség:
    - .ods fájlok beolvasása
    - munkalapok listázása
    - kiválasztott munkalap sorainak kiolvasása
    - fejlécsorok kihagyása
    - oszlopok alap automatikus felismerése
    - import előnézeti tranzakciók előállítása

Nem felelőssége:
    - grafikus felület kezelése
    - adatbázisba írás
    - végleges importálási döntés
    - számlák / aranyszámla kezelése
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
import unicodedata
from pathlib import Path
from typing import Any

from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf.text import P


@dataclass
class OdsSheetInfo:
    name: str
    row_count: int
    column_count: int


@dataclass
class ImportColumnMap:
    date_col: int | None = None
    description_col: int | None = None
    category_col: int | None = None
    income_col: int | None = None
    expense_col: int | None = None
    amount_col: int | None = None
    type_col: int | None = None
    note_col: int | None = None


@dataclass
class PreviewTransaction:
    source_row: int
    is_valid: bool
    status: str

    tx_date: str | None
    tx_type: str | None       # "income" vagy "expense"
    category: str | None
    amount: float | None
    description: str | None

    raw_values: list[Any]


class OdsTransactionImporter:
    """
    ODS fájlokból tranzakció előnézetet készítő importer.
    """

    def __init__(self, ods_path: str | Path):
        self.ods_path = Path(ods_path)
        self.document = load(str(self.ods_path))

    # ------------------------------------------------------------------
    # Publikus API
    # ------------------------------------------------------------------

    def list_sheets(self) -> list[OdsSheetInfo]:
        sheets: list[OdsSheetInfo] = []

        for table in self.document.spreadsheet.getElementsByType(Table):
            name = table.getAttribute("name") or "Névtelen munkalap"
            rows = self._read_table_rows(table, max_rows=20)
            row_count = len(rows)
            column_count = max((len(row) for row in rows), default=0)

            sheets.append(
                OdsSheetInfo(
                    name=name,
                    row_count=row_count,
                    column_count=column_count,
                )
            )

        return sheets

    def read_sheet_rows(
        self,
        sheet_name: str,
        max_rows: int | None = None,
    ) -> list[list[Any]]:
        table = self._get_table_by_name(sheet_name)
        return self._read_table_rows(table, max_rows=max_rows)

    def build_preview(
        self,
        sheet_name: str,
        header_row: int = 1,
        data_start_row: int = 2,
        max_preview_rows: int | None = 1000,
    ) -> tuple[ImportColumnMap, list[PreviewTransaction]]:
        rows = self.read_sheet_rows(sheet_name, max_rows=max_preview_rows)

        


        if not rows:
            return ImportColumnMap(), []

        header_index = header_row - 1
        data_start_index = data_start_row - 1

        header = rows[header_index] if 0 <= header_index < len(rows) else []
        column_map = self.detect_columns(header)

        


        preview: list[PreviewTransaction] = []

        for row_index, raw_row in enumerate(
            rows[data_start_index:],
            start=data_start_row,
        ):
            if self._is_empty_row(raw_row):
                continue

            tx = self._row_to_preview_transaction(
                source_row=row_index,
                row=raw_row,
                column_map=column_map,
            )
            preview.append(tx)

        return column_map, preview

    def detect_columns(self, header_row: list[Any]) -> ImportColumnMap:
        column_map = ImportColumnMap()

        for index, value in enumerate(header_row):
            normalized = self._normalize_header(value)

            if not normalized:
                continue

            if column_map.date_col is None and self._matches(normalized, ["datum", "date", "nap", "idopont", "ido", "idopontnap"]):
                column_map.date_col = index

            elif column_map.description_col is None and self._matches(
                normalized,
                [
                    "megnevezes", 
                    "leiras", 
                    "description", 
                    "nev", 
                    "tranzakcio", 
                    "tetel",
                    "termek",
                    "szolgaltatas",
                    "munkaber",
                    "kiadasmegnevezese",
                    "termekszolgaltatasmunkaberkiadasmegnevezese",
                ],
            ):
                column_map.description_col = index

            elif column_map.category_col is None and self._matches(
                normalized,
                ["kategoria", "category", "csoport"],
            ):
                column_map.category_col = index

            elif column_map.income_col is None and self._matches(
                normalized,
                ["bevetel", "income", "jovairas"],
            ):
                column_map.income_col = index

            elif column_map.expense_col is None and self._matches(
                normalized,
                ["kiadas", "expense", "koltseg", "terheles"],
            ):
                column_map.expense_col = index

            elif column_map.amount_col is None and self._matches(
                normalized,
                [
                    "osszeg", 
                    "amount", 
                    "ertek",
                    "arosszesen",
                    "fizetve",
                    "fizetendo",
                    "dij",
                    "koltseg",
                ],
            ):
                column_map.amount_col = index

            elif column_map.type_col is None and self._matches(
                normalized,
                ["tipus", "tipusa", "type", "irany"],
            ):
                column_map.type_col = index

            elif column_map.note_col is None and self._matches(
                normalized,
                ["megjegyzes", "note", "comment"],
            ):
                column_map.note_col = index


        # Ha van "Ár összesen" oszlop, az legyen az összeg,
        # ne a sima "Ár" / darabár oszlop.
        for index, value in enumerate(header_row):
            normalized = self._normalize_header(value)

            if normalized == "arosszesen":
                column_map.amount_col = index
                break


        for index, value in enumerate(header_row):
            normalized = self._normalize_header(value)

            if normalized == "tipusa":
                column_map.type_col = index
                break

        return column_map

    # ------------------------------------------------------------------
    # ODS beolvasás
    # ------------------------------------------------------------------

    def _get_table_by_name(self, sheet_name: str) -> Table:
        for table in self.document.spreadsheet.getElementsByType(Table):
            if table.getAttribute("name") == sheet_name:
                return table

        raise ValueError(f"Nem található ilyen munkalap: {sheet_name}")

    def _read_table_rows(
        self,
        table: Table,
        max_rows: int | None = 1000,
    ) -> list[list[Any]]:
        """
        Munkalap sorainak biztonságos beolvasása.

        Fontos:
            Az ODS fájlok gyakran number-rows-repeated attribútummal
            jelölnek nagyon sok üres sort. Ezeket nem szabad ténylegesen
            több százezer / millió Python listává kibontani.
        """
        result: list[list[Any]] = []

        effective_max_rows = max_rows or 1000

        for table_row in table.getElementsByType(TableRow):
            if len(result) >= effective_max_rows:
                break

            row_values = self._read_table_row(table_row)

            repeated_rows = self._get_repeat_count(
                table_row,
                "numberrowsrepeated",
            )

            # Üres ismételt sorból legfeljebb 1 darabot veszünk figyelembe.
            if self._is_empty_row(row_values):
                repeated_rows = 1

            # Semmilyen ismétlést nem engedünk a maradék limiten túl.
            remaining = effective_max_rows - len(result)
            repeated_rows = min(repeated_rows, remaining)

            for _ in range(repeated_rows):
                result.append(row_values.copy())

        return result

    
    def _read_table_row(self, table_row: TableRow) -> list[Any]:
        """
        Egy ODS sor biztonságos beolvasása.

        Fontos:
            Az ODS fájlok az egymás utáni üres cellákat gyakran
            number-columns-repeated attribútummal tárolják.

            Ezeket NEM szabad 1 darab üres cellára összenyomni,
            mert akkor az utána következő oszlopok balra csúsznak.

            Példa:
                K, L oszlop üres,
                M oszlop = Ár összesen,
                N oszlop = Tipusa

            Ha a K-L üres részt 1 cellára tömörítjük, akkor:
                M -> L
                N -> M

            Emiatt az importer rossz oszlopból olvassa az összeget
            és a típust.

        Védelem:
            A sort továbbra is maximum max_columns oszlopig bontjuk ki,
            hogy egy hibás / túl nagy ODS ne gyártson hatalmas listát.
        """
        values: list[Any] = []
        max_columns = 50

        for cell in table_row.getElementsByType(TableCell):
            if len(values) >= max_columns:
                break

            repeated_cols = self._get_repeat_count(
                cell,
                "numbercolumnsrepeated",
            )
            cell_value = self._read_cell_value(cell)

            # Fontos:
            # Üres celláknál is megtartjuk az ismétlésszámot,
            # mert különben elcsúszik az oszlopsorrend.
            remaining = max_columns - len(values)
            repeated_cols = min(repeated_cols, remaining)

            for _ in range(repeated_cols):
                values.append(cell_value)

        return values






    def _read_cell_value(self, cell: TableCell) -> Any:
        value_type = cell.getAttribute("valuetype")

        if value_type == "date":
            return cell.getAttribute("datevalue")

        if value_type in {"float", "currency", "percentage"}:
            value = cell.getAttribute("value")
            if value not in (None, ""):
                return value

        if value_type == "boolean":
            return cell.getAttribute("booleanvalue")

        texts: list[str] = []

        for p in cell.getElementsByType(P):
            text = self._extract_text(p)
            if text:
                texts.append(text)

        return " ".join(texts).strip()



    # Segédfüggvény:
    def _extract_text(self, node: Any) -> str:
        """
        ODF XML node szövegtartalmának kinyerése.

        Az odfpy elemeknél a str(element) nem mindig adja vissza a cellában
        látható szöveget, ezért rekurzívan végig kell menni a childNode-okon.
        """
        parts: list[str] = []

        for child in getattr(node, "childNodes", []):
            if getattr(child, "nodeType", None) == 3:
                parts.append(str(getattr(child, "data", "")))
            else:
                parts.append(self._extract_text(child))

        return "".join(parts)



    def _get_repeat_count(self, element: Any, attr_name: str) -> int:
        value = element.getAttribute(attr_name)

        if not value:
            return 1

        try:
            count = int(value)
        except (TypeError, ValueError):
            return 1

        # Biztonsági limit: ha az ODS milliós ismétlést kér,
        # azt nem bontjuk ki automatikusan.
        return max(1, min(count, 1000))

    # ------------------------------------------------------------------
    # Sor → előnézeti tranzakció
    # ------------------------------------------------------------------

    def _row_to_preview_transaction(
        self,
        source_row: int,
        row: list[Any],
        column_map: ImportColumnMap,
    ) -> PreviewTransaction:
        raw_date = self._get(row, column_map.date_col)
        raw_description = self._get(row, column_map.description_col)
        raw_note = self._get(row, column_map.note_col)
        raw_category = self._get(row, column_map.category_col)
        raw_income = self._get(row, column_map.income_col)
        raw_expense = self._get(row, column_map.expense_col)
        raw_amount = self._get(row, column_map.amount_col)
        raw_type = self._get(row, column_map.type_col)

        tx_date = self._parse_date(raw_date)
        category = self._clean_text(raw_category) or "Importált"
        description = self._build_description(raw_description, raw_note)

        income_amount = self._parse_amount(raw_income)
        expense_amount = self._parse_amount(raw_expense)
        generic_amount = self._parse_amount(raw_amount)

        tx_type: str | None = None
        amount: float | None = None

        if income_amount and income_amount > 0:
            tx_type = "income"
            amount = float(income_amount)

        elif expense_amount and expense_amount > 0:
            tx_type = "expense"
            amount = float(expense_amount)

        elif generic_amount and generic_amount != 0:
            amount = float(abs(generic_amount))
            tx_type = self._parse_type(raw_type, generic_amount)

        errors: list[str] = []

        if not tx_date:
            errors.append("Hiányzó vagy hibás dátum")

        if not tx_type:
            errors.append("Nem felismerhető típus")

        if amount is None or amount <= 0:
            errors.append("Hiányzó vagy hibás összeg")

        if not description:
            description = "Importált tranzakció"

        is_valid = not errors
        status = "OK" if is_valid else "; ".join(errors)

        return PreviewTransaction(
            source_row=source_row,
            is_valid=is_valid,
            status=status,
            tx_date=tx_date,
            tx_type=tx_type,
            category=category,
            amount=amount,
            description=description,
            raw_values=row,
        )

    # ------------------------------------------------------------------
    # Segédfüggvények
    # ------------------------------------------------------------------

    def _get(self, row: list[Any], index: int | None) -> Any:
        if index is None:
            return None
        if index < 0 or index >= len(row):
            return None
        return row[index]

    def _parse_date(self, value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, date):
            return value.isoformat()

        text = str(value).strip()
        if not text:
            return None

        # Régi ODS / kézzel írt dátumok normalizálása:
        # 2024.06.01. -> 2024.06.01
        # 2024-06-01  -> 2024.06.01
        # 2024/06/01  -> 2024.06.01
        text = text.replace("-", ".").replace("/", ".")
        text = text.rstrip(".")

        for fmt in ("%Y.%m.%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                pass

        return None

    def _parse_amount(self, value: Any) -> Decimal | None:
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        text = (
            text.replace("Ft", "")
            .replace("HUF", "")
            .replace("\xa0", "")
            .replace(" ", "")
            .replace(",", ".")
            .strip()
        )

        # például: "12.450" magyar ezresponttal problémás lehet,
        # ezért ha több pont van, az ezreselválasztókat kiszedjük
        if text.count(".") > 1:
            text = text.replace(".", "")

        try:
            return Decimal(text)
        except InvalidOperation:
            return None

    def _parse_type(self, raw_type: Any, amount: Decimal) -> str | None:
        text = self._normalize_header(raw_type)

        # Ha az összeg negatív, akkor biztosan kiadásként kezeljük.
        if amount < 0:
            return "expense"

        if self._matches(
            text,
            [
                "bevetel",
                "income",
                "jovairas",
                "munkaber",
                "ellatas",
                "tamogatas",
            ],
        ):
            return "income"

        if self._matches(
            text,
            [
                "kiadas",
                "expense",
                "koltseg",
                "terheles",
                "vasarlas",
                "szamlabefizetes",
                "keszpenzfelvetel",
            ],
        ):
            return "expense"

        return None

    def _build_description(self, main: Any, note: Any) -> str:
        main_text = self._clean_text(main)
        note_text = self._clean_text(note)

        if main_text and note_text:
            return f"{main_text} – {note_text}"

        return main_text or note_text or ""

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ""

        return str(value).strip()

    def _normalize_header(self, value: Any) -> str:
        text = "" if value is None else str(value).strip().lower()

        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^a-z0-9]+", "", text)

        return text

    def _matches(self, normalized: str, candidates: list[str]) -> bool:
        normalized_candidates = [self._normalize_header(candidate) for candidate in candidates]
        return any(candidate in normalized for candidate in normalized_candidates)

    def _is_empty_row(self, row: list[Any]) -> bool:
        return all(str(value).strip() == "" for value in row if value is not None)
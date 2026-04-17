# - penzugyi_naplo/core/utils.py
# -----------------------------------

"""
Általános segédfüggvények dátum- és pénzösszeg-kezeléshez (normalizálás/parse/format).

Fő cél: UI/CSV felől érkező bemenetek biztonságos tisztítása és egységesítése.
Tartalmaz többek közt: is_valid_date(), clean_amount_text(), parse_amount(),
format_number_hu(), month_key_from_date().

Függvények röviden:
    - is_valid_date(date_str) -> Optional[str]
        Dátum validálás/normalizálás 'YYYY-MM-DD' formára.
        Megj.: ha a megvalósítás strptime("%Y-%m-%d"), akkor a 'YYYY-M-D' elfogadása
        platform/Python-implementáció függő lehet (biztosra az explicit normalizálás a jó).

    - clean_amount_text(text, group_sep=" ", decimal_point=".") -> str
        Összegmező takarítás float() kompatibilisre: Ft/ft eltávolítás, NBSP/space,
        ezres tagolás kiszedése, tizedesjel normalizálása, CSV-vesszők kezelése.

    - parse_amount(text, ...) -> float
        clean_amount_text() után float()-t készít; üres bemenetnél ValueError.

    - format_number_hu(value) -> str
        Magyar ezres tagolás (szóköz), 0 tizedes; kerülje a scientific notation-t.

    - month_key_from_date(date_str) -> str
        'YYYY-MM-DD' -> 'YYYY-MM' (slice).
"""

from __future__ import annotations

import os
import subprocess
import sys

from datetime import datetime
from typing import Optional


def is_valid_date(date_str: str) -> Optional[str]:
    """
    Ellenőrzi, hogy a dátum 'YYYY-M-D' vagy 'YYYY-MM-DD' formátumú-e,
    és normalizálja 'YYYY-MM-DD' formátumra.

    Példa: '2025-2-7' -> '2025-02-07'
    """
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def clean_amount_text(
    text: str,
    group_sep: str = " ",
    decimal_point: str = ".",
) -> str:
    """
    Összeg mező takarítása float() kompatibilis formára.

    Kezeli:
    - ezres tagoló szóközök / csoportelválasztó
    - 'Ft' utótag
    - NBSP (\\xa0)
    - vessző/pont eltérések

    Visszatérés: olyan string, amit float(...) tud értelmezni.
    """
    if text is None:
        return ""

    s = str(text).strip()

    # tipikus utótagok/szemét
    s = s.replace("Ft", "").replace("ft", "").strip()
    s = s.replace("\xa0", "")  # NBSP
    s = s.replace(" ", "")

    # csoportelválasztó eltávolítása (ha nem szóköz volt)
    if group_sep and group_sep != " ":
        s = s.replace(group_sep, "")

    # tizedesjel normalizálása ponttá
    # (ha pl. decimal_point ',', akkor azt '.'-ra cseréljük)
    if decimal_point and decimal_point != ".":
        s = s.replace(decimal_point, ".")

    # biztos ami biztos: maradó vesszők ki
    # (CSV importnál előfordulhat)
    s = s.replace(",", "")

    return s


def parse_amount(
    text: str,
    group_sep: str = " ",
    decimal_point: str = ".",
) -> float:
    """
    Szövegből float összeg. Hibánál ValueError-t dob.
    """
    cleaned = clean_amount_text(text, group_sep=group_sep, decimal_point=decimal_point)
    if cleaned == "":
        raise ValueError("Üres összeg.")
    return float(cleaned)


def format_number_hu(value: str | int | float) -> str:
    """
    Magyar ezres tagolás: szóközös csoportosítás, 0 tizedesre kerekítve.
    Kerüli a tudományos jelölést.

    Példák:
    - 500000 -> '500 000'
    - 12345.67 -> '12 346'
    """
    try:
        num = float(str(value).replace(",", "."))
        if num == int(num):
            return f"{int(num):,}".replace(",", " ")
        return f"{num:,.0f}".replace(",", " ")
    except ValueError:
        return str(value)


def month_key_from_date(date_str: str) -> str:
    """
    'YYYY-MM-DD' -> 'YYYY-MM'
    """
    return date_str[:7] if date_str and len(date_str) >= 7 else ""




def open_with_default_app(path: str) -> None:
    if sys.platform.startswith("linux"):
        subprocess.Popen(["xdg-open", path])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        raise RuntimeError("Nem támogatott platform.")
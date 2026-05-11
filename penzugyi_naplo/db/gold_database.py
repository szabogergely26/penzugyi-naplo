# penzugyi_naplo/db/gold_database.py
# ---------------------------------------------------------

"""
Aranyszámla adatbázis-kezelés.

Feladata:
- az Aranyszámla modulhoz tartozó táblák létrehozása
- később arany vétel/eladás rekordok mentése és lekérdezése
"""

from __future__ import annotations

import sqlite3


def ensure_gold_tables(conn: sqlite3.Connection) -> None:
    """
    Létrehozza az Aranyszámla tábláit, ha még nem léteznek.

    A függvény meglévő adatbázis-kapcsolatot kap, hogy ugyanabba
    az adatbázisba dolgozzon, mint a Likviditás modul.
    """

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS gold_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT NOT NULL,
            trade_type TEXT NOT NULL CHECK (trade_type IN ('buy', 'sell')),
            grams REAL NOT NULL,
            unit_price_huf REAL,
            total_huf INTEGER,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
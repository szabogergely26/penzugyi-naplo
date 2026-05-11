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



    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_gold_transactions_trade_date
        ON gold_transactions(trade_date)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_gold_transactions_trade_type
        ON gold_transactions(trade_type)
        """
    )

    columns = {
        row[1]
        for row in cursor.execute("PRAGMA table_info(gold_transactions)").fetchall()
    }

    if "updated_at" not in columns:
        cursor.execute("ALTER TABLE gold_transactions ADD COLUMN updated_at TEXT")

    
    conn.commit()







def _connect(db_path: str) -> sqlite3.Connection:
    """
    SQLite kapcsolat létrehozása az Aranyszámla műveletekhez.

    A row_factory miatt a lekérdezések eredménye név szerint is elérhető lesz,
    például row["grams"] formában.
    """

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def add_gold_transaction(
    db_path: str,
    trade_date: str,
    trade_type: str,
    grams: float,
    unit_price_huf: float | None,
    total_huf: int | None,
    note: str = "",
) -> int:
    """
    Új arany vétel/eladás rekord mentése.

    trade_type:
    - 'buy'  = vétel
    - 'sell' = eladás

    Visszatér:
    - az új rekord adatbázis-azonosítójával.
    """

    if trade_type not in ("buy", "sell"):
        raise ValueError(f"Érvénytelen arany tranzakció típus: {trade_type}")

    if grams <= 0:
        raise ValueError("Az arany mennyisége csak pozitív szám lehet.")

    with _connect(db_path) as conn:
        ensure_gold_tables(conn)

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO gold_transactions (
                trade_date,
                trade_type,
                grams,
                unit_price_huf,
                total_huf,
                note
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                trade_date,
                trade_type,
                float(grams),
                unit_price_huf,
                total_huf,
                note.strip(),
            ),
        )

        conn.commit()
        return int(cur.lastrowid)


def list_gold_transactions(db_path: str) -> list[dict]:
    """
    Arany vétel/eladás rekordok listázása.

    A legfrissebb műveletek kerülnek előre.
    """

    with _connect(db_path) as conn:
        ensure_gold_tables(conn)

        rows = conn.execute(
            """
            SELECT
                id,
                trade_date,
                trade_type,
                grams,
                unit_price_huf,
                total_huf,
                note,
                created_at,
                updated_at
            FROM gold_transactions
            ORDER BY trade_date DESC, id DESC
            """
        ).fetchall()

    return [
        {
            "id": int(row["id"]),
            "trade_date": row["trade_date"],
            "trade_type": row["trade_type"],
            "grams": float(row["grams"]),
            "unit_price_huf": row["unit_price_huf"],
            "total_huf": row["total_huf"],
            "note": row["note"] or "",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def get_gold_summary(db_path: str) -> dict:
    """
    Aranyszámla összesítő lekérdezése.

    Számítás:
    - vétel növeli a grammot és az értéket
    - eladás csökkenti a grammot és az értéket

    Ez első körben bekerülési / rögzített érték alapú összesítő,
    nem aktuális árfolyamos piaci érték.
    """

    with _connect(db_path) as conn:
        ensure_gold_tables(conn)

        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN trade_type = 'buy' THEN grams
                        WHEN trade_type = 'sell' THEN -grams
                        ELSE 0
                    END
                ), 0) AS total_grams,

                COALESCE(SUM(
                    CASE
                        WHEN trade_type = 'buy' THEN COALESCE(total_huf, 0)
                        WHEN trade_type = 'sell' THEN -COALESCE(total_huf, 0)
                        ELSE 0
                    END
                ), 0) AS total_huf
            FROM gold_transactions
            """
        ).fetchone()

    return {
        "total_grams": float(row["total_grams"] or 0),
        "total_huf": int(row["total_huf"] or 0),
    }


# Tranzakció törlése:
def delete_gold_transaction(db_path: str, transaction_id: int) -> None:
    """
    Egy aranyszámla tranzakció törlése azonosító alapján.
    """

    with _connect(db_path) as conn:
        ensure_gold_tables(conn)

        conn.execute(
            """
            DELETE FROM gold_transactions
            WHERE id = ?
            """,
            (transaction_id,),
        )

        conn.commit()
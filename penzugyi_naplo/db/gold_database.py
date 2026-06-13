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


    # ---------------------------------------------------------
    # Aranyszámla tranzakciók tábla
    # ---------------------------------------------------------
    # Ebben tároljuk a számlás arany vétel/eladás műveleteket.
    #
    # trade_type:
    #   - buy  = vétel
    #   - sell = eladás
    #
    # A grams mező mindig pozitív érték, az irányt a trade_type adja meg.

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




    # ---------------------------------------------------------
    # Index: arany tranzakciók dátum szerint
    # ---------------------------------------------------------
    # A listázások és kimutatások gyakran dátum szerint rendeznek/szűrnek,
    # ezért a trade_date mezőre külön indexet készítünk.

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_gold_transactions_trade_date
        ON gold_transactions(trade_date)
        """
    )



    # ---------------------------------------------------------
    # Index: arany tranzakciók típus szerint
    # ---------------------------------------------------------
    # Később gyorsíthatja a vétel/eladás szerinti összesítéseket,
    # például amikor külön számoljuk a buy és sell rekordokat.

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_gold_transactions_trade_type
        ON gold_transactions(trade_type)
        """
    )



    # ---------------------------------------------------------
    # Séma migráció: updated_at oszlop pótlása
    # ---------------------------------------------------------
    # Régebbi adatbázisokban még nem biztos, hogy létezik az updated_at mező.
    # Ezért induláskor megnézzük a gold_transactions oszlopait, és ha hiányzik,
    # adatvesztés nélkül hozzáadjuk.

    columns = {
        row[1]
        for row in cursor.execute("PRAGMA table_info(gold_transactions)").fetchall()
    }

    if "updated_at" not in columns:
        cursor.execute("ALTER TABLE gold_transactions ADD COLUMN updated_at TEXT")






    # ---------------------------------------------------------
    # Fizikai aranytermékek tábla
    # ---------------------------------------------------------
    # Ebben tároljuk a fizikai aranyat:
    # aranylapka, érme, rúd, egyéb kézzel fogható termék.
    #
    # Fontos:
    #   - weight_grams = egy darab súlya grammban
    #   - quantity = darabszám
    #   - teljes gramm = weight_grams * quantity
    #
    # source példák:
    #   - gold_account = Aranyszámlából átvezetve
    #   - external = külső / kézi rögzítés


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS gold_physical_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_date TEXT NOT NULL,
            product_name TEXT NOT NULL,
            weight_grams REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price_huf REAL,
            total_huf INTEGER,
            source TEXT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    physical_columns = {
        row[1]
        for row in cursor.execute("PRAGMA table_info(gold_physical_items)").fetchall()
    }

    if "manufacturer" not in physical_columns:
        cursor.execute("ALTER TABLE gold_physical_items ADD COLUMN manufacturer TEXT")

    if "image_path" not in physical_columns:
        cursor.execute("ALTER TABLE gold_physical_items ADD COLUMN image_path TEXT")

    if "storage_location" not in physical_columns:
        cursor.execute("ALTER TABLE gold_physical_items ADD COLUMN storage_location TEXT")


    # ---------------------------------------------------------
    # Index: fizikai termékek vásárlási dátum szerint
    # ---------------------------------------------------------
    # A fizikai termékeket várhatóan dátum szerint listázzuk,
    # ezért a purchase_date mezőre is készül index.

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_gold_physical_items_purchase_date
        ON gold_physical_items(purchase_date)
        """
    )





    # ---------------------------------------------------------
    # Index: fizikai termékek forrás szerint
    # ---------------------------------------------------------
    # Ezzel később gyorsan szűrhető, hogy a fizikai termék
    # Aranyszámlából, külső vásárlásból vagy más forrásból származik-e.

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_gold_physical_items_source
        ON gold_physical_items(source)
        """
    )

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






# ---------------------------------------------------------
# Fizikai aranytermékek
# ---------------------------------------------------------
# Ezek a függvények a gold_physical_items táblát kezelik.
# Ide tartoznak a fizikai aranylapkák, érmék, rudak stb.


def list_gold_physical_items(db_path: str) -> list[dict]:
    """
    Fizikai aranytermékek listázása.

    A gold_physical_items táblából olvassa ki a rögzített fizikai
    aranytermékeket: aranylapka, érme, rúd vagy egyéb kézzel fogható
    aranytermék.

    A visszatérés list[dict] formátumú, hogy a UI oldalon könnyen
    lehessen táblázatba tölteni.

    Rendezés:
    - legfrissebb vásárlási dátum elöl
    - azonos dátumnál nagyobb id elöl
    """

    with _connect(db_path) as conn:
        ensure_gold_tables(conn)

        rows = conn.execute(
            """
            SELECT
                id,
                purchase_date,
                product_name,
                weight_grams,
                quantity,
                unit_price_huf,
                total_huf,
                source,
                note,
                created_at,
                manufacturer,
                image_path,
                storage_location

            FROM gold_physical_items
            ORDER BY purchase_date DESC, id DESC
            """
        ).fetchall()


    # ---------------------------------------------------------
    # SQLite sorok átalakítása dict listává
    # ---------------------------------------------------------
    # A sqlite3.Row objektum kényelmes DB-s forma, de a UI-nak jobb,
    # ha egyszerű dict-eket kap: item["product_name"], item["image_path"] stb.
    #
    # Itt számoljuk ki a total_weight_grams értéket is:
    # egy darab súlya * darabszám.

    return [
        {
            "id": int(row["id"]),
            "purchase_date": row["purchase_date"],
            "product_name": row["product_name"],
            "manufacturer": row["manufacturer"] or "",
            "image_path": row["image_path"] or "",
            "storage_location": row["storage_location"] or "",
            "weight_grams": float(row["weight_grams"]),
            "quantity": int(row["quantity"] or 1),
            "total_weight_grams": float(row["weight_grams"])
            * int(row["quantity"] or 1),
            "unit_price_huf": row["unit_price_huf"],
            "total_huf": row["total_huf"],
            "source": row["source"] or "",
            "note": row["note"] or "",
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_gold_physical_summary(db_path: str) -> dict:
    """
    Fizikai aranytermékek összesítője.

    Összesíti a gold_physical_items táblában található fizikai
    aranytermékeket.

    Számítás:
    - teljes fizikai gramm = weight_grams * quantity összege
    - teljes bekerülési érték = total_huf összege

    Fontos:
    - ha egy tételnél nincs total_huf megadva, akkor az 0-ként számít
    - ez bekerülési / rögzített érték, nem aktuális piaci árfolyam
    """

    with _connect(db_path) as conn:
        ensure_gold_tables(conn)

        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(weight_grams * quantity), 0) AS total_grams,
                COALESCE(SUM(COALESCE(total_huf, 0)), 0) AS total_huf
            FROM gold_physical_items
            """
        ).fetchone()

    return {
        "total_grams": float(row["total_grams"] or 0),
        "total_huf": int(row["total_huf"] or 0),
    }
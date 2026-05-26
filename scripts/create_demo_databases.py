from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_SCHEMA_DB = PROJECT_ROOT / "data" / "transactions.sqlite3"

DEMO_DIR = PROJECT_ROOT / "penzugyi_naplo" / "resources" / "demo"
PROD_DEMO_DB = DEMO_DIR / "transactions_demo.sqlite3"
DEV_DEMO_DB = DEMO_DIR / "transactions_dev_demo.sqlite3"


def create_schema_from_template(target_db: Path) -> None:
    """
    Új SQLite adatbázist hoz létre a meglévő adatbázis sémája alapján.

    Fontos:
    - csak CREATE TABLE / INDEX / VIEW / TRIGGER SQL-t vesz át
    - adatot nem másol
    - így személyes adat nem kerül át a demo adatbázisba
    """
    if target_db.exists():
        target_db.unlink()

    target_db.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(SOURCE_SCHEMA_DB) as source_conn:
        source_cursor = source_conn.cursor()

        source_cursor.execute(
            """
            SELECT type, name, sql
            FROM sqlite_master
            WHERE sql IS NOT NULL
              AND name != 'sqlite_sequence'
            ORDER BY
                CASE type
                    WHEN 'table' THEN 1
                    WHEN 'index' THEN 2
                    WHEN 'view' THEN 3
                    WHEN 'trigger' THEN 4
                    ELSE 5
                END,
                name
            """
        )
        schema_items = source_cursor.fetchall()

        source_cursor.execute("SELECT key, value FROM schema_version")
        schema_version_rows = source_cursor.fetchall()

    with sqlite3.connect(target_db) as target_conn:
        target_cursor = target_conn.cursor()

        for _type, name, sql in schema_items:
            if name.startswith("sqlite_"):
                continue
            target_cursor.execute(sql)

        if schema_version_rows:
            target_cursor.executemany(
                """
                INSERT OR REPLACE INTO schema_version (key, value)
                VALUES (?, ?)
                """,
                schema_version_rows,
            )

        target_conn.commit()


def insert_categories(cursor: sqlite3.Cursor) -> dict[str, int]:
    """
    Fiktív, demo célú kategóriák beszúrása.

    Visszaadja:
        kategórianév -> id
    """
    categories = [
        ("Fizetés", "income", 0),
        ("Családi támogatás", "income", 0),
        ("Egyéb bevétel", "income", 0),

        ("Élelmiszer", "expense", 0),
        ("Gyógyszer", "expense", 0),
        ("Termék", "expense", 0),
        ("Termék / Elektronika", "expense", 0),
        ("Közlekedés", "expense", 0),
        ("Szórakozás", "expense", 0),

        ("Számlabefizetés", "expense", 1),
        ("Telekom", "expense", 1),
        ("MVMNext", "expense", 1),
        ("Lakhatás", "expense", 1),
    ]

    category_ids: dict[str, int] = {}

    for name, tx_type, is_bill in categories:
        cursor.execute(
            """
            INSERT INTO categories (name, tx_type, is_bill)
            VALUES (?, ?, ?)
            """,
            (name, tx_type, is_bill),
        )
        category_ids[name] = int(cursor.lastrowid)

    return category_ids


def insert_transaction(
    cursor: sqlite3.Cursor,
    *,
    tx_date: str,
    tx_type: str,
    amount: float,
    category_id: int,
    description: str,
    name: str = "",
    payment_source: str = "bank",
    has_details: int = 0,
    period_start: str | None = None,
    period_end: str | None = None,
    invoice_number: str | None = None,
) -> int:
    year = int(tx_date[:4])
    month = int(tx_date[5:7])

    cursor.execute(
        """
        INSERT INTO transactions (
            tx_date,
            tx_type,
            amount,
            category_id,
            description,
            year,
            month,
            name,
            quantity,
            unit_price,
            has_details,
            payment_source,
            period_start,
            period_end,
            invoice_number
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tx_date,
            tx_type,
            amount,
            category_id,
            description,
            year,
            month,
            name,
            1,
            amount,
            has_details,
            payment_source,
            period_start,
            period_end,
            invoice_number,
        ),
    )

    return int(cursor.lastrowid)


def insert_demo_transactions(cursor: sqlite3.Cursor, category_ids: dict[str, int]) -> None:
    """
    Fiktív likviditási tranzakciók.
    """
    # Bevétel
    for month in range(1, 6):
        insert_transaction(
            cursor,
            tx_date=f"2026-{month:02d}-05",
            tx_type="income",
            amount=420_000,
            category_id=category_ids["Fizetés"],
            description="Demo havi fizetés",
            name="Demo fizetés",
            payment_source="bank",
        )

    insert_transaction(
        cursor,
        tx_date="2026-03-18",
        tx_type="income",
        amount=35_000,
        category_id=category_ids["Egyéb bevétel"],
        description="Demo egyszeri bevétel",
        name="Használt eszköz eladása",
        payment_source="bank",
    )

    # Kiadások
    demo_expenses = [
        ("2026-01-07", "Élelmiszer", 24_850, "Heti bevásárlás", "bank"),
        ("2026-01-12", "Gyógyszer", 8_990, "Gyógyszertár", "cash"),
        ("2026-01-20", "Termék / Elektronika", 39_990, "Bluetooth fejhallgató", "bank"),
        ("2026-02-06", "Élelmiszer", 31_420, "Havi nagybevásárlás", "bank"),
        ("2026-02-14", "Szórakozás", 12_500, "Mozi és vacsora", "bank"),
        ("2026-03-09", "Közlekedés", 9_500, "Bérlet / utazás", "bank"),
        ("2026-03-22", "Termék", 18_900, "Háztartási eszköz", "cash"),
        ("2026-04-04", "Élelmiszer", 27_300, "Bevásárlás", "bank"),
        ("2026-04-17", "Gyógyszer", 6_740, "Vitaminok", "bank"),
        ("2026-05-03", "Élelmiszer", 29_600, "Bevásárlás", "bank"),
    ]

    for tx_date, category, amount, description, payment_source in demo_expenses:
        insert_transaction(
            cursor,
            tx_date=tx_date,
            tx_type="expense",
            amount=amount,
            category_id=category_ids[category],
            description=description,
            name=description,
            payment_source=payment_source,
        )

    # Részletezett tranzakció demo
    detailed_id = insert_transaction(
        cursor,
        tx_date="2026-05-10",
        tx_type="expense",
        amount=15_470,
        category_id=category_ids["Élelmiszer"],
        description="Demo részletezett bevásárlás",
        name="Részletezett bevásárlás",
        payment_source="bank",
        has_details=1,
    )

    items = [
        ("2026-05-10", "Kenyér", "Élelmiszer", 690, 2, 1380),
        ("2026-05-10", "Tej", "Élelmiszer", 420, 4, 1680),
        ("2026-05-10", "Sajt", "Élelmiszer", 1890, 2, 3780),
        ("2026-05-10", "Zöldség", "Élelmiszer", 2450, 1, 2450),
        ("2026-05-10", "Egyéb élelmiszer", "Élelmiszer", 6180, 1, 6180),
    ]

    cursor.executemany(
        """
        INSERT INTO transaction_items (
            transaction_id,
            item_date,
            item_name,
            category_name,
            unit_price,
            quantity,
            amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (detailed_id, item_date, item_name, category, unit_price, quantity, amount)
            for item_date, item_name, category, unit_price, quantity, amount in items
        ],
    )

    # Korábbi évből pár sor, hogy az évszűrő / statisztika is mutasson valamit.
    old_rows = [
        ("2025-11-05", "income", 390_000, "Fizetés", "Demo 2025 fizetés"),
        ("2025-11-11", "expense", 23_400, "Élelmiszer", "Demo 2025 bevásárlás"),
        ("2025-12-05", "income", 405_000, "Fizetés", "Demo 2025 fizetés"),
        ("2025-12-20", "expense", 44_900, "Termék / Elektronika", "Demo 2025 elektronika"),
    ]

    for tx_date, tx_type, amount, category, description in old_rows:
        insert_transaction(
            cursor,
            tx_date=tx_date,
            tx_type=tx_type,
            amount=amount,
            category_id=category_ids[category],
            description=description,
            name=description,
            payment_source="bank",
        )


def insert_demo_bills(cursor: sqlite3.Cursor, category_ids: dict[str, int]) -> None:
    """
    Fiktív számla adatok.

    A kind értékeknél demo célra:
    - monthly
    - periodic
    """
    bills = [
        ("Telekom mobil", "monthly", "Demo havi mobilszámla"),
        ("MVMNext gáz", "periodic", "Demo időszakos gázszámla"),
        ("Lakbér / közös költség", "monthly", "Demo lakhatási költség"),
    ]

    bill_ids: dict[str, int] = {}

    for name, kind, notes in bills:
        cursor.execute(
            """
            INSERT INTO bills (name, kind, is_active, notes)
            VALUES (?, ?, 1, ?)
            """,
            (name, kind, notes),
        )
        bill_ids[name] = int(cursor.lastrowid)

    # Havi számlák
    for month in range(1, 6):
        cursor.execute(
            """
            INSERT INTO bill_monthly_amounts (bill_id, year, month, amount)
            VALUES (?, ?, ?, ?)
            """,
            (bill_ids["Telekom mobil"], 2026, month, 8_990),
        )

        cursor.execute(
            """
            INSERT INTO bill_monthly_amounts (bill_id, year, month, amount)
            VALUES (?, ?, ?, ?)
            """,
            (bill_ids["Lakbér / közös költség"], 2026, month, 95_000),
        )

    # Időszakos számla példa
    periodic_rows = [
        ("2026-01-01", "2026-01-31", 18_500),
        ("2026-02-01", "2026-02-28", 16_900),
        ("2026-03-01", "2026-03-31", 14_200),
        ("2026-04-01", "2026-04-30", 10_800),
    ]

    for start, end, amount in periodic_rows:
        cursor.execute(
            """
            INSERT INTO bill_periodic_amounts (bill_id, start, end, amount)
            VALUES (?, ?, ?, ?)
            """,
            (bill_ids["MVMNext gáz"], start, end, amount),
        )

    # Ugyanezek tranzakcióként is megjelennek.
    bill_transactions = [
        ("2026-01-15", "Telekom", 8_990, "Telekom mobil január"),
        ("2026-02-15", "Telekom", 8_990, "Telekom mobil február"),
        ("2026-03-15", "Telekom", 8_990, "Telekom mobil március"),
        ("2026-04-15", "Telekom", 8_990, "Telekom mobil április"),
        ("2026-01-22", "MVMNext", 18_500, "MVMNext gáz január"),
        ("2026-02-22", "MVMNext", 16_900, "MVMNext gáz február"),
        ("2026-03-22", "MVMNext", 14_200, "MVMNext gáz március"),
        ("2026-04-22", "MVMNext", 10_800, "MVMNext gáz április"),
        ("2026-01-10", "Lakhatás", 95_000, "Lakbér / közös költség január"),
        ("2026-02-10", "Lakhatás", 95_000, "Lakbér / közös költség február"),
        ("2026-03-10", "Lakhatás", 95_000, "Lakbér / közös költség március"),
        ("2026-04-10", "Lakhatás", 95_000, "Lakbér / közös költség április"),
    ]

    for tx_date, category, amount, description in bill_transactions:
        insert_transaction(
            cursor,
            tx_date=tx_date,
            tx_type="expense",
            amount=amount,
            category_id=category_ids[category],
            description=description,
            name=description,
            payment_source="bank",
            period_start=None,
            period_end=None,
            invoice_number="DEMO-SZLA",
        )


def insert_demo_plans(cursor: sqlite3.Cursor) -> None:
    for month in range(1, 13):
        cursor.execute(
            """
            INSERT OR REPLACE INTO plans (
                year,
                month,
                planned_income,
                planned_expense,
                planned_fixed_expense
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (2026, month, 420_000, 260_000, 130_000),
        )


def insert_demo_wallets(cursor: sqlite3.Cursor) -> None:
    wallet_rows = [
        ("2026-01-31", "bank", 585_000),
        ("2026-01-31", "cash", 45_000),
        ("2026-02-28", "bank", 642_000),
        ("2026-02-28", "cash", 38_000),
        ("2026-03-31", "bank", 701_000),
        ("2026-03-31", "cash", 52_000),
        ("2026-04-30", "bank", 748_000),
        ("2026-04-30", "cash", 41_000),
    ]

    cursor.executemany(
        """
        INSERT INTO wallet_balances (date, wallet_type, value)
        VALUES (?, ?, ?)
        """,
        wallet_rows,
    )

    account_rows = [
        ("2026-01-31", "securities", 350_000),
        ("2026-02-28", "securities", 365_000),
        ("2026-03-31", "securities", 382_000),
        ("2026-04-30", "securities", 395_000),
    ]

    cursor.executemany(
        """
        INSERT INTO account_valuations (date, account_type, value)
        VALUES (?, ?, ?)
        """,
        account_rows,
    )


def insert_demo_gold(cursor: sqlite3.Cursor) -> None:
    gold_rows = [
        ("2026-01-12", "buy", 1.25, 41_200, 51_500, "Demo arany vétel"),
        ("2026-02-08", "buy", 2.10, 42_000, 88_200, "Demo arany vétel"),
        ("2026-03-21", "buy", 0.85, 43_500, 36_975, "Demo arany vétel"),
        ("2026-04-15", "sell", 0.50, 45_000, 22_500, "Demo arany eladás"),
        ("2026-05-06", "buy", 1.40, 44_200, 61_880, "Demo arany vétel"),
    ]

    cursor.executemany(
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
        gold_rows,
    )


def fill_demo_database(target_db: Path, *, include_gold: bool) -> None:
    create_schema_from_template(target_db)

    with sqlite3.connect(target_db) as conn:
        cursor = conn.cursor()

        category_ids = insert_categories(cursor)
        insert_demo_transactions(cursor, category_ids)
        insert_demo_bills(cursor, category_ids)
        insert_demo_plans(cursor)
        insert_demo_wallets(cursor)

        if include_gold:
            insert_demo_gold(cursor)

        conn.commit()


def main() -> None:
    if not SOURCE_SCHEMA_DB.exists():
        raise FileNotFoundError(f"Sémaforrás nem található: {SOURCE_SCHEMA_DB}")

    fill_demo_database(PROD_DEMO_DB, include_gold=False)
    fill_demo_database(DEV_DEMO_DB, include_gold=True)

    print("Demo adatbázisok elkészültek:")
    print(f"  PROD: {PROD_DEMO_DB}")
    print(f"  DEV : {DEV_DEMO_DB}")


if __name__ == "__main__":
    main()
# /db/transaction_database.py
# ------------------------------

"""
Központi SQLite adatbázis-réteg a Pénzügyi Naplóhoz
(penzugyi_naplo/db/transaction_database.py).

Ez az egyetlen DB API a teljes alkalmazás számára.
Minden UI oldal (Home, Tranzakciók, Statisztika, később Számlák)
kizárólag ezen az osztályon keresztül éri el az adatbázist.
A UI nem tartalmaz SQL-t.

----------------------------------------------------------------

B-modell (adatmodell-szerződés)

A B-modellt a DB réteg garantálja (nem a wizard), mert több bemeneti út is létezhet
(import/CSV, bulk, régi DB megnyitás), és a végső igazság az adatbázisban van.

Szabályok:
    - amount mindig POZITÍV
    - tx_type: 'income' | 'expense'

Régi adatbázis esetén automatikus migráció:
    - negatív összegek → expense
    - HU típusnevek → belső income/expense formátum
    - year/month automatikus számítása tx_date alapján
    - hiányzó oszlopok pótlása (pl. name)

----------------------------------------------------------------

Adatbázis szintű felelősségek

Táblák:
    - transactions
    - categories
    - settings
    - schema_version

CRUD műveletek:
    - save_transaction
    - update_transaction
    - delete_transaction
    - add_bulk_transactions

UI lekérdezések:
    - get_transactions_filtered        → Tranzakciók oldal
    - get_available_years              → évválasztó
    - get_monthly_summary
    - get_annual_totals
    - get_monthly_income_expense*      → dashboard / diagramok

----------------------------------------------------------------

Tudatosan NEM UI-függő:
    - nincs Qt / widget / layout
    - csak tiszta adat- és üzleti logika
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

# ----------------------------
# B modell:
# - amount mindig POZITÍV
# - tx_type: 'income' | 'expense'
# ----------------------------

TxType = str  # 'income' | 'expense'


# ------- Helper függvények -------

# -- helper függvény = „hogyan alakítom/validálom a bejövő értékeket”
# (pl. db legyen mindig legalább 1)


def _now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _iso_date(d: date | str) -> str:
    if isinstance(d, date):
        return d.isoformat()
    return str(d)


def _year_month_from_iso(iso: str) -> tuple[int, int]:
    # 'YYYY-MM-DD' -> (YYYY, MM)
    y = int(iso[0:4])
    m = int(iso[5:7])
    return y, m


def _map_hu_to_type(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v in ("bevétel", "bevetel", "income"):
        return "income"
    if v in ("kiadás", "kiadas", "expense"):
        return "expense"
    # fallback
    return "expense"


def _type_to_hu(value: str) -> str:
    return "Bevétel" if value == "income" else "Kiadás"


def _normalize_quantity(value: Any) -> int:
    """
    quantity: None/"" -> 1
    quantity: 0/1/negatív -> 1
    quantity: >1 -> int
    """
    try:
        if value is None:
            return 1
        if isinstance(value, str) and value.strip() == "":
            return 1
        q = int(float(value))
        return q if q > 1 else 1
    except Exception:
        return 1


def _to_float_or_none(value: Any) -> float | None:
    """
    Üres/None -> None
    "  " -> None
    "150" -> 150.0
    """
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


# --- Dataclass-ok: ----

# dataclass = „milyen mezőkből áll egy rekord”


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    tx_type: str  # 'income' | 'expense'


@dataclass(frozen=True)
class TransactionRow:
    id: int
    tx_date: str  # 'YYYY-MM-DD'
    category_name: str
    amount: float  # ALWAYS positive
    description: str
    tx_type: str  # 'income' | 'expense'
    category_id: int


class TransactionDatabase:
    """
    SQLite tranzakció adatbázis.

    Kompatibilitás:
    - felismeri a régi sémát (date/type/amount + negatív kiadás) és automatikusan migrál B modellre
    - adatvesztés nélkül: amount abs(), type normalizálás, year/month oszlopok
    """

    def __init__(self, db_name: str = "finance_data.db") -> None:
        self.db_name = os.path.abspath(db_name)
        self.initialize_db()
        self.ensure_account_valuations()

    def get_db_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    # Helper:
    def _column_exists(self, cur: sqlite3.Cursor, table: str, column: str) -> bool:
        cols = [
            r["name"] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()
        ]
        return column in cols

    def close(self) -> None:
        # SQLite esetén itt nincs mit zárni, mert minden metódus saját conn-t nyit/zár.
        pass

    def add_account_valuation(
        self, date_iso: str, account_type: str, value: float
    ) -> None:
        """
        Új account valuation beszúrása.
        date_iso: 'YYYY-MM-DD'
        account_type: 'securities' | 'metals' (vagy később bővíthető)
        """
        if account_type not in ("securities", "metals"):
            raise ValueError(f"Invalid account_type: {account_type}")

        # Biztos ami biztos: legyen tábla (főleg régi DB-nél / dev DB-nél)
        self.ensure_account_valuations()

        with self.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO account_valuations(date, account_type, value)
                VALUES (?, ?, ?)
                """,
                (date_iso, account_type, float(value)),
            )
            conn.commit()

    def list_account_valuations(self, limit: int = 30):
        """
        Utolsó N valuation sor listázása (dátum szerint csökkenő).
        Visszatér: list[dict] formában: {date, account_type, value}
        """
        # Biztos ami biztos
        self.ensure_account_valuations()

        with self.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT date, account_type, value
                FROM account_valuations
                ORDER BY date DESC, id DESC
                LIMIT ?
                """,
                (int(limit),),
            )
            rows = cur.fetchall()

        return [{"date": r[0], "account_type": r[1], "value": r[2]} for r in rows]

    # ----------------------------
    # Schema + migration
    # ----------------------------

    # NOTE:
    # initialize_db() két ágra bomlik:

    #       - ÚJ DB: nincs 'transactions' tábla -> early return a commit után
    #       - RÉGI DB: van 'transactions' -> migráció/ensure a blokk alatt
    # Emiatt minden "mindig kell" sémát (pl. bills, wallets, valuations) mindkét ágban ensure-olni kell,
    # különben új DB-nél a return miatt nem jön létre.

    def initialize_db(self) -> None:
        conn = self.get_db_connection()
        cur = conn.cursor()
        print("DB PATH:", self.db_name)
        # schema version (minimal migration framework)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            "INSERT OR IGNORE INTO schema_version(key, value) VALUES ('version', 1)"
        )

        # settings (marad)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                last_updated TEXT
            )
            """
        )

        # plans (havi tervek)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                year INTEGER NOT NULL,
                month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
                planned_income REAL NOT NULL DEFAULT 0,
                planned_expense REAL NOT NULL DEFAULT 0,
                planned_fixed_expense REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (year, month)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_plans_year_month ON plans(year, month)"
        )

        # categories (new: tx_type)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                tx_type TEXT NOT NULL CHECK (tx_type IN ('income', 'expense'))
            )
            """
        )

        # detect old/new transactions table, mindig lefut
        cur.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='transactions'
            """
        )
        has_transactions = cur.fetchone() is not None

        # ----- Új DB ág:

        if not has_transactions:
            self._create_transactions_table(cur)
            self._seed_default_categories(cur)

            self._ensure_transaction_columns(cur)
            self._ensure_details_schema(cur)
            self._ensure_category_columns(cur)
            self._seed_bill_categories(cur)

            self._ensure_account_valuations(cur)

            self._ensure_indexes(cur)

            self._ensure_wallet_balances(cur)

            self._ensure_bills_schema(cur)

            conn.commit()
            conn.close()
            return

        # --- Új DB ág vége ----

        # table exists: detect schema
        cols = [
            r["name"] for r in cur.execute("PRAGMA table_info(transactions)").fetchall()
        ]

        # ha hiányzik a name oszlop, pótoljuk (régi DB kompatibilitás)
        if "name" not in cols:
            cur.execute("ALTER TABLE transactions ADD COLUMN name TEXT")
            # visszatöltés: ahol nincs name, legyen name = description
            cur.execute(
                "UPDATE transactions SET name = COALESCE(NULLIF(name, ''), description) WHERE name IS NULL OR name = ''"
            )

        if "tx_date" not in cols:
            # old schema -> migrate
            self._migrate_transactions_to_b_model(cur)

        # ensure default categories exist (idempotens)
        self._seed_default_categories(cur)
        self._seed_bill_categories(cur)

        # ensure transaction columns
        self._ensure_transaction_columns(cur)  # unit_price, quantity (ha ezt választod)
        self._ensure_details_schema(cur)  # ensure details schema

        # (ha kell a bills logika)
        self._ensure_category_columns(cur)  # is_bill

        self._ensure_account_valuations(cur)

        # ensure indexes exist
        self._ensure_indexes(cur)

        self._ensure_wallet_balances(cur)
        self._ensure_bills_schema(cur)

        conn.commit()
        conn.close()

    def _create_transactions_table(self, cur: sqlite3.Cursor) -> None:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_date TEXT NOT NULL,   -- 'YYYY-MM-DD'
                tx_type TEXT NOT NULL CHECK (tx_type IN ('income', 'expense')),
                amount REAL NOT NULL CHECK (amount >= 0),
                category_id INTEGER NOT NULL,
                name TEXT,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                year INTEGER NOT NULL,
                month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
            """
        )

    def _ensure_indexes(self, cur: sqlite3.Cursor) -> None:
        cur.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_year_month ON transactions(year, month);
            CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(tx_date);
            CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(tx_type);
            CREATE INDEX IF NOT EXISTS idx_categories_type ON categories(tx_type);
            """
        )

    def _seed_default_categories(self, cur: sqlite3.Cursor) -> None:
        default_categories = [
            ("Fizetés", "income"),
            ("Egyéb bevétel", "income"),
            ("Élelmiszer", "expense"),
            ("Lakbér/Törlesztés", "expense"),
            ("Szórakozás", "expense"),
            ("Közlekedés", "expense"),
            ("Egyéb kiadás", "expense"),
        ]
        for name, t in default_categories:
            try:
                cur.execute(
                    "INSERT INTO categories (name, tx_type) VALUES (?, ?)", (name, t)
                )
            except sqlite3.IntegrityError:
                # Ha létezik, biztosítjuk, hogy a típusa is helyes legyen (ha régi HU maradt volna)
                cur.execute("UPDATE categories SET tx_type=? WHERE name=?", (t, name))

    def _migrate_transactions_to_b_model(self, cur: sqlite3.Cursor) -> None:
        """
        Régi séma:
          transactions(id, date, type, amount, category_id, description, timestamp)
          categories(id, name, type) ahol type HU (Bevétel/Kiadás)
        Új séma:
          transactions(tx_date, tx_type(income|expense), amount>=0, year, month, created_at)
          categories(name, tx_type(income|expense))
        """
        # 1) migrate categories HU->internal
        cat_cols = [
            r["name"] for r in cur.execute("PRAGMA table_info(categories)").fetchall()
        ]
        if "type" in cat_cols and "tx_type" not in cat_cols:
            cur.execute("ALTER TABLE categories RENAME COLUMN type TO tx_type")

        # normalizáljuk a categories.tx_type tartalmat
        rows = cur.execute("SELECT id, tx_type FROM categories").fetchall()
        for r in rows:
            new_type = _map_hu_to_type(r["tx_type"])
            cur.execute(
                "UPDATE categories SET tx_type=? WHERE id=?", (new_type, int(r["id"]))
            )

        # 2) create new transactions table
        cur.execute("ALTER TABLE transactions RENAME TO transactions_old")
        self._create_transactions_table(cur)

        # 3) copy data
        old_rows = cur.execute(
            """
            SELECT id, date, type, amount, category_id, description, timestamp
            FROM transactions_old
            ORDER BY id
            """
        ).fetchall()

        for r in old_rows:
            iso = str(r["date"])
            # type: régi táblában lehet HU vagy bármi; ha hiányos, amount előjeléből
            t_raw = str(r["type"]) if r["type"] is not None else ""
            tx_type = _map_hu_to_type(t_raw)
            amt = float(r["amount"] or 0.0)
            if amt < 0:
                # régi modell: negatív kiadás
                tx_type = "expense"
                amt = abs(amt)
            else:
                # ha t_raw alapján kiadás, marad kiadás
                if tx_type == "expense":
                    amt = abs(amt)
            y, m = _year_month_from_iso(iso)
            created_at = str(r["timestamp"] or _now_ts())
            cur.execute(
                """
                INSERT INTO transactions
                    (id, tx_date, tx_type, amount, category_id, description, created_at, year, month)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(r["id"]),
                    iso,
                    tx_type,
                    float(amt),
                    int(r["category_id"]),
                    str(r["description"] or ""),
                    created_at,
                    y,
                    m,
                ),
            )

        # 4) drop old
        cur.execute("DROP TABLE transactions_old")

        # 5) update exports/settings names if needed (no-op)

    # ----------
    # Wallets
    # ----------

    def _ensure_wallet_balances(self, cur) -> None:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wallet_balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,           -- YYYY-MM-DD
                wallet_type TEXT NOT NULL,    -- 'cash' (később: 'bank', 'szep', ...)
                value REAL NOT NULL
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_wallet_balances_type_date
            ON wallet_balances(wallet_type, date);
        """)

    def ensure_wallet_balances(self) -> None:
        with self.get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wallet_balances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    wallet_type TEXT NOT NULL,
                    value REAL NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_wallet_balances_type_date
                ON wallet_balances(wallet_type, date);
            """)
            conn.commit()

    def set_wallet_balance(self, date_iso: str, wallet_type: str, value: float) -> None:
        valid_wallet_types = ("cash", "current_account")
        if wallet_type not in valid_wallet_types:
            raise ValueError(f"Invalid wallet_type: {wallet_type}")

        self.ensure_wallet_balances()
        with self.get_db_connection() as conn:
            conn.execute(
                "INSERT INTO wallet_balances(date, wallet_type, value) VALUES (?, ?, ?)",
                (date_iso, wallet_type, float(value)),
            )
            conn.commit()

    def get_latest_wallet_balance(self, wallet_type: str):
        valid_wallet_types = ("cash", "current_account")
        if wallet_type not in valid_wallet_types:
            raise ValueError(f"Invalid wallet_type: {wallet_type}")

        self.ensure_wallet_balances()
        with self.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT date, value
                FROM wallet_balances
                WHERE wallet_type = ?
                ORDER BY date DESC, id DESC
                LIMIT 1
                """,
                (wallet_type,),
            )
            row = cur.fetchone()

        if not row:
            return None
        return {"date": row[0], "value": row[1]}

    # ----------------------------
    # Categories
    # ----------------------------

    def get_all_categories(self):
        conn = self.get_db_connection()
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT id, name, tx_type FROM categories ORDER BY name"
        ).fetchall()
        conn.close()
        return rows

    def get_category_id_by_name(self, name: str) -> int | None:
        with self.get_db_connection() as conn:
            row = conn.execute(
                "SELECT id FROM categories WHERE name = ?",
                (str(name),),
            ).fetchone()
            return int(row["id"]) if row else None

    # ----------------------------
    # Transactions
    # ----------------------------

    def save_transaction(self, data: dict) -> int:
        """
        data elvárt kulcsok:
        date: 'YYYY-MM-DD'
        type: 'income' | 'expense' (HU-t is elfogad: 'Bevétel'/'Kiadás')
        amount: pozitív szám
        category_id: int
        description: optional
        payment_source: 'bank' | 'cash' (opcionális, default: 'bank')
        """
        iso = _iso_date(data["date"])
        tx_type = _map_hu_to_type(data["type"])
        amount = float(data["amount"])
        if amount < 0:
            raise ValueError("B modell: amount nem lehet negatív.")

        y, m = _year_month_from_iso(iso)
        created_at = data.get("timestamp") or _now_ts()
        payment_source = (
            str(data.get("payment_source", "bank") or "bank").strip().lower()
        )

        if payment_source not in {"bank", "cash"}:
            payment_source = "bank"

        conn = self.get_db_connection()
        cur = conn.cursor()

        self._ensure_payment_source_column(cur)

        cur.execute(
            """
            INSERT INTO transactions (
                tx_date, tx_type, amount, category_id, name, description,
                created_at, year, month, payment_source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                iso,
                tx_type,
                amount,
                int(data["category_id"]),
                data.get("name", "") or "",
                data.get("description", "") or "",
                created_at,
                y,
                m,
                payment_source,
            ),
        )
        tx_id = int(cur.lastrowid)
        conn.commit()
        conn.close()
        return tx_id

    def get_transactions(self):
        conn = self.get_db_connection()
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT
                t.id,
                t.tx_date AS date,
                c.name AS category_name,
                t.amount,
                t.description,
                t.tx_type AS type,
                t.category_id
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            ORDER BY t.created_at DESC, t.id DESC
            """
        ).fetchall()
        conn.close()
        return rows

    def get_transactions_filtered(
        self,
        *,
        year: int | None = None,
        all_years: bool = True,
        query: str | None = None,
        limit: int = 1000,
    ) -> list[Any]:
        where: list[str] = []
        params: list[Any] = []

        if (not all_years) and year is not None:
            where.append("t.year = ?")
            params.append(int(year))

        if query:
            where.append("(c.name LIKE ? OR t.name LIKE ? OR t.description LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q, q])

        where_sql = "WHERE " + " AND ".join(where) if where else ""

        sql = f"""
            SELECT
                t.id,
                t.tx_date      AS tx_date,
                c.name         AS category_name,
                t.amount       AS amount,
                t.unit_price   AS unit_price,
                t.quantity     AS quantity,
                t.description  AS description,
                t.tx_type      AS tx_type,
                t.category_id  AS category_id,
                t.name         AS name,
                t.has_details AS has_details

            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            {where_sql}
            ORDER BY t.tx_date DESC, t.id DESC
            LIMIT ?
        """
        params.append(int(limit))

        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            rows = cur.execute(sql, tuple(params)).fetchall()
            return rows
        finally:
            conn.close()

    def _seed_bill_categories(self, cur: sqlite3.Cursor) -> None:
        """
        Számla jellegű kiadás kategóriák.
        FONTOS: csak akkor hívd, miután _ensure_category_columns() már lefutott,
        mert az hozza létre a categories.is_bill oszlopot.
        """
        bill_categories = [
            ("Internet (KalászNet)", "expense"),
            ("Telekom", "expense"),
            ("MVMNext – Villany", "expense"),
            ("MVMNext – Gáz", "expense"),
        ]

        for name, t in bill_categories:
            try:
                cur.execute(
                    "INSERT INTO categories (name, tx_type) VALUES (?, ?)",
                    (name, t),
                )
            except sqlite3.IntegrityError:
                cur.execute("UPDATE categories SET tx_type=? WHERE name=?", (t, name))

            # jelöljük számlának
            cur.execute("UPDATE categories SET is_bill=1 WHERE name=?", (name,))

    def update_transaction(
        self,
        txn_id: int,
        date_str: str,
        category_id: int,
        amount: float,
        description: str,
        tx_type: str | None = None,
        name: str | None = None,
    ) -> bool:
        """
        tx_type opcionális (ha nincs, marad a régi).
        """
        try:
            iso = _iso_date(date_str)
            y, m = _year_month_from_iso(iso)
            if amount < 0:
                raise ValueError("B modell: amount nem lehet negatív.")
            fields = [
                "tx_date = ?",
                "amount = ?",
                "category_id = ?",
                "description = ?",
                "year = ?",
                "month = ?",
            ]
            params: list[Any] = [
                iso,
                float(amount),
                int(category_id),
                description or "",
                y,
                m,
            ]

            if name is not None:
                fields.insert(0, "name = ?")
                params.insert(0, name or "")

            if tx_type is not None:
                fields.insert(1, "tx_type = ?")
                params.insert(1, _map_hu_to_type(tx_type))

            params.append(int(txn_id))

            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute(
                f"""
                UPDATE transactions
                SET {", ".join(fields)}
                WHERE id = ?
                """,
                tuple(params),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Hiba a frissítésnél: {e}")
            return False

    def delete_transaction(self, txn_id: int) -> bool:
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()

            # töröljük a részleteket is, hogy ne maradjon árva sor
            cur.execute(
                "DELETE FROM transaction_items WHERE transaction_id = ?", (int(txn_id),)
            )

            # töröljük a fő tranzakciót
            cur.execute("DELETE FROM transactions WHERE id = ?", (int(txn_id),))
            deleted = cur.rowcount

            conn.commit()
            return deleted > 0

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            print(f"Hiba a törlésnél: {e}")
            return False
        finally:
            conn.close()

    def add_bulk_transactions(self, transactions) -> bool:
        """
        transactions: list[tuple[date(str), category_id(int), amount(float), description(str), tx_type(optional)]]
        - amount mindig pozitív legyen; ha negatívat kapsz, abs()-szal mentjük, de 'expense'-re állítjuk
        """
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()

            for item in transactions:
                if len(item) == 4:
                    d, category_id, amount, description = item
                    tx_type = None
                else:
                    d, category_id, amount, description, tx_type = item

                iso = _iso_date(d)
                y, m = _year_month_from_iso(iso)

                amt = float(amount)
                desc = (description or "").strip()
                name = desc  # ha nincs külön "name", használjuk a leírást

                # tx_type meghatározás
                inferred_type = _map_hu_to_type(tx_type) if tx_type else None

                if amt < 0:
                    inferred_type = "expense"
                    amt = abs(amt)

                if inferred_type is None:
                    cat = cur.execute(
                        "SELECT tx_type FROM categories WHERE id = ?",
                        (int(category_id),),
                    ).fetchone()
                    inferred_type = str(cat["tx_type"]) if cat else "expense"

                cur.execute(
                    """
                    INSERT INTO transactions (tx_date, tx_type, amount, category_id, name, description, created_at, year, month)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        iso,
                        inferred_type,
                        float(amt),
                        int(category_id),
                        name,
                        desc,
                        _now_ts(),
                        y,
                        m,
                    ),
                )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Hiba a tömeges beszúrásnál: {e}")
            return False

    # ----------------------------
    # Settings
    # ----------------------------

    def get_setting(self, key: str):
        conn = self.get_db_connection()
        cur = conn.cursor()
        row = cur.execute(
            "SELECT value, last_updated FROM settings WHERE key = ?",
            (key,),
        ).fetchone()
        conn.close()
        if row:
            return row["value"], row["last_updated"]
        return None, None

    def set_setting(self, key: str, value: str) -> None:
        conn = self.get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO settings (key, value, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                last_updated = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        conn.commit()
        conn.close()

    def get_year_plans(self, year: int) -> dict[int, tuple[float, float, float]]:
        """
        month -> (planned_income, planned_expense, planned_fixed_expense)
        """
        out: dict[int, tuple[float, float, float]] = {
            m: (0.0, 0.0, 0.0) for m in range(1, 13)
        }
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            rows = cur.execute(
                """
                SELECT month, planned_income, planned_expense, planned_fixed_expense
                FROM plans
                WHERE year = ?
                """,
                (int(year),),
            ).fetchall()

            for r in rows:
                m = int(r["month"])
                out[m] = (
                    float(r["planned_income"] or 0.0),
                    float(r["planned_expense"] or 0.0),
                    float(r["planned_fixed_expense"] or 0.0),
                )
        finally:
            conn.close()
        return out

    def upsert_month_plan(
        self,
        year: int,
        month: int,
        *,
        planned_income: float | None = None,
        planned_expense: float | None = None,
        planned_fixed_expense: float | None = None,
    ) -> None:
        """
        Részleges frissítést is enged: ami None, azt a DB-ben meglévő értéken hagyja.
        """
        y = int(year)
        m = int(month)

        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT planned_income, planned_expense, planned_fixed_expense FROM plans WHERE year=? AND month=?",
                (y, m),
            ).fetchone()

            if row is None:
                pi = float(planned_income or 0.0)
                pe = float(planned_expense or 0.0)
                pf = float(planned_fixed_expense or 0.0)
                cur.execute(
                    """
                    INSERT INTO plans (year, month, planned_income, planned_expense, planned_fixed_expense, updated_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (y, m, pi, pe, pf),
                )
            else:
                pi = (
                    float(row["planned_income"] or 0.0)
                    if planned_income is None
                    else float(planned_income)
                )
                pe = (
                    float(row["planned_expense"] or 0.0)
                    if planned_expense is None
                    else float(planned_expense)
                )
                pf = (
                    float(row["planned_fixed_expense"] or 0.0)
                    if planned_fixed_expense is None
                    else float(planned_fixed_expense)
                )

                cur.execute(
                    """
                    UPDATE plans
                    SET planned_income=?, planned_expense=?, planned_fixed_expense=?, updated_at=datetime('now')
                    WHERE year=? AND month=?
                    """,
                    (pi, pe, pf, y, m),
                )

            conn.commit()
        finally:
            conn.close()

    def delete_transaction_items(self, tx_id: int) -> None:
        conn = self.get_db_connection()
        conn.execute(
            "DELETE FROM transaction_items WHERE transaction_id = ?", (int(tx_id),)
        )
        conn.commit()
        conn.close()

    def insert_transaction_item(self, item: dict) -> None:
        conn = self.get_db_connection()
        conn.execute(
            """
            INSERT INTO transaction_items
            (transaction_id, item_date, item_name, category_name, unit_price, quantity, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(item["transaction_id"]),
                _iso_date(item["item_date"]),
                (item["item_name"] or "").strip(),
                item.get("category_name"),
                float(item["unit_price"])
                if item.get("unit_price") is not None
                else None,
                float(item["quantity"]) if item.get("quantity") is not None else None,
                float(item["amount"]),
            ),
        )
        conn.commit()
        conn.close()

    def finalize_transaction_from_items(self, tx_id: int) -> None:
        conn = self.get_db_connection()
        cur = conn.cursor()

        # egységes-e az egységár?
        row = cur.execute(
            """
            SELECT COUNT(DISTINCT ROUND(unit_price, 4)) AS n
            FROM transaction_items
            WHERE transaction_id = ? AND unit_price IS NOT NULL
            """,
            (int(tx_id),),
        ).fetchone()
        distinct_prices = int(row[0] or 0) if row else 0
        set_unit_price = distinct_prices <= 1

        if set_unit_price:
            cur.execute(
                """
                UPDATE transactions
                SET
                amount = (
                    SELECT COALESCE(ROUND(SUM(amount), 2), 0)
                    FROM transaction_items
                    WHERE transaction_id = ?
                ),
                quantity = (
                    SELECT COALESCE(ROUND(SUM(COALESCE(quantity, 1)), 2), 0)
                    FROM transaction_items
                    WHERE transaction_id = ?
                ),
                unit_price = (
                    SELECT
                    CASE
                        WHEN COALESCE(SUM(COALESCE(quantity, 1)), 0) > 0
                        THEN ROUND(SUM(amount) / SUM(COALESCE(quantity, 1)), 4)
                        ELSE NULL
                    END
                    FROM transaction_items
                    WHERE transaction_id = ?
                ),
                has_details = 1
                WHERE id = ?;
                """,
                (int(tx_id), int(tx_id), int(tx_id), int(tx_id)),
            )
        else:
            cur.execute(
                """
                UPDATE transactions
                SET
                amount = (
                    SELECT COALESCE(ROUND(SUM(amount), 2), 0)
                    FROM transaction_items
                    WHERE transaction_id = ?
                ),
                quantity = (
                    SELECT COALESCE(ROUND(SUM(COALESCE(quantity, 1)), 2), 0)
                    FROM transaction_items
                    WHERE transaction_id = ?
                ),
                unit_price = NULL,
                has_details = 1
                WHERE id = ?;
                """,
                (int(tx_id), int(tx_id), int(tx_id)),
            )

        conn.commit()
        conn.close()

    # ----------------------------
    # Reports / Aggregations (B modell)
    # ----------------------------

    def get_monthly_summary(self, year: int | None = None):
        conn = self.get_db_connection()
        cur = conn.cursor()

        where = ""
        params: tuple[Any, ...] = ()
        if year is not None:
            where = "WHERE year = ?"
            params = (int(year),)

        rows = cur.execute(
            f"""
            SELECT
                printf('%04d-%02d', year, month) AS month,
                SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END) AS income,
                SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END) AS expense
            FROM transactions
            {where}
            GROUP BY year, month
            ORDER BY year DESC, month DESC
            """,
            params,
        ).fetchall()

        conn.close()
        return [
            (r["month"], float(r["income"] or 0), float(r["expense"] or 0))
            for r in rows
        ]

    def get_available_years(self):
        conn = self.get_db_connection()
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT DISTINCT year AS y
            FROM transactions
            ORDER BY y DESC
            """
        ).fetchall()
        conn.close()
        return [int(r["y"]) for r in rows if r["y"] is not None]

    def get_annual_totals(self, year: int | None = None):
        conn = self.get_db_connection()
        cur = conn.cursor()

        where = ""
        params: tuple[Any, ...] = ()
        if year is not None:
            where = "WHERE year = ?"
            params = (int(year),)

        row = cur.execute(
            f"""
            SELECT
                COALESCE(SUM(CASE WHEN tx_type='income' THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN tx_type='expense' THEN amount ELSE 0 END), 0) AS expense
            FROM transactions
            {where}
            """,
            params,
        ).fetchone()
        conn.close()

        income = float(row["income"] or 0)
        expense = float(row["expense"] or 0)
        return income, expense

    def get_transactions_by_category_name(
        self, category_name: str, year: int | None = None
    ):
        conn = self.get_db_connection()
        cur = conn.cursor()

        where_year = ""
        params: list[Any] = [category_name]
        if year is not None:
            where_year = "AND t.year = ?"
            params.append(int(year))

        rows = cur.execute(
            f"""
            SELECT t.tx_date AS date, t.amount, t.description, t.tx_type AS type
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE c.name = ?
            {where_year}
            ORDER BY t.tx_date DESC, t.id DESC
            """,
            tuple(params),
        ).fetchall()

        conn.close()
        return rows

    def get_all_transactions_for_export(self):
        """
        Exporthoz:
        columns: list[str]
        rows: sqlite3.Row list
        """
        conn = self.get_db_connection()
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT t.id, t.tx_date AS date, c.name as category_name, t.tx_type AS transaction_type, t.amount, t.description
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            ORDER BY t.tx_date DESC, t.id DESC
            """
        ).fetchall()
        conn.close()

        columns = [
            "id",
            "date",
            "category_name",
            "transaction_type",
            "amount",
            "description",
        ]
        return columns, rows

    def get_transaction_by_id(self, txn_id: int) -> sqlite3.Row | None:
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    t.id,
                    t.tx_date   AS tx_date,
                    t.amount    AS amount,
                    t.description AS description,
                    t.tx_type   AS tx_type,
                    t.category_id AS category_id,
                    t.name      AS name
                FROM transactions t
                WHERE t.id = ?
                """,
                (int(txn_id),),
            )
            return cur.fetchone()
        finally:
            conn.close()

    # -------- Kezdőoldal / Dashboard ---------

    def get_monthly_income_expense(self, year: int) -> dict[int, tuple[float, float]]:
        """
        Visszaadja az adott évre a havi (bevétel, kiadás) összegeket.
        Kulcs: 1..12 hónap
        Érték: (income_sum, expense_sum)
        """
        out: dict[int, list[float]] = {m: [0.0, 0.0] for m in range(1, 13)}

        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    month,
                    tx_type,
                    SUM(amount) AS total
                FROM transactions
                WHERE year = ?
                GROUP BY month, tx_type
                """,
                (int(year),),
            )

            for row in cur.fetchall():
                m = int(row["month"])
                tx_type = row["tx_type"]
                total = float(row["total"] or 0.0)

                if tx_type == "income":
                    out[m][0] = total
                elif tx_type == "expense":
                    out[m][1] = total
        finally:
            conn.close()

        return {m: (vals[0], vals[1]) for m, vals in out.items()}

    def get_monthly_income_expense_bills(
        self, year: int
    ) -> dict[int, tuple[float, float, float]]:
        """
        month -> (income, expense_core, bills)
        expense_core = minden kiadás, ami NEM számla
        bills        = számlának jelölt kategóriák kiadásai
        """
        out = {m: [0.0, 0.0, 0.0] for m in range(1, 13)}

        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    t.month AS month,
                    t.tx_type AS tx_type,
                    COALESCE(c.is_bill, 0) AS is_bill,
                    SUM(t.amount) AS total
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.year = ?
                GROUP BY t.month, t.tx_type, COALESCE(c.is_bill, 0)
                """,
                (int(year),),
            )

            for r in cur.fetchall():
                m = int(r["month"])
                tx_type = str(r["tx_type"])
                is_bill = int(r["is_bill"] or 0)
                total = float(r["total"] or 0.0)

                if tx_type == "income":
                    out[m][0] += total
                else:
                    if is_bill == 1:
                        out[m][2] += total
                    else:
                        out[m][1] += total
        finally:
            conn.close()

        return {m: (v[0], v[1], v[2]) for m, v in out.items()}

    def _ensure_details_schema(self, cur: sqlite3.Cursor) -> None:
        # 1) transactions.has_details (idempotens)
        if not self._column_exists(cur, "transactions", "has_details"):
            cur.execute(
                "ALTER TABLE transactions ADD COLUMN has_details INTEGER NOT NULL DEFAULT 0"
            )

        # 2) transaction_items tábla (idempotens)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transaction_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                item_date TEXT NOT NULL,            -- 'YYYY-MM-DD'
                item_name TEXT NOT NULL,
                category_name TEXT,                 -- egyszerűsítés: itt most szöveg
                unit_price REAL,
                quantity REAL,
                amount REAL NOT NULL CHECK (amount >= 0),
                FOREIGN KEY(transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_items_txid ON transaction_items(transaction_id)"
        )

    def _ensure_category_columns(self, cur: sqlite3.Cursor) -> None:
        cols = [
            r["name"] for r in cur.execute("PRAGMA table_info(categories)").fetchall()
        ]
        if "is_bill" not in cols:
            cur.execute(
                "ALTER TABLE categories ADD COLUMN is_bill INTEGER NOT NULL DEFAULT 0"
            )

    def get_transaction_items(self, txn_id: int) -> list[sqlite3.Row]:
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            return cur.execute(
                """
                SELECT
                    id,
                    item_date,
                    item_name,
                    category_name,
                    unit_price,
                    quantity,
                    amount
                FROM transaction_items
                WHERE transaction_id = ?
                ORDER BY id ASC
                """,
                (int(txn_id),),
            ).fetchall()
        finally:
            conn.close()

    def set_has_details(self, txn_id: int, value: bool) -> None:
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE transactions SET has_details = ? WHERE id = ?",
                (1 if value else 0, int(txn_id)),
            )
            conn.commit()
        finally:
            conn.close()

    def add_transaction_item(
        self,
        txn_id: int,
        *,
        item_date: str,
        item_name: str,
        category_name: str | None = None,
        unit_price: float | None = None,
        quantity: float | None = None,
        amount: float,
    ) -> None:
        if amount < 0:
            raise ValueError(
                "B modell: amount nem lehet negatív (transaction_items.amount)."
            )

        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO transaction_items
                    (transaction_id, item_date, item_name, category_name, unit_price, quantity, amount)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(txn_id),
                    item_date,
                    item_name,
                    category_name,
                    unit_price,
                    quantity,
                    float(amount),
                ),
            )
            # has_details maradhat, de a sync úgyis beállítja
            cur.execute(
                "UPDATE transactions SET has_details = 1 WHERE id = ?", (int(txn_id),)
            )
            conn.commit()
        finally:
            conn.close()

        # >>> KRITIKUS: a fő tranzakció mezők szinkronja a tételekből <<<
        self._sync_transaction_amount_from_items(int(txn_id))

    def _ensure_transaction_columns(self, cur: sqlite3.Cursor) -> None:
        cols = [
            r["name"] for r in cur.execute("PRAGMA table_info(transactions)").fetchall()
        ]
        if "unit_price" not in cols:
            cur.execute("ALTER TABLE transactions ADD COLUMN unit_price REAL")
        if "quantity" not in cols:
            cur.execute("ALTER TABLE transactions ADD COLUMN quantity REAL")

    # --- Részletek ablak : ---

    def get_transaction_header(self, txn_id: int):
        """
        Egy tranzakció "header" adatai a Részletek dialoghoz.

        Visszaad:
            - tx_date, name, amount, tx_type, description
            - category_name (JOIN categories)
        """

        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            return cur.execute(
                """
                SELECT
                    t.id,
                    t.tx_date AS tx_date,
                    t.amount AS amount,
                    t.tx_type AS tx_type,
                    t.description AS description,
                    t.name AS name,
                    t.category_id AS category_id,
                    c.name AS category_name
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.id = ?
                """,
                (int(txn_id),),
            ).fetchone()
        finally:
            conn.close()

    def get_transaction_item(self, item_id: int) -> sqlite3.Row | None:
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            return cur.execute(
                """
                SELECT
                    id,
                    transaction_id,
                    item_date,
                    item_name,
                    category_name,
                    unit_price,
                    quantity,
                    amount
                FROM transaction_items
                WHERE id = ?
                """,
                (int(item_id),),
            ).fetchone()
        finally:
            conn.close()

    def _sync_transaction_amount_from_items(self, txn_id: int) -> None:
        """
        Részletezés esetén:
            - transactions.amount = tételek SUM(amount)
            - transactions.quantity = SUM(COALESCE(quantity,1))
            - transactions.unit_price:
            * ha egységes (<=1 féle, nem NULL) -> beírjuk
            * ha vegyes -> NULL
        """
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()

            row = cur.execute(
                "SELECT COALESCE(ROUND(SUM(amount), 2), 0) AS total "
                "FROM transaction_items WHERE transaction_id = ?",
                (int(txn_id),),
            ).fetchone()
            total = float(row["total"] or 0.0)

            row = cur.execute(
                "SELECT COALESCE(SUM(COALESCE(quantity, 1)), 0) AS qty "
                "FROM transaction_items WHERE transaction_id = ?",
                (int(txn_id),),
            ).fetchone()
            qty = float(row["qty"] or 0.0)
            if qty <= 0:
                qty = 1.0

            row = cur.execute(
                "SELECT COUNT(DISTINCT ROUND(unit_price, 4)) AS n "
                "FROM transaction_items "
                "WHERE transaction_id = ? AND unit_price IS NOT NULL",
                (int(txn_id),),
            ).fetchone()
            n = int(row["n"] or 0)

            unit_price = None
            if n <= 1:
                row = cur.execute(
                    "SELECT MAX(unit_price) AS up "
                    "FROM transaction_items WHERE transaction_id = ?",
                    (int(txn_id),),
                ).fetchone()
                up = row["up"]
                unit_price = float(up) if up is not None else None

            cur.execute(
                "UPDATE transactions "
                "SET amount = ?, has_details = 1, quantity = ?, unit_price = ? "
                "WHERE id = ?",
                (total, qty, unit_price, int(txn_id)),
            )
            conn.commit()
        finally:
            conn.close()

    def update_transaction_item(
        self,
        item_id: int,
        *,
        item_date: str,
        item_name: str,
        category_name: str | None,
        unit_price: float | None,
        quantity: float | None,
        amount: float,
    ) -> None:
        if amount < 0:
            raise ValueError(
                "B modell: amount nem lehet negatív (transaction_items.amount)."
            )

        conn = self.get_db_connection()
        try:
            cur = conn.cursor()

            # kell a parent txn_id a szinkronhoz
            parent = cur.execute(
                "SELECT transaction_id FROM transaction_items WHERE id = ?",
                (int(item_id),),
            ).fetchone()
            if not parent:
                raise ValueError(f"transaction_items sor nem található: id={item_id}")
            txn_id = int(parent["transaction_id"])

            cur.execute(
                """
                UPDATE transaction_items
                SET
                    item_date = ?,
                    item_name = ?,
                    category_name = ?,
                    unit_price = ?,
                    quantity = ?,
                    amount = ?
                WHERE id = ?
                """,
                (
                    str(item_date),
                    str(item_name),
                    category_name,
                    unit_price,
                    quantity,
                    float(amount),
                    int(item_id),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        # fő összeg szinkron
        self._sync_transaction_amount_from_items(txn_id)

    def get_dashboard_balances(self) -> tuple[float, float, float, float, float]:
        """
        Visszaadja:
        cash_balance, bank_balance, securities_value, metal_value, total_balance
        """
        with self.get_db_connection() as conn:
            cur = conn.cursor()
            self._ensure_account_valuations(cur)
            self._ensure_payment_source_column(cur)

            # 1) Kézpénz egyenleg
            cur.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN tx_type='income' THEN amount ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN tx_type='expense' THEN amount ELSE 0 END), 0)
                FROM transactions
                WHERE payment_source = 'cash'
            """)
            cash_balance = float(cur.fetchone()[0] or 0.0)

            # 2) Folyószámla egyenleg
            cur.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN tx_type='income' THEN amount ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN tx_type='expense' THEN amount ELSE 0 END), 0)
                FROM transactions
                WHERE payment_source = 'bank'
            """)
            bank_balance = float(cur.fetchone()[0] or 0.0)

            # 3) Értékpapírszámla összérték (legutolsó érték)
            cur.execute("""
                SELECT value
                FROM account_valuations
                WHERE account_type='securities'
                ORDER BY date DESC, id DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            securities = float(row["value"]) if row else 0.0

            # 4) Nemesfém egyenleg (legutolsó érték)
            cur.execute("""
                SELECT value
                FROM account_valuations
                WHERE account_type='metals'
                ORDER BY date DESC, id DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            metals = float(row["value"]) if row else 0.0

            total = cash_balance + bank_balance + securities + metals

            return cash_balance, bank_balance, securities, metals, total

    def ensure_account_valuations(self) -> None:
        with self.get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS account_valuations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,          -- YYYY-MM-DD
                    account_type TEXT NOT NULL,  -- 'securities' | 'metals'
                    value REAL NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_av_type_date
                ON account_valuations(account_type, date);
            """)

    def _ensure_account_valuations(self, cur) -> None:
        """
        initialize_db() cursorral dolgozik, ezért kell egy cursoros verzió is.
        """
        cur.execute("""
            CREATE TABLE IF NOT EXISTS account_valuations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,          -- YYYY-MM-DD
                account_type TEXT NOT NULL,  -- 'securities' | 'metals'
                value REAL NOT NULL
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_av_type_date
            ON account_valuations(account_type, date);
        """)

    def _ensure_bills_schema(self, cur) -> None:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL CHECK (kind IN ('monthly', 'periodic')),
                is_active INTEGER NOT NULL DEFAULT 1,
                notes TEXT
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS bill_monthly_amounts (
                bill_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
                amount REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (bill_id, year, month),
                FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS bill_periodic_amounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL,
                start TEXT NOT NULL,   -- YYYY-MM-DD
                end   TEXT NOT NULL,   -- YYYY-MM-DD
                amount REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
            );
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_kind ON bills(kind);")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_bill_monthly_year ON bill_monthly_amounts(year);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_bill_periodic_bill ON bill_periodic_amounts(bill_id);"
        )

    def ensure_bills_schema(self) -> None:
        with self.get_db_connection() as conn:
            cur = conn.cursor()
            self._ensure_bills_schema(cur)
            conn.commit()

    def get_latest_account_valuation(self, account_type: str):
        """Legutolsó (date DESC, id DESC) érték egy account_type-ra.
        Visszatér: None vagy {"date": "...", "value": ...}
        """
        if account_type not in ("securities", "metals"):
            raise ValueError(f"Invalid account_type: {account_type}")

        # biztosítsuk a táblát/indexet
        self.ensure_account_valuations()

        with self.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT date, value
                FROM account_valuations
                WHERE account_type = ?
                ORDER BY date DESC, id DESC
                LIMIT 1
                """,
                (account_type,),
            )
            row = cur.fetchone()

        if not row:
            return None
        return {"date": row[0], "value": row[1]}

    def _ensure_account_valuations(self, cur: sqlite3.Cursor) -> None:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS account_valuations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,          -- YYYY-MM-DD
                account_type TEXT NOT NULL,  -- 'securities' | 'metals'
                value REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_account_valuations_type_date
            ON account_valuations(account_type, date)
        """)

    def list_accounts_history(self, limit: int = 30):
        """
        Közös előzménylista:
            - cash a wallet_balances táblából
            - securities / metals az account_valuations táblából

        Visszatér:
            [{"date": "...", "account_type": "cash|securities|metals", "value": ...}, ...]
        """

        self.ensure_wallet_balances()
        self.ensure_account_valuations()

        with self.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT date, wallet_type AS account_type, value, id
                FROM wallet_balances

                UNION ALL

                SELECT date, account_type, value, id
                FROM account_valuations

                ORDER BY date DESC, id DESC
                LIMIT ?
                """,
                (int(limit),),
            )
            rows = cur.fetchall()

        return [
            {
                "date": r["date"],
                "account_type": r["account_type"],
                "value": r["value"],
                "id": r["id"],
            }
            for r in rows
        ]

    def _ensure_payment_source_column(self, cur) -> None:
        cur.execute("PRAGMA table_info(transactions)")
        cols = [row[1] for row in cur.fetchall()]
        if "payment_source" not in cols:
            cur.execute("""
                ALTER TABLE transactions
                ADD COLUMN payment_source TEXT NOT NULL DEFAULT 'bank'
            """)

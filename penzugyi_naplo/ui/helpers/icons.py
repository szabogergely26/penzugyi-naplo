"""
ui/helpers/icons.py

Egyszerű szimbólum-alapú ikon helper a Pénzügyi Napló UI-hoz.

Cél:
- első körben ne kelljen SVG / ICO fájlokat kezelni
- visszatérő tranzakciókhoz és számlákhoz könnyen olvasható szimbólumot adni
- később egy helyen lehessen bővíteni vagy akár rendes ikonokra cserélni
"""

from __future__ import annotations

DEFAULT_INCOME_SYMBOL = "🟩"
DEFAULT_EXPENSE_SYMBOL = "🟥"
DEFAULT_SAVING_SYMBOL = "🟦"
DEFAULT_FALLBACK_SYMBOL = "•"


def _normalize(text: str | None) -> str:
    """
    Egyszerű normalizálás kereséshez.
    """
    if not text:
        return ""
    return text.strip().lower()


def get_transaction_symbol(
    name: str | None = None,
    category_name: str | None = None,
    tx_type: str | None = None,
    description: str | None = None,
) -> str:
    """
    Szimbólum visszaadása tranzakcióhoz.

    A keresés több mezőben próbál egyezést találni:
    - name
    - category_name
    - description

    tx_type:
    - "income"
    - "expense"
    - "saving" (ha később kellene)
    """

    text = " | ".join(
        part for part in [
            _normalize(name),
            _normalize(category_name),
            _normalize(description),
        ]
        if part
    )

    # ---- Számlák / szolgáltatók ----
    if "villany" in text or "mvmnext - villany" in text or "mvm villany" in text:
        return "⚡"

    if "gáz" in text or "gaz" in text or "mvmnext - gáz" in text or "mvm gáz" in text:
        return "🔥"

    if "telekom" in text:
        return "📞"

    if "kalásznet" in text or "kalasznet" in text or "internet" in text:
        return "🌐"

    # ---- Bevételek ----
    if "munkabér" in text or "munkaber" in text or "fizetés" in text or "fizetes" in text:
        return "💼"

    if "családi pótlék" in text or "csaladi potlek" in text or "családi" in text or "csaladi" in text:
        return "👨‍👩‍👧"

    if "rehabilitáció" in text or "rehabilitacio" in text or "rehab" in text:
        return "🏥"

    # ---- Kiadások ----
    if "vásárlás" in text or "vasarlas" in text:
        return "🛒"

    # ---- Fallback típus alapján ----
    tx_type_norm = _normalize(tx_type)

    if tx_type_norm == "income":
        return DEFAULT_INCOME_SYMBOL

    if tx_type_norm == "expense":
        return DEFAULT_EXPENSE_SYMBOL

    if tx_type_norm == "saving":
        return DEFAULT_SAVING_SYMBOL

    return DEFAULT_FALLBACK_SYMBOL


def format_transaction_title(
    name: str | None = None,
    category_name: str | None = None,
    tx_type: str | None = None,
    description: str | None = None,
) -> str:
    """
    UI-barát cím előállítása szimbólummal.

    Elsőként a name mezőt használja, ha nincs, akkor a kategórianevet.
    """
    base_text = (name or category_name or "Ismeretlen tétel").strip()
    symbol = get_transaction_symbol(
        name=name,
        category_name=category_name,
        tx_type=tx_type,
        description=description,
    )
    return f"{symbol} {base_text}"


def is_bill_like_transaction(
    name: str | None = None,
    category_name: str | None = None,
    description: str | None = None,
) -> bool:
    """
    Heurisztika: számla jellegű-e a tranzakció neve/kategóriája.
    """
    text = " | ".join(
        part for part in [
            _normalize(name),
            _normalize(category_name),
            _normalize(description),
        ]
        if part
    )

    bill_keywords = (
        "villany",
        "gáz",
        "gaz",
        "telekom",
        "kalásznet",
        "kalasznet",
        "internet",
        "számla",
        "szamla",
        "számlabefizetés",
        "szamlabefizetes",
    )

    return any(keyword in text for keyword in bill_keywords)


def get_display_name_with_bill_tag(
    name: str | None = None,
    category_name: str | None = None,
    description: str | None = None,
    is_bill: bool = False,
) -> str:
    """
    Megjelenítési név számlabefizetés jelöléssel.

    Példa:
    '⚡ MVMNext - Villany (számlabefizetés)'
    """
    base_text = (name or category_name or "Ismeretlen tétel").strip()

    symbol = get_transaction_symbol(
        name=name,
        category_name=category_name,
        description=description,
        tx_type="expense",
    )

    if is_bill or is_bill_like_transaction(
        name=name,
        category_name=category_name,
        description=description,
    ):
        return f"{symbol} {base_text} (számlabefizetés)"

    return f"{symbol} {base_text}"
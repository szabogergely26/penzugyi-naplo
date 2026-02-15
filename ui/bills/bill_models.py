# - ui/bills/bill_models.py
# ---------------------------------------------------

"""
Számlák UI megjelenítéséhez használt adatmodellek
(ui/bills/bill_models.py).

Immutable (frozen) dataclass-ek, kizárólag a UI réteg számára.
Fő modell: BillCardModel (kártya megjelenítés: monthly | periodic).

Nem tartalmaz DB/üzleti logikát, csak struktúrált adatot a rendereléshez.

"""


# --- Importok ---

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# --- Importok vége


BillKind = Literal["monthly", "periodic"]


@dataclass(frozen=True)
class MonthlyAmount:
    month: int  # 1..12
    amount: float


@dataclass(frozen=True)
class PeriodicAmount:
    start: str  # "YYYY-MM-DD"
    end: str  # "YYYY-MM-DD"
    amount: float


@dataclass(frozen=True)
class BillCardModel:
    id: int
    name: str
    kind: BillKind
    is_active: bool = True

    # töltet (a kind dönti el, melyiket használjuk)
    monthly: list[MonthlyAmount] | None = None
    periodic: list[PeriodicAmount] | None = None

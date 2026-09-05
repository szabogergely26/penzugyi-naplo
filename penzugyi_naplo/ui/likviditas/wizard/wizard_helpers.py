# penzugyi_naplo/ui/likviditas/wizard/wizard_helpers.py
# --------------------------------------------------------------
# Likviditás / Tranzakciórögzítő varázsló — segédfüggvények
# --------------------------------------------------------------

"""
A tranzakció-varázsló (wizard_transaction.py) által használt, oldal-független
segédfüggvények:
- részletek-sor parszolás (parse_details_line)
- bill provider logika (bill_requires_period)
- egységes kétoszlopos wizard-oldal layout builder (create_transaction_wizard_page_layout)

Ez a fájl szándékosan nem tartalmaz semmilyen QWizardPage leszármazottat,
csak tiszta segédeszközöket, amiket több oldal is felhasznál.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
    QWizardPage,
)

from penzugyi_naplo.core.utils import parse_amount

# ---------------------------------------------------------------------------
# Részletek sor parszolás
#
# Támogatott formátumok (soronként):
#   1) tételnév;egységár*db      pl.: rágó;349*3
#   2) tételnév;egységár         pl.: kávé;450        (db=1)
#
# Megjegyzés: a régi (tételnév;összeg) bevitel továbbra is működik,
#             mert db=1 esetén az egységár == összeg.
# ---------------------------------------------------------------------------


_MULT_RE = re.compile(r"\s*[xX×\*]\s*")


def parse_details_line(line: str, *, loc: QLocale) -> tuple[str, float, float, float]:
    """
    Egy details sor parszolása.

    Returns: (item_name, unit_price, quantity, amount)
    Raises: ValueError, ha nem parszolható.
    """
    raw = (line or "").strip()
    if not raw or ";" not in raw:
        raise ValueError("Hiányzó ';' vagy üres sor")

    item_name, rhs = raw.split(";", 1)
    item_name = item_name.strip()
    rhs = rhs.strip()
    if not item_name or not rhs:
        raise ValueError("Hiányzó tételnév vagy érték")

    gs = loc.groupSeparator()
    dp = loc.decimalPoint()

    # Egységár * db (x, ×, * mind jó)
    if _MULT_RE.search(rhs):
        parts = _MULT_RE.split(rhs, maxsplit=1)
        if len(parts) != 2:
            raise ValueError("Rossz '*'/x szintaxis")
        unit_str, qty_str = parts[0].strip(), parts[1].strip()
        if not unit_str or not qty_str:
            raise ValueError("Hiányzó egységár vagy darabszám")

        unit_price = abs(parse_amount(unit_str, group_sep=gs, decimal_point=dp))
        quantity = abs(parse_amount(qty_str, group_sep=gs, decimal_point=dp))
        if quantity == 0:
            raise ValueError("Db nem lehet 0")
        amount = float(unit_price) * float(quantity)
        return (item_name, float(unit_price), float(quantity), float(amount))

    # Egyszerű: tételnév;egységár  (db=1)
    unit_price = abs(parse_amount(rhs, group_sep=gs, decimal_point=dp))
    quantity = 1.0
    amount = float(unit_price)
    return (item_name, float(unit_price), float(quantity), float(amount))


def bill_requires_period(provider: str) -> bool:
    """Csak az MVMNext igényel időszak kezdete/vége mezőket."""
    return (provider or "").strip() == "MVMNext"


def create_transaction_wizard_page_layout(
    page: QWizardPage,
    icon_text: str,
    title: str,
    subtitle: str,
) -> tuple[QVBoxLayout, QLabel, QLabel]:
    """
    Egységes kétoszlopos Likviditás-varázsló oldal.

    Bal oldal:
    - kép / ikon / illusztráció helye

    Jobb oldal:
    - az adott oldal tényleges tartalma
    """

    root_layout = QHBoxLayout(page)
    root_layout.setContentsMargins(18, 18, 18, 18)
    root_layout.setSpacing(20)

    image_panel = QFrame()
    image_panel.setObjectName("transactionWizardImagePanel")
    image_panel.setMinimumWidth(230)
    image_panel.setMaximumWidth(280)

    image_layout = QVBoxLayout(image_panel)
    image_layout.setContentsMargins(20, 20, 20, 20)
    image_layout.setSpacing(12)

    icon_label = QLabel(icon_text)
    icon_label.setObjectName("transactionWizardImagePlaceholder")
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    title_label = QLabel(title)
    title_label.setObjectName("transactionWizardImageTitle")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setWordWrap(True)

    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("transactionWizardImageSubtitle")
    subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    subtitle_label.setWordWrap(True)

    image_layout.addStretch(1)
    image_layout.addWidget(icon_label)
    image_layout.addWidget(title_label)
    image_layout.addWidget(subtitle_label)
    image_layout.addStretch(1)

    content_panel = QWidget()
    content_panel.setObjectName("transactionWizardContentPanel")

    content_layout = QVBoxLayout(content_panel)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(12)

    root_layout.addWidget(image_panel)
    root_layout.addWidget(content_panel, 1)

    return content_layout, title_label, subtitle_label
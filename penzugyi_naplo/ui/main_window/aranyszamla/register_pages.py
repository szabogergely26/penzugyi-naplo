# penzugyi_naplo/ui/main_window/aranyszamla/register_pages.py
# ----------------------------------------------------------

"""
Aranyszámla modul oldalainak regisztrálása.
"""

from __future__ import annotations

from penzugyi_naplo.ui.main_window.aranyszamla.module_page import (
    AranyszamlaModulePage,
)


def register_aranyszamla_pages(window) -> None:
    """
    Regisztrálja az Aranyszámla modult a MainWindow központi stackjébe.
    """

    aranyszamla_page = AranyszamlaModulePage(
    db_path=window.db.db_name,
    parent=window.page_stack,
)

    window.add_page("aranyszamla_home", aranyszamla_page)
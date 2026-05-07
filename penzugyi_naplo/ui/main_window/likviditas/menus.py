# penzugyi_naplo/ui/main_window/likviditas/menus.py
"""
Likviditás nézethez tartozó menü- és ribbonépítés.

Felelősség:
    - A MainWindow által létrehozott QAction objektumok elhelyezése.
    - Klasszikus menüsor építése.
    - RibbonBar építése.
    - A ribbon "Fájl" lenyíló menüjének összeállítása.

Fontos:
    - Az actionök létrehozása továbbra is a MainWindow feladata.
    - A callback metódusok továbbra is a MainWindow-ban maradnak.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMenu

from penzugyi_naplo.ui.widgets.ribbon_bar import RibbonBar


def build_likviditas_menubar(window) -> None:
    """Klasszikus menüsor felépítése a Likviditás nézethez."""
    mb = window.menuBar()
    mb.clear()

    m_file = mb.addMenu("Fájl")
    m_file.addAction(window.act_new_tx)
    m_file.addSeparator()
    m_file.addAction(window.act_exit)

    m_data = mb.addMenu("Adatok")
    m_data.addAction(window.act_backup_db)
    m_data.addAction(window.act_restore_db)
    m_data.addSeparator()
    m_data.addAction(window.act_import)
    m_data.addAction(window.act_export)
    m_data.addSeparator()
    m_data.addAction(window.act_reset_db)

    m_view = mb.addMenu("Nézet")
    m_view.addAction(window.act_toolbar_menubar)
    m_view.addAction(window.act_toolbar_ribbon)

    m_help = mb.addMenu("Súgó")
    m_help.addAction(window.act_about)
    m_help.addAction(window.act_version_info)
    m_help.addSeparator()
    m_help.addAction(window.act_log_viewer)
    m_help.addAction(window.act_version_history)


def build_likviditas_ribbon(window) -> None:
    """Ribbon felépítése a Likviditás nézethez."""
    # FONTOS:
    # A ribbon "Fájl" gombja nem ribbon-tab, hanem egy külön beépített gomb
    # (window.ribbon.file_btn). Ezért ide nem add_tab()/add_action_button() kell,
    # hanem egy külön QMenu-t építünk, és azt adjuk hozzá a file_btn-höz.
    window.ribbon = RibbonBar(window)

    tab_home = window.ribbon.add_tab("Fő")
    window.ribbon.add_action_button(tab_home, window.act_new_tx)

    tab_data = window.ribbon.add_tab("Adatok")

    window.ribbon.add_action_button(tab_data, window.act_backup_db)
    window.ribbon.add_action_button(tab_data, window.act_restore_db)

    window.ribbon.add_separator(tab_data, spacing=12)

    window.ribbon.add_action_button(tab_data, window.act_import)
    window.ribbon.add_action_button(tab_data, window.act_export)

    # Vizuális elválasztás.
    window.ribbon.add_separator(tab_data, spacing=18)

    btn_delete = window.ribbon.add_action_button(tab_data, window.act_reset_db)
    btn_delete.setObjectName("dangerButton")
    btn_delete.style().unpolish(btn_delete)
    btn_delete.style().polish(btn_delete)
    btn_delete.update()

    tab_app = window.ribbon.add_tab("Nézet")

    tab_help = window.ribbon.add_tab("Súgó")
    window.ribbon.add_action_button(tab_help, window.act_about)
    window.ribbon.add_action_button(tab_help, window.act_version_info)
    window.ribbon.add_action_button(tab_help, window.act_version_history)
    window.ribbon.add_action_button(tab_help, window.act_log_viewer)

    window.ribbon.add_action_button(tab_app, window.act_toolbar_menubar)
    window.ribbon.add_action_button(tab_app, window.act_toolbar_ribbon)

    # Fájl-hoz létrehozza a lenyíló menüt.
    file_menu = build_likviditas_file_menu_for_ribbon(window)
    window.ribbon.file_btn.setMenu(file_menu)


def build_likviditas_file_menu_for_ribbon(window) -> QMenu:
    """A ribbon Fájl gombjához tartozó lenyíló menü."""
    menu = QMenu("Fájl", window)

    menu.addAction(window.act_new_tx)
    menu.addSeparator()
    menu.addAction(window.act_exit)

    return menu
"""
QAction ikonok központi beállítása.

Itt tartjuk egy helyen, hogy melyik alkalmazásművelet milyen
rendszer-téma ikont kapjon.
"""

from __future__ import annotations

from PySide6.QtGui import QIcon


ACTION_ICON_NAMES: dict[str, str] = {
    "act_new_tx": "list-add",
    "act_backup_db": "document-save",
    "act_restore_db": "document-open",
    "act_import": "document-import",
    "act_export": "document-export",
    "act_reset_db": "edit-delete",
    "act_settings": "preferences-system",
    "act_exit": "application-exit",
    "act_toolbar_menubar": "view-list-text",
    "act_toolbar_ribbon": "view-grid-symbolic",
    "act_about": "help-about",
    "act_version_info": "dialog-information",
    "act_log_viewer": "text-x-log",
    "act_version_history": "view-history",
}


def apply_action_icons(window) -> None:
    """
    Ikonok beállítása a MainWindow-ban létrehozott QAction objektumokra.

    Ha egy action nem létezik az adott modulban, kihagyjuk.
    """
    for action_name, icon_name in ACTION_ICON_NAMES.items():
        action = getattr(window, action_name, None)

        if action is None:
            continue

        action.setIcon(QIcon.fromTheme(icon_name))
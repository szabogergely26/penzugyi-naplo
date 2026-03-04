# - stylesheet.py
# ------------------

"""
Alkalmazás szintű Qt stíluskezelés
(penzugyi_naplo/ui/stylesheet.py).

Ez a modul tartalmazza a globális és komponens-szintű QSS definíciókat.

Fő elemek:
    - apply_modern_stylesheet():
        Teljes alkalmazásra vonatkozó alap stílus beállítása
        (QApplication / QMainWindow.setStyleSheet).

    - NAV_QSS:
        Navigációs sáv (NavBar) komponenshez tartozó kiegészítő stílus.
        objectName / property alapú szelektorokat használ.

Tervezési elv:
    - A stílusok Python stringként vannak definiálva
      (nem külön .qss fájlban),
      így lehetőség van dinamikus stílusgenerálásra.

Architektúra megjegyzés:
    - A stílusréteg nem tartalmaz üzleti logikát.
    - Nem hivatkozhat DB-re vagy UI állapotra.
    - Csak megjelenési felelőssége van.
"""


def apply_modern_stylesheet(window) -> None:
    """
    Modern stíluslap alkalmazása a teljes alkalmazásra.
    A window tipikusan a MainWindow példány.
    """
    window.setStyleSheet(
        """
        QMainWindow {
            background-color: #f5f7fa;
        }

        QTabWidget::pane {
            border: none;
            background-color: #f5f7fa;
        }

        QTabWidget::tab-bar {
            alignment: left;
        }

        QTabBar::tab {
            background-color: #e8ecef;
            color: #495057;
            padding: 8px 20px;
            margin-right: 4px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            font-size: 10pt;
            font-weight: 500;
        }

        QTabBar::tab:selected {
            background-color: #ffffff;
            color: #2c5aa0;
            font-weight: 600;
        }

        QTabBar::tab:hover:!selected {
            background-color: #dce1e6;
        }

        QGroupBox {
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 10px;
            margin-top: 8px;
            padding: 15px;
            font-weight: 600;
            font-size: 10pt;
            color: #2c5aa0;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            background-color: white;
        }

        QLabel {
            color: #495057;
            font-size: 9pt;
        }

        QLineEdit, QTextEdit {
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            padding: 6px 10px;
            background-color: white;
            font-size: 9pt;
            color: #212529;
        }

        QLineEdit:focus, QTextEdit:focus {
            border: 2px solid #2c5aa0;
            background-color: #f8f9ff;
        }

        QPushButton {
            background-color: #2c5aa0;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 9pt;
            font-weight: 600;
        }

        QPushButton:hover {
            background-color: #1e3a6e;
        }

        QPushButton:pressed {
            background-color: #152847;
        }

        QTableWidget {
            background-color: white;
            alternate-background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            gridline-color: #e9ecef;
        }

        QTableWidget::item {
            padding: 6px;
        }

        QTableWidget::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }

        QHeaderView::section {
            background-color: #f8f9fa;
            color: #495057;
            padding: 8px;
            border: none;
            border-bottom: 2px solid #dee2e6;
            font-weight: 600;
            font-size: 9pt;
        }

        QComboBox {
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            padding: 6px 10px;
            background-color: white;
            font-size: 9pt;
        }

        QComboBox:focus {
            border: 2px solid #2c5aa0;
        }

        QComboBox::drop-down {
            border: none;
            width: 25px;
        }

        QMenuBar {
            background-color: #2c5aa0;
            color: white;
            padding: 2px;
        }

        QMenuBar::item {
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 4px;
        }

        QMenuBar::item:selected {
            background-color: #1e3a6e;
        }

        QMenu {
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 6px;
        }

        QMenu::item {
            padding: 6px 20px;
            border-radius: 4px;
        }

        QMenu::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        """
    )


NAV_QSS = """
#navBar {
    background: rgba(0, 0, 0, 0.03);
    border: 1px solid rgba(0, 0, 0, 0.10);
    border-radius: 8px;
}

#navBar QPushButton#navButton {
    background: transparent;
    border: 1px solid transparent;
    padding: 6px 10px;
    margin: 2px 2px;
    border-radius: 8px;
    min-height: 28px;
}

#navBar QPushButton#navButton:hover {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.10);
}

#navBar QPushButton#navButton:pressed {
    background: rgba(0, 0, 0, 0.06);
    border-color: rgba(0, 0, 0, 0.18);
}

#navBar QPushButton#navButton:checked {
    background: rgba(0, 0, 0, 0.06);
    border-color: rgba(0, 0, 0, 0.16);
    font-weight: 600;
}
"""

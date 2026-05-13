# penzugyi_naplo/ui/settings.py
# -------------------------------

"""
Beállítások ablak a Pénzügyi Napló alkalmazáshoz.

Felelősség:
- Az alkalmazás beállításainak külön QDialog ablakban történő megjelenítése.
- Bal oldali kategória-sáv kezelése.
- Jobb oldali beállítási oldalak váltása.
- App-szintű és modul-szintű beállítások elkülönítése.

Architektúra szerep:
- Ez a fájl a Beállítások alrendszer fő belépési pontja.
- Később az oldalak külön fájlokba bonthatók:
  general_page.py, appearance_page.py, developer_page.py, liquidity_page.py, gold_page.py

UI szerkezet:
- Bal oldalon kategóriagombok:
  Általános, Megjelenés, Fejlesztői
  --- vizuális elválasztó ---
  Likviditás, Aranyszámla
- Jobb oldalon QStackedWidget mutatja az aktuális beállítási oldalt.

Kapcsolódás:
- MainWindow-ból vagy menüből hívható:
  dialog = SettingsDialog(self)
  dialog.exec()
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)



from penzugyi_naplo.config import (
    APP_NAME,
    ORG_NAME,
    SETTINGS_KEY_DEV_MODE,
    SETTINGS_KEY_STYLE_MODE,
    STYLE_CLASSIC,
    STYLE_MODERN,
    STYLE_MODERN_HOME,
    DEFAULT_STYLE_MODE,
)


class SettingsDialog(QDialog):
    """Az alkalmazás fő Beállítások ablaka."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Beállítások ablak inicializálása."""
        super().__init__(parent)

        # A parent várhatóan a MainWindow.
        # Ezen keresztül tudjuk meghívni az app-szintű műveleteket:
        # - apply_style_mode()
        # - set_toolbar_mode()
        self.main_window = parent







        self.setWindowTitle("Beállítások")
        self.setObjectName("settingsDialog")
        self.resize(760, 480)

        # A bal oldali kategóriagombok csoportja.
        # Ez biztosítja, hogy egyszerre csak egy kategória legyen aktív.
        self.category_group = QButtonGroup(self)
        self.category_group.setExclusive(True)

        # A jobb oldali tartalomterület.
        # A kategóriákhoz tartozó oldalak itt váltódnak.
        self.stack = QStackedWidget()
        self.stack.setObjectName("settingsStack")

        # Fő layout: bal oldali sidebar + jobb oldali tartalom.
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        sidebar = self._build_sidebar()
        content = self._build_content_area()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content, 1)

        # Alapértelmezésként az Általános oldal legyen kiválasztva.
        self.general_btn.setChecked(True)
        self.stack.setCurrentIndex(0)

    def _build_sidebar(self) -> QWidget:
        """Bal oldali kategória-sáv létrehozása."""
        sidebar = QFrame()
        sidebar.setObjectName("settingsSidebar")
        sidebar.setFixedWidth(180)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(6)

        # App-szintű kategóriák.
        self.general_btn = self._create_category_button("Általános", 0)
        self.appearance_btn = self._create_category_button("Megjelenés", 1)
        self.developer_btn = self._create_category_button("Fejlesztői", 2)

        layout.addWidget(self.general_btn)
        layout.addWidget(self.appearance_btn)
        layout.addWidget(self.developer_btn)

        # Vizuális elválasztó az app-szintű és modul-szintű beállítások között.
        layout.addSpacing(8)
        layout.addWidget(self._create_separator())
        layout.addSpacing(8)

        # Modul-szintű kategóriák.
        self.liquidity_btn = self._create_category_button("Likviditás", 3)
        self.gold_btn = self._create_category_button("Aranyszámla", 4)

        layout.addWidget(self.liquidity_btn)
        layout.addWidget(self.gold_btn)

        layout.addStretch(1)

        return sidebar

    def _create_category_button(self, text: str, page_index: int) -> QPushButton:
        """Egy bal oldali kategóriagomb létrehozása."""
        button = QPushButton(text)
        button.setObjectName("settingsCategoryButton")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # A gombot hozzáadjuk az exkluzív csoporthoz.
        self.category_group.addButton(button)

        # Kattintáskor a megfelelő beállítási oldalra váltunk.
        button.clicked.connect(lambda: self.stack.setCurrentIndex(page_index))

        return button

    def _create_separator(self) -> QWidget:
        """
        Vizuális elválasztó létrehozása.

        Fontos:
        - Az objectName alapján QSS-ből témánként külön stílus adható.
        - Classic témában lehet sima szürke vonal.
        - Modern témában lehet színes vonal.
        - modern_home témában lehet finom neon/fénycsík hatás.
        """
        separator = QFrame()
        separator.setObjectName("settingsCategorySeparator")
        separator.setFixedHeight(2)
        separator.setFrameShape(QFrame.Shape.NoFrame)
        return separator

    def _build_content_area(self) -> QWidget:
        """Jobb oldali tartalomterület létrehozása."""
        content = QFrame()
        content.setObjectName("settingsContent")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        self.stack.addWidget(self._build_general_page())
        self.stack.addWidget(self._build_appearance_page())
        self.stack.addWidget(self._build_developer_page())
        self.stack.addWidget(self._build_liquidity_page())
        self.stack.addWidget(self._build_gold_page())

        layout.addWidget(self.stack)

        # Alsó gombsor.
        button_row = QHBoxLayout()
        button_row.addStretch(1)

        close_btn = QPushButton("Bezárás")
        close_btn.setObjectName("settingsCloseButton")
        close_btn.clicked.connect(self.accept)

        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

        return content

    def _build_general_page(self) -> QWidget:
        """Általános beállítások oldala."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = self._create_page_title("Általános")
        description = self._create_description_label(
            "Általános, az egész alkalmazásra vonatkozó beállítások."
        )

        db_section = self._create_section_title("Adatbázis")

        db_path_label = QLabel("Aktuális adatbázis helye:")
        db_path_label.setObjectName("settingsFieldLabel")

        db_path_text = "Nincs elérhető adatbázis-útvonal."

        if self.main_window is not None and hasattr(self.main_window, "db"):
            db = self.main_window.db
        if hasattr(db, "db_name"):
            db_path_text = str(db.db_name)

        db_path_value = QLabel(db_path_text)

        db_path_value.setObjectName("settingsMutedLabel")
        db_path_value.setWordWrap(True)

        prod_dev_section = self._create_section_title("PROD / DEV adatbázis műveletek")

        prod_to_dev_btn = QPushButton("PROD → DEV másolás")
        prod_to_dev_btn.setObjectName("settingsDangerAwareButton")

        dev_to_prod_btn = QPushButton("DEV → PROD másolás")
        dev_to_prod_btn.setObjectName("settingsDangerButton")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(8)

        layout.addWidget(db_section)
        layout.addWidget(db_path_label)
        layout.addWidget(db_path_value)
        layout.addSpacing(12)

        layout.addWidget(prod_dev_section)
        layout.addWidget(prod_to_dev_btn)
        layout.addWidget(dev_to_prod_btn)

        layout.addStretch(1)

        return page




    def _build_appearance_page(self) -> QWidget:
        """Megjelenési beállítások oldala."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = self._create_page_title("Megjelenés")
        description = self._create_description_label(
            "Az alkalmazás kinézetével és eszköztárával kapcsolatos beállítások."
        )

        toolbar_section = self._create_section_title("Eszköztár")

        ribbon_radio = QRadioButton("Szalag / ribbon")
        ribbon_radio.setObjectName("settingsRadioButton")

        classic_menu_radio = QRadioButton("Klasszikus menüsor")
        classic_menu_radio.setObjectName("settingsRadioButton")

        toolbar_group = QButtonGroup(page)
        toolbar_group.addButton(ribbon_radio)
        toolbar_group.addButton(classic_menu_radio)

        # Aktuális eszköztár mód betöltése.
        settings = QSettings(ORG_NAME, APP_NAME)
        toolbar_mode = str(settings.value("ui/toolbar_mode", "ribbon"))

        if toolbar_mode == "menubar":
            classic_menu_radio.setChecked(True)
        else:
            ribbon_radio.setChecked(True)

        # Fontos:
        # A jelzéseket csak az alapállapot beállítása után kötjük be,
        # így a dialog megnyitása nem vált véletlenül módot.
        ribbon_radio.toggled.connect(
            lambda checked: self._on_toolbar_mode_changed("ribbon") if checked else None
        )
        classic_menu_radio.toggled.connect(
            lambda checked: self._on_toolbar_mode_changed("menubar") if checked else None
        )

        theme_section = self._create_section_title("Téma")

        theme_combo = QComboBox()
        theme_combo.setObjectName("settingsComboBox")
        theme_combo.addItem("Klasszikus", STYLE_CLASSIC)
        theme_combo.addItem("Modern", STYLE_MODERN)
        theme_combo.addItem("Modern otthonos", STYLE_MODERN_HOME)

        # Aktuális téma betöltése.
        current_mode = str(settings.value(SETTINGS_KEY_STYLE_MODE, DEFAULT_STYLE_MODE))

        for index in range(theme_combo.count()):
            if theme_combo.itemData(index) == current_mode:
                theme_combo.setCurrentIndex(index)
                break

        # A jelzést itt is csak az alapérték beállítása után kötjük be.
        theme_combo.currentIndexChanged.connect(
            lambda _index: self._on_theme_changed(theme_combo.currentData())
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(8)

        layout.addWidget(toolbar_section)
        layout.addWidget(ribbon_radio)
        layout.addWidget(classic_menu_radio)

        layout.addSpacing(12)
        layout.addWidget(theme_section)
        layout.addWidget(theme_combo)

        layout.addStretch(1)

        return page


    def _build_developer_page(self) -> QWidget:
        """Fejlesztői beállítások oldala."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = self._create_page_title("Fejlesztői")
        description = self._create_description_label(
            "A fejlesztői mód kísérleti vagy félkész funkciókat is elérhetővé tehet. "
            "Ezt csak teszteléshez érdemes bekapcsolni."
        )

        dev_mode_section = self._create_section_title("Fejlesztői mód")

        settings = QSettings(ORG_NAME, APP_NAME)
        dev_mode_enabled = settings.value(SETTINGS_KEY_DEV_MODE, False, type=bool)

        dev_mode_btn = QPushButton("Fejlesztői mód engedélyezése")
        dev_mode_btn.setObjectName("settingsDevModeButton")
        dev_mode_btn.setCheckable(True)
        dev_mode_btn.setChecked(dev_mode_enabled)

        if dev_mode_enabled:
            dev_mode_btn.setText("Fejlesztői mód engedélyezve")

        dev_mode_btn.toggled.connect(
            lambda checked: self._on_dev_mode_toggled(dev_mode_btn, checked)
        )

        note = self._create_description_label(
            "Bekapcsoláskor megerősítő ablak jelenik meg. "
            "A módosítás bizonyos esetekben csak újraindítás után érvényesül teljesen."
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(8)

        layout.addWidget(dev_mode_section)
        layout.addWidget(dev_mode_btn)
        layout.addWidget(note)

        layout.addStretch(1)

        return page






    def _build_liquidity_page(self) -> QWidget:
        """Likviditás modul beállítási oldala."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = self._create_page_title("Likviditás")
        description = self._create_description_label(
            "A Likviditás modulhoz tartozó beállítások helye. "
            "Ide kerülhetnek később a kategóriák, számlák, importálás és szűrés beállításai."
        )

        placeholder = self._create_placeholder_label(
            "Későbbi elemek:\n"
            "- Kiadási / bevételi kategóriák kezelése\n"
            "- Számlák alapértékei\n"
            "- ODS import beállítások\n"
            "- Tranzakciós lista szűrési beállítások"
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(8)
        layout.addWidget(placeholder)

        layout.addStretch(1)

        return page

    def _build_gold_page(self) -> QWidget:
        """Aranyszámla modul beállítási oldala."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = self._create_page_title("Aranyszámla")
        description = self._create_description_label(
            "Az Aranyszámla modulhoz tartozó beállítások helye."
        )

        storage_section = self._create_section_title("Tárolási hely / szolgáltató")

        storage_label = QLabel("Arany tárolása:")
        storage_label.setObjectName("settingsFieldLabel")

        storage_value = QLabel("Itt adható majd meg például: Goldtresor")
        storage_value.setObjectName("settingsMutedLabel")

        fees_section = self._create_section_title("Alapértelmezett díjak")

        fees_placeholder = self._create_placeholder_label(
            "Későbbi elemek:\n"
            "- Kártyás befizetési díj\n"
            "- Letétbiztosítási díj\n"
            "- Egyéb, kézzel szerkeszthető aranyszámla díjak"
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(8)

        layout.addWidget(storage_section)
        layout.addWidget(storage_label)
        layout.addWidget(storage_value)

        layout.addSpacing(12)
        layout.addWidget(fees_section)
        layout.addWidget(fees_placeholder)

        layout.addStretch(1)

        return page

    def _create_page_title(self, text: str) -> QLabel:
        """Oldalcím létrehozása."""
        label = QLabel(text)
        label.setObjectName("settingsPageTitle")
        return label

    def _create_section_title(self, text: str) -> QLabel:
        """Szekciócím létrehozása."""
        label = QLabel(text)
        label.setObjectName("settingsSectionTitle")
        return label

    def _create_description_label(self, text: str) -> QLabel:
        """Leíró szöveg létrehozása."""
        label = QLabel(text)
        label.setObjectName("settingsDescriptionLabel")
        label.setWordWrap(True)
        return label

    def _create_placeholder_label(self, text: str) -> QLabel:
        """Placeholder jellegű magyarázó blokk létrehozása."""
        label = QLabel(text)
        label.setObjectName("settingsPlaceholderLabel")
        label.setWordWrap(True)
        return label




    def _on_theme_changed(self, mode: str) -> None:
        """
        Téma módosítása a Beállítások ablakból.

        Mentés:
            - QSettings-be írjuk az új témát.

        Azonnali hatás:
            - Meghívjuk a MainWindow apply_style_mode() metódusát.
            - A SettingsDialogra külön is ráadjuk az új stylesheetet,
            mert külön top-level QDialogként nem mindig frissül magától.
        """
        settings = QSettings(ORG_NAME, APP_NAME)
        settings.setValue(SETTINGS_KEY_STYLE_MODE, mode)

        if self.main_window is not None and hasattr(self.main_window, "apply_style_mode"):
            self.main_window.apply_style_mode(mode)

            if hasattr(self.main_window, "styleSheet"):
                self.setStyleSheet(self.main_window.styleSheet())


    def _on_toolbar_mode_changed(self, mode: str) -> None:
        """
        Eszköztár mód módosítása.

        mode:
            - "ribbon": szalag / ribbon mód
            - "menubar": klasszikus menüsor mód
        """
        settings = QSettings(ORG_NAME, APP_NAME)
        settings.setValue("ui/toolbar_mode", mode)

        if self.main_window is not None and hasattr(self.main_window, "set_toolbar_mode"):
            self.main_window.set_toolbar_mode(mode)


    def _on_dev_mode_toggled(self, button: QPushButton, checked: bool) -> None:
        """
        Fejlesztői mód kapcsoló kezelése.

        Bekapcsoláskor és kikapcsoláskor is megerősítést kérünk,
        mert ez app-szintű működést befolyásol.
        """
        settings = QSettings(ORG_NAME, APP_NAME)

        # A toggled jelzés közben visszaállításkor ne fusson bele végtelen logikába.
        button.blockSignals(True)

        if checked:
            answer = QMessageBox.question(
                self,
                "Fejlesztői mód engedélyezése",
                (
                    "Fejlesztői mód engedélyezésére készülsz.\n\n"
                    "Ez kísérleti vagy félkész funkciókat is elérhetővé tehet.\n\n"
                    "Biztosan engedélyezed?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if answer == QMessageBox.StandardButton.Yes:
                settings.setValue(SETTINGS_KEY_DEV_MODE, True)
                button.setChecked(True)
                button.setText("Fejlesztői mód engedélyezve")
            else:
                settings.setValue(SETTINGS_KEY_DEV_MODE, False)
                button.setChecked(False)
                button.setText("Fejlesztői mód engedélyezése")

        else:
            answer = QMessageBox.question(
                self,
                "Fejlesztői mód kikapcsolása",
                (
                    "A fejlesztői mód kikapcsolására készülsz.\n\n"
                    "A kísérleti funkciók nem lesznek elérhetők.\n\n"
                    "Folytatod?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if answer == QMessageBox.StandardButton.Yes:
                settings.setValue(SETTINGS_KEY_DEV_MODE, False)
                button.setChecked(False)
                button.setText("Fejlesztői mód engedélyezése")
            else:
                settings.setValue(SETTINGS_KEY_DEV_MODE, True)
                button.setChecked(True)
                button.setText("Fejlesztői mód engedélyezve")

        button.blockSignals(False)
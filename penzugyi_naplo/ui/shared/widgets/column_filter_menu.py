# penzugyi_naplo/ui/shared/widgets/column_filter_menu.py
# -----------------------------------------------------

"""
Excel-szerű, checkbox-listás oszlopszűrő menü QTableWidget fejlécekhez.

Cél:
    - jobb-klikk egy oszlop fejlécén megnyit egy legördülő menüt
    - a menüben az adott oszlopban ténylegesen előforduló értékek
      (vagy Dátum esetén Év/Hónap csoportok) checkbox-listaként jelennek meg
    - kipipálás/kivétel azonnal (élő) frissíti a táblázat sorainak
      láthatóságát - nincs külön "Alkalmaz" gomb

Ez a fájl NEM tud semmit a Tranzakciók oldal konkrét oszlopairól vagy
adatmodelljéről - egy általános, újrafelhasználható komponens, amit bármely
QTableWidget-alapú oldal bekothet a saját fejlécére.

Használat (nagy vonalakban, lásd transactions_page.py-ban a pontos bekötést):

    menu = FlatColumnFilterMenu(
        parent=header,
        all_values=["Bevétel", "Kiadás", "Számlabefizetés"],
        selected_values=self._type_filter_selected,   # None = "minden érték látszik"
        on_change=self._on_type_filter_changed,
    )
    menu.exec(header.mapToGlobal(pos))

Dátum-szerű, Év -> Hónap csoportos szűréshez lásd: DateColumnFilterMenu.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QScrollArea,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

# Hónapnevek a Dátum-szűrő Év -> Hónap csoportosításához.
# Index 1 = Január ... 12 = December (a hónap-szám 1-alapú a tx_date-ből).
_HU_MONTH_NAMES: tuple[str, ...] = (
    "",  # 0. index nem használt, hogy month_number közvetlenül indexelhessen
    "Január",
    "Február",
    "Március",
    "Április",
    "Május",
    "Június",
    "Július",
    "Augusztus",
    "Szeptember",
    "Október",
    "November",
    "December",
)


def _apply_fusion_style_recursively(widget: QWidget) -> None:
    """
    Fusion widget-stílus alkalmazása egy widget-re és annak összes
    gyerek-widget-jére, rekurzívan.

    A projekt nem állít be explicit "Fusion" stílust az egész
    alkalmazásra (lásd main.py) - emiatt a QApplication a rendszer natív
    widget-stílusát használja (pl. GTK/Breeze Linuxon). Egyes natív
    stílus-motorok a QMenu és a QScrollArea hátterét, illetve a
    QCheckBox kijelölő-négyzetét részben natívan rajzolják ki, a QSS-től
    függetlenül - ez okozta a "stílus nélküli", szürke, szögletes menü
    tünetét (a QSS csak a szöveg színét/vastagságát tudta érvényesíteni,
    a hátteret és a checkbox-ok kinézetét nem).

    A Fusion stílus-motor kifejezetten, megbízhatóan követi a QSS-t,
    ezért ezt a menüt (és csak ezt - az alkalmazás egészét nem érintve)
    kényszerítjük Fusion-ra, közvetlenül azelőtt, hogy a felhasználó elé
    kerülne. A setStyle() nem öröklődik automatikusan a gyerek-widget-ekre,
    ezért kell ez a rekurzív bejárás minden egyes checkbox-ra/gombra is.

    KRITIKUS - miért kap MINDEN egyes menü-megnyitás egy VADONATÚJ
    QStyleFactory.create("Fusion") példányt, egyetlen, modul-szinten
    megosztott példány helyett (gdb-vel visszafejtett ok):

    Mivel ennek a menünek explicit stíluslapja (QSS) van (lásd
    _make_scrollable_checkbox_container()), minden setStyle() hívás
    mögött Qt automatikusan létrehoz egy belső QStyleSheetStyle proxy-t,
    ami - Qt saját, dokumentálatlan belső mechanizmusaként - a neki átadott
    "alap" stílust MAGÁVAL rántja, amikor ez a proxy megsemmisül (ez
    FÜGGETLEN attól, hogy az alap-stílusnak van-e explicit Qt-szülője
    (setParent) - ez nem a QObject szülő/gyerek élettartam-kezelésen
    keresztül történik).

    Ha EGYETLEN, megosztott Fusion-példányt adnánk át több, EGYMÁSTÓL
    FÜGGETLENÜL megsemmisülő menünek (pl. mert egy korábbi menü már
    bezárult és törlődött, mire egy újabbat nyitunk), az ELSŐ ilyen menü
    megsemmisülése (a benne rejlő QStyleSheetStyle proxy-n keresztül)
    törli a megosztott stílust - a MÁSODIK, még nyitva lévő/ezután
    megnyitott menü ekkor egy már törölt QStyle-ra hivatkozna ->
    szegmentálási hiba, illetve (ha shiboken időben észreveszi) "Internal
    C++ object already deleted" RuntimeError.

    A biztonságos minta: minden menü kapja meg a SAJÁT, kizárólag hozzá
    tartozó stílus-példányát. Így egy adott menü (és a benne létrejövő
    összes QStyleSheetStyle proxy, valamint maga a Fusion-stílus) EGYETLEN,
    önmagában konzisztens egységet alkot, ami így a menü bezárásakor
    (lásd FlatColumnFilterMenu.exec() / DateColumnFilterMenu.exec() végén
    a deleteLater()-t) EGYÜTT, egyetlen kaszkádban semmisül meg - más,
    független menüt ez sosem érinthet, mert semmi nem osztozik rajta.
    """
    fusion_style = QStyleFactory.create("Fusion")
    if fusion_style is None:
        return  # Elvileg mindig elérhető, de defenzíven kezeljük.

    def _apply(w: QWidget) -> None:
        w.setStyle(fusion_style)
        for child in w.findChildren(QWidget):
            child.setStyle(fusion_style)

    _apply(widget)


def _make_scrollable_checkbox_container(
    parent: QWidget | None,
    max_visible_rows: int = 12,
) -> tuple[QMenu, QVBoxLayout]:
    """
    Közös építőelem: egy QMenu, benne egy görgethető checkbox-konténerrel.

    Görgethetőség azért kell, mert egy Kategória oszlopban simán lehet
    20-30 különböző kategória - enélkül a menü kilógna a képernyőről.

    FONTOS a QSS-öröklés miatt: egy QMenu Qt.Popup ablakként jelenik meg,
    ami NEM örökli meg automatikusan a MainWindow-on beállított QSS-t
    (lásd main_window.py apply_style_mode() - a projekt a stíluslapot a
    MainWindow-ra, nem a QApplication-re állítja be, ezért egy önálló
    popup-ablak, mint a QMenu, ebből az öröklési láncból kimarad). Ezért
    két védelmi vonal van:
        1) explicit `parent` (a fejléc widget-je) - a menü POZÍCIÓjához
           és a képernyő/DPI helyes felismeréséhez kell.
        2) a menü kap egy MÁSOLATOT a parent legfelső ablakának
           (parent.window()) ténylegesen beállított stíluslapjából - ez
           a megbízható út, mert az öröklés maga nem működne.
    """
    menu = QMenu(parent)
    menu.setObjectName("columnFilterMenu")

    # A projekt QSS-e nem app-szinten (QApplication.setStyleSheet), hanem
    # a MainWindow-on (self.setStyleSheet(...), lásd main_window.py
    # apply_style_mode()) van beállítva - ezért QApplication.styleSheet()
    # itt mindig üres lenne. A helyes forrás a `parent` legfelső ablaka
    # (parent.window()), mert a MainWindow widget-fáján ott van az
    # explicit beállított, ténylegesen érvényes stíluslap.
    if parent is not None:
        top_level_stylesheet = parent.window().styleSheet()
        if top_level_stylesheet:
            menu.setStyleSheet(top_level_stylesheet)

    container = QWidget(menu)
    lay = QVBoxLayout(container)
    lay.setContentsMargins(8, 6, 8, 6)
    lay.setSpacing(2)

    scroll = QScrollArea(menu)
    scroll.setObjectName("columnFilterScrollArea")
    scroll.setWidget(container)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    # Durva becslés a max magasságra: checkbox-onként kb. 24px + fejléc-sorok.
    scroll.setMaximumHeight(max_visible_rows * 24 + 60)

    action = QWidgetAction(menu)
    action.setDefaultWidget(scroll)
    menu.addAction(action)

    return menu, lay


class FlatColumnFilterMenu:
    """
    Lapos (nem csoportosított) checkbox-listás szűrő menü - a Típus és
    Kategória oszlopokhoz.

    Nem widget, hanem egy vékony builder: felépíti a QMenu-t, és a
    callback-eken keresztül kommunikál kifelé. A menü élettartama a
    exec() hívás alatt tart, utána eldobható.
    """

    def __init__(
        self,
        *,
        all_values: Iterable[str],
        selected_values: set[str] | None,
        on_change: Callable[[set[str] | None], None],
        parent: QWidget | None = None,
    ) -> None:
        """
        all_values:
            Az oszlopban ténylegesen előforduló, egyedi értékek listája
            (már a betöltött sorokból gyűjtve, sorrendben).
        selected_values:
            A jelenleg kijelölt (látszó) értékek halmaza, vagy None,
            ha nincs aktív szűrő (= minden érték látszik, minden checkbox
            pipálva jelenik meg).
        on_change:
            Hívás minden checkbox-váltásra, az ÚJ kijelölt halmazzal.
            Ha minden checkbox be van pipálva, None-t kap (nincs szűrés,
            hogy a hívó oldalon ne kelljen külön "van-e még aktív szűrő"
            ellenőrzést végezni minden egyes sorra).
        parent:
            A menü szülő widget-je (jellemzően a táblázat fejléce, amiről
            a jobb-klikk indult). Szülő nélkül a menü nem örökli meg
            megbízhatóan az alkalmazás-szintű QSS-t - lásd
            _make_scrollable_checkbox_container() docstringje.
        """
        self._all_values = list(dict.fromkeys(all_values))  # sorrend-megtartó dedup
        self._on_change = on_change
        self._checkboxes: dict[str, QCheckBox] = {}

        # None = minden ki van választva (nincs aktív szűrés)
        self._selected: set[str] = (
            set(self._all_values) if selected_values is None else set(selected_values)
        )

        self.menu, self._layout = _make_scrollable_checkbox_container(parent)
        self._build()

    def _build(self) -> None:
        for value in self._all_values:
            cb = QCheckBox(value, self.menu)
            cb.setObjectName("columnFilterCheckbox")
            cb.setChecked(value in self._selected)
            cb.toggled.connect(lambda checked, v=value: self._on_toggled(v, checked))
            self._checkboxes[value] = cb
            self._layout.addWidget(cb)

        self._layout.addSpacing(4)

        select_all_row = QWidget(self.menu)
        row_lay = QHBoxLayout(select_all_row)
        row_lay.setContentsMargins(0, 4, 0, 0)

        btn_all = QPushButton("Összes", select_all_row)
        btn_all.setObjectName("columnFilterQuickButton")
        btn_all.setFlat(True)
        btn_all.clicked.connect(self._select_all)

        btn_none = QPushButton("Semmi", select_all_row)
        btn_none.setObjectName("columnFilterQuickButton")
        btn_none.setFlat(True)
        btn_none.clicked.connect(self._select_none)

        row_lay.addWidget(btn_all)
        row_lay.addWidget(btn_none)
        row_lay.addStretch(1)

        self._layout.addWidget(select_all_row)

    def _on_toggled(self, value: str, checked: bool) -> None:
        if checked:
            self._selected.add(value)
        else:
            self._selected.discard(value)

        # Ha minden érték ki van választva, ez logikailag "nincs szűrés" -
        # None-t adunk tovább, hogy a hívó oldal ne tartson felesleges,
        # üres hatású szűrő-állapotot.
        result: set[str] | None
        result = None if self._selected == set(self._all_values) else set(self._selected)
        self._on_change(result)

    def _select_all(self) -> None:
        for value, cb in self._checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(True)
            cb.blockSignals(False)
            self._selected.add(value)
        self._on_change(None)

    def _select_none(self) -> None:
        for cb in self._checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self._selected.clear()
        self._on_change(set())

    def exec(self, global_pos) -> None:
        # Fusion-stílus kényszerítése a teljes widget-fára, közvetlenül
        # a menü megnyitása előtt - lásd _apply_fusion_style_recursively().
        _apply_fusion_style_recursively(self.menu)
        self.menu.exec(global_pos)

        # A QMenu a `parent` (fejléc) C++ gyerekeként jön létre (lásd
        # _make_scrollable_checkbox_container()), ezért Qt-szinten addig
        # élne, amíg a fejléc maga - enélkül a deleteLater() nélkül minden
        # jobb-klikk egy újabb, örökre a fejléc alatt maradó menü-widget-fát
        # (checkbox-ok, QScrollArea, stb.) hagyna hátra a munkamenet végéig.
        # Az exec() ide visszatér, amint a menü bezárult, tehát biztonságos
        # itt ütemezni a törlését.
        self.menu.deleteLater()


class DateColumnFilterMenu:
    """
    Két szintű (Év -> Hónap) checkbox-listás szűrő menü a Dátum oszlophoz.

    Egy Év-sor kipipálása/kivétele az összes hozzá tartozó hónapot is
    állítja; egy Hónap-sor egyenkénti (ki)pipálása az Év-sor állapotát
    frissíti (teljes/részleges/üres kijelölés).
    """

    def __init__(
        self,
        *,
        year_months: dict[int, set[int]],
        selected_year_months: set[tuple[int, int]] | None,
        on_change: Callable[[set[tuple[int, int]] | None], None],
        parent: QWidget | None = None,
    ) -> None:
        """
        year_months:
            {év: {hónap, hónap, ...}} - a Dátum oszlopban ténylegesen
            előforduló év/hónap kombinációk, a betöltött sorokból gyűjtve.
        selected_year_months:
            Jelenleg kijelölt (év, hónap) párok halmaza, vagy None, ha
            nincs aktív szűrés (minden checkbox pipálva jelenik meg).
        on_change:
            Hívás minden változásra, az új (év, hónap) kijelölt halmazzal.
            None, ha minden lehetséges (év, hónap) ki van választva.
        parent:
            A menü szülő widget-je (jellemzően a táblázat fejléce, amiről
            a jobb-klikk indult). Lásd FlatColumnFilterMenu docstringje.
        """
        self._year_months = year_months
        self._on_change = on_change

        all_pairs = {
            (year, month) for year, months in year_months.items() for month in months
        }
        self._all_pairs = all_pairs
        self._selected: set[tuple[int, int]] = (
            set(all_pairs) if selected_year_months is None else set(selected_year_months)
        )

        self._year_checkboxes: dict[int, QCheckBox] = {}
        self._month_checkboxes: dict[tuple[int, int], QCheckBox] = {}

        self.menu, self._layout = _make_scrollable_checkbox_container(
            parent, max_visible_rows=16
        )
        self._build()

    def _build(self) -> None:
        for year in sorted(self._year_months.keys(), reverse=True):
            months = sorted(self._year_months[year])

            year_cb = QCheckBox(str(year), self.menu)
            year_cb.setObjectName("columnFilterYearCheckbox")
            year_font = year_cb.font()
            year_font.setBold(True)
            year_cb.setFont(year_font)

            self._year_checkboxes[year] = year_cb
            self._layout.addWidget(year_cb)

            month_container = QWidget(self.menu)
            month_lay = QVBoxLayout(month_container)
            month_lay.setContentsMargins(20, 0, 0, 4)
            month_lay.setSpacing(1)

            for month in months:
                pair = (year, month)
                month_cb = QCheckBox(_HU_MONTH_NAMES[month], month_container)
                month_cb.setObjectName("columnFilterMonthCheckbox")
                month_cb.setChecked(pair in self._selected)
                month_cb.toggled.connect(
                    lambda checked, p=pair: self._on_month_toggled(p, checked)
                )
                self._month_checkboxes[pair] = month_cb
                month_lay.addWidget(month_cb)

            self._layout.addWidget(month_container)

            # Év checkbox állapota a hónapok alapján, jelzés nélküli
            # (blockSignals) kezdeti beállítással, mert a toggled csak
            # felhasználói kattintásra kell hogy lefusson.
            year_cb.blockSignals(True)
            self._sync_year_checkbox(year)
            year_cb.blockSignals(False)

            year_cb.toggled.connect(lambda checked, y=year: self._on_year_toggled(y, checked))

        self._layout.addStretch(1)

    def _sync_year_checkbox(self, year: int) -> None:
        """Az Év checkbox állapotát a hozzá tartozó Hónap checkbox-okhoz igazítja."""
        months = self._year_months[year]
        checked_count = sum(1 for m in months if (year, m) in self._selected)

        cb = self._year_checkboxes[year]
        cb.blockSignals(True)
        if checked_count == 0:
            cb.setCheckState(Qt.CheckState.Unchecked)
        elif checked_count == len(months):
            cb.setCheckState(Qt.CheckState.Checked)
        else:
            cb.setCheckState(Qt.CheckState.PartiallyChecked)
        cb.blockSignals(False)

    def _on_month_toggled(self, pair: tuple[int, int], checked: bool) -> None:
        if checked:
            self._selected.add(pair)
        else:
            self._selected.discard(pair)

        self._sync_year_checkbox(pair[0])
        self._emit_change()

    def _on_year_toggled(self, year: int, checked: bool) -> None:
        # Az Év checkbox tristate, de a felhasználói kattintás mindig
        # Checked/Unchecked felé billen (a PartiallyChecked programozott
        # köztes állapot, nem kattintható rá közvetlenül Qt-ban alapból) -
        # tehát itt elég a bool checked alapján dönteni.
        months = self._year_months[year]

        for month in months:
            pair = (year, month)
            if checked:
                self._selected.add(pair)
            else:
                self._selected.discard(pair)

            month_cb = self._month_checkboxes[pair]
            month_cb.blockSignals(True)
            month_cb.setChecked(checked)
            month_cb.blockSignals(False)

        self._emit_change()

    def _emit_change(self) -> None:
        result: set[tuple[int, int]] | None
        result = None if self._selected == self._all_pairs else set(self._selected)
        self._on_change(result)

    def exec(self, global_pos) -> None:
        # Fusion-stílus kényszerítése a teljes widget-fára, közvetlenül
        # a menü megnyitása előtt - lásd _apply_fusion_style_recursively().
        _apply_fusion_style_recursively(self.menu)
        self.menu.exec(global_pos)

        # A QMenu a `parent` (fejléc) C++ gyerekeként jön létre (lásd
        # _make_scrollable_checkbox_container()), ezért Qt-szinten addig
        # élne, amíg a fejléc maga - enélkül a deleteLater() nélkül minden
        # jobb-klikk egy újabb, örökre a fejléc alatt maradó menü-widget-fát
        # (checkbox-ok, QScrollArea, stb.) hagyna hátra a munkamenet végéig.
        # Az exec() ide visszatér, amint a menü bezárult, tehát biztonságos
        # itt ütemezni a törlését.
        self.menu.deleteLater()

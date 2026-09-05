# Verzió információk
# Ezt a fájlt használja:
# - Névjegy ablak
# - csomagolás / release információ (.github/workflows: build-deb.yml, publish-apt-repo.yml)

# Itt szerkezd

APP_NAME = "Pénzügyi Napló"
APP_VERSION = "0.4.0"
APP_CHANNEL = "Előzetes verzió"

BUILD_INFO = "2025. november - 2026. június között készült."

DEV_STATE = (
    "Aktuális fejlesztési állapot:\n"
    "Tranzakció nézet - Excel-szerű szűrés (Dátum/Kategória/Típus),\n"
    "Status-bar - kézi mentés/betöltés jelzése,\n"
    "Számlák oldal - témák javítása,\n"
    "Naplózás bővítve"
)

# ---------------------------------------------------------------------------
# 0.3.0 -> 0.4.0 (2026.09.05, dev -> Preview merge, 23 commit)
# ---------------------------------------------------------------------------
#
# Miért minor (0.x.0), nem patch (0.x.y):
#   Új, felhasználó-szemből is látható funkció került be (Excel-szerű
#   oszlopszűrés), nem csak hibajavítás - ez indokolja a minor-szintű emelést
#   a patch helyett.
#
# Ebben a verzióban (dev-ről mergelt főbb tételek):
#   - feat: Excel-szerű oszlopszűrés a Tranzakciók táblázatban
#     (Dátum/Kategória/Típus fejlécen jobb-klikk -> checkbox-lista).
#     Új fájl: ui/shared/widgets/column_filter_menu.py.
#   - fix: statusbar "Utolsó mentés"/"Utoljára betöltve" mostantól
#     KIZÁRÓLAG kézi backup/restore-ra frissül, nem minden DB-módosításra;
#     app-újraindítás után is megmarad (QSettings-perzisztencia).
#   - feat: globális statusbar bevezetése (utolsó mentés/utoljára betöltve).
#   - fix: Számlák oldal témái (számla sorszám mező kiemelése mindhárom
#     QSS témában).
#   - feat: állandó oldalváltás-naplózás (a korábbi, csak dev-módos
#     debug-print helyett).
#   - fix: app-szintű font egységesítése egy helyre (config.py).
#   - ruff: kódstílus-javítások (SIM102/105/108, UP031, F841, E501).
#
# Egy külön, natív szintű hiba is felmerült és javításra került menet
# közben (nem funkció, de fontos stabilitási tétel): a szűrő-menük
# ismételt megnyitása/bezárása szegmentálási hibát (később
# "Internal C++ object already deleted" RuntimeError-t) okozott
# app-bezáráskor. Gyökér-ok: a menü saját QSS-e miatt Qt egy belső
# QStyleSheetStyle proxy-t hoz létre, ami a neki átadott Fusion-stílust
# magával rántja megsemmisüléskor - egy megosztott stílus-példány esetén
# ez use-after-free-hez vezetett több, egymástól függetlenül bezáruló
# menü között. Javítás: minden menü a SAJÁT, kizárólag hozzá tartozó
# stílus-példányát kapja, ami a menüvel (deleteLater()) egyetlen,
# önmagában konzisztens egységként semmisül meg.
#
# A dev ágon 08-07 és 09-05 között felgyűlt 23 commit egyben került át
# a Preview ágra (git merge dev), konfliktusfeloldással 8 fájlban
# (.gitignore, README.md, build-venv.sh, main.py, penzugyi-naplo.pref,
# app_version.py, aranyszamla/home_page.py, main_window.py) - a Preview
# saját, csomagolás-specifikus tartalma (pl. ez a verziószám, a saját
# app-ikon, a DB-zárolás-kezelés) mindenhol megtartva, a dev funkcionális
# újdonságai mellé egyesítve.
# ---------------------------------------------------------------------------

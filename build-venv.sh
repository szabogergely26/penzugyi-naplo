#!/usr/bin/env bash
# build-venv.sh
# ------------------------------
#
# Fejlesztői venv (.venv) automatizált létrehozása/frissítése.
#
# Mindig a requirements-dev.txt-et telepíti (ami a requirements.txt-et is
# magában foglalja -r requirements.txt sorral), tehát a Ruff és Pyright is
# mindig települ - de a szkript maga nem futtat ruff check-et, azt kézzel
# indítod, amikor szükséges (lásd a szkript végén kiírt emlékeztetőt).
#
# Használat:
#   ./build-venv.sh
#
# Amit csinál:
#   1. Ha nincs .venv, létrehozza. Ha már van, csak frissíti a benne lévő
#      csomagokat - nem törli/hozza létre újra minden futtatáskor.
#   2. pip frissítése
#   3. requirements-dev.txt telepítése

set -euo pipefail

echo "==> Python venv támogatás ellenőrzése..."

if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "HIBA: Hiányzik a python3-venv csomag."
    echo
    echo "Telepítés Debian/Ubuntu alatt:"
    echo "  sudo apt install python3-venv"
    echo
    echo "Ha Python 3.13-at használsz:"
    echo "  sudo apt install python3.13-venv"
    exit 1
fi

# A szkript a projekt gyökeréből fusson, függetlenül attól, honnan hívják.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"

echo "=== [1/3] venv ellenőrzése (${VENV_DIR}) ==="
if [ -d "$VENV_DIR" ]; then
    echo "Már létezik a ${VENV_DIR} - nem hozzuk létre újra, csak frissítjük a függőségeket."
else
    echo "Nincs még ${VENV_DIR}, létrehozás..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "=== [2/3] pip frissítése ==="
python3 -m pip install --upgrade pip

echo "=== [3/3] requirements-dev.txt telepítése ==="
pip install -r requirements-dev.txt

echo ""
echo "=== Kész ==="
echo "which python: $(which python)"
echo "which pip:    $(which pip)"
echo ""
echo "Aktiválás egy új terminálban:"
echo "  source ${VENV_DIR}/bin/activate"
echo ""
echo "Kódellenőrzés (Ruff) kézi futtatása:"
echo "  ruff check ."

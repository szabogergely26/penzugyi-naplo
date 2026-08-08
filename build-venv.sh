#!/usr/bin/env bash

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



VENV_DIR=".venv"
PYTHON_BIN="python3"
REQ_FILE="requirements.txt"

echo "==> Ellenőrzés..."

if [ ! -f "${REQ_FILE}" ]; then
    echo "HIBA: ${REQ_FILE} nem található!"
    exit 1
fi

if ! command -v ${PYTHON_BIN} &> /dev/null; then
    echo "HIBA: ${PYTHON_BIN} nincs telepítve!"
    exit 1
fi

echo "==> Virtuális környezet..."

if [ -d "${VENV_DIR}" ]; then
    echo "Meglévő .venv használata"
else
    echo "Új .venv létrehozása"
    ${PYTHON_BIN} -m venv "${VENV_DIR}"
fi

echo "==> pip frissítése"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip

echo "==> Függőségek telepítése"
"${VENV_DIR}/bin/pip" install -r "${REQ_FILE}"

echo "==> Gyors ellenőrzés (PySide6)"
"${VENV_DIR}/bin/python" -c "import PySide6; print('PySide6 OK:', PySide6.__version__)"

echo
echo "Kész."
echo "Aktiválás:"
echo "source ${VENV_DIR}/bin/activate"

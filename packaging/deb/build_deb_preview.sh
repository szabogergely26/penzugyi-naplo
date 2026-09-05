#!/usr/bin/env bash
set -euo pipefail

# A stabil build_deb.sh testvér-szkriptje: ez a Preview csomagot építi.
# Külön csomagnév (penzugyi-naplo-preview), külön telepítési útvonal,
# külön parancs és külön ikon -- így a stabil "penzugyi-naplo" mellett,
# azzal egy időben is telepítve maradhat, nem írja felül.

APP_NAME="penzugyi-naplo-preview"
ARCH="all"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"

CONTROL_TEMPLATE="$ROOT_DIR/packaging/deb/control-preview.in"
DESKTOP_FILE="$ROOT_DIR/packaging/deb/penzugyi-naplo-preview.desktop"
APT_SOURCE_FILE="$ROOT_DIR/packaging/apt/penzugyi-naplo-preview.sources"
APT_KEYRING_FILE="$ROOT_DIR/packaging/apt/penzugyi-naplo-preview-archive-keyring.gpg"

VERSION="$(
  PYTHONPATH="$ROOT_DIR" python3 - <<'PY'
from penzugyi_naplo.app_version import APP_VERSION
print(APP_VERSION)
PY
)"

PKG_DIR="$BUILD_DIR/${APP_NAME}_${VERSION}_${ARCH}"

# A végleges kimeneti .deb fájl -- fix nevű, verziószám nélkül.
DEB_FILE="$BUILD_DIR/${APP_NAME}.deb"

echo "==> Root: $ROOT_DIR"
echo "==> Version: $VERSION"
echo "==> Package dir: $PKG_DIR"
echo "==> Output deb: $DEB_FILE"

if [ ! -f "$CONTROL_TEMPLATE" ]; then
  echo "HIBA: hiányzik a control sablon: $CONTROL_TEMPLATE" >&2
  exit 1
fi

if [ ! -f "$DESKTOP_FILE" ]; then
  echo "HIBA: hiányzik a desktop fájl: $DESKTOP_FILE" >&2
  exit 1
fi

if [ ! -f "$APT_SOURCE_FILE" ]; then
  echo "HIBA: hiányzik az APT source fájl: $APT_SOURCE_FILE" >&2
  exit 1
fi

if [ ! -f "$APT_KEYRING_FILE" ]; then
  echo "HIBA: hiányzik az APT keyring fájl: $APT_KEYRING_FILE" >&2
  exit 1
fi

rm -rf "$PKG_DIR"

mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/share/$APP_NAME"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/icons/hicolor"
mkdir -p "$PKG_DIR/usr/share/keyrings"
mkdir -p "$PKG_DIR/etc/apt/sources.list.d"

sed "s/@VERSION@/$VERSION/g" "$CONTROL_TEMPLATE" > "$PKG_DIR/DEBIAN/control"

rsync -a \
  --exclude ".git" \
  --exclude ".github" \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude "build" \
  --exclude "dist" \
  --exclude "artifacts" \
  --exclude "*.db" \
  --exclude "*.sqlite3" \
  --exclude "*.asc" \
  --exclude "*.gpg" \
  --exclude "data" \
  --exclude "packaging" \
  "$ROOT_DIR/" "$PKG_DIR/usr/share/$APP_NAME/"

cp "$DESKTOP_FILE" "$PKG_DIR/usr/share/applications/penzugyi-naplo-preview.desktop"

# Statikus alkalmazás-assetek explicit másolása.
mkdir -p "$PKG_DIR/usr/share/$APP_NAME/assets"
cp -a "$ROOT_DIR/assets/." \
      "$PKG_DIR/usr/share/$APP_NAME/assets/"

# KDE / hicolor alkalmazásikonok (penzugyi-naplo-preview.png minden méretben).
#
# FONTOS: a packaging/icons/hicolor/ mappa MINDKÉT ikonkészletet tartalmazza,
# egymás mellett, méretenkénti almappákban (penzugyi-naplo.png a stabil,
# penzugyi-naplo-preview.png a preview csomaghoz). A --exclude nélkül a
# sima rsync a stabil "penzugyi-naplo.png" fájlokat is bemásolná ide -
# ez okozott egy éles dpkg-ütközést telepítéskor ("trying to overwrite
# .../penzugyi-naplo.png, which is also in package penzugyi-naplo"),
# mert mindkét csomag ugyanazt a fájlnevet próbálta a rendszerre tenni.
# A --exclude biztosítja, hogy csak a preview-specifikus ikon kerüljön be.
if [ -d "$ROOT_DIR/packaging/icons/hicolor" ]; then
  rsync -a \
    --exclude "penzugyi-naplo.png" \
    "$ROOT_DIR/packaging/icons/hicolor/" "$PKG_DIR/usr/share/icons/hicolor/"
fi

# Preview APT szoftverforrás és publikus keyring -- saját fájlnéven,
# hogy ne ütközzön a stabil csomag azonos célú fájljaival.
cp "$APT_SOURCE_FILE" "$PKG_DIR/etc/apt/sources.list.d/penzugyi-naplo-preview.sources"
cp "$APT_KEYRING_FILE" "$PKG_DIR/usr/share/keyrings/penzugyi-naplo-preview-archive-keyring.gpg"

# Futásidejű (ablak/tálca) ikon cseréje a csomagolt másolatban Preview
# ikonra, hogy a két alkalmazás futás közben is megkülönböztethető legyen.
if [ -f "$ROOT_DIR/icons/app_icon_preview.png" ]; then
  cp "$ROOT_DIR/icons/app_icon_preview.png" "$PKG_DIR/usr/share/$APP_NAME/icons/app_icon.png"
fi

cat > "$PKG_DIR/usr/bin/penzugyi-naplo-preview" <<EOF_BIN
#!/usr/bin/env bash
cd /usr/share/$APP_NAME
exec python3 main.py
EOF_BIN

chmod +x "$PKG_DIR/usr/bin/penzugyi-naplo-preview"

find "$PKG_DIR" -type d -exec chmod 755 {} \;
find "$PKG_DIR" -type f -exec chmod 644 {} \;
chmod 755 "$PKG_DIR/DEBIAN"
chmod 644 "$PKG_DIR/DEBIAN/control"
chmod +x "$PKG_DIR/usr/bin/penzugyi-naplo-preview"

# --- Build-időbeli önellenőrzés: nincs-e "idegen" (nem preview-specifikus)
# fájl a becsomagolt hicolor-ikonok között? ---
#
# Ez pontosan azt a hibaosztályt kapja el, ami korábban csak TELEPÍTÉSKOR,
# egy kriptikus dpkg-ütközéssel derült ki ("trying to overwrite .../
# penzugyi-naplo.png, which is also in package penzugyi-naplo") - hetekkel/
# hónapokkal a tényleges build után, amikor valaki (vagy egy git merge)
# újra bemásolt egy nem preview-specifikus fájlt a packaging/icons/hicolor/
# forrás-mappába.
#
# Ha ez a build lépés innentől kudarcot vall (exit 1), az EGÉSZ workflow
# pirosra vált a GitHub Actions felületén - ez azért fontos, mert
# egy build-időben KIÍRT, de a buildet nem megállító figyelmeztetés
# (sima echo) csak akkor látszana, ha valaki külön rákattint a futásra és
# kinyitja ezt a konkrét lépést. Egy piros X viszont már a futáslistán,
# rákattintás nélkül is azonnal látszik.
HICOLOR_DEST="$PKG_DIR/usr/share/icons/hicolor"

if [ -d "$HICOLOR_DEST" ]; then
  UNEXPECTED_ICONS="$(find "$HICOLOR_DEST" -type f -name "*.png" ! -name "*-preview.png")"

  if [ -n "$UNEXPECTED_ICONS" ]; then
    echo "HIBA: a Preview csomagba nem preview-specifikus ikonfájl(ok) kerültek be:" >&2
    echo "$UNEXPECTED_ICONS" >&2
    echo "" >&2
    echo "Ezek valószínűleg a stabil csomag ikonjai, amik ütköznének" >&2
    echo "telepítéskor a 'penzugyi-naplo' csomaggal. Ellenőrizd a" >&2
    echo "packaging/icons/hicolor/ forrás-mappa tartalmát: minden ott" >&2
    echo "lévő .png fájlnak *-preview.png végződésűnek kell lennie," >&2
    echo "vagy a fenti rsync --exclude listát kell bővíteni." >&2
    exit 1
  fi
fi

dpkg-deb --root-owner-group -Zgzip --build "$PKG_DIR" "$DEB_FILE"

echo "==> Built: $DEB_FILE"

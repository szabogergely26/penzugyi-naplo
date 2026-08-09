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

rm -rf "$PKG_DIR"

mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/share/$APP_NAME"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/icons/hicolor"

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
if [ -d "$ROOT_DIR/packaging/icons/hicolor" ]; then
  rsync -a "$ROOT_DIR/packaging/icons/hicolor/" "$PKG_DIR/usr/share/icons/hicolor/"
fi

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

dpkg-deb --root-owner-group -Zgzip --build "$PKG_DIR" "$DEB_FILE"

echo "==> Built: $DEB_FILE"

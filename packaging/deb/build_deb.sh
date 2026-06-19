#!/usr/bin/env bash
set -euo pipefail

APP_NAME="penzugyi-naplo"
ARCH="all"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"

CONTROL_TEMPLATE="$ROOT_DIR/packaging/deb/control.in"
DESKTOP_FILE="$ROOT_DIR/packaging/deb/penzugyi-naplo.desktop"
APT_SOURCE_FILE="$ROOT_DIR/packaging/apt/penzugyi-naplo.sources"
APT_KEYRING_FILE="$ROOT_DIR/packaging/apt/penzugyi-naplo-archive-keyring.gpg"

VERSION="$(
  PYTHONPATH="$ROOT_DIR" python3 - <<'PY'
from penzugyi_naplo.app_version import APP_VERSION
print(APP_VERSION)
PY
)"

PKG_DIR="$BUILD_DIR/${APP_NAME}_${VERSION}_${ARCH}"
DEB_FILE="$BUILD_DIR/${APP_NAME}_${VERSION}_${ARCH}.deb"

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

cp "$DESKTOP_FILE" "$PKG_DIR/usr/share/applications/penzugyi-naplo.desktop"

# Statikus alkalmazás-assetek explicit másolása.
mkdir -p "$PKG_DIR/usr/share/$APP_NAME/assets"
cp -a "$ROOT_DIR/assets/." \
      "$PKG_DIR/usr/share/$APP_NAME/assets/"

# KDE / hicolor alkalmazásikonok.
if [ -d "$ROOT_DIR/packaging/icons/hicolor" ]; then
  rsync -a "$ROOT_DIR/packaging/icons/hicolor/" "$PKG_DIR/usr/share/icons/hicolor/"
fi

# Stable APT szoftverforrás és publikus keyring.
cp "$APT_SOURCE_FILE" "$PKG_DIR/etc/apt/sources.list.d/penzugyi-naplo.sources"
cp "$APT_KEYRING_FILE" "$PKG_DIR/usr/share/keyrings/penzugyi-naplo-stable-archive-keyring.gpg"

cat > "$PKG_DIR/usr/bin/penzugyi-naplo" <<EOF_BIN
#!/usr/bin/env bash
cd /usr/share/$APP_NAME
exec python3 main.py
EOF_BIN

chmod +x "$PKG_DIR/usr/bin/penzugyi-naplo"

find "$PKG_DIR" -type d -exec chmod 755 {} \;
find "$PKG_DIR" -type f -exec chmod 644 {} \;
chmod 755 "$PKG_DIR/DEBIAN"
chmod 644 "$PKG_DIR/DEBIAN/control"
chmod +x "$PKG_DIR/usr/bin/penzugyi-naplo"

dpkg-deb --root-owner-group --build "$PKG_DIR" "$DEB_FILE"

echo "==> Built: $DEB_FILE"

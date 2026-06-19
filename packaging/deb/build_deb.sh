#!/usr/bin/env bash
set -euo pipefail

APP_NAME="penzugyi-naplo-preview"
ARCH="all"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"
BIN_NAME="penzugyi-naplo-preview"
ICON_NAME="penzugyi-naplo-preview"

# Csomagolási bemeneti fájlok:
CONTROL_TEMPLATE="$ROOT_DIR/packaging/deb/control.in"
DESKTOP_FILE="$ROOT_DIR/packaging/deb/penzugyi-naplo-preview.desktop"

APT_KEYRING_FILE="$ROOT_DIR/packaging/apt/penzugyi-naplo-archive-keyring.gpg"
APT_SOURCES_FILE="$ROOT_DIR/packaging/apt/penzugyi-naplo-preview.sources"
APT_PREFERENCES_FILE="$ROOT_DIR/packaging/apt/penzugyi-naplo-preview.pref"

VERSION="$(
  PYTHONPATH="$ROOT_DIR" python3 - <<'PY'
from penzugyi_naplo.app_version import APP_VERSION
print(APP_VERSION)
PY
)"

DESKTOP_NAME="Pénzügyi Napló (Előzetes)"
DESKTOP_GENERIC_NAME="Pénzügyi napló előzetes alkalmazás"
DESKTOP_COMMENT="Helyi adatbázist használó pénzügyi napló bevételek, kiadások, számlák, statisztikák és aranyszámla nyilvántartásához"

if [[ "$VERSION" == *"preview"* || "$VERSION" == *"előzetes"* || "$VERSION" == *"beta"* ]]; then
  DESKTOP_NAME="Pénzügyi Napló (Előzetes)"
  DESKTOP_GENERIC_NAME="Pénzügyi napló alkalmazás – előzetes verzió"
  DESKTOP_COMMENT="Előzetes verzió – helyi adatbázist használó pénzügyi napló bevételek, kiadások, számlák, statisztikák és aranyszámla nyilvántartásához"
fi


PKG_DIR="$BUILD_DIR/${APP_NAME}_${VERSION}_${ARCH}"
DEB_FILE="$BUILD_DIR/${APP_NAME}_${VERSION}_${ARCH}.deb"

echo "==> Root: $ROOT_DIR"
echo "==> Version: $VERSION"
echo "==> Package dir: $PKG_DIR"
echo "==> Output deb: $DEB_FILE"

rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/share/$APP_NAME"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/icons/hicolor"
mkdir -p "$PKG_DIR/usr/share/keyrings"
mkdir -p "$PKG_DIR/etc/apt/sources.list.d"
mkdir -p "$PKG_DIR/etc/apt/preferences.d"

sed \
  -e "s|@PACKAGE_NAME@|$APP_NAME|g" \
  -e "s|@VERSION@|$VERSION|g" \
  "$CONTROL_TEMPLATE" > "$PKG_DIR/DEBIAN/control"

rsync -a \
  --exclude ".git" \
  --exclude ".github" \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude "build" \
  --exclude "artifacts" \
  --exclude "*.db" \
  --exclude "*.sqlite3" \
  --exclude "*.asc" \
  --exclude "data" \
  --exclude ".env" \
  --exclude ".ruff_cache" \
  --exclude ".mypy_cache" \
  --exclude ".pytest_cache" \
  --exclude ".vscode" \
  --exclude "logs" \
  --exclude "Mentes" \
  --exclude "menubejegyzes" \
  --exclude "packaging" \
  --exclude "requirements-dev.txt" \
  --exclude "build-venv.sh" \
  --exclude "venv-How-to.txt" \
  --exclude "*.gpg" \
  "$ROOT_DIR/" "$PKG_DIR/usr/share/$APP_NAME/"

sed \
  -e "s|@DESKTOP_NAME@|$DESKTOP_NAME|g" \
  -e "s|@DESKTOP_GENERIC_NAME@|$DESKTOP_GENERIC_NAME|g" \
  -e "s|@DESKTOP_COMMENT@|$DESKTOP_COMMENT|g" \
  -e "s|@BIN_NAME@|$BIN_NAME|g" \
  -e "s|@ICON_NAME@|$ICON_NAME|g" \
  "$DESKTOP_FILE" > "$PKG_DIR/usr/share/applications/penzugyi-naplo-preview.desktop"


# Statikus alkalmazás-assetek explicit másolása
mkdir -p "$PKG_DIR/usr/share/$APP_NAME/assets"
cp -a "$ROOT_DIR/assets/." \
      "$PKG_DIR/usr/share/$APP_NAME/assets/"

if [ -d "$ROOT_DIR/packaging/icons/hicolor" ]; then
  while IFS= read -r -d '' icon_file; do
    rel_dir="$(dirname "${icon_file#$ROOT_DIR/packaging/icons/hicolor/}")"
    ext="${icon_file##*.}"

    mkdir -p "$PKG_DIR/usr/share/icons/hicolor/$rel_dir"
    cp "$icon_file" "$PKG_DIR/usr/share/icons/hicolor/$rel_dir/$ICON_NAME.$ext"
  done < <(find "$ROOT_DIR/packaging/icons/hicolor" -type f \( -name "*.png" -o -name "*.svg" \) -print0)
fi

# APT szoftverforrás fájlok telepítése a Preview csomaghoz
install -m 644 "$APT_KEYRING_FILE" \
  "$PKG_DIR/usr/share/keyrings/penzugyi-naplo-archive-keyring.gpg"

install -m 644 "$APT_SOURCES_FILE" \
  "$PKG_DIR/etc/apt/sources.list.d/penzugyi-naplo-preview.sources"

install -m 644 "$APT_PREFERENCES_FILE" \
  "$PKG_DIR/etc/apt/preferences.d/penzugyi-naplo-preview.pref"

cat > "$PKG_DIR/usr/bin/penzugyi-naplo-preview" <<EOF
#!/usr/bin/env bash
cd /usr/share/$APP_NAME
exec python3 main.py
EOF

chmod +x "$PKG_DIR/usr/bin/penzugyi-naplo-preview"

find "$PKG_DIR" -type d -exec chmod 755 {} \;
find "$PKG_DIR" -type f -exec chmod 644 {} \;
chmod 755 "$PKG_DIR/DEBIAN"
chmod 644 "$PKG_DIR/DEBIAN/control"
chmod +x "$PKG_DIR/usr/bin/penzugyi-naplo-preview"

dpkg-deb --root-owner-group --build "$PKG_DIR" "$DEB_FILE"

echo "==> Built: $DEB_FILE"

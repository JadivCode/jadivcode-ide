#!/usr/bin/env bash
# JadivCode IDE installer for Linux.
#
#   Install or update:  curl -fsSL https://raw.githubusercontent.com/JadivCode/jadivcode-ide/main/install.sh | bash
#   Uninstall:          bash install.sh --uninstall
#
# Everything goes into your home folder; sudo is never used.
set -euo pipefail

REPO_URL="${JADIVCODE_IDE_REPO:-https://github.com/JadivCode/jadivcode-ide}"
BRANCH="${JADIVCODE_IDE_BRANCH:-main}"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_DIR/jadivcode-ide"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/jadivcode-ide"
DESKTOP_FILE="$DATA_DIR/applications/jadivcode-ide.desktop"

say() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

if [ "${1:-}" = "--uninstall" ]; then
    rm -rf "$APP_DIR"
    rm -f "$LAUNCHER" "$DESKTOP_FILE"
    say "JadivCode IDE was removed."
    exit 0
fi

[ "$(uname -s)" = "Linux" ] || die "JadivCode IDE supports Linux only."
command -v python3 >/dev/null 2>&1 || die "python3 is missing. Install it with: sudo apt install python3"
[ -f "$DATA_DIR/jadivcode/jadivcode/__init__.py" ] || python3 -c 'import jadivcode' >/dev/null 2>&1 \
    || die "Install JadivCode first:
    curl -fsSL https://raw.githubusercontent.com/JadivCode/jadivcode/main/install.sh | bash"

SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/jadivcode_ide/__init__.py" ]; then
    say "Installing from $SCRIPT_DIR"
    SRC="$SCRIPT_DIR"
else
    command -v curl >/dev/null 2>&1 || die "curl is missing. Install it with: sudo apt install curl"
    say "Downloading JadivCode IDE ($BRANCH)..."
    curl -fsSL "$REPO_URL/archive/refs/heads/$BRANCH.tar.gz" -o "$WORK/src.tar.gz" \
        || die "The download failed. Check your internet connection."
    mkdir "$WORK/src"
    tar -xzf "$WORK/src.tar.gz" -C "$WORK/src" --strip-components=1
    SRC="$WORK/src"
    [ -f "$SRC/jadivcode_ide/__init__.py" ] || die "The download does not contain the IDE."
fi

mkdir -p "$BIN_DIR" "$(dirname "$DESKTOP_FILE")"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
cp -r "$SRC/jadivcode_ide" "$SRC/assets" "$APP_DIR/"
[ -f "$SRC/LICENSE" ] && cp "$SRC/LICENSE" "$APP_DIR/LICENSE"
find "$APP_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} +

cat > "$LAUNCHER" <<LAUNCH
#!/bin/sh
PYTHONPATH="$APP_DIR\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m jadivcode_ide "\$@"
LAUNCH
chmod +x "$LAUNCHER"

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=JadivCode IDE
Comment=Write and run JadivCode programs
Exec=$LAUNCHER %f
Icon=$APP_DIR/assets/jadivcode-ide.svg
Terminal=false
Categories=Development;IDE;
MimeType=text/x-jadivcode;
DESKTOP

say ""
say "JadivCode IDE is installed. Start it with: jadivcode-ide"
python3 -c 'import PyQt5.QtWidgets' >/dev/null 2>&1 \
    || say "One more step - install the window toolkit:   sudo apt install python3-pyqt5"

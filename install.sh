#!/usr/bin/env bash
set -e

# ==============================================================================
# Awesome Wallpaper Changer (wchanger) Installer
# Installs wchanger as a system command accessible in /bin or /usr/local/bin
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[i] Installing Awesome Wallpaper Changer (wchanger)..."

# 1. Install package using pip
if command -v pip3 >/dev/null 2>&1; then
    PIP_CMD="pip3"
elif command -v pip >/dev/null 2>&1; then
    PIP_CMD="pip"
else
    PIP_CMD="python3 -m pip"
fi

if [ "$(id -u)" -eq 0 ]; then
    $PIP_CMD install .
else
    # Install for user or current environment
    $PIP_CMD install .
fi

# 2. Locate the installed wchanger executable
WCHANGER_PATH="$(command -v wchanger || true)"
if [ -z "$WCHANGER_PATH" ]; then
    for candidate in "$HOME/.local/bin/wchanger" "/usr/local/bin/wchanger" "/usr/bin/wchanger"; do
        if [ -x "$candidate" ]; then
            WCHANGER_PATH="$candidate"
            break
        fi
    done
fi

if [ -z "$WCHANGER_PATH" ]; then
    echo "[!] Could not automatically locate installed 'wchanger' binary."
    echo "[!] Please ensure ~/.local/bin is in your PATH, or run: sudo ln -sf \$(which wchanger) /bin/wchanger"
    exit 1
fi

echo "[+] Found wchanger executable at: $WCHANGER_PATH"

# 3. Create symlink in /bin so it can be run like a standard system command
TARGET_BIN="/bin/wchanger"
if [ "$WCHANGER_PATH" != "$TARGET_BIN" ]; then
    if [ -w /bin ] || [ "$(id -u)" -eq 0 ]; then
        ln -sf "$WCHANGER_PATH" "$TARGET_BIN"
        echo "[+] Successfully linked: $TARGET_BIN -> $WCHANGER_PATH"
    elif command -v sudo >/dev/null 2>&1; then
        echo "[i] Requesting sudo permissions to link into /bin..."
        sudo ln -sf "$WCHANGER_PATH" "$TARGET_BIN"
        echo "[+] Successfully linked: $TARGET_BIN -> $WCHANGER_PATH"
    else
        echo "[!] Notice: Write permissions for /bin not available without sudo."
        echo "[!] You can manually link it by running: sudo ln -sf $WCHANGER_PATH $TARGET_BIN"
    fi
fi

echo ""
echo "=========================================================================="
echo "[+] Awesome Wallpaper Changer is ready!"
echo "[+] Run it anytime simply with: wchanger"
echo "=========================================================================="

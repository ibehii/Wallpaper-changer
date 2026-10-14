# 🌊 Anahita Wallpaper Changer GNOME Extension

A high-performance, non-blocking GNOME Shell Extension companion for **Anahita Wallpaper Changer (`wchanger`)**.

---

## ✨ Features

- **⏮ Previous Wallpaper (Back)**: Move backward through your recent wallpaper history without re-downloading or re-scanning.
- **⏭ Next Wallpaper**: Trigger immediate wallpaper rotation or step forward in history.
- **⭐ Add to Favorites**: One-click bookmarking of your current desktop wallpaper into `~/Pictures/Wallpapers/Favorites/` with instant desktop notification.
- **🌐 Online Provider Quick-Switch**: Rotate on demand directly from **Wallhaven**, **Bing Daily**, **Lorem Picsum**, or **LoremFlickr**.
- **🖥️ Multi-Monitor Support**: Native trigger for multi-display spanning.
- **🔄 Service Controller**: Real-time switch to start/stop the `wallpaper-changer.service` background daemon.
- **⚙️ Shell Indicator Toggle**: Choose whether to display the icon in the top panel bar or manage via background hotkeys in the extension preferences.

---

## 💻 Compatibility

- **GNOME Shell**: 45, 46, 47, 48, 49, 50, 51+ (Ubuntu 23.10+, Fedora 39+, Debian 13+, Arch, openSUSE).
- **Session**: Both **Wayland** and **X11**.

---

## 🚀 Installation

### Option 1: Via Repository Makefile (Recommended)

From the root of the `Wallpaper-changer` repository:

```bash
make install-extension
```

Then enable the extension:
```bash
gnome-extensions enable wchanger@ibehii.github.com
```

### Option 2: Manual Installation

```bash
EXT_DIR="$HOME/.local/share/gnome-shell/extensions/wchanger@ibehii.github.com"
mkdir -p "$EXT_DIR"
cp -r metadata.json extension.js prefs.js stylesheet.css schemas "$EXT_DIR/"
glib-compile-schemas "$EXT_DIR/schemas"
gnome-extensions enable wchanger@ibehii.github.com
```

*Note: On Wayland, log out and log back in (or restart GNOME) to load freshly installed extensions.*

---

## ⚙️ Configuration & Preferences

Open preferences via the panel menu or terminal:

```bash
gnome-extensions prefs wchanger@ibehii.github.com
```

- **Show Indicator in Top Bar**: Toggle visibility in GNOME top bar.
- **Favorites Folder Path**: Customize destination directory for saved wallpapers.
- **Default Online Provider**: Select default image curation provider.
- **Multi-Monitor Spanning**: Enable `-m` spanning mode by default.

---

## 📦 Packaging

To bundle the extension for [extensions.gnome.org](https://extensions.gnome.org):

```bash
make pack-extension
```
This produces `dist/wchanger@ibehii.github.com.shell-extension.zip`.

# Anahita Wallpaper Changer GNOME Extension

GNOME Shell extension for [Anahita Wallpaper Changer (`wchanger`)](https://github.com/ibehii/Wallpaper-changer).

## Features

- Previous / Next wallpaper history navigation
- Local folder rotation (`~/Pictures/Wallpapers` or custom path) with subfolder scanning
- Online providers via D-Bus (`io.github.ibehii.Wchanger`): Wallhaven, Unsplash, Bing Daily, Lorem Picsum, LoremFlickr
- Multi-monitor wallpaper assignment
- Favorites folder (`~/Pictures/Wallpapers/Favorites`)
- Background rotation timer and `wallpaper-changer.service` D-Bus toggle

## Installation

Install the Python backend, D-Bus activation service, and GNOME Shell extension:

```bash
pip install .
wchanger --install-dbus
make install-extension
gnome-extensions enable wchanger@ibehii.github.com
```

On Wayland, log out and log back in to load the extension.

## Preferences

```bash
gnome-extensions prefs wchanger@ibehii.github.com
```

## Packaging

```bash
make pack-extension
```

Outputs `dist/wchanger@ibehii.github.com.shell-extension.zip`.

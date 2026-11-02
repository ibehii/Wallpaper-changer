<div align="center">

<p align="center">
  <img src="photos/anahita_banner.png" width="640" alt="Anahita Wallpaper Changer Banner" />
</p>

# Anahita Wallpaper Changer (`wchanger`)

**A lightweight, zero-dependency wallpaper rotation daemon and CLI for Linux.**  
Supports multi-monitor independent wallpapers, curated online photo streams, systemd user services, and a companion GNOME Shell extension.

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-FCC624?style=flat-square&logo=linux&logoColor=black)](https://www.kernel.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square&logo=open-source-initiative&logoColor=white)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-244%20Passing-brightgreen?style=flat-square&logo=pytest&logoColor=white)](tests/)
[![GNOME Shell](https://img.shields.io/badge/GNOME%20Shell-45--48-blueviolet?style=flat-square&logo=gnome&logoColor=white)](extension/)

<br/>

<p align="center">
  <img src="photos/wallpaer1.png" width="31%" alt="Sample Wallpaper 1" />
  <img src="photos/wallpaer2.jpg" width="31%" alt="Sample Wallpaper 2" />
  <img src="photos/wallpaer3.jpg" width="31%" alt="Sample Wallpaper 3" />
</p>

</div>

---

## Table of Contents

- [Why wchanger?](#why-wchanger)
- [Quick Start](#quick-start)
- [Supported Desktops & Prerequisites](#supported-desktops--prerequisites)
- [Installation](#installation)
- [Tutorial 1: Local Wallpaper Folders](#tutorial-1-local-wallpaper-folders)
- [Tutorial 2: Multi-Monitor Setups](#tutorial-2-multi-monitor-setups)
- [Tutorial 3: Online Wallpaper Providers](#tutorial-3-online-wallpaper-providers)
  - [Unsplash Setup (API Key & Categories)](#unsplash-setup-api-key--categories)
  - [Wallhaven Toplists & Topics](#wallhaven-toplists--topics)
  - [Cache Management & Prefetching](#cache-management--prefetching)
- [Tutorial 4: Background Service & Login Autostart](#tutorial-4-background-service--login-autostart)
- [Tutorial 5: GNOME Shell Companion Extension](#tutorial-5-gnome-shell-companion-extension)
- [Configuration Reference (`config.toml`)](#configuration-reference-configtoml)
- [CLI Reference](#cli-reference)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [Development & Contributing](#development--contributing)
- [License](#license)

---

## Why wchanger?

Most wallpaper rotators for Linux either depend on heavy GUI runtimes, support only a single desktop environment, or duplicate the same image across multiple monitors.

`wchanger` addresses these limitations:

- **Native Desktop Integration:** Communicates directly with desktop configuration systems (`gsettings`, `qdbus`, `xfconf-query`, `pcmanfm-qt`) without requiring third-party root daemons.
- **True Multi-Monitor Support:** Displays distinct, non-duplicate images on each screen using native screen containments or high-resolution canvas stitching with Pillow.
- **Curated Online Streaming:** Fetches high-resolution images from Unsplash, Wallhaven, Bing Daily, Picsum, and LoremFlickr with automatic cache pruning.
- **Unprivileged Autostart:** Installs as a systemd user service (`systemctl --user`), running entirely within your session without root privileges.
- **Zero Configuration Necessary:** Works immediately out of the box with auto-detected desktops, while allowing full customization via `config.toml` or CLI flags.

---

## Quick Start

Get wallpaper rotation running in under 60 seconds:

### 1. Install `wchanger`

```bash
# Clone the repository
git clone https://github.com/ibehii/Wallpaper-changer.git
cd Wallpaper-changer

# Install to your user environment
pip install --user .
```

Ensure `~/.local/bin` is in your `PATH` (typically default on modern distributions).

### 2. Set Your First Wallpaper

```bash
# Rotate through bundled wallpapers once and exit
wchanger --no-repetition
```

### 3. Start Rotating a Local Folder

```bash
# Rotate images from ~/Pictures/Wallpapers every 10 minutes in the background
wchanger -p 10m -s -b ~/Pictures/Wallpapers
```

### 4. Or Stream Online Wallpapers

```bash
# Stream fresh nature wallpapers from Wallhaven every 15 minutes
wchanger --online wallhaven -C nature -p 15m -b
```

---

## Supported Desktops & Prerequisites

`wchanger` auto-detects your active desktop session. You can also override detection manually using CLI flags (`--gnome`, `--kde`, etc.).

| Desktop Environment | Supported Versions | Session Type | Backend Tool | Multi-Monitor Method |
| :--- | :--- | :--- | :--- | :--- |
| **GNOME** | 3.38 – 48+ | Wayland / X11 | `gsettings` (`org.gnome.desktop.background`) | High-res Spanned Canvas |
| **KDE Plasma** | 5.x & 6.x | Wayland / X11 | `qdbus` / `qdbus6` (`org.kde.PlasmaShell`) | Native screen containment |
| **Cinnamon** | 4.x – 6.x+ | X11 / Wayland | `gsettings` (`org.cinnamon.desktop.background`) | High-res Spanned Canvas |
| **XFCE** | 4.14 – 4.20+ | X11 | `xfconf-query` (`xfce4-desktop`) | Native per-monitor property |
| **MATE** | 1.24 – 1.28+ | X11 | `gsettings` (`org.mate.background`) | High-res Spanned Canvas |
| **LXQt** | 0.16 – 2.1+ | X11 / Wayland | `pcmanfm-qt` (`--set-wallpaper`) | Native multi-screen config |

### Package Requirements

The core CLI relies only on Python 3.8+ and system tools already present on most distributions:

```bash
# Debian / Ubuntu / Linux Mint
sudo apt install python3-pip python3-pil libglib2.0-bin x11-xserver-utils

# Fedora / RHEL
sudo dnf install python3-pip python3-pillow glib2 xrandr

# Arch Linux / Manjaro
sudo pacman -S python-pip python-pillow glib2 xorg-xrandr
```

> [!NOTE]
> For KDE Plasma, ensure `qdbus` (or `qdbus6` / `qt6-tools`) is installed. For XFCE, ensure `xfconf` is installed.

---

## Installation

Choose the installation method that fits your workflow:

### Option 1: User Install via Pip / Pipx (Recommended)

Installing to user space avoids modifying system files and complies with PEP 668:

```bash
git clone https://github.com/ibehii/Wallpaper-changer.git
cd Wallpaper-changer

# Install to ~/.local/bin
pip install --user .
```

### Option 2: System-Wide Binary (`/bin/wchanger`)

To install system-wide so all users have access:

```bash
sudo ./install.sh
# or
sudo make install-bin
```

### Option 3: Run Directly from Source

You can run `wchanger` directly without installing:

```bash
python3 wchanger.py ~/Pictures/Wallpapers
```

---

## Tutorial 1: Local Wallpaper Folders

Learn how to control rotation interval, image order, subfolder discovery, and desktop themes when cycling local wallpaper collections.

### Step 1: Run with Default Settings

Pass a directory containing images (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`):

```bash
wchanger ~/Pictures/Wallpapers
```

By default, `wchanger` cycles through files alphabetically, changes the wallpaper every 60 seconds, and repeats indefinitely.

### Step 2: Configure Rotation Intervals

Use `-p` or `--pause` to specify the delay. You can provide integers (seconds) or human-readable time strings:

```bash
# 30 seconds
wchanger -p 30s ~/Pictures/Wallpapers

# 15 minutes
wchanger -p 15m ~/Pictures/Wallpapers

# 2 hours
wchanger -p 2h ~/Pictures/Wallpapers
```

### Step 3: Randomize and Scan Subfolders

- Use `-s` / `--shuffle` to randomize the playlist order.
- Use `-R` / `--recursive` to find images located inside nested subfolders.

```bash
wchanger -s -R -p 10m ~/Pictures/Wallpapers
```

### Step 4: Single-Pass Mode

To apply a random wallpaper once (e.g. from a script or keyboard shortcut) without running a background loop, use `-nr` / `--no-repetition`:

```bash
wchanger -s -nr ~/Pictures/Wallpapers
```

### Step 5: Light & Dark Theme Synchronization (GNOME 42+)

GNOME maintains separate wallpaper keys for light and dark modes. By default, `wchanger` updates both keys simultaneously. You can target a specific theme with `-t` / `--theme`:

```bash
# Update dark mode wallpaper only
wchanger -t dark ~/Pictures/Wallpapers/Dark

# Update light mode wallpaper only
wchanger -t light ~/Pictures/Wallpapers/Light
```

---

## Tutorial 2: Multi-Monitor Setups

Configure `wchanger` to display independent, non-repeating wallpapers across all connected screens.

### Step 1: Enable Multi-Monitor Mode

Add the `-m` (or `--multi-monitor`) flag to any rotation command:

```bash
wchanger -m -s -p 15m ~/Pictures/Wallpapers
```

When multi-monitor mode is active, `wchanger` detects connected displays and picks a unique image for each screen simultaneously.

### Step 2: How Multi-Monitor Rendering Works

Different desktop environments handle multi-monitor wallpapers differently:

```text
  ┌────────────────────────────────┐    ┌────────────────────────────┐
  │           Monitor 1            │    │           Monitor 2            │
  │        (e.g. 2560x1440)        │    │        (e.g. 1920x1080)        │
  │                                │    │                            │
  │     [ Mountain Landscape ]     │    │     [ Deep Space Nebula ]  │
  └────────────────────────────────┘    └────────────────────────────┘
```

1. **Native Per-Monitor Assignment (KDE Plasma & XFCE):**
   `wchanger` queries desktop containments (`desktop[0]`, `desktop[1]` in Plasma; `monitor0`, `monitor1` in XFCE) and sets wallpapers on each display independently using native APIs.
2. **Virtual Composite Canvas (GNOME, Cinnamon, MATE, LXQt):**
   These desktop environments expose only a single global wallpaper property. To achieve distinct wallpapers per monitor:
   - `wchanger` queries monitor geometry via `xrandr` or display metrics.
   - It crops and fits each image to match the exact resolution and aspect ratio of its assigned monitor using Pillow.
   - It stitches the images side-by-side into a single wide composite canvas.
   - It sets the desktop background mode to `spanned`.
3. **Cache Invalidation:**
   `wchanger` alternates output filenames (`multimonitor_spanned_0.png` and `multimonitor_spanned_1.png`) on every rotation to ensure desktop background managers detect the file change immediately.

---

## Tutorial 3: Online Wallpaper Providers

Stream curated photography directly from online platforms without manually downloading files.

Supported providers:

| Provider Key | Name | Authentication | Best For |
| :--- | :--- | :--- | :--- |
| `unsplash` | **Unsplash** | Personal API Access Key (Free) | High-resolution curated photography & topics |
| `wallhaven` | **Wallhaven** | None required | Desktop wallpapers, anime, digital art, 4K |
| `bing` | **Bing Daily** | None required | Microsoft's daily curated nature photograph |
| `picsum` | **Lorem Picsum** | None required | Random photography with minimal overhead |
| `loremflickr` | **LoremFlickr** | None required | Random creative commons photography |

---

<a id="unsplash-setup-guide"></a>
### Unsplash Setup (API Key & Categories)

To comply with Unsplash API terms and prevent shared rate-limit throttling, `wchanger` requires you to use your own personal Unsplash Access Key. A free personal developer account provides 50 requests per hour, which is ample for desktop wallpaper rotation.

> [!IMPORTANT]
> `wchanger` never includes hardcoded API credentials. You maintain full control over your credentials and rate limits.

#### Step 1: Obtain a Free Unsplash Access Key (1–2 Minutes)

1. Go to the [Unsplash Developer Portal](https://unsplash.com/developers) and create a free account.
2. Navigate to **Your Apps** → **New Application**.
3. Accept the API Terms and Guidelines.
4. Enter an application name (e.g. `My Linux Wallpaper Changer`) and a short description.
5. Click **Create Application**.
6. Scroll down to the **Keys** section and copy your **Access Key** (Client ID).

#### Step 2: Configure Your Access Key

Choose whichever method best fits your environment:

- **Method A: Configuration File (Recommended)**  
  Add your key to `~/.config/wchanger/config.toml`:
  ```toml
  source = "unsplash"
  unsplash_access_key = "YOUR_ACCESS_KEY_HERE"
  ```

- **Method B: Environment Variable**  
  Add to `~/.bashrc` or `~/.zshrc`:
  ```bash
  export UNSPLASH_ACCESS_KEY="YOUR_ACCESS_KEY_HERE"
  ```

- **Method C: Interactive Terminal Prompt**  
  Run `wchanger --online unsplash`. If no key is configured, `wchanger` prompts for your key and offers to save it to `config.toml` automatically.

- **Method D: CLI Flag**  
  ```bash
  wchanger --online unsplash --unsplash-key "YOUR_ACCESS_KEY_HERE"
  ```

- **Method E: GNOME Extension Preferences UI**  
  Open extension preferences, select Unsplash as the source, and paste your key into the text field.

#### Step 3: Filter by Unsplash Categories & Topics

Use `-C` / `--category` to filter photos by subject:

```bash
# Rotate nature photos every 15 minutes
wchanger --online unsplash -C nature -p 15m -b

# Stream architecture photos
wchanger --online unsplash -C architecture -p 30m -b
```

Supported Unsplash category presets:

| Category Key | Topic | Content Description |
| :--- | :--- | :--- |
| `nature` | Nature & Landscapes | Mountains, forests, oceans, and skies |
| `wallpapers` | Wallpapers | Compositions optimized for desktop screens |
| `travel` | Travel & Destinations | Scenic landmarks, culture, and outdoor journeys |
| `architecture` | Architecture & Design | Modern buildings, interiors, and minimalist structures |
| `space` | Space & Astronomy | Nebulas, galaxies, planets, and starry night skies |
| `minimalism` | Minimalist Photography | Clean lines, open space, and simple subjects |
| `animals` | Animals & Wildlife | Wildlife, pets, and fauna |
| `textures` | Textures & Patterns | Natural and geometric textures |
| `city` | Street & Urban | Skylines, city streets, and night photography |
| `technology` | Technology | Modern hardware, code, and futuristic tech |
| `all` | Unfiltered Stream | Random high-resolution photography |

---

### Wallhaven Toplists & Topics

Stream top-rated community wallpapers from Wallhaven without authentication:

```bash
# Stream Wallhaven's top-rated wallpapers
wchanger --online wallhaven -p 10m -b

# Stream wallpapers filtered by category keyword
wchanger --online wallhaven -C anime -p 10m -b
wchanger --online wallhaven -C cyberpunk -p 10m -b
wchanger --online wallhaven -C space -p 10m -b
```

---

### Cache Management & Prefetching

Downloaded online wallpapers are stored in `~/.cache/wchanger/`.

- **Automatic Cache Cleanup (`--keep-last`):**  
  `wchanger` automatically prunes older downloads to keep disk usage bounded. By default, it preserves the 20 most recent images.
  ```bash
  # Keep only the last 10 images
  wchanger --online unsplash --keep-last 10
  ```

- **Background Prefetching (`--prefetch`):**  
  When running continuous online rotation, `wchanger` downloads the upcoming image in a background thread while you enjoy the current wallpaper. When the timer expires, the transition occurs instantly without network wait time.
  ```bash
  wchanger --online unsplash -p 5m --prefetch -b
  ```

---

## Tutorial 4: Background Service & Login Autostart

Set up `wchanger` to start automatically when you log in, running silently as a background service.

### Step 1: Run the Interactive Setup Wizard

```bash
wchanger --install-autostart
```

The wizard prompts you for your preferred rotation interval and wallpaper source:

```text
============================================
  Automatic Startup Service Setup Wizard   
============================================

[+] Enter pause duration between changing wallpapers [60]: 10m
[+] Enter path to directory or online provider: unsplash
[i] Generated user systemd service definition:
    Target:  ~/.config/systemd/user/wallpaper-changer.service
    Command: /usr/bin/python3 /bin/wchanger -p 600 -o log --online unsplash

[+] Successfully installed and activated 'wallpaper-changer.service'!
[+] The service will now run automatically on login without requiring root/sudo.
```

### Step 2: Managing the User Service

Because `wchanger` uses systemd user services, all commands use `systemctl --user` without `sudo`:

```bash
# Check service status
systemctl --user status wallpaper-changer.service

# Stop the service
systemctl --user stop wallpaper-changer.service

# Restart the service
systemctl --user restart wallpaper-changer.service

# Disable starting on login
systemctl --user disable wallpaper-changer.service

# View live service logs
journalctl --user -u wallpaper-changer.service -f
```

### Step 3: Standalone Background Process (`-b`)

If you prefer not to use systemd, run `wchanger` as a detached daemon process using `-b` / `--run-background`:

```bash
wchanger -p 15m -s -b ~/Pictures/Wallpapers
```

The command detaches from your terminal session and writes logs to `info.log`.

---

## Tutorial 5: GNOME Shell Companion Extension

If you use GNOME Shell (versions 45 through 48), the bundled extension allows you to control wallpaper rotation directly from your desktop top bar.

### Step 1: Install and Compile the Extension

```bash
cd Wallpaper-changer
make install-extension
```

This installs the extension files to `~/.local/share/gnome-shell/extensions/wchanger@ibehii.github.com` and compiles the GSettings schema.

### Step 2: Restart GNOME Shell & Enable

- **On Wayland:** Log out and log back in.
- **On X11:** Press `Alt + F2`, type `r`, and press `Enter`.

Enable the extension:

```bash
gnome-extensions enable wchanger@ibehii.github.com
```

### Step 3: Top Bar Indicator Controls

A wallpaper icon appears in your top panel with the following features:

- **Next / Previous:** Manually trigger wallpaper changes with one click.
- **Pause / Resume:** Temporarily pause automatic rotation.
- **Source Switcher:** Switch between local folders and online providers (`Wallhaven`, `Unsplash`, `Bing`, `Picsum`, `LoremFlickr`).
- **Dynamic Category Submenu:** When Unsplash or Wallhaven is active, an interactive category menu appears with checkmarks to switch topics on the fly.
- **Settings & Help:** Direct access to extension preferences and setup documentation.

### Step 4: Configure Extension Preferences

Open the graphical preferences window:

```bash
gnome-extensions prefs wchanger@ibehii.github.com
```

From the settings dialog, you can configure your wallpaper directory, rotation interval, Unsplash API Access Key, and default categories.

---

## Configuration Reference (`config.toml`)

Instead of typing command-line flags every time, you can define your default preferences in a TOML configuration file.

### File Search Locations

`wchanger` checks for `config.toml` in the following order:

1. Path specified by `--config <path>`
2. Current working directory (`./config.toml`)
3. User configuration directory (`~/.config/wchanger/config.toml`)
4. System-wide configuration (`/etc/wchanger/config.toml`)

### Example `config.toml`

```toml
# Default wallpaper folder for local mode
folder = "~/Pictures/Wallpapers"

# Target desktop: "auto", "gnome", "cinnamon", "kde", "xfce", "mate", or "lxqt"
desktop = "auto"

# Pause duration (accepts integer seconds or human units like "30s", "10m", "1h")
pause = "10m"

# Wallpaper source: "folder", "wallhaven", "unsplash", "bing", "picsum", "loremflickr"
source = "unsplash"

# Unsplash API Access Key (required when source = "unsplash")
unsplash_access_key = "YOUR_PERSONAL_ACCESS_KEY"

# Category filter for Wallhaven or Unsplash (e.g. nature, space, architecture)
category = "nature"

# Randomize image selection order
shuffle = true

# Recursively scan subdirectories for images
recursive = false

# Enable independent wallpapers per monitor
multi_monitor = true

# Maximum number of downloaded online wallpapers to retain in cache
keep_last = 20

# Loop continuously (true) or exit after one pass (false)
repetition = true

# GNOME theme target: "both", "dark", or "light"
theme = "both"

# Output mode: "console" (terminal text) or "log" (info.log file)
output = "console"

# Run in background detached from terminal
run_background = false
```

### Precedence Order

When the same setting is configured in multiple places, `wchanger` resolves values in the following order of priority:

$$\text{CLI Flag} > \text{Environment Variable} > \text{config.toml} > \text{Default Value}$$

Use the `--no-config` flag to bypass `config.toml` and run purely with CLI flags.

---

## CLI Reference

```text
Usage: wchanger [OPTIONS] [PHOTO_PATH]
```

### Options Table

| Option | Short | Type | Default | Description |
| :--- | :---: | :---: | :---: | :--- |
| `--pause` | `-p` | Duration | `60` | Rotation interval (`30s`, `10m`, `1h`, or raw seconds). |
| `--shuffle` / `--no-shuffle` | `-s` | Flag | `false` | Randomize playback order instead of alphabetical sequence. |
| `--recursive` / `--no-recursive` | `-R` | Flag | `false` | Recursively scan subdirectories for valid image files. |
| `--multi-monitor` / `--single-monitor` | `-m` | Flag | `false` | Assign different wallpapers across connected displays. |
| `--online` | | Choice | `None` | Fetch online wallpapers (`wallhaven`, `unsplash`, `bing`, `picsum`, `loremflickr`). |
| `--category` | `-C` | String | `None` | Category or keyword filter for Wallhaven or Unsplash. |
| `--unsplash-key` | | String | `None` | Personal Unsplash API Access Key. |
| `--source` | | Choice | `folder` | Source type (`folder`, `local`, or online provider name). |
| `--keep-last` | | Integer | `20` | Max downloaded online wallpapers to retain in `~/.cache/wchanger/`. |
| `--prefetch` / `--no-prefetch` | | Flag | `true` | Pre-download the next online wallpaper in background. |
| `--run-background` | `-b` | Flag | `false` | Detach and run as a background daemon process. |
| `--install-autostart` | `--auto-start` | Flag | `false` | Launch interactive wizard to install systemd user service. |
| `--repetition` / `--no-repetition` | `-r` / `-nr`| Flag | `true` | Loop continuously (`-r`) or exit after setting wallpapers once (`-nr`). |
| `--theme` | `-t` | Choice | `both` | GNOME light/dark mode target (`dark`, `light`, or `both`). |
| `--output` | `-o` | Choice | `console` | Progress output (`console` for stdout, `log` for `info.log`). |
| `--config` | `-c` | Path | Auto | Path to a custom TOML configuration file. |
| `--no-config` | | Flag | `false` | Disable loading settings from `config.toml`. |
| `--gnome` | | Flag | Auto | Explicitly set desktop environment to GNOME. |
| `--cinnamon` | | Flag | Auto | Explicitly set desktop environment to Cinnamon. |
| `--kde` | `--plasma` | Flag | Auto | Explicitly set desktop environment to KDE Plasma. |
| `--xfce` | | Flag | Auto | Explicitly set desktop environment to XFCE. |
| `--mate` | | Flag | Auto | Explicitly set desktop environment to MATE. |
| `--lxqt` | | Flag | Auto | Explicitly set desktop environment to LXQt. |
| `--help` | `-h` | Flag | | Show help message and exit. |

---

## Troubleshooting & FAQ

### Missing System Tool Errors

If you see an error indicating a required tool was not found in your `PATH`:

- **`gsettings` not found:** Install `libglib2.0-bin` (Debian/Ubuntu) or `glib2` (Fedora/Arch).
- **`qdbus` not found:** On KDE Plasma, install `qdbus-qt6` (Debian/Ubuntu) or `qt6-tools` (Fedora/Arch).
- **`xfconf-query` not found:** On XFCE, install `xfconf`.
- **`pcmanfm-qt` not found:** On LXQt, install `pcmanfm-qt`.

### Unsplash HTTP 401 or 403 Errors

- **HTTP 401 (Unauthorized):** Your Unsplash Access Key is missing or invalid. Verify that the key pasted into `config.toml` or extension preferences matches the **Access Key** from your Unsplash Developer dashboard (not the Secret Key).
- **HTTP 403 (Rate Limit Exceeded):** Free Unsplash developer applications are limited to 50 requests per hour. Increase your rotation interval (e.g. `-p 15m` or `-p 30m`) so requests remain comfortably within limits.

### Multi-Monitor Shows Duplicate Images on GNOME / Cinnamon

- GNOME and Cinnamon require `xrandr` to query screen dimensions under X11, or GNOME display metrics under Wayland. Install `x11-xserver-utils` (Debian/Ubuntu) or `xorg-xrandr` (Arch).
- Ensure Pillow is installed (`pip install pillow`) so `wchanger` can render the composite canvas.

### Wallpapers Do Not Change on KDE Plasma

On some Plasma configurations, desktop containment scripts may be locked. Verify widgets are unlocked, or restart Plasma shell:

```bash
kquitapp6 plasmashell && kstart5 plasmashell # KDE 6: kquitapp6 plasmashell && plasmashell &
```

### Checking Daemon Logs

When running with `-b` or `-o log`, inspect `info.log` in your working directory or check systemd logs:

```bash
journalctl --user -u wallpaper-changer.service -e
```

---

## Development & Contributing

Contributions, bug reports, and pull requests are welcome.

### Running the Test Suite

`wchanger` includes a comprehensive unit and integration test suite covering CLI parsing, configuration loading, network mocking, and desktop setters:

```bash
python3 -m unittest discover -s tests
```

### Building the GNOME Extension Package

To package the GNOME Shell extension for distribution:

```bash
make pack-extension
```

This creates a zip archive (`wchanger@ibehii.github.com.shell-extension.zip`) ready for installation or uploading to [extensions.gnome.org](https://extensions.gnome.org/).

---

## License

This project is licensed under the [MIT License](LICENSE).

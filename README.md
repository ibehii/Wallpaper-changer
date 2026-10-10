# Awesome Wallpaper Changer 🖼️

An automated, lightweight desktop wallpaper rotator for Linux (GNOME, Cinnamon, KDE Plasma, XFCE, MATE & LXQt).

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20(GNOME%20%7C%20Cinnamon%20%7C%20KDE%20%7C%20XFCE%20%7C%20MATE%20%7C%20LXQt)-orange.svg?logo=linux&logoColor=white)](https://www.kernel.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What It Does

**Awesome Wallpaper Changer** (`wchanger`) cycles through a directory of image files or online providers and automatically sets them as your desktop wallpaper at a configurable interval. It automatically detects your desktop environment (**GNOME**, **Cinnamon**, **KDE Plasma**, **XFCE**, **MATE**, or **LXQt**), integrating natively using:
- `gsettings` for **GNOME**, **Cinnamon**, and **MATE**
- D-Bus (`qdbus`) PlasmaShell scripting for **KDE Plasma**
- `xfconf-query` backdrop properties for **XFCE**
- `pcmanfm-qt` for **LXQt**

It supports both single-monitor setups and multi-monitor setups with different wallpapers per display. Designed to be lightweight and robust, it can run interactively as a CLI command (`wchanger`), detached in the background, or as an automatic system service on boot.

---

## Features

- **System-Wide CLI Command (`wchanger`):** Installable directly via `pip` or `pipx` into standard system PATH locations (`/usr/local/bin`, `/bin`, or `~/.local/bin`) with `pyproject.toml` console script entry point.
- **Multi-Monitor Wallpaper Support (`--multi-monitor` / `-m`):** Set different wallpapers on each connected monitor simultaneously:
  - **KDE Plasma:** Native per-screen assignment via PlasmaShell scripting (`desktops()` containment indexing).
  - **XFCE:** Native per-monitor property assignment via `xfconf-query`.
  - **GNOME, Cinnamon & MATE:** Automatic panoramic wallpaper stitching based on `xrandr` screen coordinates and Pillow (`picture-options = spanned`).
  - **LXQt:** Multi-screen desktop profile management (`[Desktop_Screen_X]`) in `settings.conf`.
  - Works with local image folders as well as online wallpaper providers.
- **Automatic Desktop Detection:** Automatically senses whether you are using GNOME, Cinnamon, KDE Plasma, XFCE, MATE, or LXQt.
- **Manual Desktop Override:** Easily override detection using `--gnome`, `--cinnamon`, `--kde`, `--xfce`, `--mate`, or `--lxqt` if needed.
- **Native Desktop Integration:**
  - **KDE Plasma:** Controls wallpapers seamlessly on KDE Plasma (Plasma 5 & Plasma 6) via D-Bus (`qdbus`, `qdbus6`, or `qdbus-qt5`) executing PlasmaShell configuration scripts.
  - **XFCE:** Updates backdrop properties across screens and workspaces using `xfconf-query`.
  - **MATE:** Configures desktop background seamlessly using `gsettings` (`org.mate.background`).
  - **LXQt:** Updates wallpaper on the desktop shell using `pcmanfm-qt`.
- **Start at Login (`--install-autostart`):** An interactive wizard that configures, installs, and enables a systemd startup service so the wallpaper changer runs automatically every time you sign in (legacy `--auto-start` also supported).
- **Persistent Configuration File (`config.toml`):** Save default directories, intervals, desktop modes, online sources, multi-monitor preferences, and shuffle settings next to `wchanger.py` (or in `~/.config/wchanger/config.toml`) so you never have to retype options.
- **Download Cache & Auto-Cleanup:** Online wallpapers are cached locally in `~/.cache/wchanger/`, retaining only the most recent 20 downloads (configurable via `keep_last` in `config.toml` or `--keep-last`) to avoid eating up disk space.
- **Background Mode (`--run-background` / `-b`):** Spawns a detached daemon process, requires no user input, outputs nothing to the terminal, and exits immediately.
- **GNOME Theme Awareness:** Switch wallpapers for light mode (`picture-uri`), dark mode (`picture-uri-dark`), or both simultaneously.
- **Automated Cycling:** Rotates through all supported pictures in a folder with a custom pause duration.
- **Safe Execution:** Uses direct `subprocess.run` list execution (no shell injection risks) and generates RFC-compliant `file:///` URIs and clean paths that properly handle spaces and special characters.
- **Resource Efficient:** Validates images once during initialization, avoiding redundant filesystem rescans, busy-waiting, or CPU lockups.
- **Robust Error Handling:** Skips corrupt or unreadable files, prevents freezes on empty folders, and exits cleanly upon pressing `Ctrl+C`.
- **Online Wallpaper Sources (`--online` / `--source`):** Fetch stunning wallpapers directly from popular online providers without needing local image files:
  - **Wallhaven (`wallhaven`):** Real top-rated wallpapers from Wallhaven (`1920x1080+`).
  - **Bing Daily Image (`bing`):** Microsoft Bing's daily curated wallpaper photo.
  - **Picsum (`picsum`):** Random high-resolution photography from Lorem Picsum.
  - **LoremFlickr (`loremflickr`):** Fresh nature photography from LoremFlickr.
- **Shuffle Mode (`--shuffle` / `-s`):** Randomize the wallpaper playlist instead of cycling in folder order. Reshuffles automatically between full passes.
- **Subfolder Search (`--recursive` / `-R`):** Search directories recursively to discover wallpapers tucked away inside subfolders.
- **Flexible Time Units (`-p` / `--pause`):** Specify pause intervals using human-friendly units (e.g. `10m`, `1h`, `45s`, `1d`, `1h30m`, `1.5h`, or plain numbers `60`).
- **Single-Pass or Continuous:** Loop forever by default or exit after cycling through all images once using `--no-repetition`.

---

## Requirements

- **Operating System:** Linux
- **Desktop Environments:** GNOME (GNOME 42+ recommended), Cinnamon, KDE Plasma (Plasma 5 & 6), XFCE, MATE, or LXQt
- **Python Version:** Python 3.8 or higher
- **System Tools:**
  - **For GNOME, Cinnamon & MATE:** `gsettings`
    - *Debian/Ubuntu:* `sudo apt install libglib2.0-bin`
    - *Fedora:* `sudo dnf install glib2`
    - *Arch Linux:* `sudo pacman -S glib2`
  - **For KDE Plasma:** `qdbus` (or `qdbus6` / `qdbus-qt6` / `qdbus-qt5`)
    - *Debian/Ubuntu:* `sudo apt install qdbus-qt6` (or `qdbus-qt5` / `qt6-tools` / `qttools5-dev-tools`)
    - *Fedora:* `sudo dnf install qt6-qttools` (or `qt5-qttools`)
    - *Arch Linux:* `sudo pacman -S qt6-tools` (or `qt5-tools`)
  - **For XFCE:** `xfconf-query`
    - *Debian/Ubuntu:* `sudo apt install xfconf`
    - *Fedora:* `sudo dnf install xfconf`
  - **For LXQt:** `pcmanfm-qt`
    - *Debian/Ubuntu:* `sudo apt install pcmanfm-qt`
    - *Fedora:* `sudo dnf install pcmanfm-qt`
    - *Arch Linux:* `sudo pacman -S pcmanfm-qt`
  - **For Multi-Monitor Display Geometry Detection:** `xrandr` (standard on X11 desktop environments)
    - *Debian/Ubuntu:* `sudo apt install x11-xserver-utils`
    - *Fedora:* `sudo dnf install xrandr`
    - *Arch Linux:* `sudo pacman -S xorg-xrandr`
- **Python Dependencies:** `click`, `colorama`, `Pillow`, `requests` (listed in `requirements.txt` and `pyproject.toml`)

---

## Installation

You can install `wchanger` as a real system command or run it directly from source.

### Option 1: Install as a System Command (Recommended)

Installing `wchanger` creates the executable console script `wchanger` in your PATH so you can run it like a normal command from any directory:

```bash
# 1. Clone the repository
git clone https://github.com/ibehii/Wallpaper-changer.git
cd Wallpaper-changer

# 2. Install using the one-line installer script (installs and links to /bin/wchanger):
sudo ./install.sh

# Or using Make:
sudo make install-bin

# Or install via pip:
pip install .
```

> **Tip:** If installing with `pip install --user .`, ensure `~/.local/bin` is in your shell `PATH` (add `export PATH="$HOME/.local/bin:$PATH"` to your `~/.bashrc` or `~/.zshrc`).

#### Installing Directly to `/bin`
To make `wchanger` accessible system-wide across all users in `/bin` or `/usr/local/bin`:
```bash
# Method A: Automatic installer script
sudo ./install.sh

# Method B: Makefile
sudo make install-bin

# Method C: Direct symlink after pip install
sudo ln -sf $(which wchanger) /bin/wchanger
# or
sudo ln -sf $(which wchanger) /usr/local/bin/wchanger

# Method D: System-wide install with /usr prefix
sudo pip install --prefix=/usr .
```

#### Isolated Installation with `pipx`
If you prefer keeping Python CLI utilities isolated:
```bash
pipx install .
sudo ln -sf $(which wchanger) /bin/wchanger
```

---

### Option 2: Run Directly from Source

If you prefer running without installing the package:
```bash
git clone https://github.com/ibehii/Wallpaper-changer.git
cd Wallpaper-changer
pip install -r requirements.txt
python wchanger.py
```

---

## Usage

Awesome Wallpaper Changer uses a simple, single-command interface. It automatically detects your desktop environment without requiring subcommands.

### Command Syntax

If installed as a system command:
```bash
wchanger [OPTIONS] [PHOTO_PATH]
```

Or if running directly from source:
```bash
python wchanger.py [OPTIONS] [PHOTO_PATH]
```

> **Note:** If `PHOTO_PATH` is omitted, the script defaults to the bundled `photos/` directory in the repository (or `folder` specified in `config.toml`).

---

### Real Examples

#### 1. Quick Start (Auto-Detection)

- **Interactive prompt (auto-detects desktop and uses bundled photos):**
  ```bash
  python wchanger.py
  ```

- **Set wallpaper every 60 seconds from a custom directory:**
  ```bash
  python wchanger.py -p 60 /home/user/Pictures/Wallpapers
  ```

- **Single cycle (exit after rotating through all images once):**
  ```bash
  python wchanger.py -p 30 --no-repetition /home/user/Pictures/Wallpapers
  ```

---

#### 2. Start at Login / Automatic Startup Service (`--install-autostart`)

Run the interactive wizard to automatically create and enable a systemd service that starts the wallpaper changer every time you sign in:

```bash
python wchanger.py --install-autostart
```

*(Note: Legacy `--auto-start` is maintained as a direct alias).*

The wizard will:
1. Ask you for the pause duration (e.g. `60`, `10m`, `1h`).
2. Ask you for the folder containing your wallpapers (or use your online provider).
3. Automatically configure logging to file (`-o log` $\rightarrow$ `info.log`).
4. Request administrator privileges (`sudo`) to install and enable `wallpaper-changer.service` under systemd.
5. In case of any error (e.g., cancelled `sudo`), it directs you to the manual setup instructions below.

---

#### 3. Running in the Background (`--run-background` / `-b`)

Pass `--run-background` to launch the rotator as a silent background daemon. It requires no terminal input, produces no terminal output, and immediately returns control to your shell:

- **Run in the background with default pause (60s):**
  ```bash
  python wchanger.py --run-background /home/user/Pictures/Wallpapers
  ```

- **Run in the background with custom pause and file logging:**
  ```bash
  python wchanger.py -b -p 300 -o log /home/user/Pictures/Wallpapers
  ```

- **To stop the background process at any time:**
  ```bash
  pkill -f wchanger.py
  ```

---

#### 4. Overriding Desktop Detection (`--gnome`, `--cinnamon`, `--kde`, `--xfce`, `--mate`, or `--lxqt`)

If your desktop session is unusual or misidentified, override detection explicitly:

- **Force GNOME mode:**
  ```bash
  python wchanger.py --gnome -p 45 /home/user/Pictures/Wallpapers
  ```

- **Force Cinnamon mode:**
  ```bash
  python wchanger.py --cinnamon -p 60 /home/user/Pictures/Wallpapers
  ```

- **Force KDE Plasma mode:**
  ```bash
  python wchanger.py --kde -p 60 /home/user/Pictures/Wallpapers
  ```

- **Force XFCE mode:**
  ```bash
  python wchanger.py --xfce -p 60 /home/user/Pictures/Wallpapers
  ```

- **Force MATE mode:**
  ```bash
  python wchanger.py --mate -p 60 /home/user/Pictures/Wallpapers
  ```

- **Force LXQt mode:**
  ```bash
  python wchanger.py --lxqt -p 60 /home/user/Pictures/Wallpapers
  ```

---

#### 5. GNOME Dark and Light Themes (`-t` / `--theme`)

GNOME 42+ allows distinct wallpapers for dark and light appearances:

- **Update dark theme wallpaper only:**
  ```bash
  python wchanger.py -p 30 -t dark /home/user/Pictures/DarkWallpapers
  ```

- **Update light theme wallpaper only:**
  ```bash
  python wchanger.py -p 30 -t light /home/user/Pictures/LightWallpapers
  ```

- *(Default)*: Updating without `-t` applies changes to both dark and light modes simultaneously.
  *(Note: The `--theme` option applies only to GNOME and is ignored on Cinnamon, KDE Plasma, XFCE, MATE, and LXQt).*

---

#### 6. Online Wallpapers (`--online`)

Fetch wallpapers dynamically from online providers without needing local image files. Downloaded wallpapers are cached in `~/.cache/wchanger/`:

- **Bing Daily Wallpaper (single run):**
  ```bash
  python wchanger.py --online bing --no-repetition
  ```

- **Wallhaven Top Wallpapers (rotate every 5 minutes):**
  ```bash
  python wchanger.py --online wallhaven -p 300
  ```

- **Picsum Random Photos in Background:**
  ```bash
  python wchanger.py --online picsum -b -p 60
  ```

- **LoremFlickr Nature Wallpapers:**
  ```bash
  python wchanger.py --online loremflickr -p 120
  ```

- **Install Systemd Startup Service with Online Wallpapers:**
  ```bash
  python wchanger.py --auto-start --online bing
  ```

---

#### 7. Shuffle, Recursive Subfolders & Flexible Time Units

- **Shuffle wallpapers randomly every 10 minutes:**
  ```bash
  python wchanger.py --shuffle -p 10m /home/user/Pictures/Wallpapers
  ```

- **Scan all subfolders recursively:**
  ```bash
  python wchanger.py --recursive -p 5m /home/user/Pictures
  ```

- **Combined: Shuffle recursively across all subfolders with 1-hour interval in background:**
  ```bash
  python wchanger.py -s -R -p 1h -b /home/user/Pictures
  ```

---

#### 8. Configuration File & Download Cache Cleanup

- **Zero-typing run using settings from `config.toml`:**
  ```bash
  python wchanger.py
  ```

- **Run with a custom configuration file:**
  ```bash
  python wchanger.py --config /path/to/my_config.toml
  ```

- **Bypass `config.toml` completely and use standard CLI arguments:**
  ```bash
  python wchanger.py --no-config -p 30 /home/user/Pictures
  ```

- **Online wallpapers with custom cache retention (keep last 10 images):**
  ```bash
  python wchanger.py --online wallhaven --keep-last 10
  ```

- **Install startup service with custom online source:**
  ```bash
  python wchanger.py --install-autostart --source bing
  ```

---

#### 9. Multi-Monitor Wallpaper Mode (`-m` / `--multi-monitor`)

When multiple displays are connected, `wchanger` can automatically detect your monitors and assign distinct, different wallpapers to each screen instead of duplicating the same image everywhere.

- **Set different wallpapers on each screen from a local folder:**
  ```bash
  wchanger -m -p 60 /home/user/Pictures/Wallpapers
  ```

- **Rotate different online wallpapers per display every 5 minutes:**
  ```bash
  wchanger -m --online wallhaven -p 5m
  ```

- **Fetch Bing daily wallpapers across multiple displays:**
  ```bash
  wchanger -m --online bing
  ```

- **Temporarily disable multi-monitor mode if `multi_monitor = true` is set in `config.toml`:**
  ```bash
  wchanger --single-monitor -p 60 /home/user/Pictures/Wallpapers
  ```

- **Install an autostart startup service with multi-monitor enabled:**
  ```bash
  wchanger -m --install-autostart
  ```

##### Desktop Environment Implementation:
- **KDE Plasma:** Natively assigns different wallpapers to each display by querying Plasma containments via D-Bus (`qdbus`) and setting per-desktop configuration scripts.
- **XFCE:** Identifies all active monitors (`screen0/monitor0`, `screen0/monitor1`, etc.) via `xfconf-query` and assigns wallpapers independently to each display and workspace.
- **GNOME, Cinnamon & MATE:** Queries display resolutions and physical geometries via `xrandr`, stitches separate wallpapers side-by-side into a single high-resolution panoramic canvas using Pillow, and sets `picture-options = 'spanned'`.
- **LXQt:** Discovers connected screen counts and configures individual desktop entries (`[Desktop_Screen_0]`, `[Desktop_Screen_1]`, etc.) in `~/.config/pcmanfm-qt/lxqt/settings.conf`, falling back to spanned mode if required.

---

## Configuration File (`config.toml`)

Awesome Wallpaper Changer automatically loads settings from `config.toml` located in the same directory as `wchanger.py` (or `~/.config/wchanger/config.toml`). This allows you to configure your preferred folder, timing, desktop environment, multi-monitor preferences, and sources without having to type command-line flags every time.

### Example `config.toml`

```toml
# =====================================================================
# Awesome Wallpaper Changer (wchanger) - Configuration File
# =====================================================================
# Place this file as 'config.toml' next to wchanger.py or in ~/.config/wchanger/config.toml.
# Command-line flags always take precedence over options defined here.

# Target directory containing local wallpapers (used when source = "folder")
folder = "~/Pictures/wallpapers"

# Desktop environment: "auto", "gnome", "cinnamon", "kde", "xfce", "mate", or "lxqt"
desktop = "auto"

# Pause duration between wallpaper changes (seconds or duration string like "10m", "1h", "45s")
pause = 600

# Loop continuously (true) or exit after cycling through all images once (false)
repetition = true

# GNOME theme target: "both", "dark", or "light" (applies only to GNOME)
theme = "both"

# Output mode: "console" (terminal text) or "log" (timestamped info.log file)
output = "console"

# Randomize wallpaper display order instead of cycling in folder order
shuffle = true

# Search for wallpapers recursively across subfolders
recursive = false

# Wallpaper source: "folder" for local images, or "wallhaven", "bing", "picsum", "loremflickr"
source = "wallhaven"

# Maximum number of downloaded online wallpapers to retain in cache
keep_last = 20

# Run in background detached from terminal (true/false)
run_background = false

# Set different wallpapers across multiple connected monitors (true/false)
multi_monitor = false
```

### Configuration Keys Reference

| Key | Value Type | Example | Description |
| :--- | :--- | :--- | :--- |
| `folder` | String (Path) | `"~/Pictures/wallpapers"` | Target directory containing local images. |
| `desktop` | String | `"auto"`, `"kde"`, `"gnome"` | Target desktop environment (or auto-detect). |
| `pause` | Integer or String | `600`, `"10m"`, `"1h"` | Interval between wallpaper changes. |
| `repetition` | Boolean | `true`, `false` | Loop indefinitely (`true`) or exit after one pass (`false`). |
| `theme` | String | `"both"`, `"dark"`, `"light"` | GNOME appearance target (dark/light/both). |
| `output` | String | `"console"`, `"log"` | Output destination (terminal or `info.log`). |
| `shuffle` | Boolean | `true`, `false` | Randomize playback order. |
| `recursive` | Boolean | `false`, `true` | Scan subfolders recursively. |
| `source` | String | `"folder"`, `"wallhaven"`, `"bing"`, `"picsum"` | Wallpaper source mode. |
| `keep_last` | Integer | `20` | Max downloaded online images to retain in cache before pruning. |
| `run_background` | Boolean | `false`, `true` | Launch silently as background daemon. |
| `multi_monitor` | Boolean | `false`, `true` | Set different wallpapers on each connected display/monitor. |

> **Precedence Rule:** Command-line flags always take priority over settings in `config.toml`. For example, running `python wchanger.py -p 30` will use a 30-second interval even if `pause = 600` is defined in `config.toml`.

---

## Options and Arguments Reference

### Options

| Option | Short Flag | Accepted Values | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--pause` | `-p` | Duration string (e.g. `30s`, `10m`, `1h`, `1d`, `1h30m`, `1.5h`, `60`) | `60` *(or config)* | Duration between wallpaper changes using human units. |
| `--shuffle` / `--no-shuffle` | `-s` | Flag | `False` *(or config)* | Shuffle wallpapers randomly instead of cycling in folder order. |
| `--recursive` / `--no-recursive` | `-R` | Flag | `False` *(or config)* | Search for images recursively in subfolders. |
| `--multi-monitor` / `--single-monitor` | `-m` | Flag | `False` *(or config)* | Set different wallpapers on each connected monitor/screen. |
| `--online` | | `wallhaven`, `bing`, `picsum`, `loremflickr` | `None` | Fetch wallpapers online from a provider. |
| `--source` | | `folder`, `wallhaven`, `bing`, `picsum`, `loremflickr` | `"folder"` *(or config)* | Choose local folder or online wallpaper source. |
| `--keep-last` | | Integer $\ge 1$ | `20` *(or config)* | Maximum number of downloaded online wallpapers to retain in cache before cleanup. |
| `--config` | `-c` | File path | `config.toml` | Path to a custom TOML configuration file. |
| `--no-config` | | Flag | `False` | Disable loading settings from `config.toml`. |
| `--install-autostart` | `--auto-start` | Flag | `False` | Interactively configure and install a startup service so the changer runs every time you sign in. |
| `--run-background` | `-b` | Flag | `False` *(or config)* | Run detached in the background with no terminal output or prompts. |
| `--gnome` | | Flag | Auto-detect | Manually override desktop environment to GNOME. |
| `--cinnamon` | | Flag | Auto-detect | Manually override desktop environment to Cinnamon. |
| `--kde` | `--plasma` | Flag | Auto-detect | Manually override desktop environment to KDE Plasma. |
| `--xfce` | `--xfce4` | Flag | Auto-detect | Manually override desktop environment to XFCE. |
| `--mate` | | Flag | Auto-detect | Manually override desktop environment to MATE. |
| `--lxqt` | | Flag | Auto-detect | Manually override desktop environment to LXQt. |
| `--repetition` / `--no-repetition` | `-r` / `-nr` | Flag | `--repetition` | Loop continuously (`--repetition`) or exit after one pass (`--no-repetition`). |
| `--theme` *(GNOME only)* | `-t` | `dark`, `light`, `both` | `both` *(or config)* | Apply wallpaper changes to dark theme, light theme, or both. |
| `--output` | `-o` | `console`, `log` | `console` *(or config)* | Display colorized progress in terminal or write timestamps to `info.log`. |
| `--help` | `-h` | None | | Show command help message and available options. |

### Arguments

| Argument | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `PHOTO_PATH` | Directory Path | No | `./photos` *(or config)* | Path to a folder containing supported images (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`, `.svg`, `.tiff`). |

---

## Starting on Boot (Systemd Startup Service)

### Method 1: Automatic Setup via `--install-autostart` (Recommended)

Simply run:
```bash
python wchanger.py --install-autostart
```
*(Legacy `--auto-start` is also supported)*.

Or with explicit desktop override (e.g. for XFCE, MATE, or LXQt):
```bash
python wchanger.py --xfce --install-autostart
```
Follow the interactive prompts to set your pause time and wallpapers folder, and enter your `sudo` password when requested. The wizard automatically configures user permissions, `WorkingDirectory`, session D-Bus addresses, and `DISPLAY` environment variables so all desktop tools (including Qt GUI tools like `pcmanfm-qt`) run seamlessly every time you sign in.

---

### Method 2: Manual Systemd Setup (Fallback)

If the automatic `--install-autostart` command failed or you prefer setting up the service manually:

1. Create a user systemd service directory:
   ```bash
   mkdir -p ~/.config/systemd/user
   ```

2. Create `~/.config/systemd/user/wallpaper-changer.service`:
   ```ini
   [Unit]
   Description=Awesome Wallpaper Changer Service
   After=graphical-session.target

   [Service]
   Type=simple
   WorkingDirectory=/absolute/path/to/Wallpaper-changer
   Environment=DISPLAY=:0
   ExecStart=/usr/bin/python3 /absolute/path/to/Wallpaper-changer/wchanger.py -p 300 -o log /absolute/path/to/Pictures
   Restart=on-failure
   RestartSec=10

   [Install]
   WantedBy=default.target
   ```
   *(Note: You can pass `--kde`, `--gnome`, `--cinnamon`, `--xfce`, `--mate`, or `--lxqt` explicitly in `ExecStart` if auto-detection is not available in your systemd environment).*

3. Enable and start the service:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now wallpaper-changer.service
   ```

4. Check the service status:
   ```bash
   systemctl --user status wallpaper-changer.service
   ```

5. To stop or disable the service:
   ```bash
   systemctl --user stop wallpaper-changer.service
   systemctl --user disable wallpaper-changer.service
   ```

---

## Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `Error: Required tool 'gsettings' was not found in PATH` | GLib utilities are not installed on your system (GNOME/Cinnamon/MATE). | Install `libglib2.0-bin` (Ubuntu/Debian) or `glib2` (Fedora/Arch). |
| `Error: 'qdbus' (or 'qdbus6' / 'qdbus-qt6' / 'qdbus-qt5') utility was not found on your system PATH` | Qt D-Bus CLI tool is not installed on your system (KDE Plasma). | Install `qdbus-qt6` / `qdbus-qt5` / `qttools5-dev-tools` / `qt6-tools` (Ubuntu/Debian) or `qt6-qttools` / `qt5-qttools` (Fedora/Arch). |
| `Error: 'xfconf-query' utility was not found on your system PATH` | XFCE configuration utility is not installed (XFCE). | Install `xfconf` (Ubuntu/Debian, Fedora, Arch). |
| `Error: 'pcmanfm-qt' utility was not found on your system PATH` | LXQt desktop manager utility is not installed (LXQt). | Install `pcmanfm-qt` (Ubuntu/Debian, Fedora, Arch). |
| `Error: Could not auto-detect your desktop environment (GNOME, Cinnamon, KDE Plasma, XFCE, MATE, or LXQt)` | Running in a non-standard desktop, window manager, or headless SSH session. | Specify `--gnome`, `--cinnamon`, `--kde`, `--xfce`, `--mate`, or `--lxqt` explicitly. |
| `[!] Automatic service setup could not be completed` | `sudo` password was cancelled or systemd failed to register service. | Follow the manual instructions in the **Method 2: Manual Systemd Setup** section of this document. |
| `Error: No valid image files found in directory` | Target folder is empty or contains unsupported formats. | Ensure the folder contains supported images (`.jpg`, `.png`, `.webp`, etc.). |
| Wallpapers do not visibly change on KDE Plasma | Desktop widgets are locked or PlasmaShell script evaluation is inhibited. | Ensure widgets are unlocked, or run `qdbus org.kde.plasmashell /PlasmaShell evaluateScript 'lockCorona(!locked)'`. |
| Wallpapers do not visibly change on other desktops | Running on an unsupported window manager (e.g. i3, bspwm, sway without a wallpaper daemon). | Check your desktop environment via `echo $XDG_CURRENT_DESKTOP`. |
| `Option '--pause' requires at least 1` | Zero or negative number passed to `-p`. | Specify an integer of at least 1 (e.g. `-p 10`). |
| `PermissionError: info.log` | Current working directory is read-only when using `-o log`. | Run the script from your home directory or omit `-o log`. |
| `[!] Network Error: Unable to connect to '<provider>'` | Computer is offline, or DNS lookup failed. | Check your internet connection. In continuous mode, the script automatically retries on the next interval. |
| `[!] Network Error: Server returned HTTP error <code/reason>` | Remote API temporarily failed, rate-limited, or blocked the request. | Try another provider (e.g. `bing`, `picsum`, or `wallhaven`) or wait for rate limits to reset. |

---

## Contributing

Contributions, bug reports, and suggestions are welcome!

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/my-new-feature`).
3. Commit your changes (`git commit -am 'Add some feature'`).
4. Push to the branch (`git push origin feature/my-new-feature`).
5. Open a Pull Request.

---

## License

This project is open-source and distributed under the **[MIT License](LICENSE)**.
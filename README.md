# Awesome Wallpaper Changer 🖼️

An automated, lightweight desktop wallpaper rotator for Linux (GNOME, Cinnamon, KDE Plasma, XFCE, MATE & LXQt).

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20(GNOME%20%7C%20Cinnamon%20%7C%20KDE%20%7C%20XFCE%20%7C%20MATE%20%7C%20LXQt)-orange.svg?logo=linux&logoColor=white)](https://www.kernel.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What It Does

**Awesome Wallpaper Changer** cycles through a directory of image files and automatically sets them as your desktop wallpaper at a configurable interval. It automatically detects your desktop environment (**GNOME**, **Cinnamon**, **KDE Plasma**, **XFCE**, **MATE**, or **LXQt**), integrating natively using:
- `gsettings` for **GNOME**, **Cinnamon**, and **MATE**
- D-Bus (`qdbus`) PlasmaShell scripting for **KDE Plasma**
- `xfconf-query` backdrop properties for **XFCE**
- `pcmanfm-qt` for **LXQt**

Designed to be lightweight and robust, it can run interactively in your terminal, detached in the background, or as an automatic system service on boot.

---

## Features

- **Automatic Desktop Detection:** Automatically senses whether you are using GNOME, Cinnamon, KDE Plasma, XFCE, MATE, or LXQt.
- **Manual Desktop Override:** Easily override detection using `--gnome`, `--cinnamon`, `--kde`, `--xfce`, `--mate`, or `--lxqt` if needed.
- **Native Desktop Integration:**
  - **KDE Plasma:** Controls wallpapers seamlessly on KDE Plasma (Plasma 5 & Plasma 6) via D-Bus (`qdbus`, `qdbus6`, or `qdbus-qt5`) executing PlasmaShell configuration scripts.
  - **XFCE:** Updates backdrop properties across screens and workspaces using `xfconf-query`.
  - **MATE:** Configures desktop background seamlessly using `gsettings` (`org.mate.background`).
  - **LXQt:** Updates wallpaper on the desktop shell using `pcmanfm-qt`.
- **Automatic Service Installation (`--auto-start`):** An interactive wizard that configures, installs, and enables a systemd startup service with root privileges across all supported desktops.
- **Background Mode (`--run-background`):** Spawns a detached daemon process, requires no user input, outputs nothing to the terminal, and exits immediately.
- **GNOME Theme Awareness:** Switch wallpapers for light mode (`picture-uri`), dark mode (`picture-uri-dark`), or both simultaneously.
- **Automated Cycling:** Rotates through all supported pictures in a folder with a custom pause duration.
- **Safe Execution:** Uses direct `subprocess.run` list execution (no shell injection risks) and generates RFC-compliant `file:///` URIs and clean paths that properly handle spaces and special characters.
- **Resource Efficient:** Validates images once during initialization, avoiding redundant filesystem rescans, busy-waiting, or CPU lockups.
- **Robust Error Handling:** Skips corrupt or unreadable files, prevents freezes on empty folders, and exits cleanly upon pressing `Ctrl+C`.
- **Online Wallpaper Sources (`--online`):** Fetch stunning wallpapers directly from popular online providers without needing local image files:
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
    - *Arch Linux:* `sudo pacman -S xfconf`
  - **For LXQt:** `pcmanfm-qt`
    - *Debian/Ubuntu:* `sudo apt install pcmanfm-qt`
    - *Fedora:* `sudo dnf install pcmanfm-qt`
    - *Arch Linux:* `sudo pacman -S pcmanfm-qt`
- **Python Dependencies:** `click`, `colorama`, `Pillow` (listed in `requirements.txt`)

---

## Installation

Follow these steps to clone and set up the project:

```bash
# 1. Clone the repository
git clone https://github.com/ibehii/Wallpaper-changer.git

# 2. Navigate to the project directory
cd Wallpaper-changer

# 3. (Optional but recommended) Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install the required Python packages
pip install -r requirements.txt
```

---

## Usage

Awesome Wallpaper Changer uses a simple, single-command interface. It automatically detects your desktop environment without requiring subcommands.

### Command Syntax

```bash
python wchanger.py [OPTIONS] [PHOTO_PATH]
```

> **Note:** If `PHOTO_PATH` is omitted, the script defaults to the bundled `photos/` directory in the repository.

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

#### 2. Automatic Startup Service Setup (`--auto-start`)

Run the interactive wizard to automatically create and enable a systemd service that starts the wallpaper changer on boot:

```bash
python wchanger.py --auto-start
```

The wizard will:
1. Ask you for the pause duration (in seconds).
2. Ask you for the folder containing your wallpapers.
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

## Options and Arguments Reference

### Options

| Option | Short Flag | Accepted Values | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--pause` | `-p` | Duration string (e.g. `30s`, `10m`, `1h`, `1d`, `1h30m`, `1.5h`, `60`) | `60` *(Interactive prompt if foreground)* | Duration between wallpaper changes using human units. |
| `--shuffle` | `-s` | Flag | `False` | Shuffle wallpapers randomly instead of cycling in folder order. |
| `--recursive` | `-R` | Flag | `False` | Search for images recursively in subfolders. |
| `--online` | | `wallhaven`, `bing`, `picsum`, `loremflickr` | `None` *(Uses local photos)* | Fetch wallpapers online from a provider. |
| `--auto-start` | | Flag | `False` | Interactively configure and install a systemd startup service with root privileges. |
| `--run-background` | `-b` | Flag | `False` | Run detached in the background with no terminal output or prompts. |
| `--gnome` | | Flag | Auto-detect | Manually override desktop environment to GNOME. |
| `--cinnamon` | | Flag | Auto-detect | Manually override desktop environment to Cinnamon. |
| `--kde` | `--plasma` | Flag | Auto-detect | Manually override desktop environment to KDE Plasma. |
| `--xfce` | `--xfce4` | Flag | Auto-detect | Manually override desktop environment to XFCE. |
| `--mate` | | Flag | Auto-detect | Manually override desktop environment to MATE. |
| `--lxqt` | | Flag | Auto-detect | Manually override desktop environment to LXQt. |
| `--repetition` / `--no-repetition` | `-r` / `-nr` | Flag | `--repetition` | Loop continuously (`--repetition`) or exit after one pass (`--no-repetition`). |
| `--theme` *(GNOME only)* | `-t` | `dark`, `light` | Both | Apply wallpaper changes to dark theme, light theme, or both. |
| `--output` | `-o` | `console`, `log` | `console` | Display colorized progress in terminal or write timestamps to `info.log`. |
| `--help` | `-h` | None | | Show command help message and available options. |

### Arguments

| Argument | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `PHOTO_PATH` | Directory Path | No | `./photos` | Path to a folder containing supported images (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`, `.svg`, `.tiff`). |

---

## Starting on Boot (Systemd Startup Service)

### Method 1: Automatic Setup via `--auto-start` (Recommended)

Simply run:
```bash
python wchanger.py --auto-start
```
Or with explicit desktop override (e.g. for XFCE, MATE, or LXQt):
```bash
python wchanger.py --xfce --auto-start
```
Follow the interactive prompts to set your pause time and wallpapers folder, and enter your `sudo` password when requested. The wizard automatically configures user permissions, `WorkingDirectory`, session D-Bus addresses, and `DISPLAY` environment variables so all desktop tools (including Qt GUI tools like `pcmanfm-qt`) run seamlessly on login.

---

### Method 2: Manual Systemd Setup (Fallback)

If the automatic `--auto-start` command failed or you prefer setting up the service manually:

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
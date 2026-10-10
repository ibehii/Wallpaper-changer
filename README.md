<div align="center">

<p align="center">
  <img src="photos/anahita_banner.png" width="640" alt="Anahita Wallpaper Changer Banner" />
</p>

# 🌊 Anahita Wallpaper Changer (`wchanger`)
### *The Ultimate Autonomous Wallpaper Rotator & Multi-Monitor Engine for Linux*

[![Release](https://img.shields.io/badge/Release-v3.0.3--Aredvi_Sura_Anahita-purple?style=for-the-badge&logo=git&logoColor=white)](https://github.com/ibehii/Wallpaper-changer/releases)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20(6%20Desktops)-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://www.kernel.org/)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge&logo=open-source-initiative&logoColor=white)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-215%20Passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![Architecture](https://img.shields.io/badge/Architecture-Wayland%20%7C%20X11-blueviolet?style=for-the-badge&logo=gnome&logoColor=white)](#desktop-environments-matrix)

<br/>

<p align="center">
  <img src="photos/wallpaer1.png" width="31%" alt="Cosmic Landscape" />
  <img src="photos/wallpaer2.jpg" width="31%" alt="Serene River Forest" />
  <img src="photos/wallpaer3.jpg" width="31%" alt="Winter Mountain Pines" />
</p>

*Sample bundled high-definition wallpapers dynamically managed by `wchanger`.*

---

### 🌟 Introduction

> **Transform your Linux desktop experience.**
> 
> **Anahita Wallpaper Changer** is a lightweight, zero-bloat CLI application and system background daemon built specifically for Linux. It continuously rotates high-resolution wallpapers across **all major Linux Desktop Environments** (**GNOME**, **Cinnamon**, **KDE Plasma 5 & 6**, **XFCE**, **MATE**, and **LXQt**) with native integration, true **multi-monitor independent displays**, curated **online wallpaper providers**, persistent **TOML configuration**, and automated **systemd login service installation**.

---

### 🗺️ Quick Navigation

<table>
  <tr>
    <td align="center" width="20%">
      <a href="#-quick-start">
        <font size="6">🚀</font><br/>
        <b>Quick Start</b><br/>
        <sub>Get started in 30 seconds</sub>
      </a>
    </td>
    <td align="center" width="20%">
      <a href="#-key-features">
        <font size="6">✨</font><br/>
        <b>Key Features</b><br/>
        <sub>Everything wchanger can do</sub>
      </a>
    </td>
    <td align="center" width="20%">
      <a href="#-desktop-environments-matrix">
        <font size="6">🖥️</font><br/>
        <b>Desktop Support</b><br/>
        <sub>GNOME, KDE, XFCE & more</sub>
      </a>
    </td>
    <td align="center" width="20%">
      <a href="#-multi-monitor-support">
        <font size="6">🖥️🖥️</font><br/>
        <b>Multi-Monitor</b><br/>
        <sub>Different image per screen</sub>
      </a>
    </td>
    <td align="center" width="20%">
      <a href="#-start-at-login-systemd">
        <font size="6">⏰</font><br/>
        <b>Start at Login</b><br/>
        <sub>Systemd startup service</sub>
      </a>
    </td>
  </tr>
  <tr>
    <td align="center" width="20%">
      <a href="#-installation">
        <font size="6">📦</font><br/>
        <b>Installation</b><br/>
        <sub>Install to /bin & system PATH</sub>
      </a>
    </td>
    <td align="center" width="20%">
      <a href="#-online-wallpaper-sources">
        <font size="6">🌐</font><br/>
        <b>Online Sources</b><br/>
        <sub>Wallhaven, Bing, Picsum</sub>
      </a>
    </td>
    <td align="center" width="20%">
      <a href="#-configuration-file-configtoml">
        <font size="6">⚙️</font><br/>
        <b>Configuration</b><br/>
        <sub>Zero-typing config.toml</sub>
      </a>
    </td>
    <td align="center" width="20%">
      <a href="#-cli-reference">
        <font size="6">ℹ️</font><br/>
        <b>Change Settings</b><br/>
        <sub>Via config or CLI flags</sub>
      </a>
    </td>
    <td align="center" width="20%">
      <a href="#-troubleshooting">
        <font size="6">🔍</font><br/>
        <b>Troubleshooting</b><br/>
        <sub>Fix common desktop issues</sub>
      </a>
    </td>
  </tr>
</table>

</div>

---

<a id="-quick-start"></a>
## 🚀 Quick Start

Get your desktop cycling in seconds:

```bash
# 1. Install wchanger as a system command into /bin (one command)
sudo ./install.sh

# 2. Run immediately with auto-detection and default wallpapers
wchanger

# 3. Or rotate wallpapers from your own folder every 5 minutes
wchanger -p 5m ~/Pictures/Wallpapers

# 4. Or fetch daily curated Bing photos across all your monitors
wchanger -m --online bing
```

---

<a id="-key-features"></a>
## ✨ Key Features

| Feature | Description | Highlight |
| :--- | :--- | :--- |
| **System-Wide CLI Command** | Packaged via `pyproject.toml` console scripts with automated `/bin/wchanger` integration. | ⚡ Instant terminal access |
| **Multi-Monitor Display Engine** | Assigns independent, unique wallpapers to every connected monitor without duplicate stretching. | 🖥️ Native & Spanned Modes |
| **6 Desktop Environments** | Native hooks for GNOME, Cinnamon, KDE Plasma (5 & 6), XFCE, MATE, and LXQt. | 🐧 Zero external desktop tools |
| **Online Curated Sources** | Automatic streaming and caching from Wallhaven, Bing Daily, Picsum, and LoremFlickr. | 🌐 Unlimited fresh wallpapers |
| **Intelligent Cache Management** | Automatically retains the most recent downloads (e.g. 20) and prunes stale images. | 🧹 Zero disk bloat |
| **Automated Startup Wizard** | One-step interactive setup (`--install-autostart`) registers a background systemd login service. | 🔄 Start on sign-in |
| **Persistent Configuration** | Stores your favorite folders, intervals, and sources in `config.toml` so you never retype flags. | ⚙️ Zero-typing workflow |
| **Human Duration Parsing** | Supports flexible time units like `10m`, `1h`, `45s`, `1.5h`, `1d`, or plain seconds. | ⏱️ Intuitive syntax |
| **Shuffle & Subfolder Discovery** | Deep directory traversal (`-R`) and randomized non-repeating shuffle (`-s`). | 🔀 Fresh rotations |
| **Light & Dark Theme Sync** | Independent or synchronized GNOME 42+ day/night background switching. | 🌗 Adaptive theme modes |


---

<a id="-desktop-environments-matrix"></a>
## 🖥️ Desktop Environments Matrix

Anahita Wallpaper Changer natively interfaces with your desktop manager using system-native APIs:

| Desktop Environment | Supported Versions | Backend Setter | Multi-Monitor Method | Theme Awareness | Required Tool |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **GNOME** | 3.38 – 47+ | `gsettings` (`org.gnome.desktop.background`) | High-res Spanned Canvas (`xrandr` + Pillow) | Light & Dark (`-t`) | `gsettings` (`libglib2.0-bin`) |
| **KDE Plasma** | Plasma 5.x & 6.x | D-Bus (`org.kde.PlasmaShell`) | Native per-desktop scripting (`desktops()`) | System default | `qdbus` / `qdbus6` (`qt6-tools`) |
| **Cinnamon** | 4.x – 6.x+ | `gsettings` (`org.cinnamon.desktop.background`) | High-res Spanned Canvas (`xrandr` + Pillow) | System default | `gsettings` (`glib2`) |
| **XFCE** | 4.14 – 4.20+ | `xfconf-query` (`xfce4-desktop`) | Native per-monitor property assignment | System default | `xfconf-query` (`xfconf`) |
| **MATE** | 1.24 – 1.28+ | `gsettings` (`org.mate.background`) | High-res Spanned Canvas (`xrandr` + Pillow) | System default | `gsettings` (`libglib2.0-bin`) |
| **LXQt** | 0.16 – 2.1+ | `pcmanfm-qt` (`--set-wallpaper`) | Multi-Screen configuration profile & Spanned | System default | `pcmanfm-qt` (`pcmanfm-qt`) |

<details>
<summary><b>📦 Quick Package Install Commands for Desktop Dependencies</b></summary>

<br/>

**Debian / Ubuntu / Linux Mint:**
```bash
# GNOME, Cinnamon, MATE:
sudo apt install libglib2.0-bin x11-xserver-utils

# KDE Plasma:
sudo apt install qdbus-qt6  # or qdbus-qt5

# XFCE:
sudo apt install xfconf

# LXQt:
sudo apt install pcmanfm-qt
```

**Fedora / RHEL:**
```bash
sudo dnf install glib2 xrandr qt6-qttools xfconf pcmanfm-qt
```

**Arch Linux / Manjaro:**
```bash
sudo pacman -S glib2 xorg-xrandr qt6-tools xfconf pcmanfm-qt
```

</details>

---

<a id="-multi-monitor-support"></a>
## 🖥️ Multi-Monitor Support

When multiple displays are connected, `wchanger` detects monitor geometry and assigns **different wallpapers to each screen** simultaneously:

```bash
# Enable multi-monitor rotation from your wallpapers folder:
wchanger -m ~/Pictures/Wallpapers

# Stream different online wallpapers to each screen every 10 minutes:
wchanger -m --online wallhaven -p 10m
```

### How Multi-Monitor Works:

```
  ┌────────────────────────────────┐    ┌────────────────────────────┐
  │           Display 1            │    │           Display 2            │
  │        (HDMI-1 / 4K UHD)       │    │        (DP-1 / 1440p)          │
  │                                │    │                                │
  │    [ Mountain Sunset Image ]   │    │    [ Deep Space Nebula Image ] │
  └────────────────────────────────┘    └────────────────────────────┘
```

1. **KDE Plasma & XFCE (Native Multi-Screen):** Queries individual screen containments (`desktop[0]`, `desktop[1]` or `monitor0`, `monitor1`) and issues independent native background assignments.
2. **GNOME, Cinnamon, MATE & LXQt (Intelligent Panoramic Canvas):** Inspects physical geometry and resolution for each monitor via `xrandr`, scales and crops each wallpaper without distortion (`ImageOps.fit`), then merges them into a wide composite image that desktop environments can assign as one background.
3. **Anti-Caching Mechanism:** Alternates target output files (`multimonitor_spanned_0.png` ↔ `multimonitor_spanned_1.png`) so desktop environments register instant file URI changes and refresh correctly.

---

<a id="-installation"></a>
## 📦 Installation

Install `wchanger` as a real system command accessible across all user terminals:

### Method 1: Automatic Installer (Recommended)

```bash
git clone https://github.com/ibehii/Wallpaper-changer.git
cd Wallpaper-changer

# Installs dependencies via pip and creates /bin/wchanger
sudo ./install.sh
```

### Method 2: Using Make

```bash
sudo make install-bin
```

### Method 3: Standard Python Pip

```bash
pip install .

# Create symlink so 'wchanger' is available in /bin
sudo ln -sf $(which wchanger) /bin/wchanger
```

> [!TIP]
> **User-only installation:** If you do not have root or `sudo` access, run `pip install --user .` and ensure `~/.local/bin` is in your shell `PATH` (`export PATH="$HOME/.local/bin:$PATH"`).

---

<a id="-online-wallpaper-sources"></a>
## 🌐 Online Wallpaper Sources

Never run out of wallpapers. Stream directly from popular photo curation platforms:

| Provider Key | Provider Name | Description | Default Quality |
| :---: | :---: | :---: | :---: |
| `wallhaven` | **Wallhaven** | Real top-voted wallpapers from Wallhaven API | 1920x1080+ / 4K |
| `bing` | **Bing Daily Photo** | Microsoft Bing's official daily curated picture | High-Res Curated |
| `picsum` | **Lorem Picsum** | Stunning random photography from Picsum | 1920x1080 |
| `loremflickr` | **LoremFlickr** | Fresh nature and landscape photography | 1920x1080 |

### Examples:

```bash
# Bing Daily Wallpaper (single pass, update and exit):
wchanger --online bing --no-repetition

# Wallhaven Toplist (rotate every 5 minutes in background):
wchanger --online wallhaven -p 5m -b

# LoremFlickr with custom cache limit (keep last 15 images):
wchanger --online loremflickr -p 3m --keep-last 15
```

---

<a id="-start-at-login-systemd"></a>
## ⏰ Start at Login (Systemd Startup Service)

Run the automated wizard to have `wchanger` start cleanly on every login:

```bash
wchanger --install-autostart
```

```
============================================
  Automatic Startup Service Setup Wizard   
============================================

[+] Enter pause duration between changing wallpapers [60]: 5m
[+] Enter path to directory containing wallpapers [~/Pictures/wallpapers]: 
[i] Generated systemd service definition for user 'user':
    Command: /usr/bin/python3 /bin/wchanger -p 300 -o log /home/user/Pictures/wallpapers
    Logging: log (info.log)

[+] Successfully installed and activated 'wallpaper-changer.service'!
[+] The service will now run automatically on login.
```

### Managing the Service:

```bash
# Check service status
sudo systemctl status wallpaper-changer.service

# Stop the service
sudo systemctl stop wallpaper-changer.service

# Restart the service
sudo systemctl restart wallpaper-changer.service

# Disable from starting automatically
sudo systemctl disable wallpaper-changer.service
```

---

<a id="-configuration-file-configtoml"></a>
## ⚙️ Configuration File (`config.toml`)

Save your preferences in `config.toml` (next to the executable or in `~/.config/wchanger/config.toml`) for a zero-typing experience:

```toml
# =====================================================================
# Anahita Wallpaper Changer (wchanger) - Configuration File
# =====================================================================

# Folder containing local wallpapers (used when source = "folder")
folder = "~/Pictures/wallpapers"

# Target desktop: "auto", "gnome", "cinnamon", "kde", "xfce", "mate", or "lxqt"
desktop = "auto"

# Pause duration (supports integers or units: "60", "10m", "1h", "45s")
pause = 600

# Loop continuously (true) or exit after cycling through all images once (false)
repetition = true

# GNOME appearance theme: "both", "dark", or "light"
theme = "both"

# Output mode: "console" (terminal text) or "log" (info.log file)
output = "console"

# Randomize wallpaper playback order
shuffle = true

# Search subfolders recursively
recursive = false

# Wallpaper source: "folder", "wallhaven", "bing", "picsum", or "loremflickr"
source = "wallhaven"

# Maximum number of downloaded online wallpapers to retain in cache
keep_last = 20

# Run in background detached from terminal
run_background = false

# Set different wallpapers across multiple connected monitors
multi_monitor = true
```

> [!NOTE]
> **Precedence Rule:** Command-line arguments always override settings defined in `config.toml`. Use `--no-config` to temporarily bypass the configuration file.

---

<a id="-cli-reference"></a>
## 🛠️ CLI Options Reference

```text
Usage: wchanger [OPTIONS] [PHOTO_PATH]
```

### Command Flags:

| Option | Flag | Type | Default | Description |
| :--- | :---: | :---: | :---: | :--- |
| `--pause` | `-p` | Duration | `60` | Pause duration between rotations (`30s`, `10m`, `1h`, `1.5h`). |
| `--shuffle` / `--no-shuffle` | `-s` | Flag | `false` | Randomize wallpaper playback sequence. |
| `--recursive` / `--no-recursive` | `-R` | Flag | `false` | Recursively scan subfolders for valid images. |
| `--multi-monitor` / `--single-monitor` | `-m` | Flag | `false` | Assign different wallpapers across connected displays. |
| `--online` | | Choice | `None` | Stream online wallpapers (`wallhaven`, `bing`, `picsum`, `loremflickr`). |
| `--source` | | Choice | `folder` | Source mode (`folder`, `local`, or online provider name). |
| `--keep-last` | | Integer | `20` | Max downloaded wallpapers to retain in `~/.cache/wchanger/`. |
| `--run-background` | `-b` | Flag | `false` | Run as a silent, detached daemon process. |
| `--install-autostart` | `--auto-start` | Flag | `false` | Interactive wizard to install systemd login service. |
| `--config` | `-c` | Path | `config.toml` | Path to custom TOML configuration file. |
| `--no-config` | | Flag | `false` | Ignore `config.toml` and rely purely on CLI arguments. |
| `--gnome` | | Flag | Auto | Explicitly set desktop environment to GNOME. |
| `--cinnamon` | `--cinamon` | Flag | Auto | Explicitly set desktop environment to Cinnamon. |
| `--kde` | `--plasma` | Flag | Auto | Explicitly set desktop environment to KDE Plasma. |
| `--xfce` | `--xfce4` | Flag | Auto | Explicitly set desktop environment to XFCE. |
| `--mate` | | Flag | Auto | Explicitly set desktop environment to MATE. |
| `--lxqt` | | Flag | Auto | Explicitly set desktop environment to LXQt. |
| `--theme` | `-t` | Choice | `both` | GNOME 42+ target theme (`dark`, `light`, or `both`). |
| `--output` | `-o` | Choice | `console` | Progress output (`console` for terminal, `log` for `info.log`). |
| `--repetition` / `--no-repetition` | `-r` / `-nr`| Flag | `repetition` | Loop indefinitely or exit after setting all wallpapers once. |
| `--help` | `-h` | Flag | | Show command help message and available options. |

---

<a id="-troubleshooting"></a>
## 🔍 Troubleshooting

<details open>
<summary><b>Common Issues & Solutions</b></summary>

<br/>

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `Error: Required tool 'gsettings' was not found in PATH` | GLib utilities are not installed (GNOME / Cinnamon / MATE). | Install `libglib2.0-bin` (Debian/Ubuntu) or `glib2` (Fedora/Arch). |
| `Error: 'qdbus' utility was not found on your system PATH` | Qt D-Bus tool is missing (KDE Plasma). | Install `qdbus-qt6` or `qt6-tools` via your package manager. |
| `Error: 'xfconf-query' utility was not found` | XFCE configuration tool is missing. | Install `xfconf` package via your package manager. |
| `Error: 'pcmanfm-qt' utility was not found` | LXQt file manager / desktop utility is missing. | Install `pcmanfm-qt` package via your package manager. |
| `Error: Could not auto-detect your desktop environment` | Non-standard session or custom window manager. | Pass `--gnome`, `--cinnamon`, `--kde`, `--xfce`, `--mate`, or `--lxqt` explicitly. |
| Wallpapers do not visibly change on KDE Plasma | Desktop widgets are locked in Plasma. | Unlock desktop widgets or run: `qdbus org.kde.plasmashell /PlasmaShell evaluateScript 'lockCorona(!locked); lockCorona(false);'` to force refresh. |
| `[!] Network Error: Unable to connect to '<provider>'` | Computer is offline or DNS lookup failed. | Check connection; `wchanger` automatically retries next interval without crashing. |
| Multi-monitor shows duplicate wallpapers on GNOME | `xrandr` is not installed or running Wayland without display query. | Install `x11-xserver-utils` (Debian/Ubuntu) or `xorg-xrandr` (Arch). |

</details>

---

## 🤝 Contributing

Contributions and feedback are always welcome!

1. **Fork the Repository**: Click the `Fork` button at the top right of GitHub.
2. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/cool-new-feature
   ```
3. **Run the Test Suite**:
   ```bash
   python3 -m unittest discover -s tests
   ```
4. **Commit & Push**:
   ```bash
   git commit -m "Add cool new feature"
   git push origin feature/cool-new-feature
   ```
5. **Open a Pull Request**: Submit your PR on GitHub for review.

---

## 📄 License

This project is licensed under the **[MIT License](LICENSE)**. Open source, libre, and built for the Linux community with ❤️.

"""Anahita Wallpaper Changer (wchanger).

A lightweight Linux CLI script that cycles through desktop wallpapers on
GNOME, Cinnamon, KDE Plasma, XFCE, MATE, and LXQt desktop environments.
"""

from __future__ import annotations

import getpass
import io
import json
import logging
import os
from pathlib import Path
import platform
import random
import re
import shlex
import shutil
import subprocess
import sys
import time
from typing import Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

import click

try:
    from colorama import Fore, init

    init(autoreset=True)
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    MAGENTA = Fore.MAGENTA
    CYAN = Fore.CYAN
    RESET = Fore.RESET
except ImportError:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

try:
    from PIL import Image, ImageOps

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


VERSION = "3.0.0"
DEFAULT_PAUSE_SECONDS = 60
DEFAULT_KEEP_LAST = 20
DEFAULT_CONFIG_FILENAME = "config.toml"
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "wchanger"
ONLINE_PROVIDER_CHOICES = ("wallhaven", "bing", "picsum", "loremflickr")

DURATION_TOKEN_REGEX = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]*)")

TIME_UNIT_MULTIPLIERS = {
    "": 1,
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
    "d": 86400,
    "day": 86400,
    "days": 86400,
}


def parse_duration_to_seconds(raw_duration: str | int | float) -> int:
    """Convert human-readable duration strings (e.g. '10m', '1h', '45s', '90') to integer seconds."""
    if isinstance(raw_duration, (int, float)):
        seconds = int(raw_duration)
        if seconds < 1:
            raise ValueError("Duration must be at least 1 second.")
        return seconds

    cleaned = str(raw_duration).strip().lower()
    if not cleaned:
        raise ValueError("Duration cannot be empty.")

    tokens = DURATION_TOKEN_REGEX.findall(cleaned)
    if not tokens:
        raise ValueError(
            f"Invalid duration format '{raw_duration}'. "
            "Specify a number with optional units (e.g., 30s, 10m, 1h, 1d)."
        )

    reconstructed = "".join(f"{number_token}{unit_token}" for number_token, unit_token in tokens).replace(" ", "")
    no_space_cleaned = cleaned.replace(" ", "")
    if reconstructed != no_space_cleaned:
        raise ValueError(
            f"Invalid duration format '{raw_duration}'. "
            "Specify a number with optional units (e.g., 30s, 10m, 1h, 1d)."
        )

    total_seconds = 0.0
    for number_token, unit_token in tokens:
        multiplier = TIME_UNIT_MULTIPLIERS.get(unit_token)
        if multiplier is None:
            raise ValueError(
                f"Unknown time unit '{unit_token}' in duration '{raw_duration}'. "
                "Supported units: s (seconds), m (minutes), h (hours), d (days)."
            )
        total_seconds += float(number_token) * multiplier

    final_seconds = int(round(total_seconds))
    if final_seconds < 1:
        raise ValueError("Duration must evaluate to at least 1 second.")

    return final_seconds


class DurationParamType(click.ParamType):
    """Click parameter type parsing human duration strings like '10m', '1h', or '60'."""

    name = "duration"

    def convert(self, value, param, context) -> int | None:
        if value is None:
            return None
        try:
            return parse_duration_to_seconds(value)
        except ValueError as error:
            self.fail(str(error), param, context)


DURATION_TYPE = DurationParamType()


def get_default_config_path() -> Path:
    """Return the filesystem path to the default configuration file."""
    environment_override = os.environ.get("WCHANGER_CONFIG")
    if environment_override:
        return Path(environment_override)
    script_config = Path(__file__).resolve().parent / DEFAULT_CONFIG_FILENAME
    if script_config.exists():
        return script_config
    user_config = Path.home() / ".config" / "wchanger" / DEFAULT_CONFIG_FILENAME
    if user_config.exists():
        return user_config
    return script_config


def load_config_file(config_path: Path | str | None = None) -> dict[str, object]:
    """Load settings from a TOML configuration file if it exists."""
    if os.environ.get("WCHANGER_NO_CONFIG") == "1":
        return {}

    target_path = Path(config_path) if config_path is not None else get_default_config_path()
    if not target_path.exists() or not target_path.is_file():
        return {}

    if tomllib is None:
        click.secho(
            f"[!] Warning: Cannot parse '{target_path}' because no TOML library is available.\n"
            "    On Python < 3.11, install tomli via 'pip install tomli'.",
            fg="yellow",
            err=True,
        )
        return {}

    try:
        with open(target_path, "rb") as file_handle:
            raw_data = tomllib.load(file_handle)
    except Exception as error:
        click.secho(
            f"[!] Warning: Failed to parse configuration file '{target_path}': {error}.\n"
            "    Falling back to standard CLI defaults.",
            fg="yellow",
            err=True,
        )
        return {}

    if not isinstance(raw_data, dict):
        return {}

    # Support flat top-level keys or nested tables like [settings] / [wchanger]
    merged_settings: dict[str, object] = dict(raw_data)
    if "settings" in raw_data and isinstance(raw_data["settings"], dict):
        merged_settings.update(raw_data["settings"])
    if "wchanger" in raw_data and isinstance(raw_data["wchanger"], dict):
        merged_settings.update(raw_data["wchanger"])

    return merged_settings

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".svg",
    ".tiff",
}

GNOME_SCHEMA = "org.gnome.desktop.background"
GNOME_KEY_LIGHT = "picture-uri"
GNOME_KEY_DARK = "picture-uri-dark"

CINNAMON_SCHEMA = "org.cinnamon.desktop.background"
CINNAMON_KEY = "picture-uri"

MATE_SCHEMA = "org.mate.background"
MATE_KEY = "picture-filename"

XFCE_CHANNEL = "xfce4-desktop"
XFCE_FALLBACK_PROPERTIES = (
    "/backdrop/screen0/monitor0/workspace0/last-image",
    "/backdrop/screen0/monitorHDMI-1/workspace0/last-image",
)

DESKTOP_DISPLAY_NAMES = {
    "gnome": "GNOME",
    "cinnamon": "Cinnamon",
    "kde": "KDE Plasma",
    "xfce": "XFCE",
    "mate": "MATE",
    "lxqt": "LXQt",
}

KDE_QDBUS_CANDIDATES = ("qdbus", "qdbus6", "qdbus-qt6", "qdbus-qt5")

DEFAULT_WALLPAPERS_DIR = Path(__file__).resolve().parent / "photos"
DEFAULT_LOG_PATH = Path("info.log")

BANNER = (
    YELLOW
    + """ ██████╗██╗  ██╗ █████╗ ███╗   ██╗ ██████╗ ███████╗██████╗ 
██╔════╝██║  ██║██╔══██╗████╗  ██║██╔════╝ ██╔════╝██╔══██╗
██║     ███████║███████║██╔██╗ ██║██║  ███╗█████╗  ██████╔╝
██║     ██╔══██║██╔══██║██║╚██╗██║██║   ██║██╔══╝  ██╔══██╗
╚██████╗██║  ██║██║  ██║██║ ╚████║╚██████╔╝███████╗██║  ██║
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝"""
    + MAGENTA
    + "\n- Telegram: t.me/BZHNAM\n"
    + "- GitHub: https://github.com/ibehii\n\n"
    + YELLOW
    + f"------------ # v{VERSION} # ------------  \n"
    + RESET
)

# Backward-compatibility aliases
logo = BANNER
LOGO = BANNER


def configure_logging(output_mode: str, log_file_path: Path | str = DEFAULT_LOG_PATH) -> None:
    """Set up file logging when '-o log' is selected, leaving console runs untouched."""
    if output_mode.lower() != "log":
        return

    target_log_path = Path(log_file_path)
    try:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        for existing_handler in root_logger.handlers[:]:
            root_logger.removeHandler(existing_handler)

        file_handler = logging.FileHandler(target_log_path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
        )
        root_logger.addHandler(file_handler)
    except (PermissionError, OSError) as error:
        click.secho(
            f"[!] Warning: Cannot open log file '{target_log_path}': {error}. "
            "Using console output instead.",
            fg="yellow",
            err=True,
        )


def detect_desktop_environment() -> str | None:
    """Identify the running desktop environment based on session environment variables."""
    current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    session_desktop = os.environ.get("DESKTOP_SESSION", "").lower()
    combined_sessions = f"{current_desktop}:{session_desktop}"

    if "cinnamon" in combined_sessions:
        return "cinnamon"
    if "mate" in combined_sessions:
        return "mate"
    if "xfce" in combined_sessions:
        return "xfce"
    if "lxqt" in combined_sessions:
        return "lxqt"
    if "gnome" in combined_sessions:
        return "gnome"
    if "kde" in combined_sessions or "plasma" in combined_sessions:
        return "kde"
    return None


def find_kde_qdbus_executable() -> str | None:
    """Detect which qdbus binary is available on the system PATH."""
    for executable_candidate in KDE_QDBUS_CANDIDATES:
        if shutil.which(executable_candidate):
            return executable_candidate
    return None


def verify_system_requirements(target_desktop: str) -> None:
    """Ensure Linux OS and required desktop CLI tools are available before attempting changes."""
    if platform.system() != "Linux":
        click.secho(
            "Error: Anahita Wallpaper Changer only runs on Linux.",
            fg="red",
            bold=True,
            err=True,
        )
        sys.exit(1)

    if target_desktop == "kde":
        if not find_kde_qdbus_executable():
            click.secho(
                "Error: 'qdbus' (or 'qdbus6' / 'qdbus-qt6' / 'qdbus-qt5') utility was not found on your system PATH.\n"
                "Install it via your package manager (qdbus-qt6 / qttools5-dev-tools / qt6-tools on Debian/Ubuntu, qt6-qttools / qt5-qttools on Fedora/Arch).",
                fg="red",
                bold=True,
                err=True,
            )
            sys.exit(1)
    elif target_desktop == "xfce":
        if not shutil.which("xfconf-query"):
            click.secho(
                "Error: 'xfconf-query' utility was not found on your system PATH.\n"
                "Install it via your package manager (xfconf on Debian/Ubuntu, Fedora, or Arch Linux).",
                fg="red",
                bold=True,
                err=True,
            )
            sys.exit(1)
    elif target_desktop == "lxqt":
        if not shutil.which("pcmanfm-qt"):
            click.secho(
                "Error: 'pcmanfm-qt' utility was not found on your system PATH.\n"
                "Install it via your package manager (pcmanfm-qt on Debian/Ubuntu, Fedora, or Arch Linux).",
                fg="red",
                bold=True,
                err=True,
            )
            sys.exit(1)
    elif target_desktop in ("gnome", "cinnamon", "mate"):
        if not shutil.which("gsettings"):
            click.secho(
                "Error: 'gsettings' utility was not found on your system PATH.\n"
                "Install it via your package manager (libglib2.0-bin on Debian/Ubuntu, glib2 on Fedora/Arch).",
                fg="red",
                bold=True,
                err=True,
            )
            sys.exit(1)
    else:
        click.secho(
            f"Error: Unsupported desktop environment '{target_desktop}'.\n"
            "Supported environments: GNOME, Cinnamon, KDE Plasma, XFCE, MATE, LXQt.",
            fg="red",
            bold=True,
            err=True,
        )
        sys.exit(1)


def is_valid_image_file(image_path: Path) -> bool:
    """Verify that a path points to an actual, uncorrupted image file."""
    if not image_path.is_file():
        return False

    extension = image_path.suffix.lower()
    if extension not in SUPPORTED_IMAGE_EXTENSIONS:
        return False

    if extension == ".svg":
        try:
            return image_path.stat().st_size > 0
        except OSError:
            return False

    if HAS_PILLOW:
        try:
            with Image.open(image_path) as opened_image:
                opened_image.verify()
            return True
        except (OSError, SyntaxError):
            return False

    try:
        return image_path.stat().st_size > 0
    except OSError:
        return False


def file_validator(directory_path: str | Path, recursive: bool = False) -> list[str]:
    """Return sorted string paths of all readable images inside a directory."""
    folder = Path(directory_path)
    if not folder.exists() or not folder.is_dir():
        return []

    try:
        if recursive:
            folder_entries = sorted(entry for entry in folder.rglob("*") if entry.is_file())
        else:
            folder_entries = sorted(entry for entry in folder.iterdir() if entry.is_file())
    except (PermissionError, OSError):
        return []

    valid_paths: list[str] = [
        str(entry.resolve())
        for entry in folder_entries
        if is_valid_image_file(entry)
    ]
    return valid_paths


def _resolve_to_file_path(file_path_or_uri: str | Path) -> str:
    """Normalize a file path or file:// URI into an absolute local filesystem path."""
    raw_path_string = str(file_path_or_uri)
    if raw_path_string.startswith("file://"):
        parsed_url = urlparse(raw_path_string)
        combined_path = parsed_url.path
        if parsed_url.query:
            combined_path = f"{combined_path}?{parsed_url.query}"
        if parsed_url.fragment:
            combined_path = f"{combined_path}#{parsed_url.fragment}"
        return unquote(combined_path)
    return str(Path(raw_path_string).resolve())


def get_xrandr_monitors() -> list[dict[str, int]]:
    """Parse xrandr --listmonitors to get connected monitor geometries, with fallback to standard xrandr."""
    xrandr_bin = shutil.which("xrandr")
    if not xrandr_bin:
        return []
    try:
        xrandr_process = subprocess.run(
            [xrandr_bin, "--listmonitors"],
            capture_output=True,
            text=True,
            check=False,
        )
        monitors: list[dict[str, int]] = []
        if xrandr_process.returncode == 0:
            for line in xrandr_process.stdout.splitlines():
                line = line.strip()
                match = re.search(
                    r"\d+:\s+[+*]*\S+\s+(\d+)(?:/\d+)?x(\d+)(?:/\d+)?(?:\+?([+-]?\d+))(?:\+?([+-]?\d+))",
                    line,
                )
                if match:
                    monitor_width, monitor_height, offset_x, offset_y = (
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                        int(match.group(4)),
                    )
                    monitors.append(
                        {
                            "width": monitor_width,
                            "height": monitor_height,
                            "x": offset_x,
                            "y": offset_y,
                        }
                    )
        if not monitors:
            fallback_process = subprocess.run(
                [xrandr_bin],
                capture_output=True,
                text=True,
                check=False,
            )
            if fallback_process.returncode == 0:
                for line in fallback_process.stdout.splitlines():
                    match = re.search(
                        r"^\S+\s+connected\s+(?:primary\s+)?(\d+)x(\d+)(?:\+?([+-]?\d+))(?:\+?([+-]?\d+))",
                        line.strip(),
                    )
                    if match:
                        monitors.append(
                            {
                                "width": int(match.group(1)),
                                "height": int(match.group(2)),
                                "x": int(match.group(3)),
                                "y": int(match.group(4)),
                            }
                        )
        monitors.sort(key=lambda monitor_geometry: (monitor_geometry["x"], monitor_geometry["y"]))
        return monitors
    except Exception:
        return []


def get_wayland_monitors() -> list[dict[str, int]]:
    """Parse output from Wayland display query tools (wlr-randr, swaymsg, hyprctl)."""
    wlr_randr_executable = shutil.which("wlr-randr")
    if wlr_randr_executable:
        try:
            json_process = subprocess.run(
                [wlr_randr_executable, "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            if json_process.returncode == 0 and json_process.stdout.strip():
                json_data = json.loads(json_process.stdout)
                heads = json_data.get("heads", json_data if isinstance(json_data, list) else [])
                json_monitors: list[dict[str, int]] = []
                for head in heads:
                    if isinstance(head, dict) and head.get("enabled", True):
                        current_mode = head.get("mode") or {}
                        width = current_mode.get("width")
                        height = current_mode.get("height")
                        if width and height:
                            json_monitors.append(
                                {
                                    "width": int(width),
                                    "height": int(height),
                                    "x": int(head.get("x", 0)),
                                    "y": int(head.get("y", 0)),
                                }
                            )
                if json_monitors:
                    json_monitors.sort(key=lambda monitor_geometry: (monitor_geometry["x"], monitor_geometry["y"]))
                    return json_monitors
        except Exception:
            pass

        try:
            text_process = subprocess.run(
                [wlr_randr_executable],
                capture_output=True,
                text=True,
                check=False,
            )
            if text_process.returncode == 0 and text_process.stdout.strip():
                text_monitors: list[dict[str, int]] = []
                current_block_lines: list[str] = []

                def process_wlr_block(lines: list[str]) -> None:
                    if not lines:
                        return
                    block_content = "\n".join(lines)
                    if re.search(r"Enabled:\s*no", block_content, re.IGNORECASE):
                        return

                    position_match = re.search(r"Position:\s*([+-]?\d+),\s*([+-]?\d+)", block_content)
                    offset_x = int(position_match.group(1)) if position_match else 0
                    offset_y = int(position_match.group(2)) if position_match else 0

                    mode_match = re.search(r"(\d+)x(\d+)\s+px[^\n]*\(current\)", block_content)
                    if not mode_match:
                        mode_match = re.search(r"(\d+)x(\d+)\s+px[^\n]*current", block_content)

                    if mode_match:
                        text_monitors.append(
                            {
                                "width": int(mode_match.group(1)),
                                "height": int(mode_match.group(2)),
                                "x": offset_x,
                                "y": offset_y,
                            }
                        )

                for line in text_process.stdout.splitlines():
                    if line and not line[0].isspace():
                        process_wlr_block(current_block_lines)
                        current_block_lines = [line]
                    else:
                        current_block_lines.append(line)
                process_wlr_block(current_block_lines)

                if text_monitors:
                    text_monitors.sort(key=lambda monitor_geometry: (monitor_geometry["x"], monitor_geometry["y"]))
                    return text_monitors
        except Exception:
            pass

    swaymsg_executable = shutil.which("swaymsg")
    if swaymsg_executable:
        try:
            sway_process = subprocess.run(
                [swaymsg_executable, "-t", "get_outputs"],
                capture_output=True,
                text=True,
                check=False,
            )
            if sway_process.returncode == 0 and sway_process.stdout.strip():
                sway_outputs = json.loads(sway_process.stdout)
                sway_monitors: list[dict[str, int]] = []
                for output_item in sway_outputs:
                    if output_item.get("active", True):
                        rect = output_item.get("rect", {})
                        width = rect.get("width")
                        height = rect.get("height")
                        if width and height:
                            sway_monitors.append(
                                {
                                    "width": int(width),
                                    "height": int(height),
                                    "x": int(rect.get("x", 0)),
                                    "y": int(rect.get("y", 0)),
                                }
                            )
                if sway_monitors:
                    sway_monitors.sort(key=lambda monitor_geometry: (monitor_geometry["x"], monitor_geometry["y"]))
                    return sway_monitors
        except Exception:
            pass

    hyprctl_executable = shutil.which("hyprctl")
    if hyprctl_executable:
        try:
            hypr_process = subprocess.run(
                [hyprctl_executable, "monitors", "-j"],
                capture_output=True,
                text=True,
                check=False,
            )
            if hypr_process.returncode == 0 and hypr_process.stdout.strip():
                hypr_outputs = json.loads(hypr_process.stdout)
                hypr_monitors: list[dict[str, int]] = []
                for monitor_item in hypr_outputs:
                    if not monitor_item.get("disabled", False):
                        width = monitor_item.get("width")
                        height = monitor_item.get("height")
                        if width and height:
                            hypr_monitors.append(
                                {
                                    "width": int(width),
                                    "height": int(height),
                                    "x": int(monitor_item.get("x", 0)),
                                    "y": int(monitor_item.get("y", 0)),
                                }
                            )
                if hypr_monitors:
                    hypr_monitors.sort(key=lambda monitor_geometry: (monitor_geometry["x"], monitor_geometry["y"]))
                    return hypr_monitors
        except Exception:
            pass

    return []


def get_kde_desktop_count(qdbus_executable: str | None = None) -> int:
    """Query KDE Plasma via qdbus to get the count of active desktop containment objects."""
    selected_executable = qdbus_executable or find_kde_qdbus_executable()
    if not selected_executable:
        return 0
    command = [
        selected_executable,
        "org.kde.plasmashell",
        "/PlasmaShell",
        "org.kde.PlasmaShell.evaluateScript",
        "desktops().length",
    ]
    try:
        query_result = subprocess.run(command, capture_output=True, text=True, check=False)
        if query_result.returncode == 0 and query_result.stdout.strip().isdigit():
            return int(query_result.stdout.strip())
    except Exception:
        pass
    return 0


def get_xfce_monitor_properties() -> dict[str, list[str]]:
    """Query xfconf-query to discover all last-image properties grouped by monitor/screen."""
    list_process = subprocess.run(
        ["xfconf-query", "-c", XFCE_CHANNEL, "-l"],
        capture_output=True,
        text=True,
        check=False,
    )
    if list_process.returncode != 0:
        return {}

    monitor_groups: dict[str, list[str]] = {}
    seen_properties: set[str] = set()
    for line in list_process.stdout.splitlines():
        property_candidate = line.strip()
        if "last-image" in property_candidate and property_candidate not in seen_properties:
            seen_properties.add(property_candidate)
            match = re.search(r"/(screen\d+/monitor[^/]+)", property_candidate)
            if not match:
                match = re.search(r"/(monitor[^/]+)", property_candidate)
            if not match:
                match = re.search(r"/(screen\d+)", property_candidate)
            monitor_key = match.group(1) if match else property_candidate
            monitor_groups.setdefault(monitor_key, []).append(property_candidate)

    return monitor_groups


def detect_connected_monitors(desktop_environment: str | None = None) -> int:
    """Detect the number of connected monitors/displays across desktop environments."""
    if desktop_environment == "xfce":
        xfce_monitor_properties = get_xfce_monitor_properties()
        if xfce_monitor_properties:
            return len(xfce_monitor_properties)
    elif desktop_environment == "kde":
        kde_count = get_kde_desktop_count()
        if kde_count > 0:
            return kde_count

    is_wayland = bool(
        os.environ.get("WAYLAND_DISPLAY")
        or os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    )

    if is_wayland:
        wayland_monitors = get_wayland_monitors()
        if wayland_monitors:
            return len(wayland_monitors)
        xrandr_monitors = get_xrandr_monitors()
        if xrandr_monitors:
            return len(xrandr_monitors)
    else:
        xrandr_monitors = get_xrandr_monitors()
        if xrandr_monitors:
            return len(xrandr_monitors)
        wayland_monitors = get_wayland_monitors()
        if wayland_monitors:
            return len(wayland_monitors)

    try:
        drm_statuses = list(Path("/sys/class/drm").glob("*/status"))
        connected_count = 0
        for status_file in drm_statuses:
            try:
                if status_file.read_text(encoding="utf-8").strip() == "connected":
                    connected_count += 1
            except (OSError, UnicodeDecodeError):
                continue
        if connected_count > 0:
            return connected_count
    except Exception:
        pass

    return 1


def get_effective_monitor_count(
    desktop_environment: str | None = None,
    multi_monitor: bool = False,
) -> int:
    """Return monitor count, guaranteeing at least 2 when multi-monitor is requested."""
    detected = detect_connected_monitors(desktop_environment)
    if multi_monitor:
        return max(2, detected)
    return 1


_SPANNED_TOGGLE: int = 0


def create_spanned_wallpaper(
    wallpapers: Sequence[str | Path],
    output_path: Path | str | None = None,
) -> Path:
    """Stitch multiple wallpapers into a single spanned panoramic image using Pillow."""
    global _SPANNED_TOGGLE
    if not wallpapers:
        raise ValueError("At least one wallpaper path is required to create spanned wallpaper.")

    resolved_paths = [_resolve_to_file_path(wallpaper_path) for wallpaper_path in wallpapers]
    if len(resolved_paths) == 1:
        return Path(resolved_paths[0])

    if not HAS_PILLOW:
        return Path(resolved_paths[0])

    cache_dir = Path.home() / ".cache" / "wchanger"
    cache_dir.mkdir(parents=True, exist_ok=True)
    if output_path is not None:
        target_output = Path(output_path)
        target_output.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Alternate between two filenames so desktop environments (GNOME, Cinnamon, MATE)
        # detect URI change on every cycle and reload the wallpaper without caching
        _SPANNED_TOGGLE = 1 - _SPANNED_TOGGLE
        target_output = cache_dir / f"multimonitor_spanned_{_SPANNED_TOGGLE}.png"

    is_wayland = bool(
        os.environ.get("WAYLAND_DISPLAY")
        or os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    )
    if is_wayland:
        monitors = get_wayland_monitors() or get_xrandr_monitors()
    else:
        monitors = get_xrandr_monitors() or get_wayland_monitors()

    opened_images: list[Image.Image] = []
    try:
        for wallpaper_path in resolved_paths:
            opened_images.append(Image.open(wallpaper_path).convert("RGB"))

        resample_filter = getattr(Image, "Resampling", Image).LANCZOS

        if monitors:
            minimum_x = min(monitor_geometry["x"] for monitor_geometry in monitors)
            minimum_y = min(monitor_geometry["y"] for monitor_geometry in monitors)
            maximum_x = max(monitor_geometry["x"] + monitor_geometry["width"] for monitor_geometry in monitors)
            maximum_y = max(monitor_geometry["y"] + monitor_geometry["height"] for monitor_geometry in monitors)
            canvas_width = max(1, maximum_x - minimum_x)
            canvas_height = max(1, maximum_y - minimum_y)
            canvas = Image.new("RGB", (canvas_width, canvas_height), color=(0, 0, 0))

            for monitor_index, monitor_geometry in enumerate(monitors):
                source_image = opened_images[monitor_index % len(opened_images)]
                if hasattr(ImageOps, "fit"):
                    fitted = ImageOps.fit(
                        source_image,
                        (monitor_geometry["width"], monitor_geometry["height"]),
                        method=resample_filter,
                    )
                else:
                    fitted = source_image.resize(
                        (monitor_geometry["width"], monitor_geometry["height"]),
                        resample_filter,
                    )
                canvas.paste(
                    fitted,
                    (monitor_geometry["x"] - minimum_x, monitor_geometry["y"] - minimum_y),
                )
        else:
            target_height = max(source_image.height for source_image in opened_images)
            resized_images: list[Image.Image] = []
            total_width = 0

            for source_image in opened_images:
                aspect = source_image.width / source_image.height if source_image.height > 0 else 1.0
                new_width = max(1, int(target_height * aspect))
                resized = source_image.resize((new_width, target_height), resample_filter)
                resized_images.append(resized)
                total_width += new_width

            canvas = Image.new("RGB", (total_width, target_height), color=(0, 0, 0))
            offset_x = 0
            for resized_image in resized_images:
                canvas.paste(resized_image, (offset_x, 0))
                offset_x += resized_image.width

        canvas.save(target_output, format="PNG")
        return target_output
    except Exception as error:
        logging.warning(f"Failed to create spanned wallpaper: {error}")
        return Path(resolved_paths[0])
    finally:
        for source_image in opened_images:
            try:
                source_image.close()
            except Exception:
                pass


def set_lxqt_multimonitor_config(file_paths: Sequence[str]) -> bool:
    """Update LXQt ~/.config/pcmanfm-qt/lxqt/settings.conf for multiple monitors."""
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "pcmanfm-qt" / "lxqt"
    config_file = config_dir / "settings.conf"
    if not config_dir.exists():
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False

    lines: list[str] = []
    if config_file.exists():
        try:
            lines = config_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []

    sections_to_add: dict[str, str] = {}
    for screen_index, wallpaper_path in enumerate(file_paths):
        resolved = _resolve_to_file_path(wallpaper_path)
        sections_to_add[f"Desktop_Screen_{screen_index}"] = resolved
        if screen_index == 0:
            sections_to_add["Desktop"] = resolved
            sections_to_add["Desktop_Screen0"] = resolved
        else:
            sections_to_add[f"Desktop_Screen{screen_index}"] = resolved

    new_lines: list[str] = []
    current_section: str | None = None
    handled_sections: set[str] = set()
    skip_wallpaper_line = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1]
            if current_section in sections_to_add:
                handled_sections.add(current_section)
                new_lines.append(line)
                new_lines.append(f"Wallpaper={sections_to_add[current_section]}")
                skip_wallpaper_line = True
                continue
            else:
                skip_wallpaper_line = False
        elif skip_wallpaper_line and stripped.startswith("Wallpaper="):
            continue
        new_lines.append(line)

    for section_name, wallpaper_path in sections_to_add.items():
        if section_name not in handled_sections:
            new_lines.append(f"\n[{section_name}]")
            new_lines.append(f"Wallpaper={wallpaper_path}")

    try:
        config_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def set_gnome_background(file_uri: str | Sequence[str], theme: str | None = None) -> bool:
    """Apply wallpaper URI to GNOME background schema."""
    if isinstance(file_uri, (str, Path)):
        wallpaper_uris = [str(file_uri)]
    else:
        wallpaper_uris = [str(uri_item) for uri_item in file_uri]

    if len(wallpaper_uris) > 1:
        spanned_path = create_spanned_wallpaper(wallpaper_uris)
        target_uri = Path(spanned_path).resolve().as_uri()
        subprocess.run(
            ["gsettings", "set", GNOME_SCHEMA, "picture-options", "spanned"],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        target_uri = wallpaper_uris[0]

    if not target_uri.startswith("file://"):
        target_uri = Path(target_uri).resolve().as_uri()

    gsettings_commands: list[list[str]] = []

    if theme == "dark":
        gsettings_commands.append(["gsettings", "set", GNOME_SCHEMA, GNOME_KEY_DARK, target_uri])
    elif theme == "light":
        gsettings_commands.append(["gsettings", "set", GNOME_SCHEMA, GNOME_KEY_LIGHT, target_uri])
    else:
        gsettings_commands.append(["gsettings", "set", GNOME_SCHEMA, GNOME_KEY_LIGHT, target_uri])
        gsettings_commands.append(["gsettings", "set", GNOME_SCHEMA, GNOME_KEY_DARK, target_uri])

    all_commands_succeeded = True
    for command in gsettings_commands:
        execution_result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if execution_result.returncode != 0:
            # On GNOME < 42, picture-uri-dark does not exist. If theme was not explicitly
            # specified, don't fail as long as the primary light picture-uri succeeded.
            if theme is None and GNOME_KEY_DARK in command:
                continue
            all_commands_succeeded = False

    return all_commands_succeeded


def set_cinnamon_background(file_uri: str | Sequence[str]) -> bool:
    """Apply wallpaper URI to Cinnamon background schema."""
    if isinstance(file_uri, (str, Path)):
        wallpaper_uris = [str(file_uri)]
    else:
        wallpaper_uris = [str(uri_item) for uri_item in file_uri]

    if len(wallpaper_uris) > 1:
        spanned_path = create_spanned_wallpaper(wallpaper_uris)
        target_uri = Path(spanned_path).resolve().as_uri()
        subprocess.run(
            ["gsettings", "set", CINNAMON_SCHEMA, "picture-options", "spanned"],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        target_uri = wallpaper_uris[0]

    if not target_uri.startswith("file://"):
        target_uri = Path(target_uri).resolve().as_uri()

    command = ["gsettings", "set", CINNAMON_SCHEMA, CINNAMON_KEY, target_uri]
    execution_result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return execution_result.returncode == 0


def set_kde_background(
    file_uri: str | Sequence[str],
    qdbus_executable: str | None = None,
) -> bool:
    """Apply wallpaper URI(s) to KDE Plasma desktop via qdbus evaluateScript."""
    selected_executable = qdbus_executable or find_kde_qdbus_executable()
    if not selected_executable:
        return False

    if isinstance(file_uri, (str, Path)):
        wallpaper_uris = [str(file_uri)]
        is_single = True
    else:
        wallpaper_uris = [str(uri_item) for uri_item in file_uri]
        is_single = len(wallpaper_uris) == 1

    if is_single:
        single_uri = wallpaper_uris[0]
        if not single_uri.startswith("file://"):
            single_uri = Path(single_uri).resolve().as_uri()

        safe_uri = (
            single_uri.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "")
            .replace("\r", "")
        )

        script_content = (
            "const allDesktops = desktops();\n"
            "for (const desktop of allDesktops) {\n"
            '    desktop.wallpaperPlugin = "org.kde.image";\n'
            '    desktop.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");\n'
            f'    desktop.writeConfig("Image", "{safe_uri}");\n'
            '    desktop.reloadConfig();\n'
            "}\n"
        )
    else:
        normalized_uris: list[str] = []
        for raw_uri in wallpaper_uris:
            if not raw_uri.startswith("file://"):
                normalized_uri = Path(raw_uri).resolve().as_uri()
            else:
                normalized_uri = raw_uri
            safe_uri = (
                normalized_uri.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "")
                .replace("\r", "")
            )
            normalized_uris.append(safe_uri)

        js_array_items = ", ".join(f'"{wallpaper_uri}"' for wallpaper_uri in normalized_uris)
        script_content = (
            "const allDesktops = desktops();\n"
            f"const wallpaperList = [{js_array_items}];\n"
            "for (let desktopIndex = 0; desktopIndex < allDesktops.length; desktopIndex++) {\n"
            "    const desktop = allDesktops[desktopIndex];\n"
            "    const imageUri = wallpaperList[desktopIndex % wallpaperList.length];\n"
            '    desktop.wallpaperPlugin = "org.kde.image";\n'
            '    desktop.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");\n'
            '    desktop.writeConfig("Image", imageUri);\n'
            "    desktop.reloadConfig();\n"
            "}\n"
        )

    command = [
        selected_executable,
        "org.kde.plasmashell",
        "/PlasmaShell",
        "org.kde.PlasmaShell.evaluateScript",
        script_content,
    ]

    execution_result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return execution_result.returncode == 0


def set_xfce_background(file_path: str | Sequence[str]) -> bool:
    """Apply wallpaper path(s) to XFCE desktop via xfconf-query."""
    if isinstance(file_path, (str, Path)):
        wallpapers = [_resolve_to_file_path(file_path)]
    else:
        wallpapers = [_resolve_to_file_path(wallpaper_item) for wallpaper_item in file_path]

    if not wallpapers:
        return False

    list_process = subprocess.run(
        ["xfconf-query", "-c", XFCE_CHANNEL, "-l"],
        capture_output=True,
        text=True,
        check=False,
    )

    discovered_properties: list[str] = []
    monitor_for_property: list[str] = []
    distinct_monitors: list[str] = []

    if list_process.returncode == 0:
        seen_properties = set()
        for line in list_process.stdout.splitlines():
            property_candidate = line.strip()
            if "last-image" in property_candidate and property_candidate not in seen_properties:
                seen_properties.add(property_candidate)
                discovered_properties.append(property_candidate)
                match = re.search(r"/(screen\d+/monitor[^/]+)", property_candidate)
                if not match:
                    match = re.search(r"/(monitor[^/]+)", property_candidate)
                if not match:
                    match = re.search(r"/(screen\d+)", property_candidate)
                monitor_key = match.group(1) if match else property_candidate
                if monitor_key not in distinct_monitors:
                    distinct_monitors.append(monitor_key)
                monitor_for_property.append(monitor_key)

    if not discovered_properties:
        any_success = False
        for fallback_index, fallback_property in enumerate(XFCE_FALLBACK_PROPERTIES):
            assigned_fallback = wallpapers[fallback_index % len(wallpapers)]
            fallback_result = subprocess.run(
                ["xfconf-query", "-c", XFCE_CHANNEL, "-p", fallback_property, "-s", assigned_fallback],
                capture_output=True,
                text=True,
                check=False,
            )
            if fallback_result.returncode == 0:
                any_success = True
                if len(wallpapers) == 1:
                    return True
        return any_success

    all_properties_succeeded = True
    for target_property, monitor_key in zip(discovered_properties, monitor_for_property):
        monitor_index = distinct_monitors.index(monitor_key)
        assigned_wallpaper = wallpapers[monitor_index % len(wallpapers)]
        set_result = subprocess.run(
            ["xfconf-query", "-c", XFCE_CHANNEL, "-p", target_property, "-s", assigned_wallpaper],
            capture_output=True,
            text=True,
            check=False,
        )
        if set_result.returncode != 0:
            all_properties_succeeded = False

    return all_properties_succeeded


def set_mate_background(file_path: str | Sequence[str]) -> bool:
    """Apply wallpaper path(s) to MATE background schema."""
    if isinstance(file_path, (str, Path)):
        paths = [str(file_path)]
    else:
        paths = [str(path_item) for path_item in file_path]

    if len(paths) > 1:
        spanned_path = create_spanned_wallpaper(paths)
        resolved_path = _resolve_to_file_path(spanned_path)
        subprocess.run(
            ["gsettings", "set", MATE_SCHEMA, "picture-options", "spanned"],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        resolved_path = _resolve_to_file_path(paths[0])

    command = ["gsettings", "set", MATE_SCHEMA, MATE_KEY, resolved_path]
    execution_result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return execution_result.returncode == 0


def set_lxqt_background(file_path: str | Sequence[str]) -> bool:
    """Apply wallpaper path(s) to LXQt desktop via pcmanfm-qt."""
    if isinstance(file_path, (str, Path)):
        paths = [str(file_path)]
    else:
        paths = [str(path_item) for path_item in file_path]

    if len(paths) > 1:
        lxqt_updated = set_lxqt_multimonitor_config(paths)
        if lxqt_updated:
            reconfigure_result = subprocess.run(
                ["pcmanfm-qt", "--reconfigure"],
                capture_output=True,
                text=True,
                check=False,
            )
            if reconfigure_result.returncode == 0:
                return True
        spanned_path = create_spanned_wallpaper(paths)
        resolved_path = _resolve_to_file_path(spanned_path)
    else:
        resolved_path = _resolve_to_file_path(paths[0])

    command = ["pcmanfm-qt", f"--set-wallpaper={resolved_path}"]
    execution_result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return execution_result.returncode == 0


# Backward compatibility aliases
set_gnome_wallpaper = set_gnome_background
set_cinnamon_wallpaper = set_cinnamon_background
set_kde_wallpaper = set_kde_background
set_xfce_wallpaper = set_xfce_background
set_mate_wallpaper = set_mate_background
set_lxqt_wallpaper = set_lxqt_background


# Online Wallpaper Sources Fetchers
def _fetch_url_with_retry(
    request: Request,
    timeout: int = 15,
    max_retries: int = 3,
    retry_delay_seconds: float = 0.5,
) -> bytes:
    """Execute urlopen with automatic retry on transient network failures."""
    last_network_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as http_error:
            last_network_error = http_error
            # Only retry transient 5xx server-side errors
            if http_error.code in (500, 502, 503, 504) and attempt < max_retries - 1:
                time.sleep(retry_delay_seconds * (2 ** attempt))
                continue
            raise
        except (URLError, TimeoutError, ConnectionError, OSError) as network_error:
            last_network_error = network_error
            if attempt < max_retries - 1:
                time.sleep(retry_delay_seconds * (2 ** attempt))
                continue
            raise
    if last_network_error:
        raise last_network_error
    return b""


def fetch_wallhaven_url(max_retries: int = 3, retry_delay_seconds: float = 0.5) -> str:
    """Fetch a random top wallpaper image URL from the Wallhaven API with retries."""
    api_url = (
        "https://wallhaven.cc/api/v1/search?sorting=toplist&topRange=1d&purity=100&atleast=1920x1080"
    )
    request = Request(api_url, headers={"User-Agent": f"AwesomeWallpaperChanger/{VERSION} (Linux; x86_64)"})
    raw_payload = _fetch_url_with_retry(
        request,
        timeout=15,
        max_retries=max_retries,
        retry_delay_seconds=retry_delay_seconds,
    )
    payload = json.loads(raw_payload.decode("utf-8"))
    wallpapers = payload.get("data", [])
    if not wallpapers:
        raise ValueError("No wallpapers found in Wallhaven API response.")
    selected = random.choice(wallpapers)
    image_url = selected.get("path")
    if not image_url:
        raise ValueError("Wallhaven entry missing image path.")
    return str(image_url)


def fetch_bing_url(max_retries: int = 3, retry_delay_seconds: float = 0.5) -> str:
    """Fetch today's Bing daily photo URL with retries."""
    api_url = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US"
    request = Request(api_url, headers={"User-Agent": f"AwesomeWallpaperChanger/{VERSION} (Linux; x86_64)"})
    raw_payload = _fetch_url_with_retry(
        request,
        timeout=15,
        max_retries=max_retries,
        retry_delay_seconds=retry_delay_seconds,
    )
    payload = json.loads(raw_payload.decode("utf-8"))
    images = payload.get("images", [])
    if not images:
        raise ValueError("No images found in Bing API response.")
    image_relative_url = images[0].get("url")
    if not image_relative_url:
        raise ValueError("Bing API response missing image url.")
    return f"https://www.bing.com{image_relative_url}"


def fetch_picsum_url() -> str:
    """Fetch a random photo URL from Picsum."""
    random_seed = random.randint(1, 1000000)
    return f"https://picsum.photos/1920/1080?random={random_seed}"


def fetch_loremflickr_url() -> str:
    """Fetch a nature photo URL from LoremFlickr."""
    random_lock = random.randint(1, 1000000)
    return f"https://loremflickr.com/1920/1080/nature?lock={random_lock}"


ONLINE_PROVIDERS = {
    "wallhaven": fetch_wallhaven_url,
    "bing": fetch_bing_url,
    "picsum": fetch_picsum_url,
    "loremflickr": fetch_loremflickr_url,
}


def download_online_wallpaper(
    image_url: str,
    destination_path: Path,
    max_retries: int = 3,
    retry_delay_seconds: float = 0.5,
) -> Path:
    """Download remote image from URL and write to local destination cache with retries."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    request = Request(image_url, headers={"User-Agent": f"AwesomeWallpaperChanger/{VERSION} (Linux; x86_64)"})
    image_data = _fetch_url_with_retry(
        request,
        timeout=20,
        max_retries=max_retries,
        retry_delay_seconds=retry_delay_seconds,
    )
    if not image_data:
        raise ValueError("Received empty image content from provider.")
    destination_path.write_bytes(image_data)
    return destination_path


def cleanup_download_cache(
    cache_dir: Path | str,
    keep_last: int = DEFAULT_KEEP_LAST,
) -> list[Path]:
    """Keep only the most recent 'keep_last' image files in cache_dir, deleting older ones."""
    folder = Path(cache_dir)
    if not folder.exists() or not folder.is_dir():
        return []

    effective_keep_limit = max(1, keep_last)

    try:
        image_files: list[Path] = [
            entry
            for entry in folder.iterdir()
            if entry.is_file() and entry.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        ]
    except (PermissionError, OSError) as error:
        logging.warning(f"Failed to scan cache directory '{folder}' for cleanup: {error}")
        return []

    if len(image_files) <= effective_keep_limit:
        return []

    try:
        image_files.sort(key=lambda file_path: file_path.stat().st_mtime, reverse=True)
    except OSError as error:
        logging.warning(f"Failed to inspect timestamps in cache directory '{folder}': {error}")
        return []

    deleted_files: list[Path] = []
    for stale_file in image_files[effective_keep_limit:]:
        try:
            stale_file.unlink(missing_ok=True)
            deleted_files.append(stale_file)
        except OSError as error:
            logging.warning(f"Failed to delete old cached wallpaper '{stale_file}': {error}")

    return deleted_files


def format_network_error(provider: str, error: Exception) -> str:
    """Format a user-friendly error message when network requests fail."""
    if isinstance(error, HTTPError):
        return (
            f"Server returned HTTP error {error.code} ({error.reason}) "
            f"while requesting from '{provider}'."
        )
    if isinstance(error, URLError):
        reason = getattr(error, "reason", error)
        return (
            f"Unable to connect to '{provider}' ({reason}). "
            "Please check your internet connection."
        )
    return f"Failed to fetch wallpaper from '{provider}': {error}"


def set_wallpaper_for_desktop(
    desktop_environment: str,
    wallpaper_path: Path | str | Sequence[Path | str],
    color_theme: str | None = None,
) -> tuple[bool, str]:
    """Apply wallpaper to the current desktop environment.

    Returns a tuple of (success_status, status_message).
    """
    if isinstance(wallpaper_path, (list, tuple)):
        is_multi = len(wallpaper_path) > 1
        path_list = [str(wallpaper_item) for wallpaper_item in wallpaper_path]
    else:
        is_multi = False
        path_list = [str(wallpaper_path)]

    operation_success = False
    status_message = ""

    if not is_multi:
        single_path = path_list[0]
        wallpaper_file = Path(single_path)
        file_uri = wallpaper_file.resolve().as_uri()
        resolved_path_string = single_path

        if desktop_environment == "gnome":
            operation_success = set_gnome_background(file_uri, color_theme)
            if color_theme is not None:
                status_message = f"Wallpaper changed on GNOME to {wallpaper_path} in {color_theme} theme."
            else:
                status_message = f"Wallpaper changed on GNOME to {wallpaper_path} in both dark and light themes."
        elif desktop_environment == "cinnamon":
            operation_success = set_cinnamon_background(file_uri)
            status_message = f"Wallpaper changed on Cinnamon to {wallpaper_path}."
        elif desktop_environment == "kde":
            operation_success = set_kde_background(file_uri)
            status_message = f"Wallpaper changed on KDE Plasma to {wallpaper_path}."
        elif desktop_environment == "xfce":
            operation_success = set_xfce_background(resolved_path_string)
            status_message = f"Wallpaper changed on XFCE to {wallpaper_path}."
        elif desktop_environment == "mate":
            operation_success = set_mate_background(resolved_path_string)
            status_message = f"Wallpaper changed on MATE to {wallpaper_path}."
        elif desktop_environment == "lxqt":
            operation_success = set_lxqt_background(resolved_path_string)
            status_message = f"Wallpaper changed on LXQt to {wallpaper_path}."
    else:
        count = len(path_list)
        formatted_list = ", ".join(path_list)
        if desktop_environment == "gnome":
            operation_success = set_gnome_background(path_list, color_theme)
            if color_theme is not None:
                status_message = f"Wallpapers changed on GNOME across {count} monitors to [{formatted_list}] in {color_theme} theme."
            else:
                status_message = f"Wallpapers changed on GNOME across {count} monitors to [{formatted_list}] in both dark and light themes."
        elif desktop_environment == "cinnamon":
            operation_success = set_cinnamon_background(path_list)
            status_message = f"Wallpapers changed on Cinnamon across {count} monitors to [{formatted_list}]."
        elif desktop_environment == "kde":
            operation_success = set_kde_background(path_list)
            status_message = f"Wallpapers changed on KDE Plasma across {count} monitors to [{formatted_list}]."
        elif desktop_environment == "xfce":
            operation_success = set_xfce_background(path_list)
            status_message = f"Wallpapers changed on XFCE across {count} monitors to [{formatted_list}]."
        elif desktop_environment == "mate":
            operation_success = set_mate_background(path_list)
            status_message = f"Wallpapers changed on MATE across {count} monitors to [{formatted_list}]."
        elif desktop_environment == "lxqt":
            operation_success = set_lxqt_background(path_list)
            status_message = f"Wallpapers changed on LXQt across {count} monitors to [{formatted_list}]."

    return operation_success, status_message


def run_wallpaper_cycle(
    desktop_environment: str,
    wallpapers: Sequence[str],
    pause_seconds: int,
    repetition: bool,
    output_mode: str,
    color_theme: str | None = None,
    shuffle: bool = False,
    multi_monitor: bool = False,
) -> None:
    """Cycle wallpapers in a clean loop with graceful interruption handling."""
    playlist = list(wallpapers)
    if shuffle:
        random.shuffle(playlist)

    try:
        while True:
            if not multi_monitor:
                for wallpaper in playlist:
                    wallpaper_file = Path(wallpaper)
                    if not wallpaper_file.exists():
                        skip_message = f"Skipping missing wallpaper: {wallpaper}"
                        if output_mode == "log":
                            logging.warning(skip_message)
                        else:
                            print(f"{YELLOW}{skip_message}{RESET}")
                        continue

                    operation_success, status_message = set_wallpaper_for_desktop(
                        desktop_environment=desktop_environment,
                        wallpaper_path=wallpaper,
                        color_theme=color_theme,
                    )

                    if operation_success:
                        if output_mode == "log":
                            logging.info(status_message)
                        else:
                            print(f"{MAGENTA}{status_message}{RESET}")
                    else:
                        failure_message = f"Failed to set wallpaper to {wallpaper}"
                        if output_mode == "log":
                            logging.error(failure_message)
                        else:
                            print(f"{RED}{failure_message}{RESET}", file=sys.stderr)

                    time.sleep(pause_seconds)
            else:
                monitor_count = get_effective_monitor_count(desktop_environment, multi_monitor=True)
                batch_step = monitor_count
                for batch_start_index in range(0, len(playlist), batch_step):
                    batch = [
                        playlist[(batch_start_index + offset) % len(playlist)]
                        for offset in range(monitor_count)
                    ]
                    existing_batch = [wallpaper_candidate for wallpaper_candidate in batch if Path(wallpaper_candidate).exists()]
                    if not existing_batch:
                        skip_message = f"Skipping missing wallpapers: {batch}"
                        if output_mode == "log":
                            logging.warning(skip_message)
                        else:
                            print(f"{YELLOW}{skip_message}{RESET}")
                        continue

                    while len(existing_batch) < monitor_count and existing_batch:
                        existing_batch.append(existing_batch[0])

                    operation_success, status_message = set_wallpaper_for_desktop(
                        desktop_environment=desktop_environment,
                        wallpaper_path=existing_batch,
                        color_theme=color_theme,
                    )

                    if operation_success:
                        if output_mode == "log":
                            logging.info(status_message)
                        else:
                            print(f"{MAGENTA}{status_message}{RESET}")
                    else:
                        failure_message = f"Failed to set wallpapers across monitors: {existing_batch}"
                        if output_mode == "log":
                            logging.error(failure_message)
                        else:
                            print(f"{RED}{failure_message}{RESET}", file=sys.stderr)

                    time.sleep(pause_seconds)

            if not repetition:
                completion_message = "Program exited after setting all wallpapers."
                if output_mode == "log":
                    logging.info(completion_message)
                else:
                    print(f"{MAGENTA}{completion_message}{RESET}")
                sys.exit(0)

            if shuffle:
                random.shuffle(playlist)

    except KeyboardInterrupt:
        shutdown_message = "Program stopped by user. Exiting..."
        if output_mode == "log":
            logging.info("Wallpaper changer stopped by user.")
        else:
            print(f"\n{YELLOW}[!] {shutdown_message}{RESET}")
        sys.exit(0)


def run_online_wallpaper_cycle(
    desktop_environment: str,
    provider: str,
    pause_seconds: int,
    repetition: bool,
    output_mode: str,
    color_theme: str | None = None,
    cache_dir: Path | None = None,
    keep_last: int = DEFAULT_KEEP_LAST,
    multi_monitor: bool = False,
) -> None:
    """Cycle wallpapers from an online provider in a loop with error handling and cache cleanup."""
    provider_key = provider.lower()
    fetcher = ONLINE_PROVIDERS.get(provider_key)
    if fetcher is None:
        raise ValueError(f"Unknown online provider '{provider}'.")

    target_cache_dir = cache_dir if cache_dir is not None else DEFAULT_CACHE_DIR
    target_cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            cycle_succeeded = False
            try:
                if not multi_monitor:
                    if output_mode != "log":
                        print(f"{CYAN}[i] Fetching online wallpaper from '{provider_key}'...{RESET}")

                    image_url = fetcher()

                    parsed_path = Path(urlparse(image_url).path).suffix.lower()
                    extension = parsed_path if parsed_path in SUPPORTED_IMAGE_EXTENSIONS else ".jpg"

                    timestamp_marker = time.strftime("%Y%m%d_%H%M%S")
                    random_identifier = random.randint(1000, 9999)
                    cache_file = target_cache_dir / f"wallpaper_{provider_key}_{timestamp_marker}_{random_identifier}{extension}"

                    download_online_wallpaper(image_url, cache_file)

                    operation_success, status_message = set_wallpaper_for_desktop(
                        desktop_environment=desktop_environment,
                        wallpaper_path=cache_file,
                        color_theme=color_theme,
                    )

                    if operation_success:
                        cycle_succeeded = True
                        log_detail = f"Online wallpaper updated from {provider_key}: {image_url}"
                        if output_mode == "log":
                            logging.info(log_detail)
                        else:
                            print(f"{MAGENTA}{status_message}{RESET}")

                        pruned_files = cleanup_download_cache(target_cache_dir, keep_last=keep_last)
                        if pruned_files and output_mode == "log":
                            logging.info(
                                f"Cleaned {len(pruned_files)} old cached wallpaper(s) (retaining last {keep_last})."
                            )
                    else:
                        failure_message = f"Failed to set online wallpaper to desktop ({desktop_environment})."
                        if output_mode == "log":
                            logging.error(failure_message)
                        else:
                            print(f"{RED}{failure_message}{RESET}", file=sys.stderr)
                else:
                    monitor_count = get_effective_monitor_count(desktop_environment, multi_monitor=True)
                    if output_mode != "log":
                        print(
                            f"{CYAN}[i] Fetching {monitor_count} online wallpapers from '{provider_key}' for multi-monitor...{RESET}"
                        )

                    cache_files: list[Path] = []
                    wallpaper_urls: list[str] = []
                    for monitor_index in range(monitor_count):
                        image_url = fetcher()
                        wallpaper_urls.append(image_url)
                        parsed_path = Path(urlparse(image_url).path).suffix.lower()
                        extension = parsed_path if parsed_path in SUPPORTED_IMAGE_EXTENSIONS else ".jpg"
                        timestamp_marker = time.strftime("%Y%m%d_%H%M%S")
                        random_identifier = random.randint(1000, 9999)
                        cache_file = target_cache_dir / f"wallpaper_{provider_key}_{timestamp_marker}_{random_identifier}_m{monitor_index}{extension}"
                        download_online_wallpaper(image_url, cache_file)
                        cache_files.append(cache_file)

                    operation_success, status_message = set_wallpaper_for_desktop(
                        desktop_environment=desktop_environment,
                        wallpaper_path=cache_files,
                        color_theme=color_theme,
                    )

                    if operation_success:
                        cycle_succeeded = True
                        log_detail = f"Online wallpapers updated from {provider_key} across {monitor_count} monitors: {wallpaper_urls}"
                        if output_mode == "log":
                            logging.info(log_detail)
                        else:
                            print(f"{MAGENTA}{status_message}{RESET}")

                        pruned_files = cleanup_download_cache(target_cache_dir, keep_last=keep_last)
                        if pruned_files and output_mode == "log":
                            logging.info(
                                f"Cleaned {len(pruned_files)} old cached wallpaper(s) (retaining last {keep_last})."
                            )
                    else:
                        failure_message = f"Failed to set online wallpapers to desktop ({desktop_environment})."
                        if output_mode == "log":
                            logging.error(failure_message)
                        else:
                            print(f"{RED}{failure_message}{RESET}", file=sys.stderr)

            except (URLError, HTTPError, TimeoutError, ConnectionError, OSError, ValueError) as network_error:
                error_details = format_network_error(provider_key, network_error)
                if output_mode == "log":
                    logging.error(f"Network error with online provider '{provider_key}': {error_details}")
                else:
                    click.secho(f"[!] Network Error: {error_details}", fg="red", bold=True, err=True)

                if not repetition:
                    sys.exit(1)

            if not repetition:
                if cycle_succeeded:
                    completion_message = f"Online wallpaper from '{provider_key}' applied successfully."
                    if output_mode == "log":
                        logging.info(completion_message)
                    else:
                        print(f"{MAGENTA}{completion_message}{RESET}")
                    sys.exit(0)
                else:
                    sys.exit(1)

            time.sleep(pause_seconds)

    except KeyboardInterrupt:
        shutdown_message = "Program stopped by user. Exiting..."
        if output_mode == "log":
            logging.info("Online wallpaper changer stopped by user.")
        else:
            print(f"\n{YELLOW}[!] {shutdown_message}{RESET}")
        sys.exit(0)


def show_auto_start_failure_and_exit() -> None:
    """Print troubleshooting advice directing users to README on service setup failure."""
    click.secho(
        "\n"
        + "=" * 70 + "\n"
        + "[!] Automatic systemd service installation could not be completed.\n"
        + "[!] Please check the 'Starting on Boot (Systemd Startup Service)'\n"
        + "    section in README.md to configure the service manually.\n"
        + "=" * 70 + "\n",
        fg="yellow",
        bold=True,
        err=True,
    )
    sys.exit(1)


def setup_install_autostart_service(
    desktop_override: str | None = None,
    color_theme: str | None = None,
    initial_photo_path: Path | None = None,
    online_provider: str | None = None,
    shuffle: bool = False,
    recursive: bool = False,
    keep_last: int | None = None,
    config_settings: dict[str, object] | None = None,
    multi_monitor: bool = False,
) -> None:
    """Interactive wizard to generate and install a systemd unit via sudo tee."""
    click.secho(
        f"{CYAN}\n============================================\n"
        "  Automatic Startup Service Setup Wizard   \n"
        f"============================================\n{RESET}"
    )

    if not shutil.which("systemctl"):
        click.secho("Error: 'systemctl' command not found on this machine.", fg="red", err=True)
        show_auto_start_failure_and_exit()

    settings_dict = config_settings or {}
    default_pause = DEFAULT_PAUSE_SECONDS
    if "pause" in settings_dict and settings_dict["pause"] is not None:
        try:
            default_pause = parse_duration_to_seconds(settings_dict["pause"])
        except ValueError:
            default_pause = DEFAULT_PAUSE_SECONDS

    pause_seconds = click.prompt(
        f"{GREEN}[+] Enter pause duration between changing wallpapers (e.g. 60, 10m, 1h){RESET}",
        type=DURATION_TYPE,
        default=default_pause,
        show_default=True,
    )

    chosen_directory: Path | None = None
    if online_provider is None:
        default_directory = DEFAULT_WALLPAPERS_DIR
        if initial_photo_path is not None:
            default_directory = initial_photo_path
        elif "folder" in settings_dict and settings_dict["folder"]:
            configured_folder = Path(os.path.expanduser(str(settings_dict["folder"])))
            if configured_folder.exists() and configured_folder.is_dir():
                default_directory = configured_folder

        while True:
            chosen_directory = click.prompt(
                f"{GREEN}[+] Enter path to directory containing wallpapers{RESET}",
                type=click.Path(file_okay=False, dir_okay=True, resolve_path=True, path_type=Path),
                default=default_directory,
                show_default=True,
            )
            if not chosen_directory.exists() or not chosen_directory.is_dir():
                click.secho(f"[!] '{chosen_directory}' is not a valid directory. Please try again.", fg="red", err=True)
                continue

            discovered_wallpapers = file_validator(chosen_directory, recursive=recursive)
            if not discovered_wallpapers:
                click.secho(f"[!] No valid image files found in '{chosen_directory}'. Please try another path.", fg="red", err=True)
                continue
            break
    else:
        click.secho(f"[i] Using online wallpaper provider: {online_provider.lower()}", fg="cyan")

    output_mode = "log"

    desktop_environment = desktop_override
    if desktop_environment is None and "desktop" in settings_dict:
        configured_desktop = str(settings_dict["desktop"]).strip().lower()
        if configured_desktop and configured_desktop != "auto":
            desktop_environment = configured_desktop

    if desktop_environment is None:
        desktop_environment = detect_desktop_environment()

    if desktop_environment is None:
        if sys.stdin.isatty():
            desktop_environment = click.prompt(
                f"{GREEN}[+] Could not auto-detect desktop. Please specify your desktop environment{RESET}",
                type=click.Choice(["kde", "gnome", "cinnamon", "xfce", "mate", "lxqt"], case_sensitive=False),
                default="kde",
            ).lower()
        else:
            click.secho(
                "Error: Could not auto-detect your desktop environment (GNOME, Cinnamon, KDE Plasma, XFCE, MATE, or LXQt).\n"
                "Please explicitly pass --gnome, --cinnamon, --kde, --xfce, --mate, or --lxqt when running --install-autostart.",
                fg="red",
                bold=True,
                err=True,
            )
            show_auto_start_failure_and_exit()

    verify_system_requirements(desktop_environment)

    python_binary = sys.executable
    script_path = str(Path(__file__).resolve())
    command_tokens = [
        python_binary,
        script_path,
        "-p",
        str(pause_seconds),
        "-o",
        output_mode,
    ]
    if desktop_override:
        command_tokens.append(f"--{desktop_override}")
    elif desktop_environment:
        command_tokens.append(f"--{desktop_environment}")
    if color_theme and desktop_environment == "gnome":
        command_tokens.extend(["-t", color_theme])
    if shuffle:
        command_tokens.append("-s")
    if recursive:
        command_tokens.append("-R")
    if multi_monitor:
        command_tokens.append("--multi-monitor")
    if online_provider:
        command_tokens.extend(["--online", online_provider.lower()])
        if keep_last is not None:
            command_tokens.extend(["--keep-last", str(keep_last)])
    elif chosen_directory is not None:
        command_tokens.append(str(chosen_directory.resolve()))

    full_exec_command = shlex.join(command_tokens)

    try:
        current_username = getpass.getuser()
    except Exception:
        current_username = os.environ.get("USER", "root")

    current_uid = os.getuid()
    current_display = os.environ.get("DISPLAY", ":0")
    script_dir = str(Path(__file__).resolve().parent)
    service_filename = "wallpaper-changer.service"
    destination_service_path = f"/etc/systemd/system/{service_filename}"

    extra_environment_lines = []
    if "WAYLAND_DISPLAY" in os.environ:
        extra_environment_lines.append(f"Environment=WAYLAND_DISPLAY={os.environ['WAYLAND_DISPLAY']}")
    if "XAUTHORITY" in os.environ:
        extra_environment_lines.append(f"Environment=XAUTHORITY={os.environ['XAUTHORITY']}")
    if "XDG_SESSION_TYPE" in os.environ:
        extra_environment_lines.append(f"Environment=XDG_SESSION_TYPE={os.environ['XDG_SESSION_TYPE']}")
    if "XDG_CURRENT_DESKTOP" in os.environ:
        extra_environment_lines.append(f"Environment=XDG_CURRENT_DESKTOP={os.environ['XDG_CURRENT_DESKTOP']}")
    if "DESKTOP_SESSION" in os.environ:
        extra_environment_lines.append(f"Environment=DESKTOP_SESSION={os.environ['DESKTOP_SESSION']}")
    if "PATH" in os.environ:
        extra_environment_lines.append(f"Environment=PATH={os.environ['PATH']}")
    extra_environment_block = ("\n" + "\n".join(extra_environment_lines)) if extra_environment_lines else ""

    service_definition = f"""[Unit]
Description=Anahita Wallpaper Changer Service
After=graphical.target

[Service]
Type=simple
User={current_username}
WorkingDirectory={script_dir}
Environment=XDG_RUNTIME_DIR=/run/user/{current_uid}
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{current_uid}/bus
Environment=DISPLAY={current_display}{extra_environment_block}
ExecStart={full_exec_command}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
"""

    click.secho(
        f"\n[i] Generated systemd service definition for user '{current_username}':\n"
        f"    Command: {full_exec_command}\n"
        f"    Logging: {output_mode} (info.log)\n",
        fg="cyan",
    )

    click.secho(
        f"[i] Requesting root permissions via sudo to install and enable '{service_filename}'...",
        fg="yellow",
        bold=True,
    )

    # Secure installation: pipe content directly to sudo tee, avoiding insecure /tmp files
    write_result = subprocess.run(
        ["sudo", "tee", destination_service_path],
        input=service_definition.encode("utf-8"),
        stdout=subprocess.DEVNULL,
        check=False,
    )
    if write_result.returncode != 0:
        click.secho(f"\n[!] Failed to write service file to {destination_service_path}", fg="red", err=True)
        show_auto_start_failure_and_exit()

    setup_commands = [
        ["sudo", "chmod", "644", destination_service_path],
        ["sudo", "systemctl", "daemon-reload"],
        ["sudo", "systemctl", "enable", "--now", service_filename],
    ]

    for setup_command in setup_commands:
        step_result = subprocess.run(setup_command, check=False)
        if step_result.returncode != 0:
            click.secho(f"\n[!] Command failed: {' '.join(setup_command)}", fg="red", err=True)
            show_auto_start_failure_and_exit()

    click.secho(
        f"\n[+] Successfully installed and activated '{service_filename}'!\n"
        f"[+] The service will now run automatically on login.\n"
        f"[+] View status: sudo systemctl status {service_filename}\n"
        f"[+] Stop service: sudo systemctl stop {service_filename}\n"
        f"[+] Disable:     sudo systemctl disable {service_filename}\n",
        fg="green",
        bold=True,
    )
    sys.exit(0)


setup_auto_start_service = setup_install_autostart_service
setup_auto_start = setup_install_autostart_service
setup_install_autostart = setup_install_autostart_service


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--pause",
    "-p",
    type=DURATION_TYPE,
    default=None,
    help="Duration between changing wallpapers (e.g. 30s, 10m, 1h, or 60).",
)
@click.option(
    "--repetition/--no-repetition",
    "-r/-nr",
    default=True,
    show_default=True,
    help="By setting --no-repetition, the program will exit after setting all wallpapers once.",
)
@click.option(
    "--theme",
    "-t",
    type=click.Choice(["dark", "light", "both"], case_sensitive=False),
    default=None,
    help=(
        "By default, the script updates both dark and light themes. "
        "Specify 'dark' or 'light' to apply changes only to that theme (GNOME only)."
    ),
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["console", "log"], case_sensitive=False),
    default="console",
    show_default=True,
    help="Choose program output mode: display in console or save to a log file.",
)
@click.option(
    "--gnome",
    "desktop_override",
    flag_value="gnome",
    default=None,
    help="Manually override desktop environment to GNOME.",
)
@click.option(
    "--cinnamon",
    "--cinamon",
    "desktop_override",
    flag_value="cinnamon",
    help="Manually override desktop environment to Cinnamon.",
)
@click.option(
    "--kde",
    "--plasma",
    "desktop_override",
    flag_value="kde",
    help="Manually override desktop environment to KDE Plasma.",
)
@click.option(
    "--xfce",
    "--xfce4",
    "desktop_override",
    flag_value="xfce",
    help="Manually override desktop environment to XFCE.",
)
@click.option(
    "--mate",
    "desktop_override",
    flag_value="mate",
    help="Manually override desktop environment to MATE.",
)
@click.option(
    "--lxqt",
    "desktop_override",
    flag_value="lxqt",
    help="Manually override desktop environment to LXQt.",
)
@click.option(
    "--online",
    type=click.Choice(ONLINE_PROVIDER_CHOICES, case_sensitive=False),
    default=None,
    help="Fetch wallpapers online from a provider (wallhaven, bing, picsum, loremflickr).",
)
@click.option(
    "--source",
    type=click.Choice(["folder", "local", *ONLINE_PROVIDER_CHOICES], case_sensitive=False),
    default=None,
    help="Wallpaper source: local 'folder' or online provider ('wallhaven', 'bing', 'picsum', 'loremflickr').",
)
@click.option(
    "--shuffle/--no-shuffle",
    "-s",
    default=False,
    help="Shuffle wallpapers randomly instead of cycling in folder order.",
)
@click.option(
    "--recursive/--no-recursive",
    "-R",
    default=False,
    help="Search for images recursively in subfolders.",
)
@click.option(
    "--multi-monitor/--single-monitor",
    "-m",
    "multi_monitor",
    default=False,
    help="Set different wallpapers on each connected monitor/screen.",
)
@click.option(
    "--run-background",
    "-b",
    is_flag=True,
    default=False,
    help="Run the wallpaper changer in the background detached from the terminal.",
)
@click.option(
    "--install-autostart",
    "--auto-start",
    "install_autostart",
    is_flag=True,
    default=False,
    help="Interactively configure and install a startup service so the changer runs every time the user signs in.",
)
@click.option(
    "--keep-last",
    type=click.IntRange(min=1),
    default=None,
    help=f"Maximum number of downloaded online wallpapers to retain in cache before cleanup (default: {DEFAULT_KEEP_LAST}).",
)
@click.option(
    "--config",
    "-c",
    "config_file",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="Path to a custom TOML configuration file.",
)
@click.option(
    "--no-config",
    is_flag=True,
    default=False,
    help="Disable loading settings from config.toml.",
)
@click.argument(
    "photo_path",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True, path_type=Path),
    required=False,
    default=None,
)
@click.pass_context
def cli(
    click_context: click.Context,
    pause: int | None,
    repetition: bool,
    theme: str | None,
    output: str,
    desktop_override: str | None,
    online: str | None,
    source: str | None,
    shuffle: bool,
    recursive: bool,
    run_background: bool,
    install_autostart: bool,
    keep_last: int | None,
    config_file: Path | None,
    no_config: bool,
    photo_path: Path | None,
    multi_monitor: bool = False,
) -> None:
    """Anahita Wallpaper Changer (wchanger).

    Automatically cycle desktop wallpapers on GNOME, Cinnamon, KDE Plasma, XFCE, MATE, and LXQt.
    Desktop environment is auto-detected by default. Use --gnome, --cinnamon, --kde, --xfce, --mate, or --lxqt
    to manually override detection.
    """
    config_settings: dict[str, object] = {}
    if not no_config:
        config_settings = load_config_file(config_file)

    if desktop_override is None and "desktop" in config_settings:
        config_desktop = str(config_settings["desktop"]).strip().lower()
        if config_desktop and config_desktop != "auto":
            desktop_override = config_desktop

    pause_from_cli = click_context.get_parameter_source("pause") == click.core.ParameterSource.COMMANDLINE
    if not pause_from_cli and "pause" in config_settings and config_settings["pause"] is not None:
        try:
            pause = parse_duration_to_seconds(config_settings["pause"])
        except ValueError as error:
            click.secho(
                f"[!] Warning: Invalid 'pause' in config: {error}. Using default {DEFAULT_PAUSE_SECONDS}s.",
                fg="yellow",
                err=True,
            )
            pause = DEFAULT_PAUSE_SECONDS

    repetition_from_cli = click_context.get_parameter_source("repetition") == click.core.ParameterSource.COMMANDLINE
    if not repetition_from_cli and "repetition" in config_settings:
        repetition = bool(config_settings["repetition"])

    background_from_cli = click_context.get_parameter_source("run_background") == click.core.ParameterSource.COMMANDLINE
    if not background_from_cli and "run_background" in config_settings:
        run_background = bool(config_settings["run_background"])

    theme_from_cli = click_context.get_parameter_source("theme") == click.core.ParameterSource.COMMANDLINE
    if not theme_from_cli and "theme" in config_settings:
        config_theme = str(config_settings["theme"]).strip().lower()
        if config_theme in ("dark", "light"):
            theme = config_theme
        elif config_theme in ("both", "all"):
            theme = None

    output_from_cli = click_context.get_parameter_source("output") == click.core.ParameterSource.COMMANDLINE
    if not output_from_cli and "output" in config_settings:
        config_output = str(config_settings["output"]).strip().lower()
        if config_output in ("console", "log"):
            output = config_output

    shuffle_from_cli = click_context.get_parameter_source("shuffle") == click.core.ParameterSource.COMMANDLINE
    if not shuffle_from_cli and "shuffle" in config_settings:
        shuffle = bool(config_settings["shuffle"])

    recursive_from_cli = click_context.get_parameter_source("recursive") == click.core.ParameterSource.COMMANDLINE
    if not recursive_from_cli and "recursive" in config_settings:
        recursive = bool(config_settings["recursive"])

    multi_monitor_from_cli = click_context.get_parameter_source("multi_monitor") == click.core.ParameterSource.COMMANDLINE
    if not multi_monitor_from_cli and "multi_monitor" in config_settings:
        multi_monitor = bool(config_settings["multi_monitor"])

    keep_last_from_cli = click_context.get_parameter_source("keep_last") == click.core.ParameterSource.COMMANDLINE
    if not keep_last_from_cli and "keep_last" in config_settings:
        try:
            keep_last = int(config_settings["keep_last"])
        except (ValueError, TypeError):
            keep_last = DEFAULT_KEEP_LAST
    if keep_last is None:
        keep_last = DEFAULT_KEEP_LAST

    custom_cache_dir: Path | None = None
    if "cache_dir" in config_settings:
        custom_cache_dir = Path(os.path.expanduser(str(config_settings["cache_dir"])))

    photo_path_from_cli = click_context.get_parameter_source("photo_path") == click.core.ParameterSource.COMMANDLINE
    online_from_cli = click_context.get_parameter_source("online") == click.core.ParameterSource.COMMANDLINE
    source_from_cli = click_context.get_parameter_source("source") == click.core.ParameterSource.COMMANDLINE

    effective_online_provider: str | None = None
    if photo_path_from_cli:
        effective_online_provider = None
    elif online_from_cli and online:
        effective_online_provider = online.lower()
    elif source_from_cli and source:
        source_normalized = source.lower()
        if source_normalized in ("folder", "local"):
            effective_online_provider = None
        else:
            effective_online_provider = source_normalized
    elif "source" in config_settings:
        config_source = str(config_settings["source"]).strip().lower()
        if config_source in ONLINE_PROVIDER_CHOICES:
            effective_online_provider = config_source
        elif config_source in ("folder", "local"):
            effective_online_provider = None

    if install_autostart:
        setup_install_autostart_service(
            desktop_override=desktop_override,
            color_theme=theme,
            initial_photo_path=photo_path,
            online_provider=effective_online_provider,
            shuffle=shuffle,
            recursive=recursive,
            keep_last=keep_last,
            config_settings=config_settings,
            multi_monitor=multi_monitor,
        )
        return

    desktop_environment = desktop_override
    if desktop_environment is None:
        desktop_environment = detect_desktop_environment()

    if desktop_environment is None:
        click.secho(
            "Error: Could not auto-detect your desktop environment (GNOME, Cinnamon, KDE Plasma, XFCE, MATE, or LXQt).\n"
            "Please explicitly pass --gnome, --cinnamon, --kde, --xfce, --mate, or --lxqt.",
            fg="red",
            bold=True,
            err=True,
        )
        sys.exit(1)

    verify_system_requirements(desktop_environment)

    if pause is None:
        if not repetition or run_background or not sys.stdin.isatty():
            pause = DEFAULT_PAUSE_SECONDS
        else:
            pause = click.prompt(
                f"{GREEN}[+] - Please set pause duration between changing wallpapers (e.g. 60, 10m, 1h){RESET}",
                type=DURATION_TYPE,
                default=DEFAULT_PAUSE_SECONDS,
                show_default=True,
            )

    desktop_display_name = DESKTOP_DISPLAY_NAMES.get(desktop_environment, desktop_environment.capitalize())

    if desktop_environment != "gnome" and theme is not None and not run_background:
        click.secho(
            f"[!] Notice: The --theme option applies only to GNOME and will be ignored on {desktop_display_name}.",
            fg="yellow",
            err=True,
        )

    if effective_online_provider is not None:
        online_provider = effective_online_provider
        if run_background:
            try:
                child_pid = os.fork()
            except OSError as fork_error:
                click.secho(f"Error: Could not fork background process: {fork_error}", fg="red", err=True)
                sys.exit(1)

            if child_pid > 0:
                click.secho(
                    f"[+] Anahita Wallpaper Changer started in background (PID: {child_pid}).\n"
                    f"[+] Mode: {desktop_display_name} | Pause: {pause}s | Source: online ({online_provider})\n"
                    f"[+] To stop it later, run: kill {child_pid} (or: pkill -f wchanger.py)",
                    fg="green",
                    bold=True,
                )
                sys.exit(0)

            os.setsid()

            sys.stdout.flush()
            sys.stderr.flush()

            devnull_input = os.open(os.devnull, os.O_RDONLY)
            devnull_output = os.open(os.devnull, os.O_WRONLY)

            try:
                standard_in_fileno = sys.stdin.fileno()
            except (io.UnsupportedOperation, AttributeError):
                standard_in_fileno = 0

            try:
                standard_out_fileno = sys.stdout.fileno()
            except (io.UnsupportedOperation, AttributeError):
                standard_out_fileno = 1

            try:
                standard_error_fileno = sys.stderr.fileno()
            except (io.UnsupportedOperation, AttributeError):
                standard_error_fileno = 2

            os.dup2(devnull_input, standard_in_fileno)
            os.dup2(devnull_output, standard_out_fileno)
            os.dup2(devnull_output, standard_error_fileno)

            os.close(devnull_input)
            os.close(devnull_output)

            configure_logging(output)
            run_online_wallpaper_cycle(
                desktop_environment=desktop_environment,
                provider=online_provider,
                pause_seconds=pause,
                repetition=repetition,
                output_mode=output,
                color_theme=theme,
                cache_dir=custom_cache_dir,
                keep_last=keep_last,
                multi_monitor=multi_monitor,
            )
            sys.exit(0)

        print(BANNER)
        configure_logging(output)
        print(
            f"{CYAN}[i] Desktop environment: {desktop_display_name}"
            + (" (forced via flag)" if desktop_override else " (auto-detected)")
            + f"{RESET}"
        )
        print(f"{CYAN}[i] Wallpaper source: online provider '{online_provider}'{RESET}")
        if multi_monitor:
            effective_monitors = get_effective_monitor_count(desktop_environment, multi_monitor=True)
            print(f"{CYAN}[i] Multi-monitor: enabled ({effective_monitors} displays){RESET}")

        run_online_wallpaper_cycle(
            desktop_environment=desktop_environment,
            provider=online_provider,
            pause_seconds=pause,
            repetition=repetition,
            output_mode=output,
            color_theme=theme,
            cache_dir=custom_cache_dir,
            keep_last=keep_last,
            multi_monitor=multi_monitor,
        )
        return

    selected_folder: Path
    from_config = False

    if photo_path is not None:
        selected_folder = photo_path
    elif "folder" in config_settings and config_settings["folder"]:
        configured_path = Path(os.path.expanduser(str(config_settings["folder"])))
        selected_folder = configured_path
        from_config = True
    else:
        selected_folder = DEFAULT_WALLPAPERS_DIR

    if not selected_folder.exists() or not selected_folder.is_dir():
        if from_config and DEFAULT_WALLPAPERS_DIR.exists():
            click.secho(
                f"[!] Warning: Configured wallpaper folder '{selected_folder}' does not exist. "
                f"Falling back to default '{DEFAULT_WALLPAPERS_DIR}'.",
                fg="yellow",
                err=True,
            )
            selected_folder = DEFAULT_WALLPAPERS_DIR
        else:
            click.secho(
                f"Error: Wallpaper directory '{selected_folder}' does not exist or is not a folder.",
                fg="red",
                bold=True,
                err=True,
            )
            sys.exit(1)

    discovered_wallpapers = file_validator(selected_folder, recursive=recursive)
    if not discovered_wallpapers:
        click.secho(
            f"Error: No valid image files found in '{selected_folder}'.",
            fg="red",
            bold=True,
            err=True,
        )
        sys.exit(1)

    if run_background:
        try:
            child_pid = os.fork()
        except OSError as fork_error:
            click.secho(f"Error: Could not fork background process: {fork_error}", fg="red", err=True)
            sys.exit(1)

        if child_pid > 0:
            active_feature_flags = []
            if shuffle:
                active_feature_flags.append("shuffle")
            if recursive:
                active_feature_flags.append("recursive")
            if multi_monitor:
                active_feature_flags.append("multi-monitor")
            flags_summary_text = (
                f" | Flags: {', '.join(active_feature_flags)}" if active_feature_flags else ""
            )
            click.secho(
                f"[+] Anahita Wallpaper Changer started in background (PID: {child_pid}).\n"
                f"[+] Mode: {desktop_display_name} | Pause: {pause}s | Directory: {selected_folder}{flags_summary_text}\n"
                f"[+] To stop it later, run: kill {child_pid} (or: pkill -f wchanger.py)",
                fg="green",
                bold=True,
            )
            sys.exit(0)

        os.setsid()

        sys.stdout.flush()
        sys.stderr.flush()

        devnull_input = os.open(os.devnull, os.O_RDONLY)
        devnull_output = os.open(os.devnull, os.O_WRONLY)

        try:
            standard_in_fileno = sys.stdin.fileno()
        except (io.UnsupportedOperation, AttributeError):
            standard_in_fileno = 0

        try:
            standard_out_fileno = sys.stdout.fileno()
        except (io.UnsupportedOperation, AttributeError):
            standard_out_fileno = 1

        try:
            standard_error_fileno = sys.stderr.fileno()
        except (io.UnsupportedOperation, AttributeError):
            standard_error_fileno = 2

        os.dup2(devnull_input, standard_in_fileno)
        os.dup2(devnull_output, standard_out_fileno)
        os.dup2(devnull_output, standard_error_fileno)

        os.close(devnull_input)
        os.close(devnull_output)

        configure_logging(output)
        run_wallpaper_cycle(
            desktop_environment=desktop_environment,
            wallpapers=discovered_wallpapers,
            pause_seconds=pause,
            repetition=repetition,
            output_mode=output,
            color_theme=theme,
            shuffle=shuffle,
            multi_monitor=multi_monitor,
        )
        sys.exit(0)

    print(BANNER)
    configure_logging(output)
    print(
        f"{CYAN}[i] Desktop environment: {desktop_display_name}"
        + (" (forced via flag)" if desktop_override else " (auto-detected)")
        + f"{RESET}"
    )
    if shuffle:
        print(f"{CYAN}[i] Shuffle: enabled{RESET}")
    if recursive:
        print(f"{CYAN}[i] Recursive scan: enabled{RESET}")
    if multi_monitor:
        effective_monitors = get_effective_monitor_count(desktop_environment, multi_monitor=True)
        print(f"{CYAN}[i] Multi-monitor: enabled ({effective_monitors} displays){RESET}")

    run_wallpaper_cycle(
        desktop_environment=desktop_environment,
        wallpapers=discovered_wallpapers,
        pause_seconds=pause,
        repetition=repetition,
        output_mode=output,
        color_theme=theme,
        shuffle=shuffle,
        multi_monitor=multi_monitor,
    )


main = cli


if __name__ == "__main__":
    main()

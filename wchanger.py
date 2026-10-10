"""Awesome Wallpaper Changer (wchanger).

A lightweight Linux CLI script that cycles through desktop wallpapers on
GNOME, Cinnamon, KDE Plasma, XFCE, MATE, and LXQt desktop environments.
"""

from __future__ import annotations

import getpass
import io
import logging
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import time
from typing import Sequence
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

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
    from PIL import Image

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


VERSION = "2.4.0"
DEFAULT_PAUSE_SECONDS = 60

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
            "Error: Awesome Wallpaper Changer only runs on Linux.",
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


def file_validator(directory_path: str | Path) -> list[str]:
    """Return sorted string paths of all readable images inside a directory."""
    folder = Path(directory_path)
    if not folder.exists() or not folder.is_dir():
        return []

    try:
        folder_entries = sorted(folder.iterdir())
    except (PermissionError, OSError):
        return []

    valid_paths: list[str] = [
        str(entry.resolve())
        for entry in folder_entries
        if is_valid_image_file(entry)
    ]
    return valid_paths


def set_gnome_background(file_uri: str, theme: str | None = None) -> bool:
    """Apply wallpaper URI to GNOME background schema."""
    if not file_uri.startswith("file://"):
        file_uri = Path(file_uri).resolve().as_uri()

    gsettings_commands: list[list[str]] = []

    if theme == "dark":
        gsettings_commands.append(["gsettings", "set", GNOME_SCHEMA, GNOME_KEY_DARK, file_uri])
    elif theme == "light":
        gsettings_commands.append(["gsettings", "set", GNOME_SCHEMA, GNOME_KEY_LIGHT, file_uri])
    else:
        gsettings_commands.append(["gsettings", "set", GNOME_SCHEMA, GNOME_KEY_LIGHT, file_uri])
        gsettings_commands.append(["gsettings", "set", GNOME_SCHEMA, GNOME_KEY_DARK, file_uri])

    all_commands_succeeded = True
    for command in gsettings_commands:
        execution_result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if execution_result.returncode != 0:
            all_commands_succeeded = False

    return all_commands_succeeded


def set_cinnamon_background(file_uri: str) -> bool:
    """Apply wallpaper URI to Cinnamon background schema."""
    if not file_uri.startswith("file://"):
        file_uri = Path(file_uri).resolve().as_uri()

    command = ["gsettings", "set", CINNAMON_SCHEMA, CINNAMON_KEY, file_uri]
    execution_result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return execution_result.returncode == 0


def set_kde_background(file_uri: str, qdbus_executable: str | None = None) -> bool:
    """Apply wallpaper URI to KDE Plasma desktop via qdbus evaluateScript."""
    selected_executable = qdbus_executable or find_kde_qdbus_executable()
    if not selected_executable:
        return False

    if file_uri.startswith("/") and not file_uri.startswith("file://"):
        file_uri = Path(file_uri).resolve().as_uri()

    safe_uri = (
        file_uri.replace("\\", "\\\\")
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


def set_xfce_background(file_path: str) -> bool:
    """Apply wallpaper path to XFCE desktop via xfconf-query."""
    resolved_path = _resolve_to_file_path(file_path)

    list_process = subprocess.run(
        ["xfconf-query", "-c", XFCE_CHANNEL, "-l"],
        capture_output=True,
        text=True,
        check=False,
    )

    discovered_properties: list[str] = []
    if list_process.returncode == 0:
        seen_properties = set()
        for line in list_process.stdout.splitlines():
            property_candidate = line.strip()
            if "last-image" in property_candidate and property_candidate not in seen_properties:
                seen_properties.add(property_candidate)
                discovered_properties.append(property_candidate)

    if not discovered_properties:
        for fallback_property in XFCE_FALLBACK_PROPERTIES:
            fallback_result = subprocess.run(
                ["xfconf-query", "-c", XFCE_CHANNEL, "-p", fallback_property, "-s", resolved_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if fallback_result.returncode == 0:
                return True
        return False

    all_properties_succeeded = True
    for target_property in discovered_properties:
        set_result = subprocess.run(
            ["xfconf-query", "-c", XFCE_CHANNEL, "-p", target_property, "-s", resolved_path],
            capture_output=True,
            text=True,
            check=False,
        )
        if set_result.returncode != 0:
            all_properties_succeeded = False

    return all_properties_succeeded


def set_mate_background(file_path: str) -> bool:
    """Apply wallpaper path to MATE background schema."""
    resolved_path = _resolve_to_file_path(file_path)
    command = ["gsettings", "set", MATE_SCHEMA, MATE_KEY, resolved_path]
    execution_result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return execution_result.returncode == 0


def set_lxqt_background(file_path: str) -> bool:
    """Apply wallpaper path to LXQt desktop via pcmanfm-qt."""
    resolved_path = _resolve_to_file_path(file_path)
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


def run_wallpaper_cycle(
    desktop_environment: str,
    wallpapers: Sequence[str],
    pause_seconds: int,
    repetition: bool,
    output_mode: str,
    color_theme: str | None = None,
) -> None:
    """Cycle wallpapers in a clean loop with graceful interruption handling."""
    try:
        while True:
            for wallpaper in wallpapers:
                wallpaper_file = Path(wallpaper)
                if not wallpaper_file.exists():
                    skip_message = f"Skipping missing wallpaper: {wallpaper}"
                    if output_mode == "log":
                        logging.warning(skip_message)
                    else:
                        print(f"{YELLOW}{skip_message}{RESET}")
                    continue

                file_uri = wallpaper_file.resolve().as_uri()
                operation_success = False

                if desktop_environment == "gnome":
                    operation_success = set_gnome_background(file_uri, color_theme)
                    if color_theme is not None:
                        status_message = f"Wallpaper changed on GNOME to {wallpaper} in {color_theme} theme."
                    else:
                        status_message = f"Wallpaper changed on GNOME to {wallpaper} in both dark and light themes."
                elif desktop_environment == "cinnamon":
                    operation_success = set_cinnamon_background(file_uri)
                    status_message = f"Wallpaper changed on Cinnamon to {wallpaper}."
                elif desktop_environment == "kde":
                    operation_success = set_kde_background(file_uri)
                    status_message = f"Wallpaper changed on KDE Plasma to {wallpaper}."
                elif desktop_environment == "xfce":
                    operation_success = set_xfce_background(wallpaper)
                    status_message = f"Wallpaper changed on XFCE to {wallpaper}."
                elif desktop_environment == "mate":
                    operation_success = set_mate_background(wallpaper)
                    status_message = f"Wallpaper changed on MATE to {wallpaper}."
                elif desktop_environment == "lxqt":
                    operation_success = set_lxqt_background(wallpaper)
                    status_message = f"Wallpaper changed on LXQt to {wallpaper}."

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

            if not repetition:
                completion_message = "Program exited after setting all wallpapers."
                if output_mode == "log":
                    logging.info(completion_message)
                else:
                    print(f"{MAGENTA}{completion_message}{RESET}")
                sys.exit(0)

    except KeyboardInterrupt:
        shutdown_message = "Program stopped by user. Exiting..."
        if output_mode == "log":
            logging.info("Wallpaper changer stopped by user.")
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


def setup_auto_start_service(
    desktop_override: str | None = None,
    color_theme: str | None = None,
    initial_photo_path: Path | None = None,
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

    pause_seconds = click.prompt(
        f"{GREEN}[+] Enter pause duration between changing wallpapers (seconds){RESET}",
        type=click.IntRange(min=1),
        default=DEFAULT_PAUSE_SECONDS,
        show_default=True,
    )

    default_directory = (
        initial_photo_path if initial_photo_path is not None else DEFAULT_WALLPAPERS_DIR
    )

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

        discovered_wallpapers = file_validator(chosen_directory)
        if not discovered_wallpapers:
            click.secho(f"[!] No valid image files found in '{chosen_directory}'. Please try another path.", fg="red", err=True)
            continue
        break

    output_mode = "log"

    desktop_environment = desktop_override
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
                "Please explicitly pass --gnome, --cinnamon, --kde, --xfce, --mate, or --lxqt when running --auto-start.",
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

    extra_env_lines = []
    if "WAYLAND_DISPLAY" in os.environ:
        extra_env_lines.append(f"Environment=WAYLAND_DISPLAY={os.environ['WAYLAND_DISPLAY']}")
    if "XAUTHORITY" in os.environ:
        extra_env_lines.append(f"Environment=XAUTHORITY={os.environ['XAUTHORITY']}")
    extra_env_block = ("\n" + "\n".join(extra_env_lines)) if extra_env_lines else ""

    service_definition = f"""[Unit]
Description=Awesome Wallpaper Changer Service
After=graphical.target

[Service]
Type=simple
User={current_username}
WorkingDirectory={script_dir}
Environment=XDG_RUNTIME_DIR=/run/user/{current_uid}
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{current_uid}/bus
Environment=DISPLAY={current_display}{extra_env_block}
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


setup_auto_start = setup_auto_start_service


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--pause",
    "-p",
    type=click.IntRange(min=1),
    default=None,
    help="Duration in seconds between changing wallpapers.",
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
    type=click.Choice(["dark", "light"], case_sensitive=False),
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
    "--run-background",
    "-b",
    is_flag=True,
    default=False,
    help="Run the wallpaper changer in the background detached from the terminal.",
)
@click.option(
    "--auto-start",
    is_flag=True,
    default=False,
    help="Interactively configure and install a systemd startup service with root privileges.",
)
@click.argument(
    "photo_path",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True, path_type=Path),
    required=False,
    default=None,
)
def cli(
    pause: int | None,
    repetition: bool,
    theme: str | None,
    output: str,
    desktop_override: str | None,
    run_background: bool,
    auto_start: bool,
    photo_path: Path | None,
) -> None:
    """Awesome Wallpaper Changer (wchanger).

    Automatically cycle desktop wallpapers on GNOME, Cinnamon, KDE Plasma, XFCE, MATE, and LXQt.
    Desktop environment is auto-detected by default. Use --gnome, --cinnamon, --kde, --xfce, --mate, or --lxqt
    to manually override detection.
    """
    if auto_start:
        setup_auto_start_service(
            desktop_override=desktop_override,
            color_theme=theme,
            initial_photo_path=photo_path,
        )

    selected_folder = photo_path if photo_path is not None else DEFAULT_WALLPAPERS_DIR

    if not selected_folder.exists() or not selected_folder.is_dir():
        click.secho(
            f"Error: Wallpaper directory '{selected_folder}' does not exist or is not a folder.",
            fg="red",
            bold=True,
            err=True,
        )
        sys.exit(1)

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

    discovered_wallpapers = file_validator(selected_folder)
    if not discovered_wallpapers:
        click.secho(
            f"Error: No valid image files found in '{selected_folder}'.",
            fg="red",
            bold=True,
            err=True,
        )
        sys.exit(1)

    if pause is None:
        if run_background or not sys.stdin.isatty():
            pause = DEFAULT_PAUSE_SECONDS
        else:
            pause = click.prompt(
                f"{GREEN}[+] - Please set pause duration between changing wallpapers (seconds){RESET}",
                type=click.IntRange(min=1),
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

    if run_background:
        try:
            child_pid = os.fork()
        except OSError as fork_error:
            click.secho(f"Error: Could not fork background process: {fork_error}", fg="red", err=True)
            sys.exit(1)

        if child_pid > 0:
            click.secho(
                f"[+] Awesome Wallpaper Changer started in background (PID: {child_pid}).\n"
                f"[+] Mode: {desktop_display_name} | Pause: {pause}s | Directory: {selected_folder}\n"
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
            stdin_fd = sys.stdin.fileno()
        except (io.UnsupportedOperation, AttributeError):
            stdin_fd = 0

        try:
            stdout_fd = sys.stdout.fileno()
        except (io.UnsupportedOperation, AttributeError):
            stdout_fd = 1

        try:
            stderr_fd = sys.stderr.fileno()
        except (io.UnsupportedOperation, AttributeError):
            stderr_fd = 2

        os.dup2(devnull_input, stdin_fd)
        os.dup2(devnull_output, stdout_fd)
        os.dup2(devnull_output, stderr_fd)

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
        )
        sys.exit(0)

    print(BANNER)
    configure_logging(output)
    print(
        f"{CYAN}[i] Desktop environment: {desktop_display_name}"
        + (" (forced via flag)" if desktop_override else " (auto-detected)")
        + f"{RESET}"
    )

    run_wallpaper_cycle(
        desktop_environment=desktop_environment,
        wallpapers=discovered_wallpapers,
        pause_seconds=pause,
        repetition=repetition,
        output_mode=output,
        color_theme=theme,
    )


def main() -> None:
    """Run CLI."""
    cli()


if __name__ == "__main__":
    main()

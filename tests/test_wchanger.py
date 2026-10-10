"""Tests for wchanger.py."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError
from urllib.request import Request

from click.testing import CliRunner
from PIL import Image

import wchanger


class TestWallpaperChanger(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_file_validator_empty_dir(self) -> None:
        """file_validator should return an empty list for an empty directory."""
        result = wchanger.file_validator(self.test_dir)
        self.assertEqual(result, [])

    def test_file_validator_nonexistent_dir(self) -> None:
        """file_validator should handle non-existent directories gracefully."""
        bad_path = self.test_dir / "nonexistent"
        result = wchanger.file_validator(bad_path)
        self.assertEqual(result, [])

    def test_file_validator_ignores_non_images(self) -> None:
        """file_validator should ignore non-image files like text and scripts."""
        text_file = self.test_dir / "notes.txt"
        text_file.write_text("Hello world")

        script_file = self.test_dir / "run.sh"
        script_file.write_text("#!/bin/bash\necho hi")

        subdirectory = self.test_dir / "subfolder"
        subdirectory.mkdir()

        result = wchanger.file_validator(self.test_dir)
        self.assertEqual(result, [])

    def test_file_validator_valid_images(self) -> None:
        """file_validator should detect valid image files."""
        img1 = self.test_dir / "pic1.png"
        img2 = self.test_dir / "pic2.jpg"

        # Create valid dummy images
        image_obj = Image.new("RGB", (10, 10), color="blue")
        image_obj.save(img1, format="PNG")
        image_obj.save(img2, format="JPEG")

        result = wchanger.file_validator(self.test_dir)
        self.assertEqual(len(result), 2)
        self.assertIn(str(img1.resolve()), result)
        self.assertIn(str(img2.resolve()), result)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME", "DESKTOP_SESSION": "gnome"})
    def test_detect_desktop_gnome(self) -> None:
        """detect_desktop_environment should detect GNOME."""
        self.assertEqual(wchanger.detect_desktop_environment(), "gnome")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "X-Cinnamon", "DESKTOP_SESSION": "cinnamon"})
    def test_detect_desktop_cinnamon(self) -> None:
        """detect_desktop_environment should detect Cinnamon."""
        self.assertEqual(wchanger.detect_desktop_environment(), "cinnamon")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE", "DESKTOP_SESSION": ""})
    def test_detect_desktop_kde_from_xdg(self) -> None:
        """detect_desktop_environment should detect KDE when XDG_CURRENT_DESKTOP contains 'kde'."""
        self.assertEqual(wchanger.detect_desktop_environment(), "kde")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "", "DESKTOP_SESSION": "plasma"})
    def test_detect_desktop_kde_from_session(self) -> None:
        """detect_desktop_environment should detect KDE when DESKTOP_SESSION contains 'plasma'."""
        self.assertEqual(wchanger.detect_desktop_environment(), "kde")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE:Plasma", "DESKTOP_SESSION": "plasmawayland"})
    def test_detect_desktop_kde_combined(self) -> None:
        """detect_desktop_environment should detect KDE with combined session variables."""
        self.assertEqual(wchanger.detect_desktop_environment(), "kde")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "XFCE", "DESKTOP_SESSION": "xfce"})
    def test_detect_desktop_xfce(self) -> None:
        """detect_desktop_environment should detect XFCE."""
        self.assertEqual(wchanger.detect_desktop_environment(), "xfce")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "MATE", "DESKTOP_SESSION": "mate"})
    def test_detect_desktop_mate(self) -> None:
        """detect_desktop_environment should detect MATE."""
        self.assertEqual(wchanger.detect_desktop_environment(), "mate")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "LXQt", "DESKTOP_SESSION": "lxqt"})
    def test_detect_desktop_lxqt(self) -> None:
        """detect_desktop_environment should detect LXQt."""
        self.assertEqual(wchanger.detect_desktop_environment(), "lxqt")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "i3", "DESKTOP_SESSION": "i3"})
    def test_detect_desktop_unknown(self) -> None:
        """detect_desktop_environment should return None on unsupported desktop."""
        self.assertIsNone(wchanger.detect_desktop_environment())

    def test_find_kde_qdbus_executable_prefers_qdbus(self) -> None:
        """find_kde_qdbus_executable should return 'qdbus' if available."""
        with patch("shutil.which", side_effect=lambda name: f"/usr/bin/{name}" if name == "qdbus" else None):
            self.assertEqual(wchanger.find_kde_qdbus_executable(), "qdbus")

    def test_find_kde_qdbus_executable_falls_back_to_qdbus6(self) -> None:
        """find_kde_qdbus_executable should fall back to 'qdbus6' when 'qdbus' is absent."""
        with patch("shutil.which", side_effect=lambda name: f"/usr/bin/{name}" if name == "qdbus6" else None):
            self.assertEqual(wchanger.find_kde_qdbus_executable(), "qdbus6")

    def test_find_kde_qdbus_executable_falls_back_to_qdbus_qt6(self) -> None:
        """find_kde_qdbus_executable should fall back to 'qdbus-qt6' when predecessors are absent."""
        with patch("shutil.which", side_effect=lambda name: f"/usr/bin/{name}" if name == "qdbus-qt6" else None):
            self.assertEqual(wchanger.find_kde_qdbus_executable(), "qdbus-qt6")

    def test_find_kde_qdbus_executable_falls_back_to_qdbus_qt5(self) -> None:
        """find_kde_qdbus_executable should fall back to 'qdbus-qt5' when others are absent."""
        with patch("shutil.which", side_effect=lambda name: f"/usr/bin/{name}" if name == "qdbus-qt5" else None):
            self.assertEqual(wchanger.find_kde_qdbus_executable(), "qdbus-qt5")

    def test_find_kde_qdbus_executable_none_found(self) -> None:
        """find_kde_qdbus_executable should return None when no qdbus tool is available."""
        with patch("shutil.which", return_value=None):
            self.assertIsNone(wchanger.find_kde_qdbus_executable())

    @patch("subprocess.run")
    def test_set_gnome_wallpaper_theme_dark(self, mock_run: MagicMock) -> None:
        """Dark theme should only invoke picture-uri-dark."""
        mock_run.return_value = MagicMock(returncode=0)
        wallpaper_uri = "file:///home/user/pic.jpg"

        success = wchanger.set_gnome_wallpaper(wallpaper_uri, theme="dark")
        self.assertTrue(success)
        mock_run.assert_called_once_with(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri-dark",
                wallpaper_uri,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_set_gnome_wallpaper_theme_light(self, mock_run: MagicMock) -> None:
        """Light theme should only invoke picture-uri."""
        mock_run.return_value = MagicMock(returncode=0)
        wallpaper_uri = "file:///home/user/pic.jpg"

        success = wchanger.set_gnome_wallpaper(wallpaper_uri, theme="light")
        self.assertTrue(success)
        mock_run.assert_called_once_with(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri",
                wallpaper_uri,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_set_gnome_wallpaper_theme_both(self, mock_run: MagicMock) -> None:
        """None theme should set both picture-uri and picture-uri-dark."""
        mock_run.return_value = MagicMock(returncode=0)
        wallpaper_uri = "file:///home/user/pic.jpg"

        success = wchanger.set_gnome_wallpaper(wallpaper_uri, theme=None)
        self.assertTrue(success)
        self.assertEqual(mock_run.call_count, 2)

    @patch("subprocess.run")
    def test_set_cinnamon_wallpaper(self, mock_run: MagicMock) -> None:
        """Cinnamon should invoke org.cinnamon.desktop.background picture-uri."""
        mock_run.return_value = MagicMock(returncode=0)
        wallpaper_uri = "file:///home/user/pic.jpg"

        success = wchanger.set_cinnamon_wallpaper(wallpaper_uri)
        self.assertTrue(success)
        mock_run.assert_called_once_with(
            [
                "gsettings",
                "set",
                "org.cinnamon.desktop.background",
                "picture-uri",
                wallpaper_uri,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    @patch("subprocess.run")
    def test_set_kde_wallpaper_success(
        self, mock_run: MagicMock, mock_find_qdbus: MagicMock
    ) -> None:
        """KDE wallpaper setter should invoke evaluateScript on PlasmaShell via qdbus."""
        mock_run.return_value = MagicMock(returncode=0)
        wallpaper_uri = "file:///home/user/pic.jpg"

        success = wchanger.set_kde_wallpaper(wallpaper_uri)
        self.assertTrue(success)
        mock_run.assert_called_once()
        command_args = mock_run.call_args[0][0]
        self.assertEqual(command_args[0], "qdbus")
        self.assertEqual(command_args[1], "org.kde.plasmashell")
        self.assertEqual(command_args[2], "/PlasmaShell")
        self.assertEqual(command_args[3], "org.kde.PlasmaShell.evaluateScript")
        js_script = command_args[4]
        self.assertIn("desktops()", js_script)
        self.assertIn('desktop.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");', js_script)
        self.assertIn(f'desktop.writeConfig("Image", "{wallpaper_uri}");', js_script)

    @patch("subprocess.run")
    def test_set_kde_wallpaper_explicit_executable(self, mock_run: MagicMock) -> None:
        """KDE wallpaper setter should support passing explicit qdbus executable."""
        mock_run.return_value = MagicMock(returncode=0)
        wallpaper_uri = "file:///home/user/pic.jpg"

        success = wchanger.set_kde_background(wallpaper_uri, qdbus_executable="qdbus6")
        self.assertTrue(success)
        command_args = mock_run.call_args[0][0]
        self.assertEqual(command_args[0], "qdbus6")

    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    @patch("subprocess.run")
    def test_set_kde_wallpaper_subprocess_failure(
        self, mock_run: MagicMock, mock_find_qdbus: MagicMock
    ) -> None:
        """KDE wallpaper setter should return False if qdbus execution fails."""
        mock_run.return_value = MagicMock(returncode=1)
        wallpaper_uri = "file:///home/user/pic.jpg"

        success = wchanger.set_kde_wallpaper(wallpaper_uri)
        self.assertFalse(success)

    @patch("wchanger.find_kde_qdbus_executable", return_value=None)
    def test_set_kde_wallpaper_missing_executable(self, mock_find_qdbus: MagicMock) -> None:
        """KDE wallpaper setter should return False if no qdbus binary is available."""
        success = wchanger.set_kde_wallpaper("file:///home/user/pic.jpg")
        self.assertFalse(success)

    def test_set_kde_wallpaper_alias(self) -> None:
        """set_kde_wallpaper should be an alias of set_kde_background."""
        self.assertIs(wchanger.set_kde_wallpaper, wchanger.set_kde_background)

    @patch("platform.system", return_value="Linux")
    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    def test_verify_system_requirements_kde_success(
        self, mock_find_qdbus: MagicMock, mock_platform: MagicMock
    ) -> None:
        """verify_system_requirements for KDE should succeed when qdbus is installed."""
        wchanger.verify_system_requirements("kde")

    @patch("platform.system", return_value="Linux")
    @patch("wchanger.find_kde_qdbus_executable", return_value=None)
    def test_verify_system_requirements_kde_failure(
        self, mock_find_qdbus: MagicMock, mock_platform: MagicMock
    ) -> None:
        """verify_system_requirements for KDE should exit if qdbus is missing."""
        with self.assertRaises(SystemExit) as exception_context:
            wchanger.verify_system_requirements("kde")
        self.assertEqual(exception_context.exception.code, 1)

    @patch("platform.system", return_value="Linux")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_verify_system_requirements_gnome_success(
        self, mock_which: MagicMock, mock_platform: MagicMock
    ) -> None:
        """verify_system_requirements for GNOME should succeed when gsettings is installed."""
        wchanger.verify_system_requirements("gnome")

    @patch("platform.system", return_value="Linux")
    @patch("shutil.which", return_value=None)
    def test_verify_system_requirements_gnome_failure(
        self, mock_which: MagicMock, mock_platform: MagicMock
    ) -> None:
        """verify_system_requirements for GNOME should exit if gsettings is missing."""
        with self.assertRaises(SystemExit) as exception_context:
            wchanger.verify_system_requirements("gnome")
        self.assertEqual(exception_context.exception.code, 1)

    @patch("platform.system", return_value="Darwin")
    def test_verify_system_requirements_non_linux(self, mock_platform: MagicMock) -> None:
        """verify_system_requirements should exit on non-Linux platforms."""
        with self.assertRaises(SystemExit) as exception_context:
            wchanger.verify_system_requirements("kde")
        self.assertEqual(exception_context.exception.code, 1)

    @patch("wchanger.set_kde_background", return_value=True)
    @patch("time.sleep")
    def test_run_wallpaper_cycle_kde(
        self, mock_sleep: MagicMock, mock_set_kde: MagicMock
    ) -> None:
        """run_wallpaper_cycle should invoke set_kde_background when desktop is kde."""
        image_path = self.test_dir / "wallpaper.png"
        Image.new("RGB", (10, 10)).save(image_path)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.run_wallpaper_cycle(
                desktop_environment="kde",
                wallpapers=[str(image_path)],
                pause_seconds=1,
                repetition=False,
                output_mode="console",
            )
        self.assertEqual(exception_context.exception.code, 0)
        expected_uri = image_path.resolve().as_uri()
        mock_set_kde.assert_called_once_with(expected_uri)

    @patch("shutil.which")
    def test_setup_auto_start_missing_systemctl(self, mock_which: MagicMock) -> None:
        """setup_auto_start should exit when systemctl is missing."""
        mock_which.return_value = None
        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start()
        self.assertEqual(exception_context.exception.code, 1)

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_sudo_failure(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_auto_start should exit with status 1 if sudo/systemctl fails."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_prompt.side_effect = [30, self.test_dir]
        mock_run.return_value = MagicMock(returncode=1)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start()
        self.assertEqual(exception_context.exception.code, 1)

    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_kde_override(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_auto_start with desktop_override='kde' should inject --kde into ExecStart."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [45, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start(desktop_override="kde")
        self.assertEqual(exception_context.exception.code, 0)

        # First subprocess call is sudo tee to write the service definition
        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--kde", written_service_content)
        self.assertIn("-p 45", written_service_content)

    @patch("shutil.which")
    @patch("wchanger.detect_desktop_environment", return_value="kde")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_kde_autodetect(
        self,
        mock_run: MagicMock,
        mock_prompt: MagicMock,
        mock_detect: MagicMock,
        mock_which: MagicMock,
    ) -> None:
        """setup_auto_start should include --kde when KDE is auto-detected."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start()
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--kde", written_service_content)

    def test_cli_help_includes_kde(self) -> None:
        """cli --help should document KDE support and --kde flag."""
        runner = CliRunner()
        result = runner.invoke(wchanger.cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--kde", result.output)
        self.assertIn("KDE Plasma", result.output)

    def test_cli_theme_notice_on_kde(self) -> None:
        """cli with --kde and --theme should notify the user that theme applies only to GNOME."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle"):
            with patch("wchanger.find_kde_qdbus_executable", return_value="qdbus"):
                result = runner.invoke(
                    wchanger.cli,
                    ["--kde", "-t", "dark", "-p", "10", str(self.test_dir)],
                )
        self.assertIn("The --theme option applies only to GNOME and will be ignored on KDE Plasma", result.output)

    def test_cli_plasma_flag_alias(self) -> None:
        """cli should accept --plasma as an alias for --kde."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle") as mock_cycle:
            with patch("wchanger.find_kde_qdbus_executable", return_value="qdbus"):
                result = runner.invoke(
                    wchanger.cli,
                    ["--plasma", "-p", "10", str(self.test_dir)],
                )
        self.assertEqual(result.exit_code, 0)
        mock_cycle.assert_called_once()
        self.assertEqual(mock_cycle.call_args.kwargs["desktop_environment"], "kde")

    @patch("os.fork", return_value=12345)
    def test_cli_run_background_kde(self, mock_fork: MagicMock) -> None:
        """cli with --run-background and --kde should announce KDE Plasma mode."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("wchanger.find_kde_qdbus_executable", return_value="qdbus"):
            result = runner.invoke(
                wchanger.cli,
                ["--kde", "--run-background", "-p", "30", str(self.test_dir)],
            )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("PID: 12345", result.output)
        self.assertIn("Mode: KDE Plasma", result.output)

    def test_detect_desktop_kde_variations(self) -> None:
        """detect_desktop_environment should recognize various desktop session variations for KDE."""
        test_cases = [
            ({"XDG_CURRENT_DESKTOP": "KDE", "DESKTOP_SESSION": ""}, "kde"),
            ({"XDG_CURRENT_DESKTOP": "plasma", "DESKTOP_SESSION": ""}, "kde"),
            ({"XDG_CURRENT_DESKTOP": "", "DESKTOP_SESSION": "/usr/share/xsessions/plasma"}, "kde"),
            ({"XDG_CURRENT_DESKTOP": "", "DESKTOP_SESSION": "plasmawayland"}, "kde"),
            ({"XDG_CURRENT_DESKTOP": "KDE:Plasma", "DESKTOP_SESSION": "default"}, "kde"),
            ({"XDG_CURRENT_DESKTOP": "MATE", "DESKTOP_SESSION": "mate"}, "mate"),
            ({"XDG_CURRENT_DESKTOP": "XFCE", "DESKTOP_SESSION": "xfce"}, "xfce"),
            ({"XDG_CURRENT_DESKTOP": "LXQt", "DESKTOP_SESSION": "lxqt"}, "lxqt"),
            ({"XDG_CURRENT_DESKTOP": "i3", "DESKTOP_SESSION": "i3"}, None),
            ({"XDG_CURRENT_DESKTOP": "bspwm", "DESKTOP_SESSION": "bspwm"}, None),
        ]
        for environment_variables, expected_result in test_cases:
            with patch.dict(os.environ, environment_variables, clear=True):
                self.assertEqual(
                    wchanger.detect_desktop_environment(),
                    expected_result,
                    msg=f"Failed for env {environment_variables}",
                )

    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    @patch("subprocess.run")
    def test_set_kde_wallpaper_with_spaces_and_special_chars(
        self, mock_run: MagicMock, mock_find_qdbus: MagicMock
    ) -> None:
        """set_kde_wallpaper should format paths with spaces and special characters properly."""
        mock_run.return_value = MagicMock(returncode=0)
        wallpaper_uri = "file:///home/user/My%20Photos/wallpaper%20(1).jpg"

        success = wchanger.set_kde_wallpaper(wallpaper_uri)
        self.assertTrue(success)
        command_args = mock_run.call_args[0][0]
        self.assertIn(f'desktop.writeConfig("Image", "{wallpaper_uri}");', command_args[4])


    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    @patch("subprocess.run")
    def test_set_kde_wallpaper_raw_filepath(
        self, mock_run: MagicMock, mock_find_qdbus: MagicMock
    ) -> None:
        """set_kde_wallpaper should convert raw POSIX filepaths to file:// URIs."""
        mock_run.return_value = MagicMock(returncode=0)
        raw_path = "/home/user/Pictures/sample.jpg"

        success = wchanger.set_kde_wallpaper(raw_path)
        self.assertTrue(success)
        command_args = mock_run.call_args[0][0]
        self.assertIn('desktop.writeConfig("Image", "file:///home/user/Pictures/sample.jpg");', command_args[4])

    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    @patch("subprocess.run")
    def test_set_kde_wallpaper_escapes_quotes_and_backslashes(
        self, mock_run: MagicMock, mock_find_qdbus: MagicMock
    ) -> None:
        """set_kde_wallpaper should escape double quotes and backslashes inside JavaScript."""
        mock_run.return_value = MagicMock(returncode=0)
        tricky_uri = 'file:///home/user/photo"with"quotes.png'

        success = wchanger.set_kde_wallpaper(tricky_uri)
        self.assertTrue(success)
        command_args = mock_run.call_args[0][0]
        self.assertIn(r'desktop.writeConfig("Image", "file:///home/user/photo\"with\"quotes.png");', command_args[4])

    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_path_with_spaces(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_auto_start should safely quote directory paths containing spaces in ExecStart."""
        folder_with_spaces = self.test_dir / "Wallpapers Folder"
        folder_with_spaces.mkdir()
        image_file = folder_with_spaces / "wallpaper.jpg"
        Image.new("RGB", (5, 5)).save(image_file)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, folder_with_spaces]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start(desktop_override="kde")
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn(shlex.quote(str(folder_with_spaces.resolve())), written_service_content)

    @patch("sys.stdin.isatty", return_value=True)
    @patch("wchanger.detect_desktop_environment", return_value=None)
    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_prompts_when_desktop_undetected(
        self,
        mock_run: MagicMock,
        mock_prompt: MagicMock,
        mock_which: MagicMock,
        mock_detect: MagicMock,
        mock_isatty: MagicMock,
    ) -> None:
        """setup_auto_start should prompt for desktop environment if auto-detection returns None."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        # Prompt sequence: pause duration, photo directory, desktop environment choice
        mock_prompt.side_effect = [30, self.test_dir, "kde"]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start()
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--kde", written_service_content)

    @patch("sys.stdin.isatty", return_value=False)
    @patch("wchanger.detect_desktop_environment", return_value=None)
    @patch("shutil.which")
    @patch("click.prompt")
    def test_setup_auto_start_unattended_fails_when_desktop_undetected(
        self,
        mock_prompt: MagicMock,
        mock_which: MagicMock,
        mock_detect: MagicMock,
        mock_isatty: MagicMock,
    ) -> None:
        """setup_auto_start without a TTY should fail cleanly if desktop cannot be detected."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [30, self.test_dir]

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start()
        self.assertEqual(exception_context.exception.code, 1)

    @patch("os.fork", return_value=0)
    @patch("os.setsid")
    @patch("os.open", return_value=99)
    @patch("os.dup2")
    @patch("os.close")
    @patch("wchanger.run_wallpaper_cycle")
    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    def test_cli_run_background_child_execution(
        self,
        mock_find_qdbus: MagicMock,
        mock_cycle: MagicMock,
        mock_close: MagicMock,
        mock_dup2: MagicMock,
        mock_open: MagicMock,
        mock_setsid: MagicMock,
        mock_fork: MagicMock,
    ) -> None:
        """In background mode, the child process (fork==0) sets sid and runs wallpaper cycle without second fork."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--kde", "--run-background", "-p", "30", str(self.test_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        mock_setsid.assert_called_once()
        mock_cycle.assert_called_once()
        self.assertEqual(mock_fork.call_count, 1)

    def test_is_valid_image_file_svg_oserror(self) -> None:
        """is_valid_image_file should handle stat OSError gracefully on SVG files."""
        svg_file = self.test_dir / "broken.svg"
        svg_file.write_text("<svg></svg>")

        with patch.object(Path, "stat", side_effect=OSError("Disk error")):
            self.assertFalse(wchanger.is_valid_image_file(svg_file))

    # XFCE Wallpaper Setter Tests
    @patch("subprocess.run")
    def test_set_xfce_wallpaper_with_discovered_properties(self, mock_run: MagicMock) -> None:
        """XFCE setter should find backdrop properties containing last-image and update all of them."""
        list_output = (
            "/backdrop/screen0/monitor0/workspace0/last-image\n"
            "/backdrop/screen0/monitor1/workspace0/last-image\n"
            "/backdrop/screen0/monitor0/workspace0/image-style\n"
        )
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=list_output),
            MagicMock(returncode=0),
            MagicMock(returncode=0),
        ]
        test_path = "/home/user/wallpapers/image.png"

        result = wchanger.set_xfce_wallpaper(test_path)
        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 3)

        list_call = mock_run.call_args_list[0]
        self.assertEqual(list_call[0][0], ["xfconf-query", "-c", "xfce4-desktop", "-l"])

        first_set = mock_run.call_args_list[1]
        self.assertEqual(
            first_set[0][0],
            ["xfconf-query", "-c", "xfce4-desktop", "-p", "/backdrop/screen0/monitor0/workspace0/last-image", "-s", test_path],
        )

        second_set = mock_run.call_args_list[2]
        self.assertEqual(
            second_set[0][0],
            ["xfconf-query", "-c", "xfce4-desktop", "-p", "/backdrop/screen0/monitor1/workspace0/last-image", "-s", test_path],
        )

    @patch("subprocess.run")
    def test_set_xfce_wallpaper_fallback_primary(self, mock_run: MagicMock) -> None:
        """XFCE setter should fall back to default monitor0 property if -l yields no last-image properties."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0),
        ]
        test_path = "/home/user/wallpapers/image.png"

        result = wchanger.set_xfce_wallpaper(test_path)
        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 2)
        fallback_call = mock_run.call_args_list[1]
        self.assertEqual(
            fallback_call[0][0],
            ["xfconf-query", "-c", "xfce4-desktop", "-p", "/backdrop/screen0/monitor0/workspace0/last-image", "-s", test_path],
        )

    @patch("subprocess.run")
    def test_set_xfce_wallpaper_fallback_secondary(self, mock_run: MagicMock) -> None:
        """XFCE setter should fall back to monitorHDMI-1 if monitor0 property fails."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=1),
            MagicMock(returncode=0),
        ]
        test_path = "/home/user/wallpapers/image.png"

        result = wchanger.set_xfce_wallpaper(test_path)
        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 3)
        secondary_call = mock_run.call_args_list[2]
        self.assertEqual(
            secondary_call[0][0],
            ["xfconf-query", "-c", "xfce4-desktop", "-p", "/backdrop/screen0/monitorHDMI-1/workspace0/last-image", "-s", test_path],
        )

    @patch("subprocess.run")
    def test_set_xfce_wallpaper_failure(self, mock_run: MagicMock) -> None:
        """XFCE setter should return False if both fallback properties fail."""
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=1),
            MagicMock(returncode=1),
        ]
        result = wchanger.set_xfce_wallpaper("/home/user/wallpapers/image.png")
        self.assertFalse(result)

    @patch("subprocess.run")
    def test_set_xfce_wallpaper_converts_file_uri(self, mock_run: MagicMock) -> None:
        """XFCE setter should convert file:// URI with encoded spaces to local file path."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/backdrop/screen0/monitor0/workspace0/last-image\n"),
            MagicMock(returncode=0),
        ]
        wallpaper_uri = "file:///home/user/My%20Wallpapers/pic%20(1).jpg"
        result = wchanger.set_xfce_wallpaper(wallpaper_uri)
        self.assertTrue(result)
        second_call = mock_run.call_args_list[1]
        self.assertEqual(second_call[0][0][-1], "/home/user/My Wallpapers/pic (1).jpg")

    def test_set_xfce_wallpaper_alias(self) -> None:
        """set_xfce_wallpaper should be an alias of set_xfce_background."""
        self.assertIs(wchanger.set_xfce_wallpaper, wchanger.set_xfce_background)

    # MATE Wallpaper Setter Tests
    @patch("subprocess.run")
    def test_set_mate_wallpaper_success(self, mock_run: MagicMock) -> None:
        """MATE setter should invoke gsettings set org.mate.background picture-filename."""
        mock_run.return_value = MagicMock(returncode=0)
        test_path = "/home/user/wallpapers/picture.jpg"

        result = wchanger.set_mate_wallpaper(test_path)
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["gsettings", "set", "org.mate.background", "picture-filename", test_path],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_set_mate_wallpaper_failure(self, mock_run: MagicMock) -> None:
        """MATE setter should return False on command failure."""
        mock_run.return_value = MagicMock(returncode=1)
        result = wchanger.set_mate_wallpaper("/home/user/wallpapers/picture.jpg")
        self.assertFalse(result)

    @patch("subprocess.run")
    def test_set_mate_wallpaper_converts_file_uri(self, mock_run: MagicMock) -> None:
        """MATE setter should convert file:// URI to local file path."""
        mock_run.return_value = MagicMock(returncode=0)
        wallpaper_uri = "file:///home/user/Nature%20Photos/forest.png"

        result = wchanger.set_mate_wallpaper(wallpaper_uri)
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["gsettings", "set", "org.mate.background", "picture-filename", "/home/user/Nature Photos/forest.png"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_set_mate_wallpaper_alias(self) -> None:
        """set_mate_wallpaper should be an alias of set_mate_background."""
        self.assertIs(wchanger.set_mate_wallpaper, wchanger.set_mate_background)

    # LXQt Wallpaper Setter Tests
    @patch("subprocess.run")
    def test_set_lxqt_wallpaper_success(self, mock_run: MagicMock) -> None:
        """LXQt setter should invoke pcmanfm-qt --set-wallpaper=<filepath>."""
        mock_run.return_value = MagicMock(returncode=0)
        test_path = "/home/user/wallpapers/lxqt_bg.png"

        result = wchanger.set_lxqt_wallpaper(test_path)
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["pcmanfm-qt", f"--set-wallpaper={test_path}"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_set_lxqt_wallpaper_failure(self, mock_run: MagicMock) -> None:
        """LXQt setter should return False on command failure."""
        mock_run.return_value = MagicMock(returncode=1)
        result = wchanger.set_lxqt_wallpaper("/home/user/wallpapers/lxqt_bg.png")
        self.assertFalse(result)

    @patch("subprocess.run")
    def test_set_lxqt_wallpaper_converts_file_uri(self, mock_run: MagicMock) -> None:
        """LXQt setter should convert file:// URI to local file path."""
        mock_run.return_value = MagicMock(returncode=0)
        wallpaper_uri = "file:///home/user/Abstract%20Art/minimal.webp"

        result = wchanger.set_lxqt_wallpaper(wallpaper_uri)
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["pcmanfm-qt", "--set-wallpaper=/home/user/Abstract Art/minimal.webp"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_set_lxqt_wallpaper_alias(self) -> None:
        """set_lxqt_wallpaper should be an alias of set_lxqt_background."""
        self.assertIs(wchanger.set_lxqt_wallpaper, wchanger.set_lxqt_background)

    # System Requirements Tests for XFCE, MATE, and LXQt
    @patch("platform.system", return_value="Linux")
    @patch("shutil.which", return_value="/usr/bin/xfconf-query")
    def test_verify_system_requirements_xfce_success(
        self, mock_which: MagicMock, mock_platform: MagicMock
    ) -> None:
        """verify_system_requirements for XFCE should succeed when xfconf-query is present."""
        wchanger.verify_system_requirements("xfce")

    @patch("platform.system", return_value="Linux")
    @patch("shutil.which", return_value=None)
    def test_verify_system_requirements_xfce_failure(
        self, mock_which: MagicMock, mock_platform: MagicMock
    ) -> None:
        """verify_system_requirements for XFCE should exit when xfconf-query is missing."""
        with self.assertRaises(SystemExit) as exception_context:
            wchanger.verify_system_requirements("xfce")
        self.assertEqual(exception_context.exception.code, 1)

    @patch("platform.system", return_value="Linux")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_verify_system_requirements_mate_success(
        self, mock_which: MagicMock, mock_platform: MagicMock
    ) -> None:
        """verify_system_requirements for MATE should succeed when gsettings is present."""
        wchanger.verify_system_requirements("mate")

    @patch("platform.system", return_value="Linux")
    @patch("shutil.which", return_value=None)
    def test_verify_system_requirements_mate_failure(
        self, mock_which: MagicMock, mock_platform: MagicMock
    ) -> None:
        """verify_system_requirements for MATE should exit when gsettings is missing."""
        with self.assertRaises(SystemExit) as exception_context:
            wchanger.verify_system_requirements("mate")
        self.assertEqual(exception_context.exception.code, 1)

    @patch("platform.system", return_value="Linux")
    @patch("shutil.which", return_value="/usr/bin/pcmanfm-qt")
    def test_verify_system_requirements_lxqt_success(
        self, mock_which: MagicMock, mock_platform: MagicMock
    ) -> None:
        """verify_system_requirements for LXQt should succeed when pcmanfm-qt is present."""
        wchanger.verify_system_requirements("lxqt")

    @patch("platform.system", return_value="Linux")
    @patch("shutil.which", return_value=None)
    def test_verify_system_requirements_lxqt_failure(
        self, mock_which: MagicMock, mock_platform: MagicMock
    ) -> None:
        """verify_system_requirements for LXQt should exit when pcmanfm-qt is missing."""
        with self.assertRaises(SystemExit) as exception_context:
            wchanger.verify_system_requirements("lxqt")
        self.assertEqual(exception_context.exception.code, 1)

    # run_wallpaper_cycle Tests for XFCE, MATE, LXQt
    @patch("wchanger.set_xfce_background", return_value=True)
    @patch("time.sleep")
    def test_run_wallpaper_cycle_xfce(
        self, mock_sleep: MagicMock, mock_set_xfce: MagicMock
    ) -> None:
        """run_wallpaper_cycle should invoke set_xfce_background when desktop is xfce."""
        image_path = self.test_dir / "wallpaper.png"
        Image.new("RGB", (10, 10)).save(image_path)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.run_wallpaper_cycle(
                desktop_environment="xfce",
                wallpapers=[str(image_path)],
                pause_seconds=1,
                repetition=False,
                output_mode="console",
            )
        self.assertEqual(exception_context.exception.code, 0)
        mock_set_xfce.assert_called_once_with(str(image_path))

    @patch("wchanger.set_mate_background", return_value=True)
    @patch("time.sleep")
    def test_run_wallpaper_cycle_mate(
        self, mock_sleep: MagicMock, mock_set_mate: MagicMock
    ) -> None:
        """run_wallpaper_cycle should invoke set_mate_background when desktop is mate."""
        image_path = self.test_dir / "wallpaper.png"
        Image.new("RGB", (10, 10)).save(image_path)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.run_wallpaper_cycle(
                desktop_environment="mate",
                wallpapers=[str(image_path)],
                pause_seconds=1,
                repetition=False,
                output_mode="console",
            )
        self.assertEqual(exception_context.exception.code, 0)
        mock_set_mate.assert_called_once_with(str(image_path))

    @patch("wchanger.set_lxqt_background", return_value=True)
    @patch("time.sleep")
    def test_run_wallpaper_cycle_lxqt(
        self, mock_sleep: MagicMock, mock_set_lxqt: MagicMock
    ) -> None:
        """run_wallpaper_cycle should invoke set_lxqt_background when desktop is lxqt."""
        image_path = self.test_dir / "wallpaper.png"
        Image.new("RGB", (10, 10)).save(image_path)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.run_wallpaper_cycle(
                desktop_environment="lxqt",
                wallpapers=[str(image_path)],
                pause_seconds=1,
                repetition=False,
                output_mode="console",
            )
        self.assertEqual(exception_context.exception.code, 0)
        mock_set_lxqt.assert_called_once_with(str(image_path))

    # CLI Tests for XFCE, MATE, LXQt
    def test_cli_help_includes_xfce_mate_lxqt(self) -> None:
        """cli --help should document XFCE, MATE, and LXQt support and their flags."""
        runner = CliRunner()
        result = runner.invoke(wchanger.cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--xfce", result.output)
        self.assertIn("--mate", result.output)
        self.assertIn("--lxqt", result.output)
        self.assertIn("XFCE", result.output)
        self.assertIn("MATE", result.output)
        self.assertIn("LXQt", result.output)

    def test_cli_xfce_flag(self) -> None:
        """cli with --xfce should dispatch to xfce desktop environment."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle") as mock_cycle:
            with patch("shutil.which", return_value="/usr/bin/xfconf-query"):
                result = runner.invoke(
                    wchanger.cli,
                    ["--xfce", "-p", "10", str(self.test_dir)],
                )
        self.assertEqual(result.exit_code, 0)
        mock_cycle.assert_called_once()
        self.assertEqual(mock_cycle.call_args.kwargs["desktop_environment"], "xfce")

    def test_cli_mate_flag(self) -> None:
        """cli with --mate should dispatch to mate desktop environment."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle") as mock_cycle:
            with patch("shutil.which", return_value="/usr/bin/gsettings"):
                result = runner.invoke(
                    wchanger.cli,
                    ["--mate", "-p", "10", str(self.test_dir)],
                )
        self.assertEqual(result.exit_code, 0)
        mock_cycle.assert_called_once()
        self.assertEqual(mock_cycle.call_args.kwargs["desktop_environment"], "mate")

    def test_cli_lxqt_flag(self) -> None:
        """cli with --lxqt should dispatch to lxqt desktop environment."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle") as mock_cycle:
            with patch("shutil.which", return_value="/usr/bin/pcmanfm-qt"):
                result = runner.invoke(
                    wchanger.cli,
                    ["--lxqt", "-p", "10", str(self.test_dir)],
                )
        self.assertEqual(result.exit_code, 0)
        mock_cycle.assert_called_once()
        self.assertEqual(mock_cycle.call_args.kwargs["desktop_environment"], "lxqt")

    def test_cli_theme_notice_on_xfce(self) -> None:
        """cli with --xfce and --theme should notify the user that theme applies only to GNOME."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle"):
            with patch("shutil.which", return_value="/usr/bin/xfconf-query"):
                result = runner.invoke(
                    wchanger.cli,
                    ["--xfce", "-t", "dark", "-p", "10", str(self.test_dir)],
                )
        self.assertIn("The --theme option applies only to GNOME and will be ignored on XFCE", result.output)

    def test_cli_theme_notice_on_mate(self) -> None:
        """cli with --mate and --theme should notify the user that theme applies only to GNOME."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle"):
            with patch("shutil.which", return_value="/usr/bin/gsettings"):
                result = runner.invoke(
                    wchanger.cli,
                    ["--mate", "-t", "light", "-p", "10", str(self.test_dir)],
                )
        self.assertIn("The --theme option applies only to GNOME and will be ignored on MATE", result.output)

    def test_cli_theme_notice_on_lxqt(self) -> None:
        """cli with --lxqt and --theme should notify the user that theme applies only to GNOME."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle"):
            with patch("shutil.which", return_value="/usr/bin/pcmanfm-qt"):
                result = runner.invoke(
                    wchanger.cli,
                    ["--lxqt", "-t", "dark", "-p", "10", str(self.test_dir)],
                )
        self.assertIn("The --theme option applies only to GNOME and will be ignored on LXQt", result.output)

    @patch("os.fork", return_value=12345)
    def test_cli_run_background_xfce(self, mock_fork: MagicMock) -> None:
        """cli with --run-background and --xfce should announce XFCE mode."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("shutil.which", return_value="/usr/bin/xfconf-query"):
            result = runner.invoke(
                wchanger.cli,
                ["--xfce", "--run-background", "-p", "30", str(self.test_dir)],
            )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("PID: 12345", result.output)
        self.assertIn("Mode: XFCE", result.output)

    @patch("os.fork", return_value=12345)
    def test_cli_run_background_mate(self, mock_fork: MagicMock) -> None:
        """cli with --run-background and --mate should announce MATE mode."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("shutil.which", return_value="/usr/bin/gsettings"):
            result = runner.invoke(
                wchanger.cli,
                ["--mate", "--run-background", "-p", "30", str(self.test_dir)],
            )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("PID: 12345", result.output)
        self.assertIn("Mode: MATE", result.output)

    @patch("os.fork", return_value=12345)
    def test_cli_run_background_lxqt(self, mock_fork: MagicMock) -> None:
        """cli with --run-background and --lxqt should announce LXQt mode."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("shutil.which", return_value="/usr/bin/pcmanfm-qt"):
            result = runner.invoke(
                wchanger.cli,
                ["--lxqt", "--run-background", "-p", "30", str(self.test_dir)],
            )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("PID: 12345", result.output)
        self.assertIn("Mode: LXQt", result.output)

    # Auto-start Wizard Tests for XFCE, MATE, LXQt
    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_xfce_override(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_auto_start with desktop_override='xfce' should inject --xfce into ExecStart."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start(desktop_override="xfce")
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--xfce", written_service_content)

    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_mate_override(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_auto_start with desktop_override='mate' should inject --mate into ExecStart."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start(desktop_override="mate")
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--mate", written_service_content)

    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_lxqt_override(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_auto_start with desktop_override='lxqt' should inject --lxqt into ExecStart."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start(desktop_override="lxqt")
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--lxqt", written_service_content)

    @patch("shutil.which")
    @patch("wchanger.detect_desktop_environment", return_value="xfce")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_xfce_autodetect(
        self,
        mock_run: MagicMock,
        mock_prompt: MagicMock,
        mock_detect: MagicMock,
        mock_which: MagicMock,
    ) -> None:
        """setup_auto_start should include --xfce when XFCE is auto-detected."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start()
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--xfce", written_service_content)

    @patch("sys.stdin.isatty", return_value=True)
    @patch("wchanger.detect_desktop_environment", return_value=None)
    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_prompt_choice_mate(
        self,
        mock_run: MagicMock,
        mock_prompt: MagicMock,
        mock_which: MagicMock,
        mock_detect: MagicMock,
        mock_isatty: MagicMock,
    ) -> None:
        """setup_auto_start should allow picking mate when prompted."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [30, self.test_dir, "mate"]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start()
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--mate", written_service_content)

    @patch("shutil.which")
    @patch("wchanger.detect_desktop_environment", return_value="mate")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_mate_autodetect(
        self,
        mock_run: MagicMock,
        mock_prompt: MagicMock,
        mock_detect: MagicMock,
        mock_which: MagicMock,
    ) -> None:
        """setup_auto_start should include --mate when MATE is auto-detected."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start()
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--mate", written_service_content)

    @patch("shutil.which")
    @patch("wchanger.detect_desktop_environment", return_value="lxqt")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_lxqt_autodetect(
        self,
        mock_run: MagicMock,
        mock_prompt: MagicMock,
        mock_detect: MagicMock,
        mock_which: MagicMock,
    ) -> None:
        """setup_auto_start should include --lxqt when LXQt is auto-detected."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start()
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--lxqt", written_service_content)

    def test_resolve_to_file_path_with_unencoded_hash_and_query(self) -> None:
        """_resolve_to_file_path should not truncate unencoded '#' or '?' in file URIs."""
        uri_with_hash = "file:///home/user/wallpapers/image#1.png"
        resolved_hash = wchanger._resolve_to_file_path(uri_with_hash)
        self.assertEqual(resolved_hash, "/home/user/wallpapers/image#1.png")

        uri_with_query = "file:///home/user/wallpapers/image?1.png"
        resolved_query = wchanger._resolve_to_file_path(uri_with_query)
        self.assertEqual(resolved_query, "/home/user/wallpapers/image?1.png")

    def test_resolve_to_file_path_encoded_hash_and_spaces(self) -> None:
        """_resolve_to_file_path should properly decode %23 and %20 in file URIs."""
        encoded_uri = "file:///home/user/My%20Photos/wallpaper%2342.jpg"
        resolved = wchanger._resolve_to_file_path(encoded_uri)
        self.assertEqual(resolved, "/home/user/My Photos/wallpaper#42.jpg")

    @patch("subprocess.run")
    def test_set_xfce_wallpaper_deduplicates_properties(self, mock_run: MagicMock) -> None:
        """set_xfce_wallpaper should deduplicate properties returned by xfconf-query -l."""
        duplicate_output = (
            "/backdrop/screen0/monitor0/workspace0/last-image\n"
            "/backdrop/screen0/monitor0/workspace0/last-image\n"
        )
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=duplicate_output),
            MagicMock(returncode=0),
        ]
        test_path = "/home/user/wallpapers/image.png"

        result = wchanger.set_xfce_wallpaper(test_path)
        self.assertTrue(result)
        # Should call xfconf-query -l once, and set the unique property once (total 2 calls, not 3)
        self.assertEqual(mock_run.call_count, 2)

    @patch("subprocess.run")
    def test_set_xfce_wallpaper_one_property_fails(self, mock_run: MagicMock) -> None:
        """set_xfce_wallpaper should return False if any discovered property fails to update."""
        list_output = (
            "/backdrop/screen0/monitor0/workspace0/last-image\n"
            "/backdrop/screen0/monitor1/workspace0/last-image\n"
        )
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=list_output),
            MagicMock(returncode=0),
            MagicMock(returncode=1),
        ]
        result = wchanger.set_xfce_wallpaper("/home/user/wallpapers/image.png")
        self.assertFalse(result)

    @patch("platform.system", return_value="Linux")
    def test_verify_system_requirements_unsupported_desktop(self, mock_platform: MagicMock) -> None:
        """verify_system_requirements should exit with code 1 for unsupported desktop."""
        with self.assertRaises(SystemExit) as exception_context:
            wchanger.verify_system_requirements("unknown_de")
        self.assertEqual(exception_context.exception.code, 1)

    def test_cli_xfce4_flag_alias(self) -> None:
        """cli should accept --xfce4 as an alias for --xfce."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle") as mock_cycle:
            with patch("shutil.which", return_value="/usr/bin/xfconf-query"):
                result = runner.invoke(
                    wchanger.cli,
                    ["--xfce4", "-p", "10", str(self.test_dir)],
                )
        self.assertEqual(result.exit_code, 0)
        mock_cycle.assert_called_once()
        self.assertEqual(mock_cycle.call_args.kwargs["desktop_environment"], "xfce")

    @patch("sys.stdin.isatty", return_value=True)
    @patch("wchanger.detect_desktop_environment", return_value=None)
    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_prompt_choice_xfce(
        self,
        mock_run: MagicMock,
        mock_prompt: MagicMock,
        mock_which: MagicMock,
        mock_detect: MagicMock,
        mock_isatty: MagicMock,
    ) -> None:
        """setup_auto_start should allow picking xfce when prompted."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [30, self.test_dir, "xfce"]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start()
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--xfce", written_service_content)

    @patch("sys.stdin.isatty", return_value=True)
    @patch("wchanger.detect_desktop_environment", return_value=None)
    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_prompt_choice_lxqt(
        self,
        mock_run: MagicMock,
        mock_prompt: MagicMock,
        mock_which: MagicMock,
        mock_detect: MagicMock,
        mock_isatty: MagicMock,
    ) -> None:
        """setup_auto_start should allow picking lxqt when prompted."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [30, self.test_dir, "lxqt"]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start()
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--lxqt", written_service_content)

    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_service_environment_and_working_dir(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_auto_start should include WorkingDirectory and Environment=DISPLAY in service definition."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with patch.dict(os.environ, {"DISPLAY": ":1", "WAYLAND_DISPLAY": "wayland-0"}, clear=False):
            with self.assertRaises(SystemExit) as exception_context:
                wchanger.setup_auto_start(desktop_override="lxqt")
            self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("WorkingDirectory=", written_service_content)
        self.assertIn("Environment=DISPLAY=:1", written_service_content)
        self.assertIn("Environment=WAYLAND_DISPLAY=wayland-0", written_service_content)

    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_color_theme_omitted_on_non_gnome(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_auto_start should omit -t when target desktop is not GNOME."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start(desktop_override="xfce", color_theme="dark")
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertNotIn("-t dark", written_service_content)

    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_color_theme_included_on_gnome(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_auto_start should include -t when target desktop is GNOME."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start(desktop_override="gnome", color_theme="dark")
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("-t dark", written_service_content)

    @patch("time.sleep")
    def test_run_wallpaper_cycle_skips_missing_file(self, mock_sleep: MagicMock) -> None:
        """run_wallpaper_cycle should skip files that do not exist."""
        real_image = self.test_dir / "exists.png"
        Image.new("RGB", (5, 5)).save(real_image)
        missing_image = self.test_dir / "nonexistent.png"

        with patch("wchanger.set_xfce_background", return_value=True) as mock_set:
            with self.assertRaises(SystemExit) as exception_context:
                wchanger.run_wallpaper_cycle(
                    desktop_environment="xfce",
                    wallpapers=[str(missing_image), str(real_image)],
                    pause_seconds=1,
                    repetition=False,
                    output_mode="console",
                )
            self.assertEqual(exception_context.exception.code, 0)
            mock_set.assert_called_once_with(str(real_image))

    @patch("time.sleep")
    def test_run_wallpaper_cycle_logging_mode(self, mock_sleep: MagicMock) -> None:
        """run_wallpaper_cycle in log output mode should emit log records."""
        test_image = self.test_dir / "wallpaper.png"
        Image.new("RGB", (5, 5)).save(test_image)

        with patch("wchanger.set_mate_background", return_value=True):
            with patch("logging.info") as mock_logging_info:
                with self.assertRaises(SystemExit) as exception_context:
                    wchanger.run_wallpaper_cycle(
                        desktop_environment="mate",
                        wallpapers=[str(test_image)],
                        pause_seconds=1,
                        repetition=False,
                        output_mode="log",
                    )
                self.assertEqual(exception_context.exception.code, 0)
                mock_logging_info.assert_any_call(f"Wallpaper changed on MATE to {test_image}.")

    def test_configure_logging_creates_handler(self) -> None:
        """configure_logging with 'log' mode should add a FileHandler."""
        log_file = self.test_dir / "custom.log"
        wchanger.configure_logging("log", log_file_path=log_file)
        import logging
        root_logger = logging.getLogger()
        handler_found = any(
            isinstance(logging_handler, logging.FileHandler)
            and Path(logging_handler.baseFilename) == log_file.resolve()
            for logging_handler in root_logger.handlers
        )
        self.assertTrue(handler_found)

    @patch("subprocess.run")
    def test_set_gnome_wallpaper_raw_filepath(self, mock_run: MagicMock) -> None:
        """set_gnome_wallpaper should convert raw POSIX paths to file:// URIs."""
        mock_run.return_value = MagicMock(returncode=0)
        raw_path = "/home/user/Pictures/sample.jpg"

        success = wchanger.set_gnome_wallpaper(raw_path, theme="dark")
        self.assertTrue(success)
        mock_run.assert_called_once_with(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri-dark",
                "file:///home/user/Pictures/sample.jpg",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_set_cinnamon_wallpaper_raw_filepath(self, mock_run: MagicMock) -> None:
        """set_cinnamon_wallpaper should convert raw POSIX paths to file:// URIs."""
        mock_run.return_value = MagicMock(returncode=0)
        raw_path = "/home/user/Pictures/sample.jpg"

        success = wchanger.set_cinnamon_wallpaper(raw_path)
        self.assertTrue(success)
        mock_run.assert_called_once_with(
            [
                "gsettings",
                "set",
                "org.cinnamon.desktop.background",
                "picture-uri",
                "file:///home/user/Pictures/sample.jpg",
            ],
            capture_output=True,
            text=True,
            check=False,
        )


    # Online Wallpaper Source Tests
    @patch("wchanger.urlopen")
    def test_fetch_wallhaven_url_success(self, mock_urlopen: MagicMock) -> None:
        """fetch_wallhaven_url should parse JSON response and return image path."""
        fake_response = MagicMock()
        fake_response.read.return_value = (
            b'{"data": [{"id": "abc", "path": "https://w.wallhaven.cc/full/abc.jpg"}]}'
        )
        fake_response.__enter__.return_value = fake_response
        mock_urlopen.return_value = fake_response

        wallpaper_url = wchanger.fetch_wallhaven_url()
        self.assertEqual(wallpaper_url, "https://w.wallhaven.cc/full/abc.jpg")

    @patch("wchanger.urlopen")
    def test_fetch_wallhaven_url_empty_data(self, mock_urlopen: MagicMock) -> None:
        """fetch_wallhaven_url should raise ValueError when data is empty."""
        fake_response = MagicMock()
        fake_response.read.return_value = b'{"data": []}'
        fake_response.__enter__.return_value = fake_response
        mock_urlopen.return_value = fake_response

        with self.assertRaises(ValueError) as exception_context:
            wchanger.fetch_wallhaven_url()
        self.assertIn("No wallpapers found", str(exception_context.exception))

    @patch("wchanger.urlopen")
    def test_fetch_wallhaven_url_missing_path(self, mock_urlopen: MagicMock) -> None:
        """fetch_wallhaven_url should raise ValueError when entry is missing path."""
        fake_response = MagicMock()
        fake_response.read.return_value = b'{"data": [{"id": "123"}]}'
        fake_response.__enter__.return_value = fake_response
        mock_urlopen.return_value = fake_response

        with self.assertRaises(ValueError) as exception_context:
            wchanger.fetch_wallhaven_url()
        self.assertIn("Wallhaven entry missing image path", str(exception_context.exception))

    @patch("wchanger.urlopen")
    def test_fetch_bing_url_success(self, mock_urlopen: MagicMock) -> None:
        """fetch_bing_url should parse JSON response and construct full image URL."""
        fake_response = MagicMock()
        fake_response.read.return_value = (
            b'{"images": [{"url": "/th?id=OHR.SampleBing_EN-US_1920x1080.jpg"}]}'
        )
        fake_response.__enter__.return_value = fake_response
        mock_urlopen.return_value = fake_response

        wallpaper_url = wchanger.fetch_bing_url()
        self.assertEqual(wallpaper_url, "https://www.bing.com/th?id=OHR.SampleBing_EN-US_1920x1080.jpg")

    @patch("wchanger.urlopen")
    def test_fetch_bing_url_empty_images(self, mock_urlopen: MagicMock) -> None:
        """fetch_bing_url should raise ValueError when images list is empty."""
        fake_response = MagicMock()
        fake_response.read.return_value = b'{"images": []}'
        fake_response.__enter__.return_value = fake_response
        mock_urlopen.return_value = fake_response

        with self.assertRaises(ValueError) as exception_context:
            wchanger.fetch_bing_url()
        self.assertIn("No images found", str(exception_context.exception))

    def test_fetch_picsum_url(self) -> None:
        """fetch_picsum_url should return a 1920x1080 random URL."""
        wallpaper_url = wchanger.fetch_picsum_url()
        self.assertTrue(wallpaper_url.startswith("https://picsum.photos/1920/1080?random="))

    def test_fetch_loremflickr_url(self) -> None:
        """fetch_loremflickr_url should return a 1920x1080 nature lock URL."""
        wallpaper_url = wchanger.fetch_loremflickr_url()
        self.assertTrue(wallpaper_url.startswith("https://loremflickr.com/1920/1080/nature?lock="))

    @patch("wchanger.urlopen")
    def test_download_online_wallpaper_success(self, mock_urlopen: MagicMock) -> None:
        """download_online_wallpaper should fetch bytes and write to destination path."""
        fake_response = MagicMock()
        fake_response.read.return_value = b"FAKE_IMAGE_BYTES_123"
        fake_response.__enter__.return_value = fake_response
        mock_urlopen.return_value = fake_response

        dest_file = self.test_dir / "cache" / "wallpaper_test.jpg"
        result_path = wchanger.download_online_wallpaper("https://example.com/image.jpg", dest_file)

        self.assertEqual(result_path, dest_file)
        self.assertTrue(dest_file.exists())
        self.assertEqual(dest_file.read_bytes(), b"FAKE_IMAGE_BYTES_123")

    @patch("wchanger.urlopen")
    def test_download_online_wallpaper_empty_content(self, mock_urlopen: MagicMock) -> None:
        """download_online_wallpaper should raise ValueError when content is empty."""
        fake_response = MagicMock()
        fake_response.read.return_value = b""
        fake_response.__enter__.return_value = fake_response
        mock_urlopen.return_value = fake_response

        dest_file = self.test_dir / "cache" / "wallpaper_empty.jpg"
        with self.assertRaises(ValueError) as exception_context:
            wchanger.download_online_wallpaper("https://example.com/image.jpg", dest_file)
        self.assertIn("Received empty image content", str(exception_context.exception))

    def test_format_network_error_http(self) -> None:
        """format_network_error should format HTTPError with status code."""
        from urllib.error import HTTPError
        error = HTTPError("https://example.com", 404, "Not Found", {}, None)
        error_message = wchanger.format_network_error("bing", error)
        self.assertIn("404", error_message)
        self.assertIn("bing", error_message)

    def test_format_network_error_url(self) -> None:
        """format_network_error should format URLError advising connection check."""
        from urllib.error import URLError
        error = URLError("Temporary failure in name resolution")
        error_message = wchanger.format_network_error("wallhaven", error)
        self.assertIn("check your internet connection", error_message)
        self.assertIn("wallhaven", error_message)

    @patch("wchanger.set_gnome_background", return_value=True)
    @patch("wchanger.set_cinnamon_background", return_value=True)
    @patch("wchanger.set_kde_background", return_value=True)
    @patch("wchanger.set_xfce_background", return_value=True)
    @patch("wchanger.set_mate_background", return_value=True)
    @patch("wchanger.set_lxqt_background", return_value=True)
    def test_set_wallpaper_for_desktop_all_environments(
        self,
        mock_lxqt: MagicMock,
        mock_mate: MagicMock,
        mock_xfce: MagicMock,
        mock_kde: MagicMock,
        mock_cinnamon: MagicMock,
        mock_gnome: MagicMock,
    ) -> None:
        """set_wallpaper_for_desktop should dispatch properly across all 6 desktop environments."""
        sample_file = self.test_dir / "test.jpg"
        sample_file.write_bytes(b"data")

        # GNOME
        success, error_message = wchanger.set_wallpaper_for_desktop("gnome", sample_file, "dark")
        self.assertTrue(success)
        mock_gnome.assert_called_once_with(sample_file.resolve().as_uri(), "dark")

        # Cinnamon
        success, error_message = wchanger.set_wallpaper_for_desktop("cinnamon", sample_file)
        self.assertTrue(success)
        mock_cinnamon.assert_called_once_with(sample_file.resolve().as_uri())

        # KDE
        success, error_message = wchanger.set_wallpaper_for_desktop("kde", sample_file)
        self.assertTrue(success)
        mock_kde.assert_called_once_with(sample_file.resolve().as_uri())

        # XFCE
        success, error_message = wchanger.set_wallpaper_for_desktop("xfce", sample_file)
        self.assertTrue(success)
        mock_xfce.assert_called_once_with(str(sample_file))

        # MATE
        success, error_message = wchanger.set_wallpaper_for_desktop("mate", sample_file)
        self.assertTrue(success)
        mock_mate.assert_called_once_with(str(sample_file))

        # LXQt
        success, error_message = wchanger.set_wallpaper_for_desktop("lxqt", sample_file)
        self.assertTrue(success)
        mock_lxqt.assert_called_once_with(str(sample_file))

    @patch("wchanger.set_wallpaper_for_desktop", return_value=(True, "Wallpaper changed"))
    @patch("wchanger.download_online_wallpaper")
    @patch("wchanger.ONLINE_PROVIDERS")
    def test_run_online_wallpaper_cycle_success(
        self,
        mock_providers: MagicMock,
        mock_download: MagicMock,
        mock_setter: MagicMock,
    ) -> None:
        """run_online_wallpaper_cycle should fetch, download, set wallpaper and exit when repetition=False."""
        mock_fetcher = MagicMock(return_value="https://example.com/wallpaper.jpg")
        mock_providers.get.return_value = mock_fetcher

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.run_online_wallpaper_cycle(
                desktop_environment="gnome",
                provider="bing",
                pause_seconds=1,
                repetition=False,
                output_mode="console",
                cache_dir=self.test_dir,
            )
        self.assertEqual(exception_context.exception.code, 0)
        mock_fetcher.assert_called_once()
        mock_download.assert_called_once()
        mock_setter.assert_called_once()

    @patch("wchanger.ONLINE_PROVIDERS")
    def test_run_online_wallpaper_cycle_network_error_exit(
        self, mock_providers: MagicMock
    ) -> None:
        """run_online_wallpaper_cycle should exit with 1 on network error when repetition=False."""
        from urllib.error import URLError
        mock_fetcher = MagicMock(side_effect=URLError("DNS resolution failed"))
        mock_providers.get.return_value = mock_fetcher

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.run_online_wallpaper_cycle(
                desktop_environment="gnome",
                provider="wallhaven",
                pause_seconds=1,
                repetition=False,
                output_mode="console",
                cache_dir=self.test_dir,
            )
        self.assertEqual(exception_context.exception.code, 1)

    def test_run_online_wallpaper_cycle_unknown_provider(self) -> None:
        """run_online_wallpaper_cycle should raise ValueError on invalid provider name."""
        with self.assertRaises(ValueError) as exception_context:
            wchanger.run_online_wallpaper_cycle(
                desktop_environment="gnome",
                provider="nonexistent_provider",
                pause_seconds=1,
                repetition=False,
                output_mode="console",
            )
        self.assertIn("Unknown online provider", str(exception_context.exception))

    def test_cli_help_includes_online(self) -> None:
        """cli --help should list the --online option with all supported providers."""
        runner = CliRunner()
        result = runner.invoke(wchanger.cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--online", result.output)
        self.assertIn("wallhaven", result.output)
        self.assertIn("bing", result.output)
        self.assertIn("picsum", result.output)
        self.assertIn("loremflickr", result.output)

    @patch("wchanger.run_online_wallpaper_cycle")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_cli_online_dispatch(
        self, mock_which: MagicMock, mock_online_cycle: MagicMock
    ) -> None:
        """cli with --online should dispatch directly to run_online_wallpaper_cycle."""
        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--online", "wallhaven", "--gnome", "-p", "10", "--no-repetition"],
        )
        self.assertEqual(result.exit_code, 0)
        mock_online_cycle.assert_called_once()
        self.assertEqual(mock_online_cycle.call_args.kwargs["provider"], "wallhaven")
        self.assertEqual(mock_online_cycle.call_args.kwargs["desktop_environment"], "gnome")
        self.assertFalse(mock_online_cycle.call_args.kwargs["repetition"])

    @patch("os.fork", return_value=54321)
    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    def test_cli_online_background(
        self, mock_qdbus: MagicMock, mock_fork: MagicMock
    ) -> None:
        """cli with --online and -b should fork and report background startup."""
        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--online", "picsum", "--kde", "-b", "-p", "30"],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Anahita Wallpaper Changer started in background (PID: 54321)", result.output)
        self.assertIn("Source: online (picsum)", result.output)

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_online_provider(
        self,
        mock_run: MagicMock,
        mock_prompt: MagicMock,
        mock_which: MagicMock,
    ) -> None:
        """setup_auto_start with online_provider should configure --online in service definition."""
        mock_prompt.return_value = 60
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start(desktop_override="gnome", online_provider="bing")
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--online bing", written_service_content)
        self.assertIn("--gnome", written_service_content)


    # Duration Parsing Tests
    def test_parse_duration_plain_numbers(self) -> None:
        """parse_duration_to_seconds should parse integer numbers and numeric strings."""
        self.assertEqual(wchanger.parse_duration_to_seconds(60), 60)
        self.assertEqual(wchanger.parse_duration_to_seconds(1), 1)
        self.assertEqual(wchanger.parse_duration_to_seconds("60"), 60)
        self.assertEqual(wchanger.parse_duration_to_seconds("300"), 300)

    def test_parse_duration_units(self) -> None:
        """parse_duration_to_seconds should parse s, m, h, d units correctly."""
        self.assertEqual(wchanger.parse_duration_to_seconds("45s"), 45)
        self.assertEqual(wchanger.parse_duration_to_seconds("30sec"), 30)
        self.assertEqual(wchanger.parse_duration_to_seconds("10m"), 600)
        self.assertEqual(wchanger.parse_duration_to_seconds("5min"), 300)
        self.assertEqual(wchanger.parse_duration_to_seconds("1h"), 3600)
        self.assertEqual(wchanger.parse_duration_to_seconds("2hr"), 7200)
        self.assertEqual(wchanger.parse_duration_to_seconds("1d"), 86400)

    def test_parse_duration_decimals_and_composites(self) -> None:
        """parse_duration_to_seconds should parse decimal and compound duration strings."""
        self.assertEqual(wchanger.parse_duration_to_seconds("1.5m"), 90)
        self.assertEqual(wchanger.parse_duration_to_seconds("0.5h"), 1800)
        self.assertEqual(wchanger.parse_duration_to_seconds("1h30m"), 5400)
        self.assertEqual(wchanger.parse_duration_to_seconds("10m 30s"), 630)

    def test_parse_duration_errors(self) -> None:
        """parse_duration_to_seconds should raise ValueError on zero, negative, or invalid formats."""
        with self.assertRaises(ValueError):
            wchanger.parse_duration_to_seconds(0)
        with self.assertRaises(ValueError):
            wchanger.parse_duration_to_seconds("0s")
        with self.assertRaises(ValueError):
            wchanger.parse_duration_to_seconds("-5")
        with self.assertRaises(ValueError):
            wchanger.parse_duration_to_seconds("")
        with self.assertRaises(ValueError):
            wchanger.parse_duration_to_seconds("hello")
        with self.assertRaises(ValueError):
            wchanger.parse_duration_to_seconds("10xyz")

    def test_duration_param_type_convert(self) -> None:
        """DURATION_TYPE convert should transform valid strings and reject invalid ones."""
        self.assertEqual(wchanger.DURATION_TYPE.convert("10m", None, None), 600)
        self.assertEqual(wchanger.DURATION_TYPE.convert(60, None, None), 60)
        self.assertIsNone(wchanger.DURATION_TYPE.convert(None, None, None))

    # Recursive Directory Scanning Tests
    def test_file_validator_recursive(self) -> None:
        """file_validator should only find subfolder images when recursive=True."""
        top_level_image = self.test_dir / "top.png"
        Image.new("RGB", (10, 10)).save(top_level_image)

        subdirectory = self.test_dir / "nested" / "sub"
        subdirectory.mkdir(parents=True)
        nested_image = subdirectory / "nested.jpg"
        Image.new("RGB", (10, 10)).save(nested_image)

        non_recursive_results = wchanger.file_validator(self.test_dir, recursive=False)
        self.assertEqual(len(non_recursive_results), 1)
        self.assertEqual(non_recursive_results[0], str(top_level_image.resolve()))

        recursive_results = wchanger.file_validator(self.test_dir, recursive=True)
        self.assertEqual(len(recursive_results), 2)
        self.assertIn(str(top_level_image.resolve()), recursive_results)
        self.assertIn(str(nested_image.resolve()), recursive_results)

    # Shuffle Tests
    @patch("random.shuffle")
    @patch("wchanger.set_wallpaper_for_desktop", return_value=(True, "ok"))
    def test_run_wallpaper_cycle_shuffle_enabled(
        self, mock_setter: MagicMock, mock_shuffle: MagicMock
    ) -> None:
        """run_wallpaper_cycle should call random.shuffle when shuffle=True."""
        image_path = self.test_dir / "img1.png"
        Image.new("RGB", (5, 5)).save(image_path)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.run_wallpaper_cycle(
                desktop_environment="gnome",
                wallpapers=[str(image_path)],
                pause_seconds=1,
                repetition=False,
                output_mode="console",
                shuffle=True,
            )
        self.assertEqual(exception_context.exception.code, 0)
        mock_shuffle.assert_called_once()

    @patch("random.shuffle")
    @patch("wchanger.set_wallpaper_for_desktop", return_value=(True, "ok"))
    def test_run_wallpaper_cycle_shuffle_disabled(
        self, mock_setter: MagicMock, mock_shuffle: MagicMock
    ) -> None:
        """run_wallpaper_cycle should not call random.shuffle when shuffle=False."""
        image_path = self.test_dir / "img1.png"
        Image.new("RGB", (5, 5)).save(image_path)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.run_wallpaper_cycle(
                desktop_environment="gnome",
                wallpapers=[str(image_path)],
                pause_seconds=1,
                repetition=False,
                output_mode="console",
                shuffle=False,
            )
        self.assertEqual(exception_context.exception.code, 0)
        mock_shuffle.assert_not_called()

    # CLI Tests for Shuffle, Time Units, and Recursive
    @patch("wchanger.run_wallpaper_cycle")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_cli_pause_with_time_units(
        self, mock_which: MagicMock, mock_cycle: MagicMock
    ) -> None:
        """cli with --pause 10m should pass pause_seconds=600 to run_wallpaper_cycle."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--gnome", "-p", "10m", str(self.test_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        mock_cycle.assert_called_once()
        self.assertEqual(mock_cycle.call_args.kwargs["pause_seconds"], 600)

    @patch("wchanger.run_wallpaper_cycle")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_cli_shuffle_flags(
        self, mock_which: MagicMock, mock_cycle: MagicMock
    ) -> None:
        """cli with --shuffle and -s should activate shuffle mode."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--gnome", "-p", "10", "--shuffle", str(self.test_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(mock_cycle.call_args.kwargs["shuffle"])

        mock_cycle.reset_mock()
        result_short = runner.invoke(
            wchanger.cli,
            ["--gnome", "-p", "10", "-s", str(self.test_dir)],
        )
        self.assertEqual(result_short.exit_code, 0)
        self.assertTrue(mock_cycle.call_args.kwargs["shuffle"])

    @patch("wchanger.run_wallpaper_cycle")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_cli_recursive_flags(
        self, mock_which: MagicMock, mock_cycle: MagicMock
    ) -> None:
        """cli with --recursive and -R should find nested subfolder wallpapers."""
        subfolder = self.test_dir / "nested"
        subfolder.mkdir()
        subfolder_image = subfolder / "nested.png"
        Image.new("RGB", (5, 5)).save(subfolder_image)

        runner = CliRunner()
        result_fail = runner.invoke(
            wchanger.cli,
            ["--gnome", "-p", "10", str(self.test_dir)],
        )
        self.assertNotEqual(result_fail.exit_code, 0)

        result_success = runner.invoke(
            wchanger.cli,
            ["--gnome", "-p", "10", "--recursive", str(self.test_dir)],
        )
        self.assertEqual(result_success.exit_code, 0)
        mock_cycle.assert_called_once()
        self.assertIn(str(subfolder_image.resolve()), mock_cycle.call_args.kwargs["wallpapers"])

        mock_cycle.reset_mock()
        result_short = runner.invoke(
            wchanger.cli,
            ["--gnome", "-p", "10", "-R", str(self.test_dir)],
        )
        self.assertEqual(result_short.exit_code, 0)
        mock_cycle.assert_called_once()
        self.assertIn(str(subfolder_image.resolve()), mock_cycle.call_args.kwargs["wallpapers"])

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_shuffle_and_recursive(
        self,
        mock_run: MagicMock,
        mock_prompt: MagicMock,
        mock_which: MagicMock,
    ) -> None:
        """setup_auto_start should include -s and -R when shuffle and recursive are specified."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        mock_prompt.side_effect = [120, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_auto_start(
                desktop_override="gnome",
                shuffle=True,
                recursive=True,
            )
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("-s", written_service_content)
        self.assertIn("-R", written_service_content)

    def test_load_config_file_nonexistent(self) -> None:
        """load_config_file should return empty dict when file does not exist."""
        result = wchanger.load_config_file(self.test_dir / "does_not_exist.toml")
        self.assertEqual(result, {})

    def test_load_config_file_valid_flat(self) -> None:
        """load_config_file should parse valid TOML settings at top level."""
        config_file = self.test_dir / "test_config.toml"
        config_file.write_text(
            'folder = "/tmp/wallpapers"\n'
            'desktop = "kde"\n'
            'pause = 300\n'
            'repetition = false\n'
            'theme = "dark"\n'
            'output = "log"\n'
            'shuffle = true\n'
            'recursive = true\n'
            'source = "wallhaven"\n'
            'keep_last = 15\n'
            'run_background = true\n'
        )
        settings = wchanger.load_config_file(config_file)
        self.assertEqual(settings["folder"], "/tmp/wallpapers")
        self.assertEqual(settings["desktop"], "kde")
        self.assertEqual(settings["pause"], 300)
        self.assertFalse(settings["repetition"])
        self.assertEqual(settings["theme"], "dark")
        self.assertEqual(settings["output"], "log")
        self.assertTrue(settings["shuffle"])
        self.assertTrue(settings["recursive"])
        self.assertEqual(settings["source"], "wallhaven")
        self.assertEqual(settings["keep_last"], 15)
        self.assertTrue(settings["run_background"])

    def test_load_config_file_table_sections(self) -> None:
        """load_config_file should parse settings nested inside [settings] or [wchanger]."""
        config_file = self.test_dir / "test_sections.toml"
        config_file.write_text(
            '[settings]\n'
            'pause = "10m"\n'
            'desktop = "mate"\n'
            '[wchanger]\n'
            'source = "bing"\n'
            'keep_last = 25\n'
        )
        settings = wchanger.load_config_file(config_file)
        self.assertEqual(settings["pause"], "10m")
        self.assertEqual(settings["desktop"], "mate")
        self.assertEqual(settings["source"], "bing")
        self.assertEqual(settings["keep_last"], 25)

    def test_load_config_file_syntax_error(self) -> None:
        """load_config_file should handle corrupt TOML files gracefully without crashing."""
        config_file = self.test_dir / "corrupted.toml"
        config_file.write_text('bad_syntax = [ "unclosed array\n')
        settings = wchanger.load_config_file(config_file)
        self.assertEqual(settings, {})

    @patch.dict(os.environ, {"WCHANGER_NO_CONFIG": "1"})
    def test_load_config_file_env_bypass(self) -> None:
        """load_config_file should return empty dict when WCHANGER_NO_CONFIG is set."""
        config_file = self.test_dir / "test_config.toml"
        config_file.write_text('pause = 120\n')
        settings = wchanger.load_config_file(config_file)
        self.assertEqual(settings, {})

    def test_cleanup_download_cache_empty_or_missing(self) -> None:
        """cleanup_download_cache should handle non-existent or empty directories safely."""
        missing_directory = self.test_dir / "missing_cache"
        self.assertEqual(wchanger.cleanup_download_cache(missing_directory), [])

        empty_directory = self.test_dir / "empty_cache"
        empty_directory.mkdir()
        self.assertEqual(wchanger.cleanup_download_cache(empty_directory), [])

    def test_cleanup_download_cache_prunes_old_files(self) -> None:
        """cleanup_download_cache should delete the oldest files when count exceeds keep_last."""
        cache_dir = self.test_dir / "cache"
        cache_dir.mkdir()

        created_paths = []
        base_time = 1700000000.0
        for index in range(25):
            image_path = cache_dir / f"wallpaper_test_{index:02d}.jpg"
            image_path.write_bytes(b"dummy image data")
            timestamp = base_time + (index * 10)
            os.utime(image_path, (timestamp, timestamp))
            created_paths.append(image_path)

        pruned = wchanger.cleanup_download_cache(cache_dir, keep_last=20)
        self.assertEqual(len(pruned), 5)
        expected_pruned_names = {f"wallpaper_test_{wallpaper_index:02d}.jpg" for wallpaper_index in range(5)}
        actual_pruned_names = {candidate_wallpaper_path.name for candidate_wallpaper_path in pruned}
        self.assertEqual(actual_pruned_names, expected_pruned_names)

        remaining_files = [candidate_wallpaper_path.name for candidate_wallpaper_path in cache_dir.iterdir() if candidate_wallpaper_path.is_file()]
        self.assertEqual(len(remaining_files), 20)
        for wallpaper_index in range(5, 25):
            self.assertIn(f"wallpaper_test_{wallpaper_index:02d}.jpg", remaining_files)

    def test_cleanup_download_cache_custom_keep_last(self) -> None:
        """cleanup_download_cache should respect custom keep_last values."""
        cache_dir = self.test_dir / "cache_small"
        cache_dir.mkdir()

        base_time = 1700000000.0
        for index in range(10):
            image_path = cache_dir / f"wall_{index}.png"
            image_path.write_bytes(b"data")
            os.utime(image_path, (base_time + index, base_time + index))

        pruned = wchanger.cleanup_download_cache(cache_dir, keep_last=3)
        self.assertEqual(len(pruned), 7)
        remaining = list(cache_dir.iterdir())
        self.assertEqual(len(remaining), 3)

    def test_cleanup_download_cache_ignores_non_images(self) -> None:
        """cleanup_download_cache should not count or delete non-image files."""
        cache_dir = self.test_dir / "cache_mixed"
        cache_dir.mkdir()

        text_file = cache_dir / "notes.txt"
        text_file.write_text("keep me")

        base_time = 1700000000.0
        for index in range(5):
            image_path = cache_dir / f"wall_{index}.jpg"
            image_path.write_bytes(b"data")
            os.utime(image_path, (base_time + index, base_time + index))

        pruned = wchanger.cleanup_download_cache(cache_dir, keep_last=3)
        self.assertEqual(len(pruned), 2)
        self.assertTrue(text_file.exists())

    @patch("wchanger.run_wallpaper_cycle")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_cli_config_custom_file_and_pause(
        self, mock_which: MagicMock, mock_cycle: MagicMock
    ) -> None:
        """cli should load options from custom --config file."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        custom_config_file = self.test_dir / "my_custom.toml"
        custom_config_file.write_text(
            f'pause = "5m"\n'
            f'shuffle = true\n'
            f'folder = "{self.test_dir}"\n'
            f'source = "folder"\n'
        )

        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--config", str(custom_config_file), "--gnome"],
        )
        self.assertEqual(result.exit_code, 0)
        mock_cycle.assert_called_once()
        self.assertEqual(mock_cycle.call_args.kwargs["pause_seconds"], 300)
        self.assertTrue(mock_cycle.call_args.kwargs["shuffle"])

    @patch("wchanger.run_wallpaper_cycle")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_cli_override_config_pause(
        self, mock_which: MagicMock, mock_cycle: MagicMock
    ) -> None:
        """CLI arguments should override values specified in config file."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        custom_config_file = self.test_dir / "override.toml"
        custom_config_file.write_text(
            f'pause = 600\n'
            f'shuffle = true\n'
            f'folder = "{self.test_dir}"\n'
        )

        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--config", str(custom_config_file), "--gnome", "-p", "15", "--no-shuffle"],
        )
        self.assertEqual(result.exit_code, 0)
        mock_cycle.assert_called_once()
        self.assertEqual(mock_cycle.call_args.kwargs["pause_seconds"], 15)
        self.assertFalse(mock_cycle.call_args.kwargs["shuffle"])

    @patch("wchanger.run_wallpaper_cycle")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_cli_no_config_flag(
        self, mock_which: MagicMock, mock_cycle: MagicMock
    ) -> None:
        """--no-config should ignore any configuration file."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        custom_config_file = self.test_dir / "ignored.toml"
        custom_config_file.write_text('shuffle = true\n')

        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--config", str(custom_config_file), "--no-config", "--gnome", "-p", "10", str(self.test_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        mock_cycle.assert_called_once()
        self.assertFalse(mock_cycle.call_args.kwargs["shuffle"])

    @patch("wchanger.run_online_wallpaper_cycle")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_cli_config_source_online(
        self, mock_which: MagicMock, mock_online: MagicMock
    ) -> None:
        """config with source = 'bing' should dispatch to online cycle when no folder is passed."""
        custom_config_file = self.test_dir / "online_cfg.toml"
        custom_config_file.write_text(
            'source = "bing"\n'
            'pause = 120\n'
            'keep_last = 10\n'
            'repetition = false\n'
        )

        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--config", str(custom_config_file), "--gnome"],
        )
        self.assertEqual(result.exit_code, 0)
        mock_online.assert_called_once()
        self.assertEqual(mock_online.call_args.kwargs["provider"], "bing")
        self.assertEqual(mock_online.call_args.kwargs["pause_seconds"], 120)
        self.assertEqual(mock_online.call_args.kwargs["keep_last"], 10)

    @patch("wchanger.run_wallpaper_cycle")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_cli_photo_path_overrides_config_source(
        self, mock_which: MagicMock, mock_cycle: MagicMock
    ) -> None:
        """Passing an explicit folder on CLI should override source = 'wallhaven' in config."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        custom_config_file = self.test_dir / "source_override.toml"
        custom_config_file.write_text('source = "wallhaven"\n')

        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--config", str(custom_config_file), "--gnome", "-p", "10", str(self.test_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        mock_cycle.assert_called_once()

    @patch("wchanger.run_online_wallpaper_cycle")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_cli_source_flag_online(
        self, mock_which: MagicMock, mock_online: MagicMock
    ) -> None:
        """--source picsum should dispatch to online cycle with picsum."""
        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--source", "picsum", "--gnome", "-p", "10", "--no-repetition"],
        )
        self.assertEqual(result.exit_code, 0)
        mock_online.assert_called_once()
        self.assertEqual(mock_online.call_args.kwargs["provider"], "picsum")

    @patch("wchanger.run_wallpaper_cycle")
    @patch("shutil.which", return_value="/usr/bin/gsettings")
    def test_cli_source_flag_folder(
        self, mock_which: MagicMock, mock_cycle: MagicMock
    ) -> None:
        """--source folder should force local folder mode even if config specifies online."""
        image_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(image_path)

        custom_config_file = self.test_dir / "force_folder.toml"
        custom_config_file.write_text(f'source = "wallhaven"\nfolder = "{self.test_dir}"\n')

        runner = CliRunner()
        result = runner.invoke(
            wchanger.cli,
            ["--config", str(custom_config_file), "--source", "folder", "--gnome", "-p", "10"],
        )
        self.assertEqual(result.exit_code, 0)
        mock_cycle.assert_called_once()

    @patch("wchanger.setup_install_autostart_service")
    def test_cli_install_autostart_flag(self, mock_wizard: MagicMock) -> None:
        """--install-autostart should trigger the setup_install_autostart_service wizard."""
        runner = CliRunner()
        result = runner.invoke(wchanger.cli, ["--install-autostart"])
        self.assertEqual(result.exit_code, 0)
        mock_wizard.assert_called_once()

    @patch("wchanger.setup_install_autostart_service")
    def test_cli_auto_start_alias_flag(self, mock_wizard: MagicMock) -> None:
        """--auto-start alias should trigger setup_install_autostart_service wizard."""
        runner = CliRunner()
        result = runner.invoke(wchanger.cli, ["--auto-start"])
        self.assertEqual(result.exit_code, 0)
        mock_wizard.assert_called_once()

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_install_autostart_keep_last(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_install_autostart should forward --keep-last into systemd ExecStart when online."""
        mock_prompt.return_value = 60
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_install_autostart_service(
                desktop_override="gnome",
                online_provider="wallhaven",
                keep_last=12,
            )
        self.assertEqual(exception_context.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--online wallhaven", written_service_content)
        self.assertIn("--keep-last 12", written_service_content)

    @patch("wchanger.cleanup_download_cache")
    @patch("wchanger.set_wallpaper_for_desktop", return_value=(True, "Success"))
    @patch("wchanger.download_online_wallpaper")
    @patch("wchanger.fetch_picsum_url", return_value="https://picsum.photos/1920/1080?random=123")
    def test_run_online_wallpaper_cycle_calls_cleanup(
        self,
        mock_fetch: MagicMock,
        mock_download: MagicMock,
        mock_set: MagicMock,
        mock_cleanup: MagicMock,
    ) -> None:
        """run_online_wallpaper_cycle should invoke cleanup_download_cache after setting wallpaper."""
        with self.assertRaises(SystemExit) as exception_context:
            wchanger.run_online_wallpaper_cycle(
                desktop_environment="gnome",
                provider="picsum",
                pause_seconds=1,
                repetition=False,
                output_mode="console",
                cache_dir=self.test_dir,
                keep_last=15,
            )
        self.assertEqual(exception_context.exception.code, 0)
        mock_cleanup.assert_called_once_with(self.test_dir, keep_last=15)

    def test_main_callable_entry_point(self) -> None:
        """wchanger.main must be a callable alias of wchanger.cli."""
        self.assertTrue(callable(wchanger.main))
        self.assertIs(wchanger.main, wchanger.cli)

    def test_cli_multi_monitor_flags(self) -> None:
        """CLI should recognize --multi-monitor, -m, and --single-monitor flags."""
        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle") as mock_cycle, \
             patch("wchanger.file_validator", return_value=["/path/to/pic1.jpg", "/path/to/pic2.jpg"]):
            result = runner.invoke(wchanger.cli, ["-m", "--gnome", str(self.test_dir)])
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(mock_cycle.call_args.kwargs.get("multi_monitor"))

            mock_cycle.reset_mock()
            result = runner.invoke(wchanger.cli, ["--multi-monitor", "--gnome", str(self.test_dir)])
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(mock_cycle.call_args.kwargs.get("multi_monitor"))

            mock_cycle.reset_mock()
            result = runner.invoke(wchanger.cli, ["--single-monitor", "--gnome", str(self.test_dir)])
            self.assertEqual(result.exit_code, 0)
            self.assertFalse(mock_cycle.call_args.kwargs.get("multi_monitor"))

    def test_load_config_file_multi_monitor(self) -> None:
        """load_config_file should parse multi_monitor boolean properly."""
        config_file = self.test_dir / "config.toml"
        config_file.write_text("multi_monitor = true\n")
        settings = wchanger.load_config_file(config_file)
        self.assertTrue(settings.get("multi_monitor"))

        config_file.write_text("multi_monitor = false\n")
        settings = wchanger.load_config_file(config_file)
        self.assertFalse(settings.get("multi_monitor"))

    def test_cli_reads_multi_monitor_from_config(self) -> None:
        """CLI should read multi_monitor from config file if not overridden on command line."""
        config_file = self.test_dir / "config.toml"
        config_file.write_text("multi_monitor = true\n")
        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle") as mock_cycle, \
             patch("wchanger.file_validator", return_value=["/path/to/pic1.jpg", "/path/to/pic2.jpg"]):
            result = runner.invoke(wchanger.cli, ["-c", str(config_file), "--gnome", str(self.test_dir)])
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(mock_cycle.call_args.kwargs.get("multi_monitor"))

    @patch("shutil.which", return_value="/usr/bin/xrandr")
    @patch("subprocess.run")
    def test_get_xrandr_monitors_success(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        """get_xrandr_monitors should parse monitor geometries and sort by x coordinate."""
        output = (
            "Monitors: 2\n"
            " 0: +*DP-1 2560/597x1440/336+0+0  DP-1\n"
            " 1: +HDMI-1 1920/531x1080/299+2560+0  HDMI-1\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=output)
        monitors = wchanger.get_xrandr_monitors()
        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[0], {"width": 2560, "height": 1440, "x": 0, "y": 0})
        self.assertEqual(monitors[1], {"width": 1920, "height": 1080, "x": 2560, "y": 0})

    @patch("shutil.which", return_value=None)
    def test_get_xrandr_monitors_not_installed(self, mock_which: MagicMock) -> None:
        """get_xrandr_monitors should return empty list if xrandr is missing."""
        self.assertEqual(wchanger.get_xrandr_monitors(), [])

    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    @patch("subprocess.run")
    def test_get_kde_desktop_count(self, mock_run: MagicMock, mock_qdbus: MagicMock) -> None:
        """get_kde_desktop_count should return integer count from evaluateScript."""
        mock_run.return_value = MagicMock(returncode=0, stdout="3\n")
        count = wchanger.get_kde_desktop_count()
        self.assertEqual(count, 3)

    @patch("subprocess.run")
    def test_get_xfce_monitor_properties_groups(self, mock_run: MagicMock) -> None:
        """get_xfce_monitor_properties should group last-image properties by monitor."""
        output = (
            "/backdrop/screen0/monitor0/workspace0/last-image\n"
            "/backdrop/screen0/monitor0/workspace1/last-image\n"
            "/backdrop/screen0/monitor1/workspace0/last-image\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=output)
        groups = wchanger.get_xfce_monitor_properties()
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(groups["screen0/monitor0"]), 2)
        self.assertEqual(len(groups["screen0/monitor1"]), 1)

    @patch("wchanger.get_xrandr_monitors", return_value=[{"width": 1920, "height": 1080, "x": 0, "y": 0}, {"width": 1920, "height": 1080, "x": 1920, "y": 0}])
    def test_detect_connected_monitors_xrandr(self, mock_xrandr: MagicMock) -> None:
        """detect_connected_monitors should return monitor count from xrandr."""
        self.assertEqual(wchanger.detect_connected_monitors(), 2)

    @patch("wchanger.detect_connected_monitors", return_value=1)
    def test_get_effective_monitor_count_guarantees_two(self, mock_detect: MagicMock) -> None:
        """get_effective_monitor_count with multi_monitor=True should guarantee at least 2."""
        self.assertEqual(wchanger.get_effective_monitor_count(multi_monitor=True), 2)
        self.assertEqual(wchanger.get_effective_monitor_count(multi_monitor=False), 1)

    @patch("wchanger.detect_connected_monitors", return_value=3)
    def test_get_effective_monitor_count_three_monitors(self, mock_detect: MagicMock) -> None:
        """get_effective_monitor_count with multi_monitor=True should return 3 if 3 detected."""
        self.assertEqual(wchanger.get_effective_monitor_count(multi_monitor=True), 3)

    def test_create_spanned_wallpaper_stitches_images(self) -> None:
        """create_spanned_wallpaper should horizontally stitch images into a single file."""
        img1 = self.test_dir / "left.png"
        img2 = self.test_dir / "right.png"
        Image.new("RGB", (100, 80), color="red").save(img1)
        Image.new("RGB", (120, 80), color="blue").save(img2)

        out_path = self.test_dir / "spanned.png"
        result = wchanger.create_spanned_wallpaper([img1, img2], output_path=out_path)
        self.assertEqual(result, out_path)
        self.assertTrue(out_path.exists())

        with Image.open(out_path) as combined:
            self.assertEqual(combined.size, (220, 80))

    def test_create_spanned_wallpaper_single_image(self) -> None:
        """create_spanned_wallpaper with single image should return it without stitching."""
        img1 = self.test_dir / "single.png"
        Image.new("RGB", (50, 50)).save(img1)
        result = wchanger.create_spanned_wallpaper([img1])
        self.assertEqual(result, img1)

    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    @patch("subprocess.run")
    def test_set_kde_background_multi_monitor(self, mock_run: MagicMock, mock_qdbus: MagicMock) -> None:
        """set_kde_background with multiple wallpapers should assign different wallpapers in loop."""
        mock_run.return_value = MagicMock(returncode=0)
        wallpapers = ["file:///home/user/wall1.jpg", "file:///home/user/wall2.jpg"]
        success = wchanger.set_kde_background(wallpapers)
        self.assertTrue(success)
        mock_run.assert_called_once()
        js_script = mock_run.call_args[0][0][4]
        self.assertIn('wallpaperList = ["file:///home/user/wall1.jpg", "file:///home/user/wall2.jpg"]', js_script)
        self.assertIn('desktop.writeConfig("Image", imageUri);', js_script)

    @patch("subprocess.run")
    def test_set_xfce_background_multi_monitor(self, mock_run: MagicMock) -> None:
        """set_xfce_background with multiple wallpapers should set distinct wallpaper per monitor."""
        list_output = (
            "/backdrop/screen0/monitor0/workspace0/last-image\n"
            "/backdrop/screen0/monitor1/workspace0/last-image\n"
        )
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=list_output),
            MagicMock(returncode=0),
            MagicMock(returncode=0),
        ]
        wallpapers = ["/home/user/wall1.png", "/home/user/wall2.png"]
        success = wchanger.set_xfce_background(wallpapers)
        self.assertTrue(success)

        set1_args = mock_run.call_args_list[1][0][0]
        set2_args = mock_run.call_args_list[2][0][0]
        self.assertEqual(set1_args, ["xfconf-query", "-c", "xfce4-desktop", "-p", "/backdrop/screen0/monitor0/workspace0/last-image", "-s", "/home/user/wall1.png"])
        self.assertEqual(set2_args, ["xfconf-query", "-c", "xfce4-desktop", "-p", "/backdrop/screen0/monitor1/workspace0/last-image", "-s", "/home/user/wall2.png"])

    @patch("subprocess.run")
    @patch("wchanger.create_spanned_wallpaper")
    def test_set_gnome_background_multi_monitor(self, mock_span: MagicMock, mock_run: MagicMock) -> None:
        """set_gnome_background with multiple wallpapers should span stitched wallpaper."""
        mock_run.return_value = MagicMock(returncode=0)
        spanned_file = self.test_dir / "spanned.png"
        spanned_file.write_bytes(b"data")
        mock_span.return_value = spanned_file

        success = wchanger.set_gnome_background(["/wall1.jpg", "/wall2.jpg"])
        self.assertTrue(success)
        mock_span.assert_called_once()
        spanned_option_call = mock_run.call_args_list[0][0][0]
        self.assertEqual(spanned_option_call, ["gsettings", "set", "org.gnome.desktop.background", "picture-options", "spanned"])

    @patch("subprocess.run")
    @patch("wchanger.create_spanned_wallpaper")
    def test_set_cinnamon_background_multi_monitor(self, mock_span: MagicMock, mock_run: MagicMock) -> None:
        """set_cinnamon_background with multiple wallpapers should set picture-options to spanned."""
        mock_run.return_value = MagicMock(returncode=0)
        spanned_file = self.test_dir / "spanned.png"
        spanned_file.write_bytes(b"data")
        mock_span.return_value = spanned_file

        success = wchanger.set_cinnamon_background(["/wall1.jpg", "/wall2.jpg"])
        self.assertTrue(success)
        mock_span.assert_called_once()
        spanned_option_call = mock_run.call_args_list[0][0][0]
        self.assertEqual(spanned_option_call, ["gsettings", "set", "org.cinnamon.desktop.background", "picture-options", "spanned"])

    @patch("subprocess.run")
    @patch("wchanger.create_spanned_wallpaper")
    def test_set_mate_background_multi_monitor(self, mock_span: MagicMock, mock_run: MagicMock) -> None:
        """set_mate_background with multiple wallpapers should set picture-options to spanned."""
        mock_run.return_value = MagicMock(returncode=0)
        spanned_file = self.test_dir / "spanned.png"
        spanned_file.write_bytes(b"data")
        mock_span.return_value = spanned_file

        success = wchanger.set_mate_background(["/wall1.jpg", "/wall2.jpg"])
        self.assertTrue(success)
        mock_span.assert_called_once()
        spanned_option_call = mock_run.call_args_list[0][0][0]
        self.assertEqual(spanned_option_call, ["gsettings", "set", "org.mate.background", "picture-options", "spanned"])

    @patch("subprocess.run")
    @patch("wchanger.set_lxqt_multimonitor_config", return_value=True)
    def test_set_lxqt_background_multi_monitor(self, mock_config: MagicMock, mock_run: MagicMock) -> None:
        """set_lxqt_background with multiple wallpapers should update config and reconfigure."""
        mock_run.return_value = MagicMock(returncode=0)
        success = wchanger.set_lxqt_background(["/wall1.jpg", "/wall2.jpg"])
        self.assertTrue(success)
        mock_config.assert_called_once()
        mock_run.assert_called_once_with(["pcmanfm-qt", "--reconfigure"], capture_output=True, text=True, check=False)

    @patch("wchanger.set_kde_background", return_value=True)
    def test_set_wallpaper_for_desktop_multi_monitor_message(self, mock_kde: MagicMock) -> None:
        """set_wallpaper_for_desktop should format multi-monitor message when sequence passed."""
        success, error_message = wchanger.set_wallpaper_for_desktop("kde", ["/wall1.jpg", "/wall2.jpg"])
        self.assertTrue(success)
        self.assertIn("across 2 monitors", error_message)
        mock_kde.assert_called_once_with(["/wall1.jpg", "/wall2.jpg"])

    @patch("wchanger.get_effective_monitor_count", return_value=2)
    @patch("wchanger.set_wallpaper_for_desktop", return_value=(True, "Wallpapers changed"))
    @patch("time.sleep")
    def test_run_wallpaper_cycle_multi_monitor(self, mock_sleep: MagicMock, mock_set: MagicMock, mock_count: MagicMock) -> None:
        """run_wallpaper_cycle with multi_monitor=True should batch wallpapers by monitor count."""
        wall1 = self.test_dir / "wall1.png"
        wall2 = self.test_dir / "wall2.png"
        wall1.write_bytes(b"data1")
        wall2.write_bytes(b"data2")

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.run_wallpaper_cycle(
                desktop_environment="kde",
                wallpapers=[str(wall1), str(wall2)],
                pause_seconds=5,
                repetition=False,
                output_mode="console",
                multi_monitor=True,
            )
        self.assertEqual(exception_context.exception.code, 0)
        mock_set.assert_called_once_with(
            desktop_environment="kde",
            wallpaper_path=[str(wall1), str(wall2)],
            color_theme=None,
        )

    @patch("wchanger.get_effective_monitor_count", return_value=2)
    @patch("wchanger.cleanup_download_cache")
    @patch("wchanger.download_online_wallpaper")
    @patch("wchanger.set_wallpaper_for_desktop", return_value=(True, "Success"))
    @patch("wchanger.fetch_picsum_url", return_value="https://picsum.photos/1920/1080?random=1")
    def test_run_online_wallpaper_cycle_multi_monitor(
        self,
        mock_fetch: MagicMock,
        mock_set: MagicMock,
        mock_download: MagicMock,
        mock_cleanup: MagicMock,
        mock_count: MagicMock,
    ) -> None:
        """run_online_wallpaper_cycle with multi_monitor=True should download for each monitor."""
        with self.assertRaises(SystemExit) as exception_context:
            wchanger.run_online_wallpaper_cycle(
                desktop_environment="gnome",
                provider="picsum",
                pause_seconds=1,
                repetition=False,
                output_mode="console",
                cache_dir=self.test_dir,
                multi_monitor=True,
            )
        self.assertEqual(exception_context.exception.code, 0)
        self.assertEqual(mock_download.call_count, 2)
        mock_set.assert_called_once()
        self.assertEqual(len(mock_set.call_args.kwargs["wallpaper_path"]), 2)

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_install_autostart_multi_monitor(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_install_autostart should include --multi-monitor in ExecStart when multi_monitor=True."""
        mock_prompt.return_value = 60
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as exception_context:
            wchanger.setup_install_autostart_service(
                desktop_override="kde",
                online_provider="wallhaven",
                multi_monitor=True,
            )
        self.assertEqual(exception_context.exception.code, 0)
        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--multi-monitor", written_service_content)

    def test_cli_single_monitor_overrides_config(self) -> None:
        """CLI --single-monitor should explicitly override multi_monitor=true in config.toml."""
        config_file = self.test_dir / "config.toml"
        config_file.write_text("multi_monitor = true\n")
        runner = CliRunner()
        with patch("wchanger.run_wallpaper_cycle") as mock_cycle, \
             patch("wchanger.file_validator", return_value=["/path/to/pic1.jpg", "/path/to/pic2.jpg"]):
            result = runner.invoke(wchanger.cli, ["-c", str(config_file), "--single-monitor", "--gnome", str(self.test_dir)])
            self.assertEqual(result.exit_code, 0)
            self.assertFalse(mock_cycle.call_args.kwargs.get("multi_monitor"))

    def test_create_spanned_wallpaper_without_pillow(self) -> None:
        """create_spanned_wallpaper without Pillow should fall back to first image."""
        with patch("wchanger.HAS_PILLOW", False):
            result = wchanger.create_spanned_wallpaper(["/img1.jpg", "/img2.jpg"])
            self.assertEqual(result, Path("/img1.jpg"))

    def test_create_spanned_wallpaper_empty_list_raises(self) -> None:
        """create_spanned_wallpaper with empty sequence should raise ValueError."""
        with self.assertRaises(ValueError):
            wchanger.create_spanned_wallpaper([])

    @patch("wchanger.get_xfce_monitor_properties", return_value={})
    @patch("wchanger.get_kde_desktop_count", return_value=0)
    @patch("wchanger.get_xrandr_monitors", return_value=[])
    @patch("pathlib.Path.glob", return_value=[])
    def test_detect_connected_monitors_fallback_one(
        self, mock_glob: MagicMock, mock_xrandr: MagicMock, mock_kde: MagicMock, mock_xfce: MagicMock
    ) -> None:
        """detect_connected_monitors should fall back to 1 when no monitors detected."""
        self.assertEqual(wchanger.detect_connected_monitors(), 1)

    def test_set_xfce_background_empty_wallpapers(self) -> None:
        """set_xfce_background with empty sequence should return False."""
        self.assertFalse(wchanger.set_xfce_background([]))

    @patch("wchanger.find_kde_qdbus_executable", return_value=None)
    def test_set_kde_background_no_qdbus(self, mock_qdbus: MagicMock) -> None:
        """set_kde_background should return False when qdbus executable cannot be found."""
        self.assertFalse(wchanger.set_kde_background(["/wall1.jpg", "/wall2.jpg"]))

    def test_create_spanned_wallpaper_alternates_filenames(self) -> None:
        """create_spanned_wallpaper should alternate filenames on successive calls without output_path."""
        img1 = self.test_dir / "left.png"
        img2 = self.test_dir / "right.png"
        Image.new("RGB", (100, 80), color="red").save(img1)
        Image.new("RGB", (100, 80), color="blue").save(img2)

        res1 = wchanger.create_spanned_wallpaper([img1, img2])
        res2 = wchanger.create_spanned_wallpaper([img1, img2])
        self.assertNotEqual(res1.name, res2.name)
        self.assertTrue(res1.name.startswith("multimonitor_spanned_"))
        self.assertTrue(res2.name.startswith("multimonitor_spanned_"))

    @patch("wchanger.get_xrandr_monitors")
    def test_create_spanned_wallpaper_aspect_ratio_fit(self, mock_monitors: MagicMock) -> None:
        """create_spanned_wallpaper should fit wallpapers to monitor resolution preserving aspect ratio."""
        mock_monitors.return_value = [
            {"width": 1920, "height": 1080, "x": 0, "y": 0},
            {"width": 1920, "height": 1080, "x": 1920, "y": 0},
        ]
        img1 = self.test_dir / "wide.png"
        img2 = self.test_dir / "tall.png"
        Image.new("RGB", (800, 600), color="red").save(img1)
        Image.new("RGB", (1920, 1080), color="blue").save(img2)

        out_path = self.test_dir / "aspect_fit.png"
        result = wchanger.create_spanned_wallpaper([img1, img2], output_path=out_path)
        self.assertEqual(result, out_path)
        with Image.open(out_path) as combined:
            self.assertEqual(combined.size, (3840, 1080))

    @patch("shutil.which", return_value="/usr/bin/xrandr")
    @patch("subprocess.run")
    def test_get_xrandr_monitors_vertical_stacked(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        """get_xrandr_monitors should sort vertically stacked monitors by (x, y)."""
        output = (
            "Monitors: 2\n"
            " 0: +*DP-1 1920/531x1080/299+0+1080  DP-1\n"
            " 1: +HDMI-1 1920/531x1080/299+0+0  HDMI-1\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=output)
        monitors = wchanger.get_xrandr_monitors()
        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[0]["y"], 0)
        self.assertEqual(monitors[1]["y"], 1080)

    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    @patch("subprocess.run")
    def test_set_kde_background_relative_path(self, mock_run: MagicMock, mock_qdbus: MagicMock) -> None:
        """set_kde_background should convert relative paths to file:// URIs."""
        mock_run.return_value = MagicMock(returncode=0)
        test_image = self.test_dir / "rel.png"
        Image.new("RGB", (10, 10)).save(test_image)

        # Single relative path
        wchanger.set_kde_background(str(test_image))
        js_single = mock_run.call_args[0][0][4]
        self.assertIn(Path(test_image).resolve().as_uri(), js_single)

        # Multi relative paths
        mock_run.reset_mock()
        wchanger.set_kde_background([str(test_image), str(test_image)])
        js_multi = mock_run.call_args[0][0][4]
        self.assertIn(Path(test_image).resolve().as_uri(), js_multi)

    @patch("subprocess.run")
    def test_set_xfce_background_fallback_all_fail(self, mock_run: MagicMock) -> None:
        """set_xfce_background should return False when all fallback properties fail."""
        # list process returns empty stdout, subsequent fallbacks return returncode 1
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=1),
            MagicMock(returncode=1),
            MagicMock(returncode=1),
        ]
        result = wchanger.set_xfce_background(["/wall1.jpg", "/wall2.jpg"])
        self.assertFalse(result)

    @patch("wchanger.setup_install_autostart_service")
    def test_cli_install_autostart_reads_multi_monitor_from_config(self, mock_wizard: MagicMock) -> None:
        """--install-autostart should pick up multi_monitor=true from config.toml."""
        config_file = self.test_dir / "config.toml"
        config_file.write_text("multi_monitor = true\n")
        runner = CliRunner()
        result = runner.invoke(wchanger.cli, ["-c", str(config_file), "--install-autostart"])
        self.assertEqual(result.exit_code, 0)
        mock_wizard.assert_called_once()
        self.assertTrue(mock_wizard.call_args.kwargs.get("multi_monitor"))

    @patch("wchanger.setup_install_autostart_service")
    def test_cli_install_autostart_reads_online_source_from_config(self, mock_wizard: MagicMock) -> None:
        """--install-autostart should pick up source='wallhaven' from config.toml."""
        config_file = self.test_dir / "config.toml"
        config_file.write_text('source = "wallhaven"\n')
        runner = CliRunner()
        result = runner.invoke(wchanger.cli, ["-c", str(config_file), "--install-autostart"])
        self.assertEqual(result.exit_code, 0)
        mock_wizard.assert_called_once()
        self.assertEqual(mock_wizard.call_args.kwargs.get("online_provider"), "wallhaven")

    def test_set_lxqt_multimonitor_config_supports_desktop_alias(self) -> None:
        """set_lxqt_multimonitor_config should update existing [Desktop] section for screen 0."""
        configuration_file = self.test_dir / "settings.conf"
        configuration_file.write_text("[Desktop]\nWallpaper=/old_primary.png\n\n[General]\nVersion=1\n")

        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.test_dir)}):
            # create nested directory expected by function
            lxqt_config_dir = self.test_dir / "pcmanfm-qt" / "lxqt"
            lxqt_config_dir.mkdir(parents=True, exist_ok=True)
            target_config_file = lxqt_config_dir / "settings.conf"
            target_config_file.write_text("[Desktop]\nWallpaper=/old_primary.png\n\n[General]\nVersion=1\n")

            success = wchanger.set_lxqt_multimonitor_config(["/new0.png", "/new1.png"])
            self.assertTrue(success)
            content = target_config_file.read_text()
            self.assertIn("Wallpaper=/new0.png", content)
            self.assertIn("[Desktop_Screen_1]", content)
            self.assertIn("Wallpaper=/new1.png", content)

    @patch("shutil.which", return_value=None)
    def test_get_wayland_monitors_not_installed(self, mock_which: MagicMock) -> None:
        """get_wayland_monitors should return empty list when no tool is installed."""
        self.assertEqual(wchanger.get_wayland_monitors(), [])

    @patch("shutil.which", return_value="/usr/bin/wlr-randr")
    @patch("subprocess.run")
    def test_get_wayland_monitors_success_position_before_modes(
        self, mock_run: MagicMock, mock_which: MagicMock
    ) -> None:
        """get_wayland_monitors should parse wlr-randr when position precedes mode list."""
        sample_wlr_output = (
            "DP-1 \"DisplayPort-1\"\n"
            "  Position: 1920, 0\n"
            "  Modes:\n"
            "    1920x1080 px, 60.000000 Hz (current)\n"
            "HDMI-A-1 \"HDMI-1\"\n"
            "  Position: 0, 0\n"
            "  Modes:\n"
            "    2560x1440 px, 144.000000 Hz (current)\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=sample_wlr_output)
        detected_monitors = wchanger.get_wayland_monitors()
        self.assertEqual(len(detected_monitors), 2)
        self.assertEqual(detected_monitors[0]["x"], 0)
        self.assertEqual(detected_monitors[0]["width"], 2560)
        self.assertEqual(detected_monitors[0]["height"], 1440)
        self.assertEqual(detected_monitors[1]["x"], 1920)
        self.assertEqual(detected_monitors[1]["width"], 1920)

    @patch("shutil.which", return_value="/usr/bin/wlr-randr")
    @patch("subprocess.run")
    def test_get_wayland_monitors_success_position_after_modes_and_filters_disabled(
        self, mock_run: MagicMock, mock_which: MagicMock
    ) -> None:
        """get_wayland_monitors should parse real wlr-randr output and filter disabled heads."""
        sample_wlr_output = (
            "DP-1 \"DisplayPort-1\"\n"
            "  Enabled: yes\n"
            "  Modes:\n"
            "    1920x1080 px, 60.000000 Hz (current)\n"
            "  Position: 1920, 0\n"
            "HDMI-A-1 \"HDMI-1\"\n"
            "  Enabled: yes\n"
            "  Modes:\n"
            "    2560x1440 px, 144.000000 Hz (current)\n"
            "  Position: 0, 0\n"
            "DP-2 \"DisplayPort-2\"\n"
            "  Enabled: no\n"
            "  Modes:\n"
            "    1920x1080 px, 60.000000 Hz (current)\n"
            "  Position: 3840, 0\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=sample_wlr_output)
        detected_monitors = wchanger.get_wayland_monitors()
        self.assertEqual(len(detected_monitors), 2)
        self.assertEqual(detected_monitors[0]["x"], 0)
        self.assertEqual(detected_monitors[0]["width"], 2560)
        self.assertEqual(detected_monitors[0]["height"], 1440)
        self.assertEqual(detected_monitors[1]["x"], 1920)
        self.assertEqual(detected_monitors[1]["width"], 1920)

    @patch("shutil.which", return_value="/usr/bin/wlr-randr")
    @patch("subprocess.run")
    def test_get_wayland_monitors_json_format(
        self, mock_run: MagicMock, mock_which: MagicMock
    ) -> None:
        """get_wayland_monitors should parse wlr-randr --json output."""
        sample_json = json.dumps(
            {
                "heads": [
                    {
                        "name": "DP-1",
                        "enabled": True,
                        "x": 1920,
                        "y": 0,
                        "mode": {"width": 1920, "height": 1080},
                    },
                    {
                        "name": "HDMI-A-1",
                        "enabled": True,
                        "x": 0,
                        "y": 0,
                        "mode": {"width": 2560, "height": 1440},
                    },
                    {
                        "name": "VGA-1",
                        "enabled": False,
                        "x": 0,
                        "y": 0,
                        "mode": {"width": 1024, "height": 768},
                    },
                ]
            }
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=sample_json)
        detected_monitors = wchanger.get_wayland_monitors()
        self.assertEqual(len(detected_monitors), 2)
        self.assertEqual(detected_monitors[0]["x"], 0)
        self.assertEqual(detected_monitors[0]["width"], 2560)
        self.assertEqual(detected_monitors[1]["x"], 1920)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_get_wayland_monitors_swaymsg_fallback(
        self, mock_run: MagicMock, mock_which: MagicMock
    ) -> None:
        """get_wayland_monitors should fall back to swaymsg on Sway compositor."""
        def which_side_effect(command_candidate: str) -> str | None:
            if command_candidate == "swaymsg":
                return "/usr/bin/swaymsg"
            return None

        mock_which.side_effect = which_side_effect
        sample_sway_json = json.dumps(
            [
                {
                    "name": "DP-1",
                    "active": True,
                    "rect": {"x": 1920, "y": 0, "width": 1920, "height": 1080},
                },
                {
                    "name": "HDMI-1",
                    "active": True,
                    "rect": {"x": 0, "y": 0, "width": 2560, "height": 1440},
                },
                {
                    "name": "DP-2",
                    "active": False,
                    "rect": {"x": 3840, "y": 0, "width": 1920, "height": 1080},
                },
            ]
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=sample_sway_json)
        detected_monitors = wchanger.get_wayland_monitors()
        self.assertEqual(len(detected_monitors), 2)
        self.assertEqual(detected_monitors[0]["x"], 0)
        self.assertEqual(detected_monitors[0]["width"], 2560)
        self.assertEqual(detected_monitors[1]["x"], 1920)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_get_wayland_monitors_hyprctl_fallback(
        self, mock_run: MagicMock, mock_which: MagicMock
    ) -> None:
        """get_wayland_monitors should fall back to hyprctl on Hyprland compositor."""
        def which_side_effect(command_candidate: str) -> str | None:
            if command_candidate == "hyprctl":
                return "/usr/bin/hyprctl"
            return None

        mock_which.side_effect = which_side_effect
        sample_hypr_json = json.dumps(
            [
                {
                    "name": "DP-1",
                    "disabled": False,
                    "x": 1920,
                    "y": 0,
                    "width": 1920,
                    "height": 1080,
                },
                {
                    "name": "HDMI-1",
                    "disabled": False,
                    "x": 0,
                    "y": 0,
                    "width": 2560,
                    "height": 1440,
                },
                {
                    "name": "DP-2",
                    "disabled": True,
                    "x": 3840,
                    "y": 0,
                    "width": 1920,
                    "height": 1080,
                },
            ]
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=sample_hypr_json)
        detected_monitors = wchanger.get_wayland_monitors()
        self.assertEqual(len(detected_monitors), 2)
        self.assertEqual(detected_monitors[0]["x"], 0)
        self.assertEqual(detected_monitors[0]["width"], 2560)
        self.assertEqual(detected_monitors[1]["x"], 1920)

    @patch("shutil.which", return_value="/usr/bin/wlr-randr")
    @patch("subprocess.run")
    def test_get_wayland_monitors_process_error(
        self, mock_run: MagicMock, mock_which: MagicMock
    ) -> None:
        """get_wayland_monitors should return empty list on process failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        self.assertEqual(wchanger.get_wayland_monitors(), [])

    @patch("shutil.which", return_value="/usr/bin/xrandr")
    @patch("subprocess.run")
    def test_get_xrandr_monitors_fallback_to_standard_output(
        self, mock_run: MagicMock, mock_which: MagicMock
    ) -> None:
        """get_xrandr_monitors should parse standard xrandr output when --listmonitors returns nothing."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Monitors: 0\n"),
            MagicMock(
                returncode=0,
                stdout=(
                    "Screen 0: minimum 320 x 200, current 3840 x 1080, maximum 16384 x 16384\n"
                    "eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 344mm x 194mm\n"
                    "HDMI-1 connected 1920x1080+1920+0 (normal left inverted right x axis y axis) 597mm x 336mm\n"
                    "DP-1 disconnected (normal left inverted right x axis y axis)\n"
                ),
            ),
        ]
        monitors = wchanger.get_xrandr_monitors()
        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[0]["x"], 0)
        self.assertEqual(monitors[0]["width"], 1920)
        self.assertEqual(monitors[1]["x"], 1920)

    @patch("wchanger.get_xfce_monitor_properties", return_value={})
    @patch("wchanger.get_kde_desktop_count", return_value=0)
    @patch("wchanger.get_xrandr_monitors", return_value=[])
    @patch(
        "wchanger.get_wayland_monitors",
        return_value=[
            {"width": 1920, "height": 1080, "x": 0, "y": 0},
            {"width": 1920, "height": 1080, "x": 1920, "y": 0},
        ],
    )
    def test_detect_connected_monitors_uses_wayland(
        self,
        mock_wayland: MagicMock,
        mock_xrandr: MagicMock,
        mock_kde: MagicMock,
        mock_xfce: MagicMock,
    ) -> None:
        """detect_connected_monitors should utilize get_wayland_monitors when on Wayland."""
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}):
            self.assertEqual(wchanger.detect_connected_monitors(), 2)

    @patch("wchanger.get_xrandr_monitors")
    def test_create_spanned_wallpaper_more_wallpapers_than_monitors(
        self, mock_monitors: MagicMock
    ) -> None:
        """create_spanned_wallpaper should preserve monitor layout even if more wallpapers than monitors."""
        mock_monitors.return_value = [
            {"width": 1920, "height": 1080, "x": 0, "y": 0},
            {"width": 1920, "height": 1080, "x": 1920, "y": 0},
        ]
        first_wallpaper = self.test_dir / "first.png"
        second_wallpaper = self.test_dir / "second.png"
        third_wallpaper = self.test_dir / "third.png"
        Image.new("RGB", (800, 600), color="red").save(first_wallpaper)
        Image.new("RGB", (800, 600), color="green").save(second_wallpaper)
        Image.new("RGB", (800, 600), color="blue").save(third_wallpaper)

        output_wallpaper = self.test_dir / "spanned_three.png"
        result_path = wchanger.create_spanned_wallpaper(
            [first_wallpaper, second_wallpaper, third_wallpaper], output_path=output_wallpaper
        )
        self.assertEqual(result_path, output_wallpaper)
        with Image.open(output_wallpaper) as combined_image:
            self.assertEqual(combined_image.size, (3840, 1080))

    def test_set_lxqt_multimonitor_config_empty_file_adds_desktop_section(self) -> None:
        """set_lxqt_multimonitor_config should write [Desktop] and [Desktop_Screen_0] when config is empty."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.test_dir)}):
            lxqt_config_dir = self.test_dir / "pcmanfm-qt" / "lxqt"
            lxqt_config_dir.mkdir(parents=True, exist_ok=True)
            target_config_file = lxqt_config_dir / "settings.conf"

            operation_success = wchanger.set_lxqt_multimonitor_config(["/new0.png", "/new1.png"])
            self.assertTrue(operation_success)
            config_content = target_config_file.read_text()
            self.assertIn("[Desktop]", config_content)
            self.assertIn("Wallpaper=/new0.png", config_content)
            self.assertIn("[Desktop_Screen_1]", config_content)
            self.assertIn("Wallpaper=/new1.png", config_content)

    @patch("subprocess.run")
    def test_set_gnome_background_older_version_without_dark_key(
        self, mock_run: MagicMock
    ) -> None:
        """set_gnome_background should succeed on GNOME < 42 when picture-uri-dark key fails."""
        def run_side_effect(command_args: list[str], **kwargs) -> MagicMock:
            if "picture-uri-dark" in command_args:
                return MagicMock(returncode=1, stderr="No such key 'picture-uri-dark'")
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = run_side_effect
        wallpaper_target_uri = "file:///home/user/background.jpg"
        operation_success = wchanger.set_gnome_background(wallpaper_target_uri, theme=None)
        self.assertTrue(operation_success)

    @patch("wchanger.urlopen")
    @patch("time.sleep")
    def test_fetch_url_with_retry_does_not_retry_http_404(
        self, mock_sleep: MagicMock, mock_urlopen: MagicMock
    ) -> None:
        """_fetch_url_with_retry should immediately raise HTTPError for 404 without retries or sleep."""
        mock_urlopen.side_effect = HTTPError("https://example.com/notfound", 404, "Not Found", {}, None)
        dummy_request = Request("https://example.com/notfound")
        with self.assertRaises(HTTPError):
            wchanger._fetch_url_with_retry(
                dummy_request, timeout=10, max_retries=3, retry_delay_seconds=0.01
            )
        self.assertEqual(mock_urlopen.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("wchanger.urlopen")
    @patch("time.sleep")
    def test_fetch_url_with_retry_recovers_after_http_503(
        self, mock_sleep: MagicMock, mock_urlopen: MagicMock
    ) -> None:
        """_fetch_url_with_retry should retry and succeed when server returns HTTP 503 Service Unavailable."""
        successful_response = MagicMock()
        successful_response.read.return_value = b"healthy_response"
        successful_response.__enter__.return_value = successful_response
        mock_urlopen.side_effect = [
            HTTPError("https://example.com", 503, "Service Unavailable", {}, None),
            successful_response,
        ]

        dummy_request = Request("https://example.com")
        downloaded_bytes = wchanger._fetch_url_with_retry(
            dummy_request, timeout=10, max_retries=3, retry_delay_seconds=0.01
        )
        self.assertEqual(downloaded_bytes, b"healthy_response")
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("wchanger.urlopen")
    @patch("time.sleep")
    def test_fetch_url_with_retry_recovers_after_transient_error(
        self, mock_sleep: MagicMock, mock_urlopen: MagicMock
    ) -> None:
        """_fetch_url_with_retry should retry and recover on transient URLError."""
        successful_response = MagicMock()
        successful_response.read.return_value = b"success_bytes"
        successful_response.__enter__.return_value = successful_response
        mock_urlopen.side_effect = [
            URLError("Temporary network blip"),
            successful_response,
        ]

        dummy_request = Request("https://example.com")
        downloaded_bytes = wchanger._fetch_url_with_retry(
            dummy_request, timeout=10, max_retries=3, retry_delay_seconds=0.01
        )
        self.assertEqual(downloaded_bytes, b"success_bytes")
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("wchanger.urlopen")
    @patch("time.sleep")
    def test_fetch_url_with_retry_raises_when_exhausted(
        self, mock_sleep: MagicMock, mock_urlopen: MagicMock
    ) -> None:
        """_fetch_url_with_retry should re-raise the error once all retry attempts are exhausted."""
        mock_urlopen.side_effect = URLError("Persistent network outage")
        dummy_request = Request("https://example.com")
        with self.assertRaises(URLError):
            wchanger._fetch_url_with_retry(
                dummy_request, timeout=10, max_retries=2, retry_delay_seconds=0.01
            )
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_install_autostart_includes_wayland_session_type(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_install_autostart_service should forward XDG_SESSION_TYPE to systemd service."""
        mock_prompt.return_value = 60
        mock_run.return_value = MagicMock(returncode=0)

        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with self.assertRaises(SystemExit) as exception_context:
                wchanger.setup_install_autostart_service(
                    desktop_override="gnome",
                    online_provider="wallhaven",
                )
            self.assertEqual(exception_context.exception.code, 0)

        tee_invocation = mock_run.call_args_list[0]
        service_text = tee_invocation.kwargs["input"].decode("utf-8")
        self.assertIn("Environment=XDG_SESSION_TYPE=wayland", service_text)

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_install_autostart_includes_desktop_and_session(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_install_autostart_service should forward desktop environment variables to systemd."""
        mock_prompt.return_value = 60
        mock_run.return_value = MagicMock(returncode=0)

        session_environment = {
            "XDG_CURRENT_DESKTOP": "GNOME",
            "DESKTOP_SESSION": "gnome",
            "PATH": "/usr/local/bin:/usr/bin:/bin",
        }
        with patch.dict(os.environ, session_environment):
            with self.assertRaises(SystemExit) as exception_context:
                wchanger.setup_install_autostart_service(
                    desktop_override="gnome",
                    online_provider="wallhaven",
                )
            self.assertEqual(exception_context.exception.code, 0)

        tee_invocation = mock_run.call_args_list[0]
        service_text = tee_invocation.kwargs["input"].decode("utf-8")
        self.assertIn("Environment=XDG_CURRENT_DESKTOP=GNOME", service_text)
        self.assertIn("Environment=DESKTOP_SESSION=gnome", service_text)
        self.assertIn("Environment=PATH=/usr/local/bin:/usr/bin:/bin", service_text)

    @patch("shutil.which", return_value="/usr/bin/xrandr")
    @patch("subprocess.run")
    def test_get_xrandr_monitors_negative_offsets(
        self, mock_run: MagicMock, mock_which: MagicMock
    ) -> None:
        """get_xrandr_monitors should parse negative coordinate offsets correctly."""
        sample_xrandr_output = (
            "Monitors: 2\n"
            " 0: +*DP-1 2560/597x1440/336+0+0 DP-1\n"
            " 1: +DP-2 1920/527x1080/296-1920+0 DP-2\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=sample_xrandr_output)

        monitors = wchanger.get_xrandr_monitors()
        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[0]["x"], -1920)
        self.assertEqual(monitors[0]["y"], 0)
        self.assertEqual(monitors[0]["width"], 1920)
        self.assertEqual(monitors[0]["height"], 1080)
        self.assertEqual(monitors[1]["x"], 0)
        self.assertEqual(monitors[1]["y"], 0)
        self.assertEqual(monitors[1]["width"], 2560)
        self.assertEqual(monitors[1]["height"], 1440)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_get_wayland_monitors_negative_offsets(
        self, mock_run: MagicMock, mock_which: MagicMock
    ) -> None:
        """get_wayland_monitors should parse negative coordinate offsets in wlr-randr."""
        def fake_which(command_name: str) -> str | None:
            if command_name == "wlr-randr":
                return "/usr/bin/wlr-randr"
            return None

        mock_which.side_effect = fake_which
        sample_wlr_text = (
            "DP-1 \"Brand Display\" (enabled)\n"
            "  Position: -1920, 0\n"
            "  1920x1080 px, 60.00 Hz (current)\n"
            "DP-2 \"Brand Display\" (enabled)\n"
            "  Position: 0, 0\n"
            "  2560x1440 px, 144.00 Hz (current)\n"
        )
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=0, stdout=sample_wlr_text),
        ]

        monitors = wchanger.get_wayland_monitors()
        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[0]["x"], -1920)
        self.assertEqual(monitors[0]["width"], 1920)
        self.assertEqual(monitors[1]["x"], 0)
        self.assertEqual(monitors[1]["width"], 2560)

    @patch("wchanger.get_xrandr_monitors")
    def test_create_spanned_wallpaper_negative_offsets(
        self, mock_get_monitors: MagicMock
    ) -> None:
        """create_spanned_wallpaper should calculate correct bounding box with negative monitor coordinates."""
        mock_get_monitors.return_value = [
            {"width": 1920, "height": 1080, "x": -1920, "y": 0},
            {"width": 1920, "height": 1080, "x": 0, "y": 0},
        ]
        first_wallpaper_path = self.test_dir / "wallpaper_left.png"
        second_wallpaper_path = self.test_dir / "wallpaper_right.png"
        Image.new("RGB", (200, 200), color="blue").save(first_wallpaper_path)
        Image.new("RGB", (200, 200), color="green").save(second_wallpaper_path)

        output_wallpaper_path = self.test_dir / "spanned_output.png"
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": ""}, clear=False):
            generated_path = wchanger.create_spanned_wallpaper(
                [first_wallpaper_path, second_wallpaper_path],
                output_path=output_wallpaper_path,
            )

        self.assertTrue(generated_path.exists())
        with Image.open(generated_path) as resulting_image:
            self.assertEqual(resulting_image.size, (3840, 1080))


if __name__ == "__main__":
    unittest.main()



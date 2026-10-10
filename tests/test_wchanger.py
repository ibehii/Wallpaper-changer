"""Tests for wchanger.py."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch, MagicMock

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

        sub_dir = self.test_dir / "subfolder"
        sub_dir.mkdir()

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
        uri = "file:///home/user/pic.jpg"

        success = wchanger.set_gnome_wallpaper(uri, theme="dark")
        self.assertTrue(success)
        mock_run.assert_called_once_with(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri-dark",
                uri,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_set_gnome_wallpaper_theme_light(self, mock_run: MagicMock) -> None:
        """Light theme should only invoke picture-uri."""
        mock_run.return_value = MagicMock(returncode=0)
        uri = "file:///home/user/pic.jpg"

        success = wchanger.set_gnome_wallpaper(uri, theme="light")
        self.assertTrue(success)
        mock_run.assert_called_once_with(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri",
                uri,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_set_gnome_wallpaper_theme_both(self, mock_run: MagicMock) -> None:
        """None theme should set both picture-uri and picture-uri-dark."""
        mock_run.return_value = MagicMock(returncode=0)
        uri = "file:///home/user/pic.jpg"

        success = wchanger.set_gnome_wallpaper(uri, theme=None)
        self.assertTrue(success)
        self.assertEqual(mock_run.call_count, 2)

    @patch("subprocess.run")
    def test_set_cinnamon_wallpaper(self, mock_run: MagicMock) -> None:
        """Cinnamon should invoke org.cinnamon.desktop.background picture-uri."""
        mock_run.return_value = MagicMock(returncode=0)
        uri = "file:///home/user/pic.jpg"

        success = wchanger.set_cinnamon_wallpaper(uri)
        self.assertTrue(success)
        mock_run.assert_called_once_with(
            [
                "gsettings",
                "set",
                "org.cinnamon.desktop.background",
                "picture-uri",
                uri,
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
        uri = "file:///home/user/pic.jpg"

        success = wchanger.set_kde_wallpaper(uri)
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
        self.assertIn(f'desktop.writeConfig("Image", "{uri}");', js_script)

    @patch("subprocess.run")
    def test_set_kde_wallpaper_explicit_executable(self, mock_run: MagicMock) -> None:
        """KDE wallpaper setter should support passing explicit qdbus executable."""
        mock_run.return_value = MagicMock(returncode=0)
        uri = "file:///home/user/pic.jpg"

        success = wchanger.set_kde_background(uri, qdbus_executable="qdbus6")
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
        uri = "file:///home/user/pic.jpg"

        success = wchanger.set_kde_wallpaper(uri)
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
        with self.assertRaises(SystemExit) as cm:
            wchanger.verify_system_requirements("kde")
        self.assertEqual(cm.exception.code, 1)

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
        with self.assertRaises(SystemExit) as cm:
            wchanger.verify_system_requirements("gnome")
        self.assertEqual(cm.exception.code, 1)

    @patch("platform.system", return_value="Darwin")
    def test_verify_system_requirements_non_linux(self, mock_platform: MagicMock) -> None:
        """verify_system_requirements should exit on non-Linux platforms."""
        with self.assertRaises(SystemExit) as cm:
            wchanger.verify_system_requirements("kde")
        self.assertEqual(cm.exception.code, 1)

    @patch("wchanger.set_kde_background", return_value=True)
    @patch("time.sleep")
    def test_run_wallpaper_cycle_kde(
        self, mock_sleep: MagicMock, mock_set_kde: MagicMock
    ) -> None:
        """run_wallpaper_cycle should invoke set_kde_background when desktop is kde."""
        image_path = self.test_dir / "wallpaper.png"
        Image.new("RGB", (10, 10)).save(image_path)

        with self.assertRaises(SystemExit) as cm:
            wchanger.run_wallpaper_cycle(
                desktop_environment="kde",
                wallpapers=[str(image_path)],
                pause_seconds=1,
                repetition=False,
                output_mode="console",
            )
        self.assertEqual(cm.exception.code, 0)
        expected_uri = image_path.resolve().as_uri()
        mock_set_kde.assert_called_once_with(expected_uri)

    @patch("shutil.which")
    def test_setup_auto_start_missing_systemctl(self, mock_which: MagicMock) -> None:
        """setup_auto_start should exit when systemctl is missing."""
        mock_which.return_value = None
        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start()
        self.assertEqual(cm.exception.code, 1)

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_sudo_failure(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_auto_start should exit with status 1 if sudo/systemctl fails."""
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_prompt.side_effect = [30, self.test_dir]
        mock_run.return_value = MagicMock(returncode=1)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start()
        self.assertEqual(cm.exception.code, 1)

    @patch("shutil.which")
    @patch("click.prompt")
    @patch("subprocess.run")
    def test_setup_auto_start_kde_override(
        self, mock_run: MagicMock, mock_prompt: MagicMock, mock_which: MagicMock
    ) -> None:
        """setup_auto_start with desktop_override='kde' should inject --kde into ExecStart."""
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [45, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start(desktop_override="kde")
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start()
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        for env_dict, expected_result in test_cases:
            with patch.dict(os.environ, env_dict, clear=True):
                self.assertEqual(
                    wchanger.detect_desktop_environment(),
                    expected_result,
                    msg=f"Failed for env {env_dict}",
                )

    @patch("wchanger.find_kde_qdbus_executable", return_value="qdbus")
    @patch("subprocess.run")
    def test_set_kde_wallpaper_with_spaces_and_special_chars(
        self, mock_run: MagicMock, mock_find_qdbus: MagicMock
    ) -> None:
        """set_kde_wallpaper should format paths with spaces and special characters properly."""
        mock_run.return_value = MagicMock(returncode=0)
        uri = "file:///home/user/My%20Photos/wallpaper%20(1).jpg"

        success = wchanger.set_kde_wallpaper(uri)
        self.assertTrue(success)
        command_args = mock_run.call_args[0][0]
        self.assertIn(f'desktop.writeConfig("Image", "{uri}");', command_args[4])


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
        img_file = folder_with_spaces / "wallpaper.jpg"
        Image.new("RGB", (5, 5)).save(img_file)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, folder_with_spaces]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start(desktop_override="kde")
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        # Prompt sequence: pause duration, photo directory, desktop environment choice
        mock_prompt.side_effect = [30, self.test_dir, "kde"]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start()
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [30, self.test_dir]

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start()
        self.assertEqual(cm.exception.code, 1)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        uri = "file:///home/user/My%20Wallpapers/pic%20(1).jpg"
        result = wchanger.set_xfce_wallpaper(uri)
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
        uri = "file:///home/user/Nature%20Photos/forest.png"

        result = wchanger.set_mate_wallpaper(uri)
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
        uri = "file:///home/user/Abstract%20Art/minimal.webp"

        result = wchanger.set_lxqt_wallpaper(uri)
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
        with self.assertRaises(SystemExit) as cm:
            wchanger.verify_system_requirements("xfce")
        self.assertEqual(cm.exception.code, 1)

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
        with self.assertRaises(SystemExit) as cm:
            wchanger.verify_system_requirements("mate")
        self.assertEqual(cm.exception.code, 1)

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
        with self.assertRaises(SystemExit) as cm:
            wchanger.verify_system_requirements("lxqt")
        self.assertEqual(cm.exception.code, 1)

    # run_wallpaper_cycle Tests for XFCE, MATE, LXQt
    @patch("wchanger.set_xfce_background", return_value=True)
    @patch("time.sleep")
    def test_run_wallpaper_cycle_xfce(
        self, mock_sleep: MagicMock, mock_set_xfce: MagicMock
    ) -> None:
        """run_wallpaper_cycle should invoke set_xfce_background when desktop is xfce."""
        image_path = self.test_dir / "wallpaper.png"
        Image.new("RGB", (10, 10)).save(image_path)

        with self.assertRaises(SystemExit) as cm:
            wchanger.run_wallpaper_cycle(
                desktop_environment="xfce",
                wallpapers=[str(image_path)],
                pause_seconds=1,
                repetition=False,
                output_mode="console",
            )
        self.assertEqual(cm.exception.code, 0)
        mock_set_xfce.assert_called_once_with(str(image_path))

    @patch("wchanger.set_mate_background", return_value=True)
    @patch("time.sleep")
    def test_run_wallpaper_cycle_mate(
        self, mock_sleep: MagicMock, mock_set_mate: MagicMock
    ) -> None:
        """run_wallpaper_cycle should invoke set_mate_background when desktop is mate."""
        image_path = self.test_dir / "wallpaper.png"
        Image.new("RGB", (10, 10)).save(image_path)

        with self.assertRaises(SystemExit) as cm:
            wchanger.run_wallpaper_cycle(
                desktop_environment="mate",
                wallpapers=[str(image_path)],
                pause_seconds=1,
                repetition=False,
                output_mode="console",
            )
        self.assertEqual(cm.exception.code, 0)
        mock_set_mate.assert_called_once_with(str(image_path))

    @patch("wchanger.set_lxqt_background", return_value=True)
    @patch("time.sleep")
    def test_run_wallpaper_cycle_lxqt(
        self, mock_sleep: MagicMock, mock_set_lxqt: MagicMock
    ) -> None:
        """run_wallpaper_cycle should invoke set_lxqt_background when desktop is lxqt."""
        image_path = self.test_dir / "wallpaper.png"
        Image.new("RGB", (10, 10)).save(image_path)

        with self.assertRaises(SystemExit) as cm:
            wchanger.run_wallpaper_cycle(
                desktop_environment="lxqt",
                wallpapers=[str(image_path)],
                pause_seconds=1,
                repetition=False,
                output_mode="console",
            )
        self.assertEqual(cm.exception.code, 0)
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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start(desktop_override="xfce")
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start(desktop_override="mate")
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start(desktop_override="lxqt")
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start()
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [30, self.test_dir, "mate"]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start()
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start()
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start()
        self.assertEqual(cm.exception.code, 0)

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
        with self.assertRaises(SystemExit) as cm:
            wchanger.verify_system_requirements("unknown_de")
        self.assertEqual(cm.exception.code, 1)

    def test_cli_xfce4_flag_alias(self) -> None:
        """cli should accept --xfce4 as an alias for --xfce."""
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [30, self.test_dir, "xfce"]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start()
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [30, self.test_dir, "lxqt"]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start()
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with patch.dict(os.environ, {"DISPLAY": ":1", "WAYLAND_DISPLAY": "wayland-0"}, clear=False):
            with self.assertRaises(SystemExit) as cm:
                wchanger.setup_auto_start(desktop_override="lxqt")
            self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start(desktop_override="xfce", color_theme="dark")
        self.assertEqual(cm.exception.code, 0)

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
        img_path = self.test_dir / "test.png"
        Image.new("RGB", (5, 5)).save(img_path)

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_prompt.side_effect = [60, self.test_dir]
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start(desktop_override="gnome", color_theme="dark")
        self.assertEqual(cm.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("-t dark", written_service_content)

    @patch("time.sleep")
    def test_run_wallpaper_cycle_skips_missing_file(self, mock_sleep: MagicMock) -> None:
        """run_wallpaper_cycle should skip files that do not exist."""
        real_img = self.test_dir / "exists.png"
        Image.new("RGB", (5, 5)).save(real_img)
        missing_img = self.test_dir / "nonexistent.png"

        with patch("wchanger.set_xfce_background", return_value=True) as mock_set:
            with self.assertRaises(SystemExit) as cm:
                wchanger.run_wallpaper_cycle(
                    desktop_environment="xfce",
                    wallpapers=[str(missing_img), str(real_img)],
                    pause_seconds=1,
                    repetition=False,
                    output_mode="console",
                )
            self.assertEqual(cm.exception.code, 0)
            mock_set.assert_called_once_with(str(real_img))

    @patch("time.sleep")
    def test_run_wallpaper_cycle_logging_mode(self, mock_sleep: MagicMock) -> None:
        """run_wallpaper_cycle in log output mode should emit log records."""
        img = self.test_dir / "wallpaper.png"
        Image.new("RGB", (5, 5)).save(img)

        with patch("wchanger.set_mate_background", return_value=True):
            with patch("logging.info") as mock_log_info:
                with self.assertRaises(SystemExit) as cm:
                    wchanger.run_wallpaper_cycle(
                        desktop_environment="mate",
                        wallpapers=[str(img)],
                        pause_seconds=1,
                        repetition=False,
                        output_mode="log",
                    )
                self.assertEqual(cm.exception.code, 0)
                mock_log_info.assert_any_call(f"Wallpaper changed on MATE to {img}.")

    def test_configure_logging_creates_handler(self) -> None:
        """configure_logging with 'log' mode should add a FileHandler."""
        log_file = self.test_dir / "custom.log"
        wchanger.configure_logging("log", log_file_path=log_file)
        import logging
        root_logger = logging.getLogger()
        handler_found = any(isinstance(h, logging.FileHandler) and Path(h.baseFilename) == log_file.resolve() for h in root_logger.handlers)
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

        url = wchanger.fetch_wallhaven_url()
        self.assertEqual(url, "https://w.wallhaven.cc/full/abc.jpg")

    @patch("wchanger.urlopen")
    def test_fetch_wallhaven_url_empty_data(self, mock_urlopen: MagicMock) -> None:
        """fetch_wallhaven_url should raise ValueError when data is empty."""
        fake_response = MagicMock()
        fake_response.read.return_value = b'{"data": []}'
        fake_response.__enter__.return_value = fake_response
        mock_urlopen.return_value = fake_response

        with self.assertRaises(ValueError) as cm:
            wchanger.fetch_wallhaven_url()
        self.assertIn("No wallpapers found", str(cm.exception))

    @patch("wchanger.urlopen")
    def test_fetch_wallhaven_url_missing_path(self, mock_urlopen: MagicMock) -> None:
        """fetch_wallhaven_url should raise ValueError when entry is missing path."""
        fake_response = MagicMock()
        fake_response.read.return_value = b'{"data": [{"id": "123"}]}'
        fake_response.__enter__.return_value = fake_response
        mock_urlopen.return_value = fake_response

        with self.assertRaises(ValueError) as cm:
            wchanger.fetch_wallhaven_url()
        self.assertIn("Wallhaven entry missing image path", str(cm.exception))

    @patch("wchanger.urlopen")
    def test_fetch_bing_url_success(self, mock_urlopen: MagicMock) -> None:
        """fetch_bing_url should parse JSON response and construct full image URL."""
        fake_response = MagicMock()
        fake_response.read.return_value = (
            b'{"images": [{"url": "/th?id=OHR.SampleBing_EN-US_1920x1080.jpg"}]}'
        )
        fake_response.__enter__.return_value = fake_response
        mock_urlopen.return_value = fake_response

        url = wchanger.fetch_bing_url()
        self.assertEqual(url, "https://www.bing.com/th?id=OHR.SampleBing_EN-US_1920x1080.jpg")

    @patch("wchanger.urlopen")
    def test_fetch_bing_url_empty_images(self, mock_urlopen: MagicMock) -> None:
        """fetch_bing_url should raise ValueError when images list is empty."""
        fake_response = MagicMock()
        fake_response.read.return_value = b'{"images": []}'
        fake_response.__enter__.return_value = fake_response
        mock_urlopen.return_value = fake_response

        with self.assertRaises(ValueError) as cm:
            wchanger.fetch_bing_url()
        self.assertIn("No images found", str(cm.exception))

    def test_fetch_picsum_url(self) -> None:
        """fetch_picsum_url should return a 1920x1080 random URL."""
        url = wchanger.fetch_picsum_url()
        self.assertTrue(url.startswith("https://picsum.photos/1920/1080?random="))

    def test_fetch_loremflickr_url(self) -> None:
        """fetch_loremflickr_url should return a 1920x1080 nature lock URL."""
        url = wchanger.fetch_loremflickr_url()
        self.assertTrue(url.startswith("https://loremflickr.com/1920/1080/nature?lock="))

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
        with self.assertRaises(ValueError) as cm:
            wchanger.download_online_wallpaper("https://example.com/image.jpg", dest_file)
        self.assertIn("Received empty image content", str(cm.exception))

    def test_format_network_error_http(self) -> None:
        """format_network_error should format HTTPError with status code."""
        from urllib.error import HTTPError
        error = HTTPError("https://example.com", 404, "Not Found", {}, None)
        msg = wchanger.format_network_error("bing", error)
        self.assertIn("404", msg)
        self.assertIn("bing", msg)

    def test_format_network_error_url(self) -> None:
        """format_network_error should format URLError advising connection check."""
        from urllib.error import URLError
        error = URLError("Temporary failure in name resolution")
        msg = wchanger.format_network_error("wallhaven", error)
        self.assertIn("check your internet connection", msg)
        self.assertIn("wallhaven", msg)

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
        success, msg = wchanger.set_wallpaper_for_desktop("gnome", sample_file, "dark")
        self.assertTrue(success)
        mock_gnome.assert_called_once_with(sample_file.resolve().as_uri(), "dark")

        # Cinnamon
        success, msg = wchanger.set_wallpaper_for_desktop("cinnamon", sample_file)
        self.assertTrue(success)
        mock_cinnamon.assert_called_once_with(sample_file.resolve().as_uri())

        # KDE
        success, msg = wchanger.set_wallpaper_for_desktop("kde", sample_file)
        self.assertTrue(success)
        mock_kde.assert_called_once_with(sample_file.resolve().as_uri())

        # XFCE
        success, msg = wchanger.set_wallpaper_for_desktop("xfce", sample_file)
        self.assertTrue(success)
        mock_xfce.assert_called_once_with(str(sample_file))

        # MATE
        success, msg = wchanger.set_wallpaper_for_desktop("mate", sample_file)
        self.assertTrue(success)
        mock_mate.assert_called_once_with(str(sample_file))

        # LXQt
        success, msg = wchanger.set_wallpaper_for_desktop("lxqt", sample_file)
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

        with self.assertRaises(SystemExit) as cm:
            wchanger.run_online_wallpaper_cycle(
                desktop_environment="gnome",
                provider="bing",
                pause_seconds=1,
                repetition=False,
                output_mode="console",
                cache_dir=self.test_dir,
            )
        self.assertEqual(cm.exception.code, 0)
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

        with self.assertRaises(SystemExit) as cm:
            wchanger.run_online_wallpaper_cycle(
                desktop_environment="gnome",
                provider="wallhaven",
                pause_seconds=1,
                repetition=False,
                output_mode="console",
                cache_dir=self.test_dir,
            )
        self.assertEqual(cm.exception.code, 1)

    def test_run_online_wallpaper_cycle_unknown_provider(self) -> None:
        """run_online_wallpaper_cycle should raise ValueError on invalid provider name."""
        with self.assertRaises(ValueError) as cm:
            wchanger.run_online_wallpaper_cycle(
                desktop_environment="gnome",
                provider="nonexistent_provider",
                pause_seconds=1,
                repetition=False,
                output_mode="console",
            )
        self.assertIn("Unknown online provider", str(cm.exception))

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
        self.assertIn("Awesome Wallpaper Changer started in background (PID: 54321)", result.output)
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

        with self.assertRaises(SystemExit) as cm:
            wchanger.setup_auto_start(desktop_override="gnome", online_provider="bing")
        self.assertEqual(cm.exception.code, 0)

        tee_call = mock_run.call_args_list[0]
        written_service_content = tee_call.kwargs["input"].decode("utf-8")
        self.assertIn("--online bing", written_service_content)
        self.assertIn("--gnome", written_service_content)


if __name__ == "__main__":
    unittest.main()



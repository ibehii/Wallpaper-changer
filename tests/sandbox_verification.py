#!/usr/bin/env python3
"""Comprehensive sandboxed functional test harness for wchanger CLI."""

import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WCHANGER_PY = REPO_ROOT / "wchanger.py"

def create_valid_png(path: Path) -> None:
    # Minimal 1x1 valid PNG bytes
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05"
        b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    path.write_bytes(png_bytes)

def run_in_bwrap(args: list[str], sandbox_dir: Path, env_override: dict | None = None) -> subprocess.CompletedProcess:
    fake_home = sandbox_dir / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "bwrap",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/lib64", "/lib64",
        "--ro-bind", "/bin", "/bin",
        "--dev", "/dev",
        "--proc", "/proc",
        "--tmpfs", "/tmp",
        "--bind", str(sandbox_dir), str(sandbox_dir),
        "--bind", str(REPO_ROOT), str(REPO_ROOT),
        "--setenv", "HOME", str(fake_home),
        "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "LC_ALL", "C.UTF-8",
        "--unshare-net",
    ]
    if env_override:
        for k, v in env_override.items():
            cmd.extend(["--setenv", k, v])

    cmd.extend([sys.executable, str(WCHANGER_PY)])
    cmd.extend(args)
    
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(sandbox_dir))

def test_local_folder_rotation(sandbox_dir: Path) -> None:
    print("[*] Testing local folder rotation in bwrap sandbox...")
    img_dir = sandbox_dir / "wallpapers"
    img_dir.mkdir(parents=True, exist_ok=True)
    img1 = img_dir / "wall1.png"
    create_valid_png(img1)
    
    # Run wchanger with mock gnome environment override (using -p 1s --gnome --no-repetition --no-config)
    res = run_in_bwrap(["-p", "1", "--gnome", "--source", "folder", "--no-repetition", "--no-config", str(img_dir)], sandbox_dir)
    print(f"  Exit code: {res.returncode}")
    if res.returncode != 0:
        print(f"  Stdout:\n{res.stdout}")
        print(f"  Stderr:\n{res.stderr}")
    assert res.returncode == 0, f"Local rotation failed: {res.stderr}"
    assert "Wallpaper changed on GNOME" in res.stdout or "Program exited after setting all wallpapers" in res.stdout
    print("  [+] Local folder rotation test passed!")

def test_local_recursive_scan(sandbox_dir: Path) -> None:
    print("[*] Testing local recursive scanning...")
    nested_dir = sandbox_dir / "wallpapers" / "sub" / "deep"
    nested_dir.mkdir(parents=True, exist_ok=True)
    nested_img = nested_dir / "deep_wall.png"
    create_valid_png(nested_img)
    
    res = run_in_bwrap(["-p", "1", "--gnome", "-R", "--source", "folder", "--no-repetition", "--no-config", str(sandbox_dir / "wallpapers")], sandbox_dir)
    assert res.returncode == 0, f"Recursive scan failed: {res.stderr}"
    print("  [+] Recursive scan test passed!")

def test_empty_folder_rejection(sandbox_dir: Path) -> None:
    print("[*] Testing empty folder rejection...")
    empty_dir = sandbox_dir / "empty_dir"
    empty_dir.mkdir(parents=True, exist_ok=True)
    
    res = run_in_bwrap(["--gnome", "--no-repetition", "--no-config", str(empty_dir)], sandbox_dir)
    assert res.returncode == 1, "Expected exit code 1 on empty directory"
    assert "No valid image files found" in res.stdout or "No valid image files found" in res.stderr
    print("  [+] Empty folder rejection test passed!")

def test_category_with_offline_network(sandbox_dir: Path) -> None:
    print("[*] Testing offline network handling in network-isolated sandbox...")
    res = run_in_bwrap(["--gnome", "--online", "wallhaven", "-C", "nature", "--no-repetition", "--no-config"], sandbox_dir)
    # Since network is unshared, it should gracefully display network error
    combined = res.stdout + res.stderr
    assert "Network Error" in combined or "Unable to connect" in combined or "check your internet connection" in combined
    print("  [+] Network error gracefully handled in sandbox!")

def test_corrupt_config_fallback(sandbox_dir: Path) -> None:
    print("[*] Testing corrupt config file fallback...")
    config_file = sandbox_dir / "bad_config.toml"
    config_file.write_text("invalid [ [ toml syntax :::")
    
    img_dir = sandbox_dir / "wallpapers"
    res = run_in_bwrap(["-c", str(config_file), "-p", "1", "--gnome", "--no-repetition", str(img_dir)], sandbox_dir)
    combined = res.stdout + res.stderr
    assert "Warning: Failed to parse configuration file" in combined
    assert res.returncode == 0
    print("  [+] Corrupt config fallback test passed!")

def main() -> int:
    print("=== Running Local Sandbox Verification Suite ===")
    with tempfile.TemporaryDirectory() as tmp_str:
        sandbox_dir = Path(tmp_str)
        test_local_folder_rotation(sandbox_dir)
        test_local_recursive_scan(sandbox_dir)
        test_empty_folder_rejection(sandbox_dir)
        test_category_with_offline_network(sandbox_dir)
        test_corrupt_config_fallback(sandbox_dir)
    print("\n[+] ALL SANDBOX FUNCTIONALITY TESTS PASSED SUCCESSFULLY!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

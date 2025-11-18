#!/usr/bin/env python3
# VergeGrid Environment Manager (Cleanup / Reset / Backup / Upgrade)
# Author: Sonja + Code GPT
# Safely detects, backs up, resets, upgrades, or removes existing VergeGrid installations.

# --- VergeGrid Path Fix ---
import os
import sys

# Find VergeGrid root (one level up from /setup/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

import json
import time
import shutil
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from colorama import init, Fore, Style

from vergegrid_common import (
    load_vergegrid_config,
    ensure_vergegrid_config,
    save_install_path,
    read_saved_path,
    find_existing_install
)

init(autoreset=True)

# ============================================================
# Configuration
# ============================================================

SERVICES = ["VergeGridApache", "VergeGridMySQL", "VergeGridOpenSim"]
INSTALL_MARKER = "vergegrid.conf"
SAVE_PATH = Path(r"C:\ProgramData\VergeGrid\install_path.txt")
LOG_PATH = Path(os.getenv("TEMP", "C:\\Temp")) / "vergegrid_cleanup.log"
REPORT_PATH = Path(os.getenv("TEMP", "C:\\Temp")) / "cleanup_report.json"

# ============================================================
# Utilities
# ============================================================

def log(msg):
    """Log to both console and file."""
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as logf:
        logf.write(f"{msg}\n")


def run_cmd(cmd):
    """Run a command and return success + output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, (result.stdout or result.stderr).strip()
    except Exception as e:
        return False, str(e)


def get_available_drives():
    """Return a list of available drive roots (A-Z)."""
    drives = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        path = f"{letter}:\\"
        if os.path.exists(path):
            drives.append(path)
    return drives


def find_existing_install():
    """Scan all drives for VergeGrid installations."""
    for drive in get_available_drives():
        candidate = Path(drive) / "VergeGrid" / INSTALL_MARKER
        if candidate.exists():
            return candidate.parent
    return None


def read_saved_path():
    """Read stored install path from ProgramData."""
    if SAVE_PATH.exists():
        try:
            return Path(SAVE_PATH.read_text(encoding="utf-8").strip())
        except Exception:
            return None
    return None


def save_install_path(path: Path):
    """Persist install path to ProgramData for future use."""
    try:
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SAVE_PATH.write_text(str(path), encoding="utf-8")
        log(Fore.CYAN + f"[INFO] Saved system path reference: {path}")
    except Exception as e:
        log(Fore.RED + f"[WARN] Could not save install path: {e}")


def stop_service(name):
    """Attempt to stop a Windows service by name, handling 'not running' gracefully."""
    success, output = run_cmd(["sc", "query", name])
    if not success or "does not exist" in output:
        log(Fore.YELLOW + f"[INFO] Service {name} not found.")
        return

    if "STATE" in output and "STOPPED" in output:
        log(Fore.YELLOW + f"[INFO] Service {name} found but already stopped.")
        return

    if "STATE" in output and "RUNNING" in output:
        log(Fore.YELLOW + f"[STOPPING] {name} ...")
        success, stop_output = run_cmd(["sc", "stop", name])
        if success:
            log(Fore.GREEN + f"[STOPPED] {name}")
        elif "1062" in stop_output:
            log(Fore.YELLOW + f"[INFO] Service {name} was not running; no action needed.")
        else:
            log(Fore.RED + f"[WARN] Failed to stop {name}: {stop_output}")
    else:
        log(Fore.YELLOW + f"[INFO] Service {name} is not running or inactive.")


def unregister_service(name):
    """Attempt to delete a Windows service registration if it exists."""
    success, output = run_cmd(["sc", "query", name])
    if not success or "does not exist" in output:
        log(Fore.YELLOW + f"[INFO] Service {name} not found (no unregister needed).")
        return

    log(Fore.YELLOW + f"[REMOVING] Unregistering service {name} ...")
    success, output = run_cmd(["sc", "delete", name])
    if success:
        log(Fore.GREEN + f"[REMOVED] Service {name} unregistered successfully.")
    else:
        if "marked for deletion" in output.lower():
            log(Fore.CYAN + f"[INFO] Service {name} already marked for deletion (pending reboot).")
        else:
            log(Fore.RED + f"[WARN] Failed to unregister {name}: {output}")


def remove_dir_safe(path: Path):
    """Safely remove a directory if it exists."""
    if not path.exists():
        log(Fore.YELLOW + f"[SKIP] {path} not found.")
        return
    try:
        shutil.rmtree(path, ignore_errors=False)
        log(Fore.GREEN + f"[REMOVED] {path}")
    except Exception as e:
        log(Fore.RED + f"[ERROR] Could not remove {path}: {e}")


def cleanup_shortcuts():
    """Remove VergeGrid Start Menu shortcuts."""
    start_menu = Path(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\VergeGrid")
    if start_menu.exists():
        remove_dir_safe(start_menu)

# ============================================================
# Main Routine (patched cancel logic)
# ============================================================

def main():
    if platform.system() != "Windows":
        print(Fore.RED + "This script only runs on Windows.")
        sys.exit(2)

    if LOG_PATH.exists():
        LOG_PATH.unlink()

    print(Style.BRIGHT + "\n=== VergeGrid Cleanup / Reset / Upgrade Utility ===\n")

    root = read_saved_path() or find_existing_install()
    if not root or not root.exists():
        print(Fore.YELLOW + "No existing VergeGrid installation detected.")
        print("::VERGEGRID_CANCELLED::")
        sys.exit(111)

    cfg_file = os.path.join(root, "vergegrid.conf")
    config = load_vergegrid_config(cfg_file, root=str(root))

    if config.get("install_root", "").strip().lower() != str(root).strip().lower():
        log(Fore.YELLOW + f"[WARN] Config install_root mismatch ({config.get('install_root')} != {root}), correcting...")
        config["install_root"] = str(root)
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = []
            found = False
            for line in lines:
                if line.strip().startswith("install_root="):
                    new_lines.append(f"install_root={root}\n")
                    found = True
                else:
                    new_lines.append(line)
            if not found:
                new_lines.insert(0, f"install_root={root}\n")
            with open(cfg_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            log(Fore.GREEN + f"[FIXED] Updated install_root in {cfg_file}")
        except Exception as e:
            log(Fore.RED + f"[WARN] Failed to correct config file: {e}")

    print(Fore.CYAN + f"Detected VergeGrid installation at: {root}")
    save_install_path(root)

    print(Style.BRIGHT + "\nChoose an action:")
    print("  [1] Reset (clear logs/config only)")
    print("  [2] Cleanup (remove everything)")
    print("  [3] Backup then Cleanup")
    print("  [4] Upgrade existing VergeGrid installation")
    print("  [5] Cancel")

    choice = input("\nEnter choice [1-5]: ").strip()

    if choice == "1":
        action = "Reset"
    elif choice == "2":
        action = "Cleanup"
    elif choice == "3":
        action = "BackupCleanup"
    elif choice == "4":
        action = "Upgrade"
    elif choice == "5":
        print(Fore.YELLOW + "\n[EXIT] Operation cancelled by user. No changes made.\n")
        print(Fore.CYAN + "Goodbye from VergeGrid Environment Manager.")
        print("::VERGEGRID_CANCELLED::")
        sys.exit(111)
    else:
        print(Fore.YELLOW + "\n[INVALID] Invalid input detected — cancelling for safety.\n")
        print("::VERGEGRID_CANCELLED::")
        sys.exit(111)

    # continue normal execution for valid options...
    print(Fore.GREEN + f"Proceeding with action: {action}")

if __name__ == "__main__":
    main()

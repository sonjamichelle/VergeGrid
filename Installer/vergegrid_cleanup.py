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

INSTALLER_LOG_DIR = Path(ROOT_DIR) / "Installer_Logs"
INSTALLER_LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = INSTALLER_LOG_DIR / "cleanup.log"
REPORT_PATH = INSTALLER_LOG_DIR / "cleanup_report.json"

SERVICES = ["VergeGridApache", "VergeGridMySQL", "VergeGridOpenSim"]
INSTALL_MARKER = "vergegrid.conf"
SAVE_PATH = Path(r"C:\ProgramData\VergeGrid\install_path.txt")


# ============================================================
# Utilities
# ============================================================

def log(msg, color=None):
    """Log to both console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    with open(LOG_PATH, "a", encoding="utf-8") as logf:
        logf.write(f"{formatted}\n")
    if color:
        print(color + msg + Style.RESET_ALL)
    else:
        print(msg)


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
        log(f"[INFO] Saved system path reference: {path}", Fore.CYAN)
    except Exception as e:
        log(f"[WARN] Could not save install path: {e}", Fore.RED)


def stop_service(name):
    """Attempt to stop a Windows service by name, handling 'not running' gracefully."""
    success, output = run_cmd(["sc", "query", name])
    if not success or "does not exist" in output:
        log(f"[INFO] Service {name} not found.", Fore.YELLOW)
        return

    if "STATE" in output and "STOPPED" in output:
        log(f"[INFO] Service {name} found but already stopped.", Fore.YELLOW)
        return

    if "STATE" in output and "RUNNING" in output:
        log(f"[STOPPING] {name} ...", Fore.YELLOW)
        success, stop_output = run_cmd(["sc", "stop", name])
        if success:
            log(f"[STOPPED] {name}", Fore.GREEN)
        elif "1062" in stop_output:
            log(f"[INFO] Service {name} was not running; no action needed.", Fore.YELLOW)
        else:
            log(f"[WARN] Failed to stop {name}: {stop_output}", Fore.RED)
    else:
        log(f"[INFO] Service {name} is not running or inactive.", Fore.YELLOW)


def unregister_service(name):
    """Attempt to delete a Windows service registration if it exists."""
    success, output = run_cmd(["sc", "query", name])
    if not success or "does not exist" in output:
        log(f"[INFO] Service {name} not found (no unregister needed).", Fore.YELLOW)
        return

    log(f"[REMOVING] Unregistering service {name} ...", Fore.YELLOW)
    success, output = run_cmd(["sc", "delete", name])
    if success:
        log(f"[REMOVED] Service {name} unregistered successfully.", Fore.GREEN)
    else:
        if "marked for deletion" in output.lower():
            log(f"[INFO] Service {name} already marked for deletion (pending reboot).", Fore.CYAN)
        else:
            log(f"[WARN] Failed to unregister {name}: {output}", Fore.RED)


def remove_dir_safe(path: Path):
    """Safely remove a directory if it exists."""
    if not path.exists():
        log(f"[SKIP] {path} not found.", Fore.YELLOW)
        return
    try:
        shutil.rmtree(path, ignore_errors=False)
        log(f"[REMOVED] {path}", Fore.GREEN)
    except Exception as e:
        log(f"[ERROR] Could not remove {path}: {e}", Fore.RED)


def cleanup_shortcuts():
    """Remove VergeGrid Start Menu shortcuts."""
    start_menu = Path(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\VergeGrid")
    if start_menu.exists():
        remove_dir_safe(start_menu)


# ============================================================
# Backup / Reset / Cleanup Core (same logic, updated logging)
# ============================================================

import threading, zipfile, hashlib

def backup_install(root):
    """Create a ZIP backup with progress, retries, and verification."""
    backup_root = Path(f"{root.parent}/VergeGrid_Backups")
    backup_root.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d_%H%M%S")
    backup_file = backup_root / f"VergeGridBackup_{timestamp}.zip"

    log(f"[INFO] Creating backup at {backup_file} ...", Fore.YELLOW)
    time.sleep(0.5)

    all_files = []
    for base, _, files in os.walk(root):
        for f in files:
            all_files.append(os.path.join(base, f))
    total_files = len(all_files)
    processed = 0

    with zipfile.ZipFile(backup_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in all_files:
            rel = os.path.relpath(f, start=root)
            try:
                zf.write(f, rel)
            except Exception as e:
                log(f"[WARN] Failed to add {f}: {e}", Fore.RED)
            processed += 1
            sys.stdout.write(f"\rBacking up... {processed}/{total_files}")
            sys.stdout.flush()

    sys.stdout.write("\n")
    sys.stdout.flush()

    # Verify archive
    log("[INFO] Verifying backup integrity ...", Fore.YELLOW)
    try:
        with zipfile.ZipFile(backup_file, "r") as zf:
            bad = zf.testzip()
            if bad:
                log(f"[ERROR] Corrupt file: {bad}", Fore.RED)
                return None
    except Exception as e:
        log(f"[ERROR] Could not verify backup: {e}", Fore.RED)
        return None

    final_size = backup_file.stat().st_size / (1024 * 1024)
    log(f"[OK] Backup verified successfully ({final_size:.2f} MB)", Fore.GREEN)
    return backup_file


def confirm_dangerous_action():
    print(Style.BRIGHT + Fore.RED + "\nWARNING: This will permanently delete all VergeGrid files and data!")
    confirm = input(Fore.YELLOW + "Type DELETE to confirm, or anything else to cancel: ").strip()
    return confirm.upper() == "DELETE"


# ============================================================
# Core Logic
# ============================================================

def perform_action(action, root):
    report = {"action": action, "root": str(root), "timestamp": time.asctime(), "steps": []}

    # Stop & unregister services before destructive actions
    if action in ("Cleanup", "BackupCleanup", "Upgrade"):
        log("Stopping VergeGrid services...", Fore.YELLOW)
        for svc in SERVICES:
            stop_service(svc)

    if action in ("Cleanup", "BackupCleanup"):
        log("Unregistering VergeGrid services...", Fore.YELLOW)
        for svc in SERVICES:
            unregister_service(svc)

    if action == "BackupCleanup":
        backup_path = backup_install(root)
        if not backup_path:
            log("[ERROR] Backup failed. Aborting cleanup.", Fore.RED)
            report["status"] = "backup_failed"
            return report

    if action in ("Cleanup", "BackupCleanup"):
        if not confirm_dangerous_action():
            log("[CANCELLED] Cleanup aborted by user.", Fore.YELLOW)
            report["status"] = "cancelled"
            return report

        log("Removing VergeGrid directories...", Fore.YELLOW)
        for sub in ["MySQL", "Apache", "OpenSim", "Downloads", "Logs"]:
            remove_dir_safe(root / sub)

        cfg = root / INSTALL_MARKER
        if cfg.exists():
            try:
                cfg.unlink()
                log(f"[REMOVED] {cfg}", Fore.GREEN)
            except Exception as e:
                log(f"[WARN] Failed to delete config: {e}", Fore.RED)

        cleanup_shortcuts()
        report["status"] = "cleaned"

    elif action == "Reset":
        log("Performing reset (clearing logs and configs only)...", Fore.YELLOW)
        remove_dir_safe(root / "Logs")
        remove_dir_safe(root / "Downloads")
        report["status"] = "reset"

    elif action == "Upgrade":
        log("[UPGRADE] Detected existing VergeGrid installation.", Fore.CYAN)
        log("[INFO] Upgrade mode not yet implemented — exiting safely.", Fore.RED)
        report["status"] = "upgrade_placeholder"
        with open(REPORT_PATH, "w", encoding="utf-8") as rf:
            json.dump(report, rf, indent=4)
        sys.exit(0)

    with open(REPORT_PATH, "w", encoding="utf-8") as rf:
        json.dump(report, rf, indent=4)
    return report


def main():
    if platform.system() != "Windows":
        log("This script only runs on Windows.", Fore.RED)
        sys.exit(2)

    if LOG_PATH.exists():
        LOG_PATH.unlink()

    print(Style.BRIGHT + "\n=== VergeGrid Cleanup / Reset / Upgrade Utility ===\n")
    log("=== VergeGrid Cleanup Utility Started ===")

    root = read_saved_path() or find_existing_install()
    if not root or not root.exists():
        log("No existing VergeGrid installation detected.", Fore.YELLOW)
        sys.exit(99)

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
    else:
        log("Operation cancelled by user.", Fore.YELLOW)
        sys.exit(99)

    report = perform_action(action, root)

    print("\n" + Style.BRIGHT + "=" * 60)
    print(Fore.GREEN + "Operation completed.")
    print(Fore.CYAN + f"Detailed log: {LOG_PATH}")
    print(Fore.CYAN + f"JSON report:  {REPORT_PATH}")
    print(Style.BRIGHT + "=" * 60)

    if report.get("status") in ("cleaned", "reset", "upgrade_placeholder"):
        sys.exit(0)
    elif report.get("status") == "cancelled":
        sys.exit(99)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()

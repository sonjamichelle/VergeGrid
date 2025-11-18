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

import os
import sys
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
# Backup / Reset / Cleanup Core
# ============================================================

import threading, zipfile, hashlib, sys

def backup_install(root, retry_count=0, failed_files=None, prev_failed=None):
    """Create a visible-progress ZIP backup with I/O tracking, retry logic, and verification."""
    if failed_files is None:
        failed_files = set()

    ensure_vergegrid_config(str(root))
    conf = load_vergegrid_config(os.path.join(root, "vergegrid.conf"), str(root))
    MAX_RETRIES = conf.get("backup_max_retries", 2)

    try:
        backup_root = Path(f"{root.parent}/VergeGrid_Backups")
        backup_root.mkdir(exist_ok=True)

        timestamp = time.strftime("%Y-%m-%d_%H%M%S")
        backup_file = backup_root / f"VergeGridBackup_{timestamp}.zip"

        log(Fore.YELLOW + f"[INFO] Creating backup at {backup_file} (attempt {retry_count+1}/{MAX_RETRIES})...")
        time.sleep(0.5)

        # ============================================================
        # Collect all files — explicit, config-driven for reliability
        # ============================================================
        config = load_vergegrid_config(os.path.join(root, "vergegrid.conf"), str(root))
        php_root = config.get("PHP_ROOT", os.path.join(root, "Apache", "php"))
        apache_root = config.get("APACHE_ROOT", os.path.join(root, "Apache"))

        # Avoid double inclusion if PHP is already under Apache
        if php_root.lower().startswith(apache_root.lower()):
            php_root = None

        paths_to_backup = [
            config.get("MYSQL_ROOT", os.path.join(root, "MySQL")),
            apache_root,
            config.get("OPEN_SIM_ROOT", os.path.join(root, "OpenSim")),
            os.path.join(root, "Logs"),
            os.path.join(root, "Downloads"),
            os.path.join(root, "vergegrid.conf"),
        ]
        if php_root:
            paths_to_backup.append(php_root)

        # ============================================================
        # Build file list
        # ============================================================
        all_files = []
        for path in paths_to_backup:
            if not os.path.exists(path):
                log(Fore.YELLOW + f"[SKIP] Missing: {path}")
                continue
            if os.path.isfile(path):
                all_files.append(path)
            else:
                for b, _, fs in os.walk(path):
                    for f in fs:
                        all_files.append(os.path.join(b, f))

        total_files = len(all_files)
        if total_files == 0:
            log(Fore.RED + "[FATAL] No valid files or directories found to back up.")
            log(Fore.YELLOW + f"[DEBUG] Check vergegrid.conf and install paths under {root}")
            return None

        spinner = ["|", "/", "-", "\\"]
        spin_idx = 0
        processed = 0
        stop_flag = False
        lock = threading.Lock()

        # --- background live display ---
        def live_status():
            nonlocal spin_idx
            last_size = 0
            last_time = time.time()
            while not stop_flag:
                try:
                    current_size = backup_file.stat().st_size if backup_file.exists() else 0
                    now = time.time()
                    delta = current_size - last_size
                    elapsed = now - last_time
                    rate = (delta / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                    last_size, last_time = current_size, now
                except Exception:
                    rate = 0.0
                with lock:
                    percent = (processed / total_files) * 100 if total_files else 0
                    sys.stdout.write(
                        f"\r{Fore.CYAN}Backing up {spinner[spin_idx]} {processed}/{total_files} "
                        f"({percent:5.1f}%) @ {rate:5.2f} MB/s"
                    )
                    sys.stdout.flush()
                    spin_idx = (spin_idx + 1) % len(spinner)
                time.sleep(0.2)

        status_thread = threading.Thread(target=live_status, daemon=True)
        status_thread.start()

        # --- write zip ---
        with zipfile.ZipFile(backup_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file in all_files:
                arcname = os.path.relpath(file, start=root)
                try:
                    zf.write(file, arcname)
                except Exception as e:
                    log(Fore.RED + f"[WARN] Failed to add {file}: {e}")
                with lock:
                    processed += 1

        stop_flag = True
        status_thread.join(timeout=1)
        sys.stdout.write("\n")
        sys.stdout.flush()

        # ============================================================
        # Verify backup integrity (verbose)
        # ============================================================
        log(Fore.YELLOW + "[INFO] Verifying backup integrity ...")
        try:
            with zipfile.ZipFile(backup_file, "r") as zf:
                total_entries = len(zf.infolist())
                bad_file = zf.testzip()
                if bad_file:
                    log(Fore.RED + f"[CORRUPT] Integrity check failed on: {bad_file}")

                    if bad_file in failed_files:
                        log(Fore.RED + f"[FATAL] Repeated integrity failure on {bad_file}. Aborting backup.")
                        return None
                    failed_files.add(bad_file)

                    # Retry logic
                    if retry_count + 1 < MAX_RETRIES:
                        log(Fore.YELLOW + f"[INFO] Retrying backup (attempt {retry_count+2}/{MAX_RETRIES})...")
                        return backup_install(root, retry_count + 1, failed_files, prev_failed=backup_file)
                    else:
                        log(Fore.RED + f"[FATAL] Backup failed after {MAX_RETRIES} attempts. Possible causes:")
                        log(Fore.RED + " - File(s) in use by a running service or open folder")
                        log(Fore.RED + " - Insufficient permissions")
                        log(Fore.RED + " - Disk I/O or compression error")
                        log(Fore.YELLOW + "Resolve these issues and retry the operation manually.")
                        return None
                else:
                    log(Fore.GREEN + f"[OK] Archive passed integrity test ({total_entries} entries).")
        except Exception as e:
            log(Fore.RED + f"[ERROR] Unable to verify archive: {e}")
            return None

        # ============================================================
        # Passed integrity check
        # ============================================================
        final_size = backup_file.stat().st_size / (1024 * 1024)
        h = hashlib.sha256()
        with open(backup_file, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        sha256sum = h.hexdigest()

        log(Fore.GREEN + f"[DONE] Backup verified successfully: "
                         f"{processed} files ({final_size:.2f} MB total)")
        log(Fore.CYAN + f"[INFO] SHA256: {sha256sum}")
        print(Style.BRIGHT + Fore.GREEN + f"\nBackup complete and verified. File saved to {backup_file}")

        # Add checksum entry to report-style log for reference
        with open(REPORT_PATH, "a", encoding="utf-8") as rf:
            rf.write(f"\nBackupFile={backup_file}\nSHA256={sha256sum}\n")

        # ============================================================
        # Handle previous failed archive cleanup/tagging
        # ============================================================
        if prev_failed and os.path.exists(prev_failed):
            print(Style.BRIGHT + Fore.YELLOW + "\nPrevious backup attempt failed verification:")
            print(Fore.CYAN + f"  {prev_failed}")
            print("Would you like to delete or tag the invalid archive?")
            print("  [D] Delete it now")
            print("  [K] Keep and tag it as INVALID")
            print("  [N] Keep untouched")
            choice = input(Fore.CYAN + "\nEnter choice [D/K/N]: ").strip().upper()

            if choice == "D":
                try:
                    os.remove(prev_failed)
                    log(Fore.GREEN + f"[CLEANUP] Deleted earlier failed backup: {prev_failed}")
                except Exception as e:
                    log(Fore.RED + f"[WARN] Failed to delete invalid backup: {e}")
            elif choice == "K":
                invalid_name = str(prev_failed).replace(".zip", "_INVALID.zip")
                try:
                    os.rename(prev_failed, invalid_name)
                    h = hashlib.sha256()
                    with open(invalid_name, "rb") as f:
                        while chunk := f.read(8192):
                            h.update(chunk)
                    log(Fore.YELLOW + f"[TAGGED] Renamed invalid backup → {invalid_name}")
                    log(Fore.CYAN + f"[INFO] SHA256: {h.hexdigest()}")
                except Exception as e:
                    log(Fore.RED + f"[WARN] Failed to tag invalid archive: {e}")
            else:
                log(Fore.CYAN + f"[KEPT] User chose to keep invalid backup untouched: {prev_failed}")

        return backup_file

    except Exception as e:
        log(Fore.RED + f"[ERROR] Backup failed: {e}")
        return None


def confirm_dangerous_action():
    """Ask user to confirm irreversible deletion."""
    print(Style.BRIGHT + Fore.RED + "\nWARNING: This will permanently delete all VergeGrid files and data!")
    print(Style.BRIGHT + Fore.RED + "This action cannot be undone.\n")
    confirm = input(Fore.YELLOW + "Type DELETE to confirm, or anything else to cancel: ").strip()
    return confirm.upper() == "DELETE"


# ============================================================
# Core Logic
# ============================================================

def perform_action(action, root):
    report = {"action": action, "root": str(root), "timestamp": time.asctime(), "steps": []}

    # Stop & unregister services before destructive or upgrade actions
    if action in ("Cleanup", "BackupCleanup", "Upgrade"):
        log(Style.BRIGHT + Fore.YELLOW + "\nStopping VergeGrid services...")
        for svc in SERVICES:
            stop_service(svc)

    if action in ("Cleanup", "BackupCleanup"):
        log(Style.BRIGHT + Fore.YELLOW + "\nUnregistering VergeGrid services...")
        for svc in SERVICES:
            unregister_service(svc)

    if action == "BackupCleanup":
        backup_path = backup_install(root)
        if not backup_path:
            log(Fore.RED + "[ERROR] Backup failed. Aborting cleanup.")
            report["status"] = "backup_failed"
            return report

    if action in ("Cleanup", "BackupCleanup"):
        if not confirm_dangerous_action():
            log(Fore.YELLOW + "[CANCELLED] Cleanup aborted by user.")
            report["status"] = "cancelled"
            return report

        log(Style.BRIGHT + Fore.YELLOW + "\nRemoving VergeGrid directories...")
        for sub in ["MySQL", "Apache", "OpenSim", "Downloads", "Logs"]:
            remove_dir_safe(root / sub)

        cfg = root / INSTALL_MARKER
        if cfg.exists():
            try:
                cfg.unlink()
                log(Fore.GREEN + f"[REMOVED] {cfg}")
            except Exception as e:
                log(Fore.RED + f"[WARN] Failed to delete config: {e}")

        cleanup_shortcuts()
        report["status"] = "cleaned"

    elif action == "Reset":
        log(Style.BRIGHT + Fore.YELLOW + "\nPerforming reset (clearing logs and configs only)...")
        remove_dir_safe(root / "Logs")
        remove_dir_safe(root / "Downloads")
        report["status"] = "reset"

    elif action == "Upgrade":
        log(Style.BRIGHT + Fore.CYAN + "\n[UPGRADE] Detected existing VergeGrid installation.")
        log(Fore.YELLOW + "Performing version compatibility check (placeholder).")
        log(Fore.YELLOW + "Skipping destructive actions — preserving configs, assets, and databases.")
        log(Fore.CYAN + "Future steps: version diff, schema migration, component patching.")
        log(Fore.RED + "[INFO] Upgrade mode is not yet implemented. Exiting safely to prevent accidental overwrite.")
        report["status"] = "upgrade_placeholder"
        # Immediately terminate execution to avoid destructive reinstallation
        with open(REPORT_PATH, "w", encoding="utf-8") as rf:
            json.dump(report, rf, indent=4)
        log(Fore.CYAN + f"\nReport saved to {REPORT_PATH}")
        print(Style.BRIGHT + Fore.GREEN + "\nUpgrade mode aborted — no files were modified.")
        print(Fore.CYAN + "This is a placeholder; a future version will handle live upgrades safely.")
        sys.exit(0)


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
        sys.exit(99)

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

    if not os.path.exists(cfg_file) or os.path.getsize(cfg_file) == 0:
        log(Fore.RED + f"[CORRUPT] vergegrid.conf missing or empty at {cfg_file}. Regenerating...")
        ensure_vergegrid_config(str(root))
        log(Fore.GREEN + f"[REGEN] Created new configuration at {cfg_file}")

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
        print(Fore.YELLOW + "Operation cancelled by user.")
        sys.exit(99)

    # --------------------------------------------------------
    # Safety Interlock — prompt before destructive actions
    # --------------------------------------------------------
    if action in ("Reset", "Cleanup", "BackupCleanup"):
        print(Style.BRIGHT + Fore.RED + "\nWARNING: You selected a DESTRUCTIVE action.")
        print(Fore.YELLOW + "This may remove your configuration, logs, or data.")
        confirm_upgrade = input(
            Fore.CYAN + "Are you sure you don't mean to UPGRADE the existing installation instead? [y/N]: "
        ).strip().lower()

        if confirm_upgrade in ("y", "yes"):
            print(Fore.CYAN + "[INFO] Switching to upgrade mode instead of destructive cleanup.")
            action = "Upgrade"
        elif confirm_upgrade in ("n", "", "no"):
            print(Fore.GREEN + "[SAFE] Continuing with chosen action.")
        else:
            print(Fore.YELLOW + "[CANCELLED] Operation aborted by user.")
            sys.exit(99)

    # Execute chosen action
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

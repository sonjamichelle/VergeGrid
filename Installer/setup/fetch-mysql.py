# -*- coding: utf-8 -*-
"""
VergeGrid Modular Component Installer: MySQL
Author: Sonja + GPT
Purpose:
  - Download and extract MySQL distribution
  - Initialize and configure MySQL service via init-mysql
  - Create Start Menu shortcuts
  - Write all logs to ./Installer_Logs/fetch-mysql.log
"""

# --- VergeGrid Path Fix ---
import os
import sys
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

import time
import subprocess
import importlib.util
from datetime import datetime
from colorama import Fore, Style, init
init(autoreset=True, strip=False, convert=True)

# ------------------------------------------------------------
# Import shared helpers and init-mysql (path-safe)
# ------------------------------------------------------------
try:
    from setup import common
except ModuleNotFoundError:
    import common

# Dynamically load init-mysql.py
init_mysql_path = os.path.join(os.path.dirname(__file__), "init-mysql.py")
spec = importlib.util.spec_from_file_location("init_mysql", init_mysql_path)
init_mysql = importlib.util.module_from_spec(spec)
spec.loader.exec_module(init_mysql)

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
URLS = {
    "mysql": "https://cdn.mysql.com/Downloads/MySQL-8.4/mysql-8.4.6-winx64.zip",
}
URLS_FALLBACK = {
    "mysql": "https://downloads.mysql.com/archives/get/p/23/file/mysql-8.4.6-winx64.zip",
}

# ------------------------------------------------------------
# Centralized Installer_Logs Directory
# ------------------------------------------------------------
INSTALLER_LOG_DIR = Path(ROOT_DIR) / "Installer_Logs"
INSTALLER_LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = INSTALLER_LOG_DIR / "fetch-mysql.log"

def log(msg, color=None):
    """Write to console and Installer_Logs/fetch-mysql.log."""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    formatted = f"{timestamp} {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass
    if color:
        print(color + msg + Style.RESET_ALL)
    else:
        print(msg)


# ------------------------------------------------------------
# MySQL Installer Logic
# ------------------------------------------------------------
def install_mysql(install_root):
    """
    Downloads, extracts, and initializes VergeGrid MySQL.
    Called as: python setup/fetch-mysql.py [install_root]
    """
    install_root = Path(install_root).resolve()
    downloads_root = install_root / "Downloads"
    target = install_root / "MySQL"
    zip_path = downloads_root / "mysql.zip"

    os.makedirs(downloads_root, exist_ok=True)
    os.makedirs(target, exist_ok=True)

    log("=== Fetch-MySQL Script Starting ===", Fore.CYAN)
    log(f"Install root: {install_root}")
    log(f"Target directory: {target}")
    log(f"Log file: {LOG_FILE}")

    try:
        # 1. Download MySQL archive
        log(">>> Downloading MySQL distribution...", Fore.YELLOW)
        common.download_file(URLS["mysql"], str(zip_path), fallback_url=URLS_FALLBACK["mysql"])
        log(f"[OK] MySQL package downloaded to {zip_path}", Fore.GREEN)

        # 2. Extract MySQL
        log(">>> Extracting MySQL package...", Fore.YELLOW)
        common.extract_archive(str(zip_path), str(target))
        common.flatten_extracted_dir(str(target), expected="mysql-8.4.6-winx64")
        log(f"[OK] MySQL extracted to {target}", Fore.GREEN)

        # --- Fix nested MySQL directories automatically ---
        nested = target / "MySQL"
        if nested.exists() and (nested / "bin" / "mysqld.exe").exists():
            log(f"[FIX] Detected nested MySQL directory: {nested}", Fore.YELLOW)
            for item in nested.iterdir():
                dest = target / item.name
                if not dest.exists():
                    log(f"Moving {item} → {dest}")
                    item.rename(dest)
            import shutil
            shutil.rmtree(nested, ignore_errors=True)
            log(f"[FIX] Corrected nested MySQL structure in {target}", Fore.GREEN)

        # 3. Initialize MySQL (via init-mysql)
        log(">>> Initializing MySQL service and data directory...", Fore.YELLOW)
        sys.stdout.flush()

        log("Initializing MySQL (secure mode)...", Fore.CYAN)
        ok = init_mysql.setup_mysql(target)

        if not ok:
            log("[FATAL] init-mysql returned failure. Aborting.", Fore.RED)
            print("[FATAL] MySQL setup failed.")
            sys.exit(2)

        log("MySQL temporary password parsed successfully.", Fore.GREEN)

        # 4. Create Start Menu shortcuts
        log(">>> Creating MySQL service shortcuts...", Fore.YELLOW)
        common.create_shortcut("Start VergeGrid MySQL", "sc start VergeGridMySQL")
        common.create_shortcut("Stop VergeGrid MySQL", "sc stop VergeGridMySQL")
        common.create_shortcut("Restart VergeGrid MySQL", "sc stop VergeGridMySQL && sc start VergeGridMySQL")
        log("[OK] Service shortcuts created successfully.", Fore.GREEN)

        # 5. Done
        log(f"MySQL installed successfully in {target}", Fore.GREEN)
        print(Style.BRIGHT + Fore.GREEN + "✓ VergeGrid MySQL installation completed.\n")
        sys.exit(0)

    except Exception as e:
        import traceback
        traceback.print_exc()
        log(f"[FATAL] Exception during MySQL install: {e}", Fore.RED)
        print(Fore.RED + "\n[FATAL] MySQL installation failed. See logs for details.")
        sys.exit(1)


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch-mysql.py <install_root>")
        sys.exit(1)
    install_mysql(sys.argv[1])

# -*- coding: utf-8 -*-
"""
VergeGrid Modular Component Installer: MySQL
Author: Sonja + GPT
Purpose:
  - Download and extract MySQL distribution
  - Initialize and configure MySQL service via init-mysql
  - Create Start Menu shortcuts
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
from colorama import Fore, Style, init
init(autoreset=True, strip=False, convert=True)


# ------------------------------------------------------------
# Import shared helpers and init-mysql (path-safe)
# ------------------------------------------------------------
try:
    from setup import common
except ModuleNotFoundError:
    import common

# Force-load init-mysql.py dynamically
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
# MySQL Installer Logic
# ------------------------------------------------------------
def install_mysql(install_root):
    """
    Downloads, extracts, and initializes VergeGrid MySQL.
    Called as: python setup/fetch-mysql.py [install_root]
    """

    install_root = Path(install_root).resolve()
    downloads_root = install_root / "Downloads"
    logs_root = install_root / "Logs"

    os.makedirs(downloads_root, exist_ok=True)
    os.makedirs(logs_root, exist_ok=True)

    log_file = logs_root / "vergegrid-install.log"
    common.set_log_file(str(log_file))
    common.write_log("=== Fetch-MySQL Script Starting ===")

    target = install_root / "MySQL"
    zip_path = downloads_root / "mysql.zip"

    try:
        # 1. Download MySQL archive
        print("\n>>> Downloading MySQL distribution...")
        common.download_file(URLS["mysql"], str(zip_path), fallback_url=URLS_FALLBACK["mysql"])

        # 2. Extract MySQL
        print("\n>>> Extracting MySQL package...")
        common.extract_archive(str(zip_path), str(target))
        common.flatten_extracted_dir(str(target), expected="mysql-8.4.6-winx64")

        # --- Fix nested MySQL directories automatically ---
        nested = target / "MySQL"
        if nested.exists() and (nested / "bin" / "mysqld.exe").exists():
            print(f"[FIX] Detected nested MySQL directory: {nested}")
            for item in nested.iterdir():
                dest = target / item.name
                if not dest.exists():
                    common.write_log(f"Moving {item} → {dest}")
                    item.rename(dest)
            import shutil
            shutil.rmtree(nested, ignore_errors=True)
            common.write_log(f"[FIX] Corrected nested MySQL structure in {target}")

        # 3. Initialize MySQL (via init-mysql)
        print("\n>>> Initializing MySQL service and data directory...")
        sys.stdout.flush()

        # Run secure init process
        common.write_log("Initializing MySQL (secure mode, temporary password will be generated)...")
        ok = init_mysql.setup_mysql(target)

        # Add detailed log handoff
        common.write_log("MySQL temporary password parsed successfully, proceeding with secure root password configuration.")

        if not ok:
            common.write_log("[FATAL] init-mysql returned failure. Aborting.", "ERROR")
            print("[FATAL] MySQL setup failed.")
            sys.exit(2)

        # 4. Create Start Menu shortcuts
        print("\n>>> Creating service shortcuts...")
        common.create_shortcut("Start VergeGrid MySQL", "sc start VergeGridMySQL")
        common.create_shortcut("Stop VergeGrid MySQL", "sc stop VergeGridMySQL")
        common.create_shortcut("Restart VergeGrid MySQL", "sc stop VergeGridMySQL && sc start VergeGridMySQL")

        # 5. Done
        common.write_log(f"MySQL installed successfully in {target}")
        print("✓ VergeGrid MySQL installation completed.\n")
        sys.exit(0)

    except Exception as e:
        import traceback
        traceback.print_exc()
        common.write_log(f"[FATAL] Exception during MySQL install: {e}", "ERROR")
        print("\n[FATAL] MySQL installation failed. See logs for details.")
        sys.exit(1)


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch-mysql.py <install_root>")
        sys.exit(1)
    install_mysql(sys.argv[1])

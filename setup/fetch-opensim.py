# -*- coding: utf-8 -*-
"""
VergeGrid Modular Component Installer: OpenSim (Insecure Mode)
Author: Sonja + GPT
Purpose:
  - Download and extract OpenSimulator distribution
  - Call init-opensim.py for DB setup and configuration
  - Create Start Menu shortcut
  - Run headless with no user input (root / no password)
"""

# --- VergeGrid Path Fix ---
import os
import sys

# Find VergeGrid root (one level up from /setup/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

import subprocess
import time
from colorama import Fore, Style, init
from pathlib import Path
init(autoreset=True, strip=False, convert=True)

# ------------------------------------------------------------
# Import shared helpers
# ------------------------------------------------------------
try:
    from setup import common
except ModuleNotFoundError:
    import common


# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
URLS = {
    "opensim": "http://opensimulator.org/dist/opensim-0.9.3.0.zip",
}
URLS_FALLBACK = {
    "opensim": "https://download.4dgrid.net/mirror/opensim/opensim-latest-stable.zip",
}


# ------------------------------------------------------------
# OpenSim Fetcher Logic
# ------------------------------------------------------------
def install_opensim(install_root, mysql_user="root", mysql_pass=""):
    """
    Downloads, extracts, and prepares VergeGrid OpenSim.
    Then runs init-opensim.py to create DBs and patch configs.
    Runs fully non-interactive in insecure mode (root / no password).
    """

    install_root = Path(install_root).resolve()
    downloads_root = install_root / "Downloads"
    logs_root = install_root / "Logs"
    opensim_root = install_root / "OpenSim"

    os.makedirs(downloads_root, exist_ok=True)
    os.makedirs(logs_root, exist_ok=True)
    os.makedirs(opensim_root, exist_ok=True)

    log_file = logs_root / "vergegrid-install.log"
    common.set_log_file(str(log_file))
    common.write_log("=== Fetch-OpenSim Script Starting ===")

    zip_path = downloads_root / "opensim.zip"

    try:
        # 1. Download OpenSim archive
        print("\n>>> Downloading OpenSim distribution...")
        common.download_file(
            URLS["opensim"], str(zip_path), fallback_url=URLS_FALLBACK["opensim"]
        )

        # 2. Extract archive
        print("\n>>> Extracting OpenSim package...")
        common.extract_archive(str(zip_path), str(opensim_root))
        common.flatten_extracted_dir(str(opensim_root), expected="opensim")

        # 3. Run initialization (DB + config)
        print("\n>>> Running OpenSim initialization script (insecure mode)...")
        init_script = Path(__file__).parent / "init-opensim.py"

        if not init_script.exists():
            raise FileNotFoundError(f"init-opensim.py not found in {init_script.parent}")

        result = subprocess.run(
            [sys.executable, str(init_script), str(install_root), mysql_user, mysql_pass],
            capture_output=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"OpenSim initialization failed (exit code {result.returncode})"
            )

        # 4. Create Start Menu shortcut
        exe_path = opensim_root / "bin" / "OpenSim.exe"
        if exe_path.exists():
            print("\n>>> Creating shortcut for OpenSim launcher...")
            cmd = f'start "" "{exe_path}"'
            common.create_shortcut("Run OpenSim", cmd)
        else:
            common.write_log(f"[WARN] OpenSim.exe not found at {exe_path}", "WARN")

        # 5. Done
        common.write_log(f"OpenSim installed successfully in {opensim_root}")
        print("✓ VergeGrid OpenSim installation completed.\n")
        sys.exit(0)

    except Exception as e:
        import traceback
        traceback.print_exc()
        common.write_log(f"[FATAL] Exception during OpenSim install: {e}", "ERROR")
        print("\n[FATAL] OpenSim installation failed. See logs for details.")
        sys.exit(1)


# ------------------------------------------------------------
# Entry point (non-interactive)
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch-opensim.py <install_root>")
        sys.exit(1)

    install_root = sys.argv[1]
    # Force insecure mode defaults (no prompts)
    mysql_user = "root"
    mysql_pass = ""
    print("[INFO] Using default MySQL credentials (root / no password, insecure mode).")

    install_opensim(install_root, mysql_user, mysql_pass)

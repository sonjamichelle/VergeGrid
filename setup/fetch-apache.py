# -*- coding: utf-8 -*-
"""
VergeGrid Modular Component Installer: Apache
Author: Sonja + GPT
Purpose:
  - Download and extract Apache
  - Register Apache service (VergeGridApache)
  - Create Start Menu shortcuts for service control
"""
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
import subprocess
import time
from pathlib import Path

try:
    from setup import common
except ModuleNotFoundError:
    import common


# ------------------------------------------------------------
# Component URLs
# ------------------------------------------------------------
URLS = {
    "apache": "https://www.apachelounge.com/download/VS17/binaries/httpd-2.4.65-250724-Win64-VS17.zip",
}
URLS_FALLBACK = {
    "apache": "https://dlcdn.apachehaus.com/downloads/httpd-2.4.65-o111p-x64-vs17.zip",
}


# ------------------------------------------------------------
# Core Install Function
# ------------------------------------------------------------
def install_apache(install_root):
    install_root = Path(install_root).resolve()
    downloads_root = install_root / "Downloads"
    logs_root = install_root / "Logs"
    apache_root = install_root / "Apache"

    os.makedirs(apache_root, exist_ok=True)
    os.makedirs(downloads_root, exist_ok=True)
    os.makedirs(logs_root, exist_ok=True)

    log_file = logs_root / "vergegrid-install.log"
    common.set_log_file(str(log_file))
    common.write_log("=== Fetch-Apache Script Starting ===")

    zip_apache = downloads_root / "apache.zip"

    try:
        # --------------------------------------------------------
        # 1. Download Apache
        # --------------------------------------------------------
        print("\n>>> Downloading Apache web server...")
        common.download_file(URLS["apache"], str(zip_apache), fallback_url=URLS_FALLBACK["apache"])

        # --------------------------------------------------------
        # 2. Extract Archive
        # --------------------------------------------------------
        print("\n>>> Extracting Apache package...")
        common.extract_archive(str(zip_apache), str(apache_root))
        common.flatten_extracted_dir(str(apache_root), expected="Apache24")

        # --------------------------------------------------------
        # 3. Register Apache Service
        # --------------------------------------------------------
        print("\n>>> Registering VergeGrid Apache service...")
        service_name = "VergeGridApache"
        binpath = f'"{apache_root}\\bin\\httpd.exe" -k runservice'
        common.write_log(f"Creating Windows service: {service_name} -> {binpath}")

        subprocess.run(
            ["sc", "create", service_name, f"binPath= {binpath}", f"DisplayName= VergeGrid Apache", "start=", "auto"],
            capture_output=True,
            text=True,
        )
        subprocess.run(["sc", "description", service_name, "Apache Web Server for VergeGrid"], capture_output=True)

        # --------------------------------------------------------
        # 4. Create Shortcuts
        # --------------------------------------------------------
        print("\n>>> Creating service control shortcuts...")
        common.create_shortcut("Start VergeGrid Apache", "sc start VergeGridApache")
        common.create_shortcut("Stop VergeGrid Apache", "sc stop VergeGridApache")
        common.create_shortcut("Restart VergeGrid Apache", "sc stop VergeGridApache && sc start VergeGridApache")

        # --------------------------------------------------------
        # 5. Done
        # --------------------------------------------------------
        common.write_log(f"Apache installed at {apache_root}")
        print("\n✓ VergeGrid Apache installation completed successfully.\n")
        sys.exit(0)

    except Exception as e:
        import traceback
        traceback.print_exc()
        common.write_log(f"[FATAL] Apache installation failed: {e}", "ERROR")
        print("\n[FATAL] Apache installation failed. See logs for details.")
        sys.exit(1)


# ------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch-apache.py <install_root>")
        sys.exit(1)

    install_root = sys.argv[1]
    install_apache(install_root)

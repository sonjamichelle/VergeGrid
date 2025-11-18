# -*- coding: utf-8 -*-
"""
VergeGrid Modular Component Fetcher: Let's Encrypt (win-acme)
Author: Sonja + GPT
Purpose:
  - Download and install win-acme (Windows ACME client)
  - Prepare VergeGrid for SSL certificate issuance and renewal
  - Create Start Menu shortcuts for management
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
import zipfile
import shutil
import subprocess
from pathlib import Path

try:
    from setup import common
except ModuleNotFoundError:
    import common


# ------------------------------------------------------------
# Download URLs
# ------------------------------------------------------------
URLS = {
    "winacme": "https://github.com/win-acme/win-acme/releases/download/v2.2.9.1701/win-acme.v2.2.9.1701.x64.pluggable.zip"
}

URLS_FALLBACK = {
    "winacme": "https://github.com/win-acme/win-acme/releases/download/v2.2.9.1701/win-acme.v2.2.9.1701.x64.trimmed.zip"
}


# ------------------------------------------------------------
# Core Installer Function
# ------------------------------------------------------------
def install_letsencrypt(install_root):
    """
    Installs win-acme client into VergeGrid environment.
    """
    install_root = Path(install_root).resolve()
    downloads_root = install_root / "Downloads"
    logs_root = install_root / "Logs"
    target_root = install_root / "LetsEncrypt"

    os.makedirs(downloads_root, exist_ok=True)
    os.makedirs(logs_root, exist_ok=True)
    os.makedirs(target_root, exist_ok=True)

    log_file = logs_root / "vergegrid-install.log"
    common.set_log_file(str(log_file))
    common.write_log("=== Fetch-LetsEncrypt Script Starting ===")

    zip_path = downloads_root / "win-acme.zip"

    # --------------------------------------------------------
    # 1. Download
    # --------------------------------------------------------
    print("\n>>> Downloading win-acme (Let's Encrypt client)...")
    try:
        common.download_file(URLS["winacme"], str(zip_path), fallback_url=URLS_FALLBACK["winacme"])
    except Exception as e:
        common.write_log(f"[FATAL] Failed to download win-acme: {e}", "ERROR")
        print("[ERROR] Download failed. Check network or URLs.")
        sys.exit(1)

    # --------------------------------------------------------
    # 2. Extract
    # --------------------------------------------------------
    print("\n>>> Extracting win-acme client...")
    common.extract_archive(str(zip_path), str(target_root))
    common.flatten_extracted_dir(str(target_root))
    common.write_log(f"[OK] Extracted win-acme to {target_root}")

    # --------------------------------------------------------
    # 3. Create Start Menu Shortcut
    # --------------------------------------------------------
    print("\n>>> Creating Start Menu shortcuts...")
    exe_path = target_root / "wacs.exe"
    if exe_path.exists():
        common.create_shortcut("VergeGrid Let's Encrypt (win-acme)",
                               f'start "" "{exe_path}" --baseuri https://acme-v02.api.letsencrypt.org/')
        common.write_log(f"[OK] Created shortcut for win-acme at {exe_path}")
    else:
        common.write_log("[WARN] wacs.exe missing after extraction.", "WARN")

    # --------------------------------------------------------
    # 4. Optional: Precreate configuration folder for renewals
    # --------------------------------------------------------
    conf_dir = target_root / "config"
    os.makedirs(conf_dir, exist_ok=True)
    common.write_log(f"[INFO] Created config directory at {conf_dir}")

    # --------------------------------------------------------
    # 5. Done
    # --------------------------------------------------------
    print("\n✓ VergeGrid Let's Encrypt (win-acme) installed successfully.\n")
    print("To request a new SSL certificate, run:")
    print(f"  \"{exe_path}\" --target manual --host yourdomain.com --store pemfiles --pemfilespath \"{install_root}\\Apache\\conf\\ssl\"")
    print("\nCertificates will be stored in:")
    print(f"  {conf_dir}")
    print("\nTo configure Apache SSL, edit your httpd.conf and point SSLCertificateFile to the generated .crt/.key files.\n")

    common.write_log("[SUCCESS] win-acme installation completed successfully.")
    sys.exit(0)


# ------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch-letsencrypt.py <install_root>")
        sys.exit(1)

    try:
        install_letsencrypt(sys.argv[1])
    except Exception as e:
        import traceback

        traceback.print_exc()
        common.write_log(f"[FATAL] Let's Encrypt installation failed: {e}", "ERROR")
        print(f"[FATAL] Let's Encrypt installation failed: {e}")
        sys.exit(1)

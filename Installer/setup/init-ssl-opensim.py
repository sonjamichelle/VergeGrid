# -*- coding: utf-8 -*-
"""
VergeGrid Optional SSL Initializer for OpenSim
Author: Sonja + GPT
Purpose:
  - Enable native SSL in Robust and OpenSim configurations
  - Apply Let's Encrypt certificates (from VergeGrid\LetsEncrypt)
  - Update grid URLs to https:// where applicable
"""

# --- VergeGrid Path Fix ---
import os, sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

# --- Dependency check ---
try:
    import pymysql
except ImportError:
    import subprocess
    print("[INFO] Missing dependency: PyMySQL. Installing automatically...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pymysql"], check=True)
    import pymysql
# --- End dependency check ---

import shutil
from pathlib import Path
import time

try:
    from setup import common
except ModuleNotFoundError:
    import common


# ------------------------------------------------------------
# Utility Helpers
# ------------------------------------------------------------
def patch_ini_file(path: Path, cert_path: Path, key_path: Path):
    """Adds or updates SSL directives in a .ini file."""
    marker_start = "; --- VergeGrid SSL Configuration ---"
    marker_end = "; --- End VergeGrid SSL Configuration ---"

    lines_to_insert = [
        marker_start,
        "UseSSL = true",
        f'CertificateFile = "{cert_path}"',
        f'CertificateKeyFile = "{key_path}"',
        marker_end,
        "",
    ]

    if not path.exists():
        common.write_log(f"[WARN] {path} not found, skipping SSL patch.")
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.readlines()

    # Remove old VergeGrid SSL block if it exists
    start_idx = end_idx = None
    for i, line in enumerate(content):
        if marker_start in line:
            start_idx = i
        if marker_end in line:
            end_idx = i
            break

    if start_idx is not None and end_idx is not None:
        del content[start_idx:end_idx + 1]

    # Append SSL block at the end
    content.append("\n")
    for l in lines_to_insert:
        content.append(l + "\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(content)

    common.write_log(f"[OK] Added SSL configuration block to {path}")
    return True


def find_certs(letsencrypt_root: Path, opensim_root: Path):
    """Find valid certificate and key files from Let's Encrypt or OpenSim."""
    cert_file = None
    key_file = None

    search_paths = [
        letsencrypt_root / "config",
        letsencrypt_root,
        opensim_root / "ssl",
    ]

    for p in search_paths:
        if not p.exists():
            continue
        for ext in ("*.pem", "*.crt", "*.cer"):
            matches = list(p.glob(ext))
            if matches and not cert_file:
                cert_file = matches[0]
        if not key_file:
            keys = list(p.glob("*.key"))
            if keys:
                key_file = keys[0]
        if cert_file and key_file:
            break

    return cert_file, key_file


# ------------------------------------------------------------
# Main Logic
# ------------------------------------------------------------
def init_ssl_opensim(install_root: Path):
    """Apply Let's Encrypt SSL configuration to OpenSim and Robust."""
    install_root = Path(install_root).resolve()
    os.environ["VERGEGRID_INSTALL_ROOT"] = str(install_root)

    logs_root = install_root / "Logs"
    opensim_root = install_root / "OpenSim"
    robust_root = install_root / "OpenSim" / "bin"
    letsencrypt_root = install_root / "LetsEncrypt"

    os.makedirs(logs_root, exist_ok=True)
    log_file = logs_root / "vergegrid-install.log"
    common.set_log_file(str(log_file))
    common.write_log("=== OpenSim SSL Initialization Starting ===")

    print("\n>>> Detecting Let's Encrypt certificates...")
    cert_file, key_file = find_certs(letsencrypt_root, opensim_root)
    if not cert_file or not key_file:
        raise FileNotFoundError(
            f"No valid SSL certificate/key found.\n"
            f"Check {letsencrypt_root} or {opensim_root}\\ssl."
        )

    print(f"Using certificate: {cert_file}")
    print(f"Using key:         {key_file}")
    common.write_log(f"[INFO] Using cert: {cert_file}")
    common.write_log(f"[INFO] Using key:  {key_file}")

    # --------------------------------------------------------
    # Patch Robust configs
    # --------------------------------------------------------
    print("\n>>> Patching Robust configuration files...")
    for ini_name in ("Robust.ini", "Robust.HG.ini"):
        ini_path = robust_root / ini_name
        if ini_path.exists():
            patch_ini_file(ini_path, cert_file, key_file)
        else:
            common.write_log(f"[WARN] {ini_name} not found. Skipping.")

    # --------------------------------------------------------
    # Patch OpenSim.ini
    # --------------------------------------------------------
    print("\n>>> Patching OpenSim.ini...")
    opensim_ini = opensim_root / "bin" / "OpenSim.ini"
    if opensim_ini.exists():
        patch_ini_file(opensim_ini, cert_file, key_file)
    else:
        common.write_log("[WARN] OpenSim.ini not found. Skipping region patch.")

    # --------------------------------------------------------
    # Optional: Patch GridCommon.ini for https:// URLs
    # --------------------------------------------------------
    grid_common_ini = robust_root / "GridCommon.ini"
    if grid_common_ini.exists():
        common.write_log("[INFO] Updating service URLs to https:// where applicable.")
        with open(grid_common_ini, "r", encoding="utf-8") as f:
            lines = f.readlines()
        updated = []
        for line in lines:
            if "http://" in line and "localhost" not in line:
                updated.append(line.replace("http://", "https://"))
            else:
                updated.append(line)
        with open(grid_common_ini, "w", encoding="utf-8") as f:
            f.writelines(updated)

    # --------------------------------------------------------
    # Done
    # --------------------------------------------------------
    print("\n✓ OpenSim SSL initialization complete.")
    print("Robust and simulator configs updated to use HTTPS.\n")
    print("You may now restart your Robust and region services to apply SSL.")
    common.write_log("[SUCCESS] OpenSim SSL initialization complete.")
    return 0


# ------------------------------------------------------------
# Entry Point (Dynamic)
# ------------------------------------------------------------
if __name__ == "__main__":
    print("\n=== VergeGrid OpenSim SSL Initializer (Dynamic Mode) ===")
    if len(sys.argv) < 2:
        print("Usage: python init-ssl-opensim.py <install_root>")
        sys.exit(1)

    install_root = Path(sys.argv[1])
    try:
        sys.exit(init_ssl_opensim(install_root))
    except Exception as e:
        import traceback
        traceback.print_exc()
        common.write_log(f"[FATAL] OpenSim SSL initialization failed: {e}", "ERROR")
        print(f"[FATAL] OpenSim SSL initialization failed: {e}")
        sys.exit(1)

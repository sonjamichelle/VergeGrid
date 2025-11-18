# -*- coding: utf-8 -*-
"""
VergeGrid Optional SSL Initializer for Apache (via win-acme)
Author: Sonja + GPT
Purpose:
  - Configure Apache to use Let's Encrypt certificates
  - Enable mod_ssl if available
  - Create or patch SSL configuration block in httpd.conf
  - Verify service restart and log completion
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
import shutil
import time
import subprocess
from pathlib import Path

try:
    from setup import common
except ModuleNotFoundError:
    import common


# ------------------------------------------------------------
# Utility Helpers
# ------------------------------------------------------------
def find_httpd_conf(apache_root: Path) -> Path:
    conf_path = apache_root / "conf" / "httpd.conf"
    if conf_path.exists():
        return conf_path
    raise FileNotFoundError(f"httpd.conf not found under {apache_root}")


def append_if_missing(conf_file: Path, marker: str, lines_to_add: list):
    """Append configuration lines if marker not found."""
    with open(conf_file, "r", encoding="utf-8") as f:
        content = f.read()

    if marker in content:
        common.write_log(f"[INFO] Marker '{marker}' already present. Skipping append.")
        return

    with open(conf_file, "a", encoding="utf-8") as f:
        f.write("\n\n# --- VergeGrid SSL Configuration ---\n")
        for line in lines_to_add:
            f.write(line + "\n")
        f.write("# --- End VergeGrid SSL Configuration ---\n\n")

    common.write_log(f"[OK] Added SSL configuration block to {conf_file}")


def restart_apache_service():
    """Restart Apache service cleanly."""
    print("\n>>> Restarting Apache service to apply SSL config...")
    subprocess.run(["sc", "stop", "VergeGridApache"], capture_output=True, text=True)
    time.sleep(3)
    subprocess.run(["sc", "start", "VergeGridApache"], capture_output=True, text=True)
    time.sleep(2)
    print("[OK] Apache service restarted.")
    common.write_log("[OK] Apache service restarted after SSL config.")


# ------------------------------------------------------------
# Core Function
# ------------------------------------------------------------
def init_ssl_apache(install_root):
    install_root = Path(install_root).resolve()
    apache_root = install_root / "Apache"
    letsencrypt_root = install_root / "LetsEncrypt"
    logs_root = install_root / "Logs"

    os.makedirs(logs_root, exist_ok=True)
    log_file = logs_root / "vergegrid-install.log"
    common.set_log_file(str(log_file))
    common.write_log("=== Apache SSL Initialization Starting ===")

    # --------------------------------------------------------
    # Verify prerequisites
    # --------------------------------------------------------
    print("\n>>> Checking Apache and Let's Encrypt installation...")
    if not apache_root.exists():
        raise FileNotFoundError(f"Apache not found at {apache_root}")
    if not letsencrypt_root.exists():
        raise FileNotFoundError(f"Let's Encrypt not found at {letsencrypt_root}")

    httpd_conf = find_httpd_conf(apache_root)
    common.write_log(f"[INFO] Located Apache config: {httpd_conf}")

    ssl_conf_path = apache_root / "conf" / "extra" / "httpd-ssl.conf"
    ssl_dir = apache_root / "conf" / "ssl"
    os.makedirs(ssl_dir, exist_ok=True)

    # --------------------------------------------------------
    # Attempt to detect issued certificates
    # --------------------------------------------------------
    print("\n>>> Searching for existing certificates...")
    cert_file = None
    key_file = None

    # Search VergeGrid\LetsEncrypt\config and VergeGrid\Apache\conf\ssl
    for path in [letsencrypt_root, ssl_dir]:
        pem_files = list(path.glob("*.pem")) + list(path.glob("*.crt")) + list(path.glob("*.cer"))
        key_files = list(path.glob("*.key"))
        if pem_files:
            cert_file = pem_files[0]
        if key_files:
            key_file = key_files[0]
        if cert_file and key_file:
            break

    if not cert_file or not key_file:
        raise FileNotFoundError(
            f"No SSL certificate/key pair found.\n"
            f"Expected PEM/CRT and KEY files under:\n"
            f"  {ssl_dir}\n  {letsencrypt_root}\n"
            "Run win-acme first to issue certificates."
        )

    common.write_log(f"[INFO] Using certificate: {cert_file}")
    common.write_log(f"[INFO] Using private key: {key_file}")

    # --------------------------------------------------------
    # Patch Apache config
    # --------------------------------------------------------
    print("\n>>> Patching Apache SSL configuration...")
    ssl_lines = [
        "LoadModule ssl_module modules/mod_ssl.so",
        "Listen 443",
        f"<VirtualHost *:443>",
        f"    DocumentRoot \"{apache_root / 'htdocs'}\"",
        f"    ServerName localhost",
        f"    SSLEngine on",
        f"    SSLCertificateFile \"{cert_file}\"",
        f"    SSLCertificateKeyFile \"{key_file}\"",
        f"    ErrorLog \"logs/ssl_error.log\"",
        f"    CustomLog \"logs/ssl_access.log\" combined",
        "</VirtualHost>",
    ]

    append_if_missing(httpd_conf, "VergeGrid SSL Configuration", ssl_lines)

    # --------------------------------------------------------
    # Restart Apache
    # --------------------------------------------------------
    restart_apache_service()

    print("\n✓ Apache SSL configuration complete.")
    print("Visit: https://localhost/  (ignore self-signed warnings if testing)\n")
    common.write_log("[SUCCESS] Apache SSL configuration completed successfully.")


# ------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python init-ssl-apache.py <install_root>")
        sys.exit(1)

    try:
        init_ssl_apache(sys.argv[1])
        print("\n✓ Apache SSL initialization successful.\n")
        sys.exit(0)
    except Exception as e:
        import traceback

        traceback.print_exc()
        common.write_log(f"[FATAL] Apache SSL initialization failed: {e}", "ERROR")
        print(f"\n[FATAL] Apache SSL initialization failed: {e}\n")
        sys.exit(1)

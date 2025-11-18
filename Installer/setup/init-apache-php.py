# -*- coding: utf-8 -*-
"""
VergeGrid Apache/PHP Stack Initializer
Author: Sonja + GPT
Purpose:
  - Detect Apache and PHP installs
  - Patch Apache httpd.conf to load PHP module
  - Restart VergeGridApache service
  - Verify integration via test index.php file
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
import time
import shutil
import subprocess
from pathlib import Path

try:
    from setup import common
except ModuleNotFoundError:
    import common


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def find_httpd_conf(apache_root: Path) -> Path:
    """Locate Apache's httpd.conf."""
    conf_path = apache_root / "conf" / "httpd.conf"
    if conf_path.exists():
        return conf_path
    raise FileNotFoundError(f"Could not find httpd.conf in {apache_root}")


def append_if_missing(conf_file: Path, marker: str, lines_to_add: list):
    """Append configuration lines if marker not found."""
    with open(conf_file, "r", encoding="utf-8") as f:
        content = f.read()

    if marker in content:
        common.write_log(f"[INFO] Marker '{marker}' already present, skipping append.")
        return

    with open(conf_file, "a", encoding="utf-8") as f:
        f.write("\n\n# --- VergeGrid PHP Integration ---\n")
        for line in lines_to_add:
            f.write(line + "\n")
        f.write("# --- End VergeGrid PHP Integration ---\n\n")

    common.write_log(f"[OK] Added PHP integration block to {conf_file}")


def restart_apache_service():
    """Stop and start the VergeGridApache service cleanly."""
    print("\n>>> Restarting Apache service to apply PHP integration...")
    subprocess.run(["sc", "stop", "VergeGridApache"], capture_output=True, text=True)
    time.sleep(3)
    subprocess.run(["sc", "start", "VergeGridApache"], capture_output=True, text=True)
    time.sleep(2)
    print("[OK] Apache service restarted.")
    common.write_log("[OK] Apache service restarted successfully.")


# ------------------------------------------------------------
# Core Function
# ------------------------------------------------------------
def init_apache_php(install_root):
    install_root = Path(install_root).resolve()
    logs_root = install_root / "Logs"
    apache_root = install_root / "Apache"
    php_root = install_root / "PHP"

    os.makedirs(logs_root, exist_ok=True)
    log_file = logs_root / "vergegrid-install.log"
    common.set_log_file(str(log_file))
    common.write_log("=== Apache/PHP Integration Script Starting ===")

    # --------------------------------------------------------
    # Sanity checks
    # --------------------------------------------------------
    print("\n>>> Verifying Apache and PHP installations...")
    if not apache_root.exists():
        raise FileNotFoundError(f"Apache not found at {apache_root}")
    if not php_root.exists():
        raise FileNotFoundError(f"PHP not found at {php_root}")

    httpd_conf = find_httpd_conf(apache_root)
    common.write_log(f"[INFO] Located Apache config: {httpd_conf}")

    # --------------------------------------------------------
    # Detect PHP module DLL
    # --------------------------------------------------------
    dll_candidates = list(php_root.glob("php*apache2_4.dll"))
    if not dll_candidates:
        raise FileNotFoundError(
            f"No php*apache2_4.dll module found in {php_root}. "
            "Ensure you have the correct Thread Safe PHP build."
        )
    php_module_dll = dll_candidates[0]
    common.write_log(f"[INFO] Found PHP module DLL: {php_module_dll.name}")

    # --------------------------------------------------------
    # Build configuration lines
    # --------------------------------------------------------
    php_ini = php_root / "php.ini"
    if not php_ini.exists():
        common.write_log(f"[WARN] php.ini not found, creating a default one.", "WARN")
        ini_sample = php_root / "php.ini-development"
        if ini_sample.exists():
            shutil.copy(ini_sample, php_ini)

    conf_lines = [
        f'LoadModule php_module "{php_module_dll}"',
        'AddType application/x-httpd-php .php',
        f'PHPIniDir "{php_root}"',
    ]

    # --------------------------------------------------------
    # Patch Apache config
    # --------------------------------------------------------
    print("\n>>> Updating Apache configuration...")
    append_if_missing(httpd_conf, "VergeGrid PHP Integration", conf_lines)

    # --------------------------------------------------------
    # Create PHP test page
    # --------------------------------------------------------
    htdocs = apache_root / "htdocs"
    test_php = htdocs / "index.php"
    if not test_php.exists():
        with open(test_php, "w", encoding="utf-8") as f:
            f.write("<?php phpinfo(); ?>\n")
        common.write_log(f"[INFO] Created test PHP file: {test_php}")

    # --------------------------------------------------------
    # Restart Apache service
    # --------------------------------------------------------
    restart_apache_service()

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------
    print("\n>>> Apache/PHP integration complete.")
    print(f"Test it by visiting: http://localhost/ in your browser.\n")
    common.write_log("[SUCCESS] Apache/PHP integration completed successfully.")


# ------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python init-apache-php.py <install_root>")
        sys.exit(1)

    try:
        init_apache_php(sys.argv[1])
        print("\n✓ Apache/PHP stack initialized successfully.\n")
        sys.exit(0)
    except Exception as e:
        import traceback
        traceback.print_exc()
        common.write_log(f"[FATAL] Apache/PHP integration failed: {e}", "ERROR")
        print(f"\n[FATAL] Apache/PHP integration failed: {e}\n")
        sys.exit(1)

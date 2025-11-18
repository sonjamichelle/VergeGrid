# -*- coding: utf-8 -*-
"""
VergeGrid Modular Windows Installer (Python Edition)
Author: Sonja + GPT
Purpose:
  - Top-level orchestrator for modular installers
  - User-driven drive selection
  - Calls per-component fetchers (MySQL, OpenSim, Apache, PHP, LetsEncrypt)
  - Handles sequencing and error management
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
import ctypes
from pathlib import Path  # ✅ FIXED: Global import to avoid UnboundLocalError

try:
    from setup import common
except ModuleNotFoundError:
    import common

# --------------------------------------------------------------------
# Auto-install psutil if missing
# --------------------------------------------------------------------
try:
    import psutil
except ImportError:
    print("[INFO] Missing dependency: psutil. Installing automatically...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil"], check=True)
    import psutil


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def confirm(prompt, default_yes=True):
    while True:
        d = "[Y/n]" if default_yes else "[y/N]"
        res = input(f"{prompt} {d} ").strip().lower()
        if not res:
            return default_yes
        if res in ("y", "yes"):
            return True
        if res in ("n", "no"):
            return False


def select_install_drive():
    print("\nVergeGrid Installer - Drive Selection\n")
    drives = [d.device for d in psutil.disk_partitions(all=False)]
    for d in drives:
        try:
            usage = psutil.disk_usage(d)
            print(f"  {d} - {usage.free / (1024**3):.2f} GB free")
        except PermissionError:
            pass
    choice = input("Enter drive letter for installation (default C): ").strip().upper()
    if not choice:
        choice = "C"
    if not choice.endswith(":"):
        choice += ":"
    path = os.path.join(choice + "\\", "VergeGrid")
    print(f"Installation path set to: {path}")
    if not confirm("Confirm installation path?"):
        sys.exit(0)
    return path


def ensure_admin():
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        is_admin = False

    if not is_admin:
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{a}"' for a in sys.argv[1:]])
        print("[INFO] Restarting with admin privileges...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)
    else:
        print("[OK] Admin privileges confirmed.")


# --------------------------------------------------------------------
# Component Runner
# --------------------------------------------------------------------
def run_component(script_name, *args, title=None):
    """
    Calls a modular component (fetcher) script via subprocess.
    Logs output, exit code, and checks for failure.
    """
    if title:
        print(f"\n>>> Running {title} ...")
        print("=" * 70)
    script_path = Path("setup") / script_name
    if not script_path.exists():
        print(f"[ERROR] Missing component: {script_path}")
        common.write_log(f"[ERROR] Missing component: {script_path}")
        return False

    cmd = [sys.executable, str(script_path)] + list(args)
    result = subprocess.run(cmd)

    exit_code = result.returncode
    status = "SUCCESS" if exit_code == 0 else "FAIL"

    # Log and print results
    print(f"\n[{status}] {title or script_name} exited with code {exit_code}\n")
    common.write_log(f"[{status}] {title or script_name} exited with code {exit_code}")

    if exit_code != 0:
        print(f"[FAIL] {title or script_name} failed (exit code {exit_code}).")
        print("Check VergeGrid logs for details.")
        return False

    print(f"[OK] {title or script_name} completed successfully.\n")
    return True


# --------------------------------------------------------------------
# MAIN INSTALLER LOGIC
# --------------------------------------------------------------------
def main():
    print("\n=== VergeGrid Modular Installer ===")
    print("Author: Sonja + GPT")
    print("Version: Modular Installer Build 2025-11\n")

    install_root = select_install_drive()
    downloads_root = Path(install_root) / "Downloads"
    logs_root = Path(install_root) / "Logs"

    os.makedirs(downloads_root, exist_ok=True)
    os.makedirs(logs_root, exist_ok=True)

    # Setup unified log for all components
    log_file = logs_root / "vergegrid-install.log"
    common.set_log_file(str(log_file))
    common.write_log("=== VergeGrid Modular Installer Started ===")

    ensure_admin()

    print("\nConfiguration:")
    print(f"  Install Root:  {install_root}")
    print(f"  Logs:          {log_file}")
    print(f"  Downloads:     {downloads_root}\n")

    installed = []

    # ============================================================
    # STEP 1: MySQL
    # ============================================================
    if confirm("Install MySQL?"):
        if run_component("fetch-mysql.py", install_root, title="MySQL Installer"):
            installed.append(("MySQL", install_root))
        else:
            sys.exit(1)

    # ============================================================
    # STEP 2: Apache (Fetch + Extract Only)
    # ============================================================
    if confirm("Fetch Apache Web Server?"):
        if run_component("fetch-apache.py", install_root, title="Apache Fetcher"):
            installed.append(("Apache", install_root))
        else:
            print("[WARN] Apache install skipped or failed.")

    # ============================================================
    # STEP 3: PHP (Fetch + Extract Only)
    # ============================================================
    if confirm("Fetch PHP Interpreter?"):
        if run_component("fetch-php.py", install_root, title="PHP Fetcher"):
            installed.append(("PHP", install_root))
        else:
            print("[WARN] PHP install skipped or failed.")

    # ============================================================
    # STEP 4: Apache/PHP Integration
    # ============================================================
    if confirm("Initialize Apache/PHP Integration?"):
        if run_component("init-apache-php.py", install_root, title="Apache/PHP Integration"):
            installed.append(("Apache-PHP Stack", install_root))
        else:
            print("[WARN] Apache/PHP integration skipped or failed.")

    # ============================================================
    # STEP 5: Let’s Encrypt (Windows ACME)
    # ============================================================
    if confirm("Install Let's Encrypt (Windows ACME) Support?"):
        if run_component("fetch-letsencrypt.py", install_root, title="Let's Encrypt Installer"):
            installed.append(("LetsEncrypt", install_root))
        else:
            print("[WARN] Let's Encrypt install skipped or failed.")

    # ============================================================
    # STEP 6: OpenSim (Final Step)
    # ============================================================
    if confirm("Install OpenSim?"):
        mysql_user = input("MySQL Username [root] JUST PRESS ENTER!: ").strip() or "root"
        mysql_pass = input("MySQL Password [blank] JUST PRESS ENTER!: ").strip()

        if run_component("fetch-opensim.py", install_root, mysql_user, mysql_pass, title="OpenSim Fetcher"):
            installed.append(("OpenSim", install_root))

            # Initialize OpenSim (creates DBs + patches INIs)
            if run_component("init-opensim.py", install_root, mysql_user, mysql_pass, title="OpenSim Initializer"):
                common.write_log("[OK] OpenSim base configuration completed successfully.", "INFO")
            else:
                common.write_log("[FATAL] OpenSim initialization failed.", "ERROR")
                sys.exit(1)

            # SAFETY CHECK: Verify config files exist
            opensim_root = Path(install_root) / "OpenSim" / "bin"
            gridcommon = opensim_root / "config-include" / "GridCommon.ini"
            robust_ini = opensim_root / "Robust.ini"

            print("\n[INFO] Verifying patched configuration files before Robust registration...")
            time.sleep(5)
            if not gridcommon.exists() or gridcommon.stat().st_size < 200:
                print("[FATAL] GridCommon.ini missing or invalid. Cannot continue.")
                sys.exit(3)
            if not robust_ini.exists() or robust_ini.stat().st_size < 100:
                print("[FATAL] Robust.ini missing or invalid. Cannot continue.")
                sys.exit(3)
            print("✓ Configuration validation passed. Proceeding to Robust setup.\n")

            # STEP 6.1: Register Robust Service (manual start only)
            if run_component("init-opensim-services.py", install_root, title="OpenSim Robust Service Registration"):
                common.write_log("[OK] Robust service registered successfully (manual start).", "INFO")
                installed.append(("Robust Service", install_root))
            else:
                print("[FATAL] Robust service registration failed. Aborting installation.")
                sys.exit(1)

            print("\n[OK] OpenSim + Robust registration completed successfully.\n")

        else:
            sys.exit(1)

    # ============================================================
    # FINAL SUMMARY
    # ============================================================
    print("\n" + "=" * 70)
    print(" VergeGrid Installation Summary")
    print("=" * 70)
    if installed:
        for name, path in installed:
            print(f"  {name:<20} -> {path}")
    else:
        print("  No components were installed.")
    print("-" * 70)
    print(f"  Logs saved to:  {log_file}")
    print("  Shortcuts:      C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\VergeGrid")
    print("=" * 70)
    print("\nInstallation complete. You may close this window or launch services via Start Menu.\n")


# --------------------------------------------------------------------
if __name__ == "__main__":
    main()

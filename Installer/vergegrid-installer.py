# -*- coding: utf-8 -*-
"""
VergeGrid Modular Windows Installer (Python Edition)
Author: Sonja + GPT
Purpose:
  - Top-level orchestrator for modular installers
  - User-driven drive selection
  - Calls per-component fetchers (MySQL, OpenSim, Apache, PHP, LetsEncrypt)
  - Handles sequencing and error management
  - Auto-generates OpenSim.ini, GridCommon.ini, and GridHypergrid.ini
"""

# --- VergeGrid Path Fix ---
import os
import sys
import re
import shutil
import subprocess
import time
import ctypes
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

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
    """Prompt user to select an installation drive and custom folder name."""
    print("\nVergeGrid Installer - Drive Selection\n")

    drives = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.device)
            drives.append((part.device, usage.free / (1024**3)))
        except PermissionError:
            continue

    if not drives:
        print("[FATAL] No accessible drives found. Cannot continue.")
        sys.exit(1)

    print("Available drives:")
    for idx, (drive, free_gb) in enumerate(drives, 1):
        print(f"  {idx}. {drive:<5} - {free_gb:>7.2f} GB free")

    while True:
        choice = input(f"\nSelect target drive [1-{len(drives)}] (default 1): ").strip()
        if not choice:
            choice = "1"
        if choice.isdigit() and 1 <= int(choice) <= len(drives):
            selected_drive = drives[int(choice) - 1][0]
            break
        else:
            print(f"[WARN] Invalid selection. Enter a number between 1 and {len(drives)}.")

    folder_name = input("Enter installation folder name (default VergeGrid): ").strip()
    if not folder_name:
        folder_name = "VergeGrid"

    install_path = os.path.join(selected_drive, folder_name)
    print(f"\nInstallation path set to: {install_path}")

    if not confirm("Create and use this path?"):
        print("[CANCELLED] Installation aborted by user.")
        sys.exit(0)

    os.makedirs(os.path.join(install_path, "Downloads"), exist_ok=True)
    os.makedirs(os.path.join(install_path, "Logs"), exist_ok=True)
    print(f"[OK] Created installation directories under {install_path}")

    return install_path


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
    """Calls a modular component (fetcher) script via subprocess."""
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

    print(f"\n[{status}] {title or script_name} exited with code {exit_code}\n")
    common.write_log(f"[{status}] {title or script_name} exited with code {exit_code}")

    if exit_code != 0:
        print(f"[FAIL] {title or script_name} failed (exit code {exit_code}).")
        print("Check VergeGrid logs for details.")
        return False

    print(f"[OK] {title or script_name} completed successfully.\n")
    return True


# --------------------------------------------------------------------
# Ensure OpenSim.ini, GridCommon.ini, and GridHypergrid.ini
# --------------------------------------------------------------------
def ensure_opensim_ini(install_root):
    """Ensure OpenSim.ini and config-include files exist and are patched correctly."""
    print("\n[INFO] Verifying OpenSim.ini and include files...")

    opensim_bin = os.path.join(install_root, "OpenSim", "bin")
    ini_example = os.path.join(opensim_bin, "OpenSim.ini.example")
    ini_file = os.path.join(opensim_bin, "OpenSim.ini")

    include_dir = os.path.join(opensim_bin, "config-include")
    os.makedirs(include_dir, exist_ok=True)

    gridcommon_ex = os.path.join(include_dir, "GridCommon.ini.example")
    gridcommon_ini = os.path.join(include_dir, "GridCommon.ini")
    hg_ex = os.path.join(include_dir, "GridHypergrid.ini.example")
    hg_ini = os.path.join(include_dir, "GridHypergrid.ini")

    if not os.path.exists(ini_file) and os.path.exists(ini_example):
        shutil.copy(ini_example, ini_file)
        print("[OK] Created OpenSim.ini from example.")
    if not os.path.exists(gridcommon_ini) and os.path.exists(gridcommon_ex):
        shutil.copy(gridcommon_ex, gridcommon_ini)
        print("[OK] Created GridCommon.ini from example.")
    if not os.path.exists(hg_ini) and os.path.exists(hg_ex):
        shutil.copy(hg_ex, hg_ini)
        print("[OK] Created GridHypergrid.ini from example.")

    if not os.path.exists(ini_file):
        print("[FATAL] OpenSim.ini missing and no example available.")
        return False

    with open(ini_file, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(
        r"^\s*;?\s*(Include-Common\s*=\s*\"config-include/GridCommon.ini\")",
        r"\1", content, flags=re.MULTILINE)
    content = re.sub(
        r"^\s*;?\s*(Include-HG\s*=\s*\"config-include/GridHypergrid.ini\")",
        r"\1", content, flags=re.MULTILINE)

    if "[SimulationDataStore]" not in content:
        content += "\n\n[SimulationDataStore]\nStorageProvider = \"OpenSim.Data.Null.dll\"\n"

    if "regionload_regionsdir" not in content:
        content = re.sub(
            r"(\[Startup\][^\[]*)",
            r"\1\nregionload_regionsdir = \"./Regions\"",
            content,
            flags=re.DOTALL
        )

    with open(ini_file, "w", encoding="utf-8") as f:
        f.write(content)

    print("[OK] Verified OpenSim.ini includes GridCommon and Hypergrid references.")
    print("[OK] SimulationDataStore and region directory configured.\n")
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

    setup_dir = Path(__file__).resolve().parent / "setup"
    setup_dir.mkdir(exist_ok=True)
    install_path_file = setup_dir / "install_path.txt"
    with open(install_path_file, "w", encoding="utf-8") as f:
        f.write(install_root)
    print(f"[OK] Saved install path to {install_path_file}")

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
    # STEP 1–5: MySQL → Let's Encrypt (AUTO MODE)
    # ============================================================
    print("\n[INFO] Installing MySQL automatically...\n")
    if run_component("fetch-mysql.py", install_root, title="MySQL Installer"):
        installed.append(("MySQL", install_root))
    else:
        sys.exit(1)

    print("\n[INFO] Fetching Apache Web Server automatically...\n")
    if run_component("fetch-apache.py", install_root, title="Apache Fetcher"):
        installed.append(("Apache", install_root))
    else:
        print("[WARN] Apache install skipped or failed.")

    print("\n[INFO] Fetching PHP Interpreter automatically...\n")
    if run_component("fetch-php.py", install_root, title="PHP Fetcher"):
        installed.append(("PHP", install_root))
    else:
        print("[WARN] PHP install skipped or failed.")

    print("\n[INFO] Initializing Apache/PHP integration automatically...\n")
    if run_component("init-apache-php.py", install_root, title="Apache/PHP Integration"):
        installed.append(("Apache-PHP Stack", install_root))
    else:
        print("[WARN] Apache/PHP integration skipped or failed.")

    print("\n[INFO] Installing Let's Encrypt (Windows ACME) support automatically...\n")
    if run_component("fetch-letsencrypt.py", install_root, title="Let's Encrypt Installer"):
        installed.append(("LetsEncrypt", install_root))
    else:
        print("[WARN] Let's Encrypt install skipped or failed.")

    # ============================================================
    # STEP 6: OpenSim (AUTO MODE)
    # ============================================================
    print("\n[INFO] Installing OpenSim automatically...\n")
    mysql_user = "root"
    mysql_pass = ""

    if run_component("fetch-opensim.py", install_root, mysql_user, mysql_pass, title="OpenSim Fetcher"):
        installed.append(("OpenSim", install_root))

        if not ensure_opensim_ini(install_root):
            print("[FATAL] Failed to verify or create OpenSim.ini and include files. Aborting installation.")
            sys.exit(1)

        if run_component("init-opensim.py", install_root, mysql_user, mysql_pass, title="OpenSim Initializer"):
            common.write_log("[OK] OpenSim base configuration completed successfully.", "INFO")
        else:
            common.write_log("[FATAL] OpenSim initialization failed.", "ERROR")
            sys.exit(1)

        if not run_component("verify-db-robust.py", install_root, title="Robust Database Verifier"):
            print("[FATAL] Robust verification failed — manual inspection required.")
            common.write_log("[FATAL] Robust verification failed.", "ERROR")
            sys.exit(1)
        else:
            installed.append(("Robust Verification", install_root))
            print("[OK] Robust verification completed successfully.\n")
    else:
        sys.exit(1)

    # ============================================================
    # STEP 7: Secure MySQL Root User (AUTO MODE)
    # ============================================================
    print("\n[INFO] Securing MySQL root user automatically...\n")
    if run_component("secure_mysql_root.py", install_root, title="MySQL Root Security Setup"):
        installed.append(("MySQL Security", install_root))
        common.write_log("[OK] MySQL root password secured successfully.", "INFO")
    else:
        print("[FATAL] MySQL security setup failed. Aborting installation.")
        common.write_log("[FATAL] MySQL security setup failed.", "ERROR")
        sys.exit(1)

    # ============================================================
    # STEP 8: Create VergeGrid God User (AUTO MODE)
    # ============================================================
    print("\n[INFO] Creating VergeGrid God user automatically...\n")
    if run_component("create_god_user_db.py", install_root, title="VergeGrid God User Creator"):
        installed.append(("God User", install_root))
        common.write_log("[OK] VergeGrid God user created successfully.", "INFO")
    else:
        print("[FATAL] God user creation failed. Aborting installation.")
        common.write_log("[FATAL] God user creation failed.", "ERROR")
        sys.exit(1)

    # ============================================================
    # STEP 9: Initialize Default Landing Estate & First Region (AUTO MODE)
    # ============================================================
    print("\n[INFO] Launching VergeGrid Region Creator (Automated create-region.py)...\n")

    region_script = os.path.join(setup_dir, "create-region.py")

    cmd = [sys.executable, region_script]

    result = subprocess.run(cmd, cwd=setup_dir, text=True)
    if result.returncode == 0:
        print("[OK] Region initialization completed successfully.\n")
        common.write_log("[OK] Region initialization completed successfully.", "INFO")
    else:
        print("[FATAL] Region creation failed during Landing Estate setup.")
        common.write_log("[FATAL] Region creation failed during Landing Estate setup.", "ERROR")
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
# ENTRY POINT
# --------------------------------------------------------------------
if __name__ == "__main__":
    main()

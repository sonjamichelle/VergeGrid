# -*- coding: utf-8 -*-
"""
VergeGrid Modular Windows Installer (Fully Automated Edition)
Author: Sonja + GPT
Purpose:
  - Fully automated top-level orchestrator for VergeGrid installers
  - Single confirmation for install path
  - Automatically installs MySQL, Apache, PHP, OpenSim, and dependencies
  - Handles sequencing, logging, and error management
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
    """Simple yes/no confirmation."""
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
    """Prompt user to select installation drive and folder."""
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
    """Ensure the installer is running as Administrator."""
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


def run_component(script_name, *args, title=None):
    """Run a modular component script via subprocess."""
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

    if exit_code != 0:
        print(f"[FAIL] {title or script_name} failed (exit code {exit_code}).")
        common.write_log(f"[FAIL] {title or script_name} failed (exit code {exit_code})", "ERROR")
        sys.exit(exit_code)

    print(f"[OK] {title or script_name} completed successfully.\n")
    common.write_log(f"[OK] {title or script_name} completed successfully.", "INFO")
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
        sys.exit(1)

    with open(ini_file, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(
        r"^\s*;?\s*(Include-Common\s*=\s*\"config-include/GridCommon.ini\")",
        r"\1", content, flags=re.MULTILINE)
    content = re.sub(
        r"^\s*;?\s*(Include-HG\s*=\s*\"config-include/GridHypergrid.ini\")",
        r"\1", content, flags=re.MULTILINE)

    if "[SimulationDataStore]" not in content:
        content += (
            "\n\n[SimulationDataStore]\n"
            "StorageProvider = \"OpenSim.Data.MySQL.dll\"\n"
            "ConnectionString = \"Data Source=localhost;Database=opensim;"
            "User ID=opensim;Password=opensim;Old Guids=true;\"\n"
        )

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
    print("Version: Fully Automated Build 2025-11\n")

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
    common.write_log("=== VergeGrid Fully Automated Installer Started ===")

    ensure_admin()
    installed = []

    print("\n>>> [STEP 1] Installing Core Components (MySQL → Apache → PHP → OpenSim)")
    print("=" * 70)

    run_component("fetch-mysql.py", install_root, title="MySQL Installer")
    run_component("fetch-apache.py", install_root, title="Apache Fetcher")
    run_component("fetch-php.py", install_root, title="PHP Fetcher")
    run_component("init-apache-php.py", install_root, title="Apache/PHP Integration")
    run_component("fetch-letsencrypt.py", install_root, title="Let's Encrypt Installer")

    print("\n>>> [STEP 2] Installing and Configuring OpenSim")
    print("=" * 70)

    mysql_user, mysql_pass = "root", ""
    run_component("fetch-opensim.py", install_root, mysql_user, mysql_pass, title="OpenSim Fetcher")

    if not ensure_opensim_ini(install_root):
        sys.exit(1)

    run_component("init-opensim.py", install_root, mysql_user, mysql_pass, title="OpenSim Initializer")
    run_component("init-core.py", install_root, title="Core OpenSim Configuration")
    run_component("verify-db-robust.py", install_root, title="Robust Database Verifier")

    print("\n>>> [STEP 3] Securing MySQL and Configuring Grid User")
    print("=" * 70)
    run_component("secure_mysql_root.py", install_root, title="MySQL Root Security Setup")
    run_component("create_god_user_db.py", install_root, title="VergeGrid God User Creator")

    print("\n>>> [STEP 4] Initializing Default Landing Region")
    print("=" * 70)
    run_component("init-landing.py", install_root, title="Landing Estate Initializer")

    print("\nAll automated installation steps completed successfully.")
    print("You can now manually launch OpenSim if desired:")
    print(r"   OpenSim.exe -inifile=Regions\Landings\Landings.ini\n")

    print("\n" + "=" * 70)
    print(" VergeGrid Automated Installation Summary")
    print("=" * 70)
    print(f"  Install Root:  {install_root}")
    print(f"  Logs:          {log_file}")
    print("-" * 70)
    print("  Status:        ✅ All steps completed without user interaction.")
    print("  Next:          Launch OpenSim to verify Moonlight Landing region.")
    print("=" * 70)
    print("\nInstallation complete.\n")


# --------------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------------
if __name__ == "__main__":
    main()

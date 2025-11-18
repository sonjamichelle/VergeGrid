# -*- coding: utf-8 -*-
"""
VergeGrid Windows Installer (Python Edition)
Author: Sonja + GPT
Purpose:
  - User-driven drive selection
  - Dependency checks
  - MySQL, OpenSim, Apache/PHP, Workbench, Python installs
  - Service registration via sc.exe
  - Optional autostart & Start Menu shortcuts
"""

import os
import sys
import ctypes
import subprocess
import shutil
import zipfile
import urllib.request
import tempfile
import time
import platform
from pathlib import Path

# --------------------------------------------------------------------
# FIXED IMPORT HANDLING FOR db_setup
# --------------------------------------------------------------------
try:
    from setup import db_setup
except ModuleNotFoundError:
    import db_setup

from vergegrid_common import (
    load_vergegrid_config,
    ensure_vergegrid_config,
    save_install_path,
    read_saved_path,
    find_existing_install
)

# --------------------------------------------------------------------
# Auto-install psutil if missing
# --------------------------------------------------------------------
try:
    import psutil
except ImportError:
    print("[INFO] Missing dependency: psutil. Installing automatically...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil"], check=True)
    import psutil

# --------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------
def write_log(msg, level="INFO"):
    global INSTALL_LOG
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} [{level}] {msg}"
    print(line)
    if INSTALL_LOG:
        with open(INSTALL_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")

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

def validated_choice(prompt, options):
    options = [o.upper() for o in options]
    while True:
        res = input(f"{prompt} [{'/'.join(options)}]: ").strip().upper()
        if res in options:
            return res

def download_file(url, dest):
    import ssl
    import time
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    write_log(f"Downloading {os.path.basename(dest)} from {url}")

    comp_name = next((k for k, v in URLS.items() if v.lower() == url.lower()), None)
    try:
        if "opensimulator.org" in url.lower():
            write_log("Using OpenSim official source with forced TLS bypass.")
            context = ssl._create_unverified_context()
        else:
            context = None

        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': 'https://dev.mysql.com/downloads/',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )

        spinner = ['|', '/', '-', '\\']
        spin_index = 0
        bar_length = 50
        block_size = 8192

        with urllib.request.urlopen(req, context=context) as response, open(dest, "wb") as f:
            total_size = int(response.info().get("Content-Length", -1))
            downloaded = 0
            start_time = time.time()

            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if total_size > 0:
                    percent = downloaded / total_size
                    filled = int(bar_length * percent)
                    bar = ">" * filled + "=" * (bar_length - filled)
                    spin_char = spinner[spin_index % len(spinner)]
                    spin_index += 1

                    elapsed = max(time.time() - start_time, 0.1)
                    speed = downloaded / (1024 * 1024 * elapsed)
                    sys.stdout.write(
                        f"\r {spin_char} [{bar}] {int(percent * 100):3d}%  {speed:6.2f} MB/s"
                    )
                    sys.stdout.flush()

            total_elapsed = max(time.time() - start_time, 0.1)
            avg_speed = downloaded / (1024 * 1024 * total_elapsed)
            sys.stdout.write(
                f"\r ✓ [>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>] 100%  {avg_speed:6.2f} MB/s - done\n"
            )
            sys.stdout.flush()

        size = os.path.getsize(dest)
        if size < 1000000:
            raise RuntimeError(f"Download too small ({size} bytes) — may be invalid.")

        write_log(f"Downloaded {dest}")

    except Exception as e:
        write_log(f"Primary download failed ({e}).", "WARN")

        if comp_name and comp_name in URLS_FALLBACK:
            mirror = URLS_FALLBACK[comp_name]
            write_log(f"Attempting fallback mirror: {mirror}")
            try:
                download_file(mirror, dest)
                return
            except Exception as inner:
                write_log(f"Mirror fallback failed ({inner}), using PowerShell fallback.", "WARN")

        write_log("Trying PowerShell fallback...", "WARN")
        ps_cmd = [
            "powershell", "-Command",
            f"[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;"
            f"$ProgressPreference='SilentlyContinue';"
            f"Invoke-WebRequest -Uri '{url}' -OutFile '{dest}' -UseBasicParsing"
        ]
        result = subprocess.run(ps_cmd, capture_output=True, text=True)
        if os.path.exists(dest) and os.path.getsize(dest) > 1000000:
            write_log("PowerShell fallback succeeded.")
        else:
            write_log(f"PowerShell fallback failed: {result.stderr}", "ERROR")
            raise RuntimeError("Download failed after PowerShell fallback.")

def extract_archive(src, dest):
    sevenzip = shutil.which("7z") or shutil.which("7z.exe")
    if sevenzip:
        write_log(f"Extracting {src} to {dest} using 7-Zip")
        subprocess.run([sevenzip, "x", "-y", f"-o{dest}", src], check=True)
    else:
        write_log(f"Extracting {src} to {dest} using Python zipfile")
        with zipfile.ZipFile(src, "r") as zf:
            zf.extractall(dest)

def flatten_extracted_dir(dest, expected=None):
    entries = [e for e in os.listdir(dest) if os.path.isdir(os.path.join(dest, e))]
    if not entries:
        return
    if expected and expected in entries:
        sub = os.path.join(dest, expected)
    elif len(entries) == 1:
        sub = os.path.join(dest, entries[0])
    else:
        return
    try:
        for item in os.listdir(sub):
            shutil.move(os.path.join(sub, item), os.path.join(dest, item))
        shutil.rmtree(sub, ignore_errors=True)
        write_log(f"Flattened extracted folder structure in {dest}")
    except Exception as e:
        write_log(f"Failed to flatten {dest}: {e}", "WARN")

def run_sc_create(name, binpath, display, description):
    try:
        subprocess.run([
            "sc", "create", name,
            f"binPath= {binpath}",
            f"DisplayName= {display}",
            "start=", "demand"
        ], check=False, capture_output=True)
        subprocess.run(["sc", "description", name, description], check=False)
        write_log(f"Service {name} registered.")
    except Exception as e:
        write_log(f"Failed to create service {name}: {e}", "ERROR")

def create_shortcut(name, cmd):
    start_dir = os.path.join(os.environ["ProgramData"], r"Microsoft\Windows\Start Menu\Programs\VergeGrid")
    os.makedirs(start_dir, exist_ok=True)
    lnk_path = os.path.join(start_dir, f"{name}.bat")
    with open(lnk_path, "w", encoding="utf-8") as f:
        f.write(f"@echo off\n{cmd}\npause\n")
    write_log(f"Created shortcut: {lnk_path}")

# --------------------------------------------------------------------
# System Prep
# --------------------------------------------------------------------
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
        write_log("Restarting with admin privileges...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)
    else:
        write_log("Admin privileges confirmed.")

# --------------------------------------------------------------------
# Component Installation
# --------------------------------------------------------------------
URLS = {
    "mysql": "https://cdn.mysql.com/Downloads/MySQL-8.4/mysql-8.4.6-winx64.zip",
    "workbench": "https://cdn.mysql.com/Downloads/MySQLGUITools/mysql-workbench-community-8.0.36-winx64.msi",
    "apache": "https://www.apachelounge.com/download/VS17/binaries/httpd-2.4.65-250724-Win64-VS17.zip",
    "php": "https://windows.php.net/downloads/releases/php-8.4.14-Win32-vs17-x64.zip",
    "python": "https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe",
    "opensim": "http://opensimulator.org/dist/opensim-0.9.3.0.zip",
}

URLS_FALLBACK = {
    "mysql": "https://downloads.mysql.com/archives/get/p/23/file/mysql-8.4.6-winx64.zip",
    "apache": "https://dlcdn.apachehaus.com/downloads/httpd-2.4.65-o111p-x64-vs17.zip",
    "opensim": "https://download.4dgrid.net/mirror/opensim/opensim-latest-stable.zip",
    "workbench": "https://mirror.dl.sourceforge.net/project/mysql-workbench/mysql-workbench-community-8.0.36-winx64.msi",
}

# --------------------------------------------------------------------
# MySQL Installation
# --------------------------------------------------------------------
def install_mysql(target_root, downloads_root):
    target = Path(target_root)
    os.makedirs(target, exist_ok=True)
    os.makedirs(target / "Downloads", exist_ok=True)
    zip_path = target / "Downloads" / "mysql.zip"

    print("\n>>> Downloading and unpacking MySQL distribution...")
    write_log("Starting MySQL package download and extraction.")
    download_file(URLS["mysql"], str(zip_path))
    extract_archive(str(zip_path), str(target))
    flatten_extracted_dir(str(target), expected="mysql-8.4.6-winx64")

    print("\n>>> Initializing database engine and services...")
    sys.stdout.flush()
    write_log("Beginning MySQL service configuration and initialization.")

    success = db_setup.setup_mysql(target)
    if not success:
        write_log("[FATAL] MySQL setup failed. Aborting installation.", "ERROR")
        print("\n[FATAL] MySQL setup failed. Check logs for details.")
        sys.exit(2)

    print("\n>>> Creating VergeGrid MySQL service shortcuts...")
    create_shortcut("Start VergeGrid MySQL", "sc start VergeGridMySQL")
    create_shortcut("Stop VergeGrid MySQL", "sc stop VergeGridMySQL")
    create_shortcut("Restart VergeGrid MySQL", "sc stop VergeGridMySQL && sc start VergeGridMySQL")

    write_log(f"MySQL installed and configured successfully at {target}")
    print("✓ VergeGrid MySQL installation completed.\n")

# --------------------------------------------------------------------
# Apache + PHP Installation
# --------------------------------------------------------------------
def install_apache_php(apache_root, php_root, downloads_root):
    os.makedirs(apache_root, exist_ok=True)
    os.makedirs(php_root, exist_ok=True)
    zip_apache = os.path.join(downloads_root, "apache.zip")
    zip_php = os.path.join(downloads_root, "php.zip")

    download_file(URLS["apache"], zip_apache)
    extract_archive(zip_apache, apache_root)
    flatten_extracted_dir(apache_root, expected="Apache24")

    download_file(URLS["php"], zip_php)
    extract_archive(zip_php, php_root)
    flatten_extracted_dir(php_root)

    run_sc_create("VergeGridApache",
                  f'"{apache_root}\\bin\\httpd.exe" -k runservice',
                  "VergeGrid Apache", "Apache Web Server for VergeGrid")

    create_shortcut("Start VergeGrid Apache", "sc start VergeGridApache")
    create_shortcut("Stop VergeGrid Apache", "sc stop VergeGridApache")
    create_shortcut("Restart VergeGrid Apache", "sc stop VergeGridApache && sc start VergeGridApache")

    write_log(f"Apache installed to {apache_root}")
    write_log(f"PHP installed to {php_root}")

# --------------------------------------------------------------------
# OpenSim Installation
# --------------------------------------------------------------------
def install_opensim(target_root, downloads_root):
    target = target_root
    os.makedirs(target, exist_ok=True)
    zip_path = os.path.join(downloads_root, "opensim.zip")

    download_file(URLS["opensim"], zip_path)
    extract_archive(zip_path, target)
    flatten_extracted_dir(target, expected="opensim")

    create_shortcut("Run OpenSim", f'start "" "{target}\\bin\\OpenSim.exe"')

# --------------------------------------------------------------------
# Workbench Installation
# --------------------------------------------------------------------
def install_workbench(root):
    msi = os.path.join(root, "Downloads", "workbench.msi")
    download_file(URLS["workbench"], msi)
    subprocess.run(["msiexec", "/i", msi, "/passive"], check=False)

# --------------------------------------------------------------------
# Main Installer Flow
# --------------------------------------------------------------------
def main():
    print(">>> VergeGrid Python Installer is starting...")
    sys.stdout.flush()
    try:
        print(">>> Selecting install drive...")
        install_root = select_install_drive()
        downloads_root = os.path.join(install_root, "Downloads")
        os.makedirs(downloads_root, exist_ok=True)
        os.makedirs(os.path.join(install_root, "Logs"), exist_ok=True)

        ensure_vergegrid_config(install_root)
        global INSTALL_LOG
        INSTALL_LOG = os.path.join(install_root, "Logs", "vergegrid-install.log")
        write_log("=== VergeGrid Python Installer Started ===")
        ensure_admin()

        cfg_file = os.path.join(install_root, "vergegrid.conf")
        config = load_vergegrid_config(cfg_file, root=install_root)

        print("\nDetected Configuration:")
        for k, v in config.items():
            print(f"  {k:<15} {v}")
        print(f"  DOWNLOADS_ROOT  {downloads_root}\n")

        print(">>> Asking user which components to install...")
        installed = []

        # STEP 1: MySQL
        if confirm("Install MySQL?"):
            install_mysql(config["MYSQL_ROOT"], downloads_root)
            installed.append(("MySQL", config["MYSQL_ROOT"]))
        else:
            print(">>> Skipped MySQL")

        # STEP 2: OpenSim (before Apache/PHP)
        if confirm("Install OpenSim (recommended before Apache/PHP)?"):
            install_opensim(config["OPEN_SIM_ROOT"], downloads_root)
            installed.append(("OpenSim", config["OPEN_SIM_ROOT"]))
        else:
            print(">>> Skipped OpenSim")

        # STEP 3: Apache + PHP
        if confirm("Install Apache/PHP (after OpenSim)?"):
            install_apache_php(config["APACHE_ROOT"], config["PHP_ROOT"], downloads_root)
            installed.append(("Apache", config["APACHE_ROOT"]))
            installed.append(("PHP", config["PHP_ROOT"]))
        else:
            print(">>> Skipped Apache/PHP")

        write_log("Installation complete.")
        print("\nInstallation complete. Logs saved to:", INSTALL_LOG)
        print("\n" + "=" * 70)
        print(" VergeGrid Installation Summary")
        print("=" * 70)
        if installed:
            for name, path in installed:
                print(f"  {name:<12}  ->  {path}")
        else:
            print("  No components were installed.")
        print("-" * 70)
        print(f"  Logs saved to:  {INSTALL_LOG}")
        print("  Shortcuts:      C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\VergeGrid")
        print("=" * 70)
        print("\nInstallation complete. You may close this window or launch services via Start Menu.")
    except Exception as e:
        print("\n!!! INSTALLER CRASHED !!!")
        print("Error:", e)
        import traceback
        traceback.print_exc()
        write_log(f"FATAL ERROR: {e}", "ERROR")
        input("\nPress Enter to exit...")

# --------------------------------------------------------------------
if __name__ == "__main__":
    print(">>> VergeGrid bootstrap reached main entrypoint.")
    main()
    print(">>> VergeGrid Python Installer finished cleanly.")

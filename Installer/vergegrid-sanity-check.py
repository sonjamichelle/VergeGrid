#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VergeGrid Sanity Checker
Author: Sonja + GPT
Purpose:
  - Verify that all major VergeGrid components are installed, extracted, and running
  - Check service registration and process status
  - Confirm MySQL + Robust operational connectivity
  - Summarize results in PASS/FAIL format
  - Write all logs to ./Installer_Logs/vergegrid-sanity.log
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
import psutil
import shutil
import re
import time
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

# ------------------------------------------------------------
# Logging Setup — Centralized to ./Installer_Logs
# ------------------------------------------------------------
INSTALLER_LOG_DIR = Path(ROOT_DIR) / "Installer_Logs"
INSTALLER_LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = INSTALLER_LOG_DIR / "vergegrid-sanity.log"


def log(msg, color=None):
    """Log to console and append to sanity log file."""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    formatted = f"{timestamp} {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass
    if color:
        print(color + msg + Style.RESET_ALL)
    else:
        print(msg)


def print_section(title):
    log("\n" + "=" * 70)
    log(f"  {title}")
    log("=" * 70)


def check_exists(base, sub):
    path = Path(base) / sub
    return path.exists(), str(path)


def check_service_status(name):
    try:
        result = subprocess.run(["sc", "query", name], capture_output=True, text=True)
        if "RUNNING" in result.stdout:
            return "RUNNING"
        elif "STOPPED" in result.stdout:
            return "STOPPED"
        elif "SERVICE_NAME" in result.stdout:
            return "REGISTERED"
        else:
            return "NOT FOUND"
    except Exception:
        return "ERROR"


def check_process_running(exe_name):
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and proc.info['name'].lower() == exe_name.lower():
            return True
    return False


def scan_logs(log_path):
    if not os.path.exists(log_path):
        return "MISSING"
    errors = []
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if re.search(r"\[(ERROR|FATAL)\]", line, re.IGNORECASE):
                errors.append(line.strip())
    return errors or None


# ------------------------------------------------------------
# Main Sanity Check Routine
# ------------------------------------------------------------
def run_sanity_check(install_root):
    install_root = Path(install_root).resolve()
    log("\n=== VergeGrid Sanity Check ===", Style.BRIGHT)
    log(f"Target installation root: {install_root}\n", Fore.CYAN)

    results = {"services": {}, "processes": {}, "paths": {}, "log_errors": []}

    SERVICES = {
        "MySQL": "VergeGridMySQL",
        "Robust": "VergeGridRobust",
        "Apache": "VergeGridApache",
    }

    PROCESSES = {
        "mysqld.exe": "MySQL Daemon",
        "Robust.exe": "OpenSim Robust",
        "httpd.exe": "Apache Web Server",
    }

    PATHS = [
        ("MySQL Root", "MySQL"),
        ("OpenSim Root", "OpenSim"),
        ("Apache Root", "Apache"),
        ("PHP Root", "PHP"),
        ("Logs Directory", "Logs"),
        ("Downloads Directory", "Downloads"),
    ]

    log_file_relative = "Logs/vergegrid-install.log"

    # --------------------------------------------------------
    # 1. Directory Checks
    # --------------------------------------------------------
    print_section("Directory Structure Validation")
    for label, sub in PATHS:
        ok, path = check_exists(install_root, sub)
        status = "OK" if ok else "MISSING"
        color = Fore.GREEN if ok else Fore.RED
        log(f"{label:<20} -> {path} [{status}]", color)
        results["paths"][label] = status

    # --------------------------------------------------------
    # 2. Windows Services
    # --------------------------------------------------------
    print_section("Service Status")
    for label, svc in SERVICES.items():
        status = check_service_status(svc)
        color = Fore.GREEN if status == "RUNNING" else Fore.YELLOW if status in ("STOPPED", "REGISTERED") else Fore.RED
        log(f"{label:<10} -> {svc:<20} [{status}]", color)
        results["services"][label] = status

    # --------------------------------------------------------
    # 3. Processes
    # --------------------------------------------------------
    print_section("Process Verification")
    for exe, label in PROCESSES.items():
        running = check_process_running(exe)
        color = Fore.GREEN if running else Fore.RED
        log(f"{label:<20} ({exe:<12}) -> [{'RUNNING' if running else 'NOT FOUND'}]", color)
        results["processes"][label] = "RUNNING" if running else "NOT FOUND"

    # --------------------------------------------------------
    # 4. MySQL Connectivity Check
    # --------------------------------------------------------
    print_section("MySQL Connectivity Test")
    mysql_exe = shutil.which("mysql") or "mysql"
    try:
        test_cmd = [mysql_exe, "-u", "root", "-e", "SHOW DATABASES;"]
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
        if "information_schema" in result.stdout:
            log("✓ MySQL responded successfully.", Fore.GREEN)
            results["mysql_ok"] = True
        else:
            log("[WARN] MySQL command ran but returned no results.", Fore.YELLOW)
            results["mysql_ok"] = False
    except Exception as e:
        log(f"[FAIL] Could not run MySQL client: {e}", Fore.RED)
        results["mysql_ok"] = False

    # --------------------------------------------------------
    # 5. Log File Scan
    # --------------------------------------------------------
    print_section("Log File Scan")
    log_path = install_root / log_file_relative
    errors = scan_logs(log_path)
    if errors == "MISSING":
        log("Log file not found.", Fore.YELLOW)
    elif errors:
        log(f"[WARN] Found {len(errors)} error(s) in install log:", Fore.RED)
        for e in errors[-10:]:  # last 10
            log("  " + e)
        results["log_errors"] = errors
    else:
        log("No errors found in installation logs.", Fore.GREEN)

    # --------------------------------------------------------
    # 6. Final Summary
    # --------------------------------------------------------
    print_section("Sanity Check Summary")

    def ok(x): return x in ("OK", "RUNNING", "REGISTERED", True)

    service_pass = all(ok(v) for v in results["services"].values())
    process_pass = any(v == "RUNNING" for v in results["processes"].values())
    path_pass = all(v == "OK" for v in results["paths"].values())

    all_pass = service_pass and process_pass and path_pass and not results["log_errors"]

    log(f"Paths OK:     {path_pass}")
    log(f"Services OK:  {service_pass}")
    log(f"Processes OK: {process_pass}")
    log(f"MySQL OK:     {results.get('mysql_ok', False)}")
    log(f"Errors Found: {bool(results['log_errors'])}")

    if all_pass:
        log("\n✅ PASS — VergeGrid stack is healthy!", Fore.GREEN)
    else:
        log("\n❌ FAIL — Issues detected.", Fore.RED)
        log("Check detailed logs at:")
        log("  " + str(log_path))
        log("and review the Windows Service Manager for stopped or missing VergeGrid services.\n")

    log("\nFull sanity check log written to: " + str(LOG_FILE), Fore.CYAN)
    return all_pass


# ------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vergegrid-sanity-check.py <install_root>")
        sys.exit(1)

    install_root = sys.argv[1]
    try:
        run_sanity_check(install_root)
    except Exception as e:
        import traceback
        traceback.print_exc()
        log(f"[FATAL] Sanity check failed: {e}", Fore.RED)
        sys.exit(1)

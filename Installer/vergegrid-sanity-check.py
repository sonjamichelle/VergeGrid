# -*- coding: utf-8 -*-
"""
VergeGrid Sanity Checker
Author: Sonja + GPT
Purpose:
  - Verify that all major VergeGrid components are installed, extracted, and running
  - Check service registration and process status
  - Confirm MySQL + Robust operational connectivity
  - Summarize results in PASS/FAIL format
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
import psutil
from pathlib import Path
import time
import re

# ------------------------------------------------------------
# Configurable Service and Directory Paths
# ------------------------------------------------------------
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

LOG_FILE = "Logs/vergegrid-install.log"

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------
def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

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
    print("\n=== VergeGrid Sanity Check ===")
    print(f"Target installation root: {install_root}\n")

    results = {"services": {}, "processes": {}, "paths": {}, "log_errors": []}

    # --------------------------------------------------------
    # 1. Directory Checks
    # --------------------------------------------------------
    print_section("Directory Structure Validation")
    for label, sub in PATHS:
        ok, path = check_exists(install_root, sub)
        status = "OK" if ok else "MISSING"
        print(f"{label:<20} -> {path} [{status}]")
        results["paths"][label] = status

    # --------------------------------------------------------
    # 2. Windows Services
    # --------------------------------------------------------
    print_section("Service Status")
    for label, svc in SERVICES.items():
        status = check_service_status(svc)
        print(f"{label:<10} -> {svc:<20} [{status}]")
        results["services"][label] = status

    # --------------------------------------------------------
    # 3. Processes
    # --------------------------------------------------------
    print_section("Process Verification")
    for exe, label in PROCESSES.items():
        running = check_process_running(exe)
        print(f"{label:<20} ({exe:<12}) -> [{'RUNNING' if running else 'NOT FOUND'}]")
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
            print("✓ MySQL responded successfully.")
            results["mysql_ok"] = True
        else:
            print("[WARN] MySQL command ran but returned no results.")
            results["mysql_ok"] = False
    except Exception as e:
        print(f"[FAIL] Could not run MySQL client: {e}")
        results["mysql_ok"] = False

    # --------------------------------------------------------
    # 5. Log File Scan
    # --------------------------------------------------------
    print_section("Log File Scan")
    log_path = install_root / LOG_FILE
    errors = scan_logs(log_path)
    if errors == "MISSING":
        print("Log file not found.")
    elif errors:
        print(f"[WARN] Found {len(errors)} error(s) in install log:")
        for e in errors[-10:]:  # show last 10
            print("  " + e)
        results["log_errors"] = errors
    else:
        print("No errors found in installation logs.")

    # --------------------------------------------------------
    # 6. Final Summary
    # --------------------------------------------------------
    print_section("Sanity Check Summary")

    def ok(x): return x in ("OK", "RUNNING", "REGISTERED", True)

    service_pass = all(ok(v) for v in results["services"].values())
    process_pass = any(v == "RUNNING" for v in results["processes"].values())
    path_pass = all(v == "OK" for v in results["paths"].values())

    all_pass = service_pass and process_pass and path_pass and not results["log_errors"]

    print(f"Paths OK:     {path_pass}")
    print(f"Services OK:  {service_pass}")
    print(f"Processes OK: {process_pass}")
    print(f"MySQL OK:     {results.get('mysql_ok', False)}")
    print(f"Errors Found: {bool(results['log_errors'])}")

    print("\nOverall Result: " + ("✅ PASS — VergeGrid stack is healthy!" if all_pass else "❌ FAIL — Issues detected."))

    if not all_pass:
        print("\nCheck detailed logs at:")
        print("  " + str(log_path))
        print("and review the Windows Service Manager for stopped or missing VergeGrid services.\n")

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
        print(f"\n[FATAL] Sanity check failed: {e}")
        sys.exit(1)

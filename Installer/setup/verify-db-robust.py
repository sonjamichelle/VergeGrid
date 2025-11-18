# -*- coding: utf-8 -*-
"""
VergeGrid Robust Database Verifier
Author: Sonja + GPT
Purpose:
  - Start Robust.exe (via direct invocation)
  - Verify that the Robust database schema is populated
  - Distinguish between critical and optional tables
  - Shut Robust.exe down gracefully after verification
  - Log results for installer
"""

import os
import sys
import time
import signal
import subprocess
import pymysql
import psutil
from math import ceil
from pathlib import Path

# --- VergeGrid Path Fix ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

try:
    from setup import common
except ModuleNotFoundError:
    import common


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = ""
DB_NAME = "robust"

CORE_TABLES = [
    "assets", "auth", "avatars", "friends", "griduser",
    "inventoryfolders", "inventoryitems", "presence",
    "regions", "tokens", "useraccounts"
]

OPTIONAL_TABLES = ["agentprefs", "migrations", "muteList"]


# ------------------------------------------------------------
# VERIFY ROBUST DATABASE
# ------------------------------------------------------------
def verify_robust_db(install_root=None):
    install_root = Path(install_root or "D:\\VergeGrid").resolve()
    logs_root = install_root / "Logs"
    logs_root.mkdir(parents=True, exist_ok=True)

    log_file = logs_root / "vergegrid-install.log"
    common.set_log_file(str(log_file))
    common.write_log("=== VergeGrid Robust Database Verification ===")

    print("\n>>> Verifying Robust Database Schema...")

    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [row[f"Tables_in_{DB_NAME}"] for row in cursor.fetchall()]
    except Exception as e:
        print(f"[ERROR] Could not connect to MySQL: {e}")
        common.write_log(f"[FATAL] MySQL connection failed: {e}", "ERROR")
        return 1

    missing_core = [t for t in CORE_TABLES if t not in tables]
    missing_optional = [t for t in OPTIONAL_TABLES if t not in tables]

    print(f"  Found {len(tables)} total tables in '{DB_NAME}'.")

    if missing_core:
        print("\n[ERROR] Missing CRITICAL tables:")
        for m in missing_core:
            print(f"   - {m}")
        common.write_log(f"[FATAL] Missing core tables: {', '.join(missing_core)}", "ERROR")
        result_code = 2
    else:
        print("  ✓ All critical Robust tables are present.")
        common.write_log("[OK] All core Robust tables verified.", "INFO")
        result_code = 0

    if missing_optional:
        print("\n[INFO] Missing optional tables (not fatal):")
        for m in missing_optional:
            print(f"   - {m}")
        common.write_log(f"[INFO] Optional tables missing (OK): {', '.join(missing_optional)}", "INFO")

    try:
        cursor.execute("SELECT COUNT(*) AS c FROM useraccounts;")
        users = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) AS c FROM regions;")
        regions = cursor.fetchone()["c"]
        print(f"\n  User records: {users}, Regions: {regions}")
        common.write_log(f"[INFO] Robust DB contains {users} users and {regions} regions.", "INFO")
    except Exception as e:
        common.write_log(f"[WARN] Could not query record counts: {e}", "WARN")

    conn.close()
    print("\n✓ Robust database verification completed.\n")
    return result_code


# ------------------------------------------------------------
# LAUNCH AND VERIFY ROBUST.EXE (Grid Mode)
# ------------------------------------------------------------
def launch_and_verify(install_root):
    """
    Launch Robust.exe using Robust.HG.ini in a visible console window,
    wait for it to initialize, verify database schema creation,
    then shut it down gracefully after verification.
    """
    install_root = Path(install_root).resolve()
    opensim_root = install_root / "OpenSim" / "bin"
    logs_root = install_root / "Logs"
    logs_root.mkdir(parents=True, exist_ok=True)

    robust_exe = opensim_root / "Robust.exe"
    robust_ini = opensim_root / "Robust.ini"

    print("\n>>> Launching Robust.exe (Grid Mode) for schema population...")

    if not robust_exe.exists():
        print(f"[FATAL] {robust_exe} not found. Cannot continue.")
        common.write_log(f"[FATAL] Missing {robust_exe}", "ERROR")
        return 1

    if not robust_ini.exists():
        print(f"[FATAL] {robust_ini} missing. Cannot start Robust in grid mode.")
        common.write_log(f"[FATAL] Missing {robust_ini}", "ERROR")
        return 2

    try:
        robust_process = subprocess.Popen(
            [str(robust_exe), "-inifile", "Robust.ini"],
            cwd=str(opensim_root),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    except Exception as e:
        print(f"[FATAL] Failed to launch Robust.exe: {e}")
        common.write_log(f"[FATAL] Failed to launch Robust.exe: {e}", "ERROR")
        return 3

    print(f"✓ Robust.exe started (PID={robust_process.pid}) using {robust_ini.name}.")

    # Wait for process to initialize
    print("\n[INFO] Waiting for Robust.exe to initialize...")
    try:
        proc = psutil.Process(robust_process.pid)
    except Exception as e:
        print(f"[WARN] Could not attach to process {robust_process.pid}: {e}")
        proc = None

    wait_for_start = 10
    for i in range(wait_for_start):
        if proc and proc.is_running():
            cpu = proc.cpu_percent(interval=1.0)
            if cpu > 0.1:
                print(f"  [OK] Robust.exe responding (PID={robust_process.pid}).")
                break
        else:
            time.sleep(1)
    else:
        print("  [WARN] Process took too long to respond, continuing anyway.")

    # Live countdown for schema initialization
    total_wait = 30
    print(f"\n[INFO] Waiting {total_wait} seconds for schema creation...\n")
    print("DO NOT CLOSE THE CONSOLE OR INTERACT WITH IT.")
    print("JUST SIT BACK AND CHILL FOR A BIT.\n")

    for remaining in range(total_wait, 0, -1):
        sys.stdout.write(f"\r⏳ Initializing database schema... {remaining:2d}s remaining")
        sys.stdout.flush()
        if proc and not proc.is_running():
            sys.stdout.write("\r⚠️  Robust.exe exited unexpectedly during initialization!\n")
            sys.stdout.flush()
            common.write_log("[ERROR] Robust.exe exited prematurely during wait period.", "ERROR")
            return 4
        time.sleep(1)

    sys.stdout.write("\r✅ Schema creation wait complete!                           \n")
    sys.stdout.flush()
    common.write_log(f"[INFO] Robust.exe launched (PID={robust_process.pid})", "INFO")

    # --------------------------------------------------------------------
    # Verify DB (measure verification time)
    # --------------------------------------------------------------------
    print("\n>>> Checking database status (pass 1)...")
    start_verify = time.time()
    result = verify_robust_db(install_root)
    verify_duration = ceil(time.time() - start_verify)

    if result == 0:
        print("✓ Database verified successfully on first pass.")
        common.write_log("[OK] Database verified on first pass.", "INFO")

        # ----------------------------------------------------------------
        # Countdown before graceful shutdown (duration = verify time)
        # ----------------------------------------------------------------
        print(f"\n>>> Attempting to close Robust.exe gracefully in {verify_duration}s...")
        for remaining in range(verify_duration, 0, -1):
            sys.stdout.write(f"\r⏳ Preparing to shut down Robust.exe... {remaining:2d}s")
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write("\r🔧 Initiating shutdown now...                               \n")
        sys.stdout.flush()
    else:
        # Second pass
        total_wait_2 = 30
        print("⚠️  Database not yet complete. Waiting 30 more seconds...\n")
        print("DO NOT CLOSE THE CONSOLE OR INTERACT WITH IT.")
        print("JUST SIT BACK AND CHILL FOR A BIT.\n")
        for remaining in range(total_wait_2, 0, -1):
            sys.stdout.write(f"\r⏳ Retrying verification in {remaining:2d}s...")
            sys.stdout.flush()
            if proc and not proc.is_running():
                sys.stdout.write("\r⚠️  Robust.exe exited unexpectedly before second check!\n")
                sys.stdout.flush()
                common.write_log("[ERROR] Robust.exe exited before second check.", "ERROR")
                return 5
            time.sleep(1)
        sys.stdout.write("\r🔁 Retrying verification now...                             \n")
        sys.stdout.flush()
        print(">>> Checking database status (pass 2)...")
        result = verify_robust_db(install_root)
        if result != 0:
            print("[FATAL] Database still incomplete after second check.")
            common.write_log("[FATAL] Database verification failed after second check.", "ERROR")
            print("⚠️  Leaving Robust.exe running for manual troubleshooting.")
            return 2

    # --------------------------------------------------------------------
    # Graceful stop (with log)
    # --------------------------------------------------------------------
    print("\n>>> Attempting to close Robust.exe gracefully...")
    try:
        robust_process.send_signal(signal.CTRL_BREAK_EVENT)
        time.sleep(10)

        if robust_process.poll() is None:
            robust_process.terminate()
            time.sleep(5)

        if robust_process.poll() is None:
            robust_process.kill()

        print("✓ Robust.exe stopped cleanly after schema verification.\n")
        common.write_log("[OK] Robust.exe stopped cleanly after schema verification.", "INFO")

    except Exception as e:
        print(f"[WARN] Graceful shutdown failed: {e}")
        common.write_log(f"[WARN] Graceful shutdown failed: {e}", "WARN")

    return 0


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify-db-robust.py <install_root>")
        sys.exit(1)

    install_root = Path(sys.argv[1])
    print("=== VergeGrid Robust Database Verification and Controlled Startup ===")
    result = launch_and_verify(install_root)
    sys.exit(result)

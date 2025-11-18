# -*- coding: utf-8 -*-
"""
VergeGrid OpenSim Services Initializer
Author: Sonja + GPT
Purpose:
  - Create Robust debug launcher
  - Register VergeGrid Robust as a manual-start Windows service
  - Verify MySQL access but DO NOT run Robust.exe
"""

import os
import sys
import subprocess
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
# MySQL Compatibility Check
# ------------------------------------------------------------
def ensure_mysql_native_password(user="root", password="", host="localhost"):
    try:
        import pymysql
    except ImportError:
        print("Installing PyMySQL dependency...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMySQL"])
        import pymysql

    try:
        conn = pymysql.connect(host=host, user=user, password=password)
        conn.close()
        common.write_log("[OK] Verified MySQL root authentication is working.", "INFO")
        print("[OK] Verified MySQL root authentication is working.")
        return True
    except Exception as e:
        common.write_log(f"[ERROR] MySQL connection check failed: {e}", "ERROR")
        print(f"[ERROR] MySQL connection check failed: {e}")
        return False


# ------------------------------------------------------------
# Create Service
# ------------------------------------------------------------
def create_service(name, bin_path, display_name, description):
    """Register Windows service in manual start mode."""
    try:
        subprocess.run(
            [
                "sc", "create", name,
                f"binPath= {bin_path}",
                f"DisplayName= {display_name}",
                "start=", "demand"   # <-- manual start
            ],
            capture_output=True, text=True
        )
        subprocess.run(
            ["sc", "description", name, description],
            capture_output=True, text=True
        )
        print(f"✓ Service '{name}' created successfully (manual start).")
        common.write_log(f"[OK] Created Windows service (manual): {name}", "INFO")
    except Exception as e:
        common.write_log(f"[ERROR] Failed to create service {name}: {e}", "ERROR")
        print(f"[ERROR] Failed to create service {name}: {e}")


# ------------------------------------------------------------
# Main Routine
# ------------------------------------------------------------
def init_opensim_services(install_root):
    install_root = Path(install_root).resolve()
    opensim_root = install_root / "OpenSim" / "bin"
    logs_root = install_root / "Logs"
    os.makedirs(logs_root, exist_ok=True)

    log_file = logs_root / "vergegrid-install.log"
    common.set_log_file(str(log_file))
    common.write_log("=== VergeGrid OpenSim Service Initialization ===")

    robust_exe = opensim_root / "Robust.exe"
    if not robust_exe.exists():
        print(f"[ERROR] {robust_exe} not found.")
        common.write_log(f"[FATAL] Missing {robust_exe}", "ERROR")
        return 1

    # Verify MySQL access (no Robust.exe startup)
    ensure_mysql_native_password()

    # --------------------------------------------------------
    # Create Debug Launcher (for future manual testing)
    # --------------------------------------------------------
    debug_bat = opensim_root / "launch_robust_debug.bat"
    robust_log = logs_root / "Robust_debug.log"

    debug_bat.write_text(f"""@echo off
cd /d "{opensim_root}"
echo [Robust Debug] Launching Robust.exe at %date% %time% >> "{robust_log}"
"{robust_exe}" -console >> "{robust_log}" 2>&1
echo. >> "{robust_log}"
echo [Robust Debug] Robust.exe exited with code %errorlevel% at %time% >> "{robust_log}"
echo.
echo *** Robust.exe has exited (code %errorlevel%) ***
echo.
pause
""", encoding="utf-8")

    common.write_log(f"[INFO] Created debug launcher: {debug_bat}", "INFO")

    # --------------------------------------------------------
    # Register Manual Windows Service (no execution)
    # --------------------------------------------------------
    print("\n>>> Registering VergeGrid Robust Windows Service (manual start)...")
    bin_path = f'"{robust_exe}" -console'
    create_service(
        name="VergeGridRobust",
        bin_path=bin_path,
        display_name="VergeGrid Robust",
        description="VergeGrid Robust Services (Grid Login, Asset, User, Inventory, etc.)"
    )

    print("✓ VergeGrid Robust service registered (manual start).")
    print(f"  Debug launcher available: {debug_bat}")
    print(f"  Log output: {robust_log}\n")

    common.write_log("[SUCCESS] Robust service registered (manual start).", "INFO")
    return 0


# ------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python init-opensim-services.py <install_root>")
        sys.exit(1)

    install_root = sys.argv[1]
    try:
        sys.exit(init_opensim_services(install_root))
    except Exception as e:
        import traceback
        traceback.print_exc()
        common.write_log(f"[FATAL] OpenSim Service Initialization failed: {e}", "ERROR")
        print(f"[FATAL] OpenSim Service Initialization failed: {e}")
        sys.exit(1)

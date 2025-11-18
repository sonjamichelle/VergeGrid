#!/usr/bin/env python3
# ==========================================================
# VergeGrid Service Initialization
# init-services.py
# ----------------------------------------------------------
# Detects, stops, deletes, and recreates MySQL, Apache,
# and Robust (OpenSim) services on Windows.
# Must be run as Administrator.
# ==========================================================

import subprocess
import logging
import sys
from pathlib import Path

# ----------------------------------------------------------
# LOGGING CONFIGURATION
# ----------------------------------------------------------
INSTALLER_DIR = Path(__file__).resolve().parent
LOG_DIR = INSTALLER_DIR / "Setup_Logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "service_init.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ----------------------------------------------------------
# SERVICE DEFINITIONS
# ----------------------------------------------------------
SERVICES = {
    "MySQL": {
        "display_name": "VergeGrid Database Service (MySQL)",
        "exe_path": str(INSTALLER_DIR / "MySQL" / "bin" / "mysqld.exe"),
        "start_params": "--defaults-file=" + str(INSTALLER_DIR / "MySQL" / "my.ini")
    },
    "Apache2.4": {
        "display_name": "VergeGrid Web Server (Apache)",
        "exe_path": r"C:\Apache24\bin\httpd.exe",
        "start_params": "-k runservice"
    },
    "Robust": {
        "display_name": "VergeGrid Robust Grid Service",
        "exe_path": str(INSTALLER_DIR / "OpenSim" / "bin" / "Robust.exe"),
        "start_params": ""
    }
}

# ----------------------------------------------------------
# UTILITY FUNCTIONS
# ----------------------------------------------------------
def run_cmd(cmd: str):
    """Run a shell command and return (exit_code, stdout, stderr)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def service_exists(name: str) -> bool:
    """Check if a Windows service exists."""
    code, out, _ = run_cmd(f'sc query "{name}"')
    return "FAILED 1060" not in out

def stop_service(name: str):
    """Stop a running service."""
    logging.info(f"Stopping service '{name}'...")
    run_cmd(f'sc stop "{name}"')

def delete_service(name: str):
    """Delete a Windows service."""
    logging.info(f"Deleting service '{name}'...")
    run_cmd(f'sc delete "{name}"')

def create_service(name: str, config: dict):
    """Create a new Windows service."""
    exe = config["exe_path"]
    if not Path(exe).exists():
        logging.warning(f"Executable for {name} not found: {exe}")
        return False

    cmd = (
        f'sc create "{name}" binPath= "\"{exe}\" {config["start_params"]}" '
        f'DisplayName= "{config["display_name"]}" start= auto'
    )
    code, out, err = run_cmd(cmd)
    if code == 0:
        logging.info(f"Service '{name}' created successfully.")
        return True
    else:
        logging.error(f"Failed to create service '{name}': {out or err}")
        return False

def start_service(name: str):
    """Start a Windows service."""
    code, out, err = run_cmd(f'sc start "{name}"')
    if code == 0:
        logging.info(f"Service '{name}' started successfully.")
    else:
        logging.warning(f"Service '{name}' could not be started: {out or err}")

# ----------------------------------------------------------
# MAIN LOGIC
# ----------------------------------------------------------
def main():
    print("🧩 VergeGrid Service Initialization")
    logging.info("========== VergeGrid Service Initialization ==========")

    # Check for admin privileges
    code, _, _ = run_cmd("net session")
    if code != 0:
        print("⚠️  This script must be run as Administrator.")
        logging.error("Administrator privileges required.")
        sys.exit(1)

    for name, config in SERVICES.items():
        logging.info(f"Processing service: {name}")

        if service_exists(name):
            logging.info(f"Existing service '{name}' found — resetting.")
            stop_service(name)
            delete_service(name)

        if create_service(name, config):
            start_service(name)
            print(f"✅ {name} service created and started.")
        else:
            print(f"⚠️  {name} binary missing, service not created. Check logs.")

    logging.info("Service setup completed successfully.")
    print(f"\nAll service operations complete. Log saved at:\n{LOG_FILE}")

# ----------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        print(f"❌ Initialization failed: {e}")
        sys.exit(1)

#!/usr/bin/env python3
"""
VergeGrid Region Bootstrap (create-region.py)
Corrected to place all files directly under:
D:\VergeGrid\OpenSim\bin\Regions\
without nesting another Regions directory.
"""

import os
import sys
import uuid
import shutil
import mysql.connector
from pathlib import Path
from configparser import ConfigParser
from cryptography.fernet import Fernet
from datetime import datetime

# --- Detect Install Root ---
SETUP_DIR = Path(__file__).resolve().parent
INSTALL_PATH_FILE = SETUP_DIR / "install_path.txt"

if INSTALL_PATH_FILE.exists():
    INSTALL_ROOT = Path(INSTALL_PATH_FILE.read_text(encoding="utf-8").strip())
else:
    print("[WARN] install_path.txt not found. Using current working directory.")
    INSTALL_ROOT = Path.cwd()

# Base paths
BIN_DIR = INSTALL_ROOT / "OpenSim" / "bin"
REGIONS_DIR = BIN_DIR / "Regions"

# FIXED: point to ../Templates/Regions so we copy only the correct content level
TEMPLATES_BASE = (SETUP_DIR.parent / "Templates").resolve()
TEMPLATES_REGIONS = TEMPLATES_BASE / "Regions"

# Defaults
DEFAULT_REGION_NAME = "Verge Landing"
DEFAULT_ESTATE_NAME = "Landings"
DEFAULT_LOCATION = "9300,9300"
DEFAULT_PORT = "8005"
DEFAULT_HOSTNAME = "grid.dcwork.space"

# ------------------------------------------------------------
# Credential Loader
# ------------------------------------------------------------
def load_encrypted_credentials(user_key="robustuser"):
    creds_path = SETUP_DIR / "creds.conf"
    vault_path = SETUP_DIR / "vault.key"
    if not creds_path.exists() or not vault_path.exists():
        print("[FATAL] Missing creds.conf or vault.key.")
        sys.exit(1)
    with open(vault_path, "rb") as f:
        key = f.read()
    fernet = Fernet(key)
    config = ConfigParser()
    config.read(creds_path, encoding="utf-8")
    encrypted_pw = config["Encrypted"][user_key]
    return fernet.decrypt(encrypted_pw.encode()).decode()

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def copy_region_templates():
    """Copy only the contents of Templates/Regions into bin/Regions."""
    if not TEMPLATES_REGIONS.exists():
        print(f"[FATAL] Missing expected template folder: {TEMPLATES_REGIONS}")
        sys.exit(1)
    REGIONS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Copying region templates from {TEMPLATES_REGIONS} → {REGIONS_DIR}")
    for item in TEMPLATES_REGIONS.iterdir():
        target = REGIONS_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    print("[OK] Region templates deployed to correct path.")

def rename_template_files(base_path, old_name, new_name):
    """Rename all files and folders with the old region name."""
    for root, dirs, files in os.walk(base_path, topdown=False):
        for fname in files:
            if old_name in fname:
                old_file = Path(root) / fname
                new_file = Path(root) / fname.replace(old_name, new_name)
                old_file.rename(new_file)
        for dname in dirs:
            if old_name in dname:
                old_dir = Path(root) / dname
                new_dir = Path(root) / dname.replace(old_name, new_name)
                old_dir.rename(new_dir)

def generate_uuid():
    return str(uuid.uuid4())

def get_god_user():
    """Fetch the first God user (UserLevel >= 250)."""
    mysql_user = "robustuser"
    mysql_pw = load_encrypted_credentials("robustuser")
    try:
        conn = mysql.connector.connect(
            host="localhost", user=mysql_user, password=mysql_pw, database="robust"
        )
        cursor = conn.cursor()
        cursor.execute(
            "SELECT PrincipalID, FirstName, LastName FROM useraccounts WHERE UserLevel >= 250 LIMIT 1;"
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            pid, first, last = row
            return pid, f"{first} {last}"
    except Exception as e:
        print(f"[WARN] Could not fetch God user: {e}")
    return None, None

def substitute_placeholders(file_path, replacements):
    """Replace placeholders and old text inside template files."""
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    for key, value in replacements.items():
        text = text.replace(f"{{{key}}}", str(value))
    text = text.replace("Moonlight Landing", replacements["REGION_NAME"])
    text = text.replace("Moonlight Landing II", replacements["REGION_NAME"])
    text = text.replace("Landings", replacements["ESTATE_NAME"])
    file_path.write_text(text, encoding="utf-8")

# ------------------------------------------------------------
# Main Region Creator
# ------------------------------------------------------------
def create_region_structure():
    print("\n=== VergeGrid Landing Estate Initializer (Automated) ===")
    print(f"[INFO] Install root: {INSTALL_ROOT}")
    print(f"[INFO] OpenSim bin directory: {BIN_DIR}")
    print(f"[INFO] Template source: {TEMPLATES_REGIONS}")

    # Step 1: Copy templates (fixed to copy from Templates/Regions)
    copy_region_templates()

    # Step 2: Rename default files/folders
    rename_template_files(REGIONS_DIR, "Moonlight Landing", DEFAULT_REGION_NAME)

    # Step 3: Replace text placeholders
    god_id, god_name = get_god_user()
    if not god_id:
        god_id = "00000000-0000-0000-0000-000000000000"
        god_name = "Unknown User"

    region_uuid = generate_uuid()
    replacements = {
        "REGION_NAME": DEFAULT_REGION_NAME,
        "REGION_UUID": region_uuid,
        "ESTATE_NAME": DEFAULT_ESTATE_NAME,
        "ESTATE_OWNER": god_id,
        "ESTATE_OWNER_NAME": god_name,
        "LOCATION": DEFAULT_LOCATION,
        "PORT": DEFAULT_PORT,
        "HOSTNAME": DEFAULT_HOSTNAME,
        "DATE": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    for root, _, files in os.walk(REGIONS_DIR):
        for fname in files:
            if fname.lower().endswith((".ini", ".txt", ".cfg", ".xml", ".log")):
                substitute_placeholders(Path(root) / fname, replacements)

    # Step 4: Write master Regions.ini correctly
    regions_ini = REGIONS_DIR / "Regions.ini"
    with open(regions_ini, "w", encoding="utf-8") as f:
        f.write(f"[Regions]\n{DEFAULT_REGION_NAME} = Landings/Region/{DEFAULT_REGION_NAME}.ini\n")

    print(f"[OK] Region UUID: {region_uuid}")
    print(f"[OK] Owner: {god_name} ({god_id})")
    print("\n✅ Layout completed successfully!")
    print(f"   Regions located at: {REGIONS_DIR}")
    print(f"   Run OpenSim.exe -inifile=Regions/Landings/{DEFAULT_ESTATE_NAME}.ini\n")

# ------------------------------------------------------------
# Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    create_region_structure()

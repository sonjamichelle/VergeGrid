#!/usr/bin/env python3
"""
VergeGrid Region Bootstrap (create-region.py)
Automatically creates the default Landing region and estate.
Assigns the estate owner as the God user from the database.
Used by the VergeGrid installer during first-time setup.
"""

import configparser
import os
import shutil
import sys
import uuid
import mysql.connector
from cryptography.fernet import Fernet
from configparser import ConfigParser
from pathlib import Path

# --- Constants ---
BASE_DIR = Path(__file__).resolve().parents[1]
REGIONS_DIR = BASE_DIR / "Regions"
ACTIVE_DIR = REGIONS_DIR / "Active"
ARCHIVE_DIR = REGIONS_DIR / "Archive"
TEMPLATES_DIR = REGIONS_DIR / "Templates"
REGIONS_INI = REGIONS_DIR / "Regions.ini"

# Default region parameters
DEFAULT_REGION_NAME = "Verge Landing"
DEFAULT_ESTATE_NAME = "Landings"
DEFAULT_TEMPLATE = "256_Default.ini"
DEFAULT_LOCATION = "9300,9300"
DEFAULT_PORT = "8005"

# --- Credential Loader ---
def load_encrypted_credentials(user_key="robustuser", debug=False):
    """Decrypt VergeGrid MySQL credentials from creds.conf using vault.key."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "creds.conf")
    vault_path = os.path.join(base_dir, "vault.key")

    if not os.path.exists(creds_path) or not os.path.exists(vault_path):
        print("[FATAL] Missing creds.conf or vault.key. Run secure_mysql_root.py first.")
        sys.exit(1)

    # Load AES key
    with open(vault_path, "rb") as f:
        key = f.read()
    fernet = Fernet(key)

    # Read encrypted credentials
    config = ConfigParser()
    config.read(creds_path, encoding="utf-8")

    try:
        encrypted_pw = config["Encrypted"][user_key]
        decrypted_pw = fernet.decrypt(encrypted_pw.encode()).decode()
        if debug:
            print(f"[DEBUG] Successfully decrypted password for '{user_key}'.")
        return decrypted_pw
    except Exception as e:
        print(f"[ERROR] Unable to decrypt {user_key} password: {e}")
        sys.exit(1)

# --- Helper functions ---
def ensure_dirs():
    """Ensure region directory structure exists."""
    for d in [REGIONS_DIR, ACTIVE_DIR, ARCHIVE_DIR, TEMPLATES_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    if not REGIONS_INI.exists():
        with open(REGIONS_INI, "w", encoding="utf-8") as f:
            f.write("[Regions]\n")

    # Ensure default template exists
    default_template = TEMPLATES_DIR / DEFAULT_TEMPLATE
    if not default_template.exists():
        default_template.write_text(
            """[Region]
RegionName = DefaultRegion
RegionUUID = AUTO
Location = 1000,1000
InternalAddress = 0.0.0.0
InternalPort = 9000
AllowAlternatePorts = False
ExternalHostName = SYSTEMIP
""",
            encoding="utf-8",
        )

def generate_uuid():
    return str(uuid.uuid4())

def read_regions():
    cfg = configparser.ConfigParser()
    cfg.read(REGIONS_INI, encoding="utf-8")
    if "Regions" not in cfg:
        cfg["Regions"] = {}
    return cfg

def write_regions(cfg):
    with open(REGIONS_INI, "w", encoding="utf-8") as f:
        cfg.write(f)

def get_god_user(debug=False):
    """Fetch the first God user (UserLevel >= 250) from the robust DB using decrypted creds."""
    mysql_user = "robustuser"
    mysql_pw = load_encrypted_credentials("robustuser", debug=debug)
    mysql_db = "robust"

    try:
        conn = mysql.connector.connect(
            host="localhost",
            user=mysql_user,
            password=mysql_pw,
            database=mysql_db
        )
        cursor = conn.cursor()
        cursor.execute("SELECT PrincipalID, FirstName, LastName FROM useraccounts WHERE UserLevel >= 250 LIMIT 1;")
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            pid, first, last = row
            return pid, f"{first} {last}"
        else:
            return None, None
    except Exception as e:
        print(f"[WARN] Could not fetch God user: {e}")
        return None, None

def create_default_region():
    """Automatically create Verge Landing region and estate."""
    ensure_dirs()

    god_id, god_name = get_god_user()
    if not god_id:
        print("[WARN] No God user found. Owner will be left blank.")

    template_path = TEMPLATES_DIR / DEFAULT_TEMPLATE
    if not template_path.exists():
        print(f"[FATAL] Missing template file: {template_path}")
        sys.exit(1)

    region_path = ACTIVE_DIR / f"{DEFAULT_REGION_NAME}.ini"
    shutil.copy(template_path, region_path)

    content = region_path.read_text(encoding="utf-8")
    content = content.replace("DefaultRegion", DEFAULT_REGION_NAME)
    content = content.replace("AUTO", generate_uuid())
    content = content.replace("1000,1000", DEFAULT_LOCATION)
    content = content.replace("9000", DEFAULT_PORT)
    region_path.write_text(content, encoding="utf-8")

    cfg = read_regions()
    cfg["Regions"][DEFAULT_REGION_NAME] = f"Active/{DEFAULT_REGION_NAME}.ini"
    write_regions(cfg)

    # Estate override file (for DreamGrid-style estates)
    estate_ini = REGIONS_DIR / "Landings" / f"{DEFAULT_ESTATE_NAME}.ini"
    estate_ini.parent.mkdir(parents=True, exist_ok=True)
    estate_ini.write_text(
        f"""[EstateSettings]
EstateName = {DEFAULT_ESTATE_NAME}
EstateOwner = {god_id or '00000000-0000-0000-0000-000000000000'}
EstateOwnerName = {god_name or 'Unknown User'}
""",
        encoding="utf-8",
    )

    print(f"[OK] Created region configuration: {region_path}")
    print(f"     Region UUID: {generate_uuid()}")
    print(f"     Port: {DEFAULT_PORT}")
    print(f"     Location: {DEFAULT_LOCATION}")
    print(f"[OK] Created estate override: {estate_ini}")

    if god_id:
        print(f"[OK] Assigned estate owner: {god_name} ({god_id})")

    print("\n✅ Landing estate fully initialized!")
    print("   To start your simulator, run:")
    print(f"   OpenSim.exe -inifile=Regions/Landings/{DEFAULT_ESTATE_NAME}.ini\n")

# --- Main entry ---
def main():
    print("\n=== VergeGrid Landing Estate Initializer (Automated) ===")
    create_default_region()

if __name__ == "__main__":
    main()

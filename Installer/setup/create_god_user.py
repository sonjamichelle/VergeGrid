#!/usr/bin/env python3
# ==============================================================
# VergeGrid God User Creator (Direct MySQL Injection)
# Uses AES-encrypted credentials from creds.conf (vault.key)
# Creates a God (admin) user in robust.useraccounts and robust.auth
# ==============================================================

import os
import sys
import subprocess

# --------------------------------------------------------------
# Ensure required dependencies are installed (self-healing)
# --------------------------------------------------------------
def ensure_package(pkg_name, import_name=None):
    """Auto-install a required package if missing."""
    try:
        __import__(import_name or pkg_name)
    except ImportError:
        print(f"[INFO] Missing dependency: {pkg_name}. Installing automatically...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.run([sys.executable, "-m", "pip", "install", pkg_name], check=True)

# Ensure core packages are available before imports
ensure_package("mysql-connector-python", "mysql.connector")
ensure_package("cryptography")

# --------------------------------------------------------------
# Imports (safe to do now)
# --------------------------------------------------------------
import mysql.connector
from cryptography.fernet import Fernet
import uuid
import time
import hashlib
import re
import argparse
from getpass import getpass
from configparser import ConfigParser

# --------------------------------------------------------------
# Encryption Helper
# --------------------------------------------------------------
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

# --------------------------------------------------------------
# Helper: generate proper RFC 4122 UUIDv4
# --------------------------------------------------------------
def generate_valid_uuid():
    """Generate a proper UUIDv4 string in canonical 8-4-4-4-12 format."""
    u = str(uuid.uuid4())
    pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I
    )
    if not pattern.match(u):
        print("[WARN] Generated UUID failed validation, regenerating...")
        return generate_valid_uuid()
    return u.lower()

# --------------------------------------------------------------
# Prompt user info
# --------------------------------------------------------------
def collect_user_info():
    print("\n=== VergeGrid God User Database Creator ===")
    first = input("First Name: ").strip()
    last = input("Last Name: ").strip()
    email = input("Email: ").strip()

    while True:
        pw1 = getpass("Password: ")
        pw2 = getpass("Re-enter Password: ")
        if pw1 != pw2:
            print("❌ Passwords do not match. Try again.\n")
            continue
        if len(pw1) < 8:
            print("❌ Password must be at least 8 characters long.\n")
            continue
        break
    return first, last, email, pw1

# --------------------------------------------------------------
# Main: insert into useraccounts and auth tables
# --------------------------------------------------------------
def create_god_user(first, last, email, password, debug=False):
    mysql_user = "robustuser"
    mysql_pw = load_encrypted_credentials("robustuser", debug=debug)
    mysql_db = "robust"

    if debug:
        print(f"[DEBUG] Connecting to MySQL as '{mysql_user}' on DB '{mysql_db}'...")

    try:
        conn = mysql.connector.connect(
            host="localhost",
            user=mysql_user,
            password=mysql_pw,
            database=mysql_db
        )
        cursor = conn.cursor()
        if debug:
            print(f"[DEBUG] Connection successful as '{mysql_user}'.")
    except mysql.connector.Error as err:
        print(f"[ERROR] Could not connect to MySQL as {mysql_user}: {err}")
        sys.exit(1)

    principal_id = generate_valid_uuid()
    created_time = int(time.time())

    print(f"\n[INFO] Creating God user '{first} {last}'")
    print(f"[INFO] PrincipalID: {principal_id}")

    # --- useraccounts ---
    cursor.execute("""
        INSERT INTO useraccounts
        (PrincipalID, ScopeID, FirstName, LastName, Email, ServiceURLs,
         Created, UserLevel, UserFlags, UserTitle, active)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        principal_id,
        "00000000-0000-0000-0000-000000000000",
        first,
        last,
        email,
        "",
        created_time,
        250,  # God level
        0,
        1,
        1
    ))

    # --- auth ---
    salt = uuid.uuid4().hex
    salted_pw = hashlib.md5((password + ":" + salt).encode()).hexdigest()
    cursor.execute("""
        INSERT INTO auth
        (UUID, passwordHash, passwordSalt, webLoginKey)
        VALUES (%s,%s,%s,%s)
    """, (
        principal_id,
        salted_pw,
        salt,
        str(uuid.uuid4())
    ))

    conn.commit()

    print("\n✅ God user created in:")
    print("   - robust.useraccounts")
    print("   - robust.auth\n")
    print(f"PrincipalID: {principal_id}")
    print(f"UserLevel: 250 (God)")
    print(f"Created: {time.ctime(created_time)}\n")

    cursor.close()
    conn.close()

    if debug:
        print(f"[DEBUG] Connection closed. God user '{first} {last}' successfully inserted.")

# --------------------------------------------------------------
# Entry Point
# --------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VergeGrid God User Creator")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug output")
    args = parser.parse_args()

    first, last, email, pw = collect_user_info()
    create_god_user(first, last, email, pw, debug=args.debug)

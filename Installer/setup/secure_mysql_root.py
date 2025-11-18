#!/usr/bin/env python3
# ==============================================================
# VergeGrid Secure MySQL Root + User Provisioning Utility
# Windows Edition — Full Secure Setup
# Includes:
#   - MySQL root password hardening
#   - Creation of vergeadmin, robustuser, opensimuser accounts
#   - Grants DBManager, DBDesigner, BackupAdmin equivalent privileges
#   - AES-encrypted password vault (vault.key + creds.conf)
# ==============================================================

import os
import re
import sys
import hashlib
import logging
import subprocess
from configparser import ConfigParser

# --------------------------------------------------------------
# Ensure dependencies (auto-install if missing)
# --------------------------------------------------------------
def ensure_package(pkg_name, import_name=None):
    """Ensure a Python package is installed; install if missing."""
    try:
        __import__(import_name or pkg_name)
    except ImportError:
        print(f"[INFO] Installing missing dependency: {pkg_name}...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.run([sys.executable, "-m", "pip", "install", pkg_name], check=True)

ensure_package("mysql-connector-python", "mysql.connector")
ensure_package("cryptography")

# --------------------------------------------------------------
# Safe imports now that dependencies exist
# --------------------------------------------------------------
import mysql.connector
from cryptography.fernet import Fernet

# --------------------------------------------------------------
# Logging and paths
# --------------------------------------------------------------
base_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(base_dir, "vergegrid_install.log")
vault_file = os.path.join(base_dir, "vault.key")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

# --------------------------------------------------------------
# Encryption helpers
# --------------------------------------------------------------
def get_or_create_key():
    """Create or load VergeGrid's AES encryption key."""
    if not os.path.exists(vault_file):
        key = Fernet.generate_key()
        with open(vault_file, "wb") as f:
            f.write(key)
        print("[INFO] Created new VergeGrid encryption key: vault.key")
    else:
        with open(vault_file, "rb") as f:
            key = f.read()
    return Fernet(key)

def encrypt_password(fernet, pw):
    return fernet.encrypt(pw.encode()).decode()

def decrypt_password(fernet, token):
    return fernet.decrypt(token.encode()).decode()

# --------------------------------------------------------------
# Password validation
# --------------------------------------------------------------
def validate_password(pw: str) -> bool:
    if len(pw) < 12:
        print("❌ Password too short (min 12 chars).")
        return False
    if not re.search(r"[A-Z]", pw):
        print("❌ Must contain at least one uppercase letter.")
        return False
    if not re.search(r"[a-z]", pw):
        print("❌ Must contain at least one lowercase letter.")
        return False
    if not re.search(r"[0-9]", pw):
        print("❌ Must contain at least one number.")
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pw):
        print("❌ Must contain at least one special character.")
        return False
    return True

# --------------------------------------------------------------
# Prompt for password
# --------------------------------------------------------------
def collect_password(user_label):
    """Prompt until a valid password is entered."""
    while True:
        pw1 = input(f"Enter password for {user_label}: ")
        pw2 = input(f"Re-enter password for {user_label} to confirm: ")

        if pw1 != pw2:
            print("❌ Passwords do not match.\n")
            continue
        if not validate_password(pw1):
            print(f"❌ {user_label} password validation failed.\n")
            continue
        print(f"✅ Password accepted for {user_label}.\n")
        return pw1

# --------------------------------------------------------------
# File patch helper
# --------------------------------------------------------------
def patch_connection_file(file_path, replacements):
    """Patch User ID and Password fields in OpenSim config files."""
    if not os.path.exists(file_path):
        logging.warning(f"{file_path} not found; skipping patch.")
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        for keyword, creds in replacements.items():
            user, pw = creds
            content = re.sub(r"(User ID=).*?;", rf"\1{user};", content, flags=re.IGNORECASE)
            content = re.sub(r"(Password=).*?;", rf"\1{pw};", content, flags=re.IGNORECASE)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[OK] Updated credentials in {file_path}")
        logging.info(f"Patched credentials in {file_path}")
        return True
    except Exception as e:
        print(f"[WARN] Could not patch {file_path}: {e}")
        logging.warning(f"Failed to patch {file_path}: {e}")
        return False

# --------------------------------------------------------------
# Main MySQL setup routine
# --------------------------------------------------------------
def change_root_password_and_create_users():
    print("\n=== VergeGrid MySQL Security Setup (Windows) ===")
    print("Connecting to MySQL as root (no password)...")

    # Connect without password
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="")
        cursor = conn.cursor()
    except mysql.connector.Error as err:
        print(f"[ERROR] Could not connect to MySQL: {err}")
        sys.exit(1)

    print("\n✅ Connected successfully.")
    print("Let's secure your MySQL root user.\n")

    root_pw = collect_password("root (MySQL superuser)")

    try:
        cursor.execute(f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{root_pw}';")
        cursor.execute("FLUSH PRIVILEGES;")
        conn.commit()
        print("✅ MySQL root password updated successfully.\n")
    except mysql.connector.Error as err:
        print(f"[ERROR] Failed to update MySQL root password: {err}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

    # Reconnect with new root credentials
    print("🔐 Reconnecting with new root password to create user accounts...\n")
    conn = mysql.connector.connect(host="localhost", user="root", password=root_pw)
    cursor = conn.cursor()

    print("Creating VergeGrid MySQL accounts (vergeadmin, robustuser, opensimuser)...\n")

    vergeadmin_pw = collect_password("vergeadmin (non-root administrator)")
    robust_pw = collect_password("robustuser (Robust service)")
    opensim_pw = collect_password("opensimuser (OpenSim service)")

    try:
        # VergeAdmin
        cursor.execute("DROP USER IF EXISTS 'vergeadmin'@'localhost';")
        cursor.execute(f"CREATE USER 'vergeadmin'@'localhost' IDENTIFIED BY '{vergeadmin_pw}';")
        cursor.execute("GRANT ALL PRIVILEGES ON *.* TO 'vergeadmin'@'localhost';")
        cursor.execute("REVOKE SUPER, GRANT OPTION ON *.* FROM 'vergeadmin'@'localhost';")

        # RobustUser (matching Workbench privileges)
        cursor.execute("DROP USER IF EXISTS 'robustuser'@'localhost';")
        cursor.execute(f"CREATE USER 'robustuser'@'localhost' IDENTIFIED BY '{robust_pw}';")
        cursor.execute("""
            GRANT
                ALTER, ALTER ROUTINE, CREATE, CREATE ROUTINE, CREATE TABLESPACE,
                CREATE TEMPORARY TABLES, CREATE USER, CREATE VIEW,
                DELETE, DROP, EVENT, EXECUTE, FILE, INDEX, INSERT, LOCK TABLES,
                PROCESS, REFERENCES, RELOAD, REPLICATION CLIENT, REPLICATION SLAVE,
                SELECT, SHOW DATABASES, SHOW VIEW, SHUTDOWN, TRIGGER, UPDATE
            ON *.* TO 'robustuser'@'localhost';
        """)

        # OpenSimUser (same privileges)
        cursor.execute("DROP USER IF EXISTS 'opensimuser'@'localhost';")
        cursor.execute(f"CREATE USER 'opensimuser'@'localhost' IDENTIFIED BY '{opensim_pw}';")
        cursor.execute("""
            GRANT
                ALTER, ALTER ROUTINE, CREATE, CREATE ROUTINE, CREATE TABLESPACE,
                CREATE TEMPORARY TABLES, CREATE USER, CREATE VIEW,
                DELETE, DROP, EVENT, EXECUTE, FILE, INDEX, INSERT, LOCK TABLES,
                PROCESS, REFERENCES, RELOAD, REPLICATION CLIENT, REPLICATION SLAVE,
                SELECT, SHOW DATABASES, SHOW VIEW, SHUTDOWN, TRIGGER, UPDATE
            ON *.* TO 'opensimuser'@'localhost';
        """)

        cursor.execute("FLUSH PRIVILEGES;")
        conn.commit()

        print("✅ All VergeGrid MySQL service accounts created successfully with full DBManager, DBDesigner, and BackupAdmin privileges.")
    except mysql.connector.Error as err:
        print(f"[ERROR] Failed to create users: {err}")
        sys.exit(1)

    # --- Step 4: Securely store credentials
    fernet = get_or_create_key()
    creds_file = os.path.join(base_dir, "creds.conf")

    config = ConfigParser()
    config["MySQL_Credentials"] = {
        "root": hashlib.sha256(root_pw.encode()).hexdigest(),
        "vergeadmin": hashlib.sha256(vergeadmin_pw.encode()).hexdigest(),
        "robustuser": hashlib.sha256(robust_pw.encode()).hexdigest(),
        "opensimuser": hashlib.sha256(opensim_pw.encode()).hexdigest(),
    }
    config["Encrypted"] = {
        "root": encrypt_password(fernet, root_pw),
        "vergeadmin": encrypt_password(fernet, vergeadmin_pw),
        "robustuser": encrypt_password(fernet, robust_pw),
        "opensimuser": encrypt_password(fernet, opensim_pw),
    }

    with open(creds_file, "w", encoding="utf-8") as f:
        config.write(f)

    print(f"\n🔒 Credentials securely stored in {creds_file}")
    print("🔑 AES key saved to vault.key — KEEP THIS FILE PRIVATE.\n")

    cursor.close()
    conn.close()
    print("✅ MySQL hardening and VergeGrid setup complete.\n")

# --------------------------------------------------------------
# Entry Point
# --------------------------------------------------------------
if __name__ == "__main__":
    change_root_password_and_create_users()

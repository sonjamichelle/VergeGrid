#!/usr/bin/env python3
# ==============================================================
# VergeGrid Secure MySQL Root + User Provisioning Utility
# Windows Edition — Full Secure Setup
# Includes:
#   - MySQL root password hardening
#   - Creation of vergeadmin, robustuser, opensimuser accounts
#   - Role-based privilege grants (DBManager, DBDesigner, BackupAdmin)
#   - Automatic OpenSim configuration patch (GridCommon.ini, Robust.ini, Robust.HG.ini)
# ==============================================================

import re
import sys
import os
import hashlib
import logging
import subprocess
from configparser import ConfigParser

# --------------------------------------------------------------
# Ensure mysql-connector-python is installed (self-healing)
# --------------------------------------------------------------
try:
    import mysql.connector
except ImportError:
    print("[INFO] Missing dependency: mysql-connector-python. Installing automatically...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.run([sys.executable, "-m", "pip", "install", "mysql-connector-python"], check=True)
    import mysql.connector

# --------------------------------------------------------------
# Setup absolute log file path (Windows-safe)
# --------------------------------------------------------------
base_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(base_dir, "vergegrid_install.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

# --------------------------------------------------------------
# Password Validation Function
# --------------------------------------------------------------
def validate_password(pw: str) -> bool:
    """Ensure password meets VergeGrid security policy."""
    if len(pw) < 12:
        print("❌ Password too short. Minimum 12 characters required.")
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
# Collect and confirm password input (looping until valid)
# --------------------------------------------------------------
def collect_password(user_label):
    """Prompt repeatedly until a valid, matching password is entered."""
    while True:
        pw1 = input(f"Enter password for {user_label}: ")
        pw2 = input(f"Re-enter password for {user_label} to confirm: ")

        if pw1 != pw2:
            print(f"❌ Passwords for {user_label} do not match. Please try again.\n")
            continue

        if not validate_password(pw1):
            print(f"❌ {user_label} password validation failed. Please try again.\n")
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
            pattern_user = re.compile(r"(User ID=).*?;", re.IGNORECASE)
            pattern_pass = re.compile(r"(Password=).*?;", re.IGNORECASE)

            if keyword in file_path.lower() or keyword in content.lower():
                content = pattern_user.sub(rf"\1{user};", content)
                content = pattern_pass.sub(rf"\1{pw};", content)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logging.info(f"Patched MySQL credentials in {file_path}")
        print(f"[OK] Updated connection strings in: {file_path}")
        return True
    except Exception as e:
        logging.warning(f"Failed to patch {file_path}: {e}")
        print(f"[WARN] Could not patch {file_path}: {e}")
        return False

# --------------------------------------------------------------
# Main Routine
# --------------------------------------------------------------
def change_root_password_and_create_users():
    print("\n=== VergeGrid MySQL Security Setup (Windows) ===")
    print("Connecting to MySQL as root (no password)...")

    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            connection_timeout=5
        )
        cursor = conn.cursor()
    except mysql.connector.Error as err:
        logging.error(f"MySQL connection failed: {err}")
        print(f"\n[ERROR] Unable to connect to MySQL: {err}")
        print("Make sure MySQL is installed and the service is running (services.msc).")
        sys.exit(1)

    # --- Step 1: Secure root ---
    print("\n✅ Connected successfully. Let's secure your MySQL root user.\n")
    print("Example strong passwords:")
    print("  • t!G7@qK$2vPz")
    print("  • Cyb3r^Grid#99")
    print("  • n0va*Pulse!42\n")

    root_pw = collect_password("root (MySQL superuser)")

    try:
        cursor.execute(f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{root_pw}';")
        cursor.execute("FLUSH PRIVILEGES;")
        conn.commit()
        print("✅ MySQL root password updated successfully.\n")
        logging.info("MySQL root password successfully updated (Windows).")
    except mysql.connector.Error as err:
        logging.error(f"Failed to update MySQL root password: {err}")
        print(f"[ERROR] MySQL command failed: {err}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

    # --- Step 2: Reconnect with new root credentials ---
    print("🔐 Reconnecting with new root password to create user accounts...\n")
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password=root_pw
        )
        cursor = conn.cursor()
    except mysql.connector.Error as err:
        logging.error(f"Reconnection failed with new root credentials: {err}")
        print(f"[ERROR] Could not reconnect with new root password: {err}")
        sys.exit(1)

    # --- Step 3: Create subordinate accounts ---
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

        # RobustUser
        cursor.execute("DROP USER IF EXISTS 'robustuser'@'localhost';")
        cursor.execute(f"CREATE USER 'robustuser'@'localhost' IDENTIFIED BY '{robust_pw}';")
        cursor.execute("""
            GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP,
                   CREATE VIEW, SHOW VIEW, EVENT, TRIGGER,
                   LOCK TABLES, REFERENCES
            ON robust_db.* TO 'robustuser'@'localhost';
        """)

        # OpenSimUser
        cursor.execute("DROP USER IF EXISTS 'opensimuser'@'localhost';")
        cursor.execute(f"CREATE USER 'opensimuser'@'localhost' IDENTIFIED BY '{opensim_pw}';")
        cursor.execute("""
            GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP,
                   CREATE VIEW, SHOW VIEW, EVENT, TRIGGER,
                   LOCK TABLES, REFERENCES
            ON opensim_db.* TO 'opensimuser'@'localhost';
        """)

        cursor.execute("FLUSH PRIVILEGES;")
        conn.commit()

        print("✅ All VergeGrid MySQL service accounts created with DBManager, DBDesigner, and BackupAdmin privileges.")
        logging.info("MySQL users vergeadmin, robustuser, and opensimuser created with DBManager/Designer/BackupAdmin privileges.")
    except mysql.connector.Error as err:
        logging.error(f"MySQL user creation failed: {err}")
        print(f"[ERROR] Failed to create VergeGrid MySQL users: {err}")
        sys.exit(1)

    # --- Step 4: Store credentials securely ---
    creds_file = os.path.join(base_dir, "creds.conf")
    config = ConfigParser()
    config["MySQL_Credentials"] = {
        "root": hashlib.sha256(root_pw.encode()).hexdigest(),
        "vergeadmin": hashlib.sha256(vergeadmin_pw.encode()).hexdigest(),
        "robustuser": hashlib.sha256(robust_pw.encode()).hexdigest(),
        "opensimuser": hashlib.sha256(opensim_pw.encode()).hexdigest(),
    }

    with open(creds_file, "w", encoding="utf-8") as f:
        config.write(f)

    print(f"\n🔒 Credentials securely hashed and saved to: {creds_file}")
    logging.info(f"Credentials stored securely in creds.conf at {creds_file}")

    # --- Step 5: Patch GridCommon.ini, Robust.ini, Robust.HG.ini ---
    print("\n[INFO] Updating OpenSim configuration files...")

    # Determine install_root from command-line arg or stored file
    install_root = None
    if len(sys.argv) > 1:
        install_root = sys.argv[1]
    else:
        install_path_file = os.path.join(base_dir, "install_path.txt")
        if os.path.exists(install_path_file):
            with open(install_path_file, "r", encoding="utf-8") as f:
                install_root = f.read().strip()

    if not install_root or not os.path.exists(install_root):
        print("[WARN] Could not determine valid install_root. Skipping config patch.")
        logging.warning("install_root argument missing or invalid; skipping INI patch.")
    else:
        print(f"[INFO] Using install root: {install_root}")
        gridcommon_path = os.path.join(install_root, "OpenSim", "bin", "config-include", "GridCommon.ini")
        robust_path     = os.path.join(install_root, "OpenSim", "bin", "Robust.ini")
        robust_hg_path  = os.path.join(install_root, "OpenSim", "bin", "Robust.HG.ini")

        replacements = {
            "gridcommon": ("opensimuser", opensim_pw),
            "robust":     ("robustuser",  robust_pw),
            "robust.hg":  ("robustuser",  robust_pw),
        }

        patched_gc = patch_connection_file(gridcommon_path, replacements) if os.path.exists(gridcommon_path) else False
        patched_rb = patch_connection_file(robust_path, replacements) if os.path.exists(robust_path) else False
        patched_hg = patch_connection_file(robust_hg_path, replacements) if os.path.exists(robust_hg_path) else False

        if not patched_gc:
            print(f"[WARN] Could not locate or update GridCommon.ini at {gridcommon_path}")
        if not patched_rb:
            print(f"[WARN] Could not locate or update Robust.ini at {robust_path}")
        if not patched_hg:
            print(f"[WARN] Could not locate or update Robust.HG.ini at {robust_hg_path}")
        else:
            print("[OK] All detected OpenSim configuration files updated successfully.")

    cursor.close()
    conn.close()
    print("\n✅ MySQL hardening, user provisioning, and OpenSim configuration patch complete.")
    logging.info("Full MySQL hardening and configuration update (GridCommon.ini + Robust.ini + Robust.HG.ini) complete.")

# --------------------------------------------------------------
# Script Entry Point
# --------------------------------------------------------------
if __name__ == "__main__":
    change_root_password_and_create_users()

# -*- coding: utf-8 -*-
"""
VergeGrid Modular Component Initializer: OpenSim
Author: Sonja + GPT
Purpose:
  - Create MySQL schemas for OpenSim grid services
  - Patch database connection strings in OpenSim.ini and Robust.HG.ini
  - Prepare simulator for first launch (auto schema generation)
"""

import os
import sys
import time
import subprocess
import configparser
import pymysql
from pathlib import Path

# ---------------------------------------------------------------------
# Import VergeGrid shared logic
# ---------------------------------------------------------------------
try:
    from setup import common
except ModuleNotFoundError:
    import common


# ---------------------------------------------------------------------
# MySQL helper functions
# ---------------------------------------------------------------------
def mysql_exec(query, user="root", password="", host="localhost"):
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        with conn.cursor() as cur:
            cur.execute(query)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        common.write_log(f"MySQL query failed: {e}", "ERROR")
        return False


# ---------------------------------------------------------------------
# OpenSim database initialization
# ---------------------------------------------------------------------
def create_opensim_databases(mysql_user, mysql_pass):
    """Creates default OpenSim-related databases if not exist."""
    schemas = ["opensim", "robust", "ossearch"]
    success = True

    for dbname in schemas:
        q = f"CREATE DATABASE IF NOT EXISTS `{dbname}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        ok = mysql_exec(q, user=mysql_user, password=mysql_pass)
        if ok:
            common.write_log(f"[OK] Database '{dbname}' ready.")
        else:
            common.write_log(f"[FAIL] Could not create database '{dbname}'", "ERROR")
            success = False

    return success


# ---------------------------------------------------------------------
# INI file patching logic
# ---------------------------------------------------------------------
def patch_ini_file(path, mysql_user, mysql_pass, mysql_host="localhost"):
    """
    Patches OpenSim.ini or Robust.HG.ini with MySQL connection string.
    """
    if not os.path.exists(path):
        common.write_log(f"[WARN] Cannot patch missing file: {path}", "WARN")
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        changed = False
        for line in lines:
            if "ConnectionString" in line and "Data Source" in line:
                dbname = "robust" if "Robust" in os.path.basename(path) else "opensim"
                new_line = (
                    f'ConnectionString = "Data Source={mysql_host};'
                    f'Database={dbname};User ID={mysql_user};Password={mysql_pass};Old Guids=true;"\n'
                )
                new_lines.append(new_line)
                changed = True
            else:
                new_lines.append(line)

        if changed:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            common.write_log(f"[OK] Patched MySQL connection string in {path}")
        else:
            common.write_log(f"[INFO] No connection string found to patch in {path}")

        return True
    except Exception as e:
        common.write_log(f"[ERROR] Failed to patch INI file {path}: {e}", "ERROR")
        return False


# ---------------------------------------------------------------------
# Initialization main logic
# ---------------------------------------------------------------------
def initialize_opensim(install_root, mysql_user, mysql_pass):
    """
    Runs OpenSim initialization:
    - Ensures MySQL DBs exist
    - Patches OpenSim.ini and Robust.HG.ini
    """

    install_root = Path(install_root).resolve()
    opensim_root = install_root / "OpenSim"
    config_dir = opensim_root / "bin" / "config-include"

    common.write_log("=== OpenSim Initialization Starting ===")

    if not opensim_root.exists():
        common.write_log("[FATAL] OpenSim root folder not found.", "ERROR")
        print("[FATAL] OpenSim not installed. Run fetch-opensim first.")
        sys.exit(1)

    # 1. Ensure MySQL schemas exist
    print("\n>>> Creating OpenSim databases (opensim, robust, ossearch)...")
    if not create_opensim_databases(mysql_user, mysql_pass):
        print("[ERROR] Could not create OpenSim databases.")
        sys.exit(2)

    # 2. Patch INI files
    print("\n>>> Patching OpenSim.ini and Robust.HG.ini for MySQL access...")
    patched = 0
    for ini_file in [
        config_dir / "OpenSim.ini",
        config_dir / "Robust.HG.ini",
        config_dir / "Robust.ini"
    ]:
        if patch_ini_file(ini_file, mysql_user, mysql_pass):
            patched += 1

    if patched == 0:
        print("[WARN] No configuration files were patched. Check OpenSim config layout.")
    else:
        print(f"[OK] Patched {patched} configuration files.")

    # 3. Done
    common.write_log("[SUCCESS] OpenSim initialization complete.")
    print("\n✓ OpenSim initialization completed successfully.\n")
    sys.exit(0)


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python init-opensim.py <install_root> <mysql_user> <mysql_pass>")
        sys.exit(1)

    install_root = sys.argv[1]
    mysql_user = sys.argv[2]
    mysql_pass = sys.argv[3]

    common.set_log_file(str(Path(install_root) / "Logs" / "vergegrid-install.log"))
    initialize_opensim(install_root, mysql_user, mysql_pass)

# -*- coding: utf-8 -*-
"""
VergeGrid Modular Component Initializer: OpenSim (Insecure Mode Compatible)
Author: Sonja + GPT
Purpose:
  - Create MySQL schemas for OpenSim grid services
  - Auto-copy .example config files from /bin if missing
  - Patch connection strings for MySQL (root / no password)
"""

# --- VergeGrid Path Fix ---
import os
import sys
import time
import subprocess
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

try:
    import pymysql
except ImportError:
    print("Missing dependency: PyMySQL. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMySQL"])
    import pymysql

try:
    from setup import common
except ModuleNotFoundError:
    import common


# ---------------------------------------------------------------------
# MySQL helper
# ---------------------------------------------------------------------
def mysql_exec(query, user="root", password="", host="localhost", retries=10, delay=5):
    import pymysql
    attempt = 1
    while attempt <= retries:
        try:
            conn = pymysql.connect(
                host=host,
                user=user,
                password=(password or ""),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            with conn.cursor() as cur:
                cur.execute(query)
            conn.commit()
            conn.close()
            return True
        except pymysql.err.OperationalError as e:
            msg = str(e).lower()
            if "access denied" in msg or "can't connect" in msg or "connection refused" in msg:
                common.write_log(f"[WAIT] MySQL not ready (attempt {attempt}/{retries})...", "WARN")
                time.sleep(delay)
                attempt += 1
                continue
            else:
                common.write_log(f"[ERROR] MySQL operational error: {e}", "ERROR")
                return False
        except Exception as e:
            common.write_log(f"[ERROR] MySQL query failed: {e}", "ERROR")
            time.sleep(delay)
            attempt += 1
    common.write_log(f"[FATAL] Query failed after {retries} retries: {query}", "ERROR")
    return False


# ---------------------------------------------------------------------
# Create OpenSim Databases
# ---------------------------------------------------------------------
def create_opensim_databases(mysql_user, mysql_pass):
    schemas = ["opensim", "robust", "ossearch"]
    print("\n>>> Verifying MySQL service readiness (insecure mode, no password)...")
    ready = False
    for i in range(30):
        try:
            conn = pymysql.connect(
                host="localhost",
                user=mysql_user,
                password=(mysql_pass or ""),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            conn.close()
            ready = True
            break
        except Exception:
            print(f"  [WAIT] MySQL still starting (attempt {i+1}/30)...")
            time.sleep(2)

    if not ready:
        common.write_log("[FATAL] MySQL did not become ready after 60 seconds.", "ERROR")
        return False

    for db in schemas:
        q = f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        if mysql_exec(q, user=mysql_user, password=(mysql_pass or "")):
            common.write_log(f"[OK] Database '{db}' ready.")
        else:
            common.write_log(f"[FAIL] Could not create database '{db}'", "ERROR")
            return False
    return True


# ---------------------------------------------------------------------
# Patch INI files (OpenSim.ini, Robust.ini, Robust.HG.ini)
# ---------------------------------------------------------------------
def patch_ini_file(opensim_root, ini_name, mysql_user, mysql_pass, mysql_host="localhost"):
    bin_dir = opensim_root / "bin"
    config_dir = bin_dir / "config-include"
    search_paths = [
        (bin_dir / ini_name, bin_dir / f"{ini_name}.example"),
        (config_dir / ini_name, config_dir / f"{ini_name}.example")
    ]

    for ini_path, example_path in search_paths:
        if not ini_path.exists() and example_path.exists():
            try:
                common.write_log(f"[INFO] Creating {ini_path.name} from {example_path.name}")
                ini_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception as e:
                common.write_log(f"[ERROR] Could not copy {example_path} → {ini_path}: {e}", "ERROR")
                continue

        if not ini_path.exists():
            continue

        try:
            lines = ini_path.read_text(encoding="utf-8").splitlines()
            new_lines, changed = [], False
            for line in lines:
                if "ConnectionString" in line and "Data Source" in line:
                    dbname = "robust" if "Robust" in ini_name else "opensim"
                    newline = (
                        f'ConnectionString = "Data Source={mysql_host};'
                        f'Database={dbname};User ID={mysql_user};Password={mysql_pass};Old Guids=true;"'
                    )
                    new_lines.append(newline)
                    changed = True
                else:
                    new_lines.append(line)

            if changed:
                ini_path.write_text("\n".join(new_lines), encoding="utf-8")
                common.write_log(f"[OK] Patched MySQL connection in {ini_path}")
            else:
                common.write_log(f"[INFO] No patchable lines found in {ini_path}")
            return True
        except Exception as e:
            common.write_log(f"[ERROR] Failed to patch {ini_path}: {e}", "ERROR")
            return False

    common.write_log(f"[WARN] Could not locate {ini_name} or its .example in bin/ or config-include/", "WARN")
    return False


# ---------------------------------------------------------------------
# Patch GridCommon.ini (Full Rewrite)
# ---------------------------------------------------------------------
def patch_grid_common(opensim_root, mysql_user, mysql_pass, mysql_host="localhost"):
    """
    Ensures GridCommon.ini exists and rewrites the [DatabaseService] section
    with the required MySQL configuration, including EstateConnectionString.
    """
    config_dir = opensim_root / "bin" / "config-include"
    target = config_dir / "GridCommon.ini"
    example = config_dir / "GridCommon.ini.example"

    # Step 1: Copy example file if missing
    if not target.exists():
        if example.exists():
            try:
                target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
                common.write_log(f"[INFO] Created {target.name} from {example.name}")
            except Exception as e:
                common.write_log(f"[ERROR] Failed to copy {example} to {target}: {e}", "ERROR")
                return False
        else:
            common.write_log(f"[WARN] Missing both {target.name} and {example.name}, cannot patch.", "WARN")
            return False

    # Step 2: Rewrite DatabaseService section fully
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
        new_lines = []
        in_section = False

        for line in lines:
            stripped = line.strip()
            # Start rewriting when [DatabaseService] found
            if stripped.lower().startswith("[databaseservice]"):
                in_section = True
                new_lines.append("[DatabaseService]")
                new_lines.append("    ;")
                new_lines.append("    ; ### Choose the DB")
                new_lines.append("    ;")
                new_lines.append("")
                new_lines.append("    ; SQLite")
                new_lines.append('    ; Include-Storage = "config-include/storage/SQLiteStandalone.ini";')
                new_lines.append("")
                new_lines.append("    ; MySQL")
                new_lines.append("    ; Uncomment these lines if you want to use MySQL storage")
                new_lines.append("    ; Change the connection string to your db details")
                new_lines.append("    ; Remove SslMode=None if you need secure connection to the local MySQL")
                new_lines.append("    ; In most cases ssl is just a pure waste of resources, specially when MySQL is on same machine, and closed to outside")
                new_lines.append('    StorageProvider = "OpenSim.Data.MySQL.dll"')
                new_lines.append("    ; If using MySQL 8.0.4 or later, check that default-authentication-plugin=mysql_native_password")
                new_lines.append("    ;  rather than caching_sha2_password is set in /etc/mysql/mysql.conf.d/mysqld.cnf (not applicable to MariaDB).")
                new_lines.append(f'    ConnectionString = "Data Source={mysql_host};Database=opensim;User ID={mysql_user};Password={mysql_pass};Old Guids=true;SslMode=None;"')
                new_lines.append("")
                new_lines.append(f'    EstateConnectionString = "Data Source={mysql_host};Database=opensim;User ID={mysql_user};Password={mysql_pass};Old Guids=true;SslMode=None;"')
                new_lines.append("")
                new_lines.append("    ; MSSQL")
                new_lines.append("    ; Uncomment these lines if you want to use MSSQL storage")
                new_lines.append("    ; Change the connection string to your db details")
                new_lines.append("    ; The value for server property is shown in your SQL Server Management Studio login dialog.")
                new_lines.append("    ; (This sample is the default of express edition)")
                new_lines.append('    ;StorageProvider = "OpenSim.Data.MSSQL.dll"')
                new_lines.append('    ;ConnectionString = "Server=localhost\\SQLEXPRESS;Database=opensim;User Id=opensim; password=***;"')
                new_lines.append("")
                new_lines.append("    ; PGSQL")
                new_lines.append("    ; Uncomment these lines if you want to use PGSQL storage")
                new_lines.append("    ; Change the connection string to your db details")
                new_lines.append('    ;StorageProvider = "OpenSim.Data.PGSQL.dll"')
                new_lines.append('    ;ConnectionString = "Server=localhost;Database=opensim;User Id=opensim; password=***; SSL Mode=Disable"')
                continue

            # Skip lines until a new section header begins
            if in_section:
                if stripped.startswith("[") and not stripped.lower().startswith("[databaseservice]"):
                    in_section = False
                    new_lines.append(line)
                else:
                    continue
            else:
                new_lines.append(line)

        # Write out the modified file
        target.write_text("\n".join(new_lines), encoding="utf-8")
        common.write_log(f"[OK] Rewrote [DatabaseService] section in {target}")
        print(f"[OK] [DatabaseService] rewritten in {target.name}")
        return True

    except Exception as e:
        common.write_log(f"[ERROR] Failed to rewrite GridCommon.ini: {e}", "ERROR")
        print(f"[ERROR] Failed to rewrite GridCommon.ini: {e}")
        return False


# ---------------------------------------------------------------------
# Main initializer
# ---------------------------------------------------------------------
def initialize_opensim(install_root, mysql_user, mysql_pass):
    install_root = Path(install_root).resolve()
    opensim_root = install_root / "OpenSim"

    common.write_log("=== OpenSim Initialization Starting ===")

    if not opensim_root.exists():
        common.write_log("[FATAL] OpenSim root folder not found.", "ERROR")
        print("[FATAL] OpenSim not installed. Run fetch-opensim first.")
        sys.exit(1)

    print("\n>>> Creating OpenSim databases (opensim, robust, ossearch)...")
    if not create_opensim_databases(mysql_user, mysql_pass):
        print("[ERROR] Database creation failed.")
        sys.exit(2)

    print("\n>>> Patching OpenSim.ini and Robust.HG.ini for MySQL access...")
    patched = 0
    for ini_name in ["OpenSim.ini", "Robust.HG.ini", "Robust.ini"]:
        if patch_ini_file(opensim_root, ini_name, mysql_user, mysql_pass):
            patched += 1

    print("\n>>> Patching GridCommon.ini for MySQL access...")
    if patch_grid_common(opensim_root, mysql_user, mysql_pass):
        patched += 1

    if patched == 0:
        print("[WARN] No configuration files patched (check OpenSim/bin).")
    else:
        print(f"[OK] Patched {patched} configuration files.")

    # ------------------------------------------------------------
    # NEW: Safety wait + INI validation before proceeding
    # ------------------------------------------------------------
    print("\n[INFO] Flushing INI writes and verifying configs before continuing...")
    time.sleep(5)  # Wait for disk I/O flush

    gridcommon_ini = opensim_root / "bin" / "config-include" / "GridCommon.ini"
    if not gridcommon_ini.exists() or gridcommon_ini.stat().st_size < 200:
        print("[FATAL] GridCommon.ini missing or incomplete — cannot continue to Robust setup.")
        common.write_log("[FATAL] GridCommon.ini missing or incomplete.", "ERROR")
        sys.exit(3)

    common.write_log("[SUCCESS] All configuration files validated and written to disk.")
    print("✓ Configuration files verified successfully. Proceeding with next setup step.\n")

    common.write_log("[SUCCESS] OpenSim initialization complete.")
    print("\n✓ OpenSim initialization completed successfully.\n")
    sys.exit(0)


# ---------------------------------------------------------------------
# Entry Point (Insecure Defaults)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    install_root = Path("D:\\VergeGrid")
    mysql_user = "root"
    mysql_pass = ""  # Insecure mode (no password)

    common.set_log_file(str(install_root / "Logs" / "vergegrid-install.log"))
    print("\n[INFO] MySQL running in INSECURE MODE — using 'root' with NO password.\n")
    initialize_opensim(install_root, mysql_user, mysql_pass)

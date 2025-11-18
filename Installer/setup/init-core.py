# -*- coding: utf-8 -*-
"""
VergeGrid Core OpenSim Configuration Initializer (init-core.py)
Author: Sonja + GPT
Purpose:
  - Ensure OpenSim.ini, GridCommon.ini, and GridHypergrid.ini exist
  - Patch required core sections for MySQL operation
  - Validate config-include folder structure
  - Prevent "[SimulationDataStore] missing" startup failures
"""

import os
import re
import sys
import shutil
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


# --------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------
MYSQL_HOST = "localhost"
MYSQL_DB = "opensim"
MYSQL_USER = "opensim"
MYSQL_PASS = "opensim"


# --------------------------------------------------------------------
# File Helpers
# --------------------------------------------------------------------
def ensure_file(source, target):
    """Copy source file to target if target missing."""
    if not os.path.exists(target) and os.path.exists(source):
        shutil.copy(source, target)
        print(f"[OK] Created {os.path.basename(target)} from example.")
        return True
    return False


def ensure_section(content, section_name, defaults):
    """Ensure a section exists with default key/values."""
    if f"[{section_name}]" not in content:
        section_text = f"\n\n[{section_name}]\n"
        for k, v in defaults.items():
            section_text += f"{k} = {v}\n"
        return content + section_text
    return content


# --------------------------------------------------------------------
# Core Patcher
# --------------------------------------------------------------------
def patch_opensim_ini(ini_path):
    """Validate and patch OpenSim.ini."""
    print(f"[INFO] Checking {ini_path} ...")
    with open(ini_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Un-comment includes
    content = re.sub(
        r"^\s*;?\s*(Include-Common\s*=\s*\"config-include/GridCommon.ini\")",
        r"\1", content, flags=re.MULTILINE)
    content = re.sub(
        r"^\s*;?\s*(Include-HG\s*=\s*\"config-include/GridHypergrid.ini\")",
        r"\1", content, flags=re.MULTILINE)

    # Ensure SimulationDataStore
    if "[SimulationDataStore]" not in content:
        content += (
            "\n\n[SimulationDataStore]\n"
            f"StorageProvider = \"OpenSim.Data.MySQL.dll\"\n"
            f"ConnectionString = \"Data Source={MYSQL_HOST};Database={MYSQL_DB};"
            f"User ID={MYSQL_USER};Password={MYSQL_PASS};Old Guids=true;\"\n"
        )
        print("[OK] Added [SimulationDataStore] section for MySQL.")

    # Ensure Startup block settings
    if "regionload_regionsdir" not in content:
        content = re.sub(
            r"(\[Startup\][^\[]*)",
            r"\1\nregionload_regionsdir = \"./Regions\"",
            content, flags=re.DOTALL
        )
        print("[OK] Added regionload_regionsdir to [Startup].")

    if "physics" not in content:
        content = re.sub(
            r"(\[Startup\][^\[]*)",
            r"\1\nphysics = ubOde",
            content, flags=re.DOTALL
        )
        print("[OK] Added default physics engine (ubOde).")

    # Ensure Network and Hypergrid
    content = ensure_section(content, "Network", {"http_listener_port": 8002})
    content = ensure_section(content, "Hypergrid", {"hypergrid_enabled": "true"})

    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[OK] Verified and patched OpenSim.ini.\n")


def patch_gridcommon_ini(gridcommon_path):
    """Patch GridCommon.ini with MySQL connection string."""
    print(f"[INFO] Checking {gridcommon_path} ...")
    with open(gridcommon_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Force MySQL connection settings
    pattern = r"(?<=ConnectionString\s*=\s*).*"
    conn_str = (
        f"Data Source={MYSQL_HOST};Database={MYSQL_DB};"
        f"User ID={MYSQL_USER};Password={MYSQL_PASS};Old Guids=true;"
    )
    if "ConnectionString" in content:
        content = re.sub(pattern, conn_str, content)
    else:
        content += f"\nConnectionString = \"{conn_str}\"\n"

    with open(gridcommon_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[OK] Verified GridCommon.ini connection string.\n")


def patch_gridhypergrid_ini(hg_path):
    """Ensure basic HG settings exist."""
    print(f"[INFO] Checking {hg_path} ...")
    with open(hg_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "HomeURI" not in content:
        content += (
            "\n[Hypergrid]\n"
            "HomeURI = http://localhost:8002/\n"
            "GatekeeperURI = http://localhost:8002/\n"
        )

    with open(hg_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[OK] Verified GridHypergrid.ini defaults.\n")


# --------------------------------------------------------------------
# MAIN ROUTINE
# --------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python init-core.py <install_root>")
        sys.exit(1)

    install_root = Path(sys.argv[1])
    opensim_bin = install_root / "OpenSim" / "bin"
    include_dir = opensim_bin / "config-include"

    logs_dir = install_root / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    common.set_log_file(str(logs_dir / "vergegrid-install.log"))
    common.write_log("=== VergeGrid Core OpenSim Initializer ===")

    # Ensure required files exist
    ini_example = opensim_bin / "OpenSim.ini.example"
    ini_file = opensim_bin / "OpenSim.ini"
    gridcommon_ex = include_dir / "GridCommon.ini.example"
    gridcommon_ini = include_dir / "GridCommon.ini"
    hg_ex = include_dir / "GridHypergrid.ini.example"
    hg_ini = include_dir / "GridHypergrid.ini"

    ensure_file(ini_example, ini_file)
    ensure_file(gridcommon_ex, gridcommon_ini)
    ensure_file(hg_ex, hg_ini)

    if not ini_file.exists():
        print("[FATAL] Missing OpenSim.ini — cannot continue.")
        common.write_log("[FATAL] Missing OpenSim.ini", "ERROR")
        sys.exit(1)

    # Patch configs
    patch_opensim_ini(str(ini_file))
    patch_gridcommon_ini(str(gridcommon_ini))
    patch_gridhypergrid_ini(str(hg_ini))

    # Final verification
    if "[SimulationDataStore]" not in open(ini_file, encoding="utf-8").read():
        print("[FATAL] OpenSim.ini still missing SimulationDataStore section!")
        common.write_log("[FATAL] OpenSim.ini missing SimulationDataStore", "ERROR")
        sys.exit(2)

    print("✅ Core OpenSim configuration verified and ready.\n")
    common.write_log("[OK] Core OpenSim configuration verified successfully.", "INFO")
    sys.exit(0)


# --------------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------------
if __name__ == "__main__":
    main()

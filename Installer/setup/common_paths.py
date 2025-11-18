#!/usr/bin/env python3
"""
Common path definitions for VergeGrid Installer components.
Ensures all scripts write into the user-chosen installation root,
never into the Installer directory itself.
"""

import os
from pathlib import Path

SETUP_DIR = Path(__file__).resolve().parent
INSTALL_PATH_FILE = SETUP_DIR / "install_path.txt"

if INSTALL_PATH_FILE.exists():
    INSTALL_ROOT = Path(INSTALL_PATH_FILE.read_text(encoding="utf-8").strip())
else:
    print("[WARN] install_path.txt missing — using current directory as fallback.")
    INSTALL_ROOT = Path.cwd()

# Core paths
BIN_DIR = INSTALL_ROOT / "OpenSim" / "bin"
LOGS_DIR = INSTALL_ROOT / "Logs"
DOWNLOADS_DIR = INSTALL_ROOT / "Downloads"
REGIONS_DIR = BIN_DIR / "Regions"
CONFIG_INCLUDE_DIR = BIN_DIR / "config-include"

def ensure_dirs():
    for d in [LOGS_DIR, DOWNLOADS_DIR, BIN_DIR, REGIONS_DIR, CONFIG_INCLUDE_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def get_log_path(name="vergegrid-install.log"):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / name

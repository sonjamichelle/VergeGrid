#!/usr/bin/env python3
# VergeGrid Common Utility Module
# Shared configuration, path, and I/O helpers for VergeGrid scripts.
# Author: Sonja + Code GPT

# --- VergeGrid Path Fix ---
import os
import sys

# Find VergeGrid root (one level up from /setup/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

import os
import hashlib
import datetime
import time
from pathlib import Path
from colorama import Fore, Style

INSTALL_MARKER = "vergegrid.conf"
SAVE_PATH = Path(r"C:\ProgramData\VergeGrid\install_path.txt")

# ============================================================
# Logging System (Console + File Output)
# ============================================================

def _fallback_log(msg):
    """Fallback logger used if no log() function is defined by caller."""
    print(msg)
    try:
        base_dir = Path(__file__).parent
        log_dir = base_dir / "Setup_Logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # --- Keep only last 10 logs ---
        logs = sorted(log_dir.glob("setup_*.log"), key=os.path.getmtime, reverse=True)
        for old in logs[10:]:
            try:
                old.unlink()
            except Exception:
                pass

        # --- Write to fallback log ---
        log_file = log_dir / f"vergegrid_fallback_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} {msg}\n")

    except Exception as e:
        print(f"[LOG ERROR] Could not write to fallback log: {e}")

def _get_logger():
    """Return a unified logger that prints to console and writes to Setup_Logs directory."""
    import inspect
    import datetime

    # Determine base directory relative to this script (e.g. D:\VergeGrid_Setup)
    base_dir = Path(__file__).parent
    log_dir = base_dir / "Setup_Logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"setup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    def _log(message):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        msg = f"{timestamp} {message}"
        print(msg)
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception as e:
            print(f"[LOG ERROR] Could not write to {log_file}: {e}")

    # If calling frame already defines a log function, chain both
    frame = inspect.currentframe().f_back
    if "log" in frame.f_globals:
        parent_log = frame.f_globals["log"]

        def combined_log(msg):
            parent_log(msg)
            _log(msg)
        return combined_log

    return _log


# ============================================================
# Helper: Hash / Checksum
# ============================================================

def calc_file_sha256(path):
    """Return SHA256 checksum of a file."""
    sha = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()
    except Exception:
        return None

# ============================================================
# Configuration Loader / Creator
# ============================================================

def _default_config(root="C:\\VergeGrid"):
    """Return default VergeGrid configuration lines."""
    return [
        "# VergeGrid System Configuration",
        "# Adjust component roots as needed. Changes take effect on next run.",
        f"PHP_ROOT={os.path.join(root, 'Apache', 'php')}",
        f"APACHE_ROOT={os.path.join(root, 'Apache')}",
        f"MYSQL_ROOT={os.path.join(root, 'MySQL')}",
        f"OPEN_SIM_ROOT={os.path.join(root, 'OpenSim')}",
        "backup_max_retries=3",
        "",
    ]


def load_vergegrid_config(path="vergegrid.conf", root="C:\\VergeGrid"):
    """Load VergeGrid configuration safely with integrity checks."""
    log = _get_logger()
    config = {
        "install_root": root,
        "backup_max_retries": 3,
    }

    if not os.path.exists(path):
        log(Fore.YELLOW + f"[WARN] Config file missing. Will regenerate: {path}")
        ensure_vergegrid_config(root)
        return config

    # --- Sanity: check if zero-byte or unreadable ---
    if os.path.getsize(path) == 0:
        log(Fore.RED + f"[CORRUPT] Empty config detected at {path}. Backing up and regenerating.")
        _backup_and_regen_conf(path, root, log)
        return config

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        log(Fore.RED + f"[ERROR] Failed to read config ({e}). Backing up and regenerating.")
        _backup_and_regen_conf(path, root, log)
        return config

    try:
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = [p.strip() for p in line.split("=", 1)]
                if key.lower() == "backup_max_retries":
                    try:
                        config["backup_max_retries"] = int(value)
                    except ValueError:
                        config["backup_max_retries"] = 3
                else:
                    config[key] = value
    except Exception as e:
        log(Fore.RED + f"[CORRUPT] Config parse failed: {e}")
        _backup_and_regen_conf(path, root, log)
        return config

    # --- Integrity Check: critical keys ---
    critical_keys = ["PHP_ROOT", "APACHE_ROOT", "MYSQL_ROOT", "OPEN_SIM_ROOT"]
    missing = [k for k in critical_keys if k not in config]
    if missing:
        log(Fore.RED + f"[CORRUPT] Config missing keys: {', '.join(missing)}")
        _backup_and_regen_conf(path, root, log)
        return config

    log(Fore.GREEN + f"[OK] Config loaded successfully: {path}")
    return config


def _backup_and_regen_conf(path, root, log):
    """Backup bad config and regenerate a new one."""
    try:
        ts = time.strftime("%Y%m%d_%H%M%S")
        bad_name = f"{path}.invalid_{ts}.bak"
        os.rename(path, bad_name)
        log(Fore.YELLOW + f"[BACKUP] Damaged config backed up as {bad_name}")
    except Exception as e:
        log(Fore.RED + f"[WARN] Failed to backup corrupted config: {e}")

    ensure_vergegrid_config(root)

def ensure_vergegrid_config(root):
    """Ensures vergegrid.conf exists with sane defaults and correct install root."""
    log = _get_logger()  # <-- FIX: use the active logger (installer, cleanup, or fallback)
    cfg_path = os.path.join(root, "vergegrid.conf")
    if os.path.exists(cfg_path):
        log(Fore.CYAN + f"[INFO] Config file found: {cfg_path}")
        return cfg_path

    defaults = [
        "# VergeGrid System Configuration",
        "# Automatically generated; adjust paths as needed.",
        f"install_root={root}",
        "backup_max_retries=3",
        f"PHP_ROOT={os.path.join(root, 'Apache', 'php')}",
        f"APACHE_ROOT={os.path.join(root, 'Apache')}",
        f"MYSQL_ROOT={os.path.join(root, 'MySQL')}",
        f"OPEN_SIM_ROOT={os.path.join(root, 'OpenSim')}",
        f"DOWNLOADS_ROOT={os.path.join(root, 'Downloads')}",
        "",
    ]

    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write("\n".join(defaults))
        log(Fore.GREEN + f"[INFO] Created default VergeGrid configuration at {cfg_path}")
    except Exception as e:
        log(Fore.RED + f"[ERROR] Failed to write default vergegrid.conf: {e}")

    return cfg_path


# ============================================================
# Path Management
# ============================================================

def read_saved_path():
    """Read stored VergeGrid install path from ProgramData."""
    if SAVE_PATH.exists():
        try:
            return Path(SAVE_PATH.read_text(encoding="utf-8").strip())
        except Exception:
            return None
    return None

def save_install_path(path: Path):
    """Save install path to ProgramData for later lookups."""
    log = _get_logger()
    try:
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SAVE_PATH.write_text(str(path), encoding="utf-8")
        log(Fore.CYAN + f"[INFO] Saved system path reference: {path}")
    except Exception as e:
        log(Fore.RED + f"[WARN] Could not save install path: {e}")

def find_existing_install():
    """Scan all drives for VergeGrid installations."""
    from string import ascii_uppercase
    for letter in ascii_uppercase:
        path = Path(f"{letter}:\\VergeGrid\\{INSTALL_MARKER}")
        if path.exists():
            return path.parent
    return None

# ============================================================
# Diagnostics
# ============================================================

def dump_config(config: dict):
    """Pretty-print loaded configuration dict."""
    print(Style.BRIGHT + Fore.CYAN + "\nDetected Configuration:")
    for key, value in config.items():
        print(f"  {key:<15} {value}")
    print()

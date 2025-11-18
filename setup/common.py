# -*- coding: utf-8 -*-
"""
VergeGrid Installer - Common Helper Library
Shared utilities for all modular component installers
Author: Sonja + GPT
"""

# --- VergeGrid Path Fix ---
import os
import sys

# Find VergeGrid root (one level up from /setup/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

import os
import sys
import time
import shutil
import zipfile
import subprocess
import urllib.request
import ssl
from pathlib import Path

# ============================================================
# LOGGING
# ============================================================

LOG_PATH = None

def set_log_file(path):
    """Sets global log file path for all fetcher scripts."""
    global LOG_PATH
    LOG_PATH = path

def write_log(msg, level="INFO"):
    """Writes timestamped log entries to console and log file."""
    ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{ts} [{level}] {msg}"
    print(line)
    if LOG_PATH:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")

# ============================================================
# FILE AND NETWORK OPERATIONS
# ============================================================

def download_file(url, dest, fallback_url=None):
    """
    Downloads a file with a live progress bar and PowerShell fallback.
    """
    import ssl, time, urllib.request, sys, os
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    write_log(f"Downloading {os.path.basename(dest)} from {url}")

    spinner = ['|', '/', '-', '\\']
    spin_index = 0
    bar_length = 50
    block_size = 8192

    try:
        # Handle OpenSim TLS bypass if needed
        context = None
        if "opensimulator.org" in url.lower():
            write_log("Bypassing SSL verification for OpenSim source (legacy TLS).")
            context = ssl._create_unverified_context()

        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )

        with urllib.request.urlopen(req, context=context) as response, open(dest, "wb") as f:
            total_size = int(response.info().get("Content-Length", -1))
            downloaded = 0
            start_time = time.time()

            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if total_size > 0:
                    percent = downloaded / total_size
                    filled = int(bar_length * percent)
                    bar = ">" * filled + "=" * (bar_length - filled)
                    spin_char = spinner[spin_index % len(spinner)]
                    spin_index += 1
                    elapsed = max(time.time() - start_time, 0.1)
                    speed = downloaded / (1024 * 1024 * elapsed)
                    sys.stdout.write(
                        f"\r {spin_char} [{bar}] {int(percent * 100):3d}%  {speed:6.2f} MB/s"
                    )
                    sys.stdout.flush()

            total_elapsed = max(time.time() - start_time, 0.1)
            avg_speed = downloaded / (1024 * 1024 * total_elapsed)
            sys.stdout.write(
                f"\r ✓ [>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>] 100%  {avg_speed:6.2f} MB/s - done\n"
            )
            sys.stdout.flush()

        size = os.path.getsize(dest)
        if size < 500_000:
            raise RuntimeError(f"File too small ({size} bytes) — likely invalid download.")
        write_log(f"Downloaded successfully to {dest}")
        return True

    except Exception as e:
        write_log(f"[WARN] Download failed: {e}")

        if fallback_url:
            write_log(f"Attempting fallback mirror: {fallback_url}")
            return download_file(fallback_url, dest)

        # PowerShell fallback
        write_log("Trying PowerShell fallback...", "WARN")
        ps_cmd = [
            "powershell", "-Command",
            f"$AllProtocols = [System.Net.SecurityProtocolType]'Ssl3,Tls,Tls11,Tls12'; "
            f"[System.Net.ServicePointManager]::SecurityProtocol = $AllProtocols; "
            f"$ProgressPreference='SilentlyContinue'; "
            f"Invoke-WebRequest -Uri '{url}' -OutFile '{dest}' -UseBasicParsing"
        ]
        result = subprocess.run(ps_cmd, capture_output=True, text=True)

        if os.path.exists(dest) and os.path.getsize(dest) > 500_000:
            write_log("PowerShell fallback succeeded.")
            return True
        else:
            write_log(f"PowerShell fallback failed: {result.stderr}", "ERROR")
            raise RuntimeError(f"Download failed for {url}")

# ============================================================
# ARCHIVE OPERATIONS
# ============================================================

def extract_archive(src, dest):
    """
    Extracts an archive using 7-Zip if available, otherwise Python zipfile.
    """
    sevenzip = shutil.which("7z") or shutil.which("7z.exe")
    if sevenzip:
        write_log(f"Extracting {src} → {dest} using 7-Zip")
        subprocess.run([sevenzip, "x", "-y", f"-o{dest}", src], check=True)
    else:
        write_log(f"Extracting {src} → {dest} using Python zipfile")
        with zipfile.ZipFile(src, "r") as zf:
            zf.extractall(dest)
    write_log(f"Extraction complete for {os.path.basename(src)}")

def flatten_extracted_dir(dest, expected=None):
    """
    Flattens a single extracted folder level (if needed).
    Example: D:\VergeGrid\Apache\apache24 → D:\VergeGrid\Apache
    """
    entries = [e for e in os.listdir(dest) if os.path.isdir(os.path.join(dest, e))]
    if not entries:
        return
    if expected and expected in entries:
        sub = os.path.join(dest, expected)
    elif len(entries) == 1:
        sub = os.path.join(dest, entries[0])
    else:
        write_log(f"Multiple directories in {dest}, skipping flatten.")
        return

    try:
        for item in os.listdir(sub):
            shutil.move(os.path.join(sub, item), os.path.join(dest, item))
        shutil.rmtree(sub, ignore_errors=True)
        write_log(f"Flattened extracted folder structure in {dest}")
    except Exception as e:
        write_log(f"Failed to flatten {dest}: {e}", "WARN")

# ============================================================
# SERVICE HELPERS
# ============================================================

def run_sc_create(name, binpath, display, description):
    """
    Creates a Windows service via sc.exe
    """
    try:
        subprocess.run([
            "sc", "create", name,
            f"binPath= {binpath}",
            f"DisplayName= {display}",
            "start=", "demand"
        ], check=False, capture_output=True)
        subprocess.run(["sc", "description", name, description], check=False)
        write_log(f"Service {name} registered successfully.")
    except Exception as e:
        write_log(f"Failed to create service {name}: {e}", "ERROR")

# ============================================================
# SHORTCUT HELPERS
# ============================================================

def create_shortcut(name, cmd):
    """
    Creates a Start Menu batch shortcut for a VergeGrid component.
    """
    start_dir = os.path.join(os.environ["ProgramData"],
                             r"Microsoft\Windows\Start Menu\Programs\VergeGrid")
    os.makedirs(start_dir, exist_ok=True)
    lnk_path = os.path.join(start_dir, f"{name}.bat")
    with open(lnk_path, "w", encoding="utf-8") as f:
        f.write(f"@echo off\n{cmd}\npause\n")
    write_log(f"Created shortcut: {lnk_path}")

# ============================================================
# ENVIRONMENT UTILITIES
# ============================================================

def ensure_dir(path):
    """Ensures a directory exists."""
    os.makedirs(path, exist_ok=True)
    return path

def ensure_clean_dir(path):
    """Recreates a directory (cleans if exists)."""
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)
    return path

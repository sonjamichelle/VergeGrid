#!/usr/bin/env python3
# Windows Dependency Checker - Phase 2 (Smart .NET + Auto-Install)
# Author: Sonja + Code GPT

# --- VergeGrid Path Fix ---
import os
import sys
import platform
import subprocess
import json
import glob
from datetime import datetime

# Find VergeGrid root (one level up from /setup/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

# --- Logging Setup ---
INSTALLER_LOG_DIR = os.path.join(ROOT_DIR, "Installer_Logs")
os.makedirs(INSTALLER_LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(INSTALLER_LOG_DIR, "dependency_check.log")

def log_message(message):
    """Write message to both console and log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)

log_message("=== VergeGrid Windows Dependency Checker Started ===")

# --- Auto-install colorama if missing ---
try:
    from colorama import init, Fore, Style
except ImportError:
    log_message("colorama not found — installing it now...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "colorama"])
        from colorama import init, Fore, Style
        log_message("colorama installed successfully.\n")
    except subprocess.CalledProcessError as e:
        log_message(f"Failed to install colorama automatically: {e}")
        sys.exit(1)

init(autoreset=True)

# --- Helper Functions ---
def run_command(command):
    """Run a shell command and return (status, output)."""
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            output = (result.stdout or result.stderr).strip()
            return True, output
        else:
            err = (result.stderr or result.stdout).strip().splitlines()
            short_err = err[0] if err else "Unknown error"
            return False, short_err
    except FileNotFoundError:
        return False, "Command not found"
    except Exception as e:
        return False, str(e)

def check_file_exists(pattern):
    """Check if a file pattern exists (used for Visual C++ runtime DLL)."""
    matches = glob.glob(pattern)
    return len(matches) > 0, matches

def detect_dotnet_runtime():
    """Detect installed .NET Runtime versions via filesystem paths."""
    runtime_path = r"C:\Program Files\dotnet\shared\Microsoft.NETCore.App"
    if not os.path.exists(runtime_path):
        return False, "Runtime folder not found"
    versions = [v for v in os.listdir(runtime_path) if os.path.isdir(os.path.join(runtime_path, v))]
    if versions:
        return True, versions[-1]
    return False, "No runtime versions found"

def detect_dotnet_sdk():
    """Detect installed .NET SDKs via CLI."""
    success, output = run_command(["dotnet", "--list-sdks"])
    if not success or "Command not found" in output:
        return False, output
    lines = output.splitlines()
    versions = [line.split()[0] for line in lines if line.strip()]
    if versions:
        return True, versions[-1]
    return False, "No SDKs detected"

def install_dotnet_sdk():
    """Attempt to install the latest .NET SDK using winget (fully verbose)."""
    log_message("Attempting .NET SDK installation using winget...")
    cmd = [
        "winget", "install",
        "--id", "Microsoft.DotNet.SDK.8",
        "--accept-source-agreements",
        "--accept-package-agreements"
    ]
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in process.stdout:
            log_message(line.strip())
        process.wait()
        if process.returncode == 0:
            log_message("✅ .NET SDK installation completed successfully.")
            return True
        else:
            log_message(f"❌ .NET SDK installation failed with code {process.returncode}.")
            return False
    except Exception as e:
        log_message(f"❌ .NET SDK installation error: {e}")
        return False

# --- Dependency Definitions ---
REQUIRED_DEPENDENCIES = {
    "Python": {"command": [sys.executable, "--version"], "required": True},
    "Visual C++ Runtime": {"file_check": "C:\\Windows\\System32\\vcruntime*.dll", "required": True},
    "Git": {"command": ["git", "--version"], "required": False},
    "OpenSSL": {"command": ["openssl", "version"], "required": False},
    "pip": {"command": ["pip", "--version"], "required": True},
}

# --- Main Logic ---
def main():
    if platform.system() != "Windows":
        log_message("This script is designed for Windows systems only.")
        sys.exit(2)

    results = {}
    all_ok = True
    warnings = False

    log_message("=== Windows System Dependency Check ===")

    # --- Check .NET Runtime ---
    sdk_ok, sdk_ver = detect_dotnet_sdk()
    rt_ok, rt_ver = detect_dotnet_runtime()

    if rt_ok:
        log_message(f"[OK] .NET Runtime → {rt_ver}")
    else:
        all_ok = False
        log_message(f"[MISSING] .NET Runtime → {rt_ver}")

    if sdk_ok:
        log_message(f"[OK] .NET SDK → {sdk_ver}")
    else:
        log_message(f"[MISSING] .NET SDK → {sdk_ver}")
        if install_dotnet_sdk():
            sdk_ok, sdk_ver = detect_dotnet_sdk()
            if sdk_ok:
                log_message(f"[OK] .NET SDK (after install) → {sdk_ver}")
            else:
                log_message(f"[FAILED] .NET SDK installation could not be verified.")
        else:
            all_ok = False

    results[".NET Runtime"] = {"status": "OK" if rt_ok else "MISSING", "details": rt_ver, "required": True}
    results[".NET SDK"] = {"status": "OK" if sdk_ok else "MISSING", "details": sdk_ver, "required": True}

    # --- Check Other Dependencies ---
    for name, info in REQUIRED_DEPENDENCIES.items():
        status = False
        message = ""
        version = "N/A"

        if "command" in info:
            status, message = run_command(info["command"])
            if status:
                version = message
        elif "file_check" in info:
            status, matches = check_file_exists(info["file_check"])
            message = ", ".join(matches) if matches else "File not found"

        if status:
            log_message(f"[OK] {name:25s} → {version}")
        else:
            if info["required"]:
                all_ok = False
                log_message(f"[MISSING] {name:25s} → {message}")
            else:
                warnings = True
                log_message(f"[WARNING] {name:25s} → {message}")

        results[name] = {
            "status": "OK" if status else "MISSING" if info["required"] else "WARNING",
            "details": message,
            "required": info["required"],
        }

    # --- JSON Output ---
    json_path = os.path.join(INSTALLER_LOG_DIR, "dependency_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    log_message(f"[INFO] JSON dependency report saved to {json_path}")

    # --- Summary ---
    ok_count = sum(1 for r in results.values() if r["status"] == "OK")
    missing_count = sum(1 for r in results.values() if r["status"] == "MISSING")
    warn_count = sum(1 for r in results.values() if r["status"] == "WARNING")

    log_message(f"Summary: OK={ok_count}, Missing={missing_count}, Warnings={warn_count}")
    log_message("=== Dependency Check Complete ===")

    if not all_ok:
        sys.exit(2)
    elif warnings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Windows Dependency Checker - Phase 2 (Smart .NET + Auto-Install)
# Author: Sonja + Code GPT

import os
import sys
import platform
import subprocess
import json
import glob

from vergegrid_common import (
    load_vergegrid_config,
    ensure_vergegrid_config,
    save_install_path,
    read_saved_path,
    find_existing_install
)

# --- Auto-install colorama if missing ---
try:
    from colorama import init, Fore, Style
except ImportError:
    print("colorama not found — installing it now...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "colorama"])
        from colorama import init, Fore, Style
        print("colorama installed successfully.\n")
    except subprocess.CalledProcessError as e:
        print("Failed to install colorama automatically.")
        print("Error:", e)
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
    print("\n" + Style.BRIGHT + "=" * 60)
    print(Style.BRIGHT + Fore.YELLOW + "Starting .NET SDK installation (verbose mode enabled)")
    print(Style.BRIGHT + "=" * 60 + "\n")

    cmd = [
        "winget", "install",
        "--id", "Microsoft.DotNet.SDK.8",
        "--accept-source-agreements",
        "--accept-package-agreements"
    ]

    print(Style.DIM + "Executing command: " + " ".join(cmd) + "\n")

    try:
        process = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
        process.wait()

        print("\n" + Style.BRIGHT + "-" * 60)
        if process.returncode == 0:
            print(Fore.GREEN + "✅  .NET SDK installation completed successfully.")
            print(Style.BRIGHT + "-" * 60 + "\n")
            return True
        else:
            print(Fore.RED + f"❌  .NET SDK installation failed with exit code {process.returncode}.")
            print(Fore.YELLOW + "Try running manually:\n  winget install Microsoft.DotNet.SDK.8")
            print(Style.BRIGHT + "-" * 60 + "\n")
            return False

    except FileNotFoundError:
        print(Fore.RED + "Winget not found — please install it from the Microsoft Store or enable App Installer.")
        return False
    except Exception as e:
        print(Fore.RED + f"An unexpected error occurred while installing .NET SDK:\n{e}")
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
        print(Fore.RED + "This script is designed for Windows systems only.")
        sys.exit(2)

    results = {}
    all_ok = True
    warnings = False

    print(Style.BRIGHT + "\n=== Windows System Dependency Check ===\n")

    # --- Check .NET Runtime ---
    sdk_ok, sdk_ver = detect_dotnet_sdk()
    rt_ok, rt_ver = detect_dotnet_runtime()

    if rt_ok:
        print(Fore.GREEN + f"[OK] .NET Runtime            → {rt_ver}")
    else:
        all_ok = False
        print(Fore.RED + f"[MISSING] .NET Runtime       → {rt_ver}")

    if sdk_ok:
        print(Fore.GREEN + f"[OK] .NET SDK                → {sdk_ver}")
    else:
        print(Fore.RED + f"[MISSING] .NET SDK           → {sdk_ver}")
        if install_dotnet_sdk():
            sdk_ok, sdk_ver = detect_dotnet_sdk()
            if sdk_ok:
                print(Fore.GREEN + f"[OK] .NET SDK (after install) → {sdk_ver}")
            else:
                print(Fore.RED + f"[FAILED] .NET SDK installation could not be verified.")
        else:
            all_ok = False

    results[".NET Runtime"] = {
        "status": "OK" if rt_ok else "MISSING",
        "details": rt_ver,
        "required": True,
    }
    results[".NET SDK"] = {
        "status": "OK" if sdk_ok else "MISSING",
        "details": sdk_ver,
        "required": True,
    }

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
            print(Fore.GREEN + f"[OK] {name:25s} → {version}")
        else:
            if info["required"]:
                all_ok = False
                print(Fore.RED + f"[MISSING] {name:25s} → {message}")
            else:
                warnings = True
                print(Fore.YELLOW + f"[WARNING] {name:25s} → {message}")

        results[name] = {
            "status": "OK" if status else "MISSING" if info["required"] else "WARNING",
            "details": message,
            "required": info["required"],
        }

    # --- JSON Output ---
    if "--json" in sys.argv:
        with open("dependency_report.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        print(Fore.CYAN + "\nJSON report saved to dependency_report.json")

    # --- Summary ---
    print("\n" + Style.BRIGHT + "Summary:")
    print("  OK:", sum(1 for r in results.values() if r["status"] == "OK"))
    print("  Missing:", sum(1 for r in results.values() if r["status"] == "MISSING"))
    print("  Warnings:", sum(1 for r in results.values() if r["status"] == "WARNING"))

    if not all_ok:
        sys.exit(2)
    elif warnings:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()

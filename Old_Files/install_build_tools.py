#!/usr/bin/env python3
# Windows Build Tools Installer (Phase 3, User-Friendly)
# Author: Sonja + Code GPT
# Detects and installs Visual Studio Build Tools, CMake, and LLVM if missing

import os
import sys
import subprocess
import platform
from colorama import init, Fore, Style

from vergegrid_common import (
    load_vergegrid_config,
    ensure_vergegrid_config,
    save_install_path,
    read_saved_path,
    find_existing_install
)

init(autoreset=True)

# --------------------------------------------------------
# Helper Functions
# --------------------------------------------------------

def run_command(command):
    """Run a shell command and return (status, output)."""
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return True, (result.stdout or result.stderr).strip()
        else:
            return False, (result.stderr or result.stdout).strip()
    except FileNotFoundError:
        return False, "Command not found"
    except Exception as e:
        return False, str(e)


def tool_exists(tool_name, alt_paths=None):
    """Check if a tool exists either in PATH or known install dirs."""
    status, _ = run_command(["where", tool_name])
    if status:
        return True

    if alt_paths:
        for path in alt_paths:
            if os.path.exists(path):
                return True
    return False


def install_tool(name, winget_id):
    """Install or upgrade a tool using winget with verbose output."""
    print("\n" + Style.BRIGHT + "=" * 60)
    print(Style.BRIGHT + Fore.YELLOW + f"Installing {name} (verbose mode enabled)")
    print(Style.BRIGHT + "=" * 60 + "\n")

    cmd = [
        "winget", "install",
        "--id", winget_id,
        "--accept-source-agreements",
        "--accept-package-agreements"
    ]

    print(Style.DIM + "Executing: " + " ".join(cmd) + "\n")

    try:
        process = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
        process.wait()

        print("\n" + Style.BRIGHT + "-" * 60)
        # Winget returns non-zero for "already installed" sometimes
        if process.returncode == 0:
            print(Fore.GREEN + f"✅  {name} installation completed successfully.")
            result = True
        elif process.returncode in (2316632107, 0x89C5010B):
            print(Fore.CYAN + f"ℹ️  {name} already installed and up to date.")
            result = True
        else:
            print(Fore.RED + f"❌  {name} installation failed with exit code {process.returncode}.")
            print(Fore.YELLOW + f"Try running manually:\n  winget install --id {winget_id}")
            result = False

        print(Style.BRIGHT + "-" * 60 + "\n")
        return result

    except FileNotFoundError:
        print(Fore.RED + "Winget not found — install App Installer from Microsoft Store.")
        return False
    except Exception as e:
        print(Fore.RED + f"Error during {name} install: {e}")
        return False


# --------------------------------------------------------
# Detection + Install Sequence
# --------------------------------------------------------

def main():
    if platform.system() != "Windows":
        print(Fore.RED + "This script only runs on Windows.")
        sys.exit(2)

    print(Style.BRIGHT + "\n=== Build Tools Detection & Installation ===\n")

    tools = {
        "Visual Studio Build Tools 2022": {
            "detect": lambda: tool_exists(
                "cl.exe",
                [r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools"],
            ),
            "winget_id": "Microsoft.VisualStudio.2022.BuildTools"
        },
        "CMake": {
            "detect": lambda: tool_exists(
                "cmake.exe",
                [r"C:\Program Files\CMake\bin", r"C:\Program Files (x86)\CMake\bin"],
            ),
            "winget_id": "Kitware.CMake"
        },
        "LLVM / Clang": {
            "detect": lambda: tool_exists(
                "clang.exe",
                [r"C:\Program Files\LLVM\bin"],
            ),
            "winget_id": "LLVM.LLVM"
        }
    }

    results = {}
    all_ok = True

    for name, info in tools.items():
        print(Style.BRIGHT + Fore.YELLOW + f"[CHECKING] {name:30s} → Scanning system...")
        detected = info["detect"]()

        if detected:
            print(Fore.GREEN + f"[OK] {name:30s} → Detected")
            results[name] = "OK"
            continue

        success = install_tool(name, info["winget_id"])
        if success:
            verify = info["detect"]()
            if verify:
                print(Fore.GREEN + f"[OK] {name:30s} → Installed successfully")
                results[name] = "Installed"
            else:
                print(Fore.CYAN + f"[INFO] {name:30s} → Installed but not yet detected (may require restart)")
                results[name] = "Installed (Pending Restart)"
        else:
            print(Fore.RED + f"[FAILED] {name:30s} → Could not be installed or detected")
            all_ok = False
            results[name] = "Failed"

    print("\n" + Style.BRIGHT + "Summary:")
    for name, status in results.items():
        color = (
            Fore.GREEN
            if status in ("OK", "Installed", "Installed (Pending Restart)")
            else Fore.RED
        )
        print(color + f"  {name:30s} → {status}")

    if all_ok:
        sys.exit(0)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Windows Build Tools Installer (Phase 3, User-Friendly)
# Author: Sonja + Code GPT
# Detects and installs Visual Studio Build Tools, CMake, and LLVM if missing

# --- VergeGrid Path Fix ---
import os
import sys
import subprocess
import platform
from datetime import datetime
from colorama import init, Fore, Style

# Find VergeGrid root (one level up from /setup/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

# --- Installer Logs Setup ---
INSTALLER_LOG_DIR = os.path.join(ROOT_DIR, "Installer_Logs")
os.makedirs(INSTALLER_LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(INSTALLER_LOG_DIR, "build_tools_install.log")

def log_message(message, color=None):
    """Write message to both console and log file (with optional color)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")
    if color:
        print(color + message + Style.RESET_ALL)
    else:
        print(message)

log_message("=== VergeGrid Build Tools Installer Started ===")

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
    log_message(f"=== Installing {name} ===", Fore.YELLOW)
    cmd = [
        "winget", "install",
        "--id", winget_id,
        "--accept-source-agreements",
        "--accept-package-agreements"
    ]

    log_message("Executing: " + " ".join(cmd), Style.DIM)
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in process.stdout:
            log_message(line.strip())
        process.wait()

        if process.returncode == 0:
            log_message(f"✅ {name} installation completed successfully.", Fore.GREEN)
            return True
        elif process.returncode in (2316632107, 0x89C5010B):
            log_message(f"ℹ️ {name} already installed and up to date.", Fore.CYAN)
            return True
        else:
            log_message(f"❌ {name} installation failed with exit code {process.returncode}.", Fore.RED)
            log_message(f"Try running manually: winget install --id {winget_id}", Fore.YELLOW)
            return False

    except FileNotFoundError:
        log_message("Winget not found — install App Installer from Microsoft Store.", Fore.RED)
        return False
    except Exception as e:
        log_message(f"Error during {name} install: {e}", Fore.RED)
        return False


# --------------------------------------------------------
# Detection + Install Sequence
# --------------------------------------------------------
def main():
    if platform.system() != "Windows":
        log_message("This script only runs on Windows.", Fore.RED)
        sys.exit(2)

    log_message("\n=== Build Tools Detection & Installation ===\n", Style.BRIGHT)

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
        log_message(f"[CHECKING] {name} → Scanning system...", Fore.YELLOW)
        detected = info["detect"]()

        if detected:
            log_message(f"[OK] {name} → Detected", Fore.GREEN)
            results[name] = "OK"
            continue

        success = install_tool(name, info["winget_id"])
        if success:
            verify = info["detect"]()
            if verify:
                log_message(f"[OK] {name} → Installed successfully", Fore.GREEN)
                results[name] = "Installed"
            else:
                log_message(f"[INFO] {name} → Installed but not yet detected (may require restart)", Fore.CYAN)
                results[name] = "Installed (Pending Restart)"
        else:
            log_message(f"[FAILED] {name} → Could not be installed or detected", Fore.RED)
            all_ok = False
            results[name] = "Failed"

    log_message("\n=== Summary ===", Style.BRIGHT)
    for name, status in results.items():
        color = (
            Fore.GREEN
            if status in ("OK", "Installed", "Installed (Pending Restart)")
            else Fore.RED
        )
        log_message(f"  {name:30s} → {status}", color)

    log_message("\n=== VergeGrid Build Tools Installer Complete ===\n")
    log_message(f"Full log saved to: {LOG_FILE}")

    if all_ok:
        sys.exit(0)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
VergeGrid Modular Component Installer: PHP
Author: Sonja + GPT
Purpose:
  - Download and extract PHP
  - Copy default php.ini into place
  - Optionally add PHP to system PATH
  - Create a Start Menu shortcut for PHP dev server
  - Verify correct Thread Safe Apache module (php8apache2_4.dll)
"""

# --- VergeGrid Path Fix ---
import os
import sys

# Find VergeGrid root (one level up from /setup/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Fix ---

import shutil
import subprocess
from pathlib import Path

try:
    from setup import common
except ModuleNotFoundError:
    import common


# ------------------------------------------------------------
# Component URLs
# ------------------------------------------------------------
URLS = {
    "php": "https://windows.php.net/downloads/releases/php-8.4.14-Win32-vs17-x64.zip",
}
URLS_FALLBACK = {
    "php": "https://windows.php.net/downloads/releases/archives/php-8.4.14-Win32-vs17-x64.zip",
}


# ------------------------------------------------------------
# Core Install Function
# ------------------------------------------------------------
def install_php(install_root):
    """
    Installs PHP standalone (no Apache integration here).
    """
    install_root = Path(install_root).resolve()
    downloads_root = install_root / "Downloads"
    logs_root = install_root / "Logs"
    php_root = install_root / "PHP"

    os.makedirs(php_root, exist_ok=True)
    os.makedirs(downloads_root, exist_ok=True)
    os.makedirs(logs_root, exist_ok=True)

    log_file = logs_root / "vergegrid-install.log"
    common.set_log_file(str(log_file))
    common.write_log("=== Fetch-PHP Script Starting ===")

    zip_php = downloads_root / "php.zip"

    try:
        # --------------------------------------------------------
        # 1. Download PHP
        # --------------------------------------------------------
        print("\n>>> Downloading PHP runtime...")
        common.download_file(URLS["php"], str(zip_php), fallback_url=URLS_FALLBACK["php"])

        # --------------------------------------------------------
        # 2. Extract PHP
        # --------------------------------------------------------
        print("\n>>> Extracting PHP package...")
        common.extract_archive(str(zip_php), str(php_root))

        # Flatten nested folder if zip contained a versioned directory
        subdirs = [d for d in php_root.iterdir() if d.is_dir() and d.name.startswith("php")]
        if subdirs:
            subdir = subdirs[0]
            for item in subdir.iterdir():
                dest = php_root / item.name
                if not dest.exists():
                    shutil.move(str(item), str(dest))
            try:
                subdir.rmdir()
                print(f"[INFO] Flattened PHP directory from {subdir.name}")
                common.write_log(f"[INFO] Flattened PHP directory from {subdir.name}")
            except Exception:
                pass

        common.write_log(f"[OK] Extracted PHP to {php_root}")

        # --------------------------------------------------------
        # 3. Verify Thread Safe Apache module exists
        # --------------------------------------------------------
        print("\n>>> Verifying PHP Apache module (php8apache2_4.dll)...")
        dlls = list(php_root.glob("php*apache2_4.dll"))  # ✅ FIXED pattern (removed hyphen)
        if not dlls:
            raise FileNotFoundError(
                f"No php*apache2_4.dll module found in {php_root}. "
                "Ensure this is the Thread Safe PHP build."
            )
        php_dll = dlls[0]
        print(f"[OK] Found Apache module: {php_dll.name}")
        common.write_log(f"[OK] Found Apache module: {php_dll}", "INFO")

        # --------------------------------------------------------
        # 4. Configure php.ini
        # --------------------------------------------------------
        print("\n>>> Configuring PHP ini file...")
        ini_dev = php_root / "php.ini-development"
        ini_prod = php_root / "php.ini-production"
        ini_target = php_root / "php.ini"

        try:
            if ini_dev.exists():
                shutil.copy(ini_dev, ini_target)
            elif ini_prod.exists():
                shutil.copy(ini_prod, ini_target)
            else:
                common.write_log("[WARN] No php.ini template found in package.", "WARN")

            # quick tweak: enable extensions dir
            if ini_target.exists():
                with open(ini_target, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                new_lines = []
                for line in lines:
                    if line.strip().startswith(";extension_dir"):
                        new_lines.append(f'extension_dir = "{php_root}\\ext"\n')
                    else:
                        new_lines.append(line)

                with open(ini_target, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

                common.write_log("[OK] Configured php.ini successfully.")
        except Exception as e:
            common.write_log(f"[WARN] php.ini setup failed: {e}", "WARN")

        # --------------------------------------------------------
        # 5. Add PHP to PATH (optional)
        # --------------------------------------------------------
        print("\n>>> Adding PHP to PATH environment variable (system-wide)...")
        try:
            current_path = os.environ.get("PATH", "")
            if str(php_root) not in current_path:
                subprocess.run(
                    ["setx", "/M", "PATH", f"{php_root};{current_path}"],
                    capture_output=True,
                    text=True,
                )
                common.write_log(f"[OK] Added PHP to system PATH: {php_root}")
        except Exception as e:
            common.write_log(f"[WARN] Failed to update PATH: {e}", "WARN")

        # --------------------------------------------------------
        # 6. Create Start Menu Shortcut
        # --------------------------------------------------------
        print("\n>>> Creating PHP Dev Server shortcut...")
        common.create_shortcut(
            "Start PHP Dev Server",
            f'"{php_root}\\php.exe" -S localhost:8080 -t "{install_root}\\www"'
        )
        common.write_log("[OK] Created PHP Dev Server shortcut")

        # --------------------------------------------------------
        # 7. Done
        # --------------------------------------------------------
        print("\n✓ VergeGrid PHP installation completed successfully.\n")
        common.write_log(f"[SUCCESS] PHP installed successfully at {php_root}")
        sys.exit(0)

    except Exception as e:
        import traceback
        traceback.print_exc()
        common.write_log(f"[FATAL] PHP installation failed: {e}", "ERROR")
        print("\n[FATAL] PHP installation failed. See logs for details.")
        sys.exit(1)


# ------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch-php.py <install_root>")
        sys.exit(1)

    install_root = sys.argv[1]
    install_php(install_root)

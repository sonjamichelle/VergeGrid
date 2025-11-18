#!/usr/bin/env python3
# ==============================================================
# VergeGrid - Lightweight OpenSim Instance Override Generator
# Creates small .ini override files for each simulator (DOS box)
# ==============================================================

import os
import sys

# Base OpenSim directory (adjust if needed)
BASE_DIR = r"C:\Apps\DreamGrid\OutworldzFiles\Opensim\bin"
CONFIG_DIR = os.path.join(BASE_DIR, "config-include")

def create_override(name, port):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    override_path = os.path.join(CONFIG_DIR, f"{name}.ini")

    with open(override_path, "w", encoding="utf-8") as f:
        f.write(f"""; VergeGrid Simulator Override - {name}
; This small file overrides only what’s needed for this instance.

[Startup]
regionload_regionsdir = "./Regions/{name}"
ConsolePrompt = "{name}# "
http_listener_port = {port}
physics = ubOde
gridname = VergeGrid {name}
create_default_region = false
""")

    print(f"[OK] Created override: {override_path}")
    print(f"  ↳ Uses regions in ./Regions/{name}")
    print(f"  ↳ Listens on port {port}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: create_override.py <RegionFolderName> <Port>")
        sys.exit(1)
    create_override(sys.argv[1], sys.argv[2])

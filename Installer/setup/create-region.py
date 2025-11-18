#!/usr/bin/env python3
"""
VergeGrid Region Manager (create-region.py)
Cross-platform tool for managing OpenSim regions under VergeGrid.
Supports both interactive and command-line usage.
"""

import argparse
import configparser
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

# --- Constants ---
BASE_DIR = Path(__file__).resolve().parents[1]
REGIONS_DIR = BASE_DIR / "Regions"
ACTIVE_DIR = REGIONS_DIR / "Active"
ARCHIVE_DIR = REGIONS_DIR / "Archive"
TEMPLATES_DIR = REGIONS_DIR / "Templates"
REGIONS_INI = REGIONS_DIR / "Regions.ini"

# --- Helpers ---
def ensure_dirs():
    for d in [REGIONS_DIR, ACTIVE_DIR, ARCHIVE_DIR, TEMPLATES_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    if not REGIONS_INI.exists():
        with open(REGIONS_INI, "w", encoding="utf-8") as f:
            f.write("[Regions]\n")

    # Default template
    default_template = TEMPLATES_DIR / "256_Default.ini"
    if not default_template.exists():
        default_template.write_text(
            """[Region]
RegionName = DefaultRegion
RegionUUID = AUTO
Location = 1000,1000
InternalAddress = 0.0.0.0
InternalPort = 9000
AllowAlternatePorts = False
ExternalHostName = SYSTEMIP
""",
            encoding="utf-8",
        )


def generate_uuid():
    return str(uuid.uuid4())


def read_regions():
    cfg = configparser.ConfigParser()
    cfg.read(REGIONS_INI, encoding="utf-8")
    if "Regions" not in cfg:
        cfg["Regions"] = {}
    return cfg


def write_regions(cfg):
    with open(REGIONS_INI, "w", encoding="utf-8") as f:
        cfg.write(f)


def create_region_interactive(args):
    print("\n=== VergeGrid Region Creation Wizard ===")
    name = args.name or input("Region name: ").strip()
    template = args.template or input("Template (default: 256_Default.ini): ").strip() or "256_Default.ini"
    estate = args.estate or input("Estate name (optional): ").strip() or "DefaultEstate"
    location = args.location or input("Grid location (e.g. 1000,1000): ").strip() or "1000,1000"
    port = args.port or input("Port (default 9000): ").strip() or "9000"

    create_region(name, template, estate, location, port)


def create_region(name, template, estate, location, port):
    ensure_dirs()
    template_path = TEMPLATES_DIR / template
    if not template_path.exists():
        print(f"Template not found: {template_path}")
        sys.exit(1)

    region_path = ACTIVE_DIR / f"{name}.ini"
    shutil.copy(template_path, region_path)

    content = region_path.read_text(encoding="utf-8")
    content = content.replace("DefaultRegion", name)
    content = content.replace("AUTO", generate_uuid())
    content = content.replace("1000,1000", location)
    content = content.replace("9000", port)
    region_path.write_text(content, encoding="utf-8")

    cfg = read_regions()
    cfg["Regions"][name] = f"Active/{name}.ini"
    write_regions(cfg)

    print(f"\n✅ Region '{name}' created successfully!")
    print(f"   Template: {template}")
    print(f"   Estate: {estate}")
    print(f"   Location: {location}")
    print(f"   Port: {port}\n")


def list_regions():
    ensure_dirs()
    cfg = read_regions()
    print("\n=== Active Regions ===")
    for name, path in cfg["Regions"].items():
        print(f" - {name}: {path}")

    archived = list(ARCHIVE_DIR.glob("*.ini"))
    if archived:
        print("\n=== Archived Regions ===")
        for f in archived:
            print(f" - {f.stem}")


def activate_region(name):
    src = ARCHIVE_DIR / f"{name}.ini"
    dst = ACTIVE_DIR / f"{name}.ini"
    if not src.exists():
        print(f"Region {name} not found in archive.")
        return
    shutil.move(src, dst)
    cfg = read_regions()
    cfg["Regions"][name] = f"Active/{name}.ini"
    write_regions(cfg)
    print(f"✅ Region '{name}' activated.")


def deactivate_region(name):
    src = ACTIVE_DIR / f"{name}.ini"
    dst = ARCHIVE_DIR / f"{name}.ini"
    if not src.exists():
        print(f"Region {name} not found in active list.")
        return
    shutil.move(src, dst)
    cfg = read_regions()
    if name in cfg["Regions"]:
        del cfg["Regions"][name]
    write_regions(cfg)
    print(f"⚙️ Region '{name}' deactivated and archived.")


def launch_regions():
    ensure_dirs()
    cfg = read_regions()
    if not cfg["Regions"]:
        print("No regions to launch.")
        return

    print("\n🚀 Launching all active regions...\n")
    for name, relpath in cfg["Regions"].items():
        region_path = REGIONS_DIR / relpath
        if not region_path.exists():
            print(f"⚠️ Missing file for region {name}: {region_path}")
            continue

        exe = BASE_DIR / "bin" / "OpenSim.exe"
        if not exe.exists():
            print("⚠️ OpenSim.exe not found in bin/ — skipping launch.")
            return

        if os.name == "nt":
            subprocess.Popen([str(exe), f"-inidirectory={region_path.parent}"], cwd=exe.parent)
        else:
            subprocess.Popen(["mono", str(exe), f"-inidirectory={region_path.parent}"], cwd=exe.parent)
        print(f"Launched region: {name}")


# --- Main CLI ---
def main():
    parser = argparse.ArgumentParser(description="VergeGrid Region Management Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Create a new region")
    new_parser.add_argument("--name", type=str)
    new_parser.add_argument("--template", type=str)
    new_parser.add_argument("--estate", type=str)
    new_parser.add_argument("--location", type=str)
    new_parser.add_argument("--port", type=str)

    subparsers.add_parser("list", help="List all regions")

    act_parser = subparsers.add_parser("activate", help="Activate a region")
    act_parser.add_argument("name")

    deact_parser = subparsers.add_parser("deactivate", help="Deactivate a region")
    deact_parser.add_argument("name")

    subparsers.add_parser("launch", help="Launch all active regions")

    args = parser.parse_args()

    if args.command == "new":
        create_region_interactive(args)
    elif args.command == "list":
        list_regions()
    elif args.command == "activate":
        activate_region(args.name)
    elif args.command == "deactivate":
        deactivate_region(args.name)
    elif args.command == "launch":
        launch_regions()


if __name__ == "__main__":
    ensure_dirs()
    main()
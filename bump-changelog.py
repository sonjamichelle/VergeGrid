#!/usr/bin/env python3
"""
VergeGrid Changelog Auto-Bump Utility
-------------------------------------
Usage:
    python bump_changelog.py <version> [description]

Example:
    python bump_changelog.py v0.9.1 "Added region auto-registration support"
"""

import sys
from datetime import date
from pathlib import Path

CHANGELOG_FILE = Path(__file__).parent / "CHANGELOG.md"

TEMPLATE = """## [{version}] – {today}
### 🚀 Added
- {description}

### 🛠️ Changed
- 

### 🧱 Internal Improvements
- 

"""

def insert_entry(version: str, description: str):
    if not CHANGELOG_FILE.exists():
        print("[ERROR] CHANGELOG.md not found in this directory.")
        sys.exit(1)

    today = date.today().isoformat()
    new_entry = TEMPLATE.format(version=version, today=today, description=description)

    content = CHANGELOG_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    insert_index = 0

    # Find where to insert (after header lines)
    for i, line in enumerate(content):
        if line.strip().startswith("## ["):
            insert_index = i
            break

    # Rebuild file
    new_content = []
    new_content.extend(content[:insert_index])
    new_content.append("\n" + new_entry + "\n")
    new_content.extend(content[insert_index:])

    CHANGELOG_FILE.write_text("".join(new_content), encoding="utf-8")
    print(f"[OK] Added changelog entry for {version} ({today})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    version = sys.argv[1]
    description = sys.argv[2] if len(sys.argv) > 2 else "Describe your changes here."

    insert_entry(version, description)

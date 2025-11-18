#!/usr/bin/env python3
"""
VergeGrid Changelog Auto-Bump Utility (Interactive v2.1)
--------------------------------------------------------
Usage:
    python bump_changelog.py [version]

If no version is provided:
  - Parses CHANGELOG.md to detect the latest version.
  - Suggests the next version (increments patch by default).
  - Prompts for version and changelog sections interactively.

Example:
    python bump_changelog.py
"""

import sys
import re
from datetime import datetime
from pathlib import Path

# Optional color support for nice terminal output
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Dummy:
        def __getattr__(self, name): return ""
    Fore = Style = Dummy()

CHANGELOG_FILE = Path(__file__).parent / "CHANGELOG.md"

TEMPLATE = """## [{version}] – {timestamp}
### 🚀 Added
{added}

### 🛠️ Changed
{changed}

### 🧱 Internal Improvements
{improvements}

"""

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def find_latest_version() -> str:
    """Find latest version in CHANGELOG.md."""
    if not CHANGELOG_FILE.exists():
        return None
    pattern = re.compile(r"## \[v?(\d+\.\d+\.\d+)\]")
    for line in CHANGELOG_FILE.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if match:
            return f"v{match.group(1)}"
    return None


def suggest_next_version(current: str) -> str:
    """Suggest next patch version."""
    try:
        parts = [int(p) for p in current.lstrip("v").split(".")]
        parts[-1] += 1
        return f"v{'.'.join(map(str, parts))}"
    except Exception:
        return "v1.0.0"


def insert_entry(version: str, added: str, changed: str, improvements: str):
    """Insert formatted entry into CHANGELOG.md."""
    if not CHANGELOG_FILE.exists():
        print(Fore.RED + "[ERROR] CHANGELOG.md not found." + Fore.RESET)
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = TEMPLATE.format(
        version=version,
        timestamp=timestamp,
        added=added.strip() or "-",
        changed=changed.strip() or "-",
        improvements=improvements.strip() or "-"
    )

    lines = CHANGELOG_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    insert_index = 0

    for i, line in enumerate(lines):
        if line.strip().startswith("## ["):
            insert_index = i
            break

    new_content = []
    new_content.extend(lines[:insert_index])
    new_content.append("\n" + entry + "\n")
    new_content.extend(lines[insert_index:])

    CHANGELOG_FILE.write_text("".join(new_content), encoding="utf-8")

    print(Fore.GREEN + f"\n[OK] Added changelog entry for {version}" + Fore.RESET)
    print(Fore.CYAN + f"  → Timestamp: {timestamp}" + Fore.RESET)
    print(Fore.CYAN + f"  → Written to: {CHANGELOG_FILE}" + Fore.RESET)


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------
if __name__ == "__main__":
    print(Style.BRIGHT + Fore.CYAN + "\n=== VergeGrid Changelog Auto-Bump Utility ===" + Fore.RESET)

    latest = find_latest_version()
    suggested = suggest_next_version(latest) if latest else "v1.0.0"

    if latest:
        print(Fore.YELLOW + f"Last version detected: {latest}" + Fore.RESET)
        print(Fore.GREEN + f"Suggested next version: {suggested}\n" + Fore.RESET)
    else:
        print(Fore.RED + "No previous version found — starting new changelog.\n" + Fore.RESET)

    # --- Prompt for version ---
    if len(sys.argv) > 1:
        version = sys.argv[1]
    else:
        version = input(f"Enter new version [{suggested}]: ").strip() or suggested

    # --- Prompt for changelog sections ---
    print("\nEnter changelog notes (press Enter to skip any section):")
    added = input(Fore.CYAN + "  🚀 Added: " + Fore.RESET).strip() or "-"
    changed = input(Fore.YELLOW + "  🛠️ Changed: " + Fore.RESET).strip() or "-"
    improvements = input(Fore.MAGENTA + "  🧱 Internal Improvements: " + Fore.RESET).strip() or "-"

    # Auto-format bullet points
    def format_line(x): return x if x.startswith("-") or x == "-" else f"- {x}"
    added, changed, improvements = map(format_line, [added, changed, improvements])

    insert_entry(version, added, changed, improvements)

#!/usr/bin/env python3
"""
VergeGrid Full Git Changelog Generator (v5.2)
---------------------------------------------
Usage:
    python generate_changelog_full.py [--limit N] [--tag] [--batch 25]

Features:
  ✅ Parses entire Git history (not just since last tag)
  ✅ Groups commits into sequential dev releases (v0.0.xxx)
  ✅ Generates full historical CHANGELOG.md from scratch
  ✅ Adds concise natural build summary line per version
  ✅ Cleans duplicates, enforces VergeGrid format
  ✅ Optionally creates real tags (--tag)
"""

import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

CHANGELOG_FILE = Path(__file__).parent / "CHANGELOG.md"
BUILD_PREFIX = "VergeGrid Installer"


# ---------------------------------------------------------
# Git Utilities
# ---------------------------------------------------------
def git(args):
    res = subprocess.run(["git"] + args, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[WARN] git {' '.join(args)} failed: {res.stderr.strip()}")
        return ""
    return res.stdout.strip()


def get_all_commits():
    fmt = "%h|%ad|%s"
    args = ["log", "--pretty=format:" + fmt, "--date=short", "--reverse"]
    lines = git(args).splitlines()
    commits = []
    for line in lines:
        parts = line.split("|", 2)
        if len(parts) == 3:
            commits.append({"hash": parts[0], "date": parts[1], "msg": parts[2].strip()})
    return commits


# ---------------------------------------------------------
# Changelog Formatting
# ---------------------------------------------------------
def classify(msg):
    msg_l = msg.lower()
    if msg_l.startswith(("feat", "add", "✨")):
        return "Added"
    if msg_l.startswith(("fix", "bug", "🛠")):
        return "Fixed"
    if msg_l.startswith(("update", "improve", "refactor", "change", "🧱", "🧩", "chore")):
        return "Improved"
    if msg_l.startswith(("build", "ci", "internal")):
        return "Internal"
    return "Other"


def summarize_release(sections):
    """Generate a short build summary sentence based on section content."""
    counts = {k: len(v) for k, v in sections.items() if v}
    if not counts:
        return "Maintenance-only release."
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    main = [s for s, _ in top[:2]]
    summary_map = {
        "Added": "Introduces new features and functionality",
        "Fixed": "Fixes key issues and improves reliability",
        "Improved": "Enhances performance and user experience",
        "Internal": "Internal cleanup and dependency updates",
        "Other": "Minor maintenance and adjustments",
    }
    if len(main) == 1:
        phrase = summary_map.get(main[0], "General improvements")
    else:
        phrase = f"{summary_map.get(main[0], '')}; also includes {summary_map.get(main[1], '').lower()}"
    return phrase.rstrip(".") + "."


def build_entry(tag, commits):
    today = datetime.now()
    date = today.strftime("%Y-%m-%d")
    build = today.strftime("%Y.%m.%d.%H%M") + "a"

    sections = {"Added": [], "Fixed": [], "Improved": [], "Internal": [], "Other": []}
    for c in commits:
        cat = classify(c["msg"])
        entry = f"- {c['msg']}  ({c['hash']})"
        if entry not in sections[cat]:
            sections[cat].append(entry)

    summary = summarize_release(sections)

    lines = [f"## [{tag}] [{date}] {BUILD_PREFIX} — Build {build}\n"]
    for sec in ["Added", "Fixed", "Improved", "Internal", "Other"]:
        if sections[sec]:
            lines.append(f"### {sec}")
            lines.extend(sections[sec])
            lines.append("")

    lines.append(f"**Build Summary:**  {summary}\n")
    lines.append("---\n")
    return "\n".join(lines).strip() + "\n"


def ensure_header():
    header = (
        "# VergeGrid Modular Installer — CHANGELOG\n\n"
        "All notable changes are auto-generated from Git commits.\n\n---\n\n"
    )
    CHANGELOG_FILE.write_text(header, encoding="utf-8")
    return header


def clean_changelog():
    text = CHANGELOG_FILE.read_text(encoding="utf-8")
    text = re.sub(r"(\n---+\n)+", "\n---\n", text)
    CHANGELOG_FILE.write_text(text.strip() + "\n", encoding="utf-8")
    print("[OK] Cleaned and normalized changelog formatting.")


def create_tag(tag, push=False):
    msg = f"{BUILD_PREFIX} Release {tag}"
    subprocess.run(["git", "tag", "-a", tag, "-m", msg])
    print(f"[OK] Created local tag {tag}")
    if push:
        subprocess.run(["git", "push", "origin", tag])
        print(f"[OK] Pushed tag {tag} to origin")


# ---------------------------------------------------------
# Main Process
# ---------------------------------------------------------
def main():
    args = sys.argv[1:]
    batch_size = 25
    auto_tag = "--tag" in args

    if "--batch" in args:
        try:
            batch_size = int(args[args.index("--batch") + 1])
        except Exception:
            pass

    print((
        f"\n=== VergeGrid Full Changelog Generator v5.2 ===\n"
        f"[INFO] Grouping commits in batches of {batch_size}\n"
        f"[INFO] Output: {CHANGELOG_FILE}\n"
    ))

    commits = get_all_commits()
    if not commits:
        print("[WARN] No commits found.")
        return

    ensure_header()
    entries = []
    version_counter = 0

    for i in range(0, len(commits), batch_size):
        version_counter += 1
        tag = f"v0.0.{version_counter}"
        chunk = commits[i:i + batch_size]
        entry = build_entry(tag, chunk)
        entries.append(entry)

        if auto_tag:
            create_tag(tag, push=False)

    # Write all entries (latest at top)
    all_content = "# VergeGrid Modular Installer — CHANGELOG\n\n"
    all_content += "All notable changes are auto-generated from Git commits.\n\n---\n\n"
    all_content += "\n".join(reversed(entries))
    CHANGELOG_FILE.write_text(all_content, encoding="utf-8")

    clean_changelog()
    print(f"[OK] Generated {len(entries)} version sections in full changelog.")
    print(f"[INFO] File written: {CHANGELOG_FILE.resolve()}\n")


if __name__ == "__main__":
    main()

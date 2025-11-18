#!/usr/bin/env python3
"""
VergeGrid Clean Git Changelog Generator (v4.1)
----------------------------------------------
Usage:
    python generate_changelog_clean.py [--limit N] [--tag] [--clean]

Features:
  ✅ Strict version numbering (v0.0.xxx)
  ✅ One changelog entry per release
  ✅ Parses all commits since last tag (no missing entries)
  ✅ Cleans duplicate headers and extra separators
  ✅ Auto-creates first tag (v0.0.1) if none exist
  ✅ Auto-creates next tag (optional with --tag)
  ✅ Pretty VergeGrid changelog formatting
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


def latest_tag():
    tags = git(["tag", "--sort=-creatordate"]).splitlines()
    return tags[-1] if tags else None  # oldest → newest, take latest


def next_tag(prev):
    if not prev:
        return "v0.0.1"
    m = re.match(r"v?0\.0\.(\d+)", prev)
    if not m:
        return "v0.0.1"
    num = int(m.group(1)) + 1
    return f"v0.0.{num}"


def commits_since(tag=None):
    fmt = "%h|%ad|%s"
    args = ["log", "--pretty=format:" + fmt, "--date=short"]
    if tag:
        args.insert(1, f"{tag}..HEAD")
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

    lines = [
        f"## [{tag}] [{date}] {BUILD_PREFIX} — Build {build}\n",
    ]

    for sec in ["Added", "Fixed", "Improved", "Internal", "Other"]:
        if sections[sec]:
            lines.append(f"### {sec}")
            lines.extend(sections[sec])
            lines.append("")  # spacing

    lines.append("---\n")
    return "\n".join(lines).strip() + "\n"


# ---------------------------------------------------------
# File Operations
# ---------------------------------------------------------
def ensure_header():
    """Ensure changelog starts with VergeGrid header."""
    header = (
        "# VergeGrid Modular Installer — CHANGELOG\n\n"
        "All notable changes are auto-generated from Git commits.\n\n---\n\n"
    )
    if not CHANGELOG_FILE.exists():
        CHANGELOG_FILE.write_text(header, encoding="utf-8")
        return header
    content = CHANGELOG_FILE.read_text(encoding="utf-8")
    if not content.startswith("# VergeGrid Modular Installer"):
        content = header + content
        CHANGELOG_FILE.write_text(content, encoding="utf-8")
    return content


def write_entry(entry):
    content = ensure_header()
    # Insert new entry after the header
    parts = re.split(r"(?=^## )", content, maxsplit=1, flags=re.MULTILINE)
    new_content = parts[0].rstrip() + "\n\n" + entry
    if len(parts) > 1:
        new_content += parts[1]
    CHANGELOG_FILE.write_text(new_content.strip() + "\n", encoding="utf-8")
    print(f"[OK] Updated {CHANGELOG_FILE}")


def clean_changelog():
    """Deduplicate entries, collapse extra separators, and enforce structure."""
    if not CHANGELOG_FILE.exists():
        print("[WARN] No changelog found to clean.")
        return

    text = CHANGELOG_FILE.read_text(encoding="utf-8")

    # Remove duplicate separators
    text = re.sub(r"(\n---+\n)+", "\n---\n", text)

    # Remove duplicate headers
    seen = set()
    blocks = re.split(r"(?=^## \[v0\.0\.\d+\])", text, flags=re.MULTILINE)
    cleaned_blocks = []
    for block in blocks:
        if not block.strip():
            continue
        m = re.match(r"^## \[v0\.0\.\d+\]", block.strip())
        if m:
            tag = m.group(0)
            if tag in seen:
                continue
            seen.add(tag)
        cleaned_blocks.append(block.strip())

    cleaned_text = "\n\n".join(cleaned_blocks).strip() + "\n"
    CHANGELOG_FILE.write_text(cleaned_text, encoding="utf-8")
    print("[OK] Cleaned and normalized changelog formatting.")


def create_tag(tag, push=False):
    msg = f"{BUILD_PREFIX} Release {tag}"
    subprocess.run(["git", "tag", "-a", tag, "-m", msg])
    print(f"[OK] Created local tag {tag}")
    if push:
        subprocess.run(["git", "push", "origin", tag])
        print(f"[OK] Pushed tag {tag} to origin")


# ---------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------
def main():
    args = sys.argv[1:]
    clean = "--clean" in args
    auto_tag = "--tag" in args
    limit = 500

    if "--limit" in args:
        try:
            limit = int(args[args.index("--limit") + 1])
        except Exception:
            pass

    if clean:
        clean_changelog()
        return

    prev_tag = latest_tag()

    # 🔧 Auto-create initial tag if none exists
    if not prev_tag:
        print("[INFO] No existing tags found — creating initial v0.0.1 tag...")
        create_tag("v0.0.1", push=auto_tag)
        prev_tag = "v0.0.1"

    next_ver = next_tag(prev_tag)
    print(f"[INFO] Latest tag: {prev_tag} → Next: {next_ver}")

    # Gather commits since last tag
    commits = commits_since(prev_tag)
    if not commits:
        print("[INFO] No new commits found. Nothing to write.")
        return

    # Trim to limit (optional)
    commits = commits[:limit]

    # Build and write changelog entry
    entry = build_entry(next_ver, commits)
    write_entry(entry)

    # Cleanup old mess if exists
    clean_changelog()

    # Optional tagging
    if auto_tag:
        create_tag(next_ver, push=True)
    else:
        print(f"[INFO] Skipped tag creation. Run with --tag to push {next_ver}.")


if __name__ == "__main__":
    main()

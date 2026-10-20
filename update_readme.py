#!/usr/bin/env python3
"""
update_readme.py
────────────────
Fetches all public repos for manojdailycode from the GitHub API,
builds a Markdown table, and injects it between the two markers in README.md:

    <!-- START_SECTION:repos -->
    ...auto-generated content...
    <!-- END_SECTION:repos -->

Run locally:  python update_readme.py
Run by CI:    called from .github/workflows/update-profile.yml
"""

import os
import re
import sys
import requests

USERNAME   = "manojdailycode"
README     = "README.md"
START_TAG  = "<!-- START_SECTION:repos -->"
END_TAG    = "<!-- END_SECTION:repos -->"

# Repos to always skip (profile repo itself + any forks you don't want shown)
SKIP_REPOS = {USERNAME, f"{USERNAME}.github.io"}

# Emoji map — add more as you like
EMOJI_MAP = {
    "movie":   "🎬",
    "cash":    "💰",
    "keeper":  "💰",
    "journal": "📓",
    "api":     "⚡",
    "bot":     "🤖",
    "cli":     "💻",
    "web":     "🌐",
    "game":    "🎮",
    "tool":    "🛠️",
    "script":  "📜",
    "tracker": "📊",
}

def pick_emoji(name: str, description: str) -> str:
    combined = (name + " " + (description or "")).lower()
    for keyword, emoji in EMOJI_MAP.items():
        if keyword in combined:
            return emoji
    return "📦"

def infer_tech(repo: dict) -> str:
    lang = repo.get("language") or ""
    topics = repo.get("topics", [])
    parts = []
    if lang:
        parts.append(f"`{lang}`")
    for t in topics[:3]:          # show up to 3 topic badges
        parts.append(f"`{t}`")
    return " ".join(parts) if parts else "`code`"

def fetch_repos() -> list[dict]:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_PAT_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    repos, page = [], 1
    while True:
        resp = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            headers=headers,
            params={"sort": "updated", "per_page": 100, "page": page, "type": "owner"},
            timeout=15,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos

def build_table(repos: list[dict]) -> str:
    lines = [
        "| Project | Description | Tech |",
        "|---------|-------------|------|",
    ]
    for repo in repos:
        name = repo["name"]
        if name in SKIP_REPOS or repo.get("fork"):
            continue
        url   = repo["html_url"]
        desc  = (repo.get("description") or "No description yet.").strip()
        emoji = pick_emoji(name, desc)
        tech  = infer_tech(repo)
        lines.append(f"| [**{name}**]({url}) | {emoji} {desc} | {tech} |")
    return "\n".join(lines)

def patch_readme(table: str) -> None:
    with open(README, "r", encoding="utf-8") as fh:
        content = fh.read()

    if START_TAG not in content or END_TAG not in content:
        print("❌  Markers not found in README.md — nothing changed.")
        sys.exit(1)

    new_block = f"{START_TAG}\n{table}\n{END_TAG}"
    new_content = re.sub(
        re.escape(START_TAG) + r".*?" + re.escape(END_TAG),
        new_block,
        content,
        flags=re.DOTALL,
    )

    if new_content == content:
        print("✅  No changes — README already up to date.")
        return

    with open(README, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(new_content)
    print("✅  README.md updated with latest projects!")

if __name__ == "__main__":
    print(f"📡  Fetching repos for @{USERNAME}…")
    repos = fetch_repos()
    print(f"   Found {len(repos)} repo(s).")
    table = build_table(repos)
    patch_readme(table)

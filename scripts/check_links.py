#!/usr/bin/env python3
"""Check all GitHub repo links in README files and report dead ones."""

import re
import sys
import json
import urllib.request
import urllib.error
import os

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


def fetch_repo_status(owner: str, repo: str) -> tuple[int, str]:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "awesome-human-distillation")
    req.add_header("Accept", "application/vnd.github+json")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, "ok"
    except urllib.error.HTTPError as e:
        return e.code, str(e)
    except Exception as e:
        return 0, str(e)


def extract_repos(filepath: str) -> list[tuple[str, str]]:
    repos = []
    seen = set()
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            for match in re.finditer(r"https://github\.com/([^/]+)/([^/)\s|]+)", line):
                owner, repo = match.group(1), match.group(2)
                key = f"{owner}/{repo}"
                if key not in seen and owner not in ("mliu98",):
                    seen.add(key)
                    repos.append((owner, repo))
    return repos


def main():
    files = ["README.md", "README_EN.md"]
    dead = []

    all_repos = set()
    for f in files:
        for owner, repo in extract_repos(f):
            all_repos.add((owner, repo))

    print(f"Checking {len(all_repos)} repos...", file=sys.stderr)

    for owner, repo in sorted(all_repos):
        status, msg = fetch_repo_status(owner, repo)
        if status in (404, 451, 0):
            print(f"DEAD [{status}]: {owner}/{repo} — {msg}")
            dead.append(f"{owner}/{repo}")
        else:
            print(f"OK   [{status}]: {owner}/{repo}", file=sys.stderr)

    if dead:
        print(f"\n{len(dead)} dead link(s) found:", file=sys.stderr)
        for d in dead:
            print(f"  - {d}", file=sys.stderr)
        sys.exit(1)
    else:
        print("All links alive.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()

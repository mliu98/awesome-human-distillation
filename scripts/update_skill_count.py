#!/usr/bin/env python3
"""Count skills in README and update the skill count badge."""

import re
import sys


def count_skills(filepath: str) -> int:
    count = 0
    in_table = False
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            # Table header rows contain "Name" or "名字"
            if re.match(r"\|\s*(Name|名字)\s*\|", line):
                in_table = True
                continue
            if in_table:
                if line.startswith("|---"):
                    continue
                elif line.startswith("|"):
                    count += 1
                else:
                    in_table = False
    return count


def update_badge(filepath: str, count: int):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    badge = f"[![Skills](https://img.shields.io/badge/skills-{count}-brightgreen?style=flat-square)](#{{}})".format("")
    new_badge = f"[![Skills](https://img.shields.io/badge/skills-{count}-brightgreen?style=flat-square)](#)"

    # Replace existing skill count badge or insert after awesome badge
    if "img.shields.io/badge/skills-" in content:
        content = re.sub(
            r"\[!\[Skills\]\(https://img\.shields\.io/badge/skills-\d+-[^)]+\)\]\([^)]*\)",
            new_badge,
            content,
        )
    else:
        content = content.replace(
            "[![Awesome](https://awesome.re/badge.svg)](https://awesome.re)",
            f"[![Awesome](https://awesome.re/badge.svg)](https://awesome.re) {new_badge}",
            1,
        )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Updated {filepath}: {count} skills")


if __name__ == "__main__":
    # Use README.md as source of truth for count
    count = count_skills("README.md")
    print(f"Total skills: {count}", file=sys.stderr)
    for filepath in ["README.md", "README_EN.md"]:
        update_badge(filepath, count)

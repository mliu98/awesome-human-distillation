#!/usr/bin/env python3
"""Auto-process [Skill] issues: parse, add to README, comment, close."""

import json
import os
import re
import subprocess
import sys
import urllib.request

REPO = "mliu98/awesome-human-distillation"

SECTION_ZH = {
    "职场": "## 职场关系 Workplace",
    "学术": "## 学术关系 Academia",
    "亲密": "## 亲密关系 Intimate",
    "家庭": "## 家庭关系 Family",
    "公众": "## 公众人物 Public Figures",
}
SECTION_EN = {
    "职场": "## Workplace",
    "学术": "## Academia",
    "亲密": "## Intimate",
    "家庭": "## Family",
    "公众": "## Public Figures",
}
DEFAULT_ZH = "## 其他 / 泛用工具 General"
DEFAULT_EN = "## General / Tools"


def gh(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"gh error: {result.stderr}", file=sys.stderr)
    return result.stdout.strip()


def get_open_skill_issues():
    raw = gh("issue", "list", "--repo", REPO, "--state", "open",
             "--json", "number,title,body", "--limit", "100")
    issues = json.loads(raw) if raw else []
    return [i for i in issues if i["title"].startswith("[Skill]")]


def parse_body(body: str) -> dict:
    """Parse GitHub issue form body (### Field\\nValue) into a dict."""
    fields = {}
    parts = re.split(r"^### (.+)$", body, flags=re.MULTILINE)
    for i in range(1, len(parts) - 1, 2):
        key = parts[i].strip()
        val = parts[i + 1].strip()
        fields[key] = val
    return fields


def section_for(distill_type: str):
    for keyword in SECTION_ZH:
        if keyword in distill_type:
            return SECTION_ZH[keyword], SECTION_EN[keyword]
    return DEFAULT_ZH, DEFAULT_EN


def already_in(content: str, repo_url: str) -> bool:
    m = re.search(r"github\.com/([^/\s]+/[^/\s)]+)", repo_url)
    if m:
        return m.group(1).rstrip("/") in content
    return False


def translate(zh_desc: str, skill_name: str) -> str:
    """Call Claude API to translate description to English."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return zh_desc  # fallback: keep Chinese

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 120,
        "messages": [{
            "role": "user",
            "content": (
                f"Translate this Chinese skill description to concise English "
                f"(one sentence, under 25 words, no trailing period):\n"
                f"Skill: {skill_name}\n"
                f"Chinese: {zh_desc}\n"
                f"English:"
            )
        }]
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"].strip()
    except Exception as e:
        print(f"Warning: translation failed: {e}", file=sys.stderr)
        return zh_desc


def build_row(skill_name: str, repo_name: str, owner: str,
              repo_url: str, description: str) -> str:
    repo_url = repo_url.rstrip("/")
    return (
        f"| {skill_name} | [{repo_name}]({repo_url}) | "
        f"[@{owner}](https://github.com/{owner}) | "
        f"{description} | "
        f"![Stars](https://img.shields.io/github/stars/{owner}/{repo_name}"
        f"?style=flat-square) |"
    )


def insert_row(content: str, section_header: str, new_row: str) -> str:
    """Append new_row after the last table row in section_header."""
    lines = content.split("\n")
    in_section = False
    last_table_idx = -1

    for i, line in enumerate(lines):
        if line.strip() == section_header.strip():
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            if line.startswith("| "):
                last_table_idx = i

    if last_table_idx == -1:
        print(f"Warning: section '{section_header}' not found", file=sys.stderr)
        return content

    lines.insert(last_table_idx + 1, new_row)
    return "\n".join(lines)


def main():
    issues = get_open_skill_issues()
    if not issues:
        print("No open [Skill] issues.")
        return

    with open("README.md") as f:
        readme_zh = f.read()
    with open("README_EN.md") as f:
        readme_en = f.read()

    added = []  # list of (number, skill_name, section_zh)

    for issue in issues:
        number = issue["number"]
        fields = parse_body(issue["body"])

        distill_type = fields.get("蒸馏对象类型", "")
        skill_name = fields.get("Skill 展示名字", "").strip()
        repo_name = fields.get("GitHub 仓库名", "").strip()
        repo_url = fields.get("GitHub 链接", "").strip()
        desc_zh = fields.get("一句话描述", "").strip()

        if not all([skill_name, repo_name, repo_url, desc_zh]):
            print(f"#{number}: missing fields, skipping")
            continue

        if already_in(readme_zh, repo_url):
            print(f"#{number}: {skill_name} already in README, closing")
            gh("issue", "comment", str(number), "--repo", REPO,
               "--body", f"感谢支持！{skill_name} 已收录 🎉")
            gh("issue", "close", str(number), "--repo", REPO)
            continue

        m = re.search(r"github\.com/([^/]+)/", repo_url)
        owner = m.group(1) if m else repo_name

        desc_en = translate(desc_zh, skill_name)
        sec_zh, sec_en = section_for(distill_type)

        row_zh = build_row(skill_name, repo_name, owner, repo_url, desc_zh)
        row_en = build_row(skill_name, repo_name, owner, repo_url, desc_en)

        readme_zh = insert_row(readme_zh, sec_zh, row_zh)
        readme_en = insert_row(readme_en, sec_en, row_en)

        added.append((number, skill_name, sec_zh))
        print(f"#{number}: added {skill_name} → {sec_zh}")

    if not added:
        print("Nothing new to add.")
        return

    with open("README.md", "w") as f:
        f.write(readme_zh)
    with open("README_EN.md", "w") as f:
        f.write(readme_en)

    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(["git", "config", "user.email",
                    "github-actions[bot]@users.noreply.github.com"], check=True)

    refs = " ".join(f"#{n}" for n, _, _ in added)
    subprocess.run(["git", "add", "README.md", "README_EN.md"], check=True)
    subprocess.run(["git", "commit", "-m",
                    f"feat: auto-add skills from issues {refs} [skip ci]"], check=True)
    subprocess.run(["git", "push"], check=True)

    for number, skill_name, sec_zh in added:
        section_label = sec_zh.replace("## ", "").strip()
        gh("issue", "comment", str(number), "--repo", REPO,
           "--body", f"感谢支持！{skill_name} 已自动收录进「{section_label}」区 🎉")
        gh("issue", "close", str(number), "--repo", REPO)


if __name__ == "__main__":
    main()

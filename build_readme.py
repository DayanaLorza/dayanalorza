#!/usr/bin/env python3
"""Refresh the Recently shipped block from DayanaLorza's public GitHub repos."""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

OWNER = "DayanaLorza"
README = Path(__file__).with_name("README.md")
START = "<!-- shipped starts -->"
END = "<!-- shipped ends -->"


def github_json(path: str):
    url = "https://api.github.com" + path
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "DayanaLorza-profile-readme",
            **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def latest_repositories():
    repos = github_json(
        f"/users/{OWNER}/repos?type=owner&sort=pushed&direction=desc&per_page=100"
    )
    public_repos = [repo for repo in repos if not repo.get("private", True)]
    public_repos.sort(key=lambda repo: repo.get("pushed_at") or "", reverse=True)

    shipped = []
    for repo in public_repos[:5]:
        name = repo["name"]
        commits = github_json(
            "/repos/{}/{}/commits?per_page=1".format(
                urllib.parse.quote(OWNER), urllib.parse.quote(name)
            )
        )
        if not commits:
            continue
        commit = commits[0]["commit"]
        message = commit["message"].splitlines()[0].strip()
        # Keep generated Markdown on one line even if a commit subject is unusual.
        message = re.sub(r"[\r\n]+", " ", message)
        date_text = (commit.get("author") or commit.get("committer") or {})["date"]
        date = datetime.fromisoformat(date_text.replace("Z", "+00:00")).date().isoformat()
        shipped.append(f"- [{name}]({repo['html_url']}) — {message} — {date}")
    return shipped


def update_readme(lines):
    readme = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    replacement = START + "\n" + "\n".join(lines) + "\n" + END
    updated, count = pattern.subn(replacement, readme, count=1)
    if count != 1:
        raise RuntimeError("README markers are missing or duplicated")
    if updated != readme:
        README.write_text(updated, encoding="utf-8")
        return True
    return False


if __name__ == "__main__":
    lines = latest_repositories()
    if not lines:
        raise RuntimeError("GitHub returned no public repositories with commits")
    update_readme(lines)

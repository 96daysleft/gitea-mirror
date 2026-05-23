#!/usr/bin/env python3
"""Sync GitHub org repos to Gitea as mirrors."""

import json
import sys
import tomllib
import requests


def _load_secrets():
    with open("secret.json") as f:
        return json.load(f)


def _load_config():
    cfg = {}
    try:
        with open("pyproject.toml", "rb") as f:
            cfg = tomllib.load(f).get("tool", {}).get("mirror_sync", {})
    except FileNotFoundError:
        pass
    return cfg


_secrets = _load_secrets()
_cfg = _load_config()

GITHUB_TOKEN = _secrets["github_token"]
GITHUB_ORG = _cfg["github_org"]
GITEA_URL = _cfg["gitea_url"].rstrip("/")
GITEA_TOKEN = _secrets["gitea_token"]
GITEA_ORG = _cfg.get("gitea_org")
GITEA_UID = int(_cfg["gitea_uid"]) if "gitea_uid" in _cfg else None
MIRROR_INTERVAL = _cfg.get("mirror_interval", "8h")

GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}
GITEA_HEADERS = {
    "Authorization": f"token {GITEA_TOKEN}",
    "Content-Type": "application/json",
}


def get_github_repos():
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"https://api.github.com/orgs/{GITHUB_ORG}/repos",
            headers=GITHUB_HEADERS,
            params={"per_page": 100, "page": page},
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def get_gitea_repos():
    repos = set()
    page = 1
    while True:
        r = requests.get(
            f"{GITEA_URL}/api/v1/repos/search",
            headers=GITEA_HEADERS,
            params={"limit": 50, "page": page},
        )
        r.raise_for_status()
        data = r.json()
        batch = data.get("data", [])
        if not batch:
            break
        repos.update(repo["name"] for repo in batch)
        page += 1
    return repos


def migrate_repo(repo):
    payload = {
        "clone_addr": repo["clone_url"],
        "auth_token": GITHUB_TOKEN,
        "repo_name": repo["name"],
        "description": repo.get("description") or "",
        "private": repo["private"],
        "mirror": True,
        "mirror_interval": MIRROR_INTERVAL,
    }

    if GITEA_ORG:
        payload["repo_owner"] = GITEA_ORG
    elif GITEA_UID is not None:
        payload["uid"] = GITEA_UID
    else:
        print("  [!] Missing target owner: set gitea_org or gitea_uid", file=sys.stderr)
        return

    r = requests.post(
        f"{GITEA_URL}/api/v1/repos/migrate",
        headers=GITEA_HEADERS,
        json=payload,
    )
    if r.status_code == 201:
        print(f"  [+] Migrated: {repo['name']}")
    elif r.status_code == 409:
        print(f"  [=] Already exists (conflict): {repo['name']}")
    else:
        print(f"  [!] Failed {repo['name']}: {r.status_code} {r.text}", file=sys.stderr)


def main():
    print(f"Fetching repos from GitHub org: {GITHUB_ORG}")
    github_repos = get_github_repos()
    print(f"  Found {len(github_repos)} repos on GitHub")

    print(f"Fetching existing repos from Gitea: {GITEA_URL}")
    gitea_repos = get_gitea_repos()
    print(f"  Found {len(gitea_repos)} repos on Gitea")

    missing = [r for r in github_repos if r["name"] not in gitea_repos]
    print(f"\n{len(missing)} repos to migrate:")

    for repo in missing:
        print(f"Missing repo {repo.get('name')}")
        migrate_repo(repo)

    print("\nDone.")


if __name__ == "__main__":
    main()

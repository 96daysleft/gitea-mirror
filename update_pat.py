#!/usr/bin/env python3
"""Update the GitHub PAT for every pull-mirror repo in the Gitea org.

Gitea has no dedicated "update mirror credentials" endpoint in API v1, so this
script uses delete + re-migrate: safe for mirror-only repos because all git data
lives on GitHub and will be re-synced immediately.

Run with --dry-run to preview which repos would be updated.
"""

import json
import sys
import tomllib
import requests

DRY_RUN = "--dry-run" in sys.argv


def _load_secrets():
    with open("secret.json") as f:
        return json.load(f)


def _load_config():
    try:
        with open("pyproject.toml", "rb") as f:
            return tomllib.load(f).get("tool", {}).get("mirror_sync", {})
    except FileNotFoundError:
        return {}


_secrets = _load_secrets()
_cfg = _load_config()

GITHUB_TOKEN = _secrets["github_token"]
GITEA_URL = _cfg["gitea_url"].rstrip("/")
GITEA_TOKEN = _secrets["gitea_token"]
GITEA_ORG = _cfg["gitea_org"]
MIRROR_INTERVAL = _cfg.get("mirror_interval", "8h")

GITEA_HEADERS = {
    "Authorization": f"token {GITEA_TOKEN}",
    "Content-Type": "application/json",
}


def get_org_id():
    r = requests.get(f"{GITEA_URL}/api/v1/orgs/{GITEA_ORG}", headers=GITEA_HEADERS)
    r.raise_for_status()
    return r.json()["id"]


def get_mirrored_repos():
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"{GITEA_URL}/api/v1/org/{GITEA_ORG}/repos",
            headers=GITEA_HEADERS,
            params={"limit": 50, "page": page},
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(repo for repo in batch if repo.get("mirror"))
        page += 1
    return repos


def delete_repo(owner, name):
    r = requests.delete(
        f"{GITEA_URL}/api/v1/repos/{owner}/{name}",
        headers=GITEA_HEADERS,
    )
    r.raise_for_status()


def remigrate(repo, org_id):
    owner = repo["owner"]["login"]
    name = repo["name"]
    original_url = repo.get("original_url", "")

    if not original_url:
        print(f"  [!] {name}: missing original_url, skipping", file=sys.stderr)
        return False

    payload = {
        "clone_addr": original_url,
        "auth_token": GITHUB_TOKEN,
        "repo_owner": GITEA_ORG,
        "repo_name": name,
        "description": repo.get("description") or "",
        "private": repo["private"],
        "mirror": True,
        "mirror_interval": MIRROR_INTERVAL,
    }

    r = requests.post(
        f"{GITEA_URL}/api/v1/repos/migrate",
        headers=GITEA_HEADERS,
        json=payload,
    )
    if r.status_code == 201:
        print(f"  [+] Re-migrated: {owner}/{name}")
        return True
    else:
        print(f"  [!] Re-migrate failed for {owner}/{name}: {r.status_code} {r.text}", file=sys.stderr)
        return False


def update_repo(repo, org_id):
    owner = repo["owner"]["login"]
    name = repo["name"]

    if DRY_RUN:
        print(f"  [dry] Would update: {owner}/{name}  ({repo.get('original_url')})")
        return

    print(f"  Updating {owner}/{name} ...")
    delete_repo(owner, name)
    remigrate(repo, org_id)


def main():
    if DRY_RUN:
        print("--- DRY RUN ---")

    print(f"Fetching mirrored repos from org: {GITEA_ORG}")
    org_id = get_org_id()
    repos = get_mirrored_repos()
    print(f"  Found {len(repos)} mirror repo(s)\n")

    for repo in repos:
        update_repo(repo, org_id)

    print("\nDone.")


if __name__ == "__main__":
    main()

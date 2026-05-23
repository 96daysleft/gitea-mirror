#!/usr/bin/env python3
"""Update the GitHub PAT for every pull-mirror repo in the Gitea org.

Gitea has no dedicated "update mirror credentials" endpoint in API v1, so this
script uses delete + re-migrate: safe for mirror-only repos because all git data
lives on GitHub and will be re-synced immediately.

Run with --dry-run to preview which repos would be updated.
"""

import argparse
import sys

import requests

from config import ConfigError, Settings, load_settings

TIMEOUT = 30


def gitea_headers(s: Settings):
    return {
        "Authorization": f"token {s.gitea_token}",
        "Content-Type": "application/json",
    }


def get_org_id(s: Settings):
    r = requests.get(
        f"{s.gitea_url}/api/v1/orgs/{s.gitea_org}",
        headers=gitea_headers(s),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["id"]


def get_mirrored_repos(s: Settings):
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"{s.gitea_url}/api/v1/org/{s.gitea_org}/repos",
            headers=gitea_headers(s),
            params={"limit": 50, "page": page},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(repo for repo in batch if repo.get("mirror"))
        page += 1
    return repos


def delete_repo(s: Settings, owner, name):
    r = requests.delete(
        f"{s.gitea_url}/api/v1/repos/{owner}/{name}",
        headers=gitea_headers(s),
        timeout=TIMEOUT,
    )
    r.raise_for_status()


def remigrate(s: Settings, repo):
    owner = repo["owner"]["login"]
    name = repo["name"]
    original_url = repo.get("original_url", "")

    if not original_url:
        print(f"  [!] {name}: missing original_url, skipping", file=sys.stderr)
        return False

    payload = {
        "clone_addr": original_url,
        "auth_token": s.github_token,
        "repo_owner": s.gitea_org,
        "repo_name": name,
        "description": repo.get("description") or "",
        "private": repo["private"],
        "mirror": True,
        "mirror_interval": s.mirror_interval,
    }

    r = requests.post(
        f"{s.gitea_url}/api/v1/repos/migrate",
        headers=gitea_headers(s),
        json=payload,
        timeout=TIMEOUT,
    )
    if r.status_code == 201:
        print(f"  [+] Re-migrated: {owner}/{name}")
        return True

    print(
        f"  [!] Re-migrate failed for {owner}/{name}: {r.status_code} {r.text}",
        file=sys.stderr,
    )
    return False


def update_repo(s: Settings, repo, dry_run=False):
    owner = repo["owner"]["login"]
    name = repo["name"]

    if dry_run:
        print(f"  [dry] Would update: {owner}/{name}  ({repo.get('original_url')})")
        return

    print(f"  Updating {owner}/{name} ...")
    delete_repo(s, owner, name)
    remigrate(s, repo)


def main(dry_run=False, settings: Settings | None = None):
    """Run the PAT rotation. `settings` is for test injection; the CLI always
    passes None and lets this load settings itself."""
    if settings is None:
        try:
            settings = load_settings(need_github_org=False, need_gitea_org=True)
        except ConfigError as e:
            raise SystemExit(str(e))

    if dry_run:
        print("--- DRY RUN ---")

    print(f"Fetching mirrored repos from org: {settings.gitea_org}")
    get_org_id(settings)  # fail early if the org doesn't exist
    repos = get_mirrored_repos(settings)
    print(f"  Found {len(repos)} mirror repo(s)\n")

    for repo in repos:
        update_repo(settings, repo, dry_run=dry_run)

    print("\nDone.")


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Rotate GitHub PAT for mirrored repos")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview repos that would be updated without making changes",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(dry_run=args.dry_run)

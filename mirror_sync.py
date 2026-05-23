#!/usr/bin/env python3
"""Sync GitHub org repos to Gitea as mirrors."""

import sys

import requests

from config import ConfigError, Settings, load_settings

TIMEOUT = 30


def github_headers(s: Settings):
    return {
        "Authorization": f"token {s.github_token}",
        "Accept": "application/vnd.github+json",
    }


def gitea_headers(s: Settings):
    return {
        "Authorization": f"token {s.gitea_token}",
        "Content-Type": "application/json",
    }


def get_github_repos(s: Settings):
    # Note: /users/{name}/repos only lists public repos.
    kind = "orgs" if s.github_owner_type == "org" else "users"
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"https://api.github.com/{kind}/{s.github_org}/repos",
            headers=github_headers(s),
            params={"per_page": 100, "page": page},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def get_gitea_repos(s: Settings):
    repos = set()
    page = 1
    while True:
        r = requests.get(
            f"{s.gitea_url}/api/v1/repos/search",
            headers=gitea_headers(s),
            params={"limit": 50, "page": page},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        batch = data.get("data", [])
        if not batch:
            break
        repos.update(repo["name"] for repo in batch)
        page += 1
    return repos


def migrate_repo(s: Settings, repo):
    payload = {
        "clone_addr": repo["clone_url"],
        "auth_token": s.github_token,
        "repo_name": repo["name"],
        "description": repo.get("description") or "",
        "private": repo["private"],
        "mirror": True,
        "mirror_interval": s.mirror_interval,
    }

    if s.gitea_org:
        payload["repo_owner"] = s.gitea_org
    elif s.gitea_uid is not None:
        payload["uid"] = s.gitea_uid
    else:
        print("  [!] Missing target owner: set gitea_org or gitea_uid", file=sys.stderr)
        return

    r = requests.post(
        f"{s.gitea_url}/api/v1/repos/migrate",
        headers=gitea_headers(s),
        json=payload,
        timeout=TIMEOUT,
    )
    if r.status_code == 201:
        print(f"  [+] Migrated: {repo['name']}")
    elif r.status_code == 409:
        print(f"  [=] Already exists (conflict): {repo['name']}")
    else:
        print(f"  [!] Failed {repo['name']}: {r.status_code} {r.text}", file=sys.stderr)


def main(settings: Settings | None = None):
    """Run the sync. `settings` is for test injection; the CLI always passes None
    and lets this load settings itself, since only one subcommand runs per process."""
    if settings is None:
        try:
            settings = load_settings(need_github_org=True)
        except ConfigError as e:
            raise SystemExit(str(e))

    print(f"Fetching repos from GitHub {settings.github_owner_type}: {settings.github_org}")
    github_repos = get_github_repos(settings)
    print(f"  Found {len(github_repos)} repos on GitHub")

    print(f"Fetching existing repos from Gitea: {settings.gitea_url}")
    gitea_repos = get_gitea_repos(settings)
    print(f"  Found {len(gitea_repos)} repos on Gitea")

    missing = [r for r in github_repos if r["name"] not in gitea_repos]
    print(f"\n{len(missing)} repos to migrate:")

    for repo in missing:
        print(f"Missing repo {repo.get('name')}")
        migrate_repo(settings, repo)

    print("\nDone.")


if __name__ == "__main__":
    main()

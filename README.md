# gitea-mirror

Sync GitHub org repos to Gitea as mirrors.

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv gitea-mirror-venv
```

### 2. Activate the virtual environment

**Linux / macOS:**
```bash
source gitea-mirror-venv/bin/activate
```

**Windows:**
```bash
gitea-mirror-venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install .
```

### 4. Configure secrets

Create a `secret.json` file in the project root:

```json
{
  "github_token": "your_github_pat",
  "gitea_token": "your_gitea_token"
}
```

### 5. Configure the target orgs

Defaults live in the `[tool.mirror_sync]` section of `pyproject.toml`. Edit them, or override any of them with environment variables (env vars take precedence):

| `pyproject.toml` key | Env var | Description |
|---|---|---|
| `github_org` | `GITHUB_ORG` | GitHub org to mirror from |
| `gitea_url` | `GITEA_URL` | Base URL of your Gitea instance |
| `gitea_org` | `GITEA_ORG` | Gitea org that owns the mirrors |
| `mirror_interval` | `MIRROR_INTERVAL` | Mirror sync interval (default `8h`) |

Tokens can likewise be supplied as `GITHUB_TOKEN` and `GITEA_TOKEN` instead of `secret.json`.

Optional settings:

| Env var | Description |
|---|---|
| `GITHUB_OWNER_TYPE` | `org` (default) or `user`. With `user`, only public repos are listed. |
| `GITEA_UID` | Gitea user ID to own the mirrors, used when `gitea_org` is not set |

### Token permissions

- **GitHub PAT:** read access to the repos to mirror. A classic PAT needs `repo` (private repos) or no scopes (public only). A fine-grained PAT needs *Contents: read* and *Metadata: read* on the org's repos.
- **Gitea token:** `write:repository` and `write:organization`, so it can create migrations in the target org.

Missing configuration is reported up front, listing each value and the env var that sets it.

## Usage

**Sync missing repos from GitHub to Gitea:**
```bash
python main.py sync
```

**Update the GitHub PAT on all mirror repos:**
```bash
python main.py update-pat
```

**Dry run (preview only):**
```bash
python main.py update-pat --dry-run
```

**If installed as a package, use the console script:**
```bash
mirror-sync sync
mirror-sync update-pat --dry-run
```

## Docker

```bash
docker run --rm \
  -e GITHUB_TOKEN -e GITEA_TOKEN \
  -e GITHUB_ORG=your-github-org \
  -e GITEA_URL=https://gitea.example.com \
  -e GITEA_ORG=your-gitea-org \
  ghcr.io/96daysleft/gitea-mirror:latest sync
```

## Kubernetes

[examples/cronjob.yaml](examples/cronjob.yaml) runs `sync` on a schedule. Tokens come from a Secret, which you can populate with External Secrets or any secret manager.

## Development

```bash
pip install ".[dev]"
pytest
```

## License

MIT, see [LICENSE](LICENSE).

## Deactivate the virtual environment

```bash
deactivate
```

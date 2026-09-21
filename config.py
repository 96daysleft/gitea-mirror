"""Shared configuration loading for the mirror tools.

Values come from environment variables first, then (for tokens) ``secret.json``
and (for everything else) the ``[tool.mirror_sync]`` table in ``pyproject.toml``.
Nothing is read at import time; call :func:`load_settings` when you need them.
"""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from typing import Optional


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    github_token: str
    gitea_token: str
    gitea_url: str
    github_org: Optional[str] = None
    github_owner_type: str = "org"
    gitea_org: Optional[str] = None
    gitea_uid: Optional[int] = None
    mirror_interval: str = "8h"


# config key -> environment variable
_ENV_VARS = {
    "github_org": "GITHUB_ORG",
    "github_owner_type": "GITHUB_OWNER_TYPE",
    "gitea_url": "GITEA_URL",
    "gitea_org": "GITEA_ORG",
    "gitea_uid": "GITEA_UID",
    "mirror_interval": "MIRROR_INTERVAL",
}


def _read_secret_file(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _read_pyproject(path: str) -> dict:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f).get("tool", {}).get("mirror_sync", {})
    except FileNotFoundError:
        return {}


def load_settings(
    *,
    need_github_org: bool = True,
    need_gitea_org: bool = False,
    secret_path: str = "secret.json",
    pyproject_path: str = "pyproject.toml",
) -> Settings:
    file_secrets = _read_secret_file(secret_path)
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token is None:
        github_token = file_secrets.get("github_token")
    gitea_token = os.environ.get("GITEA_TOKEN")
    if gitea_token is None:
        gitea_token = file_secrets.get("gitea_token")


    cfg = dict(_read_pyproject(pyproject_path))
    for key, env_var in _ENV_VARS.items():
        val = os.environ.get(env_var)
        if val:
            cfg[key] = val

    missing = []
    if not github_token:
        missing.append("GITHUB_TOKEN (or github_token in secret.json)")
    if not gitea_token:
        missing.append("GITEA_TOKEN (or gitea_token in secret.json)")
    if not cfg.get("gitea_url"):
        missing.append("GITEA_URL (or gitea_url in [tool.mirror_sync])")
    if need_github_org and not cfg.get("github_org"):
        missing.append("GITHUB_ORG (or github_org in [tool.mirror_sync])")
    if need_gitea_org and not cfg.get("gitea_org"):
        missing.append("GITEA_ORG (or gitea_org in [tool.mirror_sync])")
    if missing:
        raise ConfigError("Missing configuration: " + "; ".join(missing))

    owner_type = str(cfg.get("github_owner_type", "org")).lower()
    if owner_type not in ("org", "user"):
        raise ConfigError("github_owner_type must be 'org' or 'user'")

    return Settings(
        github_token=github_token,
        gitea_token=gitea_token,
        gitea_url=str(cfg["gitea_url"]).rstrip("/"),
        github_org=cfg.get("github_org"),
        github_owner_type=owner_type,
        gitea_org=cfg.get("gitea_org"),
        gitea_uid=int(cfg["gitea_uid"]) if cfg.get("gitea_uid") is not None else None,
        mirror_interval=str(cfg.get("mirror_interval", "8h")),
    )

from unittest.mock import MagicMock

import mirror_sync
from config import Settings


def make_settings(**kw):
    base = dict(
        github_token="gh", gitea_token="gt", gitea_url="https://gitea.test",
        github_org="acme", gitea_org="mirrors",
    )
    base.update(kw)
    return Settings(**base)


def resp(json_data=None, status=200, text=""):
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.json.return_value = json_data
    return r


def test_github_repos_paginates_org(monkeypatch):
    calls = []

    def fake_get(url, **kw):
        calls.append((url, kw["params"]["page"]))
        return resp([{"name": "a"}] if kw["params"]["page"] == 1 else [])

    monkeypatch.setattr(mirror_sync.requests, "get", fake_get)
    repos = mirror_sync.get_github_repos(make_settings())
    assert [r["name"] for r in repos] == ["a"]
    assert calls[0][0] == "https://api.github.com/orgs/acme/repos"


def test_github_repos_user_endpoint(monkeypatch):
    urls = []
    monkeypatch.setattr(
        mirror_sync.requests, "get", lambda url, **kw: urls.append(url) or resp([])
    )
    mirror_sync.get_github_repos(make_settings(github_owner_type="user"))
    assert urls == ["https://api.github.com/users/acme/repos"]


def test_migrate_repo_payload(monkeypatch):
    posted = {}

    def fake_post(url, **kw):
        posted.update(url=url, **kw)
        return resp(status=201)

    monkeypatch.setattr(mirror_sync.requests, "post", fake_post)
    repo = {"name": "r", "clone_url": "https://github.com/acme/r.git", "private": True}
    mirror_sync.migrate_repo(make_settings(), repo)
    assert posted["url"] == "https://gitea.test/api/v1/repos/migrate"
    assert posted["json"]["repo_owner"] == "mirrors"
    assert posted["json"]["mirror"] is True
    assert posted["timeout"] == mirror_sync.TIMEOUT


def test_migrate_repo_without_owner_skips(monkeypatch, capsys):
    monkeypatch.setattr(
        mirror_sync.requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError)
    )
    repo = {"name": "r", "clone_url": "u", "private": False}
    mirror_sync.migrate_repo(make_settings(gitea_org=None), repo)
    assert "Missing target owner" in capsys.readouterr().err


def test_main_only_migrates_missing(monkeypatch):
    monkeypatch.setattr(
        mirror_sync, "get_github_repos", lambda s: [{"name": "a"}, {"name": "b"}]
    )
    monkeypatch.setattr(mirror_sync, "get_gitea_repos", lambda s: {"a"})
    migrated = []
    monkeypatch.setattr(mirror_sync, "migrate_repo", lambda s, r: migrated.append(r["name"]))
    mirror_sync.main(make_settings())
    assert migrated == ["b"]

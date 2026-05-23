import pytest

from config import ConfigError, load_settings

ENV_VARS = [
    "GITHUB_TOKEN", "GITEA_TOKEN", "GITHUB_ORG", "GITHUB_OWNER_TYPE",
    "GITEA_URL", "GITEA_ORG", "GITEA_UID", "MIRROR_INTERVAL",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def load(tmp_path, **kwargs):
    return load_settings(
        secret_path=str(tmp_path / "secret.json"),
        pyproject_path=str(tmp_path / "pyproject.toml"),
        **kwargs,
    )


def test_env_only(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "gh")
    monkeypatch.setenv("GITEA_TOKEN", "gt")
    monkeypatch.setenv("GITEA_URL", "https://gitea.test/")
    monkeypatch.setenv("GITHUB_ORG", "acme")
    s = load(tmp_path)
    assert s.gitea_url == "https://gitea.test"
    assert s.github_org == "acme"
    assert s.github_owner_type == "org"
    assert s.mirror_interval == "8h"


def test_file_and_pyproject_with_env_override(tmp_path, monkeypatch):
    (tmp_path / "secret.json").write_text('{"github_token": "gh", "gitea_token": "gt"}')
    (tmp_path / "pyproject.toml").write_text(
        '[tool.mirror_sync]\ngithub_org = "a"\ngitea_url = "https://x"\ngitea_org = "b"\n'
    )
    monkeypatch.setenv("GITHUB_ORG", "override")
    s = load(tmp_path)
    assert s.github_org == "override"
    assert s.gitea_org == "b"
    assert s.github_token == "gh"


def test_missing_values_are_listed(tmp_path):
    with pytest.raises(ConfigError) as e:
        load(tmp_path)
    msg = str(e.value)
    for name in ("GITHUB_TOKEN", "GITEA_TOKEN", "GITEA_URL", "GITHUB_ORG"):
        assert name in msg


def test_github_org_optional(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "gh")
    monkeypatch.setenv("GITEA_TOKEN", "gt")
    monkeypatch.setenv("GITEA_URL", "https://gitea.test")
    assert load(tmp_path, need_github_org=False).github_org is None


def test_bad_owner_type(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "gh")
    monkeypatch.setenv("GITEA_TOKEN", "gt")
    monkeypatch.setenv("GITEA_URL", "https://gitea.test")
    monkeypatch.setenv("GITHUB_ORG", "acme")
    monkeypatch.setenv("GITHUB_OWNER_TYPE", "team")
    with pytest.raises(ConfigError):
        load(tmp_path)

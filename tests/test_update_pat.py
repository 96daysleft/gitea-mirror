import update_pat
from test_mirror_sync import make_settings, resp


def repo(name="r", url="https://github.com/acme/r.git"):
    return {"name": name, "owner": {"login": "mirrors"}, "original_url": url,
            "private": False, "mirror": True}


def test_dry_run_changes_nothing(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not call API in dry run")

    monkeypatch.setattr(update_pat.requests, "delete", boom)
    monkeypatch.setattr(update_pat.requests, "post", boom)
    update_pat.update_repo(make_settings(), repo(), dry_run=True)


def test_update_deletes_then_remigrates(monkeypatch):
    order = []
    monkeypatch.setattr(
        update_pat.requests, "delete", lambda *a, **k: order.append("delete") or resp()
    )
    monkeypatch.setattr(
        update_pat.requests, "post", lambda *a, **k: order.append("post") or resp(status=201)
    )
    update_pat.update_repo(make_settings(), repo())
    assert order == ["delete", "post"]


def test_remigrate_skips_without_original_url(monkeypatch):
    monkeypatch.setattr(update_pat.requests, "post", lambda *a, **k: 1 / 0)
    assert update_pat.remigrate(make_settings(), repo(url="")) is False

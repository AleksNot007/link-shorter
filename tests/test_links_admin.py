from datetime import datetime, timedelta

from app import main as app_main
from app.models import ExpiredLink, Link
from tests.helpers import login_token


def test_expired_redirect_and_history(client):
    token = login_token(client, "exp_user")
    old = (datetime.utcnow() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
    made = client.post(
        "/links/shorten",
        headers={"token": token},
        json={
            "original_url": "https://example.com/expired",
            "custom_alias": "exp-link",
            "expires_at": old,
        },
    )
    assert made.status_code == 200

    redir = client.get("/links/exp-link", follow_redirects=False)
    assert redir.status_code == 404

    hist = client.get("/admin/expired-history", params={"limit": 20})
    assert hist.status_code == 200
    codes = [x["short_code"] for x in hist.json()["items"] if "short_code" in x]
    assert "exp-link" in codes


def test_cleanup_unused_and_old_rows(client):
    token = login_token(client, "cleanup_user")
    made1 = client.post(
        "/links/shorten",
        headers={"token": token},
        json={"original_url": "https://example.com/old1", "custom_alias": "old1"},
    )
    made2 = client.post(
        "/links/shorten",
        headers={"token": token},
        json={"original_url": "https://example.com/old2", "custom_alias": "old2"},
    )
    assert made1.status_code == 200
    assert made2.status_code == 200

    client.get("/links/old2", follow_redirects=False)

    db = app_main.SessionLocal()
    try:
        l1 = db.query(Link).filter(Link.short_code == "old1").first()
        l2 = db.query(Link).filter(Link.short_code == "old2").first()
        l1.created_at = datetime.utcnow() - timedelta(days=10)
        l2.last_used_at = datetime.utcnow() - timedelta(days=10)
        db.commit()

        border = datetime.utcnow() - timedelta(days=1)
        rows = app_main.old_rows(db, border)
        got = sorted([x.short_code for x in rows])
        assert got == ["old1", "old2"]
    finally:
        db.close()

    cleaned = client.post("/admin/cleanup-unused", params={"days": 1})
    assert cleaned.status_code == 200
    assert cleaned.json()["removed"] >= 2


def test_manual_expire_helpers(client):
    token = login_token(client, "tick_user")
    old = (datetime.utcnow() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
    made = client.post(
        "/links/shorten",
        headers={"token": token},
        json={"original_url": "https://example.com/tick", "custom_alias": "tick1", "expires_at": old},
    )
    assert made.status_code == 200

    app_main.cache_set("stats:tick1", '{"k":"v"}', 60)
    assert app_main.cache_get("stats:tick1") is not None

    removed = app_main.expired_tick()
    assert "tick1" in removed
    app_main.expired_clean(removed)

    db = app_main.SessionLocal()
    try:
        gone = db.query(Link).filter(Link.short_code == "tick1").first()
        moved = db.query(ExpiredLink).filter(ExpiredLink.short_code == "tick1").first()
        assert gone is None
        assert moved is not None
    finally:
        db.close()

    class BadRedis:
        def get(self, key):
            raise RuntimeError("x")

        def set(self, key, value, ex=None):
            raise RuntimeError("x")

        def delete(self, key):
            raise RuntimeError("x")

    prev = app_main.rdb
    app_main.rdb = BadRedis()
    try:
        assert app_main.cache_get("x") is None
        app_main.cache_set("x", "y", 1)
        app_main.cache_drop("tick1")
    finally:
        app_main.rdb = prev

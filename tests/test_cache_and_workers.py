import asyncio

import pytest

from app import main as app_main
from tests.helpers import login_token


def test_cache_works(client, monkeypatch):
    monkeypatch.setattr(app_main, "popular", 1)
    token = login_token(client, "cache_user")
    made = client.post(
        "/links/shorten",
        headers={"token": token},
        json={
            "original_url": "https://ru.wikipedia.org/wiki/Боуи,_Дэвид", "custom_alias": "cache-link"

            },
    ) # +rizz
    assert made.status_code == 200

    r1 = client.get("/links/cache-link", follow_redirects=False)
    assert r1.status_code == 307
    assert app_main.rdb.get("link:cache-link") is not None

    r2 = client.get("/links/cache-link", follow_redirects=False)
    assert r2.status_code == 307

    s1 = client.get("/links/cache-link/stats")
    assert s1.status_code == 200
    assert app_main.rdb.get("stats:cache-link") is not None

    s2 = client.get("/links/cache-link/stats")
    assert s2.status_code == 200
    assert s2.json()["short_code"] == "cache-link"


def test_stop_task(client):
    async def run_stop():
        async def sleeper():
            await asyncio.sleep(10)

        app_main.cleanup_task = asyncio.create_task(sleeper())
        await app_main.on_stop()

    asyncio.run(run_stop())


def test_worker_loop_stop(monkeypatch):
    monkeypatch.setattr(app_main,"expired_tick", lambda: ["abc"])
    monkeypatch.setattr(app_main, "expired_clean", lambda codes: None)

    async def stop_sleep(_):
        raise RuntimeError("stop-loop")

    monkeypatch.setattr(app_main.asyncio, "sleep", stop_sleep)

    with pytest.raises(RuntimeError):
        asyncio.run(app_main.cleanup_worker_loop())

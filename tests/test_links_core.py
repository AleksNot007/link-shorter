from tests.helpers import login_token


def test_shorten_redirect_and_stats(client):
    token = login_token(client, "bob", "pwd")
    resp = client.post(
        "/links/shorten",
        headers={"token": token},
        json={"original_url": "https://example.com/x", "custom_alias": "my-link"},
    )
    assert resp.status_code == 200
    assert resp.json()["short_code"] == "my-link"

    redirect = client.get("/links/my-link", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://example.com/x"

    stats = client.get("/links/my-link/stats")
    assert stats.status_code == 200
    assert stats.json()["clicks"] == 1


def test_search_update_delete_flow(client):
    token = login_token(client, "mike", "pwd")
    make = client.post(
        "/links/shorten",
        headers={"token": token},
        json={"original_url": "https://example.com/old"},
    )
    assert make.status_code == 200
    code = make.json()["short_code"]

    found = client.get("/links/search", params={"original_url": "https://example.com/old"})
    assert found.status_code == 200
    assert len(found.json()["items"]) == 1
    assert found.json()["items"][0]["short_code"] == code

    no_auth = client.put(f"/links/{code}", json={"original_url": "https://example.com/new"})
    assert no_auth.status_code == 401

    upd = client.put(
        f"/links/{code}",
        headers={"x-token": token},
        json={"original_url": "https://example.com/new"},
    )
    assert upd.status_code == 200

    delete = client.delete(f"/links/{code}", headers={"x-token": token})
    assert delete.status_code == 200

    after = client.get(f"/links/{code}/stats")
    assert after.status_code == 404


def test_bad_expires_at_format(client):
    resp = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/xx", "expires_at": "bad-format"},
    )
    assert resp.status_code == 400


def test_alias_with_spaces_is_rejected(client):
    token = login_token(client, "alias_user")
    bad = client.post(
        "/links/shorten",
        headers={"token": token},
         json={"original_url": "https://example.com/a", "custom_alias": "   "},
    )
    assert bad.status_code == 400


def test_duplicate_alias_is_rejected(client):
    token = login_token(client, "alias_user_2")
    first = client.post(
        "/links/shorten",
        headers={"token": token},
        json={"original_url":"https://example.com/a", "custom_alias": "same-alias"},
    )
    assert first.status_code == 200

    second = client.post(
        "/links/shorten",
        headers={"token": token},
        json={"original_url": "https://example.com/b", "custom_alias": "same-alias"},
    )
    assert second.status_code == 409


def test_owner_cannot_edit_foreign_link(client):
    owner = login_token(client, "owner_user")
    other = login_token(client, "other_user")

    made = client.post(
        "/links/shorten",
        headers={"token": owner},
        json={"original_url": "https://example.com/u"},
    )
    code = made.json()["short_code"]

    
    bad_token = client.put(
        f"/links/{code}",
        headers={"x-token": "not-valid"},
        json={"original_url": "https://example.com/new-u"},
    )
    assert bad_token.status_code == 401

    forbidden = client.put(
        f"/links/{code}",
        headers={"x-token": other},
        json={"original_url": "https://example.com/new-u"},
    )
    assert forbidden.status_code == 403

    missing = client.put(
        "/links/no-such-code",
        headers={"x-token": owner},
        json={"original_url": "https://example.com/new-u"},
    )
    assert missing.status_code == 404

    bad_token_del = client.delete(f"/links/{code}", headers = {"x-token": "not-valid"})
    assert bad_token_del.status_code == 401

    forbidden_del = client.delete(f"/links/{code}", headers={"x-token": other})
    assert forbidden_del.status_code == 403

    nf_del = client.delete("/links/no-such-code", headers={"x-token": owner})
    assert nf_del.status_code == 404

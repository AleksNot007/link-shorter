from tests.helpers import login_token



def test_register_and_login_returns_token(client):
    token = login_token(client, "aleksa")
    assert token


def test_register_rejects_duplicate_username(client):
    client.post("/register", json={"username": "aleksa", "password": "12345"})
    dup = client.post("/register", json={"username": "aleksa", "password": "12345"})
    assert dup.status_code == 400


def test_login_fails_for_wrong_password(client):
    client.post("/register", json={"username": "aleksa",
                                         "password": "12345"})
    bad = client.post("/login", json={"username": "aleksa", "password": "wrong"})
    assert bad.status_code == 401


def test_login_fails_for_unknown_user(client):
    resp = client.post("/login", json={"username": "ghost", "password": "x"})
    assert resp.status_code == 404

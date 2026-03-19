def login_token(client, username, password="12345"):
  #  password = password if password else "12345"
    reg = client.post("/register", json={"username": username, "password": password})
    assert reg.status_code == 200
    login = client.post("/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return login.json()["token"]

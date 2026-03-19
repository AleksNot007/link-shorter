import random
import string

from locust import HttpUser, between, task

TARGET_URLS = [
    "https://ru.wikipedia.org/wiki/Боуи,_Дэвид",
    "https://fastapi.tiangolo.com/tutorial/testing/#extended-testing-file",
    "https://fastapi.tiangolo.com/advanced/async-tests/",
    "https://locust.io/",
    "https://example.com/docs",
    "https://example.com/profile",
]


class ShortenerUser(HttpUser):
    wait_time = between(0.2, 1.2)

    def on_start(self):
        suffix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        self.username = "load_" + suffix
        self.password = "pass12345"
        self.token = None
        self.codes = []

        self.client.post("/register", json={"username": self.username, "password": self.password})
        login = self.client.post("/login", json={"username": self.username, "password": self.password})
        if login.status_code == 200:
            self.token = login.json().get("token")

    @task(4)
    def shorten(self):
        alias = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(7))
        payload = {"original_url": random.choice(TARGET_URLS)}
        headers = {}
        if self.token:
            headers["token"] = self.token

        if random.random() < 0.15:
            payload["custom_alias"] = f"u{alias.lower()}"

        response = self.client.post("/links/shorten", json=payload, headers=headers, name="/links/shorten")
        if response.status_code == 200:
            code = response.json().get("short_code")
            if code:
                self.codes.append(code)
                if len(self.codes) > 200:
                    self.codes.pop(0)

        
    @task(3)
    def redirect(self):
        if not self.codes: return
        code = random.choice(self.codes)
        self.client.get(f"/links/{code}", allow_redirects=False, name="/links/{code}")


    @task(2)
    def stats(self):
        if not self.codes:
            return
        code = random.choice(self.codes)
        self.client.get(f"/links/{code}/stats", name="/links/{code}/stats")

    @task(1)
    def search(self):
        url = random.choice(TARGET_URLS)
        self.client.get(
            "/links/search",
            params={"original_url": url},
            name="/links/search",
        )

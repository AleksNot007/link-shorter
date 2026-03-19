from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main as app_main
from app.models import Base


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value
        return True

    def delete(self, key):
        if key in self.data:
            del self.data[key]
            return 1
        
        return 0


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    db_file = tmp_path/"test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
  connect_args={"check_same_thread": False},
    )
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    fake_redis = FakeRedis()

    monkeypatch.setattr(app_main, "SessionLocal", test_session)
    monkeypatch.setattr(app_main, "rdb", fake_redis)
    monkeypatch.setattr(app_main, "log_file", str(tmp_path / "expired.log"))

    def fake_init_db():
        Base.metadata.create_all(bind=engine)

    async def fake_worker():
        return None

    class FakeRedisLib:
        class Redis:
            @staticmethod
            def from_url(*args, **kwargs):
                return fake_redis

    monkeypatch.setattr(app_main, "init_db", fake_init_db)
    monkeypatch.setattr(app_main, "cleanup_worker_loop", fake_worker)
    monkeypatch.setattr(app_main, "redis_lib", FakeRedisLib)

    with TestClient(app_main.app) as c:
        yield c

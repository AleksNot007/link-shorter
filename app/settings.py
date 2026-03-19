import os


db = os.getenv(
    "DB_DSN",
    "postgresql+psycopg2://postgres:postgres@db:5432/url_shorter",
)
redis = os.getenv("REDIS_URL", "redis://redis:6379/0")
days = int(os.getenv("DEFAULT_UNUSED_DAYS", "30"))
popular = int(os.getenv("POPULAR_HIT_BORDER", "5"))
sweep = int(os.getenv("EXPIRED_SWEEP_SECONDS", "60"))
base = os.getenv("BASE_URL", "http://localhost:8000")
log_file = os.getenv("EXPIRED_ACCESS_LOG_PATH", "/tmp/acces.log")

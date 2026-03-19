from app.settings import db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(db, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    from app.models import Base

    Base.metadata.create_all(bind=engine)


def get_db():
    local_db = SessionLocal()
    try:
        yield local_db
    finally:
        local_db.close()

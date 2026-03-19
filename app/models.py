from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    token = Column(String, nullable=True)


class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True)
    short_code = Column(String, unique=True, nullable=False)
    original_url = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    clicks = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime, nullable=True)


class ExpiredLink(Base):
    __tablename__ = "expired_links"
    id = Column(Integer, primary_key=True)
    short_code = Column(String, nullable=False)
    original_url = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=False)
    clicks = Column(Integer, nullable=False, default=0)

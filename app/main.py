import asyncio
import json
import random
import string
import uuid
from datetime import datetime, timedelta

import redis as redis_lib
from app.db import SessionLocal, init_db
from app.models import ExpiredLink, Link, User
from app.schemas import LoginReq, RegisterReq, ShortenReq, UpdateReq
from app.settings import base, days, log_file, popular, redis, sweep
from fastapi import FastAPI, Header, Query
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

app = FastAPI()

rdb = None
expired_buffer = []
cleanup_task = None


def move_link_to_expired(db: Session, link_obj: Link):
    item = ExpiredLink(
        short_code=link_obj.short_code,
        original_url=link_obj.original_url,
        created_at=link_obj.created_at,
        expired_at=datetime.utcnow(),
        clicks=link_obj.clicks,
    )
    db.add(item)
    db.delete(link_obj)


def expired_clean(codes):
    global expired_buffer

    for i in range(len(codes)):
        expired_buffer.append(codes[i])
        if len(expired_buffer) > 1000:
            expired_buffer.pop(0)
        cache_drop(codes[i])


def expired_tick():
    db = SessionLocal()
    now = datetime.utcnow()
    removed = []
    try:
        q = db.query(Link)
        notnone = Link.expires_at.isnot(None)
        lessnow = Link.expires_at <= now

        items = q.filter(notnone, lessnow).all()
        # print("expired_tick rows:", len(items))
        for i in range(len(items)):
            removed.append(items[i].short_code)
            move_link_to_expired(db, items[i])

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    return removed


async def cleanup_worker_loop():
    while True:
        codes = expired_tick()
        if len(codes) > 0:
            expired_clean(codes)
        await asyncio.sleep(sweep)


def user_by_token(db: Session, token: str | None):
    if token is None:
        return None
    return db.query(User).filter(
        User.token == token
    ).first()


def link_by_code(db: Session, short_code: str):
    links_db = db.query(Link)
    return links_db.filter(
        Link.short_code == short_code).first()


def old_rows(db: Session, border):
    q = db.query(Link)
    all_rows = q.all()
    out = []
    for i in range(len(all_rows)):
        row = all_rows[i]
        if row.last_used_at is None:
            if row.created_at < border:
                out.append(row)
        else:
            if row.last_used_at < border:
                out.append(row)
    return out


def cache_get(key: str):
    try:
        return rdb.get(key)
    except Exception:
        return None


def cache_set(key: str, val: str, ttl: int):
    try:
        rdb.set(key, val, ex=ttl)
    except Exception:
        pass


def cache_drop(short_code: str):
    try:
        rdb.delete("link:" + short_code)
        rdb.delete("stats:" + short_code)
    except Exception:
        pass


@app.on_event("startup")
async def on_start():
    global rdb, cleanup_task
    init_db()
    rdb = redis_lib.Redis.from_url(redis, decode_responses=True)
    cleanup_task = asyncio.create_task(cleanup_worker_loop())


@app.on_event("shutdown")
async def on_stop():
    global cleanup_task
    if cleanup_task is not None:
        cleanup_task.cancel()

        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


@app.post("/register")
def register(body: RegisterReq):
    db = SessionLocal()
    try:
        user_db = db.query(User)
        existed = user_db.filter(User.username == body.username).first()
        if existed is not None:
            raise HTTPException(status_code=400, detail="user exists")
        db.add(User(username=body.username, password=body.password))
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()


@app.post("/login")
def login(body: LoginReq):
    db = SessionLocal()
    try:
        user_db = db.query(User)
        user = user_db.filter(
            User.username == body.username).first()
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")
        if user.password != body.password:
            raise HTTPException(status_code=401, detail="bad password")
        user.token = str(uuid.uuid4())
        db.commit()
        return {"token": user.token}
    finally:
        db.close()


@app.post("/links/shorten")
def shorten(data: ShortenReq, token=Header(None)):
    db = SessionLocal()
    try:
        uid = None
        user = user_by_token(db, token)
        if user is not None:
            uid = user.id

        exp = None
        if data.expires_at:
            try:
                exp = datetime.strptime(data.expires_at, "%Y-%m-%d %H:%M")
            except Exception:
                raise HTTPException(status_code=400, detail="bad expires_at")

        short_code = ""
        if data.custom_alias:
            short_code = data.custom_alias.strip()
            if short_code == "":
                raise HTTPException(status_code=400, detail="empty alias")
            link_db = db.query(Link)
            hit = link_db.filter(Link.short_code == short_code).first()
            if hit is not None:
                raise HTTPException(status_code=409, detail="alias exists")
        else:
            chars = string.ascii_letters + string.digits
            tries = 0
            while True:
                tries += 1
                tmp = []
                for i in range(7):
                    tmp.append(random.choice(chars))
                short_code = "".join(tmp)
                hit = db.query(Link).filter(
                    Link.short_code == short_code).first()
                if hit is None:
                    break
                if tries > 30:
                    # print("too many tries for short code")
                    raise HTTPException(status_code=500, detail="cannot generate code")

        obj = Link(
            short_code=short_code,
            original_url=data.original_url,
            created_at=datetime.utcnow(),
            user_id=uid,
            expires_at=exp,
        )
        db.add(obj)
        db.commit()
        return {"short_code": short_code, "short_url": f"{base}/links/{short_code}"}
    finally:
        db.close()


@app.get("/links/search")
def search(original_url: str = Query(...)):
    db = SessionLocal()
    try:
        links_db = db.query(Link)
        rows = links_db.filter(Link.original_url == original_url).order_by(desc(Link.id)).all()
        data = []
        for i in range(len(rows)):
            data.append(
                {
                    "short_code": rows[i].short_code,
                    "created_at": str(rows[i].created_at),
                    "clicks": rows[i].clicks,
                    "last_used_at": str(rows[i].last_used_at) if rows[i].last_used_at else None,
                    "expires_at": str(rows[i].expires_at) if rows[i].expires_at else None,
                }
            )
        return {"items": data}
    finally:
        db.close()


@app.get("/links/{short_code}")
def redirect(short_code: str):
    # что-то может быть сохранено в кэше
    key = "link:" + short_code
    cached = cache_get(key)
    # print("redirect code:", short_code, "cache:", bool(cached))

    db = SessionLocal()
    try:
        if cached:
            obj = json.loads(cached)
            exp = obj.get("expires_at")
            if exp:
                try:
                    dt = datetime.fromisoformat(exp)
                    if datetime.utcnow() >= dt:
                        link_obj = link_by_code(db, short_code)
                        if link_obj is not None:
                            move_link_to_expired(db, link_obj)
                            db.commit()
                        cache_drop(short_code)
                        raise HTTPException(status_code=404, detail="expired")
                except ValueError:
                    pass
            link_row = link_by_code(db, short_code)
            if link_row is not None:
                link_row.clicks = link_row.clicks + 1
                link_row.last_used_at = datetime.utcnow()
                db.commit()
            return RedirectResponse(url=obj["original_url"], status_code=307)

        row = link_by_code(db, short_code)
        if row is None:
            raise HTTPException(status_code=404, detail="not found")

        if row.expires_at is not None and datetime.utcnow() >= row.expires_at:
            move_link_to_expired(db, row)
            db.commit()
            cache_drop(short_code)
            raise HTTPException(status_code=404, detail="expired")

        row.clicks = row.clicks + 1
        row.last_used_at = datetime.utcnow()
        db.commit()
        click_now = row.clicks
        original_url_value = row.original_url
        expires_at_value = row.expires_at.isoformat() if row.expires_at else None
        payload = {"original_url": original_url_value, "expires_at": expires_at_value}
        if click_now >= popular:
            cache_set(key, json.dumps(payload), 300)
        return RedirectResponse(url=row.original_url, status_code=307)
    finally:
        db.close()


@app.get("/links/{short_code}/stats")
def stats(short_code: str):
    skey = "stats:" + short_code
    got = cache_get(skey)
    if got:
        return json.loads(got)

    db = SessionLocal()
    try:
        row = link_by_code(db, short_code)
        if row is None:
            raise HTTPException(status_code=404, detail="not found")
        data = {
            "short_code": short_code,
            "original_url": row.original_url,
            "created_at": str(row.created_at),
            "clicks": row.clicks,
            "last_used_at": str(row.last_used_at) if row.last_used_at else None,
        }
        if row.clicks >= popular:
            cache_set(skey, json.dumps(data), 120)
        return data
    finally:
        db.close()


@app.put("/links/{short_code}")
def update_link(short_code: str, body: UpdateReq, x_token: str | None = Header(default=None)):
    if x_token is None:
        raise HTTPException(status_code=401, detail="auth required")
    db = SessionLocal()
    try:
        user = user_by_token(db, x_token)
        if user is None:
            raise HTTPException(status_code=401, detail="bad token")
        link = link_by_code(db, short_code)
        if link is None:
            raise HTTPException(status_code=404, detail="not found")
        if link.user_id is None or link.user_id != user.id:
            raise HTTPException(status_code=403, detail="forbidden")
        link.original_url = body.original_url
        db.commit()
        cache_drop(short_code)
        return {"status": "updated"}
    finally:
        db.close()


@app.delete("/links/{short_code}")
def delete_link(short_code: str, x_token: str | None = Header(default=None)):
    if x_token is None:
        raise HTTPException(status_code=401, detail="auth required")
    db = SessionLocal()
    try:
        user = user_by_token(db, x_token)
        if user is None:
            raise HTTPException(status_code=401, detail="bad token")
        link = link_by_code(db, short_code)
        if link is None:
            raise HTTPException(status_code=404, detail="not found")
        if link.user_id is None or link.user_id != user.id:
            raise HTTPException(status_code=403, detail="forbidden")
        db.delete(link)
        db.commit()
        cache_drop(short_code)
        return {"status": "deleted"}
    finally:
        db.close()


@app.post("/admin/cleanup-unused")
def cleanup_unused(days: int = Query(days)):
    # чистим старые линкы пачкой, логика местами дублит код
    border = datetime.utcnow() - timedelta(days=days)
    db = SessionLocal()
    try:
        rows = old_rows(db, border)
        # print("cleanup rows:", len(rows))
        for i in range(len(rows)):
            code = rows[i].short_code
            move_link_to_expired(db, rows[i])
            expired_buffer.append(code)
            if len(expired_buffer) > 1000:
                expired_buffer.pop(0)
            cache_drop(code)
        db.commit()
        return {"removed": len(rows), "days": days}
    finally:
        db.close()


@app.get("/links/expired-history")
def expired_history(limit: int = Query(50)):
    data = []
    # тут пока оставлено по-простому, без with
    f = open(log_file, "a+")
    try:
        f.write("request " + str(datetime.utcnow()) + "\n")
    except Exception:
        pass

    db = SessionLocal()
    try:
        rows = db.query(ExpiredLink).order_by(desc(ExpiredLink.id)).limit(limit).all()
        for i in range(len(rows)):
            item = {
                "short_code": rows[i].short_code,
                "original_url": rows[i].original_url,
                "created_at": str(rows[i].created_at) if rows[i].created_at else None,
                "expired_at": str(rows[i].expired_at) if rows[i].expired_at else None,
                "clicks": rows[i].clicks,
            }
            data.append(item)
        if len(expired_buffer) > 0:
            tmp = []
            for j in range(len(expired_buffer)):
                tmp.append(expired_buffer[j])
            data.append({"recent_removed_from_memory": tmp})
        return {"items": data}
    finally:
        db.close()

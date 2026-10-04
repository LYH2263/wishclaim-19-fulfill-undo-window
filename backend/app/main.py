from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app import seed
from app.db import connect
from app.engines.claim_lock import claim_allowed, lock_payload, release_if_expired
from app.engines.undo_window import project_wish, undo_allowed, undo_payload

app = FastAPI(title="Wishclaim", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _startup(): seed.init_db()

def now(): return datetime.now(timezone.utc)

def setting(key, default):
    c = connect(); row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone(); c.close()
    return row["value"] if row else default

def ttl(): return int(setting("ttl_seconds", 86400))
def undo_seconds(): return int(setting("undo_seconds", 300))

def sweep(c):
    for r in c.execute("SELECT * FROM wishes WHERE status='claimed'"):
        rel = release_if_expired(r["status"], r["expires_at"], now())
        if rel:
            c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=? WHERE id=?",
                      (rel["status"], None, None, None, r["id"]))

def project(rows):
    u = undo_seconds(); t = now()
    return [project_wish(dict(r), t, u) for r in rows]

@app.get("/api/health")
def health(): return {"ok": True, "project": "wishclaim"}

@app.get("/api/wishes")
def list_wishes():
    c = connect(); sweep(c); c.commit()
    rows = c.execute("SELECT * FROM wishes ORDER BY id DESC").fetchall(); c.close()
    return project(rows)

@app.get("/api/wishes/{wid}")
def get_wish(wid: int):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone(); c.close()
    if not r: raise HTTPException(404, "not found")
    return project([r])[0]

class WishIn(BaseModel):
    title: str
    note: str = ""

@app.post("/api/wishes")
def create_wish(body: WishIn):
    c = connect()
    cur = c.execute("INSERT INTO wishes(title,note,status,data_quality) VALUES (?,?,?,?)",
                    (body.title, body.note, "open", "clean"))
    c.commit(); wid = cur.lastrowid; c.close(); return {"id": wid}

class ClaimIn(BaseModel):
    claimer: str

@app.post("/api/wishes/{wid}/claim")
def claim(wid: int, body: ClaimIn):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    allowed = claim_allowed(r["status"], r["claimer"], now(), r["expires_at"])
    if not allowed["ok"]:
        c.close(); raise HTTPException(409, allowed["reason"])
    p = lock_payload(body.claimer, now(), ttl())
    c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=? WHERE id=?",
              (p["status"], p["claimer"], p["claimed_at"], p["expires_at"], wid))
    c.commit(); c.close(); return p

@app.post("/api/wishes/{wid}/release")
def release(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "not_claimed")
    c.execute("UPDATE wishes SET status='released', claimer=NULL, claimed_at=NULL, expires_at=NULL WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "released"}

class FulfillIn(BaseModel):
    evidence: str = ""

@app.post("/api/wishes/{wid}/fulfill")
def fulfill(wid: int, body: FulfillIn | None = None):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "need_claim")
    ev = (body.evidence if body else "").strip()
    c.execute("UPDATE wishes SET status='fulfilled', fulfilled_at=?, evidence=? WHERE id=?",
              (now().isoformat(), ev or None, wid))
    c.commit(); c.close(); return {"ok": True, "status": "fulfilled"}

@app.post("/api/wishes/{wid}/undo")
def undo(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    gate = undo_allowed(r["status"], r["fulfilled_at"], now(), undo_seconds())
    if not gate["ok"]:
        c.close(); raise HTTPException(409, gate["reason"])
    p = undo_payload()
    c.execute("UPDATE wishes SET status=?, fulfilled_at=?, evidence=? WHERE id=?",
              (p["status"], p["fulfilled_at"], p["evidence"], wid))
    c.commit(); c.close(); return {"ok": True, **p}

@app.get("/api/mine")
def mine(claimer: str):
    c = connect(); sweep(c); c.commit()
    rows = c.execute("SELECT * FROM wishes WHERE claimer=?", (claimer,)).fetchall(); c.close()
    return project(rows)

@app.get("/api/done")
def done():
    c = connect()
    rows = c.execute("SELECT * FROM wishes WHERE status='fulfilled'").fetchall(); c.close()
    return project(rows)

@app.get("/api/settings")
def settings():
    c = connect(); rows = {r["key"]: r["value"] for r in c.execute("SELECT * FROM settings")}; c.close(); return rows

@app.get("/api/rules")
def rules():
    return {
        "mutex": "同一愿望同时只能被一人认领",
        "ttl": "认领超时未核销则自动释放",
        "fulfill": "核销后状态变为 fulfilled",
        "undo": "核销后 undo_seconds 内可撤销回认领中, 窗外不可撤销",
        "undo_evidence": "撤销即清空举证快照, 再次核销需重新举证",
        "undo_ttl": "撤销后 TTL 继承核销前剩余, 不重开满额",
    }

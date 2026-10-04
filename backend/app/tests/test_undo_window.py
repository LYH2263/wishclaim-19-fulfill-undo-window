from datetime import datetime, timedelta, timezone
from app.engines.undo_window import undo_allowed, undo_payload, project_wish

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
UNDO = 300

def test_undo_requires_fulfilled():
    for st in ("open", "claimed", "released"):
        r = undo_allowed(st, NOW.isoformat(), NOW, UNDO)
        assert r["ok"] is False and r["reason"] == "not_fulfilled"

def test_undo_within_window():
    fa = (NOW - timedelta(seconds=120)).isoformat()
    assert undo_allowed("fulfilled", fa, NOW, UNDO)["ok"] is True

def test_undo_outside_window_fails():
    fa = (NOW - timedelta(seconds=301)).isoformat()
    r = undo_allowed("fulfilled", fa, NOW, UNDO)
    assert r["ok"] is False and r["reason"] == "undo_window_expired"

def test_undo_boundary_is_closed():
    fa = (NOW - timedelta(seconds=UNDO)).isoformat()
    assert undo_allowed("fulfilled", fa, NOW, UNDO)["ok"] is False

def test_undo_missing_fulfilled_at():
    r = undo_allowed("fulfilled", None, NOW, UNDO)
    assert r["ok"] is False and r["reason"] == "missing_fulfilled_at"

def test_undo_payload_clears_evidence_keeps_ttl():
    p = undo_payload()
    assert p["status"] == "claimed" and p["fulfilled_at"] is None and p["evidence"] is None
    assert "expires_at" not in p and "claimed_at" not in p  # 拍板2: 继承核销前剩余, 不回写

def test_projection_pins_undo_window():
    w = {"status": "fulfilled", "fulfilled_at": (NOW - timedelta(seconds=60)).isoformat(),
         "expires_at": None}
    p = project_wish(w, NOW, UNDO)
    assert p["undoable"] is True and p["undo_remaining_seconds"] == 240
    assert p["countdown_seconds"] is None
    p2 = project_wish({**w, "fulfilled_at": (NOW - timedelta(seconds=600)).isoformat()}, NOW, UNDO)
    assert p2["undoable"] is False and p2["undo_remaining_seconds"] < 0
    p3 = project_wish({**w, "fulfilled_at": None}, NOW, UNDO)
    assert p3["undoable"] is False and p3["undo_remaining_seconds"] is None

def test_projection_countdown_for_claimed():
    exp = (NOW + timedelta(seconds=90)).isoformat()
    p = project_wish({"status": "claimed", "expires_at": exp, "fulfilled_at": None}, NOW, UNDO)
    assert p["countdown_seconds"] == 90 and p["undoable"] is False
    p2 = project_wish({"status": "open", "expires_at": None, "fulfilled_at": None}, NOW, UNDO)
    assert p2["countdown_seconds"] is None and p2["undo_remaining_seconds"] is None

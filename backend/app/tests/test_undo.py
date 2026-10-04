from datetime import datetime, timedelta, timezone
from app.engines.undo_gate import undo_allowed
from app.engines.undo_writeback import undo_writeback
from app.modules.claim_projection import project_wish

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
F_AT = (NOW - timedelta(minutes=10)).isoformat()
UNDO = 3600

def test_undo_gate_rejects_non_fulfilled():
    assert undo_allowed("claimed", None, NOW, UNDO)["reason"] == "not_fulfilled"
    assert undo_allowed("open", None, NOW, UNDO)["ok"] is False
    assert undo_allowed("fulfilled", None, NOW, UNDO)["reason"] == "not_fulfilled"

def test_undo_gate_window():
    assert undo_allowed("fulfilled", F_AT, NOW, UNDO)["ok"] is True
    assert undo_allowed("fulfilled", (NOW - timedelta(hours=2)).isoformat(), NOW, UNDO)["reason"] == "window_expired"

def test_writeback_inherits_remaining_and_clears_proof():
    exp = (NOW + timedelta(minutes=50)).isoformat()  # fulfilled_at 时刻还剩 60min
    p = undo_writeback(NOW, F_AT, exp)
    assert p["status"] == "claimed"
    assert p["proof"] is None and p["fulfilled_at"] is None
    assert p["expires_at"] == (NOW + timedelta(minutes=60)).isoformat()

def test_writeback_clamps_negative_remaining():
    exp = (NOW - timedelta(minutes=15)).isoformat()  # fulfilled_at 前 5min 已过期
    p = undo_writeback(NOW, F_AT, exp)
    assert p["expires_at"] == NOW.isoformat()

def test_projection_pins_countdown_and_undo():
    c = project_wish({"status": "claimed", "expires_at": (NOW + timedelta(seconds=90)).isoformat()}, NOW, UNDO)
    assert c["remaining_seconds"] == 90 and c["can_undo"] is False
    f = project_wish({"status": "fulfilled", "fulfilled_at": F_AT}, NOW, UNDO)
    assert f["can_undo"] is True and f["undo_remaining_seconds"] == 3000
    g = project_wish({"status": "fulfilled", "fulfilled_at": (NOW - timedelta(hours=2)).isoformat()}, NOW, UNDO)
    assert g["can_undo"] is False and g["undo_remaining_seconds"] == 0

"""Fulfill undo window: gating, state writeback, projection.

拍板 1 — 举证快照: 撤销即清空。撤销 = 完整回滚本次核销事件,
举证是对那一次核销的证明, 再次核销必须重新举证。
拍板 2 — TTL: 继承核销前剩余。claimed_at/expires_at 原地保留,
不重开满额, 杜绝 fulfill→undo 循环续锁。
"""
from datetime import datetime, timedelta

from app.engines.claim_lock import parse_ts


def undo_deadline(fulfilled_at: str, undo_seconds: int) -> datetime:
    return parse_ts(fulfilled_at) + timedelta(seconds=undo_seconds)


def undo_allowed(status: str, fulfilled_at: str | None, now: datetime, undo_seconds: int) -> dict:
    """门禁: 仅 fulfilled 且在撤销窗内可撤销。"""
    if status != "fulfilled":
        return {"ok": False, "reason": "not_fulfilled"}
    if not fulfilled_at:
        return {"ok": False, "reason": "missing_fulfilled_at"}
    if now >= undo_deadline(fulfilled_at, undo_seconds):
        return {"ok": False, "reason": "undo_window_expired"}
    return {"ok": True, "reason": ""}


def undo_payload() -> dict:
    """状态回写: 回到 claimed; 举证快照清空(拍板1)。
    claimed_at/expires_at 不在回写载荷里 —— 原地保留, 继承核销前剩余 TTL(拍板2)。"""
    return {"status": "claimed", "fulfilled_at": None, "evidence": None}


def project_wish(w: dict, now: datetime, undo_seconds: int) -> dict:
    """投影: 列表/详情/我的认领/已完成共用同一份派生视图(同钉)。"""
    p = dict(w)
    exp = w.get("expires_at")
    if w.get("status") == "claimed" and exp:
        p["countdown_seconds"] = int((parse_ts(exp) - now).total_seconds())
    else:
        p["countdown_seconds"] = None
    fa = w.get("fulfilled_at")
    if w.get("status") == "fulfilled" and fa:
        rem = int((undo_deadline(fa, undo_seconds) - now).total_seconds())
        p["undo_remaining_seconds"] = rem
        p["undoable"] = rem > 0
    else:
        p["undo_remaining_seconds"] = None
        p["undoable"] = False
    return p

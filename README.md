# Wishclaim · 礼物愿望认领

发布 → 认领锁定（互斥+TTL）→ 核销/释放 → 撤销窗内可撤销核销。

## 核销撤销窗

核销（fulfill）后 `undo_seconds`（默认 300，见 settings）内可 `POST /api/wishes/{id}/undo`
撤销回 `claimed`；窗外与非 fulfilled 状态撤销均失败（409）。
撤销后自动移出已完成页，墙/详情/我的认领经同一投影（`project_wish`）同钉。

两处拍板（`backend/app/engines/undo_window.py`）：

1. **举证快照：撤销即清空** —— 撤销 = 完整回滚本次核销，再次核销须重新举证。
2. **TTL：继承核销前剩余** —— `claimed_at`/`expires_at` 原地保留，不重开满额，
   杜绝 fulfill→undo 循环续锁。

实现分三模块：撤销门禁 `undo_allowed` / 状态回写 `undo_payload` / 投影 `project_wish`。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5200 |
| API | 10200 |

```bash
docker compose up --build
pytest backend/app/tests
```

0-1：`wish_comment` / `secret_santa` / `price_cap`。

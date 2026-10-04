from app.db import connect

WISH_COLUMNS = (
    "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, note TEXT, status TEXT,"
    " claimer TEXT, claimed_at TEXT, expires_at TEXT, data_quality TEXT,"
    " fulfilled_at TEXT, evidence TEXT"
)

DEFAULT_SETTINGS = {
    "ttl_seconds": "86400",
    "undo_seconds": "300",
    "wall_title": "暖粉愿望墙",
}

def migrate(c):
    cols = {r["name"] for r in c.execute("PRAGMA table_info(wishes)")}
    for col in ("fulfilled_at", "evidence"):
        if col not in cols:
            c.execute(f"ALTER TABLE wishes ADD COLUMN {col} TEXT")

def init_db():
    c = connect()
    c.executescript(f"""
    CREATE TABLE IF NOT EXISTS wishes({WISH_COLUMNS});
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    """)
    migrate(c)
    if c.execute("SELECT COUNT(*) c FROM wishes").fetchone()["c"] == 0:
        c.executemany(
            "INSERT INTO wishes(title,note,status,claimer,claimed_at,expires_at,data_quality,fulfilled_at,evidence) VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("机械键盘", "红轴", "open", None, None, None, "clean", None, None),
                ("围巾", "羊毛", "open", None, None, None, "clean", None, None),
                ("脏愿望-空标题", "", "open", None, None, None, "dirty", None, None),
                ("过期锁样例", "应被TTL释放", "claimed", "ghost", "2020-01-01T00:00:00+00:00",
                 "2020-01-01T01:00:00+00:00", "dirty", None, None),
                ("窗外核销样例", "撤销窗早已关闭", "fulfilled", "ghost", "2020-01-01T00:00:00+00:00",
                 "2020-01-01T01:00:00+00:00", "dirty", "2020-01-01T00:30:00+00:00", "签收照片.jpg"),
            ],
        )
    for k, v in DEFAULT_SETTINGS.items():
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)", (k, v))
    c.commit()
    c.close()

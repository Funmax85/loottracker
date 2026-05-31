"""SQLite persistence: tracks active vs. expired deals so stale data is hidden."""
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS deals (
    id            TEXT PRIMARY KEY,      -- stable hash of source+native id
    source        TEXT NOT NULL,         -- gamerpower | cheapshark | reddit
    title         TEXT NOT NULL,
    platform      TEXT NOT NULL,         -- steam | playstation | xbox
    deal_type     TEXT NOT NULL,         -- free | discount
    discount      INTEGER,               -- percent off (100 for free)
    price         TEXT,                  -- e.g. "$4.99" or "FREE"
    worth         TEXT,                  -- original/retail value
    image         TEXT,
    claim_url     TEXT NOT NULL,
    expiry        TEXT,                  -- ISO date or NULL
    status        TEXT NOT NULL DEFAULT 'active',  -- active | expired
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_status   ON deals(status);
CREATE INDEX IF NOT EXISTS idx_platform ON deals(platform);
CREATE INDEX IF NOT EXISTS idx_type     ON deals(deal_type);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_deals(deals: list[dict]) -> int:
    """Insert new deals / refresh last_seen on existing ones. Returns count touched."""
    now = _now()
    touched = 0
    with get_conn() as conn:
        for d in deals:
            row = conn.execute("SELECT id FROM deals WHERE id = ?", (d["id"],)).fetchone()
            if row:
                conn.execute(
                    """UPDATE deals SET last_seen=?, status='active', title=?, platform=?,
                       deal_type=?, discount=?, price=?, worth=?, image=?, claim_url=?, expiry=?
                       WHERE id=?""",
                    (now, d["title"], d["platform"], d["deal_type"], d.get("discount"),
                     d.get("price"), d.get("worth"), d.get("image"), d["claim_url"],
                     d.get("expiry"), d["id"]),
                )
            else:
                conn.execute(
                    """INSERT INTO deals (id, source, title, platform, deal_type, discount,
                       price, worth, image, claim_url, expiry, status, first_seen, last_seen)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?, 'active', ?, ?)""",
                    (d["id"], d["source"], d["title"], d["platform"], d["deal_type"],
                     d.get("discount"), d.get("price"), d.get("worth"), d.get("image"),
                     d["claim_url"], d.get("expiry"), now, now),
                )
            touched += 1
    return touched


def expire_stale(seen_ids: set[str]):
    """Mark any active deal NOT in the latest fetch as expired (it dropped off the source)."""
    with get_conn() as conn:
        rows = conn.execute("SELECT id FROM deals WHERE status='active'").fetchall()
        stale = [r["id"] for r in rows if r["id"] not in seen_ids]
        for sid in stale:
            conn.execute("UPDATE deals SET status='expired' WHERE id=?", (sid,))
        return len(stale)


def query_deals(platform=None, deal_type=None, min_discount=None, limit=300) -> list[dict]:
    sql = "SELECT * FROM deals WHERE status='active'"
    params = []
    if platform and platform != "all":
        sql += " AND platform = ?"; params.append(platform)
    if deal_type:
        sql += " AND deal_type = ?"; params.append(deal_type)
    if min_discount is not None:
        sql += " AND discount >= ?"; params.append(min_discount)
    sql += " ORDER BY discount DESC, last_seen DESC LIMIT ?"; params.append(limit)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def stats() -> dict:
    with get_conn() as conn:
        active = conn.execute("SELECT COUNT(*) c FROM deals WHERE status='active'").fetchone()["c"]
        free = conn.execute("SELECT COUNT(*) c FROM deals WHERE status='active' AND deal_type='free'").fetchone()["c"]
        disc = conn.execute("SELECT COUNT(*) c FROM deals WHERE status='active' AND deal_type='discount'").fetchone()["c"]
        return {"active": active, "free": free, "discount": disc}

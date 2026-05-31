"""LootTracker FastAPI backend — endpoints, background refresh, static frontend serving."""
import threading
import time

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import database as db
import scrapers
from config import REFRESH_INTERVAL_MINUTES, DEEP_DISCOUNT_THRESHOLD

app = FastAPI(title="LootTracker API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_last_refresh = {"ts": None, "count": 0, "expired": 0}


def refresh_now() -> dict:
    deals = scrapers.fetch_all()
    seen_ids = {d["id"] for d in deals}
    touched = db.upsert_deals(deals)
    expired = db.expire_stale(seen_ids) if seen_ids else 0
    _last_refresh.update(ts=time.strftime("%Y-%m-%d %H:%M:%S"), count=touched, expired=expired)
    return _last_refresh


def _background_loop():
    while True:
        try:
            refresh_now()
        except Exception as e:
            print(f"[refresh] error: {e}")
        time.sleep(REFRESH_INTERVAL_MINUTES * 60)


@app.on_event("startup")
def startup():
    db.init_db()
    threading.Thread(target=_background_loop, daemon=True).start()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.get("/api/deals")
def get_deals(
    platform: str = Query("all", pattern="^(all|steam|playstation|xbox)$"),
    filter: str = Query("all", pattern="^(all|free|deep)$"),
):
    deal_type = None
    min_discount = None
    if filter == "free":
        deal_type = "free"
    elif filter == "deep":
        deal_type = "discount"
        min_discount = DEEP_DISCOUNT_THRESHOLD
    rows = db.query_deals(platform=platform, deal_type=deal_type, min_discount=min_discount)
    return {"count": len(rows), "deals": rows}


@app.get("/api/stats")
def get_stats():
    return {**db.stats(), "last_refresh": _last_refresh}


@app.post("/api/refresh")
def manual_refresh():
    return refresh_now()


# ---------------------------------------------------------------------------
# Serve frontend
# ---------------------------------------------------------------------------
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND = os.path.normpath(os.path.join(_HERE, "..", "frontend"))


@app.get("/")
def index():
    return FileResponse(os.path.join(_FRONTEND, "index.html"))


@app.get("/sw.js")
def service_worker():
    # Served from root so its scope covers the whole app ('/').
    return FileResponse(
        os.path.join(_FRONTEND, "sw.js"),
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@app.get("/manifest.json")
def manifest():
    return FileResponse(os.path.join(_FRONTEND, "manifest.json"), media_type="application/manifest+json")


try:
    app.mount("/static", StaticFiles(directory=_FRONTEND), name="static")
except Exception:
    pass

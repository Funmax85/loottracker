"""Scrapers/aggregators for GamerPower, CheapShark, and Reddit deal feeds.

Every record passes through validation.passes_all_checks before being returned.
NOTHING here generates, guesses, or brute-forces codes — it only aggregates real,
published deals from public APIs/feeds.
"""
import re
import hashlib
import requests

from config import (
    GAMERPOWER_API, CHEAPSHARK_DEALS_API, CHEAPSHARK_STORES_API,
    REDDIT_FEEDS, USER_AGENT, PLATFORM_MAP, ACCEPTED_FLAIR_REGEX,
    DEEP_DISCOUNT_THRESHOLD,
)
from validation import passes_all_checks

_HEADERS = {"User-Agent": USER_AGENT}
_FLAIR_RE = re.compile(ACCEPTED_FLAIR_REGEX, re.IGNORECASE)
# Catch "(85%)" / "85% off" / "-85%" inside Reddit titles.
_PCT_RE = re.compile(r"(\d{1,3})\s*%")


def _hid(*parts) -> str:
    return hashlib.sha1("::".join(str(p) for p in parts).encode()).hexdigest()[:16]


def _norm_platform(raw: str) -> str | None:
    raw = (raw or "").lower()
    for key, val in PLATFORM_MAP.items():
        if key in raw:
            return val
    return None


# ---------------------------------------------------------------------------
# 1) GamerPower — 100%-off giveaways, beta keys, in-game loot
# ---------------------------------------------------------------------------
def fetch_gamerpower() -> list[dict]:
    out = []
    for plat_param, norm in (("pc", "steam"), ("ps4", "playstation"),
                             ("ps5", "playstation"), ("xbox-one", "xbox"),
                             ("xbox-series-xs", "xbox"), ("epic-games-store", "steam")):
        try:
            r = requests.get(GAMERPOWER_API, params={"platform": plat_param, "type": "game.loot"},
                             headers=_HEADERS, timeout=20)
            # GamerPower returns a JSON array, or {"status":...} on empty.
            data = r.json()
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for g in data:
            title = g.get("title", "")
            url = g.get("open_giveaway_url") or g.get("gamerpower_url") or ""
            status = g.get("status")
            ok, _ = passes_all_checks(title, url, "gamerpower", status)
            if not ok:
                continue
            out.append({
                "id": _hid("gamerpower", g.get("id")),
                "source": "gamerpower",
                "title": title,
                "platform": norm,
                "deal_type": "free",
                "discount": 100,
                "price": "FREE",
                "worth": g.get("worth") if g.get("worth") not in (None, "N/A") else None,
                "image": g.get("image") or g.get("thumbnail"),
                "claim_url": url,
                "expiry": _parse_gp_expiry(g.get("end_date")),
            })
    return out


def _parse_gp_expiry(raw):
    if not raw or raw == "N/A":
        return None
    return raw.split(" ")[0]  # "2025-06-01 23:59:00" -> "2025-06-01"


# ---------------------------------------------------------------------------
# 2) CheapShark — deep historical price drops on Steam games
# ---------------------------------------------------------------------------
def fetch_cheapshark(min_savings: int = DEEP_DISCOUNT_THRESHOLD) -> list[dict]:
    out = []
    try:
        stores = {s["storeID"]: s for s in requests.get(
            CHEAPSHARK_STORES_API, headers=_HEADERS, timeout=20).json()}
    except Exception:
        stores = {}
    # storeID 1 = Steam. Pull the deepest discounts.
    try:
        deals = requests.get(CHEAPSHARK_DEALS_API, headers=_HEADERS, timeout=20, params={
            "storeID": 1, "sortBy": "Savings", "pageSize": 60, "upperPrice": 50,
        }).json()
    except Exception:
        return out
    for d in deals if isinstance(deals, list) else []:
        savings = round(float(d.get("savings", 0)))
        if savings < min_savings:
            continue
        title = d.get("title", "")
        # CheapShark redirect resolves to the Steam store page.
        url = f"https://store.steampowered.com/app/{d.get('steamAppID')}" if d.get("steamAppID") \
              else f"https://www.cheapshark.com/redirect?dealID={d.get('dealID')}"
        ok, _ = passes_all_checks(title, url, "cheapshark", None)
        if not ok:
            continue
        out.append({
            "id": _hid("cheapshark", d.get("dealID")),
            "source": "cheapshark",
            "title": title,
            "platform": "steam",
            "deal_type": "discount",
            "discount": savings,
            "price": f"${d.get('salePrice')}",
            "worth": f"${d.get('normalPrice')}",
            "image": d.get("thumb"),
            "claim_url": url,
            "expiry": None,
        })
    return out


# ---------------------------------------------------------------------------
# 3) Reddit — moderated deal communities, flair-filtered
# ---------------------------------------------------------------------------
def fetch_reddit() -> list[dict]:
    out = []
    for feed in REDDIT_FEEDS:
        try:
            data = requests.get(feed, headers=_HEADERS, timeout=20).json()
            posts = data["data"]["children"]
        except Exception:
            continue
        for child in posts:
            p = child.get("data", {})
            title = p.get("title", "")
            flair = p.get("link_flair_text", "") or ""
            # Expiry indicator: NSFW/Spoiler flags = deal ended.
            if p.get("over_18") or p.get("spoiler"):
                continue
            # Require an accepted flair OR a bracketed tag in the title.
            tag_source = f"{flair} {title}"
            m = _FLAIR_RE.search(tag_source)
            if not m:
                continue
            platform = _norm_platform(m.group(1)) or _norm_platform(flair) or _norm_platform(title)
            if platform is None:
                # [Giveaway] with no platform -> default bucket steam (PC) unless title says otherwise
                platform = "steam"
            url = p.get("url_overridden_by_dest") or p.get("url") or ""
            is_free = bool(re.search(r"\b(free|100%|giveaway)\b", title, re.IGNORECASE))
            pct = _PCT_RE.search(title)
            discount = 100 if is_free else (int(pct.group(1)) if pct else None)
            deal_type = "free" if is_free else "discount"
            ok, _ = passes_all_checks(title, url, "reddit", None)
            if not ok:
                continue
            # For discounts coming from Reddit, only keep meaningful ones.
            if deal_type == "discount" and (discount is None or discount < 50):
                continue
            out.append({
                "id": _hid("reddit", p.get("id")),
                "source": "reddit",
                "title": title,
                "platform": platform,
                "deal_type": deal_type,
                "discount": discount,
                "price": "FREE" if is_free else None,
                "worth": None,
                "image": _reddit_thumb(p),
                "claim_url": url,
                "expiry": None,
            })
    return out


def _reddit_thumb(p):
    t = p.get("thumbnail")
    return t if t and t.startswith("http") else None


def fetch_all() -> list[dict]:
    """Aggregate every source. Dedupe by id."""
    seen, merged = set(), []
    for fn in (fetch_gamerpower, fetch_cheapshark, fetch_reddit):
        try:
            for d in fn():
                if d["id"] not in seen:
                    seen.add(d["id"])
                    merged.append(d)
        except Exception as e:
            print(f"[scraper] {fn.__name__} failed: {e}")
    return merged

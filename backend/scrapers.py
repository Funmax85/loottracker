"""Scrapers/aggregators for GamerPower, CheapShark, and Reddit deal feeds..

Every record passes through validation.passes_all_checks before being returned.
NOTHING here generates, guesses, or brute-forces codes — it only aggregates real,
published deals from public APIs/feeds.
"""
import re
import hashlib
import requests
import xml.etree.ElementTree as ET

from config import (
    GAMERPOWER_API, CHEAPSHARK_DEALS_API, CHEAPSHARK_STORES_API,
    REDDIT_FEEDS, USER_AGENT, PLATFORM_MAP, ACCEPTED_FLAIR_REGEX,
    DEEP_DISCOUNT_THRESHOLD, SLICKDEALS_FEEDS, PS_PLUS_FEED,
    PLATPRICES_API, PLATPRICES_API_KEY,
    XBOX_FEED, ITAD_API_KEY, ITAD_DEALS_API,
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
            # No "type" filter -> returns ALL giveaway types (full games, loot,
            # beta keys, DLC). Restricting to game.loot was hiding free games.
            r = requests.get(GAMERPOWER_API, params={"platform": plat_param},
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


# ---------------------------------------------------------------------------
# 4) Slickdeals — RSS feeds for PlayStation & Xbox console deals
# ---------------------------------------------------------------------------
def fetch_slickdeals() -> list[dict]:
    out = []
    for feed in SLICKDEALS_FEEDS:
        try:
            resp = requests.get(feed, headers=_HEADERS, timeout=20)
            root = ET.fromstring(resp.content)
        except Exception:
            continue
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if not title or not link:
                continue
            platform = _norm_platform(title)
            if platform is None:
                continue  # only keep items we can confidently tag to a platform
            is_free = bool(re.search(r"\bfree\b", title, re.IGNORECASE))
            pct = _PCT_RE.search(title)
            discount = 100 if is_free else (int(pct.group(1)) if pct else None)
            deal_type = "free" if is_free else "discount"
            # Slickdeals discounts without a clear % are noisy — require a number.
            if deal_type == "discount" and discount is None:
                continue
            ok, _ = passes_all_checks(title, link, "slickdeals", None)
            if not ok:
                continue
            out.append({
                "id": _hid("slickdeals", link),
                "source": "slickdeals",
                "title": re.sub(r"\s+", " ", title)[:140],
                "platform": platform,
                "deal_type": deal_type,
                "discount": discount,
                "price": "FREE" if is_free else None,
                "worth": None,
                "image": None,
                "claim_url": link,
                "expiry": None,
            })
    return out


# ---------------------------------------------------------------------------
# 5) Subscription monthly free games — PS Plus & Xbox Game Pass
#    (via moderated subreddits that mirror official monthly announcements)
# ---------------------------------------------------------------------------
def _fetch_subscription_feed(feed_url, platform, source, label,
                             official_domain, store_url) -> list[dict]:
    out = []
    try:
        data = requests.get(feed_url, headers=_HEADERS, timeout=20).json()
        posts = data["data"]["children"]
    except Exception:
        return out
    for child in posts:
        p = child.get("data", {})
        title = p.get("title", "")
        if p.get("over_18") or p.get("spoiler"):
            continue
        # Only monthly-games / free announcements.
        if not re.search(r"\b(free|monthly games|game pass|added|essential|claim|leaving)\b",
                         title, re.IGNORECASE):
            continue
        # "leaving"/"removed" posts indicate games going AWAY — skip those.
        if re.search(r"\b(leaving|removed|delisted|last chance)\b", title, re.IGNORECASE):
            continue
        url = p.get("url_overridden_by_dest") or p.get("url") or ""
        if official_domain not in url:
            url = store_url
        ok, _ = passes_all_checks(title, url, source, None)
        if not ok:
            continue
        out.append({
            "id": _hid(source, p.get("id")),
            "source": source,
            "title": re.sub(r"\s+", " ", title)[:140],
            "platform": platform,
            "deal_type": "free",
            "discount": 100,
            "price": label,
            "worth": None,
            "image": _reddit_thumb(p),
            "claim_url": url,
            "expiry": None,
        })
    return out


def fetch_ps_plus() -> list[dict]:
    return _fetch_subscription_feed(
        PS_PLUS_FEED, "playstation", "ps_plus", "FREE (PS+)",
        "playstation.com", "https://store.playstation.com/")


def fetch_xbox_gamepass() -> list[dict]:
    return _fetch_subscription_feed(
        XBOX_FEED, "xbox", "xbox_gamepass", "FREE (Game Pass)",
        "xbox.com", "https://www.xbox.com/")


# ---------------------------------------------------------------------------
# 6) PlatPrices — free PlayStation pricing API (dormant unless key is set)
# ---------------------------------------------------------------------------
def fetch_platprices() -> list[dict]:
    if not PLATPRICES_API_KEY:
        return []  # no key configured -> source stays off, no error
    out = []
    try:
        resp = requests.get(PLATPRICES_API, headers=_HEADERS, timeout=20, params={
            "key": PLATPRICES_API_KEY, "sales": 1, "region": "us",
        })
        data = resp.json()
    except Exception:
        return out
    items = data if isinstance(data, list) else data.get("games", data.get("data", []))
    for g in (items or []):
        try:
            title = g.get("Name") or g.get("name") or ""
            sale = float(g.get("SalePrice") or g.get("sale_price") or 0)
            base = float(g.get("BasePrice") or g.get("base_price") or 0)
            if base <= 0 or sale >= base:
                continue
            discount = round((1 - sale / base) * 100)
            if discount < DEEP_DISCOUNT_THRESHOLD:
                continue
            url = g.get("URL") or g.get("PSStoreURL") or "https://store.playstation.com/"
            ok, _ = passes_all_checks(title, url, "platprices", None)
            if not ok:
                continue
            out.append({
                "id": _hid("platprices", g.get("PPID") or url),
                "source": "platprices",
                "title": title[:140],
                "platform": "playstation",
                "deal_type": "discount",
                "discount": discount,
                "price": f"${sale:.2f}",
                "worth": f"${base:.2f}",
                "image": g.get("Image") or g.get("image"),
                "claim_url": url,
                "expiry": None,
            })
        except Exception:
            continue
    return out


# ---------------------------------------------------------------------------
# 8) IsThereAnyDeal — aggregates many legitimate stores (dormant unless keyed)
#    License: do NOT alter prices or strip affiliate tags from URLs.
# ---------------------------------------------------------------------------
def fetch_itad() -> list[dict]:
    if not ITAD_API_KEY:
        return []  # no key -> source stays off, no error
    out = []
    try:
        resp = requests.get(ITAD_DEALS_API, headers=_HEADERS, timeout=20, params={
            "key": ITAD_API_KEY, "country": "US", "limit": 80,
            "sort": "-cut",  # biggest discounts first
        })
        data = resp.json()
    except Exception:
        return out
    deals = data.get("list", data) if isinstance(data, dict) else data
    for g in (deals or []):
        try:
            title = g.get("title", "")
            deal = g.get("deal", {}) or {}
            cut = int(deal.get("cut", 0))  # discount %
            if cut < DEEP_DISCOUNT_THRESHOLD:
                continue
            price = (deal.get("price", {}) or {}).get("amount")
            regular = (deal.get("regular", {}) or {}).get("amount")
            # ITAD license: use their URL as-is (keeps affiliate tags intact).
            url = deal.get("url") or g.get("url") or ""
            ok, _ = passes_all_checks(title, url, "isthereanydeal", None)
            if not ok:
                continue
            out.append({
                "id": _hid("itad", g.get("id") or url),
                "source": "isthereanydeal",
                "title": title[:140],
                "platform": "steam",  # ITAD is predominantly PC stores
                "deal_type": "discount",
                "discount": cut,
                "price": f"${price:.2f}" if isinstance(price, (int, float)) else None,
                "worth": f"${regular:.2f}" if isinstance(regular, (int, float)) else None,
                "image": (g.get("assets", {}) or {}).get("banner400"),
                "claim_url": url,
                "expiry": (deal.get("expiry") or "").split("T")[0] or None,
            })
        except Exception:
            continue
    return out


def fetch_all() -> list[dict]:
    """Aggregate every source. Dedupe by id."""
    seen, merged = set(), []
    for fn in (fetch_gamerpower, fetch_cheapshark, fetch_reddit,
               fetch_slickdeals, fetch_ps_plus, fetch_xbox_gamepass,
               fetch_platprices, fetch_itad):
        try:
            for d in fn():
                if d["id"] not in seen:
                    seen.add(d["id"])
                    merged.append(d)
        except Exception as e:
            print(f"[scraper] {fn.__name__} failed: {e}")
    return merged

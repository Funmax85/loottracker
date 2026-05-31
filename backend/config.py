"""LootTracker configuration: source endpoints, whitelist/blocklist, and filtering rules."""
import os

# ---------------------------------------------------------------------------
# Data source endpoints
# ---------------------------------------------------------------------------
GAMERPOWER_API = "https://www.gamerpower.com/api/giveaways"
CHEAPSHARK_DEALS_API = "https://www.cheapshark.com/api/1.0/deals"
CHEAPSHARK_STORES_API = "https://www.cheapshark.com/api/1.0/stores"

REDDIT_FEEDS = [
    "https://www.reddit.com/r/GameDeals/hot/.json",
    "https://www.reddit.com/r/FreeGameFindings/hot/.json",
]

# Slickdeals category RSS feeds (free, no key). Console-focused.
SLICKDEALS_FEEDS = [
    # Video games front-page deals feed (covers PS / Xbox / Steam, vote-filtered).
    "https://feeds.feedburner.com/SlickdealsnetGames",
    # Hot video-game deals (forum feed, broader coverage).
    "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1&q=playstation",
    "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1&q=xbox",
]

# PlatPrices — FREE PlayStation pricing API, but requires a key obtained by
# emailing contact@platprices.com. Leave unset and this source stays dormant.
# Set the PLATPRICES_API_KEY environment variable in Render to enable it.
PLATPRICES_API_KEY = os.environ.get("PLATPRICES_API_KEY", "").strip()
PLATPRICES_API = "https://platprices.com/api.php"

# PS Plus monthly free games — sourced via the free Reddit r/PS_Plus feed,
# which mirrors Sony's official monthly announcements (no scraping of PSN).
PS_PLUS_FEED = "https://www.reddit.com/r/PS_Plus/hot/.json"

# Xbox Game Pass / Games with Gold — via the free r/XboxGamePass feed,
# mirroring Microsoft's official monthly additions (no scraping of Xbox store).
XBOX_FEED = "https://www.reddit.com/r/XboxGamePass/hot/.json"

# IsThereAnyDeal — aggregates many LEGITIMATE stores. Free, but requires
# registering an app at https://isthereanydeal.com/apps/my/ to get a key.
# NOTE: their license forbids "competing" apps and altering their data
# (keep affiliate tags & prices intact). Dormant until a key is set.
ITAD_API_KEY = os.environ.get("ITAD_API_KEY", "").strip()
ITAD_DEALS_API = "https://api.isthereanydeal.com/deals/v2"

# A descriptive User-Agent is REQUIRED by Reddit and polite for the others.
USER_AGENT = "LootTracker/1.0 (deal aggregator; contact: admin@loottracker.local)"

# ---------------------------------------------------------------------------
# Anti-scam: domain whitelist. A claim link must resolve to one of these.
# ---------------------------------------------------------------------------
DOMAIN_WHITELIST = {
    "steampowered.com",
    "store.steampowered.com",
    "store.playstation.com",
    "xbox.com",
    "epicgames.com",
    "store.epicgames.com",
    "gog.com",
    "humblebundle.com",
    "greenmangaming.com",
    "alienwarearena.com",
}

# GamerPower hands out keys via its own redirect ("open-giveaway") and a few
# trusted partner storefronts. These are allowed in addition to the whitelist.
TRUSTED_AGGREGATOR_DOMAINS = {
    "gamerpower.com",
    "cheapshark.com",
    "slickdeals.net",
    "platprices.com",
    "isthereanydeal.com",
}

# ---------------------------------------------------------------------------
# Anti-scam: keyword blocklist. Any title/url/source containing these is dropped.
# ---------------------------------------------------------------------------
BLOCKLIST_KEYWORDS = [
    "generator",
    "human verification",
    "survey",
    "hack",
    "free-gg",
    "freegg",
    "free gg",
    "no survey",
    "cracked",
    "keygen",
    "giftcardgen",
]

# Reddit flair patterns we accept (case-insensitive).
ACCEPTED_FLAIR_REGEX = r"\[(xbox|psn|playstation|ps[45]|steam|pc|giveaway|epic|gog)\]"

# Platform normalization map.
PLATFORM_MAP = {
    "steam": "steam",
    "pc": "steam",
    "epic": "steam",
    "gog": "steam",
    "playstation": "playstation",
    "ps": "playstation",
    "psn": "playstation",
    "ps4": "playstation",
    "ps5": "playstation",
    "xbox": "xbox",
    "xbox one": "xbox",
    "xbox series": "xbox",
}

DEEP_DISCOUNT_THRESHOLD = 70  # percent
DB_PATH = "loottracker.db"
REFRESH_INTERVAL_MINUTES = 30

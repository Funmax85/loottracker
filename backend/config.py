"""LootTracker configuration: source endpoints, whitelist/blocklist, and filtering rules."""

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

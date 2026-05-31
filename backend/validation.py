"""Anti-scam and validation logic: domain whitelisting, keyword blocklist, expiry checks."""
from urllib.parse import urlparse

from config import (
    DOMAIN_WHITELIST,
    TRUSTED_AGGREGATOR_DOMAINS,
    BLOCKLIST_KEYWORDS,
)

_ALLOWED = DOMAIN_WHITELIST | TRUSTED_AGGREGATOR_DOMAINS


def _root_domain(host: str) -> str:
    """Reduce 'www.store.steampowered.com' -> 'steampowered.com' (last two labels),
    while still matching multi-label whitelist entries like 'store.playstation.com'."""
    host = (host or "").lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_domain_allowed(url: str) -> bool:
    """Return True only if the URL's host (or its registrable parent) is whitelisted."""
    if not url:
        return False
    try:
        host = _root_domain(urlparse(url).netloc)
    except Exception:
        return False
    if not host:
        return False
    # exact match OR the whitelisted entry is a suffix of the host
    for allowed in _ALLOWED:
        if host == allowed or host.endswith("." + allowed):
            return True
    return False


def contains_blocked_keyword(*texts: str) -> bool:
    """Return True if any provided text contains a blocklisted scam keyword."""
    blob = " ".join(t for t in texts if t).lower()
    return any(kw in blob for kw in BLOCKLIST_KEYWORDS)


def is_expired(status: str | None) -> bool:
    """GamerPower marks ended giveaways with status 'Expired'."""
    return (status or "").strip().lower() == "expired"


def passes_all_checks(title: str, url: str, source: str = "", status: str | None = None) -> tuple[bool, str]:
    """Master validator. Returns (ok, reason_if_rejected)."""
    if is_expired(status):
        return False, "expired"
    if contains_blocked_keyword(title, url, source):
        return False, "blocklisted_keyword"
    if not is_domain_allowed(url):
        return False, "domain_not_whitelisted"
    return True, ""

# 🎮 LootTracker

Aggregates **verified, active** free game keys, giveaways, and deep discounts for **Steam, PlayStation & Xbox** — with strict anti-scam filtering. It only **aggregates real published deals**; it never generates, guesses, or brute-forces codes.

## Stack
- **Backend:** Python + FastAPI + SQLite (tracks active vs. expired so you never see stale deals)
- **Frontend:** single-file HTML/CSS/JS (no build step), fully responsive / mobile-ready
- **Sources:** GamerPower API · CheapShark API · Reddit JSON feeds (r/GameDeals, r/FreeGameFindings)

## Run it (3 steps)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Then open **http://localhost:8000** in your browser.

The backend auto-refreshes every 30 min and on startup. Hit **↻ Refresh** in the UI or `POST /api/refresh` to pull immediately.

## API
| Endpoint | Description |
|---|---|
| `GET /api/deals?platform=all\|steam\|playstation\|xbox&filter=all\|free\|deep` | Active deals |
| `GET /api/stats` | Counts + last refresh time |
| `POST /api/refresh` | Force an immediate re-aggregation |

## Anti-scam guarantees (in `validation.py` + `config.py`)
1. **Domain whitelist** — claim links must resolve to `steampowered.com`, `store.playstation.com`, `xbox.com`, `epicgames.com`, `gog.com`, `humblebundle.com`, `greenmangaming.com`, `alienwarearena.com` (plus the trusted aggregator redirects).
2. **Keyword blocklist** — drops anything containing `generator`, `human verification`, `survey`, `hack`, `free-gg`, etc.
3. **Expiry checker** — drops GamerPower `Expired` status and Reddit threads flagged NSFW/Spoiler (the community signal a deal has ended). Deals that vanish from a source are auto-marked expired in SQLite.

## Mobile / Install as an app (PWA)
LootTracker is a full Progressive Web App — it installs to a phone home screen and runs standalone (no browser chrome), with an offline app shell.

**To install:**
- **Android (Chrome):** open the site → menu (⋮) → **Add to Home screen** / **Install app**.
- **iOS (Safari):** open the site → Share → **Add to Home Screen**.

The service worker (`sw.js`) caches the app shell **cache-first** so it opens instantly/offline, while `/api/*` calls are **network-first** so deals are always fresh (falling back to the last cached response only when offline). Home-screen shortcuts jump straight to **Free Giveaways** (`/?filter=free`) and **Deep Discounts** (`/?filter=deep`).

> Installability requires HTTPS in production (or `localhost` during dev). Behind a real domain, put the app behind TLS (e.g. a reverse proxy) and it becomes installable automatically.

## Files
```
backend/
  main.py          FastAPI app, endpoints, background refresh loop
  scrapers.py      GamerPower / CheapShark / Reddit aggregators
  validation.py    whitelist + blocklist + expiry logic
  database.py      SQLite layer (active vs expired tracking)
  config.py        sources, whitelist, blocklist, thresholds
  requirements.txt
frontend/
  index.html       full single-page UI (PWA-enabled)
  manifest.json    web app manifest (name, icons, shortcuts)
  sw.js            service worker (offline shell + fresh API)
  icon-192.png     app icons (any + maskable)
  icon-512.png
  icon-192-mask.png
  icon-512-mask.png
```

> Always sanity-check a deal before entering account credentials. LootTracker filters known scam patterns but no filter is perfect.

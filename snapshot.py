"""
Frozen game facts (2026-09-27).

Once a game goes final its weather and playing surface should stay what the site last showed,
not change or vanish: the forecast used to disappear at the final whistle (Page 1 then waits on
nflverse to record a kickoff temperature, sometimes for days), and nflverse blanks a finished
game's surface until it fills in the real one later.

Every build can't simply remember -- it starts from a fresh checkout -- so each build publishes
game-snapshot.json with the site (like nflverse-stamps.json), holding every game's latest
populated Page 1 weather, Page 2 weather and surface. The next build reads it back from the
live site; page1_data.apply_game_snapshot keeps it current until a game is final and serves it
unchanged from then on.
"""

import json
import os
import time
import urllib.request

FILE_NAME = "game-snapshot.json"
DEFAULT_SITE_URL = "https://l0d3st4r.github.io/at-a-glance"  # overridden in CI by AAG_SITE_URL
ROOT = os.path.dirname(os.path.abspath(__file__))
LOCAL_PATH = os.path.join(ROOT, "data", FILE_NAME)


def load(warnings):
    """{game_id: {...}} from the live site's snapshot, else this machine's last build, else {}."""
    base = (os.environ.get("AAG_SITE_URL") or DEFAULT_SITE_URL).rstrip("/")
    try:
        # ?t= skips GitHub Pages' 10-minute cache, so the snapshot from a just-finished deploy is seen
        req = urllib.request.Request(f"{base}/{FILE_NAME}?t={int(time.time())}", headers={"User-Agent": "at-a-glance-build"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8")).get("games") or {}
    except Exception as live_err:
        try:
            with open(LOCAL_PATH, encoding="utf-8") as f:
                return json.load(f).get("games") or {}
        except (OSError, ValueError):
            warnings.append(f"game snapshot: none on the live site ({live_err}) or locally -- "
                            "finished games fall back to observed weather and the stadium's usual surface")
            return {}


def save(games, season):
    os.makedirs(os.path.dirname(LOCAL_PATH), exist_ok=True)
    with open(LOCAL_PATH, "w", encoding="utf-8") as f:
        json.dump({"season": season, "games": games}, f, separators=(",", ":"), default=str)

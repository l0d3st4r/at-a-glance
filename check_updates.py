"""
Has nflverse published anything new since the live site was built? (2026-09-24)

The refresh workflow runs this every 15 minutes in season. It builds a small
"fingerprint" of the nflverse data the site uses, compares it with the fingerprint
the live site was built from (site/nflverse-stamps.json, published alongside the
pages), and tells the workflow whether a rebuild is worth doing.

The site reads seven nflverse-data releases (see nflverse_client.py):

  schedules     games.csv -- scores, kickoff times, stadiums. Updated MANY times a
                day, but almost always only for betting lines (moneylines, spreads,
                totals), which the site never shows. So for this one we download
                the file (small) and fingerprint its current-season rows WITHOUT the
                betting columns. A line move doesn't trigger a rebuild; a score,
                kickoff time or QB change does.
  stats_team, stats_player, injuries, rosters, snap_counts, depth_charts
                Updated on nflverse's own schedules (stats after each game window
                and daily at 09:00 UTC, injuries/rosters/depth charts daily at 07:00
                UTC, snap counts every 6 hours -- see nflverse/nflverse-data's
                workflows.md). These are bigger files, so for them we use the time
                GitHub says the current season's file was last uploaded.

Standard library only, so the check job doesn't have to install anything.

Usage:
    python check_updates.py --out stamps.json
        Write the current fingerprint (the build job saves it into site/).
    python check_updates.py --compare https://<pages-url>/nflverse-stamps.json
        Print changed=true/false (and append it to $GITHUB_OUTPUT when set).
"""

import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.github.com/repos/nflverse/nflverse-data"
GAMES_CSV = "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv"
TIMESTAMP_TAGS = ["stats_team", "stats_player", "injuries", "rosters", "snap_counts", "depth_charts"]
BETTING_COLUMNS = {"away_moneyline", "home_moneyline", "spread_line", "away_spread_odds", "home_spread_odds",
                   "total_line", "under_odds", "over_odds"}


def current_season(today=None):
    """NFL seasons start in September and end in February: Jan-Feb belong to last year's season."""
    today = today or datetime.date.today()
    return today.year if today.month >= 3 else today.year - 1


def _get(url, accept=None):
    req = urllib.request.Request(url, headers={"User-Agent": "at-a-glance-refresh"})
    if accept:
        req.add_header("Accept", accept)
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def schedule_fingerprint(season, games_csv_text):
    """sha256 of this season's schedule rows with the betting columns left out."""
    rows = csv.DictReader(io.StringIO(games_csv_text))
    keep = [c for c in (rows.fieldnames or []) if c not in BETTING_COLUMNS]
    lines = sorted(",".join(r.get(c) or "" for c in keep) for r in rows if r.get("season") == str(season))
    if not lines:
        return None
    return hashlib.sha256("\n".join([",".join(keep)] + lines).encode()).hexdigest()[:16]


def latest_upload(assets, season):
    """Newest upload time among a release's files for this season (e.g. injuries_2026.parquet)."""
    pat = re.compile(rf"_{season}\.")
    times = [a["updated_at"] for a in assets if pat.search(a.get("name", ""))]
    return max(times) if times else None


def release_assets(tag):
    release = json.loads(_get(f"{API}/releases/tags/{tag}", "application/vnd.github+json"))
    assets, page = [], 1
    while True:
        batch = json.loads(_get(f"{API}/releases/{release['id']}/assets?per_page=100&page={page}",
                                "application/vnd.github+json"))
        assets += batch
        if len(batch) < 100:
            return assets
        page += 1


def fingerprint(season=None):
    """{dataset: value or None}. None = couldn't read it this time (never counts as a change)."""
    season = season or current_season()
    out = {"season": season}
    try:
        out["schedules"] = schedule_fingerprint(season, _get(GAMES_CSV).decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"check_updates: schedules unreadable: {e}", file=sys.stderr)
        out["schedules"] = None
    for tag in TIMESTAMP_TAGS:
        try:
            out[tag] = latest_upload(release_assets(tag), season)
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            print(f"check_updates: {tag} unreadable: {e}", file=sys.stderr)
            out[tag] = None
    return out


def changed(now, live):
    """True if anything we could read differs from what the live site was built from.
    No live fingerprint (first run, or the site predates this) counts as changed."""
    if not live:
        return True
    return any(v is not None and live.get(k) != v for k, v in now.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write the current fingerprint to this file")
    ap.add_argument("--compare", help="URL of the live site's nflverse-stamps.json")
    args = ap.parse_args()

    now = fingerprint()
    print(json.dumps(now, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(now, f, indent=2)
    if args.compare:
        if all(v is None for k, v in now.items() if k != "season"):
            # nflverse (or GitHub's API) unreachable: don't rebuild blind, the next check will retry
            result = False
            print("check_updates: nothing readable -- skipping this round")
        else:
            try:
                live = json.loads(_get(args.compare))
            except (urllib.error.URLError, OSError, ValueError) as e:
                print(f"check_updates: no live fingerprint ({e}) -- rebuilding")
                live = None
            result = changed(now, live)
            if live:
                diff = [k for k, v in now.items() if v is not None and live.get(k) != v]
                print("check_updates: changed: " + (", ".join(diff) if diff else "nothing"))
        line = f"changed={'true' if result else 'false'}"
        print(line)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write(line + "\n")


if __name__ == "__main__":
    main()

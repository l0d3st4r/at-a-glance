"""
TV networks, kept by hand in tv_networks.csv (2026-09-29) -- nflverse has no broadcast field.

tv_networks.csv has one row per game. Only the "network" and "time_tbd" columns are read; the
others are there so you can tell the games apart. To change a game's network, edit its
"network" cell (on GitHub: open the file, click the pencil, edit, commit) -- the next build
shows it. Write it the way the
site should show it: CBS, FOX, NBC, ESPN, ABC, ESPN/ABC, Prime Video, NFL Network, Netflix.
A blank cell shows "TV TBD".

Every Tuesday the "Check TV networks" workflow (check_tv_networks.py) compares the file with
the published schedule and lists flexed games and newly announced networks in a GitHub issue,
"TV networks to review". It never edits the file itself.

"time_tbd" marks a game whose kickoff time the NFL hasn't set yet (Week 18, and the late-season
games waiting on the Saturday picks). nflverse lists those at a placeholder Sunday 1:00 PM, so
without the mark the site would show a time that isn't real. Put "yes" in the cell and the site
shows TBD instead of the time; clear the cell once the time is announced. The mark stops
counting TBD_IGNORE_DAYS days before the game, so a forgotten "yes" can't hide a real kickoff.

When nflverse adds games the file doesn't have yet (the playoffs), add them with
    python tv_networks.py
which appends a row for every missing game and never touches rows already there.

A game is found by its nflverse game_id (season_week_away_home, e.g. 2026_04_PIT_CLE), which
stays the same when a game is flexed to another time slot -- only the network needs changing.
"""

import csv
import os
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, "tv_networks.csv")
COLUMNS = ["game_id", "week", "gameday", "kickoff_et", "away", "home", "network", "time_tbd"]
TBD_IGNORE_DAYS = 5   # by then the NFL has announced every time (Week 18's come six days ahead)


def _read():
    try:
        with open(PATH, newline="", encoding="utf-8-sig") as f:   # -sig: Excel saves a BOM
            return list(csv.DictReader(f))
    except OSError:
        return []


def load(schedules, warnings):
    """{game_id: "CBS", ...} for every game with a network filled in."""
    rows = _read()
    if not rows:
        warnings.append(f"TV networks: {os.path.basename(PATH)} missing or empty -- every game shows TV TBD")
        return {}
    known = {g.get("game_id") for g in schedules}
    out = {}
    for r in rows:
        gid, net = (r.get("game_id") or "").strip(), (r.get("network") or "").strip()
        if not gid or not net:
            continue
        if known and gid not in known:
            warnings.append(f"TV networks: {gid} in {os.path.basename(PATH)} isn't in nflverse's schedule -- check the game_id")
            continue
        out[gid] = net
    return out


def _yes(value):
    return str(value or "").strip().lower() in ("yes", "y", "true", "1", "tbd", "x")


def load_time_tbd(schedules, today):
    """{game_id, ...} of upcoming games marked time_tbd -- the site shows TBD for their kickoff time."""
    days = {g.get("game_id"): str(g.get("gameday") or "")[:10] for g in schedules}
    out = set()
    for r in _read():
        gid = (r.get("game_id") or "").strip()
        if not _yes(r.get("time_tbd")) or gid not in days:
            continue
        try:
            if (date.fromisoformat(days[gid]) - today).days > TBD_IGNORE_DAYS:
                out.add(gid)
        except ValueError:
            continue
    return out


def sync(schedules):
    """Adds a row for every game missing from the file (keeping existing rows as they are). Returns how many."""
    rows = _read()
    have = {r.get("game_id") for r in rows}
    new = [{"game_id": g["game_id"], "week": g.get("week"), "gameday": g.get("gameday"),
            "kickoff_et": g.get("gametime"), "away": g.get("away_team"), "home": g.get("home_team"), "network": "", "time_tbd": ""}
           for g in sorted(schedules, key=lambda g: (str(g.get("gameday")), str(g.get("gametime")), g["game_id"]))
           if g.get("game_id") and g["game_id"] not in have]
    if new:
        with open(PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows + new)
    return len(new)


if __name__ == "__main__":
    import nflverse_client
    season, _week, _err = nflverse_client.get_current_season_and_week()
    schedules, err = nflverse_client.get_schedules(season)
    if err:
        raise SystemExit(f"couldn't load nflverse's schedule: {err}")
    print(f"added {sync(schedules)} game(s) to {PATH}")

"""
College football data build (2026-10-12), the CFB counterpart of build_data.py. Run with:

    python build_cfb_data.py                   -> data/cfb.json (+ data/cfb-snapshot.json) for the current season
    python build_cfb_data.py --season 2025     -> another season

render_cfb.py turns data/cfb.json into site/cfb/. Everything comes through cfb_client.py.

Which games (Jason, 2026-10-12): only games involving a team in that week's AP poll -- the Top 25 and the
others receiving votes. Each week is frozen to the poll that came out before it (poll week N is the one
released ahead of week N's games; week 1's is the preseason poll), so Week 3 always shows the games that
mattered in Week 3. Weeks with no poll yet follow the latest one, and so do the bowls and the Playoff.

The output follows build_data.py's data/matchups.json shape wherever the NFL pages show the same thing,
so render_cfb.py can draw it with the NFL's own page code:
  season_weeks          Page 0: a week a panel (Week 1 ... Week 16, then "Bowls & Playoff"), each game with
                        its records frozen the NFL's way (a finished game the record right after it)
  game_details          every game on Page 0, "as of kickoff" like page1_data.py's: record, streak, the
                        offense / defense ranks among the FBS teams (points and yards a game), season or
                        game leaders with their league crowns, weather, the Game Info page, and the team
                        pages (Overview, Team Stats, Schedule; no injury report -- there's no source for one).
                        College additions on each side: "rank" (that week's AP rank), "trend" (the AP rank
                        poll by poll), "conf" (conference and conference record)
  player_weeks          every FBS player's week (player_stats.py's keys), for Player Stats and Stat Leaders
                        (all of FBS -- Jason, 2026-10-12)
  matchup_weeks         the offenses' EPA rows for the Matchups card (matchup.py), from the play-by-play
  defense_vs_position   what each FBS defense allows (matchup.defense_table)
  rankings              this week's AP / Coaches / CFP polls for the Rankings page, each team's record
                        and conference added
  teams                 every school on the pages: name, conference, colors (helmets, pills)

Nothing here knows NFL abbreviations: teams are ESPN ids until the very end, then each school's
abbreviation from cfb_team_info (made unique where two share one).

Like build_data.py, every piece is wrapped so one failure is a warning, not a failed build.
"""

import argparse
import json
import os
import re
import sys
import traceback
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import cfb_client as cc
import matchup
import names
import weather as wx
from page1_data import NWS_WINDOW_DAYS, _p1_weather_from_detail, haversine_miles
from stadiums import NEUTRAL_VENUES, STADIUMS, STATE_NAMES

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(ROOT, "data", "cfb.json")
SNAP_NAME = "cfb-snapshot.json"
SNAP_LOCAL = os.path.join(ROOT, "data", SNAP_NAME)
DEFAULT_SITE_URL = "https://l0d3st4r.github.io/at-a-glance"   # overridden in CI by AAG_SITE_URL, as snapshot.py
ET = ZoneInfo("America/New_York")
POST_KEY, POST_LABEL = "post", "Bowls & Playoff"
COACH_DAYS = 7          # a cached head coach is re-checked after a week

CONF_SHORT = {"American Athletic": "AAC", "Conference USA": "CUSA", "FBS Independents": "IND", "Big Ten": "B1G",
              "Sun Belt": "SBC", "Pac-12": "PAC", "Mountain West": "MW", "ACC": "ACC", "SEC": "SEC",
              "Mid-American": "MAC", "Big 12": "B12"}
CONF_NAME = {"American Athletic": "American", "Conference USA": "C-USA", "FBS Independents": "Independent",
             "Mid-American": "MAC"}

LEADER_STATS = [("passing_yards", "Passing Yards", "pyds"), ("rushing_yards", "Rushing Yards", "ryds"),
                ("receiving_yards", "Receiving Yards", "reyds"), ("interceptions", "Interceptions", "dint"),
                ("sacks", "Sacks", "dsk")]
LEADER_EXTRAS = {"pyds": {"completions": "cmp", "attempts": "att", "passing_tds": "ptd", "passing_ints": "int"},
                 "ryds": {"carries": "car", "rushing_tds": "rtd"},
                 "reyds": {"receptions": "rec", "receiving_tds": "retd"}}

# ESPN's college box score: a row a player and category, each value in its named column -- or, for some
# rows (every passing line in 2026), only in stat_1 ... stat_5 in this order
BOX = {
    "passing": [("completions/passingAttempts", ("cmp", "att")), ("passingYards", "pyds"), (None, None),
                ("passingTouchdowns", "ptd"), ("interceptions", "int")],
    "rushing": [("rushingAttempts", "car"), ("rushingYards", "ryds"), (None, None), ("rushingTouchdowns", "rtd")],
    "receiving": [("receptions", "rec"), ("receivingYards", "reyds"), (None, None), ("receivingTouchdowns", "retd")],
    "fumbles": [("fumbles", None), ("fumblesLost", "rfum"), ("fumblesRecovered", "fr")],
    "defensive": [("totalTackles", "_tot"), ("soloTackles", "solo"), ("sacks", "dsk"), ("tacklesForLoss", "tfl"),
                  ("passesDefended", "pd"), ("hurries", "qbh"), ("defensiveTouchdowns", "dtd")],
    "interceptions": [("interceptions", "dint")],
    "kicking": [("fieldGoalsMade/fieldGoalAttempts", ("fgm", "fga")), (None, None), ("longFieldGoalMade", "fglng"),
                ("extraPointsMade/extraPointAttempts", ("xpm", "xpa"))],
    "punting": [("punts", "p"), ("puntYards", "pyd"), (None, None), (None, None), ("puntsInside20", "p20")],
    "kickReturns": [("kickReturns", "kr"), ("kickReturnYards", "kryds")],
    "puntReturns": [("puntReturns", "pr"), ("puntReturnYards", "pryds")],
}
MAX_KEYS = {"fglng"}


def num(v):
    try:
        f = float(str(v).strip())
    except (TypeError, ValueError):
        return 0
    if f != f:
        return 0
    return int(f) if f == int(f) else round(f, 1)


# ---------------------------------------------------------------- snapshot (what earlier builds learned)
# The cache every build reads back from the live site and publishes again (like snapshot.py): past weeks'
# AP polls (they never change), each school's head coach (re-checked weekly) and each finished game's
# weather (frozen at what the site last showed).

def load_snapshot(warnings):
    import time
    import urllib.request
    base = (os.environ.get("AAG_SITE_URL") or DEFAULT_SITE_URL).rstrip("/")
    try:
        req = urllib.request.Request(f"{base}/cfb/{SNAP_NAME}?t={int(time.time())}", headers={"User-Agent": "at-a-glance-build"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as live_err:
        try:
            with open(SNAP_LOCAL, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            warnings.append(f"cfb snapshot: none on the live site ({live_err}) or locally -- starting fresh")
            return {}


# ---------------------------------------------------------------- teams

def build_teams(info_rows):
    """{team_id: {...}}: every school, with a unique abbreviation (a clash keeps the FBS school's and
    gives the other its id)."""
    rank = {"fbs": 0, "fcs": 1, "ii": 2, "iii": 3}
    teams, taken = {}, {}
    for r in sorted(info_rows, key=lambda r: rank.get(r.get("classification"), 9)):
        tid = r.get("team_id")
        if tid is None:
            continue
        tid = int(tid)
        a = (r.get("abbreviation") or "").strip() or (r.get("school") or str(tid))[:4].upper()
        if a in taken:
            a = f"{a}{tid}"
        taken[a] = tid
        ok = lambda c: isinstance(c, str) and len(c.lstrip("#")) == 6
        conf = r.get("conference") or ""
        teams[tid] = {
            "id": tid, "abbr": a, "school": r.get("school") or a, "mascot": r.get("mascot"),
            "classification": r.get("classification"), "fbs": r.get("classification") == "fbs",
            "conference": conf, "conf_name": CONF_NAME.get(conf, conf), "conf_short": CONF_SHORT.get(conf, conf),
            "color": ("#" + r["color"].lstrip("#")) if ok(r.get("color")) else None,
            "alt_color": ("#" + r["alt_color"].lstrip("#")) if ok(r.get("alt_color")) else None,
            "venue": {"id": r.get("venue_id"), "name": r.get("venue_name"), "city": r.get("city"), "state": r.get("state"),
                      "country": r.get("country_code"), "lat": r.get("latitude"), "lon": r.get("longitude"),
                      "dome": bool(r.get("dome")), "grass": r.get("grass")},
        }
    return teams


# ---------------------------------------------------------------- games

def build_games(sched_rows, scoreboards, teams):
    """The season's games, in kickoff order, with ESPN's scoreboard over the schedule file where it's
    newer (a final the file hasn't caught up to) and for the TV networks."""
    games = []
    for r in sched_rows:
        if r.get("home_id") is None or r.get("away_id") is None or not r.get("start_date"):
            continue
        gid = str(r["game_id"])
        sb = scoreboards.get(gid) or {}
        ko = datetime.fromisoformat(str(r["start_date"]).replace("Z", "+00:00"))
        et = ko.astimezone(ET)
        final = bool(r.get("completed"))
        hp, ap = r.get("home_points"), r.get("away_points")
        if not final and sb.get("completed") and sb.get("home_score") is not None:
            final, hp, ap = True, sb["home_score"], sb["away_score"]
        post = r.get("season_type") == "postseason"
        games.append({
            "game_id": gid, "post": post, "week": int(r.get("week") or 0),
            "kickoff": ko, "gameday": et.date().isoformat(), "gametime": None if r.get("start_time_tbd") else et.strftime("%H:%M"),
            "home": int(r["home_id"]), "away": int(r["away_id"]),
            "final": final and hp is not None and ap is not None,
            "home_score": int(hp) if final and hp is not None else None, "away_score": int(ap) if final and ap is not None else None,
            "neutral": bool(r.get("neutral_site")), "conf_game": bool(r.get("conference_game")),
            "venue_id": r.get("venue_id"), "venue": r.get("venue"),
            "note": (r.get("playoff_bowl_name") if r.get("playoff_round") else None) or r.get("notes"),
            "playoff_round": r.get("playoff_round_name"),
            "networks": sb.get("networks") or None, "sb_city": sb.get("city"), "sb_region": sb.get("region"),
            "sb_indoor": sb.get("indoor"), "ot_period": sb.get("period"),
        })
    games.sort(key=lambda g: (g["kickoff"], g["game_id"]))
    return games


def week_key(g):
    return POST_KEY if g["post"] else str(g["week"])


# Neutral sites that aren't a school's stadium, by name: the NFL's stadiums and international venues
# (stadiums.py), and the college-only ones the season openers, rivalry games and bowls use. "indoor" for a
# dome or a retractable roof (no way to know if it's open).
NEUTRAL_EXTRA = [
    {"name": "Aviva Stadium", "city": "Dublin", "region": "Ireland", "lat": 53.3352, "lon": -6.2285, "roof": "outdoor"},
    {"name": "Camping World Stadium", "city": "Orlando", "state": "FL", "lat": 28.5392, "lon": -81.4029, "roof": "outdoor"},
    {"name": "Cotton Bowl Stadium", "city": "Dallas", "state": "TX", "lat": 32.7795, "lon": -96.7593, "roof": "outdoor"},
    {"name": "Alamodome", "city": "San Antonio", "state": "TX", "lat": 29.4170, "lon": -98.4789, "roof": "dome"},
    {"name": "Protective Stadium", "city": "Birmingham", "state": "AL", "lat": 33.5241, "lon": -86.8130, "roof": "outdoor"},
    {"name": "Yankee Stadium", "city": "Bronx", "state": "NY", "lat": 40.8296, "lon": -73.9262, "roof": "outdoor"},
    {"name": "Fenway Park", "city": "Boston", "state": "MA", "lat": 42.3467, "lon": -71.0972, "roof": "outdoor"},
    {"name": "Independence Stadium", "city": "Shreveport", "state": "LA", "lat": 32.4747, "lon": -93.7920, "roof": "outdoor"},
    {"name": "State Farm Stadium", "city": "Glendale", "state": "AZ", "lat": 33.5276, "lon": -112.2626, "roof": "retractable"},
    {"name": "Mercedes-Benz Stadium", "city": "Atlanta", "state": "GA", "lat": 33.7554, "lon": -84.4008, "roof": "retractable"},
    {"name": "Wrigley Field", "city": "Chicago", "state": "IL", "lat": 41.9484, "lon": -87.6553, "roof": "outdoor"},
]
NEUTRAL_BY_NAME = {v["name"].lower(): v for v in list(STADIUMS.values()) + list(NEUTRAL_VENUES.values()) + NEUTRAL_EXTRA}
NEUTRAL_BY_NAME["cotton bowl"] = NEUTRAL_BY_NAME["cotton bowl stadium"]   # how the schedule names it


def venue_of(g, teams, venues_by_id):
    """{name, city, region (state's full name), state, lat, lon, indoor, surface, neutral} for where it's played:
    the home team's stadium, or for a neutral site any school stadium with that venue id, else the
    scoreboard's city (no location -- no weather)."""
    home = teams.get(g["home"]) or {}
    v = (home.get("venue") or {}) if not g["neutral"] else (venues_by_id.get(g["venue_id"]) or {})
    if g["neutral"] and not v:
        n = NEUTRAL_BY_NAME.get(re.sub(r"\s*\([^)]*\)$", "", g["venue"] or "").lower())
        if n:
            v = {"name": n["name"], "city": n["city"], "state": n.get("state"), "lat": n["lat"], "lon": n["lon"],
                 "dome": n.get("roof") in ("dome", "retractable"), "grass": None,
                 "country": "US" if n.get("state") else n.get("region")}
    city, state = v.get("city"), v.get("state")
    if g["neutral"] and not v:
        city, state = g["sb_city"], g["sb_region"]
    indoor = bool(v.get("dome")) if v else bool(g["sb_indoor"])
    grass = v.get("grass") if v else None
    name = re.sub(r"\s*\([^)]*\)$", "", g["venue"] or v.get("name") or "") or None   # "Memorial Stadium (Bloomington, IN)"
    return {"name": name, "city": city, "state": state,
            "region": STATE_NAMES.get(state, state) or (v.get("country") if v.get("country") not in (None, "US", "USA") else None), "us": (v.get("country") in (None, "US", "USA")) if v else True,
            "lat": v.get("lat"), "lon": v.get("lon"), "indoor": indoor,
            "surface": None if grass is None else ("Grass" if grass else "Artificial Turf"), "neutral": g["neutral"]}


# ---------------------------------------------------------------- polls

def load_polls(season, now, snap, warnings):
    """{poll week: {"ranks": {team_id: rank}, "others": [team_id]}} for every AP poll so far, and the latest
    week. Past weeks come from the snapshot when it has them (they never change)."""
    ap_now = now.get("ap")
    latest = int(ap_now["week"]) if ap_now and ap_now.get("week") else 0
    cached = (snap.get("polls") or {}) if snap.get("season") == season else {}
    polls = {}
    for w in range(1, latest + 1):
        if w == latest and ap_now:
            polls[w] = {"ranks": {int(e["team_id"]): e["current"] for e in ap_now["ranks"]},
                        "others": [int(e["team_id"]) for e in ap_now["others"]]}
            continue
        c = cached.get(str(w))
        if c is None:
            c, err = cc.get_ap_poll(season, w)
            if err:
                if w > 1:   # ESPN has no "Week 1" poll after the preseason one in some years -- not worth a warning
                    warnings.append(err)
                continue
        polls[w] = {"ranks": {int(k): v for k, v in c["ranks"].items()}, "others": [int(x) for x in c["others"]]}
    return polls, latest


def poll_for(polls, week):
    """The AP poll that came out before `week`'s games (the latest one for later weeks and the postseason)."""
    ws = [w for w in polls if w <= week]
    return polls[max(ws)] if ws else (polls[min(polls)] if polls else {"ranks": {}, "others": []})


# ---------------------------------------------------------------- box scores

def box_value(row, cat, i, col):
    v = row.get(col) if col else None
    if v is None:
        v = row.get(f"stat_{i + 1}")
    return v


def build_player_rows(pbox, rosters, games_by_id, pbp_extra):
    """(player_weeks {team_id: [row]}, game_lines {(game_id, team_id): [row]}) in player_stats.py's keys.
    player_weeks: regular season only (a row a player and week), like the NFL's."""
    pos = {}
    for r in rosters:
        if r.get("athlete_id") is not None:
            pos[int(r["athlete_id"])] = (r.get("position_abbreviation") or "", r.get("jersey"))
    lines = {}   # (game_id, team_id, athlete_id) -> row
    for r in pbox:
        cat = r.get("category")
        if cat not in BOX or r.get("athlete_id") is None or r.get("team_id") is None:
            continue
        gid = str(r.get("game_id"))
        g = games_by_id.get(gid)
        if not g:
            continue
        aid, tid = int(r["athlete_id"]), int(r["team_id"])
        key = (gid, tid, aid)
        row = lines.get(key)
        if row is None:
            p, jersey = pos.get(aid, ("", None))
            row = lines[key] = {"id": str(aid), "name": r.get("athlete_name") or "", "pos": p,
                                "wk": g["week"], "post": g["post"]}
            j = num(r.get("jersey") or jersey)
            if j or str(r.get("jersey") or "") == "0":
                row["jersey"] = j
        for i, (col, out) in enumerate(BOX[cat]):
            if out is None:
                continue
            v = box_value(r, cat, i, col)
            if v is None:
                continue
            if isinstance(out, tuple):
                parts = str(v).replace("-", "/").split("/")
                if len(parts) == 2:
                    for k, x in zip(out, parts):
                        row[k] = row.get(k, 0) + num(x)
            else:
                x = num(v)
                row[out] = max(row.get(out, 0), x) if out in MAX_KEYS else row.get(out, 0) + x
    for (gid, tid, aid), row in lines.items():
        tot = row.pop("_tot", 0)
        if tot:
            row["ast"] = max(0, tot - row.get("solo", 0))
        for k, v in (pbp_extra.get((gid, aid)) or {}).items():
            row[k] = row.get(k, 0) + v
    # the team's sacks taken that game go to its passer with the most attempts (ESPN's college box score
    # has no sacks line, and the play-by-play's passer ids are missing for whole teams)
    for (gid, tid), sk in (pbp_extra.get("_sacks") or {}).items():
        qbs = [row for (g2, t2, _a), row in lines.items() if g2 == gid and t2 == tid and row.get("att")]
        if qbs:
            top = max(qbs, key=lambda r: r["att"])
            top["sk"] = top.get("sk", 0) + sk
    player_weeks, game_lines = defaultdict(list), defaultdict(list)
    for (gid, tid, _aid), row in lines.items():
        game_lines[(gid, tid)].append(row)
        if not row["post"]:
            player_weeks[tid].append({k: v for k, v in row.items() if k != "post"})
    for rows in player_weeks.values():
        rows.sort(key=lambda r: r["wk"])
    return player_weeks, game_lines


def build_pbp_extras(pbp, school_ids):
    """From the play-by-play, what the box score lacks: targets and forced fumbles a player a game
    {(game_id, athlete_id): {"tgt", "ff"}}, and each team's sacks taken a game under "_sacks"."""
    import polars as pl
    out = defaultdict(lambda: defaultdict(int))
    if pbp is None:
        return out
    f0 = lambda c: pl.col(c).cast(pl.Float64).fill_null(0)
    p = pbp.with_columns(pl.col("game_id").cast(pl.String).alias("gid"))
    tg = (p.filter((f0("pass") > 0) & (f0("sack") == 0))
          .with_columns(pl.coalesce(pl.col("reception_player_id"), pl.col("target_player_id")).cast(pl.Int64).alias("aid"))
          .filter(pl.col("aid").is_not_null()).group_by("gid", "aid").agg(pl.len().alias("n")))
    for r in tg.iter_rows(named=True):
        out[(r["gid"], r["aid"])]["tgt"] += r["n"]
    ff = (p.filter(pl.col("fumble_forced_player_id").is_not_null())
          .with_columns(pl.col("fumble_forced_player_id").cast(pl.Int64).alias("aid")).group_by("gid", "aid").agg(pl.len().alias("n")))
    for r in ff.iter_rows(named=True):
        out[(r["gid"], r["aid"])]["ff"] += r["n"]
    sk = (p.filter(f0("sack") > 0).with_columns(pl.col("pos_team").replace_strict(school_ids, default=None).alias("tid"))
          .filter(pl.col("tid").is_not_null()).group_by("gid", "tid").agg(pl.len().alias("n")))
    out["_sacks"] = {(r["gid"], int(r["tid"])): r["n"] for r in sk.iter_rows(named=True)}
    return out


def build_team_games(tbox):
    """{(game_id, team_id): {...}} from ESPN's team box score, each side with its opponent's numbers too."""
    by_game = defaultdict(list)
    for r in tbox:
        if r.get("team_id") is not None:
            by_game[str(r.get("game_id"))].append(r)
    out = {}

    def parse(r):
        def pair(v, sep="-"):
            try:
                a, b = str(v).replace("/", "-").split("-")[:2]
                return num(a), num(b)
            except (ValueError, AttributeError):
                return None, None
        comp, att = pair(r.get("completionAttempts"))
        third_c, third_a = pair(r.get("thirdDownEff"))
        pens, pen_yds = pair(r.get("totalPenaltiesYards"))
        rush_att = num(r.get("rushingAttempts"))
        top = str(r.get("possessionTime") or "")
        try:
            mm, ss = top.split(":")
            top_s = int(mm) * 60 + int(ss)
        except ValueError:
            top_s = None
        return {"yards": num(r.get("totalYards")), "pass_yards": num(r.get("netPassingYards")),
                "rush_yards": num(r.get("rushingYards")), "plays": (att or 0) + rush_att,
                "first_downs": num(r.get("firstDowns")), "third_conv": third_c, "third_att": third_a,
                "penalties": pens, "penalty_yards": pen_yds, "turnovers": num(r.get("turnovers")), "top_s": top_s}
    for gid, rows in by_game.items():
        if len(rows) != 2:
            continue
        a, b = parse(rows[0]), parse(rows[1])
        out[(gid, int(rows[0]["team_id"]))] = {"us": a, "them": b}
        out[(gid, int(rows[1]["team_id"]))] = {"us": b, "them": a}
    return out


def build_linescores(rows):
    """{game_id: {team_id: [points by period]}}."""
    out = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        if r.get("team_id") is None or r.get("period") is None:
            continue
        out[str(r["game_id"])][int(r["team_id"])][int(r["period"])] = num(r.get("value"))
    return {gid: {t: [p[k] for k in sorted(p)] for t, p in by_team.items()} for gid, by_team in out.items()}


# ---------------------------------------------------------------- ranks and stats (season to date)

def competition_ranks(values, higher_better=True):
    """{team: value} -> {team: rank}, 1 = best, ties share."""
    order = sorted(values.items(), key=lambda kv: kv[1], reverse=higher_better)
    out, prev, rank = {}, None, 0
    for i, (t, v) in enumerate(order, 1):
        rank = rank if v == prev else i
        out[t], prev = rank, v
    return out


class SeasonStats:
    """Each FBS team's numbers over the regular-season weeks before a given week, cached by week:
    the Page 1 ranks, the Team Stats card, the leaders and their crowns."""

    def __init__(self, games, team_games, player_weeks, teams):
        self.games = [g for g in games if g["final"] and not g["post"]]
        self.team_games = team_games
        self.player_weeks = player_weeks
        self.fbs = {t for t, v in teams.items() if v["fbs"]}
        self._cache = {}

    def through(self, week):
        """week None = the whole regular season."""
        key = week
        if key in self._cache:
            return self._cache[key]
        tot = defaultdict(lambda: defaultdict(float))
        for g in self.games:
            if week is not None and g["week"] >= week:
                continue
            for me, opp, pf, pa in ((g["home"], g["away"], g["home_score"], g["away_score"]),
                                    (g["away"], g["home"], g["away_score"], g["home_score"])):
                t = tot[me]
                t["games"] += 1
                t["pf"] += pf
                t["pa"] += pa
                tg = self.team_games.get((g["game_id"], me))
                if tg:
                    us, them = tg["us"], tg["them"]
                    t["box"] += 1
                    for k in ("yards", "pass_yards", "rush_yards", "third_conv", "third_att", "turnovers"):
                        t["o_" + k] += us.get(k) or 0
                        t["d_" + k] += them.get(k) or 0
                    if us.get("top_s"):
                        t["top_s"] += us["top_s"]
                        t["top_n"] += 1
        # touchdowns, sacks and interceptions from the player lines, each with what the opponents did
        opp_of = {}
        for g in self.games:
            opp_of[(g["home"], g["week"])], opp_of[(g["away"], g["week"])] = g["away"], g["home"]
        for team, rows in self.player_weeks.items():
            for r in rows:
                if week is not None and r["wk"] >= week:
                    continue
                for k, src in (("ptd", "ptd"), ("rtd", "rtd"), ("dsk", "dsk"), ("dint", "dint")):
                    if r.get(src):
                        tot[team]["o_" + k] += r[src]
                        opp = opp_of.get((team, r["wk"]))
                        if opp is not None:
                            tot[opp]["d_" + k] += r[src]
        per = {t: v for t, v in tot.items() if t in self.fbs and v["games"]}
        pg = lambda v, k, n="games": v[k] / v[n] if v[n] else None
        vals = {
            "off_points": {t: pg(v, "pf") for t, v in per.items()}, "def_points": {t: pg(v, "pa") for t, v in per.items()},
            "off_yards": {t: pg(v, "o_yards", "box") for t, v in per.items() if v["box"]},
            "def_yards": {t: pg(v, "d_yards", "box") for t, v in per.items() if v["box"]},
            "off_pass": {t: pg(v, "o_pass_yards", "box") for t, v in per.items() if v["box"]},
            "def_pass": {t: pg(v, "d_pass_yards", "box") for t, v in per.items() if v["box"]},
            "off_rush": {t: pg(v, "o_rush_yards", "box") for t, v in per.items() if v["box"]},
            "def_rush": {t: pg(v, "d_rush_yards", "box") for t, v in per.items() if v["box"]},
            "off_ptd": {t: v["o_ptd"] for t, v in per.items()}, "def_ptd": {t: v["d_ptd"] for t, v in per.items()},
            "off_rtd": {t: v["o_rtd"] for t, v in per.items()}, "def_rtd": {t: v["d_rtd"] for t, v in per.items()},
            "off_3rd": {t: v["o_third_conv"] / v["o_third_att"] * 100 for t, v in per.items() if v["o_third_att"]},
            "def_3rd": {t: v["d_third_conv"] / v["d_third_att"] * 100 for t, v in per.items() if v["d_third_att"]},
            "to_margin": {t: v["d_turnovers"] - v["o_turnovers"] for t, v in per.items() if v["box"]},
            "sacks": {t: v["o_dsk"] for t, v in per.items()}, "ints": {t: v["o_dint"] for t, v in per.items()},
        }
        # offense: more is better; defense: less is better (what it allowed)
        better_low = {"def_points", "def_yards", "def_pass", "def_rush", "def_ptd", "def_rtd", "def_3rd"}
        ranks = {k: competition_ranks({t: x for t, x in v.items() if x is not None}, k not in better_low)
                 for k, v in vals.items()}
        out = {"vals": vals, "ranks": ranks, "n": len(per)}
        self._cache[key] = out
        return out

    def page1_ranks(self, team, week):
        r = self.through(week)["ranks"]
        return {k: r[k].get(team) for k in ("off_points", "off_yards", "def_points", "def_yards")} if team in self.fbs else {}

    def team_stats(self, team, week):
        """render_page2team's Team Stats card: offense / defense pairs, then the singles."""
        s = self.through(week)
        v, r = s["vals"], s["ranks"]
        if team not in self.fbs or team not in v["off_points"]:
            return {}
        pair = lambda o, d: {"off_value": v[o].get(team), "off_rank": r[o].get(team),
                             "def_value": v[d].get(team), "def_rank": r[d].get(team)}
        one = lambda k: {"value": v[k].get(team), "rank": r[k].get(team)} if team in v[k] else None
        return {"points": pair("off_points", "def_points"), "pass_tds": pair("off_ptd", "def_ptd"),
                "rush_tds": pair("off_rtd", "def_rtd"), "all_yards": pair("off_yards", "def_yards"),
                "pass_yards": pair("off_pass", "def_pass"), "rush_yards": pair("off_rush", "def_rush"),
                "third_down_pct": pair("off_3rd", "def_3rd"), "top": None,
                "turnover_margin": one("to_margin"), "sacks": one("sacks"), "def_ints": one("ints")}


class Leaders:
    """Season leaders before a week (with league crowns among every FBS player), and a game's own."""

    def __init__(self, player_weeks, game_lines, fbs):
        self.pw = {t: rows for t, rows in player_weeks.items() if t in fbs}
        self.game_lines = game_lines
        self._cache = {}

    def _totals(self, week):
        if week in self._cache:
            return self._cache[week]
        tot = defaultdict(lambda: defaultdict(float))
        info = {}
        for team, rows in self.pw.items():
            for r in rows:
                if week is not None and r["wk"] >= week:
                    continue
                k = (team, r["id"])
                info[k] = r
                for s, v in r.items():
                    if isinstance(v, (int, float)) and s not in ("wk", "jersey"):
                        tot[k][s] += v
        crowns = {}
        for _key, _lbl, stat in LEADER_STATS:
            vals = sorted(((v[stat], k) for k, v in tot.items() if v.get(stat, 0) > 0), reverse=True)
            for i, (x, k) in enumerate(vals):
                place = 1 + sum(1 for y, _ in vals[:i] if y > x)
                if place > 3:
                    break
                crowns[(stat, k)] = place
        out = (tot, info, crowns)
        self._cache[week] = out
        return out

    @staticmethod
    def _entry(stat, r, value, rank):
        extra = {k: int(r.get(src) or 0) for k, src in LEADER_EXTRAS.get(stat, {}).items()}
        e = {"name": names.short_name(r["name"]), "full_name": r["name"], "position": r.get("pos") or "",
             "value": value, "league_rank": rank}
        if extra:
            e["extra"] = extra
        return e

    def season(self, team, week):
        tot, info, crowns = self._totals(week)
        out = {}
        for key, _lbl, stat in LEADER_STATS:
            best = max(((v.get(stat, 0), k) for k, v in tot.items() if k[0] == team and v.get(stat, 0) > 0), default=None)
            if best:
                k = best[1]
                out[key] = self._entry(stat, dict(info[k], **tot[k]), best[0], crowns.get((stat, k)))
        return out

    def game(self, gid, team):
        out = {}
        rows = self.game_lines.get((gid, team)) or []
        for key, _lbl, stat in LEADER_STATS:
            best = max(rows, key=lambda r: r.get(stat, 0), default=None)
            if best and best.get(stat, 0) > 0:
                out[key] = self._entry(stat, best, best[stat], None)
        return out


# ---------------------------------------------------------------- weather

def p1_weather(g, v, now, frozen):
    if v["indoor"]:
        return {"available": True, "indoor": True}
    if g["final"]:
        return frozen.get("weather") or {"available": False, "reason": "finished"}
    if v["lat"] is None:
        return {"available": False, "reason": "no venue location"}
    if g["gametime"] is None:
        return {"available": False, "reason": "kickoff time not set"}
    if not (now - timedelta(hours=4) <= g["kickoff"] <= now + timedelta(days=NWS_WINDOW_DAYS)) or not v["us"]:
        return {"available": False, "reason": "outside the NWS 7-day forecast window"}
    w = wx.get_game_window_weather(v["lat"], v["lon"], g["kickoff"])
    if w.get("available"):
        w["source"] = "nws"
    return w


def detail_weather(g, v, now, frozen):
    if v["indoor"]:
        return {"indoor": True}
    if v["lat"] is None or g["gametime"] is None:
        return {"available": False, "reason": "no kickoff time or venue location"}
    if g["final"]:
        if frozen.get("weather_detail"):
            return frozen["weather_detail"]
        w = wx.get_game_window_detail_om(v["lat"], v["lon"], g["kickoff"])
        if w.get("available"):
            w["precip_pct"] = None
        return w
    if not (now - timedelta(hours=4) <= g["kickoff"] <= now + timedelta(days=NWS_WINDOW_DAYS)):
        return {"available": False, "reason": "forecast_window", "window_days": NWS_WINDOW_DAYS}
    if not v["us"]:
        return {"available": False, "reason": "outside the US (no NWS forecast)"}
    return wx.get_game_window_detail_nws(v["lat"], v["lon"], g["kickoff"])


# ---------------------------------------------------------------- the build

def build(season, now=None):
    now = now or datetime.now(timezone.utc)
    warnings = []

    def step(name, fn, default):
        try:
            return fn()
        except Exception:
            warnings.append(f"{name}: {traceback.format_exc(limit=2)}")
            return default

    def fetch(name, result):
        value, err = result
        if err:
            warnings.append(f"{name}: {err}")
        return value

    snap = load_snapshot(warnings)
    snap = snap if snap.get("season") == season else {"season": season}

    info_rows = fetch("team info", cc.get_team_info(season))
    teams = build_teams(info_rows)
    if not teams:
        raise SystemExit("build_cfb_data: no team info -- nothing to build")
    abbr = lambda tid: (teams.get(tid) or {}).get("abbr") or str(tid)
    sched = fetch("schedule", cc.get_schedule(season))
    if not sched:
        raise SystemExit("build_cfb_data: no schedule -- nothing to build")

    # which regular-season week we're in: the first with a game still ahead (a game never played -- a
    # cancellation -- stays "not completed" forever, so an unfinished game alone doesn't count)
    reg = [r for r in sched if r.get("season_type") == "regular" and r.get("home_id") is not None]
    ahead = lambda r: datetime.fromisoformat(str(r["start_date"]).replace("Z", "+00:00")) > now - timedelta(hours=12)
    open_weeks = sorted({int(r["week"]) for r in reg if not r.get("completed") and r.get("start_date") and ahead(r)})
    cur_week = open_weeks[0] if open_weeks else max((int(r["week"]) for r in reg), default=1)
    # ESPN's scoreboard: the weeks around this one every build (finals, TV, kickoff times); earlier weeks
    # once, for their TV networks, kept in the snapshot from then on
    scoreboards = {}
    tv_cache = dict(snap.get("tv") or {})
    done_weeks = set(snap.get("tv_weeks") or [])
    for w in range(1, cur_week + 2):
        if w >= cur_week - 1 or w not in done_weeks:
            sb = fetch(f"scoreboard week {w}", cc.get_scoreboard(season, w)) or {}
            scoreboards.update(sb)
            if sb and w < cur_week - 1:
                done_weeks.add(w)
    for gid, nets in tv_cache.items():
        scoreboards.setdefault(gid, {"networks": nets})
    for gid, sb in scoreboards.items():
        if sb.get("networks"):
            tv_cache[gid] = sb["networks"]
    if not open_weeks and any(r.get("season_type") == "postseason" for r in sched):
        scoreboards.update(fetch("scoreboard postseason", cc.get_scoreboard(season, 1, 3)) or {})

    games = build_games(sched, scoreboards, teams)
    by_id = {g["game_id"]: g for g in games}
    venues_by_id = {}
    for t in teams.values():
        if t["venue"].get("id") is not None and t["venue"].get("lat") is not None:
            venues_by_id.setdefault(t["venue"]["id"], t["venue"])

    rankings_now = fetch("rankings", cc.get_rankings_now()) or {}
    polls, latest_poll = load_polls(season, rankings_now, snap, warnings)
    if not polls:
        warnings.append("no AP polls -- no poll teams, so no games")

    # each week's poll teams and their ranks
    week_keys = []
    for g in games:
        k = week_key(g)
        if k not in week_keys:
            week_keys.append(k)
    week_keys = sorted({k for k in week_keys if k != POST_KEY}, key=int) + ([POST_KEY] if POST_KEY in week_keys else [])
    poll_by_key = {k: poll_for(polls, 99 if k == POST_KEY else int(k)) for k in week_keys}
    tracked = {k: set(p["ranks"]) | set(p["others"]) for k, p in poll_by_key.items()}
    shown = [g for g in games if (g["home"] in tracked[week_key(g)] or g["away"] in tracked[week_key(g)])
             and teams.get(g["home"]) and teams.get(g["away"])]

    # results in order, for records, streaks and conference records
    results = defaultdict(list)   # team -> [(game, "W"/"L", pf, pa)]
    for g in games:
        if g["final"]:
            for me, pf, pa in ((g["home"], g["home_score"], g["away_score"]), (g["away"], g["away_score"], g["home_score"])):
                results[me].append((g, "W" if pf > pa else "L" if pf < pa else "T", pf, pa))

    def record(team, before=None, through=None, conf_only=False):
        w = l = t = 0
        last, streak = None, 0
        for g, res, _pf, _pa in results.get(team, []):
            if before is not None and g["kickoff"] >= before:
                break
            if not conf_only or g["conf_game"]:
                w, l, t = w + (res == "W"), l + (res == "L"), t + (res == "T")
                streak = streak + 1 if res == last else 1
                last = res
            if through is not None and g["game_id"] == through:
                break
        return {"wins": w, "losses": l, "ties": t}, last, streak

    team_games = step("team box", lambda: build_team_games(fetch("team box", cc.get_team_box(season)) or []), {})
    linescores = step("linescores", lambda: build_linescores(fetch("linescores", cc.get_linescores(season)) or []), {})
    pbp = fetch("play-by-play", cc.get_pbp(season))
    school_ids = {}
    for tid, t in sorted(teams.items(), key=lambda kv: not kv[1]["fbs"]):
        school_ids.setdefault(t["school"], tid)
    pbp_extra = step("play-by-play extras", lambda: build_pbp_extras(pbp, school_ids), {})
    rosters = fetch("rosters", cc.get_rosters(season)) or []
    player_weeks, game_lines = step("player box", lambda: build_player_rows(
        fetch("player box", cc.get_player_box(season)) or [], rosters, by_id, pbp_extra), ({}, {}))
    fbs = {t for t, v in teams.items() if v["fbs"]}
    stats = SeasonStats(games, team_games, player_weeks, teams)
    leaders = Leaders(player_weeks, game_lines, fbs)

    # head coaches, for the teams on the pages (cached a week in the snapshot)
    coaches = dict(snap.get("coaches") or {})
    today = now.date().isoformat()
    for tid in sorted({t for g in shown for t in (g["home"], g["away"]) if t in fbs}):
        c = coaches.get(str(tid))
        if c and c.get("name") and c.get("checked", "") >= (now - timedelta(days=COACH_DAYS)).date().isoformat():
            continue
        name, err = cc.get_head_coach(season, tid)
        if name:
            coaches[str(tid)] = {"name": name, "checked": today}
        elif not c:
            warnings.append(f"head coach {abbr(tid)}: {err}")

    # last meetings, from earlier seasons and this one
    history = fetch("schedule history", cc.get_schedule_history(season)) or []
    meetings = defaultdict(list)
    for r in history:
        h, a = int(r["home_id"]), int(r["away_id"])
        meetings[frozenset((h, a))].append((str(r["start_date"]), {"date": str(r["start_date"])[:10], "season": r["season"],
                                                                   "score": {abbr(h): int(r["home_points"]), abbr(a): int(r["away_points"])}}))
    for g in games:
        if g["final"]:
            meetings[frozenset((g["home"], g["away"]))].append((g["kickoff"].isoformat(), {
                "date": g["gameday"], "season": season, "score": {abbr(g["home"]): g["home_score"], abbr(g["away"]): g["away_score"]}}))
    for v in meetings.values():
        v.sort(key=lambda x: x[0])

    def last_meeting(g):
        best = None
        for key, m in meetings.get(frozenset((g["home"], g["away"])), []):
            if key < g["kickoff"].isoformat() and m["date"] != g["gameday"]:
                best = m
        return best

    # each team's season: schedule rows (with byes), conference standings, byes
    team_sched = defaultdict(list)
    for g in games:
        if not g["post"]:
            team_sched[g["home"]].append(g)
            team_sched[g["away"]].append(g)
    reg_weeks = sorted({g["week"] for g in games if not g["post"]})

    sched_cache = {}

    def schedule_rows(team):
        if team not in sched_cache:
            sched_cache[team] = _schedule_rows(team)
        return sched_cache[team]

    def _schedule_rows(team):
        rows, by_week = [], {g["week"]: g for g in team_sched.get(team, [])}
        first, last = (min(by_week), max(by_week)) if by_week else (0, -1)
        for w in reg_weeks:
            if w < first or w > last:
                continue
            g = by_week.get(w)
            if not g:
                rows.append({"week": w, "bye": True})
                continue
            home = g["home"] == team
            opp = g["away"] if home else g["home"]
            sc = None
            if g["final"]:
                mine, theirs = (g["home_score"], g["away_score"]) if home else (g["away_score"], g["home_score"])
                sc = {"team": mine, "opp": theirs}
            rows.append({"week": w, "bye": False, "opponent": abbr(opp), "home": home or g["neutral"], "neutral": g["neutral"],
                         "gameday": g["gameday"], "gametime": g["gametime"], "game_id": g["game_id"], "final": g["final"],
                         "score": sc, "result": (None if not sc else "W" if sc["team"] > sc["opp"] else "L" if sc["team"] < sc["opp"] else "T"),
                         "record_after": record(team, through=g["game_id"])[0] if g["final"] else record(team, before=g["kickoff"])[0]})
        return rows

    def standings(team, before):
        conf = (teams.get(team) or {}).get("conference")
        if not conf or conf == "FBS Independents":
            return None
        rows = []
        for tid, t in teams.items():
            if t["conference"] == conf and t["fbs"]:
                cr = record(tid, before=before, conf_only=True)[0]
                ov = record(tid, before=before)[0]
                gp = cr["wins"] + cr["losses"]
                rows.append({"team": t["abbr"], "wins": cr["wins"], "losses": cr["losses"], "ties": 0,
                             "pct": cr["wins"] / gp if gp else 0.0, "overall": ov})
        rows.sort(key=lambda r: (-r["pct"], -r["wins"], r["losses"], -r["overall"]["wins"], r["team"]))
        return {"division": (teams.get(team) or {}).get("conf_name") or conf, "rows": rows}

    def bye_week(team, week):
        sched_rows = schedule_rows(team)
        byes = [r["week"] for r in sched_rows if r.get("bye")]
        nxt = [w for w in byes if w >= week]
        return (nxt or byes[-1:] or [None])[0]

    def rest_days(team, g):
        prev = [x for x in team_sched.get(team, []) if x["kickoff"] < g["kickoff"]]
        if not prev:
            return None
        return (datetime.fromisoformat(g["gameday"]) - datetime.fromisoformat(prev[-1]["gameday"])).days

    def trend(team, week):
        return [[w, (polls[w]["ranks"].get(team) or ("RV" if team in polls[w]["others"] else None))]
                for w in sorted(polls) if w <= week]

    # weather: finished games without a frozen one get Open-Meteo, a request or two a venue
    frozen_games = dict(snap.get("games") or {})
    venues = {g["game_id"]: venue_of(g, teams, venues_by_id) for g in shown}
    need = defaultdict(list)
    for g in shown:
        v = venues[g["game_id"]]
        if g["final"] and not v["indoor"] and v["lat"] is not None and g["gametime"] and not (frozen_games.get(g["game_id"]) or {}).get("weather_detail"):
            need[(v["lat"], v["lon"])].append(g["kickoff"])
    errs = []
    for (lat, lon), kos in need.items():
        errs += wx.prefetch_open_meteo(lat, lon, kos, now)
    if errs:
        warnings.append(f"weather: {len(errs)} Open-Meteo request(s) failed, first: {errs[0]}")

    # ---------------------------------------------------------------- each game
    details, new_frozen = {}, {}
    for g in shown:
        gid, k = g["game_id"], week_key(g)
        try:
            poll = poll_by_key[k]
            week = None if g["post"] else g["week"]
            poll_week = max([w for w in polls if w <= (week or 99)], default=None)
            v = venues[gid]
            fz = frozen_games.get(gid) or {}
            w1 = p1_weather(g, v, now, fz)
            w2 = detail_weather(g, v, now, fz)
            if g["final"] and not (w1 or {}).get("available") and (w2 or {}).get("available"):
                w1 = _p1_weather_from_detail(w2)
            keep = {"weather": w1 if (w1 or {}).get("available") else fz.get("weather"),
                    "weather_detail": w2 if (w2 or {}).get("available") else fz.get("weather_detail")}
            keep = {a: b for a, b in keep.items() if b}
            if keep:
                new_frozen[gid] = keep

            def side(team, opp, home):
                if g["final"]:
                    rec, last, streak = record(team, through=gid)
                    crec = record(team, through=gid, conf_only=True)[0]
                else:
                    rec, last, streak = record(team, before=g["kickoff"])
                    crec = record(team, before=g["kickoff"], conf_only=True)[0]
                t = teams[team]
                tg = (team_games.get((gid, team)) or {}).get("us") if g["final"] else None
                game_stats = None
                if tg:
                    them = team_games[(gid, team)]["them"]
                    game_stats = {"yards": tg["yards"], "plays": tg["plays"],
                                  "ypp": tg["yards"] / tg["plays"] if tg["plays"] else None,
                                  "penalties": tg["penalties"], "penalty_yards": tg["penalty_yards"],
                                  "first_downs": tg["first_downs"], "third_conv": tg["third_conv"], "third_att": tg["third_att"],
                                  "turnover_diff": (them["turnovers"] or 0) - (tg["turnovers"] or 0)}
                home_v = (t.get("venue") or {})
                miles = haversine_miles(home_v.get("lat"), home_v.get("lon"), v["lat"], v["lon"]) if not (home and not g["neutral"]) else 0
                coach = (coaches.get(str(team)) or {}).get("name")
                return {
                    "team": t["abbr"], "record": rec, "last": last, "streak": streak,
                    "injuries": [], "injury_report_out": False, "game_absences": None,
                    "game_stats": game_stats,
                    "ranks": stats.page1_ranks(team, week),
                    "rank": poll["ranks"].get(team), "trend": trend(team, poll_week or 0),
                    "conf": {"name": t["conf_name"], "short": t["conf_short"],
                             "rec": None if t["conference"] in ("FBS Independents", "") or not t["fbs"] else crec},
                    "team_page": {
                        "injuries_full": [],
                        "stats": stats.team_stats(team, week),
                        "schedule": schedule_rows(team),
                        "standings": standings(team, g["kickoff"]),
                        "coaches": {"head_coach": coach, "off_caller": None, "def_caller": None} if coach else None,
                        "next": {"opponent": abbr(opp), "gameday": g["gameday"], "gametime": g["gametime"],
                                 "rest_days": rest_days(team, g), "bye_week": bye_week(team, g["week"] if not g["post"] else 99),
                                 "miles_traveled": None if miles is None else round(miles)},
                    },
                }

            away, home = side(g["away"], g["home"], False), side(g["home"], g["away"], True)
            game_scope = False
            if g["final"]:
                gl = {g["away"]: leaders.game(gid, g["away"]), g["home"]: leaders.game(gid, g["home"])}
                game_scope = any(gl.values())
            sl = {g["away"]: leaders.season(g["away"], week), g["home"]: leaders.season(g["home"], week)}
            pick = (lambda key, t: gl[t].get(key)) if game_scope else (lambda key, t: sl[t].get(key))
            ls = linescores.get(gid) or {}
            linescore = None
            if g["final"] and ls.get(g["away"]) and ls.get(g["home"]):
                n = max(len(ls[g["away"]]), len(ls[g["home"]]))
                labels = [str(i) if i <= 4 else ("OT" if i == 5 else f"{i - 4}OT") for i in range(1, n + 1)]
                pad = lambda xs: xs + [0] * (n - len(xs))
                linescore = {"labels": labels, "away": pad(ls[g["away"]]), "home": pad(ls[g["home"]])}
            overtime = bool(linescore and len(linescore["labels"]) > 4)
            key_label = (POST_KEY, POST_LABEL) if g["post"] else (str(g["week"]), f"Week {g['week']}")
            details[gid] = {
                "game_id": gid, "game_type": "POST" if g["post"] else "REG", "week": g["week"],
                "week_key": key_label[0], "week_label": key_label[1],
                "gameday": g["gameday"], "gametime": g["gametime"], "final": g["final"], "overtime": overtime,
                "score": {"away": g["away_score"], "home": g["home_score"]} if g["final"] else None,
                "linescore": linescore, "networks": g["networks"] or {"status": "pending"},
                "neutral": g["neutral"], "note": g["note"], "playoff_round": g["playoff_round"],
                "venue": {"city": ", ".join(x for x in (v["city"], v["state"]) if x) or None, "stadium": v["name"],
                          "indoor": v["indoor"], "neutral": g["neutral"]},
                "weather": w1, "stats_through_week": (g["week"] - 1) if not g["post"] else "regular season",
                "away": away, "home": home,
                "leaders_scope": "game" if game_scope else "season",
                "leaders": [{"key": key, "label": lbl, "away": pick(key, g["away"]), "home": pick(key, g["home"])}
                            for key, lbl, _s in LEADER_STATS],
                "info": {
                    "kickoff_utc": g["kickoff"].strftime("%Y-%m-%dT%H:%M:00Z") if g["gametime"] else None,
                    "referee": None, "last_meeting": last_meeting(g),
                    "networks": g["networks"] or {"status": "pending"}, "broadcasters": [],
                    "stadium": {"name": v["name"], "city": v["city"], "region": v["region"],
                                "roof_type": "dome" if v["indoor"] else "outdoor", "roof_status": None,
                                "surface": v["surface"], "neutral": g["neutral"]},
                    "weather": w2,
                },
            }
        except Exception:
            warnings.append(f"game {gid}: {traceback.format_exc(limit=2)}")

    # ---------------------------------------------------------------- Page 0 weeks
    season_weeks = []
    for k in week_keys:
        if not any(week_key(g) == k and g["game_id"] in details for g in shown):
            continue   # no poll team plays that week (yet): conference title games are added once they're set
        wk_games = []
        for g in shown:
            if week_key(g) != k or g["game_id"] not in details:
                continue
            d = details[g["game_id"]]
            wk_games.append({"game_id": g["game_id"], "game_type": d["game_type"], "week": g["week"],
                             "gameday": g["gameday"], "gametime": g["gametime"], "final": g["final"],
                             "overtime": d["overtime"], "networks": g["networks"], "neutral": g["neutral"], "note": g["note"],
                             "away": {"team": abbr(g["away"]), "record": d["away"]["record"], "score": g["away_score"],
                                      "rank": d["away"]["rank"]},
                             "home": {"team": abbr(g["home"]), "record": d["home"]["record"], "score": g["home_score"],
                                      "rank": d["home"]["rank"]}})
        p = poll_by_key[k]
        season_weeks.append({"key": k, "label": POST_LABEL if k == POST_KEY else f"Week {k}",
                             "game_type": "POST" if k == POST_KEY else "REG", "games": wk_games,
                             "tracked": sorted(abbr(t) for t in tracked[k]),
                             "ranks": {abbr(t): r for t, r in p["ranks"].items()}})
    # the week Page 0 opens on: the first with a poll-team game still to play, else the last
    current = next((w["key"] for w in season_weeks if any(not g["final"] for g in w["games"])),
                   season_weeks[-1]["key"] if season_weeks else None)

    # ---------------------------------------------------------------- the rest
    def rank_payload(p):
        if not p:
            return None

        def entry(e):
            tid = int(e["team_id"])
            t = teams.get(tid) or {}
            rec = record(tid)[0]
            return {"team": abbr(tid), "school": e.get("location") or t.get("school") or abbr(tid),
                    "current": e.get("current"), "previous": e.get("previous"), "points": e.get("points"),
                    "first_place_votes": e.get("first_place_votes"), "record": rec,
                    "conf": t.get("conf_short") or ""}
        return {"name": p["name"], "week": p.get("week"), "date": p.get("date"),
                "ranks": [entry(e) for e in p["ranks"]], "others": [entry(e) for e in p["others"]],
                "dropped": [entry(e) for e in p["dropped"]]}

    dvp = fetch("defense vs position", cc.get_defense_vs_position(season)) or []
    matchup_weeks, defense = step("matchups", lambda: matchup_inputs(pbp, teams, school_ids, cur_week, rosters, dvp), ({}, {}))
    pw_out = {abbr(t): rows for t, rows in player_weeks.items() if t in fbs}
    on_pages = {t for g in shown for t in (g["home"], g["away"])} | {
        int(e["team_id"]) for p in rankings_now.values() for e in p["ranks"] + p["others"] + p["dropped"]}
    on_pages |= fbs   # Stat Leaders ranks every FBS player, each with his team's pill
    team_out = {abbr(t): {"id": t, "school": teams[t]["school"], "conference": teams[t]["conf_name"], "conf_short": teams[t]["conf_short"],
                          "fbs": teams[t]["fbs"], "color": teams[t]["color"], "alt_color": teams[t]["alt_color"]}
                for t in on_pages if t in teams}
    for g in shown:   # every opponent on a page or a team's schedule needs a helmet and a name
        for t in (g["home"], g["away"]):
            for row in schedule_rows(t):
                if row.get("opponent") and row["opponent"] not in team_out:
                    tid = next((i for i, x in teams.items() if x["abbr"] == row["opponent"]), None)
                    if tid is not None:
                        x = teams[tid]
                        team_out[x["abbr"]] = {"id": tid, "school": x["school"], "conference": x["conf_name"], "conf_short": x["conf_short"],
                                               "fbs": x["fbs"], "color": x["color"], "alt_color": x["alt_color"]}

    out = {
        "generated_at_utc": now.isoformat(), "season": season, "week": cur_week, "current_week_key": current,
        "poll_week": latest_poll, "n_fbs": len(fbs), "warnings": warnings,
        "season_weeks": season_weeks, "game_details": details, "player_weeks": pw_out,
        "matchup_weeks": matchup_weeks, "defense_vs_position": defense,
        "rankings": {k: rank_payload(rankings_now.get(k)) for k in ("ap", "coaches", "cfp")},
        "teams": team_out,
    }
    snapshot = {"season": season, "polls": {str(w): {"ranks": {str(t): r for t, r in p["ranks"].items()}, "others": p["others"]}
                                            for w, p in polls.items() if w < latest_poll},
                "coaches": coaches, "games": dict(frozen_games, **new_frozen),
                "tv": {gid: n for gid, n in tv_cache.items() if gid in details}, "tv_weeks": sorted(done_weeks)}
    return out, snapshot


def matchup_inputs(pbp, teams, school_ids, now_week, rosters, dvp):
    """(matchup_weeks, defense) shaped the way matchup.py takes them from the NFL build (its player_weeks
    and defense_vs_position), from cfbfastR's play-by-play, each play's EPA to:
      - the team's QBs as one row a week, every dropback (attempts and sacks) -- ESPN's passer ids are
        missing on whole teams' plays (South Florida: 158 of 164 in 2026), and the card counts QBs as a group
      - the target: reception_player_id on a catch, target_player_id on an incompletion (cfbfastR fills one
        or the other), else the receiver's name on the team's roster
      - the rusher, by rush_player_id
    positions from ESPN's rosters. ~92% of passes and runs carry an id; a few teams far fewer (Nebraska's
    receivers 40% in 2026), so their RB / WR / TE rates rest on fewer plays.
    defense: sportsdataverse's cfb_defense_vs_position (the NFL file's columns, FBS defenses), plus QB
    passing yards an attempt allowed, totaled from the same plays."""
    import polars as pl
    if pbp is None:
        return {}, {}
    abbr_by_id = {tid: t["abbr"] for tid, t in teams.items()}
    by_school = {s: abbr_by_id[t] for s, t in school_ids.items()}
    rost = pl.DataFrame(rosters, infer_schema_length=None) if rosters else pl.DataFrame(
        {"athlete_id": [], "team_id": [], "position_abbreviation": [], "display_name": []})
    pos_by_id = rost.select(pl.col("athlete_id").cast(pl.Int64).alias("pid"),
                            pl.col("position_abbreviation").alias("pos_id")).unique("pid")
    pos_by_name = (rost.select(pl.col("team_id").cast(pl.Int64).replace_strict(abbr_by_id, default=None).alias("team"),
                               pl.col("display_name").alias("rname"), pl.col("position_abbreviation").alias("pos_nm"))
                   .unique(["team", "rname"]))
    f0 = lambda c: pl.col(c).cast(pl.Float64).fill_null(0)
    plays = (pbp.filter((pl.col("season_type") == "regular") & (pl.col("week") < now_week))
             .with_columns(pl.col("pos_team").replace_strict(by_school, default=None).alias("team"),
                           pl.col("def_pos_team").replace_strict(by_school, default=None).alias("dteam"),
                           pl.col("week").cast(pl.Int64).alias("wk"), f0("EPA").alias("epa"),
                           (f0("sack") > 0).alias("is_sack"), (f0("completion") > 0).alias("is_comp"))
             .filter(pl.col("team").is_not_null()))
    zero = {k: pl.lit(0.0) for k in ("att", "pyds", "pepa", "sk", "car", "ryds", "tgt", "rpepa", "repa", "reyds")}

    def pick(df, pid, pos=None, **vals):
        return df.select("team", "dteam", "wk", pid.cast(pl.Int64).alias("pid"),
                         (pl.lit(pos) if pos else pl.col("pos")).cast(pl.String).alias("pos"),
                         *[vals.get(k, v).cast(pl.Float64).alias(k) for k, v in zero.items()])
    dropbacks = plays.filter((f0("pass") > 0) | pl.col("is_sack"))
    passing = pick(dropbacks, pl.lit(-1), "QB",
                   att=(f0("pass_attempt") > 0) & ~pl.col("is_sack"), sk=pl.col("is_sack"), pepa=pl.col("epa"),
                   pyds=pl.when(pl.col("is_comp")).then(f0("yds_receiving")).otherwise(0.0))
    tg = (dropbacks.filter(~pl.col("is_sack"))
          .with_columns(pl.coalesce(pl.col("reception_player_id"), pl.col("target_player_id")).cast(pl.Int64).alias("rid"),
                        pl.col("receiver_player_name").alias("rname"))
          .filter(pl.col("rid").is_not_null() | pl.col("rname").is_not_null())
          .join(pos_by_id, left_on="rid", right_on="pid", how="left")
          .join(pos_by_name, on=["team", "rname"], how="left")
          .with_columns(pl.coalesce("pos_id", "pos_nm").alias("pos"),
                        # a player without an id keeps one by name, so his plays still add up as one player
                        pl.coalesce(pl.col("rid"), -(pl.col("rname").hash() // 4).cast(pl.Int64) - 2).alias("rid")))
    targets = pick(tg, pl.col("rid"), tgt=pl.lit(1.0), repa=pl.col("epa"),
                   reyds=pl.when(pl.col("is_comp")).then(f0("yds_receiving")).otherwise(0.0))
    ru = (plays.filter((f0("rush") > 0) & pl.col("rush_player_id").is_not_null())
          .with_columns(pl.col("rush_player_id").cast(pl.Int64).alias("rid"))
          .join(pos_by_id, left_on="rid", right_on="pid", how="left").rename({"pos_id": "pos"}))
    rushes = pick(ru, pl.col("rid"), car=pl.lit(1.0), ryds=f0("yds_rushed"), rpepa=pl.col("epa"))
    rows = pl.concat([passing, targets, rushes]).with_columns(pl.col("pos").fill_null(""))
    per_week = rows.group_by("team", "pid", "pos", "wk").agg(*[pl.col(k).sum() for k in zero])
    matchup_weeks = defaultdict(list)
    for r in per_week.filter(pl.col("pos").is_in(["QB", "RB", "FB", "WR", "TE"])).sort("wk").iter_rows(named=True):
        matchup_weeks[r["team"]].append({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()
                                         if k not in ("team", "pid") and v != 0} | {"pos": r["pos"], "wk": r["wk"]})

    rows_d = [dict(r, team=abbr_by_id.get(int(r["team_id"]))) for r in dvp or [] if r.get("division") == "fbs" and r.get("team_id") is not None]
    defense = matchup.defense_table([r for r in rows_d if r["team"]])
    qb = passing.group_by("dteam").agg(pl.col("pyds").sum(), pl.col("att").sum())
    for r in qb.iter_rows(named=True):
        if r["dteam"] in defense and r["att"]:
            defense[r["dteam"]]["pass"] = r["pyds"] / r["att"]
    return dict(matchup_weeks), defense


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()
    season = args.season or cc.current_season()
    out, snapshot = build(season)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(cc.to_json(out))
    with open(SNAP_LOCAL, "w", encoding="utf-8") as f:
        f.write(cc.to_json(snapshot))
    n_games = sum(len(w["games"]) for w in out["season_weeks"])
    print(f"build_cfb_data: {season} -- {len(out['season_weeks'])} weeks, {n_games} games, "
          f"{len(out['game_details'])} game pages, {len(out['warnings'])} warning(s)")
    for w in out["warnings"][:15]:
        print("  warning:", w.strip().splitlines()[-1][:300])
    if not out["game_details"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

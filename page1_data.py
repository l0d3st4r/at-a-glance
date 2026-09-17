"""
Page 1 data: everything the matchup page shows, for EVERY game of the season.
Called from build_data.py; output lands in data/matchups.json as "game_details",
keyed by game_id. render_page1.py turns each entry into site/game/<game_id>.html.

Each game is a snapshot "as of kickoff" (Jason's Page 1 is about context
before the game):
  - record, last-game arrow ........ from games played before this one; for a FINISHED
                                     game, the record right after it (matches its Page 0
                                     tile) and the arrow for this game's result, plus
                                     the final score (Jason, 2026-09-16)
  - offense/defense ranks .......... regular-season weeks before this game's week,
                                     per-game averages so bye weeks don't skew ranks
                                     (offense: most points/yards = 1st;
                                      defense: fewest allowed = 1st)
  - season leaders + league crowns . same weeks as the ranks. FINISHED games show each
                                     team's leaders in that game instead, no crowns
                                     (Jason, 2026-09-16)
  - injury report .................. that week's official report (Out / Doubtful /
                                     Questionable), starters first, then severity.
                                     Starter = first string on that team's depth chart
                                     (latest chart before the game); if there's no
                                     chart, >= 50% of snaps in earlier games.
  - weather ........................ upcoming outdoor games inside the NWS 7-day window:
                                     average temp over kickoff..+3h + most common
                                     condition. Finished games: nflverse's recorded
                                     temp/wind. Domes: "Indoors".
Playoff games use the full regular season for ranks/leaders.

Column names come from the live site's raw dump (checked 2026-09-16):
  team stats  -> team, passing_yards, rushing_yards, ...
  injuries    -> team, week, full_name, position, report_status
Player-stat and snap-count column names are not confirmed yet, so those use
the same "first matching column wins" approach as build_data.py and add a
warning if nothing matches.

Everything is defensive: a missing piece shows as "—" on the page instead
of breaking the build.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    EASTERN = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover
    EASTERN = None

from divisions import normalize_abbr
from stadiums import STADIUMS
from weather import get_game_window_weather

PLAYOFF_LABELS = {"WC": "Wild Card", "DIV": "Divisional Round", "CON": "Conference Championships", "SB": "Super Bowl"}
INJURY_ORDER = {"Out": 0, "Doubtful": 1, "Questionable": 2}
INJURY_SHORT = {"Out": "OUT", "Doubtful": "DOUBT", "Questionable": "QUES"}
STARTER_SNAP_SHARE = 0.5   # average share of offensive or defensive snaps in games played so far
NWS_WINDOW_DAYS = 7

LEADER_STATS = [
    ("passing_yards", "Passing Yards", ["passing_yards"]),
    ("rushing_yards", "Rushing Yards", ["rushing_yards"]),
    ("receiving_yards", "Receiving Yards", ["receiving_yards"]),
    ("interceptions", "Interceptions", ["def_interceptions", "interceptions"]),
    ("sacks", "Sacks", ["def_sacks", "sacks"]),
]

# Candidate column names (first present wins)
TEAM_COLS = ["team", "recent_team", "team_abbr", "club_code"]
OPP_COLS = ["opponent_team", "opponent", "opp_team"]
WEEK_COLS = ["week"]
SEASON_TYPE_COLS = ["season_type", "game_type"]
PLAYER_ID_COLS = ["player_id", "gsis_id", "pfr_player_id"]
PLAYER_NAME_COLS = ["player_display_name", "full_name", "player_name", "player", "name"]
POSITION_COLS = ["position", "position_group"]
SNAP_OFF_COLS = ["offense_pct", "off_pct"]
SNAP_DEF_COLS = ["defense_pct", "def_pct"]
SNAP_NAME_COLS = ["player", "player_name", "full_name", "player_display_name"]
# Depth charts: nflverse switched sources in 2025. New files: team, dt (snapshot time),
# player_name, gsis_id, pos_slot, pos_rank. Older files: club_code, week, full_name,
# gsis_id, depth_team. Both are handled.
DEPTH_TEAM_COLS = ["team", "club_code"]
DEPTH_RANK_COLS = ["pos_rank", "depth_team"]
DEPTH_NAME_COLS = ["player_name", "full_name", "football_name"]

NAME_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
NWS_STADIUM_ALIASES = {"WAS": "WSH", "LA": "LAR"}  # stadiums.py was keyed on ESPN abbreviations


# ---------------------------------------------------------------- helpers

def _col(row, candidates):
    for c in candidates:
        if c in row:
            return c
    return None


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int_week(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def short_name(full):
    """'Jer'Zhan Newton' -> 'J. Newton', 'Marvin Harrison Jr.' -> 'M. Harrison Jr.'"""
    parts = str(full or "").split()
    if len(parts) < 2:
        return str(full or "")
    last = parts[-1]
    if last.lower() in NAME_SUFFIXES and len(parts) >= 3:
        last = f"{parts[-2]} {parts[-1]}"
    return f"{parts[0][0]}. {last}"


def _name_key(name):
    parts = [p for p in str(name or "").lower().replace(".", "").replace("'", "").split() if p not in NAME_SUFFIXES]
    return " ".join(parts)


def competition_ranks(values, higher_is_better=True):
    """{key: number} -> {key: rank} with ties sharing a rank (1, 2, 2, 4)."""
    items = [(k, v) for k, v in values.items() if v is not None]
    items.sort(key=lambda kv: kv[1], reverse=higher_is_better)
    ranks, prev, prev_rank = {}, object(), 0
    for i, (k, v) in enumerate(items, start=1):
        if v != prev:
            prev_rank, prev = i, v
        ranks[k] = prev_rank
    return ranks


def kickoff_utc(gameday, gametime):
    """nflverse gameday 'YYYY-MM-DD' + gametime 'HH:MM' (US Eastern) -> aware UTC datetime, or None."""
    try:
        naive = datetime.fromisoformat(f"{str(gameday)[:10]}T{str(gametime)[:5]}")
    except (TypeError, ValueError):
        return None
    if EASTERN is None:
        return (naive + timedelta(hours=4)).replace(tzinfo=timezone.utc)  # EDT fallback
    return naive.replace(tzinfo=EASTERN).astimezone(timezone.utc)


def stadium_for(abbr):
    abbr = normalize_abbr(abbr)
    return STADIUMS.get(abbr) or STADIUMS.get(NWS_STADIUM_ALIASES.get(abbr, ""), {})


# ---------------------------------------------------------------- games

def _games(schedules):
    games = []
    for g in schedules:
        week = _int_week(g.get("week"))
        hs, as_ = _num(g.get("home_score")), _num(g.get("away_score"))
        games.append({
            "raw": g,
            "game_id": g.get("game_id"),
            "game_type": g.get("game_type") or "REG",
            "week": week,
            "gameday": g.get("gameday"),
            "gametime": g.get("gametime"),
            "home": normalize_abbr(g.get("home_team")),
            "away": normalize_abbr(g.get("away_team")),
            "home_score": hs,
            "away_score": as_,
            "final": hs is not None and as_ is not None,
            "sort": (str(g.get("gameday") or "9999"), str(g.get("gametime") or "99:99"), str(g.get("game_id") or "")),
        })
    games.sort(key=lambda x: x["sort"])
    return games


def _game_records(games):
    """
    game_id -> {team: {"record": {...}, "last": "W"|"L"|"T"|None}}
    Upcoming game: record and last result from games finished before it.
    Finished game: record right after it (regular-season record, like Page 0's
    frozen tiles) and "last" = this game's result.
    """
    blank = lambda: {"wins": 0, "losses": 0, "ties": 0}
    running, last = defaultdict(blank), {}
    out = {}
    for g in games:  # already in kickoff order
        teams = (g["home"], g["away"])
        if g["final"]:
            for team, mine, theirs in ((g["home"], g["home_score"], g["away_score"]), (g["away"], g["away_score"], g["home_score"])):
                result = "W" if mine > theirs else "L" if mine < theirs else "T"
                last[team] = result
                if g["game_type"] == "REG":
                    running[team]["wins" if result == "W" else "losses" if result == "L" else "ties"] += 1
        out[g["game_id"]] = {t: {"record": dict(running[t]), "last": last.get(t)} for t in teams}
    return out


# ---------------------------------------------------------------- ranks

def _rank_builder(games, team_weekly, warnings):
    """Returns ranks_through(week) -> {team: {off_points, off_yards, def_points, def_yards}} (cached)."""
    reg_final = [g for g in games if g["game_type"] == "REG" and g["final"] and g["week"] is not None]

    # opponent per (team, week) from the schedule, in case weekly stats lack an opponent column
    opponent = {}
    for g in games:
        if g["week"] is not None:
            opponent[(g["home"], g["week"])] = g["away"]
            opponent[(g["away"], g["week"])] = g["home"]

    yard_rows = []  # (week, team, opponent, yards)
    if team_weekly:
        sample = team_weekly[0]
        tcol, wcol, ocol, stcol = _col(sample, TEAM_COLS), _col(sample, WEEK_COLS), _col(sample, OPP_COLS), _col(sample, SEASON_TYPE_COLS)
        if not tcol or not wcol:
            warnings.append(f"page1 ranks: weekly team stats missing team/week columns (have: {sorted(sample)[:12]}...)")
        else:
            for r in team_weekly:
                if stcol and r.get(stcol) not in (None, "REG"):
                    continue
                wk, team = _int_week(r.get(wcol)), normalize_abbr(r.get(tcol))
                if wk is None or not team:
                    continue
                yards = (_num(r.get("passing_yards")) or 0) + (_num(r.get("rushing_yards")) or 0)
                opp = normalize_abbr(r.get(ocol)) if ocol and r.get(ocol) else opponent.get((team, wk))
                yard_rows.append((wk, team, opp, yards))
    else:
        warnings.append("page1 ranks: no weekly team stats -- yards ranks will show as —")

    cache = {}

    def ranks_through(week_limit):
        """Uses regular-season weeks < week_limit (None = all)."""
        if week_limit in cache:
            return cache[week_limit]
        ok = lambda wk: week_limit is None or wk < week_limit
        pts_for, pts_against, games_played = defaultdict(float), defaultdict(float), defaultdict(int)
        for g in reg_final:
            if not ok(g["week"]):
                continue
            for team, mine, theirs in ((g["home"], g["home_score"], g["away_score"]), (g["away"], g["away_score"], g["home_score"])):
                pts_for[team] += mine
                pts_against[team] += theirs
                games_played[team] += 1
        yds_for, yds_against, yds_games, yds_opp_games = defaultdict(float), defaultdict(float), defaultdict(int), defaultdict(int)
        for wk, team, opp, yards in yard_rows:
            if not ok(wk):
                continue
            yds_for[team] += yards
            yds_games[team] += 1
            if opp:
                yds_against[opp] += yards
                yds_opp_games[opp] += 1
        per_game = lambda total, n: {t: total[t] / n[t] for t in n if n[t]}
        off_pts = competition_ranks(per_game(pts_for, games_played), True)
        def_pts = competition_ranks(per_game(pts_against, games_played), False)
        off_yds = competition_ranks(per_game(yds_for, yds_games), True)
        def_yds = competition_ranks(per_game(yds_against, yds_opp_games), False)
        teams = set(off_pts) | set(off_yds) | set(def_yds)
        cache[week_limit] = {
            t: {"off_points": off_pts.get(t), "off_yards": off_yds.get(t),
                "def_points": def_pts.get(t), "def_yards": def_yds.get(t)}
            for t in teams
        }
        return cache[week_limit]

    return ranks_through


# ---------------------------------------------------------------- leaders

def _leader_builder(player_weekly, warnings):
    """Returns leaders_through(week) -> {stat_key: {"by_team": {team: leader}, ...}} (cached)."""
    rows = []
    if player_weekly:
        sample = player_weekly[0]
        tcol, wcol, stcol = _col(sample, TEAM_COLS), _col(sample, WEEK_COLS), _col(sample, SEASON_TYPE_COLS)
        idcol, ncol, pcol = _col(sample, PLAYER_ID_COLS), _col(sample, PLAYER_NAME_COLS), _col(sample, POSITION_COLS)
        stat_cols = {key: _col(sample, cands) for key, _label, cands in LEADER_STATS}
        missing = [k for k, c in stat_cols.items() if not c]
        if missing:
            warnings.append(f"page1 leaders: player stats missing columns for {missing} (have: {sorted(sample)[:20]}...)")
        if not (tcol and ncol):
            warnings.append(f"page1 leaders: player stats missing team/name columns (have: {sorted(sample)[:20]}...)")
        else:
            for r in player_weekly:
                wk = _int_week(r.get(wcol)) if wcol else None
                rows.append({
                    "regular": not stcol or r.get(stcol) in (None, "REG"),
                    "week": wk,
                    "team": normalize_abbr(r.get(tcol)),
                    "id": r.get(idcol) if idcol else r.get(ncol),
                    "name": r.get(ncol),
                    "position": r.get(pcol) if pcol else "",
                    "stats": {k: (_num(r.get(c)) or 0) if c else 0 for k, c in stat_cols.items()},
                })
    else:
        warnings.append("page1 leaders: no player stats -- leaders will show as —")

    cache = {}

    def leaders_through(week_limit):
        if week_limit in cache:
            return cache[week_limit]
        team_totals = defaultdict(lambda: defaultdict(float))   # (team, id) -> stat -> total
        league_totals = defaultdict(lambda: defaultdict(float)) # id -> stat -> total
        info = {}
        for r in rows:
            if not r["regular"]:
                continue
            if week_limit is not None and (r["week"] is None or r["week"] >= week_limit):
                continue
            info[r["id"]] = (r["name"], r["position"])
            for k, v in r["stats"].items():
                team_totals[(r["team"], r["id"])][k] += v
                league_totals[r["id"]][k] += v
        result = {}
        for key, _label, _c in LEADER_STATS:
            league_rank = competition_ranks({pid: s[key] for pid, s in league_totals.items() if s[key] > 0}, True)
            by_team = {}
            for (team, pid), s in team_totals.items():
                v = s[key]
                if v <= 0:
                    continue
                if team not in by_team or v > by_team[team]["value"]:
                    name, pos = info.get(pid, ("", ""))
                    by_team[team] = {"name": short_name(name), "full_name": name, "position": pos or "",
                                     "value": v, "league_rank": league_rank.get(pid)}
            result[key] = by_team
        cache[week_limit] = result
        return result

    by_game = defaultdict(list)  # (team, week) -> that game's player rows (regular season or playoffs)
    for r in rows:
        by_game[(r["team"], r["week"])].append(r)

    def game_leaders(team, week):
        """{stat_key: leader} for one team's players in one game (no league rank)."""
        out = {}
        for key, _label, _c in LEADER_STATS:
            best = None
            for r in by_game.get((team, week), []):
                v = r["stats"].get(key, 0)
                if v > 0 and (best is None or v > best["value"]):
                    best = {"name": short_name(r["name"]), "full_name": r["name"], "position": r["position"] or "",
                            "value": v, "league_rank": None}
            out[key] = best
        return out

    leaders_through.game = game_leaders
    return leaders_through


# ---------------------------------------------------------------- injuries

def _depth_builder(depth, warnings):
    """
    Returns starters_before(team, week, gameday) -> set of ("id", gsis_id) / ("name", key)
    for first-string players on the latest depth chart on or before the game,
    or None if that team has no chart yet.
    """
    import bisect
    if not depth:
        warnings.append("page1 injuries: no depth charts -- starters from snap counts only")
        return lambda team, week, gameday: None
    sample = depth[0]
    tcol, rcol = _col(sample, DEPTH_TEAM_COLS), _col(sample, DEPTH_RANK_COLS)
    ncol, idcol = _col(sample, DEPTH_NAME_COLS), _col(sample, ["gsis_id"])
    dtcol, wcol = _col(sample, ["dt"]), _col(sample, WEEK_COLS)
    if not (tcol and rcol and (ncol or idcol) and (dtcol or wcol)):
        warnings.append(f"page1 injuries: depth charts missing columns, using snap counts (have: {sorted(sample)[:15]}...)")
        return lambda team, week, gameday: None
    by_date = bool(dtcol)
    charts = defaultdict(lambda: defaultdict(set))  # team -> snapshot key -> starters
    for r in depth:
        key = str(r.get(dtcol) or "")[:10] if by_date else _int_week(r.get(wcol))
        if key in (None, ""):
            continue
        bucket = charts[normalize_abbr(r.get(tcol))][key]
        if _num(r.get(rcol)) == 1:
            if idcol and r.get(idcol):
                bucket.add(("id", r.get(idcol)))
            if ncol and r.get(ncol):
                bucket.add(("name", _name_key(r.get(ncol))))
    keys = {team: sorted(k) for team, k in charts.items()}

    def starters_before(team, week, gameday):
        team_keys = keys.get(team)
        marker = str(gameday or "")[:10] if by_date else week
        if not team_keys or marker in (None, ""):
            return None
        i = bisect.bisect_right(team_keys, marker)
        return charts[team][team_keys[i - 1]] if i else None

    return starters_before


def _injury_builder(injuries, snaps, depth, warnings):
    """Returns injuries_for(team, week, gameday) -> [{"name", "short", "status", "status_short", "starter"}] (top 3)."""
    report = defaultdict(list)  # (team, week) -> rows
    if injuries:
        sample = injuries[0]
        tcol, wcol = _col(sample, TEAM_COLS), _col(sample, WEEK_COLS)
        if not (tcol and wcol):
            warnings.append(f"page1 injuries: missing team/week columns (have: {sorted(sample)[:15]}...)")
        else:
            for r in injuries:
                status = str(r.get("report_status") or "").strip().title()
                if status not in INJURY_ORDER:
                    continue
                wk = _int_week(r.get(wcol))
                name = r.get("full_name") or " ".join(x for x in (r.get("first_name"), r.get("last_name")) if x)
                report[(normalize_abbr(r.get(tcol)), wk)].append({"name": name, "gsis_id": r.get("gsis_id"),
                                                                  "position": r.get("position"), "status": status})

    snap_rows = defaultdict(list)  # (team, name_key) -> [(week, share)]
    if snaps:
        sample = snaps[0]
        tcol, wcol, ncol = _col(sample, TEAM_COLS), _col(sample, WEEK_COLS), _col(sample, SNAP_NAME_COLS)
        ocol, dcol = _col(sample, SNAP_OFF_COLS), _col(sample, SNAP_DEF_COLS)
        if not (tcol and wcol and ncol and (ocol or dcol)):
            warnings.append(f"page1 injuries: snap counts missing columns, starters can't be detected (have: {sorted(sample)[:15]}...)")
        else:
            for r in snaps:
                share = max(_num(r.get(ocol)) or 0 if ocol else 0, _num(r.get(dcol)) or 0 if dcol else 0)
                if share > 1.5:  # some sources use 0-100
                    share /= 100
                snap_rows[(normalize_abbr(r.get(tcol)), _name_key(r.get(ncol)))].append((_int_week(r.get(wcol)), share))
    else:
        warnings.append("page1 injuries: no snap counts -- starters come from depth charts only")

    starters_before = _depth_builder(depth, warnings)

    def is_starter(team, row, week, gameday):
        chart = starters_before(team, week, gameday)
        if chart is not None:  # depth chart first
            return ("id", row.get("gsis_id")) in chart or ("name", _name_key(row["name"])) in chart
        games = [s for wk, s in snap_rows.get((team, _name_key(row["name"])), []) if wk is not None and (week is None or wk < week)]
        return bool(games) and sum(games) / len(games) >= STARTER_SNAP_SHARE

    weeks_with_report = {wk for (_team, wk) in report}

    def report_out(week):
        return week in weeks_with_report

    def injuries_for(team, week, gameday=None):
        rows = report.get((team, week), [])
        seen, out = set(), []
        for r in rows:
            if r["name"] in seen:
                continue
            seen.add(r["name"])
            out.append({**r, "starter": is_starter(team, r, week, gameday)})
        out.sort(key=lambda r: (not r["starter"], INJURY_ORDER[r["status"]], r["name"]))
        return [{"name": r["name"], "short": short_name(r["name"]), "status": r["status"],
                 "status_short": INJURY_SHORT[r["status"]], "starter": r["starter"]} for r in out[:3]]

    injuries_for.report_out = report_out
    return injuries_for


# ---------------------------------------------------------------- weather + venue

def _venue(g):
    raw = g["raw"]
    roof = str(raw.get("roof") or "").lower()
    stadium = stadium_for(g["home"])
    neutral = str(raw.get("location") or "").lower() == "neutral"
    indoor = roof in ("dome", "closed") if roof else bool(stadium.get("indoor"))
    if neutral:
        city = raw.get("stadium") or "Neutral site"
        stadium = {}  # home team's stadium coordinates don't apply
    elif stadium.get("city"):
        city = f"{stadium['city']}, {stadium['state']}" if stadium.get("state") else stadium["city"]
    else:
        city = raw.get("stadium") or ""
    return {"city": city, "stadium": raw.get("stadium") or stadium.get("name"), "indoor": indoor, "neutral": neutral}, stadium


def _weather(g, venue, stadium, now_utc):
    if venue["indoor"]:
        return {"available": True, "indoor": True}
    raw = g["raw"]
    if g["final"]:
        temp, wind = _num(raw.get("temp")), _num(raw.get("wind"))
        if temp is None:
            return {"available": False, "reason": "no recorded temperature"}
        return {"available": True, "temp_f": round(temp), "wind_mph": wind,
                "condition": "wind" if wind is not None and wind >= 18 else None, "source": "nflverse"}
    ko = kickoff_utc(g["gameday"], g["gametime"])
    if ko is None or not stadium.get("lat"):
        return {"available": False, "reason": "no kickoff time or stadium location"}
    if not (now_utc - timedelta(hours=4) <= ko <= now_utc + timedelta(days=NWS_WINDOW_DAYS)):
        return {"available": False, "reason": "outside the NWS 7-day forecast window"}
    w = get_game_window_weather(stadium["lat"], stadium["lon"], ko)
    if w.get("available"):
        w["source"] = "nws"
    return w


# ---------------------------------------------------------------- main entry

def week_key_and_label(game_type, week):
    if game_type in PLAYOFF_LABELS:
        return game_type, PLAYOFF_LABELS[game_type]
    return str(week), f"Week {week}"


def build_game_details(schedules, team_weekly, player_weekly, injuries, snaps, warnings, now_utc=None, depth=None):
    now_utc = now_utc or datetime.now(timezone.utc)
    games = _games(schedules)
    records = _game_records(games)
    ranks_through = _rank_builder(games, team_weekly, warnings)
    leaders_through = _leader_builder(player_weekly, warnings)
    injuries_for = _injury_builder(injuries, snaps, depth, warnings)

    details = {}
    for g in games:
        gid = g["game_id"]
        if not gid:
            continue
        try:
            limit = g["week"] if g["game_type"] == "REG" else None
            ranks = ranks_through(limit)
            leaders = leaders_through(limit)
            venue, stadium = _venue(g)
            key, label = week_key_and_label(g["game_type"], g["week"])

            def side(team):
                pre = records.get(gid, {}).get(team, {})
                return {
                    "team": team,
                    "record": pre.get("record") or {"wins": 0, "losses": 0, "ties": 0},
                    "last": pre.get("last"),
                    "injuries": injuries_for(team, g["week"], g["gameday"]),
                    "injury_report_out": injuries_for.report_out(g["week"]),
                    "ranks": ranks.get(team) or {},
                }

            if g["final"]:
                game = {g["away"]: leaders_through.game(g["away"], g["week"]),
                        g["home"]: leaders_through.game(g["home"], g["week"])}
                pick = lambda k, team: game[team].get(k)
            else:
                pick = lambda k, team: leaders.get(k, {}).get(team)

            details[gid] = {
                "game_id": gid,
                "game_type": g["game_type"],
                "week": g["week"],
                "week_key": key,
                "week_label": label,
                "gameday": g["gameday"],
                "gametime": g["gametime"],
                "final": g["final"],
                "score": {"away": g["away_score"], "home": g["home_score"]} if g["final"] else None,
                "networks": {"status": "pending"},
                "venue": venue,
                "weather": _weather(g, venue, stadium, now_utc),
                "stats_through_week": (limit - 1) if limit else "regular season",
                "away": side(g["away"]),
                "home": side(g["home"]),
                "leaders_scope": "game" if g["final"] else "season",
                "leaders": [
                    {"key": k, "label": lbl, "away": pick(k, g["away"]), "home": pick(k, g["home"])}
                    for k, lbl, _c in LEADER_STATS
                ],
            }
        except Exception as e:  # one bad game never breaks the rest
            warnings.append(f"page1 {gid}: {e}")
    return details

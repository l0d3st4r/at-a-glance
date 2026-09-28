"""
Player Stats data (added 2026-09-28) for the Page 2 Player Stats page the Leaders card opens
(render_page2players.py).

Two halves, so the data file stays small:
  * build_player_weeks() -- run by build_data.py: every regular-season player row from
    nflverse's weekly player stats, grouped by team, keeping only the stats the page shows and
    only the non-zero ones. Written once to data/matchups.json as "player_weeks" (not copied
    into each of the ~270 games, which would multiply it).
  * season_totals() -- run by render_page1.write_all for each game page: adds up a team's
    rows for the weeks before this game's week, the same season-to-date rule as the ranks and
    Leaders card (page1_data: regular-season weeks < the game's week; playoffs use the whole
    regular season).
"""

from collections import defaultdict

from divisions import normalize_abbr

# short key in the data file -> nflverse weekly player stats column
STATS = {
    "cmp": "completions", "att": "attempts", "pyds": "passing_yards", "ptd": "passing_tds",
    "int": "passing_interceptions", "sk": "sacks_suffered",
    "car": "carries", "ryds": "rushing_yards", "rtd": "rushing_tds", "r1d": "rushing_first_downs",
    "rfum": "rushing_fumbles_lost",
    "rec": "receptions", "tgt": "targets", "reyds": "receiving_yards", "retd": "receiving_tds",
    "re1d": "receiving_first_downs",
    "solo": "def_tackles_solo", "ast": "def_tackle_assists", "tfl": "def_tackles_for_loss",
    "dsk": "def_sacks", "qbh": "def_qb_hits", "dint": "def_interceptions", "pd": "def_pass_defended",
    "ff": "def_fumbles_forced", "fr": "fumble_recovery_opp", "dtd": "def_tds",
    "fgm": "fg_made", "fga": "fg_att", "fglng": "fg_long", "xpm": "pat_made", "xpa": "pat_att",
    "p": "pt_att", "pyd": "pt_yards", "pnet": "pt_net_yards", "p20": "pt_inside_20",
    "kr": "kickoff_returns", "kryds": "kickoff_return_yards",
    "pr": "punt_returns", "pryds": "punt_return_yards",
}
MAX_STATS = {"fglng"}   # a season's long is the best week, not the sum

NAME_COLS = ("player_display_name", "player_name")
POS_COLS = ("position",)


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0
    if f != f:   # NaN
        return 0
    return int(f) if f == int(f) else round(f, 1)


def build_player_weeks(player_weekly, warnings):
    """{team: [{"id", "name", "pos", "wk", <short key>: value, ...}]} -- regular season only."""
    out = defaultdict(list)
    if not player_weekly:
        warnings.append("player stats page: no weekly player stats")
        return {}
    sample = player_weekly[0]
    missing = sorted(k for k, c in STATS.items() if c not in sample)
    if missing:
        warnings.append(f"player stats page: missing columns for {missing}")
    name_col = next((c for c in NAME_COLS if c in sample), None)
    for r in player_weekly:
        if r.get("season_type") not in (None, "REG"):
            continue
        try:
            wk = int(r.get("week"))
        except (TypeError, ValueError):
            continue
        row = {"id": r.get("player_id") or r.get(name_col), "name": r.get(name_col) or "",
               "pos": r.get("position") or "", "wk": wk}
        for k, c in STATS.items():
            v = _num(r.get(c))
            if v:
                row[k] = v
        if len(row) > 4:
            out[normalize_abbr(r.get("team"))].append(row)
    for rows in out.values():
        rows.sort(key=lambda row: row["wk"])   # season_totals takes a player's latest name/position
    return dict(out)


def season_totals(player_weeks, team, week_limit):
    """One totals row per player for `team` over regular-season weeks < week_limit (None = all)."""
    players = {}
    for r in (player_weeks or {}).get(team) or []:
        if week_limit is not None and r["wk"] >= week_limit:
            continue
        p = players.get(r["id"])
        if p is None:
            p = players[r["id"]] = defaultdict(int, id=r["id"], name=r["name"], pos=r["pos"])
        p["name"], p["pos"] = r["name"] or p["name"], r["pos"] or p["pos"]   # latest week wins
        for k in STATS:
            v = r.get(k)
            if v:
                p[k] = max(p[k], v) if k in MAX_STATS else p[k] + v
    return list(players.values())


# ---------------------------------------------------------------- league top 3 (gold / silver / bronze)
# The stats a player can medal in (Jason, 2026-09-28): 1st / 2nd / 3rd in the whole league over
# the same weeks as the page. Most is best for all of them -- passing INTs included, as asked.
# Y/A only ranks qualified passers (the NFL's 14 attempts per team game), so a backup's lone
# 40-yard completion doesn't top the league.
MEDAL_STATS = {
    "pyds": lambda r: r["pyds"], "ptd": lambda r: r["ptd"], "int": lambda r: r["int"],
    "ypa": lambda r: r["pyds"] / r["att"] if r["att"] else 0,
    "car": lambda r: r["car"], "ryds": lambda r: r["ryds"], "rtd": lambda r: r["rtd"],
    "rec": lambda r: r["rec"], "reyds": lambda r: r["reyds"], "retd": lambda r: r["retd"],
    "tkl": lambda r: r["solo"] + r["ast"], "tfl": lambda r: r["tfl"], "dsk": lambda r: r["dsk"],
    "dint": lambda r: r["dint"], "ff": lambda r: r["ff"],
}
YPA_ATTEMPTS_PER_GAME = 14


def league_medals(player_weeks, week_limit):
    """{(team, player id): {stat: 1 | 2 | 3}} for everyone in the league's top 3 of a MEDAL_STATS
    stat over regular-season weeks < week_limit. Places use competition ranking (two tied for
    1st are both gold and the next is bronze); a zero never medals."""
    rows = []   # (team, row, games the team has played)
    for team in (player_weeks or {}):
        games = len({r["wk"] for r in player_weeks[team] if week_limit is None or r["wk"] < week_limit})
        rows += [(team, r, games) for r in season_totals(player_weeks, team, week_limit)]
    out = defaultdict(dict)
    for stat, value in MEDAL_STATS.items():
        vals = []
        for team, r, games in rows:
            if stat == "ypa" and r["att"] < YPA_ATTEMPTS_PER_GAME * games:
                continue
            v = value(r)
            if v > 0:
                vals.append((v, team, r["id"]))
        vals.sort(key=lambda x: -x[0])
        for i, (v, team, pid) in enumerate(vals):
            place = 1 + sum(1 for w, _t, _p in vals[:i] if w > v)
            if place > 3:
                break
            out[(team, pid)][stat] = place
    return dict(out)

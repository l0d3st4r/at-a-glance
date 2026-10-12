"""
College football section -- mockup (2026-10-12), NOT part of the live build.

SNAPSHOT: Jason picked rank badge "A", asked for full school names and a CFP tab on Rankings, the conference
on the team cards, a proportional small trend chart and Matchups from the play-by-play's EPA -- all of it now
lives in the real section (build_cfb_data.py, render_cfb.py). Kept for reference; its index-b.html (badge B)
is gone.

The first look at a CFB section built on the NFL pages (Jason, 2026-10-12): only games involving teams
in that week's AP poll -- the Top 25 and the others receiving votes -- each week frozen to the poll that
came out before it (weeks not played yet follow the latest poll). Built from live 2026 data with the
real page code (render_html, render_page1, render_standings' styles), patched here for college:

  index.html       Page 0: the AP rank as a small number ahead of the abbreviation (Jason picked this,
                   "A", 2026-10-12, over a disc on the helmet's corner)
  game/<id>.html   Page 1 for every game on Page 0 (tapping a tile opens it): the team cards trade the
                   injury report for an AP rank trend line and carry the conference and conference
                   record, and the offense / defense ranks are out of the FBS teams (the green-to-red
                   scale stretched to fit). Matchups (matchup.py, unchanged) from cfbfastR's play-by-play
                   EPA for the offenses and sportsdataverse's cfb_defense_vs_position for the defenses
  rankings.html    the Rankings page in Standings' place, schools' full names: AP Poll | Coaches Poll |
                   CFP, each a deck of Top 25 | Receiving Votes (+ dropped out) | Key; CFP says when its
                   first rankings come out until they do

Data: ESPN's rankings (site API for this week's AP and Coaches polls; core API for each past week's AP
poll with its receiving votes), and sportsdataverse's 2026 files -- the schedule, team info (colors,
conference, stadium), team and player box scores, play-by-play, rosters (positions) and defense vs
position -- plus ESPN's scoreboard for the TV networks.
Downloads are cached in site/cfb-mockup/_cache (delete it for fresh data).

Run:  py mockups/build_cfb_mockup.py   then serve site/ and open /cfb-mockup/
"""

import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import polars as pl
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import helmets  # noqa: E402
import matchup  # noqa: E402
import logo  # noqa: E402
import render_html as rh  # noqa: E402
import render_page1 as p1  # noqa: E402
import render_page2team as tp  # noqa: E402
import render_standings as rs  # noqa: E402
import theme  # noqa: E402

OUT = os.path.join(ROOT, "site", "cfb-mockup")
CACHE = os.path.join(OUT, "_cache")
SEASON = 2026
REL = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"
SITE_API = "https://site.api.espn.com/apis/site/v2/sports/football/college-football"
CORE_API = f"https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{SEASON}"
ET = ZoneInfo("America/New_York")
N_FBS = 138

CONF_SHORT = {"American Athletic": "AAC", "Conference USA": "CUSA", "FBS Independents": "IND", "Big Ten": "B1G",
              "Sun Belt": "SBC", "Pac-12": "PAC", "Mountain West": "MW", "ACC": "ACC", "SEC": "SEC",
              "Mid-American": "MAC", "Big 12": "B12"}
# the team cards' conference line
CONF_NAME = {"American Athletic": "American", "Conference USA": "C-USA", "FBS Independents": "Independent",
             "Mid-American": "MAC"}

# The CFP committee's 2026 rankings (collegefootballplayoff.com/about-the-rankings): Tuesdays, then the
# 12-team field on Selection Day. The CFP tab says so until ESPN's rankings carry the first one.
CFP_DATES = [("Tue", "Nov 3"), ("Tue", "Nov 10"), ("Tue", "Nov 17"), ("Tue", "Nov 24"), ("Tue", "Dec 1"),
             ("Sun", "Dec 6")]


# ---------------------------------------------------------------- fetching (cached)

def _get(url, name, binary=True):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
    with open(path, "rb") as f:
        data = f.read()
    return data if binary else json.loads(data)


def parquet(tag, name):
    return pl.read_parquet(io.BytesIO(_get(f"{REL}/{tag}/{name}", name)))


def ap_poll(week):
    """{team_id: rank} and [receiving-votes team ids] for the AP poll before `week`'s games (week 1 = preseason)."""
    url = f"{CORE_API}/types/1/weeks/1/rankings/1" if week == 1 else f"{CORE_API}/types/2/weeks/{week}/rankings/1"
    d = _get(url, f"ap_{week}.json", binary=False)
    tid = lambda e: int(re.search(r"/teams/(\d+)", e["team"]["$ref"]).group(1))
    return {tid(e): e["current"] for e in d.get("ranks") or []}, [tid(e) for e in d.get("others") or []]


# ---------------------------------------------------------------- data

def load():
    info = parquet("cfb_team_info", f"cfb_team_info_{SEASON}.parquet")
    teams = {r["team_id"]: r for r in info.iter_rows(named=True)}
    sched = parquet("cfb_schedules", f"cfb_schedules_{SEASON}.parquet").filter(pl.col("season_type") == "regular")
    tbox = parquet("espn_cfb_team_box", f"team_box_{SEASON}.parquet")
    pbox = parquet("espn_cfb_player_box", f"player_box_{SEASON}.parquet")
    current = _get(f"{SITE_API}/rankings", "rankings_now.json", binary=False)
    now_week = int(next(r for r in current["rankings"] if r["name"].startswith("AP"))["occurrence"]["value"])
    polls = {w: ap_poll(w) for w in [1] + list(range(2, now_week + 1))}
    sb = _get(f"{SITE_API}/scoreboard?week={now_week}&groups=80&limit=300", f"scoreboard_{now_week}.json", binary=False)
    tv = {}
    for ev in sb.get("events") or []:
        names = [n for b in (ev["competitions"][0].get("broadcasts") or []) for n in b.get("names") or []]
        tv[int(ev["id"])] = names
    return teams, sched, tbox, pbox, current, now_week, polls, tv


def abbr_of(teams, tid):
    t = teams.get(tid) or {}
    return t.get("abbreviation") or str(tid)


def file_of(abbr):
    return re.sub(r"[^A-Za-z0-9]", "_", abbr)


def eastern(iso):
    t = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ET)
    return t.date().isoformat(), t.strftime("%H:%M")


def build(teams, sched, tbox, pbox, now_week, polls, tv):
    games = sorted(sched.iter_rows(named=True), key=lambda g: g["start_date"])
    fbs = {tid for tid, t in teams.items() if t.get("classification") == "fbs"}

    # every team's results in order -> records before / after each game, streaks
    results = {}
    for g in games:
        if g["completed"] and g["home_points"] is not None:
            for me, opp, mine, theirs in ((g["home_id"], g["away_id"], g["home_points"], g["away_points"]),
                                          (g["away_id"], g["home_id"], g["away_points"], g["home_points"])):
                results.setdefault(me, []).append((g["week"], g["game_id"], "W" if mine > theirs else "L", mine, theirs,
                                                   bool(g["conference_game"])))

    def record(tid, before_week=None, through_game=None, conf_only=False):
        w = l = 0
        last, streak = None, 0
        for wk, gid, res, _pf, _pa, conf in results.get(tid, []):
            if before_week is not None and wk >= before_week:
                break
            if conf_only and not conf:
                if gid == through_game:
                    break
                continue
            w += res == "W"
            l += res == "L"
            streak = streak + 1 if res == last else 1
            last = res
            if gid == through_game:
                break
        return {"wins": w, "losses": l}, last, streak

    # season-to-date team ranks among FBS: points and yards a game, scored and allowed
    yards = {}
    for gid, grp in tbox.group_by("game_id"):
        rows = grp.to_dicts()
        if len(rows) == 2:
            for a, b in ((rows[0], rows[1]), (rows[1], rows[0])):
                yards[(gid[0], int(a["team_id"]))] = (float(a["totalYards"] or 0), float(b["totalYards"] or 0))

    def ranks_before(week):
        tot = {}
        for tid, res in results.items():
            for wk, gid, _r, pf, pa, _c in res:
                if wk >= week:
                    break
                s = tot.setdefault(tid, [0, 0, 0, 0, 0, 0])
                s[0] += 1
                s[1] += pf
                s[2] += pa
                y = yards.get((gid, tid))
                if y:
                    s[3] += 1
                    s[4] += y[0]
                    s[5] += y[1]
        per = {t: s for t, s in tot.items() if t in fbs and s[0]}

        def rank(key, high_good):
            vals = sorted(((key(s), t) for t, s in per.items() if key(s) is not None), reverse=high_good)
            return {t: i + 1 for i, (_v, t) in enumerate(vals)}
        r = {"off_points": rank(lambda s: s[1] / s[0], True), "def_points": rank(lambda s: s[2] / s[0], False),
             "off_yards": rank(lambda s: s[4] / s[3] if s[3] else None, True),
             "def_yards": rank(lambda s: s[5] / s[3] if s[3] else None, False)}
        return {t: {k: r[k].get(t) for k in r} for t in per}

    # season leaders before a week, from the player box
    week_of = {g["game_id"]: g["week"] for g in games}
    pb = pbox.with_columns(pl.col("game_id").cast(pl.Int64).replace_strict(week_of, default=None).alias("week"),
                           pl.col("team_id").cast(pl.Int64))
    num = lambda c: pl.col(c).cast(pl.Float64, strict=False).fill_null(0)
    split = lambda c, i: pl.col(c).str.split("/").list.get(i, null_on_oob=True).cast(pl.Float64, strict=False).fill_null(0)
    stat_defs = [
        ("passing_yards", "Passing Yards", "passing", num("passingYards"),
         {"completions": split("completions/passingAttempts", 0), "attempts": split("completions/passingAttempts", 1),
          "passing_tds": num("passingTouchdowns")}),
        ("rushing_yards", "Rushing Yards", "rushing", num("rushingYards"),
         {"carries": num("rushingAttempts"), "rushing_tds": num("rushingTouchdowns")}),
        ("receiving_yards", "Receiving Yards", "receiving", num("receivingYards"),
         {"receptions": num("receptions"), "receiving_tds": num("receivingTouchdowns")}),
        ("interceptions", "Interceptions", "interceptions", num("interceptions"), {}),
        ("sacks", "Sacks", "defensive", num("sacks"), {}),
    ]

    def leaders_before(week, a_id, h_id):
        out = []
        for key, label, cat, expr, extras in stat_defs:
            sub = pb.filter((pl.col("category") == cat) & (pl.col("week") < week))
            tot = (sub.group_by("athlete_id", "athlete_name", "team_id")
                   .agg(expr.sum().alias("v"), *[e.sum().alias(k) for k, e in extras.items()])
                   .filter(pl.col("v") > 0).sort("v", descending=True))
            lr = {r["athlete_id"]: i + 1 for i, r in enumerate(tot.iter_rows(named=True))}

            def pick(tid):
                rows = tot.filter(pl.col("team_id") == tid).head(1).to_dicts()
                if not rows:
                    return None
                r = rows[0]
                x = {k: int(r[k]) for k in extras}
                return {"value": r["v"], "name": r["athlete_name"], "position": "", "extra": x or None,
                        "league_rank": lr[r["athlete_id"]] if lr[r["athlete_id"]] <= 3 else None}
            out.append({"key": key, "label": label, "away": pick(a_id), "home": pick(h_id)})
        return out

    def trend(tid, week):
        """AP rank by poll week through `week`: an int, "RV", or None (unranked)."""
        pts = []
        for w in sorted(polls):
            if w > week:
                break
            ranked, others = polls[w]
            pts.append((w, ranked.get(tid) or ("RV" if tid in others else None)))
        return pts

    season_weeks, details, tracked_by_week, rank_by_week = [], {}, {}, {}
    for wk in sorted({g["week"] for g in games}):
        ranked, others = polls[min(wk, now_week)] if wk >= 1 else polls[1]
        tracked = set(ranked) | set(others)
        tracked_by_week[str(wk)] = {abbr_of(teams, t) for t in tracked}
        rank_by_week[str(wk)] = {abbr_of(teams, t): r for t, r in ranked.items()}
        r_before = ranks_before(wk)
        wk_games = []
        for g in games:
            if g["week"] != wk or not ({g["home_id"], g["away_id"]} & tracked):
                continue
            gid, final = g["game_id"], bool(g["completed"])
            day, tm = eastern(g["start_date"])
            gametime = None if g["start_time_tbd"] else tm
            sides = {}
            for side, tid, pts in (("away", g["away_id"], g["away_points"]), ("home", g["home_id"], g["home_points"])):
                rec, last, streak = record(tid, through_game=gid) if final else record(tid, before_week=wk)
                crec = (record(tid, through_game=gid, conf_only=True) if final else record(tid, before_week=wk, conf_only=True))[0]
                conf = (teams.get(tid) or {}).get("conference") or ""
                sides[side] = {"team": abbr_of(teams, tid), "tid": tid, "record": rec, "score": pts if final else None,
                               "last": last, "streak": streak, "rank": ranked.get(tid),
                               "ranks": r_before.get(tid) or {}, "trend": trend(tid, min(wk, now_week)),
                               "fbs": tid in fbs,
                               "conf": {"name": CONF_NAME.get(conf, conf), "short": CONF_SHORT.get(conf, conf),
                                        "rec": None if conf in ("FBS Independents", "") else crec}}
            home_t = teams.get(g["home_id"]) or {}
            city = ", ".join(x for x in (home_t.get("city"), home_t.get("state")) if x)
            m = {"game_id": str(gid), "gameday": day, "gametime": gametime, "networks": tv.get(gid) or None,
                 "final": final, "neutral": bool(g["neutral_site"]),
                 "away": {k: sides["away"][k] for k in ("team", "record", "score")},
                 "home": {k: sides["home"][k] for k in ("team", "record", "score")}}
            wk_games.append(m)
            details[str(gid)] = dict(
                m, week=wk, week_key=str(wk), week_label=f"Week {wk}", game_type="REG", away=sides["away"], home=sides["home"],
                score={"away": g["away_points"], "home": g["home_points"]} if final else None,
                venue={"city": g["venue"] if g["neutral_site"] else city},
                leaders=leaders_before(wk, g["away_id"], g["home_id"]), leaders_scope="season")
        season_weeks.append({"key": str(wk), "label": f"Week {wk}", "game_type": "REG", "games": wk_games})
    data = {"season": SEASON, "season_weeks": season_weeks, "current_week_key": str(now_week)}
    return data, details, tracked_by_week, rank_by_week


# ---------------------------------------------------------------- Matchups (matchup.py's inputs)

PBP_COLS = ["week", "season_type", "pos_team", "def_pos_team", "EPA", "rush", "pass", "pass_attempt", "sack", "completion",
            "rush_player_id", "reception_player_id", "target_player_id", "receiver_player_name", "yds_rushed",
            "yds_receiving"]
OFF_POS = {"QB", "RB", "FB", "WR", "TE"}


def matchup_inputs(teams, now_week):
    """(player_weeks, defense) shaped the way matchup.py takes them from the NFL build.

    player_weeks {abbr: [{"pos", "wk", "att", "pyds", "pepa", "sk", "car", "ryds", "tgt", "rpepa", "repa",
    "reyds"}]}, totaled from cfbfastR's play-by-play, each play's EPA to:
      - the team's QBs as one row a week, every dropback (attempts and sacks) -- ESPN's passer ids are
        missing on whole teams' plays (South Florida: 158 of 164), and the card only counts QBs as a group
      - the target: reception_player_id on a catch, target_player_id on an incompletion (cfbfastR fills
        one or the other), else the receiver's name on the team's roster
      - the rusher, by rush_player_id
    positions from ESPN's rosters. ~92% of passes and runs carry an id; a few teams far fewer (Nebraska's
    receivers 40%), so their RB / WR / TE rates rest on fewer plays.
    defense {abbr: {...}} -- sportsdataverse's cfb_defense_vs_position (the NFL file's columns, FBS
    defenses), plus QB passing yards an attempt allowed, totaled from the same plays."""
    pbp = pl.read_parquet(io.BytesIO(_get(f"{REL}/cfbfastR_cfb_pbp/play_by_play_{SEASON}.parquet",
                                          f"play_by_play_{SEASON}.parquet")), columns=PBP_COLS)
    roster = parquet("espn_cfb_rosters", f"cfb_rosters_{SEASON}.parquet")
    abbr_by_id = {tid: t.get("abbreviation") for tid, t in teams.items()}
    pos_by_id = roster.select(pl.col("athlete_id").cast(pl.Int64).alias("pid"),
                              pl.col("position_abbreviation").alias("pos_id")).unique("pid")
    pos_by_name = (roster.select(pl.col("team_id").cast(pl.Int64).replace_strict(abbr_by_id, default=None).alias("team"),
                                 pl.col("display_name").alias("rname"), pl.col("position_abbreviation").alias("pos_nm"))
                   .unique(["team", "rname"]))
    dvp = parquet("cfb_defense_vs_position", f"cfb_defense_vs_position_{SEASON}.parquet")
    by_school = {}
    for t in sorted(teams.values(), key=lambda t: t.get("classification") != "fbs"):   # FBS first
        by_school.setdefault(t.get("school"), t.get("abbreviation"))
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
    player_weeks = {}
    for r in per_week.filter(pl.col("pos").is_in(list(OFF_POS))).sort("wk").iter_rows(named=True):
        player_weeks.setdefault(r["team"], []).append(r)

    rows_d = [dict(r, team=abbr_by_id.get(r["team_id"])) for r in dvp.filter(pl.col("division") == "fbs").iter_rows(named=True)]
    defense = matchup.defense_table([r for r in rows_d if r["team"]])
    qb = passing.group_by("dteam").agg(pl.col("pyds").sum(), pl.col("att").sum())
    for r in qb.iter_rows(named=True):
        if r["dteam"] in defense and r["att"]:
            defense[r["dteam"]]["pass"] = r["pyds"] / r["att"]
    return player_weeks, defense


# ---------------------------------------------------------------- helmets

def write_helmets(teams, abbrs):
    for sub, width in (("", helmets.OUTLINE_WIDTH), (helmets.LARGE_DIR, helmets.LARGE_OUTLINE_WIDTH)):
        folder = os.path.join(OUT, "helmets", sub)
        os.makedirs(folder, exist_ok=True)
        for tid, t in teams.items():
            a = t.get("abbreviation")
            if a not in abbrs:
                continue
            ok = lambda c: isinstance(c, str) and re.fullmatch(r"#?[0-9A-Fa-f]{6}", c)
            shell = t.get("color") if ok(t.get("color")) else helmets.FALLBACK_COLORS[0]
            alt = t.get("alt_color") if ok(t.get("alt_color")) else helmets.FALLBACK_COLORS[1]
            for mir in (False, True):
                name = f"{file_of(a)}-mirrored.svg" if mir else f"{file_of(a)}.svg"
                with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
                    f.write(helmets.helmet_svg(a, mirrored=mir, outline_width=width, colors=(shell, alt, alt)))


def helmet_filename(team, mirrored=False, large=False):
    name = f"{file_of(team or '_')}-mirrored.svg" if mirrored else f"{file_of(team or '_')}.svg"
    return f"{helmets.LARGE_DIR}/{name}" if large else name


# ---------------------------------------------------------------- rank trend (Page 1 team cards)

def trend_svg(pts, compact=False):
    """AP rank by poll week: 1 at the top, 25 at the bottom, a dashed "RV" lane under it for weeks in the
    receiving votes; unranked weeks leave a gap. compact (the condensed card): no labels, and the chart
    keeps its proportions (Jason, 2026-10-12) -- as tall as the card allows and only as wide as that
    height calls for, so a narrow card shrinks it whole instead of squashing the weeks together."""
    w, h = 300, 92
    lpad, rpad, tpad, bpad = (8, 8, 6, 6) if compact else (24, 10, 6, 6)
    n = len(pts)
    x = lambda i: lpad + (w - lpad - rpad) * (i / max(1, n - 1))
    rv = 28
    y = lambda r: tpad + (h - tpad - bpad) * ((min(r, rv) - 1) / (rv - 1))
    val = lambda r: rv if r == "RV" else r
    grid = "".join(
        f'<line x1="{lpad}" x2="{w - rpad}" y1="{y(r):.1f}" y2="{y(r):.1f}" class="apt-g{" apt-rv" if r == rv else ""}"/>'
        + ("" if compact else f'<text x="{lpad - 5}" y="{y(r) + 3.5:.1f}" class="apt-l">{"RV" if r == rv else r}</text>')
        for r in ((1, 25, rv) if compact else (1, 10, 25, rv)))
    segs, cur = [], []
    for i, (_w, r) in enumerate(pts):
        if r is None:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append((x(i), y(val(r))))
    if cur:
        segs.append(cur)
    lines = "".join(f'<polyline points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in s)}" class="apt-line"/>' for s in segs if len(s) > 1)
    dots = "".join(f'<circle cx="{x(i):.1f}" cy="{y(val(r)):.1f}" r="{4 if i == n - 1 else 2.6}" class="apt-dot{" apt-now" if i == n - 1 else ""}"/>'
                   for i, (_w, r) in enumerate(pts) if r is not None)
    fit = "xMidYMid meet" if compact else "none"
    return (f'<svg class="tsvg" viewBox="0 0 {w} {h}" preserveAspectRatio="{fit}" aria-hidden="true">{grid}{lines}{dots}</svg>')


def trend_html(side, compact=False):
    pts = side.get("trend") or []
    if not pts:
        return ""
    if all(r is None for _w, r in pts):   # never in the poll: no chart, just say so
        return (f'<div class="apt{" c-trend" if compact else ""} apt-none"><div class="tr-head"><span class="tr-lbl">AP{"" if compact else " Rank"}</span>'
                f'<span class="tr-now">NR</span></div><p class="tr-note">Not ranked this season</p></div>')
    now = pts[-1][1]
    now_txt = f"#{now}" if isinstance(now, int) else "RV" if now == "RV" else "NR"
    best = min((r for _w, r in pts if isinstance(r, int)), default=None)
    weeks = "".join(f"<span>{'Pre' if w == 1 else w}</span>" for w, _r in pts)
    if compact:
        return (f'<div class="apt c-trend"><div class="tr-head"><span class="tr-lbl">AP</span>'
                f'<span class="tr-now">{now_txt}</span></div>{trend_svg(pts, True)}</div>')
    sub = f"Best #{best}" if best else "Not ranked yet"
    return (f'<div class="apt"><div class="tr-head"><span class="tr-lbl">AP Rank</span><span class="tr-sub">{sub}</span>'
            f'<span class="tr-now">{now_txt}</span></div>{trend_svg(pts)}<div class="tr-weeks">{weeks}</div></div>')


TREND_CSS = """
.apt{display:flex;flex-direction:column;gap:4px;width:100%}
.tr-head{display:flex;align-items:baseline;gap:8px}
.tr-lbl{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--aag-text-2)}
.tr-sub{font-size:12px;color:var(--aag-text-3)}
.tr-now{margin-left:auto;font-size:22px;font-weight:900;font-variant-numeric:tabular-nums}
.tsvg{width:100%;height:92px;overflow:visible}
.apt-g{stroke:var(--aag-tile-border-soft,rgba(0,0,0,.08));stroke-width:1;vector-effect:non-scaling-stroke}
.apt-rv{stroke-dasharray:3 3}
.apt-l{font:600 9px Inter,system-ui,sans-serif;fill:var(--aag-text-3);text-anchor:end}
.apt-line{fill:none;stroke:var(--aag-text);stroke-width:2;stroke-linejoin:round;stroke-linecap:round;vector-effect:non-scaling-stroke}
.apt-dot{fill:var(--aag-text)}
.apt-now{stroke:var(--aag-bg,#fff);stroke-width:1.5}
.tr-weeks{display:flex;justify-content:space-between;padding:0 10px 0 24px;font-size:10px;color:var(--aag-text-3);font-variant-numeric:tabular-nums}
.tr-weeks span{width:0;display:flex;justify-content:center;white-space:nowrap}
.c-team>.c-trend-wrap{grid-row:4;align-self:start;width:100%;display:flex;flex-direction:column;align-items:center;gap:4px}
/* conference + conference record, under the record */
.cf{display:flex;justify-content:center;align-items:baseline;gap:8px;font-size:13px;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;color:var(--aag-text-2);margin:-6px 0 14px}
.cf-r{font-weight:400;letter-spacing:.02em;color:var(--aag-text-3);font-variant-numeric:tabular-nums}
.cf-r::before{content:"·";margin-right:8px}
.c-team .cf{font-size:10px;gap:5px;margin:0}
.c-team .cf-r::before{margin-right:5px}
.tr-note{font-size:12px;color:var(--aag-text-3);text-align:center;margin:2px 0 0}
.apt-none:not(.c-trend) .tr-note{text-align:left}
.c-trend{gap:2px;margin:2px 0}
.c-trend .tr-head{justify-content:center}
.c-trend .tr-lbl{font-size:10px}
.c-trend .tr-now{margin-left:0;font-size:14px}
.c-trend .tsvg{width:100%;height:auto;aspect-ratio:300/92;max-height:clamp(34px,6.2vh,56px)}
.c-trend .apt-l{font-size:8px}
.c-trend .tr-note{display:none}   /* "AP NR" says it on the small card */
/* short phones (iPhone SE): the small card keeps "AP #4" and drops the chart, so the ranks still fit */
@media (max-height:640px){.c-trend .tsvg{display:none}}
"""


def conf_html(side, compact=False):
    """The team's conference and its record in conference games: "Big Ten · 3-0" (the condensed card
    "B1G · 3-0"); independents just "Independent"."""
    c = side.get("conf") or {}
    if not c.get("name"):
        return ""
    name = c["short"] if compact else c["name"]
    r = c.get("rec")
    rec = f'<span class="cf-r">{r["wins"]}-{r["losses"]}{"" if compact else " conf"}</span>' if r else ""
    return f'<div class="cf"><span class="cf-n">{rs.esc(name)}</span>{rec}</div>'


def c_team(side, label, final=False):
    html = ORIG_C_TEAM(side, label, final)
    body = f'<div class="c-trend-wrap">{conf_html(side, True)}{trend_html(side, compact=True)}</div>'
    return re.sub(r'<ul class="injuries c-inj">.*?</ul>', lambda _m: body, html, count=1, flags=re.S)


def l_team(side, final=False):
    html = ORIG_L_TEAM(side, final)
    return re.sub(r'<ul class="l-inj">.*?</ul>', lambda _m: conf_html(side) + trend_html(side), html, count=1, flags=re.S)


def rank_color(n):
    """The 32-step green-to-red scale stretched over the 138 FBS teams."""
    i = round((max(1, min(N_FBS, n)) - 1) * 31 / (N_FBS - 1))
    return p1.RANK_COLORS[i]


# ---------------------------------------------------------------- rank badges (Page 0 and Page 1's top bar)

BADGE_CSS = """
.rk{font-family:Inter,system-ui,sans-serif;font-style:normal;font-weight:700;font-size:.6em;color:var(--text-2);
  margin-right:.18em;vertical-align:.2em;letter-spacing:0}
/* under the helmet the number hangs off the abbreviation's left, so the abbreviation stays centered */
.team .abbr{position:relative}
.team .rk{position:absolute;right:100%;top:.2em;line-height:1}
/* condensed: inline and smaller, the abbreviation's slot a little wider so the records still line up */
[data-view=condensed] .abbr-c{min-width:3.5em;margin-right:2px}
[data-view=condensed] .abbr-c .rk{font-size:.58em;margin-right:.12em}
"""


def badge_week(html, ranks):
    """Each ranked team's abbreviation on a week's tiles (and Teams on Bye) gets its AP rank ahead of it."""
    def sub(m):
        a = m.group(2)
        r = ranks.get(rh.esc(a)) or ranks.get(a)
        return f'{m.group(1)}<span class="rk">{r}</span>{a}</span>' if r else m.group(0)
    return re.sub(r'(<span class="abbr(?: abbr-c)?"(?: aria-hidden="true")?>)([^<]+)</span>', sub, html)


# ---------------------------------------------------------------- Rankings page

RK_CSS = """
.rk-row{display:grid;grid-template-columns:20px 30px minmax(0,1fr) 34px 34px 74px;
  align-items:center;column-gap:4px;padding:0 4px;font-size:13px;font-variant-numeric:tabular-nums;
  border-bottom:1px solid var(--aag-tile-border-soft)}
.rk-row.end,.rk-row.head{border-bottom:0}
.rk-row.head{padding:0 4px 4px;font-size:10px;font-weight:700;letter-spacing:.04em;color:var(--text-3);align-items:end}
.rk-row.head .grp{grid-column:1/4}
.pc-long .rk-row:not(.head){padding-top:6px;padding-bottom:6px}
.rk-n{font-size:13px;font-weight:700;text-align:right}
.mv{font-size:11px;font-weight:700;text-align:center;white-space:nowrap}
.mv.up{color:#1E8A3C}.mv.dn{color:#A00000}.mv.new{color:var(--text-2);font-size:9px;letter-spacing:.06em}.mv.eq{color:var(--text-3)}
.pts{text-align:right;padding-right:4px}
.fpv{color:var(--text-3);font-size:11px;margin-left:3px}
.conf{color:var(--text-2);font-size:11px;font-weight:700;letter-spacing:.03em;text-align:center}
.rv .rk-row:not(.head){padding-top:5px;padding-bottom:5px}
/* the school's full name (Jason, 2026-10-12): Inter, wrapping to a second line only for the longest */
.who .school{font-size:13px;font-weight:700;line-height:1.15;min-width:0;overflow-wrap:anywhere}
.drop .school{font-weight:700;color:var(--text)}
/* CFP, before its first rankings */
.soon{display:flex;flex-direction:column;align-items:center;text-align:center;gap:6px;padding:28px 8px 0}
.soon h2{font-size:15px;font-weight:900;letter-spacing:.1em;text-transform:uppercase}
.soon .lead{font-size:14px;color:var(--text-2);max-width:30em;line-height:1.4}
.soon .big{font-size:28px;font-weight:900;margin:6px 0 2px}
.soon .sub{font-size:12px;color:var(--text-3)}
.soon ol{list-style:none;margin:18px 0 0;padding:0;width:100%;max-width:300px}
.soon li{display:flex;justify-content:space-between;padding:7px 4px;border-bottom:1px solid var(--aag-tile-border-soft);font-size:13px;
  font-variant-numeric:tabular-nums}
.soon li:last-child{border-bottom:0}
.soon li span:first-child{color:var(--text-2)}
.soon li.sel span:last-child{font-weight:700}
.drop{margin-top:16px;font-size:12px;color:var(--text-2);line-height:1.5;padding:0 4px}
.drop b{font-size:11px;letter-spacing:.06em;text-transform:uppercase;margin-right:6px}
.drop .abbr{font-size:13px;color:var(--text)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .mv.up{color:#4CC46F}:root:not([data-theme=light]) .mv.dn{color:#FF6B5E}}
:root[data-theme=dark] .mv.up{color:#4CC46F}:root[data-theme=dark] .mv.dn{color:#FF6B5E}
"""


def rankings_page(current, teams, records, now_week, prefix=""):
    polls = current["rankings"]
    views = [("ap", "AP Poll", next(r for r in polls if r["name"].startswith("AP"))),
             ("coaches", "Coaches Poll", next(r for r in polls if r["name"].startswith("AFCA"))),
             # the committee's rankings once ESPN carries them; until then None -> when they come out
             ("cfp", "CFP", next((r for r in polls if "Playoff" in r["name"] or r["name"].startswith("CFP")), None))]

    def who(t):
        a = t["team"]["abbreviation"]
        return (f'<span class="who">{p1.helmet_img(a, rs.HELMET, prefix="")}'
                f'<span class="school">{rs.esc(t["team"].get("location") or a)}</span></span>')

    def conf(t):
        c = (teams.get(int(t["team"]["id"])) or {}).get("conference") or ""
        return CONF_SHORT.get(c, c[:4].upper())

    def rec(t):
        r = records.get(int(t["team"]["id"]))
        return f'{r["wins"]}-{r["losses"]}' if r else "—"

    def move(t):
        cur, prev = t["current"], t["previous"]
        if not prev:
            return '<span class="mv new">NEW</span>'
        d = prev - cur
        return (f'<span class="mv up">▲{d}</span>' if d > 0 else f'<span class="mv dn">▼{-d}</span>' if d < 0
                else '<span class="mv eq">–</span>')

    def row(t, i, n, rv=False):
        fpv = t.get("firstPlaceVotes") or 0
        pts = f'{int(t.get("points") or 0):,}' + (f'<span class="fpv">({fpv})</span>' if fpv else "")
        mv = ('<span class="mv dn">▼</span>' if t.get("previous") else '<span></span>') if rv else move(t)
        return (f'<div class="rk-row{" end" if i == n else ""}"><span class="rk-n">{"" if rv else t["current"]}</span>{mv}'
                f'{who(t)}<span class="n">{rec(t)}</span><span class="conf">{conf(t)}</span><span class="pts">{pts}</span></div>')

    def head(label):
        return (f'<div class="rk-row head"><span class="grp">{label}</span>'
                '<span class="n">REC</span><span class="n">CONF</span><span class="pts">PTS</span></div>')

    def deck(p):
        ranks, others = p["ranks"], p.get("others") or []
        # dropped out: only the teams that fell out of the votes entirely (the rest are under Receiving votes, marked ▼)
        rv_ids = {t["team"]["id"] for t in others}
        dropped = [t for t in p.get("droppedOut") or [] if t["team"]["id"] not in rv_ids]
        top = "".join(row(t, i, len(ranks)) for i, t in enumerate(ranks, 1))
        rv = "".join(row(t, i, len(others), rv=True) for i, t in enumerate(others, 1))
        drop = ("<p class='drop'><b>Dropped out</b>" + ", ".join(
            f'<span class="school">{rs.esc(t["team"].get("location") or t["team"]["abbreviation"])}</span> ({t["previous"]})'
            for t in dropped) + "</p>") if dropped else ""
        key = ('<article class="pc pc-key">' + rs._peek("Receiving Votes", up=True) +
               '<footer class="legend"><h3>Key</h3><dl>'
               '<div><dt>▲ ▼</dt><dd>Places up or down from last week\'s poll</dd></div>'
               '<div><dt>NEW</dt><dd>Not ranked last week</dd></div>'
               '<div><dt>REC</dt><dd>Record this season</dd></div>'
               '<div><dt>CONF</dt><dd>Conference</dd></div>'
               '<div><dt>PTS</dt><dd>Poll points: 25 for a first-place vote down to 1 for 25th; first-place votes in ( )</dd></div>'
               '</dl><p class="note">Receiving Votes: teams outside the 25 that still got points, most first. ▼ = ranked last week.</p></footer></article>')
        return (f'<article class="pc pc-long"><div class="pc-body"><section class="grp-box">{head("Top 25")}{top}</section></div>'
                f'{rs._peek("Receiving Votes")}</article>'
                f'<article class="pc">{rs._peek("Top 25", up=True)}<div class="pc-body"><section class="grp-box rv">'
                f'{head("Receiving votes")}{rv}</section>{drop}</div>{rs._peek("Key")}</article>{key}')

    def soon():
        (d0, first), rest = CFP_DATES[0], CFP_DATES[1:]
        dates = "".join(f'<li{" class=sel" if i == len(rest) - 1 else ""}><span>{"Selection Day" if i == len(rest) - 1 else "Update"}</span>'
                        f'<span>{day}, {d}</span></li>' for i, (day, d) in enumerate(rest))
        return ('<article class="pc"><div class="soon"><h2>College Football Playoff</h2>'
                "<p class='lead'>The selection committee's first Top 25 comes out</p>"
                f'<p class="big">{"Tuesday" if d0 == "Tue" else d0}, {first}</p><p class="sub">on ESPN · the 12-team field is set Sunday, Dec 6</p>'
                f'<ol>{dates}</ol></div></article>')

    tabs = "".join(f'<button class="sw-tab{" on" if i == 0 else ""}" type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" '
                   f'data-view="{k}">{label}</button>' for i, (k, label, _p) in enumerate(views))
    panes = "".join(f'<section class="pane" data-pane="{k}" role="tabpanel" aria-label="{label}"><div class="pane-in">{deck(p) if p else soon()}</div></section>'
                    for k, label, p in views)
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        f"<script>{theme.THEME_HEAD_JS}</script><title>{SEASON} Rankings · At A Glance</title>{logo.favicon_links('../')}"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
        f"<style>{theme.THEME_CSS}{theme.MENU_CSS}{theme.HELMET_SHADOW_CSS}{rs.CSS}{RK_CSS}</style></head><body>"
        f"<header class='top'><div class='top-in'><h1 class='title'><span class='yr abbr'>{SEASON}</span>"
        f"<span class='rs-line'><span class='rs'>Rankings</span><span class='thru'>Week {now_week}</span></span></h1>"
        f"<div class='sw' role='tablist' aria-label='Poll'>{tabs}</div></div></header>"
        f"<main class='track' id='track'>{panes}</main>"
        "<nav class='bottombar' aria-label='Page controls'><div class='bar-in'>"
        f"{theme.menu_html('../', 'standings')}<a class='week' href='index.html#week-{now_week}'>{p1.CHEV}<span>Week {now_week}</span></a>"
        "</div></nav>"
        f"<script>{theme.THEME_JS}</script><script>{rs.JS}</script></body></html>"
    )


# ---------------------------------------------------------------- main

def main():
    global ORIG_C_TEAM, ORIG_L_TEAM
    teams, sched, tbox, pbox, current, now_week, polls, tv = load()
    data, details, tracked_by_week, rank_by_week = build(teams, sched, tbox, pbox, now_week, polls, tv)

    abbrs = {s["team"] for d in details.values() for s in (d["away"], d["home"])}
    abbrs |= {t["team"]["abbreviation"] for r in current["rankings"] for t in r.get("ranks", []) + r.get("others", []) + r.get("droppedOut", [])}
    write_helmets(teams, abbrs)

    # the page code, pointed at college teams: helmets, and each team's colors for its pill and the
    # Matchups chart (helmets.PILL_COLORS / TEAM_COLORS, which team_line_colors picks from)
    helmets.helmet_filename = helmet_filename
    ok = lambda c: isinstance(c, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", c)
    for t in teams.values():
        a = t.get("abbreviation")
        if a in abbrs and ok(t.get("color")):
            alt = t.get("alt_color") if ok(t.get("alt_color")) else helmets.FALLBACK_COLORS[1]
            helmets.PILL_COLORS[a] = helmets.TEAM_COLORS[a] = (t["color"], alt)
            helmets.EAR_COLORS[a] = alt
            helmets.SHADING_OVERRIDES.pop(a, None)
    names = {t["abbreviation"]: t.get("school") for t in teams.values() if t.get("abbreviation")}
    for a in abbrs:
        rh.TEAM_NAMES[a] = p1.TEAM_NAMES[a] = tp.LOCATION_NAMES[a] = names.get(a, a)
    ORIG_C_TEAM, ORIG_L_TEAM = p1.c_team, p1.l_team
    p1.c_team, p1.l_team, p1.rank_color = c_team, l_team, rank_color
    p1.P1_CSS += TREND_CSS + BADGE_CSS
    # Teams on Bye: that week's poll teams without a game (weeks_for_page0 passes each week's own list)
    week_of_list = {id(w["games"]): w["key"] for w in data["season_weeks"]}
    rh.bye_teams = lambda games: sorted(tracked_by_week.get(week_of_list.get(id(games)), set())
                                        - {(m.get(s) or {}).get("team") for m in games for s in ("away", "home")})

    # Matchups: games not yet played get the season so far, finished ones their own numbers against both
    # units' averages -- as on the NFL pages (render_page1.write_all), the edge needing the same quarter of
    # the field: 8 places of 32 there, a quarter of the FBS teams here
    player_weeks, defense = matchup_inputs(teams, now_week)
    fbs_abbrs = {t["abbreviation"] for t in teams.values() if t.get("classification") == "fbs"}
    lg = matchup.league({t: r for t, r in player_weeks.items() if t in fbs_abbrs}, defense)
    n_teams = len(defense)
    matchup.EDGE_GAP = round(8 / 32 * n_teams)
    opponents = {}
    for g in sched.iter_rows(named=True):
        a_t, h_t = abbr_of(teams, g["away_id"]), abbr_of(teams, g["home_id"])
        opponents[(a_t, g["week"])], opponents[(h_t, g["week"])] = h_t, a_t
    n_mu = 0
    for d in details.values():
        a_t, h_t = d["away"]["team"], d["home"]["team"]
        try:
            mu = (matchup.final_data(player_weeks, d["week"], a_t, h_t, opponents) if d["final"]
                  else matchup.card_data(lg, a_t, h_t))
        except Exception:
            mu = None
        if mu:
            d["matchup"] = mu
            n_mu += 1

    os.makedirs(os.path.join(OUT, "game"), exist_ok=True)
    orig_panel = rh.render_week_panel
    rh.render_week_panel = lambda key, label, games, cur, byes=None: badge_week(
        orig_panel(key, label, games, cur, byes), rank_by_week.get(key, {}))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(rh.render_page0(data).replace("</style>", BADGE_CSS + "</style>", 1))
    rh.render_week_panel = orig_panel
    if os.path.exists(os.path.join(OUT, "index-b.html")):
        os.remove(os.path.join(OUT, "index-b.html"))

    for gid, d in details.items():
        html = p1.render_standalone(d)
        ranks = {d["away"]["team"]: d["away"]["rank"], d["home"]["team"]: d["home"]["rank"]}
        html = re.sub(r'(<div class="side (?:away|home)">(?:(?!</div>).)*?<span class="abbr">)([^<]+)</span>',
                      lambda m: f'{m.group(1)}<span class="rk">{ranks[m.group(2)]}</span>{m.group(2)}</span>'
                      if ranks.get(m.group(2)) else m.group(0), html, flags=re.S)
        html = html.replace("rank among 32 teams", f"rank among {n_teams} FBS teams")
        if d.get("neutral"):
            html = html.replace('<span class="at">@</span>', '<span class="at">vs</span>')
        with open(os.path.join(OUT, "game", f"{gid}.html"), "w", encoding="utf-8") as f:
            f.write(html)

    records = {}
    for g in sched.iter_rows(named=True):
        if g["completed"] and g["home_points"] is not None:
            for me, mine, theirs in ((g["home_id"], g["home_points"], g["away_points"]), (g["away_id"], g["away_points"], g["home_points"])):
                r = records.setdefault(me, {"wins": 0, "losses": 0})
                r["wins" if mine > theirs else "losses"] += 1
    with open(os.path.join(OUT, "rankings.html"), "w", encoding="utf-8") as f:
        f.write(rankings_page(current, teams, records, now_week))
    print(f"Wrote {OUT}: Page 0, {len(details)} game pages ({n_mu} with Matchups), rankings.html")


if __name__ == "__main__":
    main()

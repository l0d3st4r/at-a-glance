"""
College football data client (2026-10-12), the CFB counterpart of nflverse_client.py / nba_client.py.

Where the data comes from (worked out in mockups/build_cfb_mockup.py):

  sportsdataverse-data releases   ESPN and CFBD data that the sportsdataverse project (cfbfastR) posts as
                                  plain files on GitHub, one a season -- the same model as nflverse. Every
                                  file below was refreshed daily through the 2026 season:
      cfb_team_info               every school: abbreviation, conference, classification (fbs / fcs / ii /
                                  iii), colors, home stadium with its location, dome and grass
      cfb_schedules               every game: week, kickoff (UTC), neutral site, conference game, scores,
                                  bowl / playoff names; past seasons too (the last meeting)
      espn_cfb_team_box           each team's box score a game (yards, 3rd downs, penalties, turnovers)
      espn_cfb_player_box         each player's box score lines a game, a row per category
      espn_cfb_linescores         points by quarter
      espn_cfb_rosters            positions and jersey numbers
      cfbfastR_cfb_pbp            play-by-play with EPA (~60 MB a season; only the columns asked for are kept)
      cfb_defense_vs_position     what each FBS defense allows to QBs / RBs / WRs / TEs -- the NFL file's columns
  ESPN's APIs                     the polls and what the files don't carry:
      site rankings               this week's AP, Coaches and (from November) CFP rankings with points,
                                  first-place votes, previous rank, receiving votes and dropped out
      core rankings               any past week's AP poll with its receiving votes (week 1 = preseason)
      site scoreboard             TV networks, scores newer than the files, neutral-site venues
      core coaches                each school's head coach (two requests a school, so the build caches it)
    ESPN blocked the NFL side's scripted requests on 2026-09-16, but these answered from GitHub Actions
    for the NBA section and from here. Everything else works without them: no rankings means no poll
    teams, so the build reports that rather than guessing.

Same defensive pattern as the other clients: every get_* function returns (value, error) and never raises.
Seasons are keyed by the year they start (2026 = the 2026 season, bowls in January 2027 included).
"""

import datetime
import io
import json
import re
import time

import requests

RELEASES = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"
SITE_API = "https://site.api.espn.com/apis/site/v2/sports/football/college-football"
CORE_API = "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football"
TIMEOUT = 60
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}

PBP_COLUMNS = ["game_id", "week", "season_type", "pos_team", "def_pos_team", "EPA", "rush", "pass", "pass_attempt",
               "sack", "completion", "rush_player_id", "reception_player_id", "target_player_id", "receiver_player_name",
               "completion_player_id", "incompletion_player_id", "interception_thrown_player_id", "sack_taken_player_id",
               "fumble_forced_player_id", "yds_rushed", "yds_receiving"]


def current_season(today=None):
    """College seasons start in late August and end with the title game in January."""
    today = today or datetime.date.today()
    return today.year if today.month >= 3 else today.year - 1


def _get(url, tries=2):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, timeout=TIMEOUT, headers=UA)
            if r.status_code == 404:
                raise FileNotFoundError(f"{url} isn't published")
            r.raise_for_status()
            return r
        except FileNotFoundError:
            raise
        except Exception as e:   # one retry for a network blip
            last = e
            time.sleep(2 * (i + 1))
    raise last


def _parquet(tag, name, columns=None):
    import polars as pl
    return pl.read_parquet(io.BytesIO(_get(f"{RELEASES}/{tag}/{name}").content), columns=columns)


def _rows(tag, name, columns=None):
    try:
        return _parquet(tag, name, columns).to_dicts(), None
    except Exception as e:
        return [], f"{tag}/{name}: {e}"


def get_team_info(season):
    return _rows("cfb_team_info", f"cfb_team_info_{season}.parquet")


def get_schedule(season):
    return _rows("cfb_schedules", f"cfb_schedules_{season}.parquet")


def get_team_box(season):
    return _rows("espn_cfb_team_box", f"team_box_{season}.parquet")


def get_player_box(season):
    return _rows("espn_cfb_player_box", f"player_box_{season}.parquet")


def get_linescores(season):
    return _rows("espn_cfb_linescores", f"linescores_{season}.parquet")


def get_rosters(season):
    return _rows("espn_cfb_rosters", f"cfb_rosters_{season}.parquet",
                 ["athlete_id", "team_id", "position_abbreviation", "display_name", "jersey"])


def get_defense_vs_position(season):
    return _rows("cfb_defense_vs_position", f"cfb_defense_vs_position_{season}.parquet")


def get_pbp(season):
    """The play-by-play as a polars DataFrame (PBP_COLUMNS only) -- kept as a frame, it's ~150k plays."""
    try:
        return _parquet("cfbfastR_cfb_pbp", f"play_by_play_{season}.parquet", PBP_COLUMNS), None
    except Exception as e:
        return None, f"cfbfastR_cfb_pbp: {e}"


def get_schedule_history(season, years=12):
    """Finished games of the `years` seasons before this one, for the last meeting (oldest first)."""
    out, errors = [], []
    for y in range(season - years, season):
        rows, err = _rows("cfb_schedules", f"cfb_schedules_{y}.parquet",
                          ["season", "start_date", "home_id", "away_id", "home_points", "away_points", "completed",
                           "season_type"])
        if err:
            errors.append(err)
        out += [r for r in rows if r.get("completed") and r.get("home_points") is not None]
    return out, ("; ".join(errors[:2]) if errors else None)


def release_timestamp(tag):
    """When sportsdataverse last uploaded a release ("2026-10-12 06:22:55 EDT"), for check_updates."""
    try:
        return _get(f"{RELEASES}/{tag}/timestamp.json").json().get("last_updated"), None
    except Exception as e:
        return None, str(e)


# ---------------------------------------------------------------- ESPN

def _team_id(entry):
    t = entry.get("team") or {}
    if t.get("id"):
        return int(t["id"])
    m = re.search(r"/teams/(\d+)", t.get("$ref") or "")
    return int(m.group(1)) if m else None


def _poll(entry_list):
    return [{"team_id": _team_id(e), "current": e.get("current"), "previous": e.get("previous"),
             "points": e.get("points"), "first_place_votes": e.get("firstPlaceVotes"),
             "location": (e.get("team") or {}).get("location")} for e in entry_list or [] if _team_id(e)]


def poll_key(r):
    """Which of the site's polls an ESPN ranking is -- "ap", "coaches", "cfp" -- or None. By ESPN's own poll id,
    not the name: the feed also carries the FCS Coaches Poll and the AFCA Division II Coaches Poll (since
    2026-10-12), and the Coaches tab is only ever the FBS AFCA Coaches Poll (Jason, 2026-10-12)."""
    pid, name, kind = str(r.get("id") or ""), r.get("name") or "", r.get("type") or ""
    if pid == "1" and name.startswith("AP"):
        return "ap"
    if pid == "2" and name == "AFCA Coaches Poll":
        return "coaches"
    if kind == "cfp" or "Playoff" in name:
        return "cfp"
    return None


def get_rankings_now():
    """This week's polls: {"ap" | "coaches" | "cfp": {"name", "week", "date", "ranks", "others", "dropped"}}.
    "week" is the poll's week (the poll before that week's games; 1 = preseason)."""
    try:
        d = _get(f"{SITE_API}/rankings").json()
    except Exception as e:
        return {}, f"ESPN rankings: {e}"
    out = {}
    for r in d.get("rankings") or []:
        key = poll_key(r)
        if not key or key in out:
            continue
        name = r.get("name") or ""
        occ = r.get("occurrence") or {}
        week = int(occ.get("value") or occ.get("number") or 0) if str(occ.get("value") or "").isdigit() else occ.get("number")
        out[key] = {"name": name, "week": week, "date": r.get("date"), "ranks": _poll(r.get("ranks")),
                    "others": _poll(r.get("others")), "dropped": _poll(r.get("droppedOut"))}
    return out, (None if out else "ESPN rankings: no polls in the response")


def get_ap_poll(season, week):
    """One week's AP poll -- {team_id: rank} and [receiving-votes team ids] -- or (None, error) if ESPN
    has none for that week. Week 1 is the preseason poll."""
    url = (f"{CORE_API}/seasons/{season}/types/1/weeks/1/rankings/1" if week == 1
           else f"{CORE_API}/seasons/{season}/types/2/weeks/{week}/rankings/1")
    try:
        d = _get(url).json()
    except Exception as e:
        return None, f"AP poll week {week}: {e}"
    if not d.get("ranks"):
        return None, f"AP poll week {week}: not out"
    return {"ranks": {str(_team_id(e)): e.get("current") for e in d["ranks"] if _team_id(e)},
            "others": [_team_id(e) for e in d.get("others") or [] if _team_id(e)]}, None


def get_scoreboard(season, week, season_type=2):
    """{game_id: {"networks", "status", "away_score", "home_score", "venue", "city", "state", "period"}} for
    one week of FBS games (groups=80) -- for TV, and finals newer than the schedule file."""
    try:
        d = _get(f"{SITE_API}/scoreboard?dates={season}&week={week}&seasontype={season_type}&groups=80&limit=400").json()
    except Exception as e:
        return {}, f"ESPN scoreboard week {week}: {e}"
    out = {}
    for ev in d.get("events") or []:
        try:
            c = ev["competitions"][0]
            nets = [n for b in c.get("broadcasts") or [] for n in b.get("names") or []]
            st = (c.get("status") or ev.get("status") or {}).get("type") or {}
            sides = {x.get("homeAway"): x for x in c.get("competitors") or []}
            score = lambda s: int(float(sides[s]["score"])) if s in sides and str(sides[s].get("score") or "").strip() else None
            v = c.get("venue") or {}
            addr = v.get("address") or {}
            out[str(ev["id"])] = {"networks": nets, "state": st.get("state"), "completed": bool(st.get("completed")),
                                  "period": (c.get("status") or {}).get("period"),
                                  "away_score": score("away"), "home_score": score("home"),
                                  "venue": v.get("fullName"), "city": addr.get("city"), "region": addr.get("state"),
                                  "indoor": v.get("indoor")}
        except Exception:
            continue
    return out, None


def get_head_coach(season, team_id):
    """The school's head coach's name, or (None, error)."""
    try:
        items = _get(f"{CORE_API}/seasons/{season}/teams/{team_id}/coaches").json().get("items") or []
        if not items:
            return None, "no coach listed"
        c = _get(items[0]["$ref"].replace("http://", "https://")).json()
        name = " ".join(x for x in (c.get("firstName"), c.get("lastName")) if x)
        return (name or None), (None if name else "coach without a name")
    except Exception as e:
        return None, str(e)


def to_json(obj):
    return json.dumps(obj, separators=(",", ":"), default=str)

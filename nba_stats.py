"""
Player numbers for the NBA pages (2026-10-08), the NBA counterpart of player_stats.py.

Built from build_nba_data.py's player_games (every player's line in every game, by team):
  Season(player_games)
    .lines(team, before)     each player's season to date before a day (YYYY-MM-DD): games played and
                             per-game averages -- the Player Stats page, the Leaders card
    .team_games(team, before)  how many games the team had played by then
    .tops(before)            the league's top 3 per game in each MEDAL_STATS stat by then -- the gold /
                             silver / bronze bars and the Leaders card's crowns
  game_lines(rows, game_id)  one game's box score, the same shape (gp = 1, "averages" = the game)

Season to date counts the regular season only, like the NFL pages; a playoff game's page shows the
whole regular season. Each team's running totals are snapshotted once per game day in one pass, so a
page asking "before this day" is a lookup, not a recount.

Per-game leaders, as the NBA lists them, count only players in 70% of their team's games so far
(QUALIFY_SHARE -- 58 of 82 at the end of a season). Percentages need made shots on top: 3.65 field
goals a team game for FG% (300 over a season), 1 three for 3P% (82) and 1.52 free throws for FT% (125).
"""

import bisect
from collections import defaultdict

COUNTING = ("min", "pts", "fgm", "fga", "tpm", "tpa", "ftm", "fta", "oreb", "dreb", "reb", "ast", "stl", "blk",
            "tov", "pf", "pm")
MEDAL_STATS = ("pts", "reb", "ast", "stl", "blk", "tpm")
QUALIFY_SHARE = 0.70
PCT_MINIMUMS = {"fg_pct": ("fgm", 3.65), "tp_pct": ("tpm", 1.0), "ft_pct": ("ftm", 1.52)}
REG = 2


def _line(pid, info, gp, totals, starts, team=None):
    out = {"id": pid, "name": info["name"], "pos": info["pos"], "jersey": info.get("jersey"), "gp": gp,
           "gs": starts, "team": team}
    for k in COUNTING:
        out[k + "_t"] = totals.get(k, 0)
        out[k] = out[k + "_t"] / gp if gp else 0.0
    out["fg_pct"] = 100 * out["fgm_t"] / out["fga_t"] if out["fga_t"] else None
    out["tp_pct"] = 100 * out["tpm_t"] / out["tpa_t"] if out["tpa_t"] else None
    out["ft_pct"] = 100 * out["ftm_t"] / out["fta_t"] if out["fta_t"] else None
    return out


def game_lines(rows, game_id):
    """One game's box score (players who got in), starters first, then by minutes."""
    out = [_line(r["id"], r, 1, {k: r.get(k) or 0 for k in COUNTING}, int(r["starter"]))
           for r in rows or [] if r["gid"] == game_id and not r["dnp"]]
    return sorted(out, key=lambda x: (not x["gs"], -x["min"], x["name"]))


def qualified(line, team_games, stat=None):
    """The NBA's minimums for its per-game leaders (see the module notes)."""
    if not team_games or line["gp"] < QUALIFY_SHARE * team_games:
        return False
    if stat in PCT_MINIMUMS:
        made, per = PCT_MINIMUMS[stat]
        return line[made + "_t"] >= per * team_games
    return True


class Season:
    def __init__(self, player_games):
        self.pg = player_games or {}
        self.days = {}    # team -> sorted game days
        self.snaps = {}   # team -> [(team games, {pid: (info, gp, gs, totals)}) after each of those days]
        for team, rows in self.pg.items():
            days, snaps = [], []
            gp, gs, tot, info, games = defaultdict(int), defaultdict(int), defaultdict(lambda: defaultdict(float)), {}, set()
            reg = sorted((r for r in rows if r["st"] == REG), key=lambda r: (r["date"], r["gid"]))
            for i, r in enumerate(reg):
                games.add(r["gid"])
                if not r["dnp"]:
                    pid = r["id"]
                    info[pid] = r
                    gp[pid] += 1
                    gs[pid] += r["starter"]
                    for k in COUNTING:
                        tot[pid][k] += r.get(k) or 0
                if i + 1 == len(reg) or reg[i + 1]["date"] != r["date"]:
                    days.append(r["date"])
                    snaps.append((len(games), {p: (info[p], gp[p], gs[p], dict(tot[p])) for p in gp}))
            self.days[team], self.snaps[team] = days, snaps
        self._tops = {}

    def _snap(self, team, before):
        i = bisect.bisect_left(self.days.get(team) or [], before) - 1
        return self.snaps[team][i] if i >= 0 else (0, {})

    def team_games(self, team, before):
        return self._snap(team, before)[0]

    def lines(self, team, before):
        """Each player who's played for this team before that day, most minutes first."""
        _n, players = self._snap(team, before)
        out = [_line(p, info, gp, tot, gs, team) for p, (info, gp, gs, tot) in players.items()]
        return sorted(out, key=lambda x: (-x["min_t"], x["name"]))

    def tops(self, before):
        """{(team, player id): {stat: 1 | 2 | 3}} -- the league's top 3 per game before that day."""
        if before in self._tops:
            return self._tops[before]
        pool = []
        for team in self.pg:
            n = self.team_games(team, before)
            pool += [x for x in self.lines(team, before) if qualified(x, n)]
        out = defaultdict(dict)
        for stat in MEDAL_STATS:
            vals = sorted(pool, key=lambda x: -x[stat])
            for i, x in enumerate(vals):
                place = 1 + sum(1 for o in vals[:i] if o[stat] > x[stat])
                if place > 3 or x[stat] <= 0:
                    break
                out[(x["team"], x["id"])][stat] = place
        self._tops[before] = dict(out)
        return self._tops[before]

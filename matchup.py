"""
Page 1's Matchup card, titled "Matchups" (Jason, 2026-10-10; worked out in mockups/build_matchup_edges_mockup.py): each
team's offense against the other's defense, position by position, from the season to date -- a card
of its own in the deck, after the two team cards and before Leaders. Games not yet played only: the
defense numbers are the season so far, so on a finished game they'd count that game too.

  QB passing  its quarterbacks' passing yards an attempt   vs  passing yards an attempt it allows to QBs
              (added 2026-10-11)
  ...and under each of the first four, on Page 2 only (EPA_OF), its expected points added a play:
    QB  passing EPA / (attempts + sacks)                   vs  EPA a play it allows to QBs
    RB  RBs' rushing + receiving EPA / (carries + targets) vs  EPA a play it allows to RBs (runs and targets)
    WR  WRs' receiving EPA / targets                       vs  EPA a target it allows to WRs
    TE  TEs' receiving EPA / targets                       vs  EPA a target it allows to TEs
  Run game    the offense's running backs' yards a carry   vs  yards a carry the defense allows to RBs
  To WRs      yards a target to its wide receivers         vs  yards a target it allows to WRs
  To TEs      yards a target to its tight ends             vs  yards a target it allows to TEs
  Pass rush   how often its quarterbacks are sacked        vs  how often the defense sacks the QB
              (sacks / (attempts + sacks): the offense wants it low, the defense high)

The defense side is sportsdataverse's defense-vs-position file (sportsdataverse_client.py, kept as
"defense_vs_position" in data/matchups.json by build_data.py) -- except QB passing, which that file
doesn't have: it's totaled from nflverse's weekly player stats by opponent (defense_passing). The
offense side is totaled here from the site's own player stats (player_weeks), so the two measure the
same thing. Each side is ranked among the league's teams, 1 = best on that side. The edge goes to the
side ranked EDGE_GAP or more places better; closer than that is even.

Everything goes by EPA (Jason, 2026-10-11 -- a combined yards-and-EPA rank before that, which a reader
couldn't work out from the two ranks on Page 2): the chart puts the marks at the EPA ranks, and every
edge, bolt and Matchups to Watch pick goes by them. The yards are shown as numbers only, no ranks. Pass
rush has no EPA, so it goes by its sack rate.

The card (Page 1) is the chart: a slim row a position -- its name over a 1-to-32 track (Jason,
2026-10-11: 1st on the left, the 1 and 32 at the track's ends) with the offense's O and the defense's
X on it at their EPA ranks, as on a play diagram, the stretch between them in the favored team's color (gray when even),
each mark's rank under it. No numbers. Both at the same rank: one mark, the offense's O with a small
x in the defense's color inside it.

Tapping it opens its Page 2 (Jason, 2026-10-10; it was a Numbers view behind a switch on the card), a
deck of three cards (render_block), swiped between sideways with the game's other Page 2s:
  Key Matchups       the edges in plain sentences, biggest first: the EPA and its ranks, then the yards
                     (titled "Matchups to Watch" until 2026-10-11; a key its icon, the O-vs-D cards O-bolt-X)
  <away> O vs <home> D  the away offense against the home defense: a group a stat -- its title, then
                     a line a measure, each with its descriptor and both numbers -- the EPA with both
                     ranks, then the yards (no ranks; Pass rush has only its sack rate, ranked) -- and
                     one edge for the group (the favored team's pill, a short line when even), under
                     "BAL O" / "CLE D"
  <home> O vs <away> D  the home offense against the away defense, the same way
Page 2's ranks are on the site's green-to-red rank scale (render_page1.rank_color; Jason, 2026-10-11).
One edge a group (Jason, 2026-10-11; each line had its own, and yards and EPA disagreed in a third of
them), from the EPA ranks.
In each half (one team's offense against the other's defense) the biggest edge gets a bolt beside its
name in the favored team's color and a tint -- no words; on the chart its stretch is bolder too.
Nothing is marked in a half where every row is even.

A finished regular-season game (Jason, 2026-10-11; final_data): the same two halves -- each offense
against the other's defense -- but each stat is the one number from that game, set against both units'
own season averages (their other games): what the offense usually gains, and what the defense usually
allows (totaled here from its opponents' player stats, so it's the same measure). Each difference is
colored on the rank colors' scale by its share of that average. No ranks anywhere. The "Advantage"
(not "won": a team can have the better EPA and still lose the game) goes to the offense when it beat
its average and the defense allowed more than its average, to the defense when both went the other
way, by ADV_SHARE or more each; mixed is even. The bolt goes to the advantage that moved the game most:
its EPA above what the two averages expected, times the plays. Each unit's difference is told from its
own side (Jason, 2026-10-11): ▲ better than its average, ▼ worse, the arrow and the color agreeing.
Page 1 (option C of mockups/build_final_matchup_mockup.py): a row a stat -- its name and the game's
EPA, then a bar a unit (its O or X, in its team's color) centered on its own average, to the right
when it did better and the left when worse. Page 2 (option A): "Key Matchups", then "<away> O vs
<home> D" and "<home> O vs <away> D" as tables -- the stat, the game's EPA, each unit's ▲/▼ and
average, the advantage. The condensed view's strip shows the card's longest bar (_final_strip).
"""

import html
from collections import defaultdict

import helmets
import render_page2gameinfo
import team_line_colors
from divisions import normalize_abbr

EDGE_GAP = 8

def _epa(v):
    """+.33 / −.05, the way EPA is usually written -- no leading zero, so it fits Page 2's number columns."""
    v = 0.0 if abs(v) < 0.005 else v   # not "−.00"
    return f"{v:+.2f}".replace("0.", ".", 1).replace("-", "−")


# (key, row name, what the Numbers view says the offense number is, defense column in the file,
#  defense position group, is a higher number better for the offense?, format). QB passing has no
#  column in the file: defense_passing totals it.
ROWS = [
    ("pass", "QB passing", "Yards/att", None, None, True, lambda v: f"{v:.1f}"),
    ("pass_epa", "QB EPA", "EPA/dropback", "epa_per_play_allowed", "QB", True, _epa),
    ("rb", "Run game", "Yards/carry", "rush_yards_per_carry_allowed", "RB", True, lambda v: f"{v:.1f}"),
    ("rb_epa", "RB EPA", "EPA/play", "epa_per_play_allowed", "RB", True, _epa),
    ("wr", "To WRs", "Yards/target", "yards_per_target_allowed", "WR", True, lambda v: f"{v:.1f}"),
    ("wr_epa", "WR EPA", "EPA/target", "epa_per_play_allowed", "WR", True, _epa),
    ("te", "To TEs", "Yards/target", "yards_per_target_allowed", "TE", True, lambda v: f"{v:.1f}"),
    ("te_epa", "TE EPA", "EPA/target", "epa_per_play_allowed", "TE", True, _epa),
    ("qb", "Pass rush", "Sack rate", "sack_rate_allowed", "QB", False, lambda v: f"{v * 100:.1f}%"),
]
# Page 2's EPA lines, each under its row on the offense cards (Jason, 2026-10-11) -- not on the chart, in
# Matchups to Watch or in the bolt
EPA_OF = {"pass": "pass_epa", "rb": "rb_epa", "wr": "wr_epa", "te": "te_epa"}
P2_ONLY = set(EPA_OF.values())


def esc(v):
    return html.escape(str(v), quote=True)


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# ---------------------------------------------------------------- the numbers

def defense_passing(player_weekly):
    """nflverse's weekly player stats -> {team: passing yards an attempt its defense allows to QBs},
    regular season, the same QB rows offense_table counts for the offense."""
    tot = defaultdict(lambda: [0.0, 0.0])
    for r in player_weekly or []:
        if r.get("season_type") not in (None, "REG") or r.get("position") != "QB" or not r.get("opponent_team"):
            continue
        t = tot[normalize_abbr(r["opponent_team"])]
        t[0] += float(r.get("passing_yards") or 0)
        t[1] += float(r.get("attempts") or 0)
    return {team: yds / att for team, (yds, att) in tot.items() if att}


def defense_table(rows, player_weekly=None):
    """sportsdataverse_client.get_defense_vs_position's rows (and nflverse's weekly player stats, for QB
    passing) -> {team: {"pass", "rb", "wr", "te", "qb", and their "<key>_epa"}}, what each defense allows (build_data.py keeps
    this in data/matchups.json)."""
    out = defaultdict(dict)
    for r in rows or []:
        for key, _n, _m, col, group, _hb, _f in ROWS:
            if group and r.get("position_group") == group and r.get(col) is not None:
                out[r["team"]][key] = float(r[col])
    for team, v in defense_passing(player_weekly).items():
        out[team]["pass"] = v
    return dict(out)


def _add(t, r):
    """One player-week row into a team's sums."""
    pos = r.get("pos")
    if pos == "QB":
        t["att"] += r.get("att") or 0
        t["pyds"] += r.get("pyds") or 0
        t["pepa"] += r.get("pepa") or 0
        t["sk"] += r.get("sk") or 0
    elif pos in ("RB", "FB"):
        t["car"] += r.get("car") or 0
        t["ryds"] += r.get("ryds") or 0
        t["RBtgt"] += r.get("tgt") or 0
        t["RBepa"] += (r.get("rpepa") or 0) + (r.get("repa") or 0)
    elif pos in ("WR", "TE"):
        t[pos + "tgt"] += r.get("tgt") or 0
        t[pos + "yds"] += r.get("reyds") or 0
        t[pos + "epa"] += r.get("repa") or 0


def _measures(t):
    """A team's sums -> {"pass", "rb", "wr", "te", "qb", their "<key>_epa"}, and each EPA's plays
    ("<key>_n": dropbacks, carries + targets, targets) and total ("<key>_tot")."""
    per = lambda a, b: a / b if b else None
    return {"pass": per(t["pyds"], t["att"]), "rb": per(t["ryds"], t["car"]), "wr": per(t["WRyds"], t["WRtgt"]),
            "te": per(t["TEyds"], t["TEtgt"]), "qb": per(t["sk"], t["att"] + t["sk"]),
            "pass_epa": per(t["pepa"], t["att"] + t["sk"]), "rb_epa": per(t["RBepa"], t["car"] + t["RBtgt"]),
            "wr_epa": per(t["WRepa"], t["WRtgt"]), "te_epa": per(t["TEepa"], t["TEtgt"]),
            "pass_n": t["att"] + t["sk"], "rb_n": t["car"] + t["RBtgt"], "wr_n": t["WRtgt"], "te_n": t["TEtgt"],
            "pass_tot": t["pepa"], "rb_tot": t["RBepa"], "wr_tot": t["WRepa"], "te_tot": t["TEepa"]}


def offense_table(player_weeks, week=None, skip_week=None, teams=None):
    """{team: _measures} for each offense, from player_weeks: the season, one week's game, or the season
    without one week (final_data), for every team or just `teams`."""
    tot = defaultdict(lambda: defaultdict(float))
    for team, rows in (player_weeks or {}).items():
        if teams is not None and team not in teams:
            continue
        for r in rows:
            if (week is None or r.get("wk") == week) and (skip_week is None or r.get("wk") != skip_week):
                _add(tot[team], r)
    return {team: _measures(t) for team, t in tot.items() if any(t.values())}


def allowed(player_weeks, opponents, defense, skip_week):
    """_measures of what `defense` allowed in its games but skip_week -- its opponents' player stats in
    the weeks they played it (opponents: {(team, week): opponent}); None without any."""
    t = defaultdict(float)
    for (team, week), opp in opponents.items():
        if team == defense and week != skip_week:
            for r in (player_weeks or {}).get(opp) or []:
                if r.get("wk") == week:
                    _add(t, r)
    return _measures(t) if any(t.values()) else None


def _ranks(values, higher_better):
    """{team: value} -> {team: rank}, 1 = best; ties share a rank."""
    order = sorted(values.items(), key=lambda kv: kv[1], reverse=higher_better)
    out, prev, rank = {}, None, 0
    for i, (t, v) in enumerate(order, 1):
        rank = rank if v == prev else i
        out[t], prev = rank, v
    return out


def league(player_weeks, defense):
    """Both sides' numbers and ranks for every team, once a build; None without data for both."""
    off, dfn = offense_table(player_weeks), defense or {}
    if not off or not dfn:
        return None
    o_rank, d_rank = {}, {}
    for key, _n, _m, _c, _g, hb, _f in ROWS:
        o_rank[key] = _ranks({t: v[key] for t, v in off.items() if v.get(key) is not None}, hb)
        # a defense is best where the offense's number is worst: fewest yards allowed, most sacks
        d_rank[key] = _ranks({t: v[key] for t, v in dfn.items() if v.get(key) is not None}, not hb)
    return {"off": off, "def": dfn, "o_rank": o_rank, "d_rank": d_rank}


def _line(lg, o, d, key):
    """One measure's line: both numbers, both ranks; None without them."""
    _k, _name, measure, _c, _g, _hb, f = next(r for r in ROWS if r[0] == key)
    ov, dv = lg["off"].get(o, {}).get(key), lg["def"].get(d, {}).get(key)
    orr, drr = lg["o_rank"][key].get(o), lg["d_rank"][key].get(d)
    if None in (ov, dv, orr, drr):
        return None
    n = lg["n"][key] if "n" in lg else max(len(lg["o_rank"][key]), len(lg["d_rank"][key]))
    return {"key": key, "measure": measure, "ov": f(ov), "dv": f(dv), "orr": orr, "drr": drr, "n": n}


def _half(lg, o, d):
    """One team's offense (o) against the other's defense (d): a group a stat -- its lines (the EPA, then
    the yards unranked; Pass rush its sack rate alone), the ranks it goes by (orr / drr, of n: the
    EPA's, or the sack rate's), the edge -- the biggest edge marked (a tie marks both). Without EPA for
    one of the teams a group goes by its yards, ranked."""
    groups = []
    for key, name, *_ in ROWS:
        if key in P2_ONLY or not (ln := _line(lg, o, d, key)):
            continue
        ep = _line(lg, o, d, EPA_OF[key]) if key in EPA_OF else None
        lines = [ep, dict(ln, ranked=False)] if ep else [ln]
        by = lines[0]
        edge = o if by["drr"] - by["orr"] >= EDGE_GAP else d if by["orr"] - by["drr"] >= EDGE_GAP else None
        groups.append({"key": key, "name": name, "lines": lines, "orr": by["orr"], "drr": by["drr"], "n": by["n"],
                       "edge": edge, "top": False})
    edged = [g for g in groups if g["edge"]]
    if edged:
        most = max(abs(g["orr"] - g["drr"]) for g in edged)
        for g in edged:
            g["top"] = abs(g["orr"] - g["drr"]) == most
    return groups


def card_data(lg, away, home):
    """What the card shows for a game -- {"halves": [(offense, defense, groups), ...]} -- or None."""
    if not lg or not (away and home):
        return None
    halves = [(o, d, _half(lg, o, d)) for o, d in ((away, home), (home, away))]
    return {"halves": halves} if all(groups for _o, _d, groups in halves) else None


# A finished game (Jason, 2026-10-11): each offense's game against the other's defense, set against both
# units' season averages (their other games). A stat counts only on MIN_PLAYS or more plays (dropbacks,
# carries + targets, targets) -- in the game and in a season average -- so one lucky target says nothing.
MIN_PLAYS = 3
_FAMILY = {"pass": "pass", "pass_epa": "pass", "qb": "pass", "rb": "rb", "rb_epa": "rb",
           "wr": "wr", "wr_epa": "wr", "te": "te", "te_epa": "te"}
ADV_SHARE = 0.10   # an advantage needs both units 10% or more of their averages to the same side
_WEEKS = {}   # (id(player_weeks), week) -> that week's games, once a build


def _counted(v):
    """A _measures dict with the stats on too few plays taken out."""
    v = dict(v or {})
    for k, fam in _FAMILY.items():
        if (v.get(fam + "_n") or 0) < MIN_PLAYS:
            v[k] = None
    return v


def _share(key, game, avg, better_high):
    """The difference as a share of the average, + when better for the unit (never dividing by less
    than DIFF_FLOOR: an average near zero would make any difference a huge share)."""
    share = (game - avg) / max(abs(avg), DIFF_FLOOR["epa" if key in P2_ONLY else "qb"])
    return share if better_high else -share


def _final_half(games, off_avg, def_avg, o, d):
    """One offense's game (o) against the other's defense (d): a group a stat -- the measured key (the
    EPA, or the sack rate), the game's number, the offense's and the defense's averages, the plays, the
    game's yards, the advantage and its impact -- the bolt on the biggest impact."""
    groups = []
    for key, name, *_ in ROWS:
        if key in P2_ONLY:
            continue
        ekey = EPA_OF.get(key, key)
        game = games[o].get(ekey)
        if game is None:
            continue
        hb = next(r[5] for r in ROWS if r[0] == ekey)
        oa, da = off_avg.get(ekey), (def_avg or {}).get(ekey)
        edge, impact = None, 0.0
        if oa is not None and da is not None:
            so, sd = _share(ekey, game, oa, hb), _share(ekey, game, da, not hb)   # + good for that unit
            if so >= ADV_SHARE and sd <= -ADV_SHARE:
                edge = o
            elif sd >= ADV_SHARE and so <= -ADV_SHARE:
                edge = d
            if ekey in P2_ONLY:   # the EPA above (or below) what the two averages expected, on these plays
                impact = abs(game - (oa + da) / 2) * games[o][_FAMILY[ekey] + "_n"]
        yards = None
        if key in EPA_OF and games[o].get(key) is not None:
            ymeasure, yf = next((r[2], r[6]) for r in ROWS if r[0] == key)
            yards = (ymeasure, yf(games[o][key]))
        groups.append({"key": key, "name": name, "ekey": ekey, "game": game, "oa": oa, "da": da,
                       "n": int(games[o].get(_FAMILY[ekey] + "_n") or 0), "yards": yards,
                       "edge": edge, "impact": impact, "top": False})
    edged = [g for g in groups if g["edge"] and g["impact"]]
    if edged:
        most = max(g["impact"] for g in edged)
        for g in edged:
            g["top"] = g["impact"] == most
    return groups


def final_data(player_weeks, week, away, home, opponents):
    """A finished game's card -- {"final": True, "week", "halves": [(offense, defense, groups), ...]} --
    each offense's game against the other's defense, against both units' season averages. None before
    the game's player stats are out."""
    if week is None or not (away and home):
        return None
    key = (id(player_weeks), week)
    if key not in _WEEKS:
        _WEEKS[key] = offense_table(player_weeks, week)
    if away not in _WEEKS[key] or home not in _WEEKS[key]:
        return None
    games = {t: _counted(_WEEKS[key][t]) for t in (away, home)}
    off_avg = offense_table(player_weeks, skip_week=week, teams={away, home})
    off_avg = {t: _counted(off_avg.get(t)) for t in (away, home)}
    def_avg = {t: _counted(allowed(player_weeks, opponents or {}, t, week)) for t in (away, home)}
    halves = [(o, d, _final_half(games, off_avg[o], def_avg[d], o, d)) for o, d in ((away, home), (home, away))]
    return {"final": True, "week": week, "halves": halves} if all(g for _o, _d, g in halves) else None


def _fmt_diff(key, v):
    """A difference from an average: +.30 (EPA), +1.2% (sack rate)."""
    return _epa(v) if key in P2_ONLY else f"{v * 100:+.1f}%".replace("-", "\u2212")


# The difference's color (Jason, 2026-10-11): its share of the average (_share) on the rank colors'
# green-to-red scale -- 100% better or more the greenest, level the middle gray, 100% worse or more the
# reddest -- better meaning better for that unit: more EPA for an offense, less allowed for a defense,
# and the sack rate the other way round for each.
DIFF_FLOOR = {"epa": 0.10, "qb": 0.02}


def _diff(key, game, avg, better_high):
    """The difference HTML, colored by its share; "" without an average."""
    if avg is None:
        return ""
    share = max(-1.0, min(1.0, _share(key, game, avg, better_high)))
    return f'<span class="mu-dl" style="color:{_rank_color(round(16.5 - share * 15.5))}">{_fmt_diff(key, game - avg)}</span>'


def _diffs(g):
    """(the offense's difference, the defense's) HTML for a finished game's group."""
    hb = next(r[5] for r in ROWS if r[0] == g["ekey"])
    return _diff(g["ekey"], g["game"], g["oa"], hb), _diff(g["ekey"], g["game"], g["da"], not hb)


def _verdict(g, side):
    """(arrow, amount, color, share) for one unit ("o" or "d") -- its difference from its own average,
    told from its own side: ▲ better, ▼ worse, = level; the color its share on the rank scale. None
    without an average."""
    avg = g["oa"] if side == "o" else g["da"]
    if avg is None:
        return None
    hb = next(r[5] for r in ROWS if r[0] == g["ekey"])
    share = _share(g["ekey"], g["game"], avg, hb if side == "o" else not hb)
    capped = max(-1.0, min(1.0, share))
    arrow = "=" if abs(share) < 0.03 else "\u25b2" if share > 0 else "\u25bc"
    amount = _fmt_diff(g["ekey"], abs(g["game"] - avg)).lstrip("+")
    return arrow, amount, _rank_color(round(16.5 - capped * 15.5)), capped


def _vchip(g, side):
    v = _verdict(g, side)
    if not v:
        return '<span class="mf-v mf-na">\u2013</span>'
    arrow, amount, color, _ = v
    return f'<span class="mf-v" style="color:{color}"><i>{arrow}</i>{esc(amount)}</span>'


def _game_label(g, html=False):
    """The game's number with what it is: "+.05 EPA", "11.1% sacked" (as HTML, the unit in a span a
    short phone's one-line row drops)."""
    f = next(r[6] for r in ROWS if r[0] == g["ekey"])
    unit = "EPA" if g["ekey"] in P2_ONLY else "sacked"
    return f'{esc(f(g["game"]))}<span class="mf-unit"> {unit}</span>' if html else f'{f(g["game"])} {unit}'


# ---------------------------------------------------------------- the card

# the chart's marks, as on a play diagram: O the offense, X the defense (each in its team's color)
O_MARK = ('<svg class="mu-xo" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="4.6" fill="var(--aag-tile)" '
          'stroke="currentColor" stroke-width="2.4"/></svg>')
# The X's backing is an outline of the X itself, in the card's color, cutting it out of the track
# (Jason, 2026-10-10: it was a disc, which read as a circle around the X)
_X = "M3.4 3.4l7.2 7.2M10.6 3.4l-7.2 7.2"
X_MARK = ('<svg class="mu-xo" viewBox="0 0 14 14" fill="none" stroke-linecap="round" aria-hidden="true">'
          f'<path d="{_X}" stroke="var(--aag-tile)" stroke-width="5"/><path d="{_X}" stroke="currentColor" stroke-width="2.4"/></svg>')


def tie_mark(oc, dc, final=False):
    """Both teams at the same rank (Jason, 2026-10-10, option A of mockups/tie-marks.html): one mark,
    the offense's O with a small x in the defense's color inside it -- a mark that only ever means a
    tie (an O and an X a rank apart already sit half on top of each other). A finished game's two
    offenses: a small o inside instead."""
    inner = ('<circle cx="7" cy="7" r="1.9" stroke="currentColor" stroke-width="1.8"/>' if final else
             '<path d="M5.1 5.1l3.8 3.8M8.9 5.1l-3.8 3.8" stroke="currentColor" stroke-width="2"/>')
    return ('<svg class="mu-xo" viewBox="0 0 14 14" fill="none" stroke-linecap="round" aria-hidden="true">'
            f'<g class="mu-c mu-half" style="{oc}"><circle cx="7" cy="7" r="5.2" fill="var(--aag-tile)" stroke="currentColor" stroke-width="2.4"/></g>'
            f'<g class="mu-c mu-half" style="{dc}">{inner}</g></svg>')


# each half's biggest edge
BOLT = '<svg viewBox="0 0 12 16" aria-hidden="true"><path d="M7.4 0 0 9.2h4.6L3.6 16 12 6.4H7.3z" fill="currentColor"/></svg>'
# the card's icon (its title and nav dot): Jason's clipboard drawing, Kickoff's before (Jason, 2026-10-10)
ICON = render_page2gameinfo.CLIPBOARD_ICON


def _colors(o, d):
    """Each team's light and dark color as the race charts pick them (team_line_colors) -- so a
    black-and-orange team isn't a black mark on the dark card, and the two teams tell apart."""
    return [f"--lc:{c['lc']};--dc:{c['dc']}" for c in team_line_colors.for_both([o, d])]


def _bolt(r, style):
    return f'<span class="mu-bolt mu-c" style="{style}" title="Biggest edge">{BOLT}</span>' if r["top"] else ""


# Under each mark, its rank in its team's color (Jason, 2026-10-10: the ranks back on the chart, not the
# numbers). Marks closer than this (percent of the track) push their ranks apart -- the left one's to
# its left, the right one's to its right -- so the two never overlap; a tie has one, centered.
RANK_CLOSE = 16


def _rank_labels(po, pd, r, oc, dc):
    if r["orr"] == r["drr"]:
        return f'<span class="mu-rk" style="left:{po:.1f}%">{ordinal(r["orr"])}</span>'
    close = abs(po - pd) < RANK_CLOSE
    (lx, lr, lc), (rx, rr, rc) = sorted([(po, r["orr"], oc), (pd, r["drr"], dc)])
    return (f'<span class="mu-rk mu-c{" mu-rk-l" if close else ""}" style="left:{lx:.1f}%;{lc}">{ordinal(lr)}</span>'
            f'<span class="mu-rk mu-c{" mu-rk-r" if close else ""}" style="left:{rx:.1f}%;{rc}">{ordinal(rr)}</span>')


def _chart(o, d, rows, oc, dc, final=False):
    """One half's rows. final: a finished game's two offenses -- both marks O's, "advantage" for "edge"."""
    px = lambda rank, n: (rank - 1) / max(1, n - 1) * 100   # 1st at the left (Jason, 2026-10-11)
    d_side, d_mark, edge_word = ("offense", O_MARK, "advantage") if final else ("defense", X_MARK, "edge")
    out = []
    for r in rows:
        po, pd = px(r["orr"], r["n"]), px(r["drr"], r["n"])
        gap = oc if r["edge"] == o else dc if r["edge"] == d else "--lc:var(--aag-text-3);--dc:var(--aag-text-3)"
        label = (f'{r["name"]}{" (EPA)" if len(r["lines"]) > 1 else ""}: {o} offense {ordinal(r["orr"])}, '
                 f'{d} {d_side} {ordinal(r["drr"])}'
                 + (f', {edge_word} {r["edge"]}' if r["edge"] else ", even"))
        out.append(
            f'<div class="mu-tr{" top" if r["top"] else ""}" role="img" aria-label="{esc(label)}">'
            f'<div class="mu-tr-l"><span class="mu-nm">{esc(r["name"])}{_bolt(r, gap)}</span></div>'
            f'<div class="mu-line"><span class="mu-tk">1</span>'
            f'<div class="mu-track"><i class="mu-gap mu-c" style="left:{min(po, pd):.1f}%;width:{abs(po - pd):.1f}%;{gap}"></i>'
            + (f'<i class="mu-mk" style="left:{po:.1f}%">{tie_mark(oc, dc, final)}</i>' if r["orr"] == r["drr"] else
               f'<i class="mu-mk mu-c" style="left:{pd:.1f}%;{dc}">{d_mark}</i>'
               f'<i class="mu-mk mu-c" style="left:{po:.1f}%;{oc}">{O_MARK}</i>')
            + _rank_labels(po, pd, r, oc, dc) + f'</div><span class="mu-tk">{r["n"]}</span></div></div>')
    return (f'<div class="mu-blk"><div class="mu-blk-h"><span>{helmets.pill_html(o)} offense <i class="mu-lg mu-c" style="{oc}">{O_MARK}</i></span>'
            f'<span class="mu-vs">vs</span><span>{helmets.pill_html(d)} {d_side} <i class="mu-lg mu-c" style="{dc}">{d_mark}</i></span></div>'
            f'{"".join(out)}</div>')


def _rank_color(n):
    from render_page1 import rank_color   # (render_page1 imports this module)
    return rank_color(n)


def _numbers(o, d, groups, oc, dc):
    """Page 2's offense card before the game: a group a stat -- its title, a line a measure, one edge."""
    d_side, d_tag, edge_head = "defense", "D", "Edge"
    rk = lambda n: f'<small style="color:{_rank_color(n)}">{ordinal(n)}</small>'   # green-to-red (Jason, 2026-10-11)

    def row(label, a_cell, d_cell, cls=""):
        return (f'<div class="mu-ln{cls}"><div class="mu-ln-l">{esc(label)}</div><div class="mu-er-v">{a_cell}</div>'
                f'<div class="mu-er-vs">vs</div><div class="mu-er-v">{d_cell}</div></div>')

    def line(r):   # the yards under the EPA: the numbers alone (Jason, 2026-10-11)
        ranked = r.get("ranked", True)
        return row(r["measure"], f'<b>{r["ov"]}</b>{rk(r["orr"]) if ranked else ""}', f'<b>{r["dv"]}</b>{rk(r["drr"]) if ranked else ""}')

    out = "".join(
        f'<div class="mu-grp{" top" if g["top"] else ""}"><div class="mu-grp-r">'
        f'<div class="mu-grp-t">{esc(g["name"])}{_bolt(g, oc if g["edge"] == o else dc)}</div>'
        f'{"".join(line(r) for r in g["lines"])}</div>'
        f'<div class="mu-er-e">{helmets.pill_html(g["edge"]) if g["edge"] else "<span class=mu-even title=Even></span>"}</div></div>'
        for g in groups)
    head = (f'<div class="mu-grp mu-hd"><div class="mu-grp-r"><div class="mu-ln"><div></div><div>{esc(o)} O</div><div></div>'
            f'<div>{esc(d)} {d_tag}</div></div></div><div class="mu-er-e">{edge_head}</div></div>')   # "BAL O" (Jason, 2026-10-11)
    return (f'<div class="mu-blk"><div class="mu-blk-h"><span>{helmets.pill_html(o)} offense</span><span class="mu-vs">vs</span>'
            f'<span>{helmets.pill_html(d)} {d_side}</span></div>{head}{out}</div>')


YDS_SHORT = {"pass": "yds/att", "rb": "yds/carry", "wr": "yds/tgt", "te": "yds/tgt"}
ADV_HEAD = '<span class="mu-adv-l">Advantage</span><span class="mu-adv-s">ADVTG</span>'   # "ADVTG" on a narrow phone


def _final_numbers(o, d, groups, oc, dc):
    """Page 2's card for a finished game's half (option A of mockups/build_final_matchup_mockup.py): a row
    a stat -- its name, what's measured and the game's yards; the game's number; each unit's ▲/▼ and
    its average; the advantage."""
    def avg(g, v):
        f = next(r[6] for r in ROWS if r[0] == g["ekey"])
        return f'<small>avg {esc(f(v)) if v is not None else "\u2013"}</small>'
    rows = "".join(
        f'<div class="mft{" top" if g["top"] else ""}"><span class="mft-l">'
        f'<span class="mft-n">{esc(g["name"])}{_bolt(g, oc if g["edge"] == o else dc)}</span>'
        f'<small>{esc(next(r[2] for r in ROWS if r[0] == g["ekey"]))}</small>'
        + (f'<small>{esc(g["yards"][1])} {YDS_SHORT.get(g["key"], "")}</small>' if g["yards"] else "")
        + f'</span><b class="mft-g">{esc(next(r[6] for r in ROWS if r[0] == g["ekey"])(g["game"]))}</b>'
        f'<span class="mft-c">{_vchip(g, "o")}{avg(g, g["oa"])}</span><span class="mft-c">{_vchip(g, "d")}{avg(g, g["da"])}</span>'
        f'<span class="mft-e">{helmets.pill_html(g["edge"]) if g["edge"] else "<span class=mu-even title=Even></span>"}</span></div>'
        for g in groups)
    head = (f'<div class="mft mft-hd"><span></span><span>Game</span>'
            f'<span><i class="mu-lg mu-c" style="{oc}">{O_MARK}</i>{esc(o)} O</span>'
            f'<span><i class="mu-lg mu-c" style="{dc}">{X_MARK}</i>{esc(d)} D</span><span class="mft-e">{ADV_HEAD}</span></div>')
    return (f'<div class="mu-blk"><div class="mu-blk-h"><span>{helmets.pill_html(o)} offense</span><span class="mu-vs">vs</span>'
            f'<span>{helmets.pill_html(d)} defense</span></div>{head}{rows}</div>')


def _final_chart(o, d, groups, oc, dc):
    """A finished game's half on Page 1 (option C of mockups/build_final_matchup_mockup.py, Jason,
    2026-10-11): a row a stat -- its name and the game's EPA ("+.05 EPA"), then a bar a unit, its O or X
    and the bar in its team's color, centered on its own season average: to the right when it did
    better than usual, the left when worse, as far as the difference's share of the average (100% the
    whole half). The amount beside it, ▲ / ▼ on the rank colors. A scale over the half's bars:
    worse, avg, better."""
    gray = "--lc:var(--aag-text-3);--dc:var(--aag-text-3)"

    def unit(g, side, c, mark):
        v = _verdict(g, side)
        if not v:
            return (f'<span class="mf-u"><i class="mu-lg mu-c" style="{c}">{mark}</i><span class="mf-tr"><i class="mf-mid"></i></span>'
                    '<span class="mf-v mf-na">\u2013</span></span>')
        arrow, amount, color, share = v
        w = abs(share) * 50
        return (f'<span class="mf-u"><i class="mu-lg mu-c" style="{c}">{mark}</i><span class="mf-tr"><i class="mf-mid"></i>'
                f'<i class="mf-bar mu-c" style="left:{50 if share >= 0 else 50 - w:.1f}%;width:{w:.1f}%;{c}"></i></span>'
                f'<span class="mf-v" style="color:{color}"><i>{arrow}</i>{esc(amount)}</span></span>')
    out = []
    for g in groups:
        bar = oc if g["edge"] == o else dc if g["edge"] == d else gray
        words = lambda side, who: (f'{who} ' + (lambda v: f'{"level with" if v[0] == "=" else ("better" if v[0] != "\u25bc" else "worse")} '
                                                 f'its average by {v[1]}' if v else "no average")(_verdict(g, side)))
        label = (f'{g["name"]}: {_game_label(g)} this game; {words("o", o + " offense")}; {words("d", d + " defense")}'
                 + (f'; advantage {g["edge"]}' if g["edge"] else "; even"))
        out.append(f'<div class="mf-cr{" top" if g["top"] else ""}" role="img" aria-label="{esc(label)}">'
                   f'<span class="mf-l"><span class="mf-nm">{esc(g["name"])}{_bolt(g, bar)}</span><span class="mf-g">{_game_label(g, True)}</span></span>'
                   f'<span class="mf-us">{unit(g, "o", oc, O_MARK)}{unit(g, "d", dc, X_MARK)}</span></div>')
    scale = ('<div class="mf-cr mf-sc" aria-hidden="true"><span class="mf-l">EPA vs avg</span><span class="mf-u"><i></i>'
             '<span class="mf-tr"><span>\u25c0 worse</span><span class="mf-avg">avg</span><span>better \u25b6</span></span><i></i></span></div>')
    return (f'<div class="mu-blk"><div class="mu-blk-h"><span>{helmets.pill_html(o)} offense <i class="mu-lg mu-c" style="{oc}">{O_MARK}</i></span>'
            f'<span class="mu-vs">vs</span><span>{helmets.pill_html(d)} defense <i class="mu-lg mu-c" style="{dc}">{X_MARK}</i></span></div>'
            f'{scale}{"".join(out)}</div>')


def card_body(data):
    """The card's body (render_page1 puts it in the deck): the chart, or "" without data."""
    if not data:
        return ""
    if data.get("final"):
        chart = "".join(_final_chart(o, d, groups, *_colors(o, d)) for o, d, groups in data["halves"])
        return f'<div class="mu"><div class="mu-sub">EPA: each unit vs its own season average</div>{chart}</div>'
    chart = "".join(_chart(o, d, groups, *_colors(o, d)) for o, d, groups in data["halves"])
    return f'<div class="mu"><div class="mu-sub">League rank by EPA · 1st on the left</div>{chart}</div>'


# ---------------------------------------------------------------- the condensed view's strip

# The condensed view has no room for the card, so it gets one line (Jason, 2026-10-11, option C of
# mockups/build_matchup_condensed_mockup.py): the game's biggest edge -- the largest rank gap among
# both halves' edges -- as a slim card between the team cards and Leaders: a bolt, the favored team's
# pill, what the edge is ("receivers vs CLE", "pass D vs ATL", short enough for a 320px phone), the two ranks (the favored side's
# first) and what they rank ("EPA"; Pass rush "sack %"). Tapping it opens the Page 2.
OFF_WORDS = {"pass": "passing", "rb": "run game", "wr": "receivers", "te": "TEs", "qb": "O-line"}
DEF_WORDS = {"pass": "pass D", "rb": "run D", "wr": "coverage", "te": "TE D", "qb": "rush"}


def biggest(data):
    """(offense, defense, group) for the game's biggest edge, or None (no data, or every row even)."""
    best = None
    for o, d, groups in (data or {}).get("halves", []):
        for g in groups:
            if g["edge"] and (best is None or abs(g["orr"] - g["drr"]) > abs(best[2]["orr"] - best[2]["drr"])):
                best = (o, d, g)
    return best


def _biggest_diff(data):
    """A finished game's biggest difference: (offense, defense, group, side) for the longest bar on the
    Page 1 card -- the unit furthest from its own season average, either way, as the bar shows it (its
    share of the average, capped at 100%) -- ties (many bars are full) going to the one that added up to
    the most over the game (the difference times the plays, so five targets to a tight end don't beat
    thirty to the receivers); None without one."""
    best, most = None, (-1.0, -1.0)
    for o, d, groups in data.get("halves", []):
        for g in groups:
            hb = next(r[5] for r in ROWS if r[0] == g["ekey"])
            for side, avg in (("o", g["oa"]), ("d", g["da"])):
                if avg is not None:
                    size = (min(1.0, abs(_share(g["ekey"], g["game"], avg, hb))), abs(g["game"] - avg) * g["n"])
                    if size > most:
                        best, most = (o, d, g, side), size
    return best


def _final_strip(data):
    """A finished game's strip (Jason, 2026-10-11): the Page 1 card's biggest difference -- the unit's
    O or X and pill, what it is ("receivers", "pass D"), its bar centered on its average in its team's
    color, and the amount, ▲ better / ▼ worse, with what it measures ("EPA vs avg")."""
    b = _biggest_diff(data)
    if not b:
        return ""
    o, d, g, side = b
    team, c = (o, _colors(o, d)[0]) if side == "o" else (d, _colors(o, d)[1])
    words = (OFF_WORDS if side == "o" else DEF_WORDS)[g["key"]]
    arrow, amount, color, share = _verdict(g, side)
    w = abs(share) * 50
    kind = "EPA" if g["ekey"] in P2_ONLY else "sack %"
    label = (f'Biggest difference: {team} {words}, {amount} {kind} '
             f'{"better" if arrow == "\u25b2" else "worse" if arrow == "\u25bc" else "level with"} than its season average')
    return (f'<a class="card c-mu" tabindex="0" data-detail="matchup" aria-label="{esc(label)}"><span class="mx-in">'
            f'<span class="mx-mark mu-c" style="{c}">{O_MARK if side == "o" else X_MARK}</span>{helmets.pill_html(team)}'
            f'<span class="mx-t">{esc(words)}</span><span class="mx-bar"><i class="mf-mid"></i>'
            f'<i class="mf-bar mu-c" style="left:{50 if share >= 0 else 50 - w:.1f}%;width:{w:.1f}%;{c}"></i></span>'
            f'<span class="mx-r"><b style="color:{color}">{arrow}{esc(amount)}</b> <i>{kind} vs avg</i></span></span></a>')


def strip_html(data):
    """The condensed view's strip: the biggest edge before a game, the biggest difference after; "" without one."""
    if (data or {}).get("final"):
        return _final_strip(data)
    b = biggest(data)
    if not b:
        return ""
    o, d, g = b
    words = f'{OFF_WORDS[g["key"]]} vs {d}' if g["edge"] == o else f'{DEF_WORDS[g["key"]]} vs {o}'
    fav, other = (g["orr"], g["drr"]) if g["edge"] == o else (g["drr"], g["orr"])
    kind = "sack %" if g["key"] == "qb" else "EPA"
    rk = lambda n: f'<b style="color:{_rank_color(n)}">{ordinal(n)}</b>'
    label = f'Biggest edge: {g["edge"]} {words}, {ordinal(fav)} vs {ordinal(other)} in {kind}'
    return (f'<a class="card c-mu" tabindex="0" data-detail="matchup" aria-label="{esc(label)}"><span class="mx-in">'
            f'<span class="mx-bolt">{BOLT}</span>{helmets.pill_html(g["edge"])}<span class="mx-t">{esc(words)}</span>'
            f'<span class="mx-r">{rk(fav)} <span class="mx-vs">vs</span> {rk(other)} <i>{kind}</i></span></span></a>')


# ---------------------------------------------------------------- Page 2

# "Matchups to Watch": an edge a sentence, in plain words -- the EPA and its ranks, then the yards
# (2026-10-11). Each sentence is about the side that makes the edge -- whichever is further from the
# middle of the league on the EPA ranks: a strong offense or a weak defense when the offense has the
# edge, a strong defense or a weak offense when the defense has it (so a defense ranked 17th is never
# said to "stop the run"). {o} / {d} the teams, {oe} / {de} their EPA and {oer} / {der} those ranks,
# {ov} / {dv} their yards. (Pass rush: {ov} / {dv} the sack rates, {orr} / {drr} their ranks.)
_WORDS = {   # who, the yards, the EPA, a weak defense, a strong one
    "pass": ("quarterbacks", "yards an attempt", "EPA a dropback", "has struggled against the pass", "shuts down the pass"),
    "rb": ("running backs", "yards a carry", "EPA a play", "has struggled against the run", "stops the run"),
    "wr": ("receivers", "yards a target", "EPA a target", "has struggled to cover receivers", "covers receivers well"),
    "te": ("tight ends", "yards a target", "EPA a target", "has struggled to cover tight ends", "handles tight ends well"),
}
_KINDS = {
    "off_strong": "{o}'s {who} average {oe} {e} ({oer}) and {ov} {y}; {d} allows {de} ({der}) and {dv}.",
    "def_weak": "{d} {weak}, allowing {de} {e} ({der}) and {dv} {y}; {o}'s {who} average {oe} ({oer}) and {ov}.",
    "def_strong": "{d} {strong}, allowing {de} {e} ({der}) and {dv} {y}; {o}'s {who} average {oe} ({oer}) and {ov}.",
    "off_weak": "{o}'s {who} have had a hard time, averaging {oe} {e} ({oer}) and {ov} {y}; {d} allows {de} ({der}) and {dv}.",
}
_FIELDS = {f: "{" + f + "}" for f in ("o", "d", "ov", "dv", "orr", "drr", "oe", "de", "oer", "der")}
SENTENCES = {key: {kind: t.format(who=who, y=y, e=e, weak=weak, strong=strong, **_FIELDS) for kind, t in _KINDS.items()}
             for key, (who, y, e, weak, strong) in _WORDS.items()}
# pass rush has no EPA: the sack rates alone
SENTENCES["qb"] = {
    "off_strong": "{o} keeps its quarterback upright, sacked on just {ov} of dropbacks ({orr}), and {d}'s pass rush gets home on {dv} ({drr}).",
    "def_weak": "{d}'s pass rush has rarely gotten home, with sacks on {dv} of dropbacks ({drr}), and {o} gives up sacks on {ov} ({orr}).",
    "def_strong": "{d}'s pass rush gets to the quarterback on {dv} of dropbacks ({drr}), and {o} has given up sacks on {ov} ({orr}).",
    "off_weak": "{o} has had trouble protecting its quarterback, sacked on {ov} of dropbacks ({orr}), and {d} gets sacks on {dv} ({drr})."}
WATCH_MAX = 4   # the biggest edges only: what to watch, not everything


def _rank_words(n, total):
    """A sentence's rank, in its color on the green-to-red scale (Jason, 2026-10-11)."""
    if n is None:
        return "\u2013"
    words = "best in the NFL" if n == 1 else "worst in the NFL" if n == total else ordinal(n)
    return f'<b class="mu-w-rk" style="color:{_rank_color(n)}">{words}</b>'


def _sentence(g, o, d):
    """The sentence as HTML: the template is ours, the teams and numbers are escaped."""
    mid = (g["n"] + 1) / 2
    if g["edge"] == o:   # a strong offense, or a weak defense?
        kind = "off_strong" if mid - g["orr"] >= g["drr"] - mid else "def_weak"
    else:                # a strong defense, or a weak offense?
        kind = "def_strong" if mid - g["drr"] >= g["orr"] - mid else "off_weak"
    ln = next(x for x in g["lines"] if x["key"] == g["key"])
    ep = next((x for x in g["lines"] if x["key"] == EPA_OF.get(g["key"])), None)
    if ep is None and g["key"] != "qb":   # no EPA for one of them: say so with a dash
        ep = {"ov": "\u2013", "dv": "\u2013", "orr": None, "drr": None, "n": ln["n"]}
    v = {"ov": esc(ln["ov"]), "dv": esc(ln["dv"]), "orr": _rank_words(ln["orr"], ln["n"]), "drr": _rank_words(ln["drr"], ln["n"])}
    if ep:
        v.update(oe=esc(ep["ov"]), de=esc(ep["dv"]), oer=_rank_words(ep["orr"], ep["n"]), der=_rank_words(ep["drr"], ep["n"]))
    return esc(SENTENCES[g["key"]][kind]).format(o=esc(o), d=esc(d), **v)


# "Deciding Matchups" (a finished game, Jason, 2026-10-11): each advantage in a sentence -- the game's
# number, then both units against their season averages, the side with the advantage first -- the
# biggest impact first (the bolt's). Pass rush: the sack rates.
_FINAL_WORDS = {"pass": ("quarterbacks", "EPA a dropback", "dropbacks"), "rb": ("running backs", "EPA a play", "plays"),
                "wr": ("receivers", "EPA a target", "targets"), "te": ("tight ends", "EPA a target", "targets")}
FINAL_OFFENSE = "{o}'s {who} put up {g} {e} on {n} {plays}: {od} vs their {oa} average, and {dd} vs the {da} {d} usually allows."
FINAL_DEFENSE = "{d}'s defense held {o}'s {who} to {g} {e} on {n} {plays}: {dd} vs the {da} it usually allows, and {od} vs their {oa} average."
FINAL_PROTECT = "{o} kept its quarterback clean, sacked on {g} of dropbacks: {od} vs its {oa} average, and {dd} vs the {da} {d} usually gets."
FINAL_RUSH = "{d}'s pass rush got home on {g} of {o}'s dropbacks: {dd} vs the {da} it usually gets, and {od} vs the {oa} {o} usually gives up."


def _final_sentence(g, o, d):
    """The sentence as HTML for an advantage: the templates are ours, the numbers escaped."""
    f = next(r[6] for r in ROWS if r[0] == g["ekey"])
    od, dd = _diffs(g)
    if g["key"] == "qb":
        t = FINAL_PROTECT if g["edge"] == o else FINAL_RUSH
        words = {}
    else:
        t = FINAL_OFFENSE if g["edge"] == o else FINAL_DEFENSE
        who, e, plays = _FINAL_WORDS[g["key"]]
        words = {"who": who, "e": e, "plays": plays, "n": g["n"]}
    return esc(t).format(o=esc(o), d=esc(d), g=esc(f(g["game"])), oa=esc(f(g["oa"])), da=esc(f(g["da"])), od=od, dd=dd, **words)


def watch(data):
    """The summary card's lines -- [(favored team, sentence HTML, the biggest?)], the WATCH_MAX biggest
    gaps on the EPA ranks (Pass rush: the sack rate's), biggest first. (The rows too close to call were listed under them until
    2026-10-11.)"""
    if data.get("final"):   # Deciding Matchups: the biggest impact first
        adv = sorted(((g, o, d) for o, d, groups in data["halves"] for g in groups if g["edge"]), key=lambda x: -x[0]["impact"])
        most = adv[0][0]["impact"] if adv else None   # one bolt here: the game's biggest, not each half's
        return [(g["edge"], _final_sentence(g, o, d), bool(g["impact"]) and g["impact"] == most) for g, o, d in adv[:WATCH_MAX]]
    edges = [(abs(g["orr"] - g["drr"]), g["edge"], _sentence(g, o, d))
             for o, d, groups in data["halves"] for g in groups if g["edge"]]
    edges.sort(key=lambda e: -e[0])
    most = edges[0][0] if edges else None
    return [(team, text, gap == most) for gap, team, text in edges[:WATCH_MAX]]


BOLT_TAG = f'<span class="mu-bolt" title="Biggest edge">{BOLT}</span>'


def _watch_body(data):
    lines = watch(data)
    if lines:
        items = "".join(
            f'<li class="mu-w-i"><span class="mu-w-p">{helmets.pill_html(team)}</span>'
            f'<p>{text}{BOLT_TAG if top else ""}</p></li>'
            for team, text, top in lines)
        body = f'<ul class="mu-w">{items}</ul>'
    elif data.get("final"):
        body = ('<p class="mu-w-none">No clear advantages: in no matchup did the offense and the defense both land on the '
                'same side of their season averages.</p>')
    else:
        body = f'<p class="mu-w-none">No big edges in this one: every matchup is within {EDGE_GAP} spots in the league rankings.</p>'
    sub = ("Both units against their season averages" if data.get("final")
           else f"Edges: {EDGE_GAP}+ spots apart in the EPA rankings")
    # a list too long for a short phone scrolls inside the card (P1_JS's detailAtTop knows .mu-scroll)
    return (f'<div class="mu mu-p2"><div class="mu-sub">{esc(sub)}</div>'
            f'<div class="mu-scroll">{body}</div></div>')


# the Page 2 cards' icons (titles and nav dots): an O, a bolt and an X for each offense against a
# defense, a key for the summary
# (2026-10-11: the summary card is "Key Matchups" with a key, before the game and after; the bolt
# moved in between the offense cards' O and X)
OX_ICON = ('<svg viewBox="0 0 44 16" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" aria-hidden="true">'
           '<circle cx="7" cy="8" r="5.4"/><path d="M22.4 0 15 9.2h4.6L18.6 16 27 6.4h-4.7z" fill="currentColor" stroke="none"/>'
           '<path d="M32 2.6l10.8 10.8M42.8 2.6 32 13.4"/></svg>')
KEY_ICON = ('<svg viewBox="0 0 26 14" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
            'stroke-linejoin="round" aria-hidden="true"><circle cx="6.4" cy="7" r="4.6"/><path d="M11 7h13.4M19.6 7v4M23.4 7v3"/></svg>')
PAGE_ICONS = {"away": OX_ICON, "home": OX_ICON, "watch": KEY_ICON}


def render_block(data):
    """The hidden .p2 layer for the Matchups card's Page 2, spliced into Page 1's .p1 block ("" without
    data). The two offense cards are titled "CIN O vs MIA D" (Jason, 2026-10-11; "Cincinnati Offense" before)."""
    if not data:
        return ""
    from render_page1 import DOWN, UP
    final = bool(data.get("final"))

    def numbers_card(o, d, rows):
        sub = "EPA this game · each unit vs its average" if final else "Season to date · rank among 32 teams"
        body = (_final_numbers if final else _numbers)(o, d, rows, *_colors(o, d))
        return f'<div class="mu mu-p2"><div class="mu-sub">{esc(sub)}</div>{body}</div>'
    # the summary first (Jason, 2026-10-10) -- what decided a finished game -- then each offense against
    # the other's defense
    (ao, ad, arows), (ho, hd, hrows) = data["halves"]
    cards = [("watch", "Key Matchups", _watch_body(data)),
             ("away", f"{ao} O vs {ad} D", numbers_card(ao, ad, arows)), ("home", f"{ho} O vs {hd} D", numbers_card(ho, hd, hrows))]

    def title(cid, name):
        return f'<span class="ttl"><span class="t-ic">{PAGE_ICONS[cid]}</span>{esc(name)}</span>'
    slots = "".join(
        f'<section class="slot"><a class="card p2k p2k-mu p2k-mu-{cid}" tabindex="-1" aria-label="{esc(name)}">'
        f'<span class="peek peek-top">{DOWN}{title(cid, name)}</span><div class="body">{body}</div>'
        f'<span class="peek peek-bot">{UP}{title(cid, name)}</span></a></section>'
        for cid, name, body in cards)
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(name)}">{PAGE_ICONS[cid]}</button>' for cid, name, _b in cards)
    return ('<div class="p2 p2-mu" data-page="matchup" aria-label="Matchups" role="region">'
            f'<div class="p2-view p2-l deck">{slots}</div><nav class="dots p2-dots ic-dots" aria-label="Cards">{dots}</nav></div>')


# Appended to Page 1's stylesheet. Team colors are --lc / --dc (light / dark) mixed by the
# --aag-tc-light token (theme.py) rather than a [data-theme] selector, as temp_colors.py does -- so
# they follow the theme inside Page 0's overlay shadow roots too.
MATCHUP_CSS = """
/* The condensed view's strip (strip_html), between the team cards and Leaders. Its height comes from
   the team cards (10px, never below the 184px their contents need on a short phone), the Leaders rows
   closing up (gaps of 4-7px instead of 6-10px), and on phones under 760px tall, where that isn't
   enough, a page floor of 760px instead of 720px (they scroll up to 40px more). The rows' share is
   render_page1's .view-c formula. */
.view-c.has-mu{min-height:760px;
  grid-template-rows:auto max(calc((max(100dvh, 720px) - var(--bar) - var(--bbar) - 48px) * 1.18 / 3.42 - 10px),184px) auto minmax(0,1fr)}
.view-c.has-mu .c-cmp-in{gap:clamp(4px,calc(2.4vh - 15px),14px)}
/* one line, centered -- the bolt, pill, words and ranks stay together on a wide screen (Jason, 2026-10-11) */
a.card.c-mu{display:flex;justify-content:center;align-items:center;padding:9px 16px;min-width:0}
.mx-in{display:flex;align-items:center;gap:7px;min-width:0;max-width:100%;font-size:13px;font-weight:700;white-space:nowrap}
.mx-bolt{display:block;flex:none;width:9px;height:12px;color:var(--aag-text-3)}
.mx-bolt svg{display:block;width:100%;height:100%}
.c-mu .tpill{height:18px;min-width:44px;padding:0 5px;border-width:2px;font-size:10px;flex:none}
.mx-t{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis}
.mx-r{flex:none;margin-left:3px;font-size:12.5px}
.mx-vs{color:var(--aag-text-3);font-weight:400}
.mx-r i{font-style:normal;font-size:9.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--aag-text-3);margin-left:2px}
/* a finished game's strip: the unit's mark and a small bar centered on its average */
.mx-mark{display:block;flex:none;width:10px;height:10px;color:var(--c)}
.mx-bar{position:relative;flex:none;width:52px;height:6px;border-radius:2px;background:var(--tile-border-soft)}
/* a finished game has no room to spare (its Game Info has the score by quarter, its team cards the game
   stats, and on some phones its Leaders were already a few pixels short): the strip is slimmer; on
   phones 800px tall or more the team cards give 14px of their spacing and the Leaders rows close up
   to 3px gaps, the page's floor 830px; below 800px, where the team cards have no spacing to give (they
   get 16px more instead), the floor is 840px -- those phones scroll a little more than they already do */
.p1[data-final] .view-c.has-mu{min-height:830px;
  grid-template-rows:auto calc((max(100dvh, 720px) - var(--bar) - var(--bbar) - 48px) * 1.18 / 3.42 - 14px) auto minmax(0,1fr)}
.p1[data-final] .view-c.has-mu .c-cmp-in{gap:clamp(3px,calc(2.4vh - 17px),12px)}
@media (max-height:799px){ .p1[data-final] .view-c.has-mu{min-height:840px;
  grid-template-rows:auto calc((max(100dvh, 720px) - var(--bar) - var(--bbar) - 48px) * 1.18 / 3.42 + 16px) auto minmax(0,1fr)} }
.p1[data-final] .view-c.has-mu a.card.c-mu{padding:5px 14px}
@media (max-width:370px){ .mx-in{gap:5px;font-size:12px} .mx-r{font-size:11.5px} .mx-bar{width:40px} }   /* 360px Androids */
@media (max-width:340px){   /* a 320px phone: the bolt goes, and the ranks wrap under the words when
  they don't fit beside them (two-digit ranks and "sack %"); the page's floor gives that line room */
  .view-c.has-mu{min-height:776px}
  .mx-in{flex-wrap:wrap;justify-content:center;column-gap:5px;row-gap:1px;font-size:12px}
  .mx-bolt{display:none} .c-mu .tpill{min-width:38px} .mx-t{overflow:visible} .mx-r{font-size:11.5px} }
.matchup .body{padding:48px 18px 16px;justify-content:flex-start}   /* right under the title, like the Player Stats cards */
.mu{width:100%;max-width:440px;margin:0 auto}
.mu-c{--c:color-mix(in srgb,var(--lc) var(--aag-tc-light),var(--dc))}
.mu-sub{text-align:center;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-2);margin:0}
/* Page 2 (render_block): a deck only, like the team pages -- no condensed layer, so no +/- toggle */
.p1[data-detail="matchup"] .p2[data-page="matchup"]{display:block}
.p1[data-detail="matchup"] .toggle{display:none}
.p2 .slot .p2k-mu .body{padding:48px 18px 18px;justify-content:flex-start}
/* the offense cards' four rows share the card's height (up to a point), like the Player Stats rows */
.p2k-mu .body>.mu-p2{flex:1;min-height:0;display:flex;flex-direction:column}
.p2k-mu .mu-p2>.mu-blk{flex:1;display:flex;flex-direction:column}
.p2k-mu .mu-blk>.mu-grp:not(.mu-hd){flex:1 1 auto;max-height:120px}
.mu-p2 .mu-blk{margin-top:14px}
.mu-p2 .tpill{height:20px;min-width:50px;font-size:11px}
.mu-p2 .mu-blk-h{font-size:13px;margin-bottom:8px}
.mu-p2 .mu-grp.top{margin:0 -10px;padding-left:10px;padding-right:10px}
/* Matchups to Watch: the favored team's pill, then the sentence */
.mu-scroll{flex:1;min-height:0;overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;scrollbar-width:none}
.mu-scroll::-webkit-scrollbar{display:none}
.mu-w{list-style:none;margin-top:12px}
.mu-w-i{display:grid;grid-template-columns:52px 1fr;column-gap:10px;align-items:start;padding:10px 0;border-top:1px solid var(--tile-border-soft)}
.mu-w-i:first-child{border-top:0}
.mu-w-p{padding-top:1px}
.mu-w-i p{font-size:14px;line-height:1.4}
.mu-w-i .mu-bolt{color:var(--text-2)}
.mu-w-rk{font-weight:700}
.mu-w-none{margin-top:10px;padding-top:10px;font-size:14px;line-height:1.4}
.mu .tpill{height:18px;min-width:44px;padding:0 5px;border-width:2px;font-size:10px}
.mu-blk{margin-top:6px}
.mu-blk+.mu-blk{margin-top:8px;padding-top:6px;border-top:1px solid var(--tile-border-soft)}
.mu-blk-h{display:flex;align-items:center;justify-content:center;gap:8px;font-size:11px;font-weight:700;color:var(--text-2);margin-bottom:4px}
.mu-blk-h>span{display:inline-flex;align-items:center;gap:5px}
.mu-vs{color:var(--aag-text-3);font-weight:400}
.mu-lg{display:inline-block;width:12px;height:12px;color:var(--c)}
.mu-xo{display:block;width:100%;height:100%;overflow:visible}
.mu-half{color:var(--c)}
/* Chart: a slim row -- the name over the track, 1 and 32 at its ends */
.mu-tr{padding:3px 0 4px;border-top:1px solid var(--tile-border-soft)}
.mu-tr-l{text-align:center;font-size:12px;font-weight:700;margin:0 0 3px}
.mu-nm{position:relative;display:inline-block}
.mu-line{display:grid;grid-template-columns:12px 1fr 12px;align-items:center;column-gap:11px;margin-bottom:10px}
.mu-tk{font-size:9px;font-weight:700;line-height:1;color:var(--aag-text-3)}
.mu-tk:first-child{text-align:right}.mu-tk:last-child{text-align:left}
.mu-track{position:relative;height:3px;border-radius:2px;background:var(--tile-border)}
/* each mark's rank under it, in its team's color; close marks push theirs apart */
.mu-rk{position:absolute;top:8px;transform:translateX(-50%);font-size:9px;font-weight:700;line-height:1;white-space:nowrap;
  color:var(--c,var(--text-2))}
.mu-rk-l{transform:translateX(calc(-100% + 1px))}
.mu-rk-r{transform:translateX(-1px)}
.mu-gap{position:absolute;top:0;bottom:0;border-radius:2px;opacity:.6;background:var(--c)}
.mu-mk{position:absolute;top:50%;width:14px;height:14px;margin:-7px 0 0 -7px;color:var(--c)}
/* Numbers: a group a stat -- its title over a line a measure (descriptor, offense, vs, defense), the
   group's edge at the right */
.mu-grp{display:flex;align-items:center;column-gap:6px;padding:8px 0;border-top:1px solid var(--tile-border-soft)}
.mu-grp-r{flex:1;min-width:0}
.mu-grp-t{font-size:15px;font-weight:700;line-height:1.2;margin-bottom:2px}
.mu-ln{display:grid;grid-template-columns:minmax(0,1fr) 66px 10px 66px;align-items:baseline;column-gap:3px;line-height:1.35}
.mu-ln-l{font-size:11px;color:var(--text-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mu-er-v{display:flex;justify-content:center;align-items:baseline;gap:2px}
.mu-er-v b{font-size:17px;font-variant-numeric:proportional-nums}
.mu-er-v small{font-size:10px;font-weight:700}
.mu-er-vs{text-align:center;font-size:9px;color:var(--aag-text-3)}
.mu-er-e{flex:0 0 54px;display:flex;justify-content:center}
.mu-hd{border-top:0;padding:0 0 3px}
.mu-hd .mu-ln>div,.mu-hd .mu-er-e{font-size:10px;font-weight:700;letter-spacing:.05em;color:var(--aag-text-3);text-align:center}
.mu-hd .mu-er-e{min-width:0;white-space:nowrap}   /* "Advantage" may hang over its column's edges, not widen it */
.mu-adv-s{display:none}
@media (max-width:440px){ .mu-adv-l{display:none} .mu-adv-s{display:inline} }   /* "ADVTG" (Jason, 2026-10-11) */
/* a finished game: each unit's ▲/▼ and amount, from its own side, in the rank colors */
.mu-dl{font-weight:700}
.mf-v{font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
.mf-v i{font-style:normal;font-size:.8em;margin-right:1px}
.mf-na{color:var(--aag-text-3)}
/* Page 1 (C): a row a stat -- name and game EPA, then a bar a unit centered on its average */
.mf-cr{display:grid;grid-template-columns:86px 1fr;align-items:center;column-gap:8px;padding:4px 0;border-top:1px solid var(--tile-border-soft)}
.mf-l{display:flex;flex-direction:column;line-height:1.15;min-width:0}
.mf-nm{display:inline-flex;align-items:center;font-size:12px;font-weight:700;white-space:nowrap}
.mf-nm .mu-bolt{position:static;transform:none;margin-left:3px}
.mf-g{font-size:10.5px;font-weight:700;color:var(--text-2);white-space:nowrap}
.mf-us{display:flex;flex-direction:column;gap:3px}
.mf-u{display:grid;grid-template-columns:10px 1fr 40px;align-items:center;column-gap:5px;line-height:1}
.mf-u .mu-lg{width:10px;height:10px}
.mf-tr{position:relative;height:6px;border-radius:2px;background:var(--tile-border-soft)}
.mf-mid{position:absolute;left:50%;top:-3px;bottom:-3px;width:1.5px;margin-left:-.75px;background:var(--aag-text-3)}
.mf-bar{position:absolute;top:0;bottom:0;border-radius:2px;background:var(--c)}
.mf-u .mf-v{font-size:11px;text-align:right}
/* the scale over a half's bars: worse, avg, better */
.mf-sc{border-top:0;padding:0 0 1px}
.mf-sc .mf-l{font-size:9px;font-weight:700;color:var(--aag-text-3);text-transform:uppercase;letter-spacing:.04em}
.mf-sc .mf-tr{height:auto;background:none;display:flex;justify-content:space-between;font-size:8.5px;font-weight:700;color:var(--aag-text-3)}
.mf-sc .mf-avg{position:absolute;left:50%;transform:translateX(-50%)}
/* Page 2 (A): the stat, the game, each unit, the advantage */
.mft{display:grid;grid-template-columns:minmax(0,1fr) 42px 58px 58px 48px;align-items:center;column-gap:4px;padding:6px 0;
  border-top:1px solid var(--tile-border-soft)}
.p2k-mu .mu-blk>.mft:not(.mft-hd){flex:1 1 auto;max-height:104px}
.mft-hd{border-top:0;padding:0 0 3px;font-size:10px;font-weight:700;letter-spacing:.04em;color:var(--aag-text-3);text-align:center}
.mft-hd>span{display:inline-flex;align-items:center;justify-content:center;gap:3px;min-width:0;white-space:nowrap}
.mft-l{display:flex;flex-direction:column;line-height:1.2;min-width:0}
.mft-n{display:inline-flex;align-items:center;font-size:14px;font-weight:700}
.mft-n .mu-bolt{position:static;transform:none;margin-left:4px}
.mft-l small{font-size:9.5px;color:var(--aag-text-3);white-space:nowrap}
.mft-g{text-align:center;font-size:15px;font-variant-numeric:proportional-nums;white-space:nowrap}
.mft-c{display:flex;flex-direction:column;align-items:center;line-height:1.15}
.mft-c .mf-v{font-size:13.5px}
.mft-c small{font-size:9px;color:var(--aag-text-3)}
.mft-e{display:flex;justify-content:center;min-width:0}
@media (max-width:400px){ .mft{grid-template-columns:minmax(0,1fr) 44px 50px 50px 44px} .mft-n{font-size:13px} .mft-g{font-size:14px} .mft-e .tpill{min-width:40px} }
.mu-even{display:block;width:14px;height:2px;border-radius:1px;background:var(--aag-text-3)}   /* even: just a line */
/* each half's biggest edge: tinted, its stretch bolder, a bolt in the favored team's color */
.mu-grp.top,.mu-tr.top,.mf-cr.top,.mft.top{background:var(--tile-hover);border-radius:10px;border-top-color:transparent;margin:0 -8px;padding-left:8px;padding-right:8px}
.mu-grp.top+.mu-grp,.mu-tr.top+.mu-tr,.mf-cr.top+.mf-cr,.mft.top+.mft{border-top-color:transparent}
.mu-tr.top .mu-track{height:5px}
.mu-tr.top .mu-gap{opacity:1}
.mu-bolt{display:inline-block;width:9px;height:12px;margin-left:5px;vertical-align:-1px;color:var(--c)}
.mu-bolt svg{display:block;width:100%;height:100%}
.mu-nm .mu-bolt{position:absolute;left:100%;top:50%;transform:translateY(-50%)}   /* the name stays centered */
/* shorter phones: the card is shorter, so the rows close up -- below 790px tall the chart's ten rows
   don't fit with each name over its line, so the name goes to the line's left (2026-10-11); below
   740px (an iPhone 8 / SE 2nd gen) the subtitle and Numbers' "vs" go; below
   600px (an SE 1st gen) a size down again */
@media (max-height:790px){
  .mf-cr{padding:3px 0;grid-template-columns:106px 1fr} .mf-l{flex-direction:row;align-items:baseline;gap:4px}
  .mf-unit{display:none} .mf-nm{font-size:11.5px} .mf-g{font-size:10px} .mf-us{gap:2px}
  .mu-tr{display:grid;grid-template-columns:74px 1fr;align-items:center;padding:5px 0 14px}
  .mu-tr-l{margin:0;text-align:left;font-size:11.5px;white-space:nowrap}
  .mu-line{margin:0}
}
@media (max-height:740px){
  .mu-w-i{padding:8px 0}
  .mu-w-i p,.mu-w-none{font-size:13px;line-height:1.35}
  .mu-sub{display:none}
  .mu-tr{padding:4px 0 13px}
  .mu-grp{padding:4px 0}
  .mu-grp-t{font-size:14px;margin-bottom:1px}
  .mf-cr{padding:2px 0}
  .mu-ln{grid-template-columns:minmax(0,1fr) 66px 0 66px}   /* the "vs" goes: the descriptors need the room */
  .mu-er-vs{visibility:hidden}
  .mu-er-v b{font-size:16px}
}
@media (max-height:600px){
  .matchup .body{padding-top:40px;padding-bottom:8px}
  .mu-sw button{padding:2px 9px}
  .mu-blk{margin-top:5px}
  .mu-blk+.mu-blk{margin-top:5px;padding-top:4px}
  .mu-blk-h{margin-bottom:1px}
  .mu .tpill{height:16px;min-width:40px;font-size:9px}
  .mu-tr{padding:2px 0 11px;grid-template-columns:66px 1fr}
  .mu-tr-l{font-size:10.5px}
  .mu-line{column-gap:9px}
  .mu-rk{top:5px;font-size:8px}
  .mu-grp{padding:2px 0}
  .mu-grp-t{font-size:12.5px;margin-bottom:0}
  .mf-cr{padding:1px 0} .mf-nm{font-size:11px} .mf-g{font-size:9.5px} .mf-us{gap:1px} .mf-tr{height:5px}
  .mf-u .mf-v{font-size:10px} .mf-u .mu-lg{width:8px;height:8px}
  .mft{padding:2px 0} .mft-n{font-size:12.5px} .mft-g{font-size:14px} .mft-c .mf-v{font-size:12px}
  .mu-ln{line-height:1.25}
  .mu-er-v b{font-size:14px}
  .mu-er-v small{font-size:9px}
}
/* a phone 320px wide: a finished game's rows narrower */
@media (max-width:340px){
  .mf-cr{grid-template-columns:96px 1fr;column-gap:6px} .mf-nm{font-size:10.5px} .mf-u{grid-template-columns:10px 1fr 36px;column-gap:4px}
  .mft{grid-template-columns:minmax(0,1fr) 36px 50px 50px 42px;column-gap:3px} .mft-n{font-size:12px} .mft-g{font-size:14px}
  .mft-n,.mft-l small{white-space:normal} .mft-l small:first-of-type{display:none}   /* names and yards may wrap; "EPA/dropback" goes */
  .mft-g{font-size:13px}
  .mft-c .mf-v{font-size:12px} .mft-e .tpill{min-width:38px;padding:0 4px}
}
/* a phone 320px wide: narrower number and edge columns, so the descriptors keep one line */
@media (max-width:340px){
  .mu-grp{column-gap:3px}
  .mu-ln{grid-template-columns:minmax(0,1fr) 59px 0 59px;column-gap:3px}
  .mu-er-vs{visibility:hidden}
  .mu-ln-l{font-size:9.5px}
  .mu-grp-t{font-size:12.5px}
  .mu-er-v b{font-size:14px}
  .mu-er-v small{font-size:9.5px}
  .mu-er-e{flex-basis:44px}
  .mu-er-e .tpill{min-width:38px;padding:0 4px}
}
"""

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
  Matchups to Watch  the edges in plain sentences, biggest first: the EPA and its ranks, then the yards
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


def offense_table(player_weeks):
    """{team: {"pass", "rb", "wr", "te", "qb", and their "<key>_epa"}} -- the same measures for each offense, from player_weeks."""
    tot = defaultdict(lambda: defaultdict(float))
    for team, rows in (player_weeks or {}).items():
        t = tot[team]
        for r in rows:
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
    per = lambda a, b: a / b if b else None
    return {team: {"pass": per(t["pyds"], t["att"]), "rb": per(t["ryds"], t["car"]), "wr": per(t["WRyds"], t["WRtgt"]),
                   "te": per(t["TEyds"], t["TEtgt"]), "qb": per(t["sk"], t["att"] + t["sk"]),
                   "pass_epa": per(t["pepa"], t["att"] + t["sk"]), "rb_epa": per(t["RBepa"], t["car"] + t["RBtgt"]),
                   "wr_epa": per(t["WRepa"], t["WRtgt"]), "te_epa": per(t["TEepa"], t["TEtgt"])} for team, t in tot.items()}


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
    return {"key": key, "measure": measure, "ov": f(ov), "dv": f(dv), "orr": orr, "drr": drr,
            "n": max(len(lg["o_rank"][key]), len(lg["d_rank"][key]))}


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


# ---------------------------------------------------------------- the card

# the chart's marks, as on a play diagram: O the offense, X the defense (each in its team's color)
O_MARK = ('<svg class="mu-xo" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="4.6" fill="var(--aag-tile)" '
          'stroke="currentColor" stroke-width="2.4"/></svg>')
# The X's backing is an outline of the X itself, in the card's color, cutting it out of the track
# (Jason, 2026-10-10: it was a disc, which read as a circle around the X)
_X = "M3.4 3.4l7.2 7.2M10.6 3.4l-7.2 7.2"
X_MARK = ('<svg class="mu-xo" viewBox="0 0 14 14" fill="none" stroke-linecap="round" aria-hidden="true">'
          f'<path d="{_X}" stroke="var(--aag-tile)" stroke-width="5"/><path d="{_X}" stroke="currentColor" stroke-width="2.4"/></svg>')


def tie_mark(oc, dc):
    """Both teams at the same rank (Jason, 2026-10-10, option A of mockups/tie-marks.html): one mark,
    the offense's O with a small x in the defense's color inside it -- a mark that only ever means a
    tie (an O and an X a rank apart already sit half on top of each other)."""
    return ('<svg class="mu-xo" viewBox="0 0 14 14" fill="none" stroke-linecap="round" aria-hidden="true">'
            f'<g class="mu-c mu-half" style="{oc}"><circle cx="7" cy="7" r="5.2" fill="var(--aag-tile)" stroke="currentColor" stroke-width="2.4"/></g>'
            f'<g class="mu-c mu-half" style="{dc}"><path d="M5.1 5.1l3.8 3.8M8.9 5.1l-3.8 3.8" stroke="currentColor" stroke-width="2"/></g></svg>')


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


def _chart(o, d, rows, oc, dc):
    px = lambda rank, n: (rank - 1) / max(1, n - 1) * 100   # 1st at the left (Jason, 2026-10-11)
    out = []
    for r in rows:
        po, pd = px(r["orr"], r["n"]), px(r["drr"], r["n"])
        gap = oc if r["edge"] == o else dc if r["edge"] == d else "--lc:var(--aag-text-3);--dc:var(--aag-text-3)"
        label = (f'{r["name"]}{" (EPA)" if len(r["lines"]) > 1 else ""}: {o} offense {ordinal(r["orr"])}, '
                 f'{d} defense {ordinal(r["drr"])}'
                 + (f', edge {r["edge"]}' if r["edge"] else ", even"))
        out.append(
            f'<div class="mu-tr{" top" if r["top"] else ""}" role="img" aria-label="{esc(label)}">'
            f'<div class="mu-tr-l"><span class="mu-nm">{esc(r["name"])}{_bolt(r, gap)}</span></div>'
            f'<div class="mu-line"><span class="mu-tk">1</span>'
            f'<div class="mu-track"><i class="mu-gap mu-c" style="left:{min(po, pd):.1f}%;width:{abs(po - pd):.1f}%;{gap}"></i>'
            + (f'<i class="mu-mk" style="left:{po:.1f}%">{tie_mark(oc, dc)}</i>' if r["orr"] == r["drr"] else
               f'<i class="mu-mk mu-c" style="left:{pd:.1f}%;{dc}">{X_MARK}</i>'
               f'<i class="mu-mk mu-c" style="left:{po:.1f}%;{oc}">{O_MARK}</i>')
            + _rank_labels(po, pd, r, oc, dc) + f'</div><span class="mu-tk">{r["n"]}</span></div></div>')
    return (f'<div class="mu-blk"><div class="mu-blk-h"><span>{helmets.pill_html(o)} offense <i class="mu-lg mu-c" style="{oc}">{O_MARK}</i></span>'
            f'<span class="mu-vs">vs</span><span>{helmets.pill_html(d)} defense <i class="mu-lg mu-c" style="{dc}">{X_MARK}</i></span></div>'
            f'{"".join(out)}</div>')


def _rank_color(n):
    from render_page1 import rank_color   # (render_page1 imports this module)
    return rank_color(n)


def _numbers(o, d, groups, oc, dc):
    """Page 2's offense card: a group a stat -- its title, a line a measure, one edge."""
    rk = lambda n: f'<small style="color:{_rank_color(n)}">{ordinal(n)}</small>'   # green-to-red (Jason, 2026-10-11)

    def line(r):   # the yards under the EPA: the numbers alone (Jason, 2026-10-11)
        ranked = r.get("ranked", True)
        return (f'<div class="mu-ln"><div class="mu-ln-l">{esc(r["measure"])}</div>'
                f'<div class="mu-er-v"><b>{r["ov"]}</b>{rk(r["orr"]) if ranked else ""}</div><div class="mu-er-vs">vs</div>'
                f'<div class="mu-er-v"><b>{r["dv"]}</b>{rk(r["drr"]) if ranked else ""}</div></div>')
    out = "".join(
        f'<div class="mu-grp{" top" if g["top"] else ""}"><div class="mu-grp-r">'
        f'<div class="mu-grp-t">{esc(g["name"])}{_bolt(g, oc if g["edge"] == o else dc)}</div>{"".join(line(r) for r in g["lines"])}</div>'
        f'<div class="mu-er-e">{helmets.pill_html(g["edge"]) if g["edge"] else "<span class=mu-even title=Even></span>"}</div></div>'
        for g in groups)
    head = (f'<div class="mu-grp mu-hd"><div class="mu-grp-r"><div class="mu-ln"><div></div><div>{esc(o)} O</div><div></div>'
            f'<div>{esc(d)} D</div></div></div><div class="mu-er-e">Edge</div></div>')   # "BAL O" (Jason, 2026-10-11)
    return (f'<div class="mu-blk"><div class="mu-blk-h"><span>{helmets.pill_html(o)} offense</span><span class="mu-vs">vs</span>'
            f'<span>{helmets.pill_html(d)} defense</span></div>{head}{out}</div>')


def card_body(data):
    """The card's body (render_page1 puts it in the deck): the chart, or "" without data."""
    if not data:
        return ""
    chart = "".join(_chart(o, d, groups, *_colors(o, d)) for o, d, groups in data["halves"])
    return f'<div class="mu"><div class="mu-sub">League rank by EPA · 1st on the left</div>{chart}</div>'


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


def watch(data):
    """The summary card's lines -- [(favored team, sentence HTML, the biggest?)], the WATCH_MAX biggest
    gaps on the EPA ranks (Pass rush: the sack rate's), biggest first. (The rows too close to call were listed under them until
    2026-10-11.)"""
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
    else:
        body = f'<p class="mu-w-none">No big edges in this one: every matchup is within {EDGE_GAP} spots in the league rankings.</p>'
    # a list too long for a short phone scrolls inside the card (P1_JS's detailAtTop knows .mu-scroll)
    return (f'<div class="mu mu-p2"><div class="mu-sub">Edges: {EDGE_GAP}+ spots apart in the EPA rankings</div>'
            f'<div class="mu-scroll">{body}</div></div>')


# the Page 2 cards' icons (titles and nav dots): an O and an X for each offense against a defense, the
# bolt for the summary
OX_ICON = ('<svg viewBox="0 0 30 14" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" aria-hidden="true">'
           '<circle cx="7" cy="7" r="5.4"/><path d="M18.4 1.6l10.8 10.8M29.2 1.6 18.4 12.4"/></svg>')
PAGE_ICONS = {"away": OX_ICON, "home": OX_ICON, "watch": BOLT}


def render_block(data):
    """The hidden .p2 layer for the Matchups card's Page 2, spliced into Page 1's .p1 block ("" without
    data). The two offense cards are titled "CIN O vs MIA D" (Jason, 2026-10-11; "Cincinnati Offense" before)."""
    if not data:
        return ""
    from render_page1 import DOWN, UP
    (ao, ad, arows), (ho, hd, hrows) = data["halves"]
    away_title, home_title = f"{ao} O vs {ad} D", f"{ho} O vs {hd} D"

    def numbers_card(o, d, rows):
        return (f'<div class="mu mu-p2"><div class="mu-sub">Season to date · rank among 32 teams</div>'
                f'{_numbers(o, d, rows, *_colors(o, d))}</div>')
    # the summary first (Jason, 2026-10-10), then each offense against the other's defense
    cards = [("watch", "Matchups to Watch", _watch_body(data)),
             ("away", away_title, numbers_card(ao, ad, arows)), ("home", home_title, numbers_card(ho, hd, hrows))]

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
.mu-even{display:block;width:14px;height:2px;border-radius:1px;background:var(--aag-text-3)}   /* even: just a line */
/* each half's biggest edge: tinted, its stretch bolder, a bolt in the favored team's color */
.mu-grp.top,.mu-tr.top{background:var(--tile-hover);border-radius:10px;border-top-color:transparent;margin:0 -8px;padding-left:8px;padding-right:8px}
.mu-grp.top+.mu-grp,.mu-tr.top+.mu-tr{border-top-color:transparent}
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
  .mu-ln{line-height:1.25}
  .mu-er-v b{font-size:14px}
  .mu-er-v small{font-size:9px}
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

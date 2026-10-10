"""
Page 1's Matchup card, titled "Matchups" (Jason, 2026-10-10; worked out in mockups/build_matchup_edges_mockup.py): each
team's offense against the other's defense, position by position, from the season to date -- a card
of its own in the deck, after the two team cards and before Leaders. Games not yet played only: the
defense numbers are the season so far, so on a finished game they'd count that game too.

  Run game    the offense's running backs' yards a carry   vs  yards a carry the defense allows to RBs
  To WRs      yards a target to its wide receivers         vs  yards a target it allows to WRs
  To TEs      yards a target to its tight ends             vs  yards a target it allows to TEs
  Pass rush   how often its quarterbacks are sacked        vs  how often the defense sacks the QB
              (sacks / (attempts + sacks): the offense wants it low, the defense high)

The defense side is sportsdataverse's defense-vs-position file (sportsdataverse_client.py, kept as
"defense_vs_position" in data/matchups.json by build_data.py); the offense side is totaled here from
the site's own player stats (player_weeks), so the two measure the same thing. Each side is ranked
among the league's teams, 1 = best on that side. The edge goes to the side ranked EDGE_GAP or more
places better; closer than that is even.

The card (Page 1) is the chart: a slim row a position -- 32, its name, 1 -- over a 32-to-1 track with
the offense's O and the defense's X on it, as on a play diagram, the stretch between them in the
favored team's color (gray when even), each mark's rank under it. No numbers. Both at the same rank:
one mark, the offense's O with a small x in the defense's color inside it.

Tapping it opens its Page 2 (Jason, 2026-10-10; it was a Numbers view behind a switch on the card), a
deck of three cards (render_block), swiped between sideways with the game's other Page 2s:
  Matchups to Watch  the edges in plain sentences, biggest first, then the ones too close to call
  <away> Offense     the away offense against the home defense: both numbers, both ranks and the edge
                     (the favored team's pill, a short line when even)
  <home> Offense     the home offense against the away defense, the same way
In each half (one team's offense against the other's defense) the biggest edge gets a bolt beside its
name in the favored team's color and a tint -- no words; on the chart its stretch is bolder too.
Nothing is marked in a half where every row is even.
"""

import html
from collections import defaultdict

import helmets
import render_page2gameinfo
import team_line_colors

EDGE_GAP = 8

# (key, row name, what the Numbers view says the offense number is, defense column in the file,
#  defense position group, is a higher number better for the offense?, format)
ROWS = [
    ("rb", "Run game", "RB yards a carry", "rush_yards_per_carry_allowed", "RB", True, lambda v: f"{v:.1f}"),
    ("wr", "To WRs", "Yards a target", "yards_per_target_allowed", "WR", True, lambda v: f"{v:.1f}"),
    ("te", "To TEs", "Yards a target", "yards_per_target_allowed", "TE", True, lambda v: f"{v:.1f}"),
    ("qb", "Pass rush", "Sack rate", "sack_rate_allowed", "QB", False, lambda v: f"{v * 100:.1f}%"),
]


def esc(v):
    return html.escape(str(v), quote=True)


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# ---------------------------------------------------------------- the numbers

def defense_table(rows):
    """sportsdataverse_client.get_defense_vs_position's rows -> {team: {"rb", "wr", "te", "qb"}}, what
    each defense allows (build_data.py keeps this in data/matchups.json)."""
    out = defaultdict(dict)
    for r in rows or []:
        for key, _n, _m, col, group, _hb, _f in ROWS:
            if r.get("position_group") == group and r.get(col) is not None:
                out[r["team"]][key] = float(r[col])
    return dict(out)


def offense_table(player_weeks):
    """{team: {"rb", "wr", "te", "qb"}} -- the same four measures for each offense, from player_weeks."""
    tot = defaultdict(lambda: defaultdict(float))
    for team, rows in (player_weeks or {}).items():
        t = tot[team]
        for r in rows:
            pos = r.get("pos")
            if pos == "QB":
                t["att"] += r.get("att") or 0
                t["sk"] += r.get("sk") or 0
            elif pos in ("RB", "FB"):
                t["car"] += r.get("car") or 0
                t["ryds"] += r.get("ryds") or 0
            elif pos in ("WR", "TE"):
                t[pos + "tgt"] += r.get("tgt") or 0
                t[pos + "yds"] += r.get("reyds") or 0
    per = lambda a, b: a / b if b else None
    return {team: {"rb": per(t["ryds"], t["car"]), "wr": per(t["WRyds"], t["WRtgt"]), "te": per(t["TEyds"], t["TEtgt"]),
                   "qb": per(t["sk"], t["att"] + t["sk"])} for team, t in tot.items()}


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


def _half(lg, o, d):
    """One team's offense (o) against the other's defense (d): a dict a row, the biggest edge marked."""
    rows = []
    for key, name, measure, _c, _g, _hb, f in ROWS:
        ov, dv = lg["off"].get(o, {}).get(key), lg["def"].get(d, {}).get(key)
        orr, drr = lg["o_rank"][key].get(o), lg["d_rank"][key].get(d)
        if None in (ov, dv, orr, drr):
            continue
        n = max(len(lg["o_rank"][key]), len(lg["d_rank"][key]))
        edge = o if drr - orr >= EDGE_GAP else d if orr - drr >= EDGE_GAP else None
        rows.append({"key": key, "name": name, "measure": measure, "ov": f(ov), "dv": f(dv), "orr": orr, "drr": drr,
                     "n": n, "edge": edge, "top": False})
    edges = [r for r in rows if r["edge"]]
    if edges:   # the half's biggest edge; a tie marks both
        most = max(abs(r["orr"] - r["drr"]) for r in edges)
        for r in edges:
            r["top"] = abs(r["orr"] - r["drr"]) == most
    return rows


def card_data(lg, away, home):
    """What the card shows for a game -- {"halves": [(offense, defense, rows), ...]} -- or None."""
    if not lg or not (away and home):
        return None
    halves = [(o, d, _half(lg, o, d)) for o, d in ((away, home), (home, away))]
    return {"halves": halves} if all(rows for _o, _d, rows in halves) else None


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
    px = lambda rank, n: (n - rank) / max(1, n - 1) * 100   # 1st at the right, the "better" end
    out = []
    for r in rows:
        po, pd = px(r["orr"], r["n"]), px(r["drr"], r["n"])
        gap = oc if r["edge"] == o else dc if r["edge"] == d else "--lc:var(--aag-text-3);--dc:var(--aag-text-3)"
        label = (f'{r["name"]}: {o} offense {ordinal(r["orr"])}, {d} defense {ordinal(r["drr"])}'
                 + (f', edge {r["edge"]}' if r["edge"] else ", even"))
        out.append(
            f'<div class="mu-tr{" top" if r["top"] else ""}" role="img" aria-label="{esc(label)}">'
            f'<div class="mu-tr-top"><span class="mu-tk">{r["n"]}</span><span class="mu-tr-l"><span class="mu-nm">{esc(r["name"])}'
            f'{_bolt(r, gap)}</span></span><span class="mu-tk">1</span></div>'
            f'<div class="mu-track"><i class="mu-gap mu-c" style="left:{min(po, pd):.1f}%;width:{abs(po - pd):.1f}%;{gap}"></i>'
            + (f'<i class="mu-mk" style="left:{po:.1f}%">{tie_mark(oc, dc)}</i>' if r["orr"] == r["drr"] else
               f'<i class="mu-mk mu-c" style="left:{pd:.1f}%;{dc}">{X_MARK}</i>'
               f'<i class="mu-mk mu-c" style="left:{po:.1f}%;{oc}">{O_MARK}</i>')
            + _rank_labels(po, pd, r, oc, dc) + '</div></div>')
    return (f'<div class="mu-blk"><div class="mu-blk-h"><span>{helmets.pill_html(o)} offense <i class="mu-lg mu-c" style="{oc}">{O_MARK}</i></span>'
            f'<span class="mu-vs">vs</span><span>{helmets.pill_html(d)} defense <i class="mu-lg mu-c" style="{dc}">{X_MARK}</i></span></div>'
            f'{"".join(out)}</div>')


def _numbers(o, d, rows, oc, dc):
    out = "".join(
        f'<div class="mu-er{" top" if r["top"] else ""}"><div class="mu-er-l">{esc(r["name"])}{_bolt(r, oc if r["edge"] == o else dc)}'
        f'<small>{esc(r["measure"])}</small></div>'
        f'<div class="mu-er-v"><b>{r["ov"]}</b><small>{ordinal(r["orr"])}</small></div><div class="mu-er-vs">vs</div>'
        f'<div class="mu-er-v"><b>{r["dv"]}</b><small>{ordinal(r["drr"])}</small></div>'
        f'<div class="mu-er-e">{helmets.pill_html(r["edge"]) if r["edge"] else "<span class=mu-even title=Even></span>"}</div></div>'
        for r in rows)
    return (f'<div class="mu-blk"><div class="mu-blk-h"><span>{helmets.pill_html(o)} offense</span><span class="mu-vs">vs</span>'
            f'<span>{helmets.pill_html(d)} defense</span></div>'
            f'<div class="mu-er mu-er-hd"><div></div><div>{esc(o)}</div><div></div><div>{esc(d)}</div><div>Edge</div></div>{out}</div>')


def card_body(data):
    """The card's body (render_page1 puts it in the deck): the chart, or "" without data."""
    if not data:
        return ""
    chart = "".join(_chart(o, d, rows, *_colors(o, d)) for o, d, rows in data["halves"])
    return f'<div class="mu"><div class="mu-sub">League rank · 1st on the right</div>{chart}</div>'


# ---------------------------------------------------------------- Page 2

# "Matchups to Watch": an edge a sentence, in plain words. Each sentence is about the side that makes
# the edge -- whichever is further from the middle of the league: a strong offense or a weak defense
# when the offense has the edge, a strong defense or a weak offense when the defense has it (so a
# defense ranked 17th is never said to "stop the run"). {o} / {d} the teams, {ov} / {dv} their
# numbers, {orr} / {drr} their ranks.
SENTENCES = {
    "rb": {"off_strong": "{o}'s running backs average {ov} yards a carry ({orr}), and {d} gives up {dv} to running backs ({drr}).",
           "def_weak": "{d} has struggled against the run, giving up {dv} yards a carry ({drr}), and {o}'s running backs average {ov} ({orr}).",
           "def_strong": "{d} stops the run, allowing {dv} yards a carry ({drr}), while {o}'s running backs average {ov} ({orr}).",
           "off_weak": "{o}'s running backs have had a hard time, averaging {ov} yards a carry ({orr}), and {d} allows {dv} ({drr})."},
    "wr": {"off_strong": "{o}'s receivers average {ov} yards a target ({orr}), and {d} allows {dv} to receivers ({drr}).",
           "def_weak": "{d} has struggled to cover receivers, allowing {dv} yards a target ({drr}), and {o}'s receivers average {ov} ({orr}).",
           "def_strong": "{d} covers receivers well, allowing {dv} yards a target ({drr}), while {o}'s receivers average {ov} ({orr}).",
           "off_weak": "{o}'s receivers have had a hard time, averaging {ov} yards a target ({orr}), and {d} allows {dv} ({drr})."},
    "te": {"off_strong": "{o}'s tight ends average {ov} yards a target ({orr}), and {d} allows {dv} to tight ends ({drr}).",
           "def_weak": "{d} has struggled to cover tight ends, allowing {dv} yards a target ({drr}), and {o}'s tight ends average {ov} ({orr}).",
           "def_strong": "{d} handles tight ends well, allowing {dv} yards a target ({drr}), while {o}'s tight ends average {ov} ({orr}).",
           "off_weak": "{o}'s tight ends have had a hard time, averaging {ov} yards a target ({orr}), and {d} allows {dv} ({drr})."},
    "qb": {"off_strong": "{o} keeps its quarterback upright, sacked on just {ov} of dropbacks ({orr}), and {d}'s pass rush gets home on {dv} ({drr}).",
           "def_weak": "{d}'s pass rush has rarely gotten home, with sacks on {dv} of dropbacks ({drr}), and {o} gives up sacks on {ov} ({orr}).",
           "def_strong": "{d}'s pass rush gets to the quarterback on {dv} of dropbacks ({drr}), and {o} has given up sacks on {ov} ({orr}).",
           "off_weak": "{o} has had trouble protecting its quarterback, sacked on {ov} of dropbacks ({orr}), and {d} gets sacks on {dv} ({drr})."},
}
# a too-close row, named from the offense's side
CLOSE_WORDS = {"rb": "run game", "wr": "receivers", "te": "tight ends", "qb": "pass protection"}
WATCH_MAX = 4   # the biggest edges only: what to watch, not everything


def _rank_words(n, total):
    return "best in the NFL" if n == 1 else "worst in the NFL" if n == total else ordinal(n)


def _sentence(r, o, d):
    mid = (r["n"] + 1) / 2
    if r["edge"] == o:   # a strong offense, or a weak defense?
        kind = "off_strong" if mid - r["orr"] >= r["drr"] - mid else "def_weak"
    else:                # a strong defense, or a weak offense?
        kind = "def_strong" if mid - r["drr"] >= r["orr"] - mid else "off_weak"
    return SENTENCES[r["key"]][kind].format(o=o, d=d, ov=r["ov"], dv=r["dv"],
                                            orr=_rank_words(r["orr"], r["n"]), drr=_rank_words(r["drr"], r["n"]))


def watch(data):
    """The summary card's lines -- [(favored team, sentence, the biggest?)], the WATCH_MAX biggest gaps,
    biggest first -- and the rows too close to call, ["CIN's run game vs MIA", ...]."""
    edges, close = [], []
    for o, d, rows in data["halves"]:
        for r in rows:
            if r["edge"]:
                edges.append((abs(r["orr"] - r["drr"]), r["edge"], _sentence(r, o, d)))
            else:
                close.append(f"{o}'s {CLOSE_WORDS[r['key']]} vs {d}")
    edges.sort(key=lambda e: -e[0])
    most = edges[0][0] if edges else None
    return [(team, text, gap == most) for gap, team, text in edges[:WATCH_MAX]], close


BOLT_TAG = f'<span class="mu-bolt" title="Biggest edge">{BOLT}</span>'


def _watch_body(data):
    lines, close = watch(data)
    if lines:
        items = "".join(
            f'<li class="mu-w-i"><span class="mu-w-p">{helmets.pill_html(team)}</span>'
            f'<p>{esc(text)}{BOLT_TAG if top else ""}</p></li>'
            for team, text, top in lines)
        body = f'<ul class="mu-w">{items}</ul>'
    else:
        body = f'<p class="mu-w-none">No big edges in this one: every matchup is within {EDGE_GAP} spots in the league rankings.</p>'
    if close and lines:
        body += f'<p class="mu-w-close"><b>Too close to call:</b> {esc(", ".join(close))}.</p>'
    # a list too long for a short phone scrolls inside the card (P1_JS's detailAtTop knows .mu-scroll)
    return (f'<div class="mu mu-p2"><div class="mu-sub">Edges: {EDGE_GAP}+ spots apart in the rankings</div>'
            f'<div class="mu-scroll">{body}</div></div>')


# the Page 2 cards' icons (titles and nav dots): an O and an X for each offense against a defense, the
# bolt for the summary
OX_ICON = ('<svg viewBox="0 0 30 14" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" aria-hidden="true">'
           '<circle cx="7" cy="7" r="5.4"/><path d="M18.4 1.6l10.8 10.8M29.2 1.6 18.4 12.4"/></svg>')
PAGE_ICONS = {"away": OX_ICON, "home": OX_ICON, "watch": BOLT}


def render_block(data, away_title, home_title):
    """The hidden .p2 layer for the Matchups card's Page 2, spliced into Page 1's .p1 block ("" without
    data). away_title / home_title: the two offense cards' titles ("Cincinnati Offense")."""
    if not data:
        return ""
    from render_page1 import DOWN, UP
    (ao, ad, arows), (ho, hd, hrows) = data["halves"]

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
.p2k-mu .mu-blk>.mu-er:not(.mu-er-hd){flex:1 1 auto;max-height:104px}
.mu-p2 .mu-blk{margin-top:14px}
.mu-p2 .tpill{height:20px;min-width:50px;font-size:11px}
.mu-p2 .mu-blk-h{font-size:13px;margin-bottom:8px}
.mu-p2 .mu-er{padding:11px 0;grid-template-columns:1fr 56px 18px 56px 58px}
.mu-p2 .mu-er-l{font-size:15px}
.mu-p2 .mu-er-l small{font-size:10.5px;margin-top:2px}
.mu-p2 .mu-er-v b{font-size:19px}
.mu-p2 .mu-er-v small{font-size:10.5px}
.mu-p2 .mu-er-hd{font-size:10px;padding-bottom:4px}
.mu-p2 .mu-er.top{margin:0 -10px;padding-left:10px;padding-right:10px}
/* Matchups to Watch: the favored team's pill, then the sentence */
.mu-scroll{flex:1;min-height:0;overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;scrollbar-width:none}
.mu-scroll::-webkit-scrollbar{display:none}
.mu-w{list-style:none;margin-top:12px}
.mu-w-i{display:grid;grid-template-columns:52px 1fr;column-gap:10px;align-items:start;padding:10px 0;border-top:1px solid var(--tile-border-soft)}
.mu-w-i:first-child{border-top:0}
.mu-w-p{padding-top:1px}
.mu-w-i p{font-size:14px;line-height:1.4}
.mu-w-i .mu-bolt{color:var(--text-2)}
.mu-w-close,.mu-w-none{margin-top:10px;padding-top:10px;border-top:1px solid var(--tile-border-soft);font-size:13px;line-height:1.4;color:var(--text-2)}
.mu-w-none{border-top:0;font-size:14px;color:inherit}
.mu-w-close b{color:var(--ink)}
.mu .tpill{height:18px;min-width:44px;padding:0 5px;border-width:2px;font-size:10px}
.mu-blk{margin-top:10px}
.mu-blk+.mu-blk{margin-top:12px;padding-top:10px;border-top:1px solid var(--tile-border-soft)}
.mu-blk-h{display:flex;align-items:center;justify-content:center;gap:8px;font-size:11px;font-weight:700;color:var(--text-2);margin-bottom:4px}
.mu-blk-h>span{display:inline-flex;align-items:center;gap:5px}
.mu-vs{color:var(--aag-text-3);font-weight:400}
.mu-lg{display:inline-block;width:12px;height:12px;color:var(--c)}
.mu-xo{display:block;width:100%;height:100%;overflow:visible}
.mu-half{color:var(--c)}
/* Chart: a slim row -- 32, the name, 1 -- over the track */
.mu-tr{padding:5px 0 7px;border-top:1px solid var(--tile-border-soft)}
.mu-tr-top{display:grid;grid-template-columns:20px 1fr 20px;align-items:baseline;margin:0 0 6px}
.mu-tr-l{text-align:center;font-size:12px;font-weight:700}
.mu-nm{position:relative;display:inline-block}
.mu-tk{font-size:8.5px;font-weight:700;color:var(--aag-text-3)}
.mu-tk:first-child{text-align:left}.mu-tk:last-child{text-align:right}
.mu-track{position:relative;height:3px;margin:0 2px 15px;border-radius:2px;background:var(--tile-border)}
/* each mark's rank under it, in its team's color; close marks push theirs apart */
.mu-rk{position:absolute;top:9px;transform:translateX(-50%);font-size:9px;font-weight:700;line-height:1;white-space:nowrap;
  color:var(--c,var(--text-2))}
.mu-rk-l{transform:translateX(calc(-100% + 3px))}
.mu-rk-r{transform:translateX(-3px)}
.mu-gap{position:absolute;top:0;bottom:0;border-radius:2px;opacity:.6;background:var(--c)}
.mu-mk{position:absolute;top:50%;width:14px;height:14px;margin:-7px 0 0 -7px;color:var(--c)}
/* Numbers: name, offense, vs, defense, edge */
.mu-er{display:grid;grid-template-columns:1fr 46px 16px 46px 52px;align-items:center;column-gap:4px;padding:5px 0;border-top:1px solid var(--tile-border-soft)}
.mu-er-hd{border-top:0;padding:0 0 2px;font-size:9px;font-weight:700;letter-spacing:.05em;color:var(--aag-text-3);text-align:center}
.mu-er-l{font-size:13px;font-weight:700;line-height:1.15}
.mu-er-l small{display:block;font-size:9.5px;font-weight:400;color:var(--aag-text-3)}
.mu-er-v{text-align:center;line-height:1.1}
.mu-er-v b{display:block;font-size:15px;font-variant-numeric:proportional-nums}
.mu-er-v small{font-size:9.5px;font-weight:700;color:var(--text-2)}
.mu-er-vs{text-align:center;font-size:9px;color:var(--aag-text-3)}
.mu-er-e{display:flex;justify-content:center}
.mu-even{display:block;width:14px;height:2px;border-radius:1px;background:var(--aag-text-3)}   /* even: just a line */
/* each half's biggest edge: tinted, its stretch bolder, a bolt in the favored team's color */
.mu-er.top,.mu-tr.top{background:var(--tile-hover);border-radius:10px;border-top-color:transparent;margin:0 -8px;padding-left:8px;padding-right:8px}
.mu-er.top+.mu-er,.mu-tr.top+.mu-tr{border-top-color:transparent}
.mu-tr.top .mu-track{height:5px}
.mu-tr.top .mu-gap{opacity:1}
.mu-bolt{display:inline-block;width:9px;height:12px;margin-left:5px;vertical-align:-1px;color:var(--c)}
.mu-bolt svg{display:block;width:100%;height:100%}
.mu-nm .mu-bolt{position:absolute;left:100%;top:50%;transform:translateY(-50%)}   /* the name stays centered */
/* shorter phones: the card is shorter, so the rows close up -- below 740px tall (an iPhone 8 / SE 2nd
   gen) the subtitle and Numbers' small "RB yards a carry" lines go; below 600px (an SE 1st gen) a
   size down again */
@media (max-height:740px){
  .mu-w-i{padding:8px 0}
  .mu-w-i p,.mu-w-none{font-size:13px;line-height:1.35}
  .mu-w-close{font-size:12px}
  .mu-sub,.mu-er-l small{display:none}
  .mu-blk{margin-top:8px}
  .mu-blk+.mu-blk{margin-top:8px;padding-top:6px}
  .mu-tr{padding:3px 0 2px}
  .mu-tr-top{margin-bottom:4px}
  .mu-track{margin-bottom:13px}
  .mu-rk{top:8px}
  .mu-er{padding:4px 0;grid-template-columns:1fr 66px 10px 66px 50px}
  .mu-er-v{display:flex;justify-content:center;align-items:baseline;gap:4px}   /* "3.5 27th": the rank beside the number */
  .mu-er-v b{display:inline}
}
@media (max-height:600px){
  .matchup .body{padding-top:40px;padding-bottom:8px}
  .mu-sw button{padding:2px 9px}
  .mu-blk{margin-top:5px}
  .mu-blk+.mu-blk{margin-top:5px;padding-top:4px}
  .mu-blk-h{margin-bottom:1px}
  .mu .tpill{height:16px;min-width:40px;font-size:9px}
  .mu-tr{padding:1px 0 0}
  .mu-tr-top{margin-bottom:1px;line-height:1.1}
  .mu-track{margin-bottom:9px}
  .mu-rk{top:5px;font-size:8px}
  .mu-tr-l{font-size:11px}
  .mu-er-hd{display:none}
  .mu-er{padding:1px 0}
  .mu-er-l{font-size:12px}
  .mu-er-v b{font-size:13px}
  .mu-er-v small{font-size:9px}
}
/* a phone 320px wide: narrower number and edge columns, so the names keep one line */
@media (max-width:340px){
  .mu-er{grid-template-columns:1fr 56px 6px 56px 44px;column-gap:3px}
  .mu-er-v{gap:3px}
  .mu-er-v b{font-size:12px}
  .mu-er-e .tpill{min-width:38px;padding:0 4px}
  .mu-er-l{font-size:11.5px;white-space:nowrap}   /* "Pass rush" kept to one line */
}
"""

"""
Page 1's Matchup card (Jason, 2026-10-10; worked out in mockups/build_matchup_edges_mockup.py): each
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

Two views behind a Chart | Numbers switch under the title; it opens on the chart, the quicker read
(Jason, 2026-10-10):
  Chart     a slim row a position: 32, its name, 1 -- over a 32-to-1 track with the offense's O and
            the defense's X on it, as on a play diagram, and the stretch between them in the favored
            team's color (gray when even). No numbers.
  Numbers   both numbers, both ranks and the edge: the favored team's pill, a short line when even.
In each half (one team's offense against the other's defense) the biggest edge gets a bolt beside its
name in the favored team's color, a tint and a bolder stretch, on both views -- no words. Nothing is
marked in a half where every row is even.
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
X_MARK = ('<svg class="mu-xo" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="6.5" fill="var(--aag-tile)"/>'
          '<path d="M3.4 3.4l7.2 7.2M10.6 3.4l-7.2 7.2" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>')
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
            f'<i class="mu-mk mu-c" style="left:{pd:.1f}%;{dc}">{X_MARK}</i>'
            f'<i class="mu-mk mu-c" style="left:{po:.1f}%;{oc}">{O_MARK}</i></div></div>')
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
    """The card's body (render_page1 puts it in the deck), or "" without data."""
    if not data:
        return ""
    chart, numbers = [], []
    for o, d, rows in data["halves"]:
        oc, dc = _colors(o, d)
        chart.append(_chart(o, d, rows, oc, dc))
        numbers.append(_numbers(o, d, rows, oc, dc))
    sw = "".join(f'<button type="button" data-mu-v="{v}"{" class=on" if v == "chart" else ""} aria-pressed="{"true" if v == "chart" else "false"}">{t}</button>'
                 for v, t in (("chart", "Chart"), ("numbers", "Numbers")))
    return (f'<div class="mu" data-mu="chart"><div class="mu-sw" role="group" aria-label="Show">{sw}</div>'
            f'<div class="mu-sub mu-v-chart">League rank · 1st on the right</div>'
            f'<div class="mu-sub mu-v-numbers">Season to date · rank among 32 teams</div>'
            f'<div class="mu-v-chart">{"".join(chart)}</div><div class="mu-v-numbers">{"".join(numbers)}</div></div>')


# Appended to Page 1's stylesheet. Team colors are --lc / --dc (light / dark) mixed by the
# --aag-tc-light token (theme.py) rather than a [data-theme] selector, as temp_colors.py does -- so
# they follow the theme inside Page 0's overlay shadow roots too.
MATCHUP_CSS = """
.matchup .body{padding:48px 18px 16px;justify-content:flex-start}   /* right under the title, like the Player Stats cards */
.mu{width:100%;max-width:440px;margin:0 auto}
.mu-c{--c:color-mix(in srgb,var(--lc) var(--aag-tc-light),var(--dc))}
.mu-sw{width:max-content;margin:0 auto;display:flex;gap:1px;padding:1px;border:1px solid var(--tile-border);border-radius:999px}
.mu-sw button{font:inherit;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:3px 10px;border:0;
  border-radius:999px;background:none;color:var(--text-2);cursor:pointer;-webkit-tap-highlight-color:transparent}
.mu-sw button.on{background:var(--ink);color:var(--tile)}
.mu-sw button:focus-visible{outline:2px solid var(--aag-focus);outline-offset:1px}
.mu[data-mu=chart] .mu-v-numbers,.mu[data-mu=numbers] .mu-v-chart{display:none}
.mu-sub{text-align:center;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-2);margin:7px 0 0}
.mu .tpill{height:18px;min-width:44px;padding:0 5px;border-width:2px;font-size:10px}
.mu-blk{margin-top:10px}
.mu-blk+.mu-blk{margin-top:12px;padding-top:10px;border-top:1px solid var(--tile-border-soft)}
.mu-blk-h{display:flex;align-items:center;justify-content:center;gap:8px;font-size:11px;font-weight:700;color:var(--text-2);margin-bottom:4px}
.mu-blk-h>span{display:inline-flex;align-items:center;gap:5px}
.mu-vs{color:var(--aag-text-3);font-weight:400}
.mu-lg{display:inline-block;width:12px;height:12px;color:var(--c)}
.mu-xo{display:block;width:100%;height:100%}
/* Chart: a slim row -- 32, the name, 1 -- over the track */
.mu-tr{padding:5px 0 7px;border-top:1px solid var(--tile-border-soft)}
.mu-tr-top{display:grid;grid-template-columns:20px 1fr 20px;align-items:baseline;margin:0 0 6px}
.mu-tr-l{text-align:center;font-size:12px;font-weight:700}
.mu-nm{position:relative;display:inline-block}
.mu-tk{font-size:8.5px;font-weight:700;color:var(--aag-text-3)}
.mu-tk:first-child{text-align:left}.mu-tk:last-child{text-align:right}
.mu-track{position:relative;height:3px;margin:0 2px 4px;border-radius:2px;background:var(--tile-border)}
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
  .mu-sub,.mu-er-l small{display:none}
  .mu-blk{margin-top:8px}
  .mu-blk+.mu-blk{margin-top:8px;padding-top:6px}
  .mu-tr{padding:3px 0 4px}
  .mu-tr-top{margin-bottom:4px}
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
  .mu-tr{padding:1px 0 3px}
  .mu-tr-top{margin-bottom:3px}
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

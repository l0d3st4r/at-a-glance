"""
Matchup edges mockup (2026-10-10) -- NOT part of the live build.

Jason asked to see how sportsdataverse's NFL "defense vs. position" data could go on the site. For
every defense it says how it does this season against each kind of player -- quarterbacks, running
backs, wide receivers, tight ends -- so a game page can set one team's strength against the other's
weakness ("DET runs for 5.1 a carry; ATL allows 3.1").

Where the numbers come from:
  defense  sportsdataverse-data release nfl_defense_vs_position, defense_vs_position_<season>.parquet
           (a small file, updated weekly): what each defense allows to each position group
  offense  the site's own player stats (data/matchups.json "player_weeks"), the same four measures
           for each offense, so the two sides line up:
             Pass rush   QB sack rate: sacks / (attempts + sacks)   -- offense lower is better,
                                                                       defense higher is better
             Run game    RB/FB yards per carry
             To WRs      yards per target to wide receivers
             To TEs      yards per target to tight ends
  ranks    1 = best in the NFL on that side, among the 32 teams
  edge     the side ranked at least EDGE_GAP places better; otherwise "Even"

The card (a new Matchup card on Page 1), in a phone frame (375 wide), for real Week N games -- shown
twice, as it opens and turned to the numbers. A Chart | Numbers switch under the title flips between (Jason, 2026-10-10,
from the first round's A, B and C):
  Numbers (A)  each team's offense against the other's defense, a row a position: both numbers, both
               ranks, and who has the edge
  Chart (B)    a slim row a position: 32, its name centered, 1, over a 32-to-1 track with the offense's
               O and the defense's X on it (as on a play diagram) and the stretch between them in the
               favored team's color -- no numbers, the Numbers side has them
It opens on the chart -- the quicker read, the numbers a tap away -- and in each half (one team's
offense against the other's defense) the row with the biggest edge is highlighted on both sides: tinted,
its stretch bolder, a bolt beside its name in the favored team's color -- no words (Jason, 2026-10-10).
A half with no edge at all (every row Even) highlights nothing; an Even row's edge is just a line.
(The first round's C, a Defense by position block on the team pages, was left out.)

Run after build_data.py:
    py mockups/build_matchup_edges_mockup.py [out.html]
Writes mockups/matchup-edges.html (self-contained but for the web fonts).
"""

import html
import io
import json
import os
import sys
from collections import defaultdict

import requests
import polars as pl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import helmets  # noqa: E402
import team_line_colors  # noqa: E402
import theme  # noqa: E402

DVP_URL = ("https://github.com/sportsdataverse/sportsdataverse-data/releases/download/"
           "nfl_defense_vs_position/defense_vs_position_{season}.parquet")
EDGE_GAP = 8
GAMES = 2   # how many of the week's games to show

# (key, label, offense measure, defense column, higher is better for the offense?, format)
ROWS = [
    ("rb", "Run game", "RB yards a carry", "rush_yards_per_carry_allowed", True, lambda v: f"{v:.1f}"),
    ("wr", "To WRs", "Yards a target", "yards_per_target_allowed", True, lambda v: f"{v:.1f}"),
    ("te", "To TEs", "Yards a target", "yards_per_target_allowed", True, lambda v: f"{v:.1f}"),
    ("qb", "Pass rush", "Sack rate", "sack_rate_allowed", False, lambda v: f"{v * 100:.1f}%"),
]
GROUP = {"rb": "RB", "wr": "WR", "te": "TE", "qb": "QB"}


def esc(v):
    return html.escape(str(v), quote=True)


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def ranks(values, higher_better):
    """{team: value} -> {team: rank}, 1 = best; ties share a rank."""
    order = sorted(values.items(), key=lambda kv: kv[1], reverse=higher_better)
    out, prev, prev_rank = {}, None, 0
    for i, (t, v) in enumerate(order, 1):
        prev_rank = prev_rank if v == prev else i
        out[t], prev = prev_rank, v
    return out


def offense(player_weeks):
    """{team: {key: value}} -- the four offense measures, season to date."""
    tot = defaultdict(lambda: defaultdict(float))
    for team, rows in player_weeks.items():
        for r in rows:
            t, pos = tot[team], r.get("pos")
            if pos == "QB":
                t["att"] += r.get("att") or 0
                t["sk"] += r.get("sk") or 0
            if pos in ("RB", "FB"):
                t["rb_car"] += r.get("car") or 0
                t["rb_yds"] += r.get("ryds") or 0
            if pos in ("WR", "TE"):
                t[pos + "_tgt"] += r.get("tgt") or 0
                t[pos + "_yds"] += r.get("reyds") or 0
    out = {}
    for team, t in tot.items():
        out[team] = {
            "rb": t["rb_yds"] / t["rb_car"] if t["rb_car"] else None,
            "wr": t["WR_yds"] / t["WR_tgt"] if t["WR_tgt"] else None,
            "te": t["TE_yds"] / t["TE_tgt"] if t["TE_tgt"] else None,
            "qb": t["sk"] / (t["att"] + t["sk"]) if t["att"] + t["sk"] else None,
        }
    return out


def defense(season):
    df = pl.read_parquet(io.BytesIO(requests.get(DVP_URL.format(season=season), timeout=60).content))
    out, pct = defaultdict(dict), defaultdict(dict)
    for r in df.to_dicts():
        team = {"LA": "LAR"}.get(r["pos_team"], r["pos_team"])   # the file says LA; the site, LAR
        for key, _l, _m, col, _hb, _f in ROWS:
            if GROUP[key] == r["position_group"] and r.get(col) is not None:
                out[team][key] = r[col]
                pct[team][key] = r.get(col + "_pct")
    return out, pct


def build(data):
    season = int(data.get("season") or 2026)
    off = offense(data.get("player_weeks") or {})
    dfn, pct = defense(season)
    o_rank, d_rank = {}, {}
    for key, _l, _m, _c, hb, _f in ROWS:
        o_rank[key] = ranks({t: v[key] for t, v in off.items() if v.get(key) is not None}, hb)
        # a defense is best when the offense measure is worst: fewest yards allowed, most sacks
        d_rank[key] = ranks({t: v[key] for t, v in dfn.items() if key in v}, not hb)
    return off, dfn, pct, o_rank, d_rank


def side_rows(o, d, off, dfn, o_rank, d_rank):
    """One team's offense (o) against the other's defense (d): a dict a row."""
    rows = []
    for key, label, measure, _c, _hb, f in ROWS:
        ov, dv = off.get(o, {}).get(key), dfn.get(d, {}).get(key)
        if ov is None or dv is None:
            continue
        orr, drr = o_rank[key][o], d_rank[key][d]
        edge = o if drr - orr >= EDGE_GAP else d if orr - drr >= EDGE_GAP else None
        rows.append(dict(key=key, label=label, measure=measure, ov=f(ov), dv=f(dv), orr=orr, drr=drr, edge=edge, top=False))
    # the half's biggest gap (Jason, 2026-10-10) -- if it's a real edge; ties all count
    edges = [r for r in rows if r["edge"]]
    if edges:
        most = max(abs(r["orr"] - r["drr"]) for r in edges)
        for r in edges:
            r["top"] = abs(r["orr"] - r["drr"]) == most
    return rows


def pick_games(data, off, dfn, o_rank, d_rank):
    """This week's games with the most edges (the clearest examples)."""
    scored = []
    for m in data.get("matchups") or []:
        a, h = (m.get("away") or {}).get("team"), (m.get("home") or {}).get("team")
        if not (a and h) or m.get("final"):
            continue
        rows = side_rows(a, h, off, dfn, o_rank, d_rank) + side_rows(h, a, off, dfn, o_rank, d_rank)
        scored.append((sum(1 for r in rows if r["edge"]), a, h, m))
    scored.sort(key=lambda x: -x[0])
    return scored[:GAMES]


# ---------------------------------------------------------------- the card: Numbers | Chart

def pill(t):
    return helmets.pill_html(t)


# the chart's marks, as on a play diagram: O the offense, X the defense
O_MARK = ('<svg class="xo" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="4.6" fill="var(--aag-tile)" '
          'stroke="currentColor" stroke-width="2.4"/></svg>')
X_MARK = ('<svg class="xo" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="6.5" fill="var(--aag-tile)"/>'
          '<path d="M3.4 3.4l7.2 7.2M10.6 3.4l-7.2 7.2" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>')


def team_style(*teams):
    """Each team's color as the race charts pick it (team_line_colors): one for each ground, so a
    black-and-orange team isn't a black mark on the dark card. --lc / --dc, which .tc reads."""
    return [f"--lc:{c['lc']};--dc:{c['dc']}" for c in team_line_colors.for_both(list(teams))]


# each half's biggest edge: a bolt in the favored team's color, no words (Jason, 2026-10-10)
BOLT = '<svg viewBox="0 0 12 16" aria-hidden="true"><path d="M7.4 0 0 9.2h4.6L3.6 16 12 6.4H7.3z" fill="currentColor"/></svg>'


def top_tag(r, style):
    return f'<span class="top-tag tc" style="{style}" title="Biggest edge">{BOLT}</span>' if r["top"] else ""


def numbers(a, h, off, dfn, o_rank, d_rank):
    """View A: both numbers, both ranks and the edge, a row a position."""
    blocks = []
    for o, d in ((a, h), (h, a)):
        oc, dc = team_style(o, d)
        rows = "".join(
            f'<div class="er{" top" if r["top"] else ""}"><div class="er-l">{esc(r["label"])}{top_tag(r, oc if r["edge"] == o else dc)}'
            f'<small>{esc(r["measure"])}</small></div>'
            f'<div class="er-v"><b>{r["ov"]}</b><small>{ordinal(r["orr"])}</small></div>'
            f'<div class="er-vs">vs</div>'
            f'<div class="er-v"><b>{r["dv"]}</b><small>{ordinal(r["drr"])}</small></div>'
            f'<div class="er-e">{pill(r["edge"]) if r["edge"] else "<span class=even title=Even></span>"}</div></div>'
            for r in side_rows(o, d, off, dfn, o_rank, d_rank))
        blocks.append(f'<div class="blk"><div class="blk-h"><span>{pill(o)} offense</span><span class="blk-vs">vs</span>'
                      f'<span>{pill(d)} defense</span></div>'
                      f'<div class="er er-hd"><div></div><div>{esc(o)}</div><div></div><div>{esc(d)}</div><div>Edge</div></div>'
                      f'{rows}</div>')
    return "".join(blocks)


def chart(a, h, off, dfn, o_rank, d_rank):
    """View B: a row a position, just its name over a 32-to-1 track with the offense's O and the
    defense's X on it -- the numbers are view A's."""
    blocks = []
    for o, d in ((a, h), (h, a)):
        oc, dc = team_style(o, d)
        px = lambda rank: (32 - rank) / 31 * 100   # 1st at the right, the "better" end
        rows = []
        for r in side_rows(o, d, off, dfn, o_rank, d_rank):
            gap = oc if r["edge"] == o else dc if r["edge"] == d else "--lc:var(--aag-text-3);--dc:var(--aag-text-3)"
            rows.append(
                f'<div class="tr{" top" if r["top"] else ""}"><div class="tr-top"><span class="tk">32</span>'
                f'<span class="tr-l"><span class="tr-nm">{esc(r["label"])}{top_tag(r, gap)}</span></span>'
                f'<span class="tk">1</span></div><div class="track">'
                f'<i class="gap tc" style="left:{min(px(r["orr"]), px(r["drr"])):.1f}%;width:{abs(px(r["orr"]) - px(r["drr"])):.1f}%;{gap}"></i>'
                f'<i class="mk tc" style="left:{px(r["drr"]):.1f}%;{dc}" title="{esc(d)} defense: {ordinal(r["drr"])}">{X_MARK}</i>'
                f'<i class="mk tc" style="left:{px(r["orr"]):.1f}%;{oc}" title="{esc(o)} offense: {ordinal(r["orr"])}">{O_MARK}</i>'
                f'</div></div>')
        blocks.append(f'<div class="blk"><div class="blk-h"><span>{pill(o)} offense <i class="lg tc" style="{oc}">{O_MARK}</i></span>'
                      f'<span class="blk-vs">vs</span><span>{pill(d)} defense <i class="lg tc" style="{dc}">{X_MARK}</i></span></div>'
                      f'{"".join(rows)}</div>')
    return "".join(blocks)


def matchup_card(a, h, off, dfn, o_rank, d_rank, start="b"):
    """The Matchup card: Chart | Numbers under its title (like Stat Leaders' Total | Behind); it opens
    on the chart (Jason, 2026-10-10: the quicker read, the numbers a tap away)."""
    sw = "".join(f'<button type="button" data-v="{v}"{" class=on" if v == start else ""}>{t}</button>'
                 for v, t in (("b", "Chart"), ("a", "Numbers")))
    return (f'<div class="card" data-view="{start}"><div class="ttl-row"><span class="ttl">Matchup</span></div>'
            f'<div class="mode-sw" role="group" aria-label="Show">{sw}</div>'
            f'<div class="sub v-a">Season to date · rank among 32 teams</div>'
            f'<div class="sub v-b">League rank · 1st on the right</div>'
            f'<div class="v-a">{numbers(a, h, off, dfn, o_rank, d_rank)}</div>'
            f'<div class="v-b">{chart(a, h, off, dfn, o_rank, d_rank)}</div></div>')


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--aag-bg);color:var(--aag-text);font-family:Inter,system-ui,sans-serif;padding:20px 16px 60px}
.abbr{font-family:Saira,Inter,sans-serif;font-style:italic;font-weight:800;font-variation-settings:'wdth' 95;letter-spacing:.02em;line-height:1}
header{max-width:1200px;margin:0 auto 18px}
h1{font-size:20px;margin-bottom:6px}
header p{font-size:13px;color:var(--aag-text-2);max-width:760px;line-height:1.45}
.ctl{display:flex;gap:8px;margin-top:10px}
.ctl button{font:inherit;font-size:12px;font-weight:700;padding:5px 12px;border-radius:999px;border:1px solid var(--aag-tile-border);
  background:var(--aag-tile);color:var(--aag-text);cursor:pointer}
.game{max-width:1200px;margin:26px auto 0}
.game h2{font-size:14px;letter-spacing:.08em;text-transform:uppercase;color:var(--aag-text-2);margin-bottom:12px;display:flex;gap:8px;align-items:center}
.row{display:flex;gap:22px;flex-wrap:wrap}
.opt{width:375px;max-width:100%}
.opt h3{font-size:15px;margin-bottom:4px}
.opt p{font-size:12px;color:var(--aag-text-2);line-height:1.4;margin-bottom:10px;min-height:50px}
.phone{background:var(--aag-bg);border:1px solid var(--aag-tile-border);border-radius:28px;padding:16px}
.card{background:var(--aag-tile);border:1px solid var(--aag-card-line);border-radius:20px;padding:12px 14px 14px}
.ttl-row{display:flex;justify-content:center}
.ttl{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;border:1px solid var(--aag-tile-border);
  border-radius:999px;padding:4px calc(11px - .12em) 4px 11px}
.sub{text-align:center;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--aag-text-2);margin:6px 0 2px}
.tpill{display:inline-flex;align-items:center;justify-content:center;height:18px;min-width:44px;padding:0 5px;border-radius:999px;
  border:2px solid transparent;color:var(--pl);font-size:10px;white-space:nowrap;
  background:linear-gradient(var(--pf1),var(--pf2)) padding-box,linear-gradient(var(--pr1),var(--pr2)) border-box}
.blk{margin-top:12px}
.blk+.blk{margin-top:16px;padding-top:12px;border-top:1px solid var(--aag-tile-border-soft)}
.blk-h{display:flex;align-items:center;justify-content:center;gap:8px;font-size:11px;font-weight:700;color:var(--aag-text-2);margin-bottom:6px}
.blk-h>span{display:inline-flex;align-items:center;gap:5px}
.blk-vs{color:var(--aag-text-3);font-weight:400}
/* A */
.er{display:grid;grid-template-columns:1fr 46px 16px 46px 52px;align-items:center;column-gap:4px;padding:6px 0;border-top:1px solid var(--aag-tile-border-soft)}
.er-hd{border-top:0;padding:0 0 2px;font-size:9px;font-weight:700;letter-spacing:.05em;color:var(--aag-text-3);text-align:center}
.er-l{font-size:13px;font-weight:700;line-height:1.15}
.er-l small{display:block;font-size:9.5px;font-weight:400;color:var(--aag-text-3)}
.er-v{text-align:center;line-height:1.1}
.er-v b{display:block;font-size:15px;font-variant-numeric:proportional-nums}
.er-v small{font-size:9.5px;font-weight:700;color:var(--aag-text-2)}
.er-vs{text-align:center;font-size:9px;color:var(--aag-text-3)}
.er-e{display:flex;justify-content:center}
.even{display:block;width:14px;height:2px;border-radius:1px;background:var(--aag-text-3)}   /* Even: just a line */
/* the switch and the two views */
.mode-sw{width:max-content;margin:8px auto 0;display:flex;gap:1px;padding:1px;border:1px solid var(--aag-tile-border);border-radius:999px}
.mode-sw button{font:inherit;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:3px 10px;border:0;
  border-radius:999px;background:none;color:var(--aag-text-2);cursor:pointer}
.mode-sw button.on{background:var(--aag-text);color:var(--aag-tile)}
.card[data-view=a] .v-b,.card[data-view=b] .v-a{display:none}
/* B -- a slim row: 32, the name, 1, then the track */
.tr{padding:5px 0 7px;border-top:1px solid var(--aag-tile-border-soft)}
.tr-top{display:grid;grid-template-columns:20px 1fr 20px;align-items:baseline;margin:0 0 6px}
.tr-l{text-align:center;font-size:12px;font-weight:700}
.tk{font-size:8.5px;font-weight:700;color:var(--aag-text-3)}
.tk:first-child{text-align:left}.tk:last-child{text-align:right}
.track{position:relative;height:3px;margin:0 2px 4px;border-radius:2px;background:var(--aag-tile-border)}
.track .gap{position:absolute;top:0;bottom:0;border-radius:2px;opacity:.6;background:var(--c)}
.track .mk{position:absolute;top:50%;width:14px;height:14px;margin:-7px 0 0 -7px;color:var(--c)}
.xo{display:block;width:100%;height:100%}
.lg{display:inline-block;width:12px;height:12px;color:var(--c)}
.tc{--c:var(--lc)}
/* each half's biggest edge: the row tinted, its stretch bolder, a tag in the favored team's color */
.er.top,.tr.top{background:var(--aag-tile-hover);border-radius:10px;border-top-color:transparent;margin:0 -8px;padding-left:8px;padding-right:8px}
.er.top+.er,.tr.top+.tr{border-top-color:transparent}
.tr.top .track{height:5px}
.tr.top .track .gap{opacity:1}
.top-tag{display:inline-block;width:9px;height:12px;margin-left:5px;vertical-align:-1px;color:var(--c)}
.top-tag svg{display:block;width:100%;height:100%}
.tr-nm{position:relative;display:inline-block}
.tr-nm .top-tag{position:absolute;left:100%;top:50%;transform:translateY(-50%);white-space:nowrap}   /* the name stays centered */
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .tc{--c:var(--dc)}}
:root[data-theme=dark] .tc{--c:var(--dc)}
"""


def page(data):
    off, dfn, pct, o_rank, d_rank = build(data)
    week = data.get("week")
    games = []
    for n, a, h, _m in pick_games(data, off, dfn, o_rank, d_rank):
        opts = [
            ("Opens on Chart", "Each row a line from 32nd to 1st -- O the offense, X the defense, the colored stretch "
             "between them the gap and who it favors. Each half's biggest edge is highlighted.",
             matchup_card(a, h, off, dfn, o_rank, d_rank, "b")),
            ("Numbers (a tap away)", "Both numbers, both league ranks, and who has the edge (Even when they're within "
             f"{EDGE_GAP} places). The same rows are highlighted.", matchup_card(a, h, off, dfn, o_rank, d_rank, "a")),
        ]
        cols = "".join(f'<div class="opt"><h3>{esc(t)}</h3><p>{esc(d)}</p><div class="phone">{body}</div></div>' for t, d, body in opts)
        games.append(f'<section class="game"><h2>Week {esc(week)} · {pill(a)} @ {pill(h)} <span style="font-weight:400">'
                     f'({n} edges)</span></h2><div class="row">{cols}</div></section>')
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Matchup Edges Mockup</title>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap' rel='stylesheet'>"
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&display=swap' rel='stylesheet'>"
        f"<style>{theme.THEME_CSS}{CSS}</style></head><body>"
        "<header><h1>Matchup edges -- mockup</h1>"
        "<p>Defense numbers: sportsdataverse's defense-vs-position file. Offense numbers: the site's own player stats, "
        f"the same four measures. Rank 1 = best in the NFL on that side. An edge goes to the side ranked {EDGE_GAP}+ places "
        "better; closer than that is Even. Pass rush: the offense wants a low sack rate, the defense a high one.</p>"
        "<div class='ctl'><button type='button' data-t='light'>Light</button><button type='button' data-t='dark'>Dark</button></div></header>"
        + "".join(games) +
        "<script>document.querySelectorAll('.ctl button').forEach(function(b){b.onclick=function(){"
        "document.documentElement.setAttribute('data-theme',b.dataset.t)}});"
        "document.querySelectorAll('.mode-sw button').forEach(function(b){b.onclick=function(){var c=b.closest('.card');"
        "c.setAttribute('data-view',b.dataset.v);c.querySelectorAll('.mode-sw button').forEach(function(x){x.classList.toggle('on',x===b)})}})"
        "</script></body></html>")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mockups", "matchup-edges.html")
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        data = json.load(f)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page(data))
    print("Wrote", out)

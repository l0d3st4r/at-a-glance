"""
Race chart over a full season -- mockup (2026-10-07), NOT part of the live build.

Jason: as the numbers keep climbing, the race chart (running totals from zero) has to keep showing how
far apart the top five are, and their path since week 1. On an axis from zero, a few hundred yards
between 4,000-yard passers is a sliver; the lines bunch at the top and the early weeks squash into the
corner. This draws the real top 5 for passing yards and sacks over a whole season -- weeks 1 to N real,
the rest simulated from each player's real pace (yards: his average a game, +/- a quarter; sacks: a
coin-flip count around his rate), each with one bye -- five ways:

  "Now"               the running total from zero, as the page draws it today
  "Behind the leader" his total minus that week's top total among the five: the leader rides along 0,
                      everyone else is "N behind" -- the gap stays the same size all season, a lead
                      change is two lines crossing at 0
  "Share of leader"   his total as a % of that week's top total
  "Per game"          his running average per game played (byes don't count)
  "Rank by week"      1st to 5th among the five, week by week (a bump chart)

Line colors are the page's (team_line_colors.py), for this page's ground. Weeks past the real ones sit on
a shaded band. Run after build_data.py:
    python mockups/build_race_scale_mockup.py [out.html]
Writes mockups/race-scale.html.
"""

import html
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import render_leaders  # noqa: E402
import theme  # noqa: E402

SEASON_WEEKS = 18   # 17 games + a bye


def esc(v):
    return html.escape(str(v), quote=True)


def season(top, P, real_weeks, kind, seed):
    """Each player's weekly numbers for a whole season: the real weeks, then simulated from his pace."""
    rnd = random.Random(seed)
    out = []
    for r in top:
        run = r[4]
        weekly = [run[0]] + [round(run[i] - run[i - 1], 1) for i in range(1, len(run))]
        if kind == "yds":   # a real week with no yards was a week he didn't play
            weekly = [w if w else None for w in weekly]
        played = [w for w in weekly if w is not None] or [0]
        pace = sum(played) / len(played)
        bye = rnd.randint(real_weeks + 2, 14)
        for wk in range(real_weeks + 1, SEASON_WEEKS + 1):
            if wk == bye:
                weekly.append(None)          # no game
            elif kind == "yds":
                weekly.append(max(0, round(rnd.gauss(pace, pace * .25))))
            else:
                weekly.append(sum(rnd.random() < pace / 3 for _ in range(3)) * 1.0 + (0.5 if rnd.random() < .15 else 0))
        out.append((P[r[1]], weekly))
    return out


def views(seasons):
    """The five ways to draw it: {view: (series per player, y-range, y tick formatter, invert?)}."""
    n = SEASON_WEEKS
    totals = []
    for _p, weekly in seasons:
        acc, run = 0, []
        for w in weekly:
            acc += w or 0
            run.append(acc)
        totals.append(run)
    top = [max(t[i] for t in totals) for i in range(n)]
    games = []
    for _p, weekly in seasons:
        g, run = 0, []
        for w in weekly:
            g += w is not None
            run.append(g)
        games.append(run)
    behind = [[t[i] - top[i] for i in range(n)] for t in totals]
    share = [[100 * t[i] / top[i] if top[i] else 100 for i in range(n)] for t in totals]
    pergame = [[t[i] / g[i] if g[i] else 0 for i in range(n)] for t, g in zip(totals, games)]
    ranks = []
    for t in totals:
        ranks.append([1 + sum(1 for o in totals if o[i] > t[i]) for i in range(n)])
    lo_b = min(min(b) for b in behind)
    lo_s = min(min(s[2:]) for s in share)
    pg = [v for s in pergame for v in s[2:]]
    return {
        "now": (totals, (0, max(top)), lambda v: f"{v:,.0f}", False),
        "behind": (behind, (lo_b, 0), lambda v: "Leader" if v == 0 else f"{v:,.0f}", False),
        "share": (share, (max(0, lo_s - 5), 100), lambda v: f"{v:.0f}%", False),
        "pergame": (pergame, (min(pg) * .9, max(pg) * 1.05), lambda v: f"{v:,.1f}", False),
        "rank": (ranks, (1, 5), lambda v: f"{v:.0f}", True),
    }, totals


W, H, PL, PR, PT, PB = 340, 170, 38, 66, 10, 18


def chart(series, yr, fmt, invert, colors, labels, real_weeks, kind_note):
    n = SEASON_WEEKS
    lo, hi = yr
    if hi == lo:
        hi = lo + 1
    x = lambda i: PL + (W - PL - PR) * i / (n - 1)
    y = (lambda v: PT + (H - PT - PB) * (v - lo) / (hi - lo)) if invert else (lambda v: PT + (H - PT - PB) * (1 - (v - lo) / (hi - lo)))
    out = [f'<rect x="{x(real_weeks - 1):.1f}" y="{PT}" width="{x(n - 1) - x(real_weeks - 1):.1f}" height="{H - PT - PB}" class="sim"/>']
    ticks = [1, 2, 3, 4, 5] if invert else [lo, (lo + hi) / 2, hi]
    for t in ticks:
        out.append(f'<line class="gl" x1="{PL}" x2="{W - PR}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                   f'<text class="ax" x="{PL - 5}" y="{y(t) + 3:.1f}" text-anchor="end">{esc(fmt(t))}</text>')
    for i in range(0, n, 4):
        out.append(f'<text class="ax" x="{x(i):.1f}" y="{H - 4}" text-anchor="middle">Wk {i + 1}</text>')
    ends = sorted((y(s[-1]), i) for i, s in enumerate(series))
    placed, prev = {}, -99
    for ly, i in ends:
        placed[i] = max(ly, prev + 11)
        prev = placed[i]
    for i, s in enumerate(series):
        c = colors[i]
        pts = " ".join(f"{x(j):.1f},{y(v):.1f}" for j, v in enumerate(s))
        out.append(f'<polyline class="ln tl" style="{c}" points="{pts}"/>'
                   f'<circle class="dt tl" style="{c}" cx="{x(n - 1):.1f}" cy="{y(s[-1]):.1f}" r="4.5"/>'
                   f'<text class="lb" x="{x(n - 1) + 8:.1f}" y="{placed[i] + 3:.1f}">{esc(labels[i])}</text>')
    return f'<svg viewBox="0 0 {W} {H}" class="race">{"".join(out)}</svg><p class="kn">{esc(kind_note)}</p>'


NOTES = {
    "now": ("Now: running total", "From zero. By late season the gaps are a sliver of the axis and the lines bunch at the top."),
    "behind": ("Behind the leader", "Total minus that week's top total. The leader rides the top line; the gap keeps its true size all season; a lead change is two lines crossing at the top."),
    "share": ("Share of the leader", "Total as a % of that week's top total. Readable late; the first weeks swing wildly (cut from the axis here)."),
    "pergame": ("Per game", "Running average per game played. Steady scale all season -- but it ranks by rate while the list ranks by total."),
    "rank": ("Rank by week", "1st to 5th among the five. Shows every lead change, says nothing about how big the gaps are."),
}


def page():
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        data = json.load(f)
    d = render_leaders.build(data.get("player_weeks"))
    P, real = d["players"], d["through"]
    cards = []
    for key, kind, seed in (("pyds", "yds", 7), ("dsk", "cnt", 11)):
        s = next(x for x in d["stats"] if x["key"] == key)
        top = s["rows"][:5]
        seasons = season(top, P, real, kind, seed)
        vs, totals = views(seasons)
        colors = [";".join(f"--{k}:{v}" for k, v in r[5].items()) for r in top]
        labels = [render_leaders.short(p[1]).split(". ")[-1][:10] for p, _w in seasons]
        panels = []
        for v in ("now", "behind", "share", "pergame", "rank"):
            series, yr, fmt, inv = vs[v]
            if v == "share":   # the first two weeks swing too wildly to show
                series = [[max(yr[0], min(100, x)) for x in sr] for sr in series]
            title, note = NOTES[v]
            panels.append(f'<section class="pn" data-v="{v}"><h3>{esc(title)}</h3>'
                          f'{chart(series, yr, fmt, inv, colors, labels, real, note)}</section>')
        final = sorted(zip(totals, seasons), key=lambda t: -t[0][-1])
        standings = " · ".join(f'{esc(render_leaders.short(p[1]))} {t[-1]:,.{1 if kind != "yds" else 0}f}' for t, (p, _w) in final)
        cards.append(f'<article class="card"><h2>{esc(s["name"])}</h2><p class="sub">Real weeks 1–{real}, simulated weeks {real + 1}–{SEASON_WEEKS} '
                     f'(shaded). Season end: {standings}</p>{"".join(panels)}</article>')
    css = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,system-ui,sans-serif;background:var(--aag-bg);color:var(--aag-text);-webkit-font-smoothing:antialiased;padding:12px 12px 40px}
.wrap{max-width:720px;margin:0 auto}
h1{font-size:18px;font-weight:900;margin-bottom:6px}
.intro{font-size:12px;line-height:1.45;color:var(--aag-text-2);margin-bottom:6px}
h2{font-size:14px;font-weight:900;letter-spacing:.06em;text-transform:uppercase;margin:20px 0 2px}
.sub{font-size:10.5px;color:var(--aag-text-2);margin-bottom:6px;line-height:1.4}
h3{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--aag-text-2);margin:12px 0 2px}
.pn{border-top:1px solid var(--aag-tile-border-soft);padding-top:2px}
.race{width:100%;height:auto;display:block;overflow:visible}
.kn{font-size:10.5px;color:var(--aag-text-3);margin-top:2px;line-height:1.35}
.sim{fill:var(--aag-tile-hover)}
.gl{stroke:var(--aag-tile-border-soft);stroke-width:1}
.ax{font-size:9px;fill:var(--aag-text-3)}
.ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.lb{font-size:10px;font-weight:700;fill:var(--aag-text)}
.tl{--c:var(--lc);--r:var(--lr);--d:var(--ld)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .tl{--c:var(--dc);--r:var(--dr);--d:var(--dd)}}
:root[data-theme=dark] .tl{--c:var(--dc);--r:var(--dr);--d:var(--dd)}
.ln.tl{stroke:var(--c);stroke-dasharray:var(--d)}
.dt.tl{fill:var(--c);stroke:var(--r);stroke-width:2}
@media (min-width:700px){.card{display:grid;grid-template-columns:1fr 1fr;column-gap:16px}.card h2,.card .sub{grid-column:1/-1}}
"""
    intro = ('<h1>Race chart, whole season</h1><p class="intro">The same top five drawn five ways, so you can see which still shows '
             'how far apart they are -- and their path since week 1 -- once the totals are big. Weeks past the real ones are simulated '
             'from each player\'s pace, with one bye each.</p>')
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Race chart, whole season</title><script>{theme.THEME_HEAD_JS}</script>"
            "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap' rel='stylesheet'>"
            f"<style>{theme.THEME_CSS}{css}</style></head><body><div class='wrap'>{intro}{''.join(cards)}</div></body></html>")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mockups", "race-scale.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page())
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

"""
Stat Leaders page mockup (2026-10-07) -- NOT part of the live build.

One place to follow the league's leaders in every player stat the site tracks (player_stats.py),
a page of its own beside Standings. Five layouts, each a different idea of what the page is for,
picked with the mockup-only strip at the top:

  A "Leaderboards"  -- the reference book. Every stat gets a card: the leader big (helmet, name,
                       number), then 2-5 underneath, under Passing / Rushing / Receiving / Defense /
                       Kicking / Returns headings. Scroll to browse.
  B "One stat deep" -- the deep dive. Pick a category, then a stat; the top 20 fill the screen as a
                       ranked list with a bar for each value, so the gaps between players show.
  C "At a glance"   -- the site's condensed idea: every stat's leader on one screen, two tiles a
                       row. Tap a tile for its top 5.
  D "Medal table"   -- about players, not stats: everyone with a league top-3 finish, ranked by
                       golds, then silvers, then bronzes (like the Olympics), with the stats they
                       medaled in. A switch flips it to teams.
  E "The race"      -- about time: one card per stat, swipe sideways between them; each charts the
                       top 5's running totals week by week, so you see who's pulling away.

Leaders are the regular season to date. Rate stats only count qualified players, as the NFL does:
Y/A 14 attempts a team game (player_stats.YPA_ATTEMPTS_PER_GAME), Y/C 6.25 carries a team game,
punt average 2.5 punts a team game. Ties share a place (two tied for 1st are both 1st).

The race chart's five line colors are the dataviz reference palette's first five categorical slots,
light and dark steps, checked with its validator against the site's two grounds (#F3F3EE / #161510):
both pass color-blind separation; in light mode four sit under 3:1 contrast, so every line carries
a direct name label and the list under the chart repeats the numbers.

Run after build_data.py (needs data/matchups.json):
    python mockups/build_stat_leaders_mockup.py [out.html]
Writes mockups/stat-leaders.html -- one self-contained file (helmets inlined once each in CSS).
stat-leaders.html#c opens on layout C.
"""

import html
import json
import os
import sys
import urllib.parse
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import helmets  # noqa: E402
import player_stats  # noqa: E402
import theme  # noqa: E402
from divisions import DIVISIONS  # noqa: E402
from render_page1 import CHEV  # noqa: E402
from render_page2players import PS_ICONS  # noqa: E402

SEASON = 2026


def esc(v):
    return html.escape(str(v), quote=True)


# ---------------------------------------------------------------- the stats

def _per(a, b):
    return lambda r: r[a] / r[b] if r[b] else 0


# (key, category, name, short name, value, decimals, qualifier per team game: (stat, minimum))
STATS = [
    ("pyds", "passing", "Passing Yards", "Pass Yds", lambda r: r["pyds"], 0, None),
    ("ptd", "passing", "Passing TDs", "Pass TD", lambda r: r["ptd"], 0, None),
    ("ypa", "passing", "Yards per Attempt", "Y/A", _per("pyds", "att"), 1, ("att", 14)),
    ("ryds", "rushing", "Rushing Yards", "Rush Yds", lambda r: r["ryds"], 0, None),
    ("rtd", "rushing", "Rushing TDs", "Rush TD", lambda r: r["rtd"], 0, None),
    ("ypc", "rushing", "Yards per Carry", "Y/C", _per("ryds", "car"), 1, ("car", 6.25)),
    ("rec", "receiving", "Receptions", "Rec", lambda r: r["rec"], 0, None),
    ("reyds", "receiving", "Receiving Yards", "Rec Yds", lambda r: r["reyds"], 0, None),
    ("retd", "receiving", "Receiving TDs", "Rec TD", lambda r: r["retd"], 0, None),
    ("tkl", "defense", "Tackles", "Tackles", lambda r: r["solo"] + r["ast"], 0, None),
    ("dsk", "defense", "Sacks", "Sacks", lambda r: r["dsk"], 1, None),
    ("tfl", "defense", "Tackles for Loss", "TFL", lambda r: r["tfl"], 0, None),
    ("dint", "defense", "Interceptions", "INT", lambda r: r["dint"], 0, None),
    ("pd", "defense", "Passes Defended", "PD", lambda r: r["pd"], 0, None),
    ("ff", "defense", "Forced Fumbles", "FF", lambda r: r["ff"], 0, None),
    ("fgm", "kicking", "Field Goals Made", "FG", lambda r: r["fgm"], 0, None),
    ("fglng", "kicking", "Longest Field Goal", "FG Long", lambda r: r["fglng"], 0, None),
    ("pavg", "kicking", "Punting Average", "Punt Avg", _per("pyd", "p"), 1, ("p", 2.5)),
    ("p20", "kicking", "Punts Inside the 20", "Inside 20", lambda r: r["p20"], 0, None),
    ("kryds", "returns", "Kick Return Yards", "KR Yds", lambda r: r["kryds"], 0, None),
    ("pryds", "returns", "Punt Return Yards", "PR Yds", lambda r: r["pryds"], 0, None),
]
CATS = [("passing", "Passing"), ("rushing", "Rushing"), ("receiving", "Receiving"),
        ("defense", "Defense"), ("kicking", "Kicking"), ("returns", "Returns")]
# medals (variant D) only for the stats the site already medals in (player_stats.MEDAL_STATS) plus PD
MEDAL_KEYS = ["pyds", "ptd", "ypa", "ryds", "rtd", "rec", "reyds", "retd", "tkl", "tfl", "dsk", "dint", "ff", "pd"]


def short(name):
    parts = (name or "").split()
    return f"{parts[0][0]}. {' '.join(parts[1:])}" if len(parts) > 1 else (name or "")


def load():
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        data = json.load(f)
    pw = data.get("player_weeks") or {}
    games = {t: len({r["wk"] for r in rows}) for t, rows in pw.items()}
    players = []
    for team in pw:
        for r in player_stats.season_totals(pw, team, None):
            r["team"] = team
            players.append(r)
    through = max((r["wk"] for rows in pw.values() for r in rows), default=0)
    return data, pw, games, players, through


def ranked(players, games, stat, n):
    """[(place, value, player)] -- the top n (and anyone tied with the nth), zero never counts."""
    key, _c, _name, _s, fn, _d, qual = stat
    vals = []
    for r in players:
        if qual and r[qual[0]] < qual[1] * games.get(r["team"], 0):
            continue
        v = fn(r)
        if v and v > 0:
            vals.append((v, r))
    vals.sort(key=lambda x: (-x[0], x[1]["name"]))
    out = []
    for i, (v, r) in enumerate(vals):
        place = 1 + sum(1 for w, _ in vals[:i] if w > v)
        if place > n:
            break
        out.append((place, v, r))
    return out


def fmt(v, d):
    return f"{v:.{d}f}" if d else f"{int(round(v)):,}"


# ---------------------------------------------------------------- shared bits

def helmet(team, size=18):
    return f'<i class="hm hl h-{team}" style="--hs:{size}px;width:{size}px;height:{size}px"></i>'


def helmet_css():
    return "".join(f'.h-{t}{{background-image:url("data:image/svg+xml,'
                   f'{urllib.parse.quote(helmets.helmet_svg(t, id_prefix="h" + t))}")}}' for t in DIVISIONS)


def icon(cat):
    return f'<span class="ic">{PS_ICONS.get(cat, "")}</span>'


def meta(r):
    return f'{esc(r["pos"])} · <span class="abbr">{esc(r["team"])}</span>'


MEDAL_CLASS = {1: "g", 2: "s", 3: "b"}


# ---------------------------------------------------------------- A: leaderboards

def variant_a(players, games):
    out = []
    for cat, cname in CATS:
        cards = []
        for st in [s for s in STATS if s[1] == cat]:
            top = ranked(players, games, st, 5)
            if not top:
                continue
            p1, v1, r1 = top[0]
            rest = "".join(
                f'<li><span class="pl pl-{MEDAL_CLASS.get(p, "")}">{p}</span>{helmet(r["team"])}'
                f'<span class="nm">{esc(short(r["name"]))}</span><span class="tm abbr">{esc(r["team"])}</span>'
                f'<span class="v">{fmt(v, st[5])}</span></li>' for p, v, r in top[1:])
            cards.append(
                f'<article class="a-card"><h3>{esc(st[2])}</h3>'
                f'<div class="a-lead">{helmet(r1["team"], 40)}<div class="a-who"><b>{esc(r1["name"])}</b>'
                f'<span>{meta(r1)}</span></div><span class="a-v">{fmt(v1, st[5])}</span></div>'
                f'<ol class="a-rest">{rest}</ol></article>')
        out.append(f'<section class="a-cat"><h2 class="cat-h">{icon(cat)}{cname}</h2>{"".join(cards)}</section>')
    return "".join(out)


# ---------------------------------------------------------------- B: one stat, deep

def variant_b(players, games):
    cats = "".join(f'<button class="chip{" on" if i == 0 else ""}" data-bcat="{c}">{icon(c)}{n}</button>'
                   for i, (c, n) in enumerate(CATS))
    stats_rows, panes = [], []
    for cat, _n in CATS:
        mine = [s for s in STATS if s[1] == cat]
        stats_rows.append(f'<div class="b-stats{" on" if cat == "passing" else ""}" data-bcat="{cat}">'
                          + "".join(f'<button class="chip sm{" on" if j == 0 else ""}" data-bstat="{s[0]}">{esc(s[3])}</button>'
                                    for j, s in enumerate(mine)) + "</div>")
        for st in mine:
            top = ranked(players, games, st, 20)
            hi = top[0][1] if top else 1
            rows = "".join(
                f'<li title="{esc(r["name"])} ({esc(r["team"])}): {fmt(v, st[5])}">'
                f'<span class="pl">{p}</span>{helmet(r["team"])}<span class="nm">{esc(short(r["name"]))}'
                f'<small>{meta(r)}</small></span>'
                f'<span class="bar"><i style="width:{max(2, v / hi * 100):.1f}%"></i></span>'
                f'<span class="v">{fmt(v, st[5])}</span></li>' for p, v, r in top)
            qual = (f'<p class="qual">Qualified: {st[6][1]:g} {"attempts" if st[6][0] == "att" else "carries" if st[6][0] == "car" else "punts"} '
                    f'a team game</p>') if st[6] else ""
            panes.append(f'<div class="b-pane{" on" if st[0] == "pyds" else ""}" data-bstat="{st[0]}">'
                         f'<h3 class="b-h">{esc(st[2])}</h3>{qual}<ol class="b-list">{rows}</ol></div>')
    return (f'<div class="b-pick"><div class="b-cats">{cats}</div>{"".join(stats_rows)}</div>'
            f'{"".join(panes)}')


# ---------------------------------------------------------------- C: at a glance

def variant_c(players, games):
    tiles = []
    for cat, cname in CATS:
        for st in [s for s in STATS if s[1] == cat]:
            top = ranked(players, games, st, 5)
            if not top:
                continue
            _p, v1, r1 = top[0]
            more = "".join(f'<li><span class="pl">{p}</span>{helmet(r["team"], 14)}<span class="nm">{esc(short(r["name"]))}</span>'
                           f'<span class="v">{fmt(v, st[5])}</span></li>' for p, v, r in top)
            tiles.append(
                f'<button class="c-tile" type="button" data-cat="{cat}"><span class="c-lbl">{icon(cat)}{esc(st[3])}</span>'
                f'<span class="c-who">{helmet(r1["team"], 22)}<span class="c-nm">{esc(short(r1["name"]))}</span></span>'
                f'<span class="c-v">{fmt(v1, st[5])}</span>'
                f'<span class="c-more"><b>{esc(st[2])}</b><ol>{more}</ol></span></button>')
    return f'<div class="c-grid">{"".join(tiles)}</div><p class="hint">Tap a tile for its top 5</p>'


# ---------------------------------------------------------------- D: medal table

def variant_d(players, games):
    by_player = defaultdict(lambda: {1: [], 2: [], 3: []})
    by_team = defaultdict(lambda: {1: 0, 2: 0, 3: 0})
    who = {}
    for st in [s for s in STATS if s[0] in MEDAL_KEYS]:
        for p, v, r in ranked(players, games, st, 3):
            k = (r["team"], r["id"])
            who[k] = r
            by_player[k][p].append(st[3])
            by_team[r["team"]][p] += 1

    def table(items, kind):
        items = sorted(items, key=lambda kv: (-len(kv[1][1]) if kind == "p" else -kv[1][1],
                                              -len(kv[1][2]) if kind == "p" else -kv[1][2],
                                              -len(kv[1][3]) if kind == "p" else -kv[1][3]))
        rows = []
        for i, (k, m) in enumerate(items, 1):
            counts = [len(m[x]) if kind == "p" else m[x] for x in (1, 2, 3)]
            if kind == "p":
                r = who[k]
                name = (f'{helmet(r["team"], 22)}<span class="nm"><b>{esc(short(r["name"]))}</b><small>{meta(r)}</small>'
                        f'<span class="d-tags">' + "".join(f'<em class="t-{MEDAL_CLASS[x]}">{esc(s)}</em>' for x in (1, 2, 3) for s in m[x])
                        + '</span></span>')
            else:
                name = f'{helmet(k, 22)}<span class="nm"><b class="abbr">{esc(k)}</b></span>'
            rows.append(f'<li><span class="pl">{i}</span>{name}'
                        + "".join(f'<span class="mc mc-{MEDAL_CLASS[x]}">{c}</span>' if c else '<span class="mc mc-0">·</span>'
                                  for x, c in zip((1, 2, 3), counts))
                        + '</li>')
        head = ('<li class="d-head"><span></span><span></span><span></span><span class="mc"><i class="dot g"></i></span>'
                '<span class="mc"><i class="dot s"></i></span><span class="mc"><i class="dot b"></i></span></li>')
        return f'<ol class="d-list" data-dview="{kind}"{" hidden" if kind == "t" else ""}>{head}{"".join(rows)}</ol>'

    switch = ('<div class="d-sw"><button class="chip on" data-dsw="p">Players</button>'
              '<button class="chip" data-dsw="t">Teams</button></div>')
    note = ('<p class="hint">League top 3 in each of 14 stats: passing yards / TDs / Y/A, rushing yards / TDs, '
            'receptions, receiving yards / TDs, tackles, TFL, sacks, INT, forced fumbles, passes defended</p>')
    return switch + table(by_player.items(), "p") + table(by_team.items(), "t") + note


# ---------------------------------------------------------------- E: the race

def weekly(pw, team, pid, through):
    by_wk = defaultdict(lambda: defaultdict(int))
    for r in pw.get(team) or []:
        if r["id"] == pid:
            for k in player_stats.STATS:
                if r.get(k):
                    by_wk[r["wk"]][k] += r[k]
    return [by_wk.get(w, {}) for w in range(1, through + 1)]


RACE_KEYS = ["pyds", "ptd", "ryds", "rtd", "rec", "reyds", "retd", "tkl", "dsk", "dint", "fgm", "kryds"]
W, H, PADL, PADR, PADT, PADB = 343, 190, 30, 64, 10, 22


def variant_e(pw, players, games, through):
    chips, cards = [], []
    for st in [s for s in STATS if s[0] in RACE_KEYS]:
        top = ranked(players, games, st, 5)[:5]
        if not top:
            continue
        series = []
        for _p, v, r in top:
            run, acc = [], defaultdict(int)
            for wk in weekly(pw, r["team"], r["id"], through):
                for k, x in wk.items():
                    acc[k] += x
                acc_row = defaultdict(int, acc)
                run.append(st[4](acc_row))
            series.append((r, run))
        hi = max(max(run) for _r, run in series) or 1
        x = lambda i: PADL + (W - PADL - PADR) * (i / max(1, through - 1))
        y = lambda v: PADT + (H - PADT - PADB) * (1 - v / hi)
        grid = "".join(f'<line class="gl" x1="{PADL}" x2="{W - PADR}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                       f'<text class="ax" x="{PADL - 6}" y="{y(t) + 3:.1f}" text-anchor="end">{fmt(t, 0)}</text>'
                       for t in (0, hi / 2, hi))
        xs = "".join(f'<text class="ax" x="{x(i):.1f}" y="{H - 6}" text-anchor="middle">Wk {i + 1}</text>' for i in range(through))
        lines, labels = [], []
        ends = sorted(((y(run[-1]), i) for i, (_r, run) in enumerate(series)))
        placed = {}
        last = -99
        for ly, i in ends:   # nudge end labels apart so they don't collide
            ly = max(ly, last + 11)
            placed[i] = ly
            last = ly
        for i, (r, run) in enumerate(series):
            pts = " ".join(f"{x(j):.1f},{y(v):.1f}" for j, v in enumerate(run))
            lines.append(f'<polyline class="ln s{i + 1}" points="{pts}"/>'
                         f'<circle class="dt s{i + 1}" cx="{x(len(run) - 1):.1f}" cy="{y(run[-1]):.1f}" r="4"/>')
            labels.append(f'<text class="lb" x="{x(len(run) - 1) + 8:.1f}" y="{placed[i] + 3:.1f}">'
                          f'{esc(short(r["name"]).split(". ")[-1][:10])}</text>')
        data = json.dumps([[short(r["name"]), [round(v, 1) for v in run]] for r, run in series])
        svg = (f'<svg class="race" viewBox="0 0 {W} {H}" data-series=\'{esc(data)}\' data-d="{st[5]}" role="img" '
               f'aria-label="{esc(st[2])}: running totals by week for the top five">{grid}{xs}{"".join(lines)}{"".join(labels)}'
               f'<line class="xh" y1="{PADT}" y2="{H - PADB}" x1="0" x2="0"/></svg>')
        legend = "".join(f'<li><i class="sw s{i + 1}"></i>{helmet(r["team"])}<span class="nm">{esc(short(r["name"]))}'
                         f'<small>{meta(r)}</small></span><span class="v">{fmt(v, st[5])}</span></li>'
                         for i, (_p, v, r) in enumerate(top))
        chips.append(f'<button class="chip sm{" on" if not chips else ""}" data-ego="{len(chips)}">{esc(st[3])}</button>')
        cards.append(f'<article class="e-card"><h3>{icon(st[1])}{esc(st[2])}</h3>'
                     f'<div class="e-chart">{svg}<div class="tip" hidden></div></div><ol class="e-leg">{legend}</ol></article>')
    return f'<div class="e-chips">{"".join(chips)}</div><div class="e-track">{"".join(cards)}</div>'


# ---------------------------------------------------------------- page

CSS = """
:root{--bbar:""" + theme.BBAR_HEIGHT + """;--text:var(--aag-text);--text-2:var(--aag-text-2);--text-3:var(--aag-text-3);
  --line:var(--aag-tile-border);--line-soft:var(--aag-tile-border-soft);--gold:#D4A20A;--silver:#A2A7AD;--bronze:#B5702F;
  --s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181}}
:root[data-theme=dark]{--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--aag-bg)}
body{min-height:100vh;color:var(--text);font-family:Inter,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
button{font:inherit;color:inherit}
.abbr{line-height:1;font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;font-style:italic;font-variation-settings:'wdth' 95;letter-spacing:.02em}
.hl{display:inline-block;flex:none;background-position:center;background-size:contain;background-repeat:no-repeat}
.ic svg{height:1em;width:auto;display:block}
.ic{display:inline-flex;margin-right:6px}

.mock{position:sticky;top:0;z-index:20;display:flex;flex-wrap:wrap;justify-content:center;gap:6px;padding:8px 12px;
  background:var(--aag-bar-bg);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);border-bottom:1px dashed var(--line);font-size:12px}
.mock b{font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-3);align-self:center}
.mock button{background:none;border:1px solid var(--line);border-radius:999px;padding:3px 10px;cursor:pointer}
.mock button.on{background:var(--text);color:var(--aag-bg);border-color:var(--text)}
.mock .why{flex-basis:100%;text-align:center;color:var(--text-2);font-size:11px}

.wrap{max-width:600px;margin:0 auto;padding:10px 16px calc(28px + var(--bbar))}
.variant{display:none}.variant.on{display:block}
.top{display:flex;flex-direction:column;align-items:center;gap:2px;padding:4px 0 12px}
.yr{font-size:36px}
.rs-line{display:flex;gap:6px;align-items:baseline;font-size:11px;white-space:nowrap}
.rs{letter-spacing:.12em;text-transform:uppercase;color:var(--text-2);font-weight:700}
.thru{color:var(--text-3)}
.thru::before{content:"·";margin-right:6px}
.chip{display:inline-flex;align-items:center;background:none;border:1px solid transparent;border-radius:999px;padding:5px 12px;
  font-size:14px;font-weight:700;cursor:pointer;opacity:.45;white-space:nowrap}
.chip.on{opacity:1;border-color:var(--line)}
.chip.sm{font-size:12px;padding:4px 10px}
.hint{text-align:center;font-size:11px;color:var(--text-3);margin-top:12px}
.pl{font-size:11px;font-weight:700;color:var(--text-3);text-align:right;font-variant-numeric:tabular-nums}
.v{font-variant-numeric:tabular-nums;font-weight:700;text-align:right}
.nm{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nm small{display:block;font-size:10px;color:var(--text-3);font-weight:400}
.nm small .abbr{font-size:10px}

/* A */
.cat-h{display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:900;letter-spacing:.1em;
  text-transform:uppercase;margin:22px 0 4px}
.a-cat:first-child .cat-h{margin-top:4px}
.a-card{padding:12px 4px 10px;border-bottom:1px solid var(--line-soft)}
.a-card h3{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-2);margin-bottom:8px}
.a-lead{display:flex;align-items:center;gap:10px}
.a-who{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.a-who b{font-size:16px}
.a-who span{font-size:11px;color:var(--text-2)}
.a-who .abbr{font-size:11px}
.a-v{font-family:Teko,Inter,sans-serif;font-size:40px;line-height:.9;font-weight:600}
.a-rest{list-style:none;margin-top:8px}
.a-rest li{display:grid;grid-template-columns:16px 18px minmax(0,1fr) 36px 48px;gap:6px;align-items:center;padding:3px 0;font-size:13px}
.a-rest .tm{font-size:12px;color:var(--text-2)}
.pl-g,.pl-s,.pl-b{border-bottom:3px solid;padding-bottom:1px}
.pl-g{border-color:var(--gold)}.pl-s{border-color:var(--silver)}.pl-b{border-color:var(--bronze)}

/* B */
.b-pick{position:sticky;top:76px;z-index:5;background:var(--aag-bg);padding-bottom:6px;margin:0 -16px;padding-inline:16px}
.b-cats,.b-stats{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;justify-content:flex-start}
.b-cats::-webkit-scrollbar,.b-stats::-webkit-scrollbar{display:none}
.b-stats{display:none;justify-content:center;margin-top:4px}
.b-stats.on{display:flex}
.b-pane{display:none}.b-pane.on{display:block}
.b-h{text-align:center;font-size:15px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;margin-top:10px}
.qual{text-align:center;font-size:11px;color:var(--text-3);margin-top:2px}
.b-list{list-style:none;margin-top:8px}
.b-list li{display:grid;grid-template-columns:18px 18px 112px minmax(0,1fr) 44px;gap:8px;align-items:center;padding:4px 0;
  border-bottom:1px solid var(--line-soft);font-size:13px}
.b-list li:last-child{border-bottom:0}
.bar{height:8px;display:block}
.bar i{display:block;height:100%;background:var(--text-2);border-radius:0 4px 4px 0}
.b-list li:first-child .bar i{background:var(--text)}

/* C */
.c-grid{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.c-tile{position:relative;display:grid;grid-template-columns:minmax(0,1fr) auto;grid-template-rows:auto auto;gap:2px 6px;
  text-align:left;background:var(--aag-tile-hover);border:0;border-radius:12px;padding:5px 9px;cursor:pointer}
.c-lbl{grid-column:1/-1;display:flex;align-items:center;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2)}
.c-lbl .ic{margin-right:4px}
.c-who{display:flex;align-items:center;gap:5px;min-width:0}
.c-nm{font-size:12px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.c-v{font-family:Teko,Inter,sans-serif;font-size:21px;line-height:1;font-weight:600}
.v-c .top{padding-bottom:8px}
.c-more{display:none}
.c-tile.open{grid-column:1/-1}
.c-tile.open .c-more{display:block;grid-column:1/-1;margin-top:6px}
.c-more b{display:block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2);margin-bottom:4px}
.c-more ol{list-style:none}
.c-more li{display:grid;grid-template-columns:14px 14px minmax(0,1fr) 44px;gap:6px;align-items:center;font-size:12px;padding:2px 0}

/* D */
.d-sw{display:flex;justify-content:center;gap:4px;margin-bottom:6px}
.d-list{list-style:none}
.d-list li{display:grid;grid-template-columns:18px 22px minmax(0,1fr) 24px 24px 24px;gap:8px;align-items:center;padding:7px 0;
  border-bottom:1px solid var(--line-soft);font-size:13px}
.d-list li.d-head{padding:0 0 4px;border-bottom:0}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%}
.dot.g,.mc-g{--m:var(--gold)}.dot.s,.mc-s{--m:var(--silver)}.dot.b,.mc-b{--m:var(--bronze)}
.dot{background:var(--m)}
.mc{text-align:center;font-weight:700;font-variant-numeric:tabular-nums}
.mc-g,.mc-s,.mc-b{border-bottom:3px solid var(--m);padding-bottom:1px;justify-self:center;min-width:14px}
.d-tags{display:flex;flex-wrap:wrap;gap:3px;margin-top:3px}
.d-tags em{font-style:normal;font-size:10px;padding:0 5px;border-radius:999px;border:1.5px solid;line-height:15px}
.d-tags .t-g{border-color:var(--gold)}.d-tags .t-s{border-color:var(--silver)}.d-tags .t-b{border-color:var(--bronze)}
.mc-0{color:var(--text-3)}

/* E */
.e-chips{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;margin:0 -16px 6px;padding:0 16px}
.e-chips::-webkit-scrollbar{display:none}
.e-track{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;margin:0 -16px;overscroll-behavior-x:contain}
.e-track::-webkit-scrollbar{display:none}
.e-card{flex:0 0 100%;scroll-snap-align:start;padding:0 16px}
.e-card h3{display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;margin:6px 0 4px}
.e-chart{position:relative}
.race{width:100%;height:auto;display:block;overflow:visible}
.gl{stroke:var(--line-soft);stroke-width:1}
.ax{font-size:9px;fill:var(--text-3)}
.ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.dt{stroke:var(--aag-bg);stroke-width:2}
.lb{font-size:10px;font-weight:700;fill:var(--text)}
.s1{stroke:var(--s1)}.s2{stroke:var(--s2)}.s3{stroke:var(--s3)}.s4{stroke:var(--s4)}.s5{stroke:var(--s5)}
circle.s1{fill:var(--s1)}circle.s2{fill:var(--s2)}circle.s3{fill:var(--s3)}circle.s4{fill:var(--s4)}circle.s5{fill:var(--s5)}
.xh{stroke:var(--text-3);stroke-width:1;stroke-dasharray:2 3;opacity:0}
.race.hover .xh{opacity:1}
.tip{position:absolute;top:0;pointer-events:none;background:var(--aag-bg);border:1px solid var(--line);border-radius:8px;
  padding:5px 8px;font-size:11px;box-shadow:0 4px 14px rgba(0,0,0,.15);white-space:nowrap}
.tip b{display:block;margin-bottom:2px}
.e-leg{list-style:none;margin-top:6px}
.e-leg li{display:grid;grid-template-columns:12px 18px minmax(0,1fr) 48px;gap:8px;align-items:center;padding:5px 0;
  border-bottom:1px solid var(--line-soft);font-size:13px}
.e-leg li:last-child{border-bottom:0}
.sw{width:12px;height:3px;border-radius:2px}
i.sw.s1{background:var(--s1)}i.sw.s2{background:var(--s2)}i.sw.s3{background:var(--s3)}i.sw.s4{background:var(--s4)}i.sw.s5{background:var(--s5)}

.bottombar{position:fixed;left:0;right:0;bottom:0;z-index:10;height:var(--bbar);padding-bottom:env(safe-area-inset-bottom);
  background:var(--aag-bar-bg);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.bar-in{position:relative;max-width:600px;height:52px;margin:0 auto;display:flex;align-items:flex-start;justify-content:center;padding-top:10px}
.week{color:inherit;text-decoration:none;display:inline-flex;align-items:center;gap:6px;font-size:16px;line-height:19px;padding:6px 12px}
.week .chev{width:12px;height:12px}
""" + theme.MENU_CSS + theme.HELMET_SHADOW_CSS

JS = r"""
(function () {
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-pick-variant]');
    if (b) {
      var v = b.getAttribute('data-pick-variant');
      document.querySelectorAll('[data-pick-variant]').forEach(function (x) { x.classList.toggle('on', x === b); });
      document.querySelectorAll('.variant').forEach(function (x) { x.classList.toggle('on', x.getAttribute('data-variant') === v); });
      document.querySelector('.why').textContent = b.getAttribute('data-why');
      scrollTo(0, 0); return;
    }
    var c = e.target.closest('[data-bcat]');
    if (c && c.classList.contains('chip')) {
      var cat = c.getAttribute('data-bcat');
      document.querySelectorAll('.b-cats .chip').forEach(function (x) { x.classList.toggle('on', x === c); });
      document.querySelectorAll('.b-stats').forEach(function (x) { x.classList.toggle('on', x.getAttribute('data-bcat') === cat); });
      var first = document.querySelector('.b-stats[data-bcat="' + cat + '"] .chip'); if (first) first.click();
      return;
    }
    var s = e.target.closest('[data-bstat]');
    if (s && s.classList.contains('chip')) {
      var k = s.getAttribute('data-bstat');
      s.parentNode.querySelectorAll('.chip').forEach(function (x) { x.classList.toggle('on', x === s); });
      document.querySelectorAll('.b-pane').forEach(function (x) { x.classList.toggle('on', x.getAttribute('data-bstat') === k); });
      return;
    }
    var t = e.target.closest('.c-tile');
    if (t) { var was = t.classList.contains('open'); document.querySelectorAll('.c-tile.open').forEach(function (x) { x.classList.remove('open'); }); if (!was) t.classList.add('open'); return; }
    var d = e.target.closest('[data-dsw]');
    if (d) {
      var kind = d.getAttribute('data-dsw');
      document.querySelectorAll('[data-dsw]').forEach(function (x) { x.classList.toggle('on', x === d); });
      document.querySelectorAll('.d-list').forEach(function (x) { x.hidden = x.getAttribute('data-dview') !== kind; });
      return;
    }
    var g = e.target.closest('[data-ego]');
    if (g) { var tr = document.querySelector('.e-track'); tr.scrollTo({ left: +g.getAttribute('data-ego') * tr.clientWidth, behavior: 'smooth' }); }
  });
  // #a .. #e opens on that layout
  var start = document.querySelector('[data-pick-variant="' + location.hash.slice(1) + '"]');
  if (start) start.click();
  // E: the chip row follows the swipe
  var tr = document.querySelector('.e-track'), chips = [].slice.call(document.querySelectorAll('[data-ego]')), settle;
  if (tr) tr.addEventListener('scroll', function () {
    clearTimeout(settle);
    settle = setTimeout(function () {
      var i = Math.round(tr.scrollLeft / tr.clientWidth);
      chips.forEach(function (c, j) { c.classList.toggle('on', j === i); });
      if (chips[i]) chips[i].scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' });
    }, 90);
  }, { passive: true });
  // E: crosshair + tooltip -- the nearest week, every runner's total at that point
  document.querySelectorAll('.race').forEach(function (svg) {
    var data = JSON.parse(svg.getAttribute('data-series')), dec = +svg.getAttribute('data-d'),
        tip = svg.parentNode.querySelector('.tip'), xh = svg.querySelector('.xh'),
        n = data[0][1].length, L = """ + str(PADL) + """, R = """ + str(W - PADR) + """, W = """ + str(W) + """;
    function show(ev) {
      var box = svg.getBoundingClientRect(), px = (ev.clientX - box.left) / box.width * W,
          i = Math.max(0, Math.min(n - 1, Math.round((px - L) / ((R - L) / Math.max(1, n - 1))))), x = L + (R - L) * i / Math.max(1, n - 1);
      xh.setAttribute('x1', x); xh.setAttribute('x2', x); svg.classList.add('hover');
      tip.innerHTML = '<b>Week ' + (i + 1) + '</b>' + data.map(function (s) { return s[0] + ' &nbsp;' + s[1][i].toFixed(dec); }).join('<br>');
      tip.hidden = false;
      var left = x / W * box.width + 10; if (left + 140 > box.width) left = x / W * box.width - 150;
      tip.style.left = left + 'px';
    }
    svg.addEventListener('pointermove', show);
    svg.addEventListener('pointerdown', show);
    svg.addEventListener('pointerleave', function () { svg.classList.remove('hover'); tip.hidden = true; });
  });
})();
"""

WHY = {
    "a": "The reference book: every stat's leader big, with 2-5 under it. Scroll to browse.",
    "b": "The deep dive: pick one stat and see the top 20, with bars so the gaps show.",
    "c": "At a glance: every stat's leader on one screen. Tap a tile for its top 5.",
    "d": "About players, not stats: who has the most league top-3 finishes.",
    "e": "About time: who's pulling away, week by week. Swipe between stats.",
}
NAMES = {"a": "A · Leaderboards", "b": "B · One stat deep", "c": "C · At a glance", "d": "D · Medal table", "e": "E · The race"}


def page(data, pw, games, players, through):
    bodies = {"a": variant_a(players, games), "b": variant_b(players, games), "c": variant_c(players, games),
              "d": variant_d(players, games), "e": variant_e(pw, players, games, through)}
    top = (f'<header class="top"><span class="yr abbr">{SEASON}</span><span class="rs-line"><span class="rs">Stat Leaders</span>'
           f'<span class="thru">Through Week {through}</span></span></header>')
    variants = "".join(f'<div class="variant v-{k}{" on" if k == "a" else ""}" data-variant="{k}">{top}{b}</div>'
                       for k, b in bodies.items())
    mock = ('<div class="mock"><b>Mockup</b>'
            + "".join(f'<button class="{"on" if k == "a" else ""}" data-pick-variant="{k}" data-why="{esc(WHY[k])}">{n}</button>'
                      for k, n in NAMES.items())
            + f'<div class="why">{esc(WHY["a"])}</div></div>')
    menu = theme.menu_html("", None).replace('<a href="standings.html">Standings</a>',
                                             '<a href="standings.html">Standings</a><a href="#" aria-current="page">Stat Leaders</a>')
    bar = ('<nav class="bottombar"><div class="bar-in">' + menu
           + f'<a class="week" href="#">{CHEV}<span>Week {through + 1}</span></a></div></nav>')
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        f"<title>{SEASON} Stat Leaders mockup</title><script>{theme.THEME_HEAD_JS}</script>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
        f"<style>{theme.THEME_CSS}{CSS}{helmet_css()}</style></head><body>"
        f"{mock}<main class='wrap'>{variants}</main>{bar}"
        f"<script>{theme.THEME_JS}</script><script>{JS}</script></body></html>"
    )


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mockups", "stat-leaders.html")
    data, pw, games, players, through = load()
    with open(out, "w", encoding="utf-8") as f:
        f.write(page(data, pw, games, players, through))
    print(f"Wrote {out} ({len(players)} players, through week {through})")


if __name__ == "__main__":
    main()

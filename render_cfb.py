"""
Renders the college football section (2026-10-12) from data/cfb.json (after build_cfb_data.py has run):

  site/cfb/index.html        Page 0: each week's games involving AP poll teams, the rank ahead of each
                             ranked team's abbreviation ("A" in mockups/build_cfb_mockup.py, Jason)
  site/cfb/game/*.html       each game's page and its deep dives
  site/cfb/rankings.html     Rankings, in Standings' place: AP Poll | Coaches Poll | CFP
  site/cfb/leaders.html      Stat Leaders, every FBS player
  site/cfb/helmets/*.svg     each school's helmet in its colors
  site/cfb/cfb-snapshot.json what this build learned for the next one (build_cfb_data.py)

Run with: python render_cfb.py  (--data to read another file)

Unlike the NBA section, which writes its own markup, this one IS the NFL pages: render_html, render_page1
(with the team pages, Game Info, Player Stats and Matchups) and render_leaders draw it, with their own
CSS and scripts. setup() points them at college before anything is drawn -- in this process only (the
workflow runs each section as its own step, so the NFL's pages never see it):
  - helmets in Jason's colors (cfb_helmet_colors.py, 2026-10-12), else cfb_team_info's two; the team pills and
    chart lines from the same colors (pill_colors); helmets in site/cfb/helmets/
  - school names wherever a page names a team; the menu and favicon links one folder deeper
  - the AP rank ahead of a ranked team's abbreviation on Page 0's tiles, Teams on Bye and Page 1's top bar
    (the rank that week); "vs" for "@" at a neutral site; a bowl's or title game's name under its tile's TV
  - team cards: the injury report's place goes to the conference and conference record, then the AP rank
    poll by poll (Jason, 2026-10-12: the rank trend line); offense / defense ranks out of the FBS teams on
    the NFL's green-to-red scale, stretched; the team pages drop Injuries (no source) and show the
    conference standings around the team, places numbered
  - Matchups from the play-by-play's EPA (build_cfb_data.matchup_inputs), the edge a quarter of the field
    (8 places of 32 in the NFL)
  - Player Stats and Stat Leaders without the columns the college box score lacks (first downs, net
    punting), and the NCAA's passer efficiency in place of the NFL passer rating
  - Jason's college icons (cfb_icons.py) for Game Info, Passing, Receiving, Kicking, Overview and Schedule
"""

import argparse
import html
import json
import os
import re
import shutil

import cfb_helmet_colors
import cfb_icons
import helmets
import logo
import matchup
import render_html as rh
import render_leaders as rl
import render_page1 as p1
import render_page2players as ps
import render_page2team as tp
import render_standings as rs
import team_line_colors
import theme

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "data", "cfb.json")
SNAP_PATH = os.path.join(ROOT, "data", "cfb-snapshot.json")
SITE_DIR = os.path.join(ROOT, "site", "cfb")
DASH = "—"
MIN_TILE = 26   # px: the shortest a condensed Page 0 row may be (see main)

# The CFP committee's rankings (collegefootballplayoff.com/about-the-rankings), by season: Tuesdays, then
# the 12-team field on Selection Day. The CFP tab says so until ESPN's rankings carry the first one.
CFP_DATES = {2026: [("Tuesday", "Nov 3"), ("Tuesday", "Nov 10"), ("Tuesday", "Nov 17"), ("Tuesday", "Nov 24"),
                    ("Tuesday", "Dec 1"), ("Sunday", "Dec 6")]}


def esc(v):
    return html.escape(str(v), quote=True)


def file_of(abbr):
    return re.sub(r"[^A-Za-z0-9]", "_", abbr or "_")


# ---------------------------------------------------------------- helmets and team colors

def team_colors(t):
    """(shell, facemask, ear piece): Jason's picks (cfb_helmet_colors.py), else the school's primary on the
    shell and its alternate on the facemask and ear piece."""
    pick = cfb_helmet_colors.HELMET_COLORS.get(t.get("id"))
    if pick:
        return pick
    alt = t.get("alt_color") or helmets.FALLBACK_COLORS[1]
    return (t.get("color") or helmets.FALLBACK_COLORS[0], alt, alt)


def pill_colors(t):
    """(fill, ring) for the team pill, whose letters are always white: the helmet's shell and facemask --
    unless the shell is too light for white letters (a white, gold or silver helmet), when the fill is the
    ear piece or facemask color that white reads on and the ring is the shell."""
    shell, mask, ear = team_colors(t)
    reads = lambda c: team_line_colors.contrast(c, "#FFFFFF") >= 3
    if reads(shell):
        return shell, mask
    for c in (ear, mask):
        if reads(c):
            return c, shell
    return (t.get("color") or shell), (t.get("alt_color") or mask)


def write_helmets(teams, out_dir):
    for sub, width in (("", helmets.OUTLINE_WIDTH), (helmets.LARGE_DIR, helmets.LARGE_OUTLINE_WIDTH)):
        folder = os.path.join(out_dir, "helmets", sub)
        os.makedirs(folder, exist_ok=True)
        for a, t in list(teams.items()) + [("_", {})]:
            colors = team_colors(t)
            for mir in (False, True):
                name = f"{file_of(a)}-mirrored.svg" if mir else f"{file_of(a)}.svg"
                with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
                    f.write(helmets.helmet_svg(a, mirrored=mir, outline_width=width, colors=colors))


def helmet_filename(team, mirrored=False, large=False):
    name = f"{file_of(team)}-mirrored.svg" if mirrored else f"{file_of(team)}.svg"
    return f"{helmets.LARGE_DIR}/{name}" if large else name


# ---------------------------------------------------------------- Page 0 / Page 1 additions

BADGE_CSS = """
.rk{font-family:Inter,system-ui,sans-serif;font-style:normal;font-weight:700;font-size:.6em;color:var(--aag-text-2);
  margin-right:.18em;vertical-align:.2em;letter-spacing:0}
/* under the helmet the number hangs off the abbreviation's left, so the abbreviation stays centered */
.team .abbr{position:relative}
.team .rk{position:absolute;right:100%;top:.2em;line-height:1}
/* condensed: inline and smaller, the abbreviation's slot a little wider so the records still line up */
[data-view=condensed] .abbr-c{min-width:3.5em;margin-right:2px}
[data-view=condensed] .abbr-c .rk{font-size:.58em;margin-right:.12em}
/* a bowl's or title game's name, under the tile's TV */
.g-note{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10px;
  line-height:12px;color:var(--aag-text-3);margin-top:1px}
[data-view=condensed] .g-note{display:none}
"""


def badge(html_text, ranks):
    """The AP rank ahead of each ranked team's abbreviation (tiles, Teams on Bye)."""
    def sub(m):
        a = html.unescape(m.group(2))
        r = ranks.get(a)
        return f'{m.group(1)}<span class="rk">{r}</span>{m.group(2)}</span>' if r else m.group(0)
    return re.sub(r'(<span class="abbr(?: abbr-c)?"(?: aria-hidden="true")?>)([^<]+)</span>', sub, html_text)


def short_note(g):
    """A bowl's or title game's name for under its tile: "CFP Quarterfinal · Rose Bowl", "SEC Championship"."""
    note = (g.get("note") or "").strip()
    if not note:
        return ""
    rnd = g.get("playoff_round")
    if rnd:
        bowl = note if "Bowl" in note and "Playoff" not in note else ""
        return f"CFP {rnd}" + (f" · {bowl}" if bowl else "")
    return note


def notes(html_text, games):
    for g in games:
        n = short_note(g)
        if not n:
            continue
        pat = re.compile(r'(href="#game-' + re.escape(g["game_id"]) + r'".*?<div class="center">.*?)(</div>)', re.S)
        html_text = pat.sub(lambda m: f'{m.group(1)}<span class="g-note">{esc(n)}</span>{m.group(2)}', html_text, count=1)
    return html_text


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
.tr-note{font-size:12px;color:var(--aag-text-3);text-align:left;margin:2px 0 0}
.c-team>.c-trend-wrap{grid-row:4;align-self:start;width:100%;display:flex;flex-direction:column;align-items:center;gap:4px}
.c-trend{gap:2px;margin:2px 0}
.c-trend .tr-head{justify-content:center}
.c-trend .tr-lbl{font-size:10px}
.c-trend .tr-now{margin-left:0;font-size:14px}
.c-trend .tsvg{width:100%;height:auto;aspect-ratio:300/92;max-height:clamp(34px,6.2vh,56px)}
.c-trend .tr-note{display:none}   /* "AP NR" says it on the small card */
/* short phones (iPhone SE): the small card keeps "AP #4" and drops the chart, so the ranks still fit */
@media (max-height:640px){.c-trend .tsvg{display:none}}
/* conference + conference record, under the record */
.cf{display:flex;justify-content:center;align-items:baseline;gap:8px;font-size:13px;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;color:var(--aag-text-2);margin:-6px 0 14px}
.cf-r{font-weight:400;letter-spacing:.02em;color:var(--aag-text-3);font-variant-numeric:tabular-nums}
.cf-r::before{content:"·";margin-right:8px}
.c-team .cf{font-size:10px;gap:5px;margin:0}
.c-team .cf-r::before{margin-right:5px}
/* the team page's conference standings: places numbered, no ties column */
.ov-standings.cfb-st .st-row,.ov-standings.cfb-st .st-headrow{grid-template-columns:18px 22px minmax(0,1fr) 28px 28px 44px}
.cfb-st .st-pl{font-size:11px;font-weight:700;color:var(--aag-text-3);text-align:right}
.cfb-st .st-more{list-style:none;text-align:center;font-size:11px;color:var(--aag-text-3);letter-spacing:.1em;line-height:1}
"""


def trend_svg(pts, compact=False):
    """AP rank by poll week: 1 at the top, 25 at the bottom, a dashed "RV" lane under it for weeks in the
    receiving votes; unranked weeks leave a gap. compact (the condensed card): no labels, and the chart
    keeps its proportions (Jason, 2026-10-12) -- as tall as the card allows and only as wide as that calls
    for, so a narrow card shrinks it whole instead of squashing the weeks together."""
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
    return f'<svg class="tsvg" viewBox="0 0 {w} {h}" preserveAspectRatio="{fit}" aria-hidden="true">{grid}{lines}{dots}</svg>'


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
    label = f"AP rank {now_txt}" + (f", best #{best}" if best else "")
    if compact:
        return (f'<div class="apt c-trend" role="img" aria-label="{esc(label)}"><div class="tr-head"><span class="tr-lbl">AP</span>'
                f'<span class="tr-now">{now_txt}</span></div>{trend_svg(pts, True)}</div>')
    weeks = "".join(f"<span>{'Pre' if w == 1 else w}</span>" for w, _r in pts)
    sub = f"Best #{best}" if best else "Not ranked yet"
    return (f'<div class="apt" role="img" aria-label="{esc(label)}"><div class="tr-head"><span class="tr-lbl">AP Rank</span>'
            f'<span class="tr-sub">{sub}</span><span class="tr-now">{now_txt}</span></div>{trend_svg(pts)}'
            f'<div class="tr-weeks" aria-hidden="true">{weeks}</div></div>')


def conf_html(side, compact=False):
    """The conference and the record in conference games: "Big Ten · 3-0 conf" ("B1G · 3-0" condensed);
    an independent just "Independent"."""
    c = side.get("conf") or {}
    if not c.get("name"):
        return ""
    r = c.get("rec")
    rec = f'<span class="cf-r">{r["wins"]}-{r["losses"]}{"" if compact else " conf"}</span>' if r else ""
    return f'<div class="cf"><span class="cf-n">{esc(c["short"] if compact else c["name"])}</span>{rec}</div>'


def standings_block(standings, team, prefix="../"):
    """The team page's conference standings (a conference runs to 18 teams, a card fits about 8): the
    places around the team, numbered, W / L in conference games and the percentage."""
    from render_page1 import helmet_img
    if not standings or not standings.get("rows"):
        return ""
    rows = standings["rows"]
    i = next((k for k, r in enumerate(rows) if r["team"] == team), 0)
    lo = max(0, min(i - 3, len(rows) - 7))
    window = rows[lo:lo + 7]
    items = []
    if lo > 0:
        items.append('<li class="st-more" aria-hidden="true">···</li>')
    for k, r in enumerate(window, lo + 1):
        items.append(f'<li class="st-row{" is-you" if r["team"] == team else ""}"><span class="st-pl">{k}</span>'
                     f'{helmet_img(r["team"], 22, prefix=prefix)}<span class="st-team abbr">{esc(r["team"])}</span>'
                     f'<span class="st-w">{r["wins"]}</span><span class="st-l">{r["losses"]}</span>'
                     f'<span class="st-pct">{esc(tp._fmt_pct(r))}</span></li>')
    if lo + len(window) < len(rows):
        items.append('<li class="st-more" aria-hidden="true">···</li>')
    head = ('<div class="st-headrow" aria-hidden="true"><span></span><span></span><span></span>'
            '<span>W</span><span>L</span><span></span></div>')
    return (f'<div class="ov-standings cfb-st"><h3>{esc(standings["division"])} · Conference</h3>'
            f'{head}<ul class="st-list">{"".join(items)}</ul></div>')


# ---------------------------------------------------------------- Player Stats / Stat Leaders columns

def ncaa_rating(r):
    """The NCAA's passer efficiency rating: (8.4 yds + 330 TD + 100 comp - 200 INT) / att."""
    att = r["att"]
    if not att:
        return DASH
    return f'{(8.4 * r["pyds"] + 330 * r["ptd"] + 100 * r["cmp"] - 200 * r["int"]) / att:.1f}'


def college_columns():
    drop = {"1D", "NET"}

    def section(s):
        head, who, order, cols, medals = s
        cols = [(lbl, ncaa_rating if lbl == "RTG" else fn) for lbl, fn in cols if lbl not in drop]
        return (head, who, order, cols, medals)
    ps.CARDS = [(cid, title, [section(s) for s in secs], layout) for cid, title, secs, layout in ps.CARDS]
    rl.LINES = {k: [(lbl, fn) for lbl, fn in v if lbl not in drop] for k, v in rl.LINES.items()}


# ---------------------------------------------------------------- Rankings

RK_CSS = """
.rk-row{display:grid;grid-template-columns:20px 30px minmax(0,1fr) 34px 34px 74px;align-items:center;column-gap:4px;padding:0 4px;
  font-size:13px;font-variant-numeric:tabular-nums;border-bottom:1px solid var(--aag-tile-border-soft)}
.rk-row.end,.rk-row.head{border-bottom:0}
.rk-row.head{padding:0 4px 4px;font-size:10px;font-weight:700;letter-spacing:.04em;color:var(--text-3);align-items:end}
.rk-row.head .grp{grid-column:1/4}
.pc-long .rk-row:not(.head){padding-top:6px;padding-bottom:6px}
.rv .rk-row:not(.head){padding-top:5px;padding-bottom:5px}
.rk-n{font-size:13px;font-weight:700;text-align:right}
.mv{font-size:11px;font-weight:700;text-align:center;white-space:nowrap}
.mv.up{color:#1E8A3C}.mv.dn{color:#A00000}.mv.new{color:var(--text-2);font-size:9px;letter-spacing:.06em}.mv.eq{color:var(--text-3)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .mv.up{color:#4CC46F}:root:not([data-theme=light]) .mv.dn{color:#FF6B5E}}
:root[data-theme=dark] .mv.up{color:#4CC46F}:root[data-theme=dark] .mv.dn{color:#FF6B5E}
.pts{text-align:right;padding-right:4px}
.fpv{color:var(--text-3);font-size:11px;margin-left:3px}
.conf{color:var(--text-2);font-size:11px;font-weight:700;letter-spacing:.03em;text-align:center}
/* the school's full name (Jason, 2026-10-12): Inter, wrapping to a second line only for the longest */
.who .school{font-size:13px;font-weight:700;line-height:1.15;min-width:0;overflow-wrap:anywhere}
.drop{margin-top:16px;font-size:12px;color:var(--text-2);line-height:1.5;padding:0 4px}
.drop b{font-size:11px;letter-spacing:.06em;text-transform:uppercase;margin-right:6px}
.drop .school{font-weight:700;color:var(--text)}
.empty-poll{padding:24px 8px;text-align:center;color:var(--text-3);font-size:13px}
/* CFP, before its first rankings */
.soon{display:flex;flex-direction:column;align-items:center;text-align:center;gap:6px;padding:28px 8px 0}
.soon h2{font-size:15px;font-weight:900;letter-spacing:.1em;text-transform:uppercase}
.soon .lead{font-size:14px;color:var(--text-2);max-width:30em;line-height:1.4}
.soon .big{font-size:28px;font-weight:900;margin:6px 0 2px}
.soon .sub{font-size:12px;color:var(--text-3)}
.soon ol{list-style:none;margin:18px 0 0;padding:0;width:100%;max-width:300px}
.soon li{display:flex;justify-content:space-between;padding:7px 4px;border-bottom:1px solid var(--aag-tile-border-soft);
  font-size:13px;font-variant-numeric:tabular-nums}
.soon li:last-child{border-bottom:0}
.soon li span:first-child{color:var(--text-2)}
.soon li.sel span:last-child{font-weight:700}
"""


def _rec(r):
    r = r or {}
    return f'{r.get("wins", 0)}-{r.get("losses", 0)}' + (f'-{r["ties"]}' if r.get("ties") else "")


def rankings_page(data):
    """Rankings (Jason, 2026-10-12), Standings' layout: AP Poll | Coaches Poll | CFP, each a deck of the
    Top 25 (rank, change from last week, school, record, conference, points with first-place votes) |
    Receiving Votes (and the teams that dropped out of the votes entirely) | Key."""
    season = data.get("season") or ""
    rk = data.get("rankings") or {}
    views = [("ap", "AP Poll", rk.get("ap")), ("coaches", "Coaches Poll", rk.get("coaches")), ("cfp", "CFP", rk.get("cfp"))]

    def who(t):
        return (f'<span class="who">{p1.helmet_img(t["team"], rs.HELMET, prefix="")}'
                f'<span class="school">{esc(t.get("school") or t["team"])}</span></span>')

    def move(t):
        cur, prev = t.get("current"), t.get("previous")
        if not prev:
            return '<span class="mv new">NEW</span>'
        d = prev - cur
        return (f'<span class="mv up">▲{d}</span>' if d > 0 else f'<span class="mv dn">▼{-d}</span>' if d < 0
                else '<span class="mv eq">–</span>')

    def row(t, i, n, rv=False, show_move=True):
        fpv = t.get("first_place_votes") or 0
        pts = f'{int(t.get("points") or 0):,}' + (f'<span class="fpv">({fpv})</span>' if fpv else "")
        if rv:
            mv = '<span class="mv dn">▼</span>' if t.get("previous") else "<span></span>"
        else:
            mv = move(t) if show_move else "<span></span>"
        return (f'<div class="rk-row{" end" if i == n else ""}"><span class="rk-n">{"" if rv else t.get("current") or ""}</span>{mv}'
                f'{who(t)}<span class="n">{_rec(t.get("record"))}</span><span class="conf">{esc(t.get("conf") or "")}</span>'
                f'<span class="pts">{pts if t.get("points") else ""}</span></div>')

    def head(label, pts=True):
        return (f'<div class="rk-row head"><span class="grp">{label}</span>'
                f'<span class="n">REC</span><span class="n">CONF</span><span class="pts">{"PTS" if pts else ""}</span></div>')

    def key_card(prev, cfp=False):
        rows = ([("▲ ▼", "Places up or down from last week's rankings"), ("NEW", "Not ranked last week")]
                + [("REC", "Record this season"), ("CONF", "Conference")]
                + ([] if cfp else [("PTS", "Poll points: 25 for a first-place vote down to 1 for 25th; first-place votes in ( )")]))
        dl = "".join(f"<div><dt>{a}</dt><dd>{esc(b)}</dd></div>" for a, b in rows)
        note = ("" if cfp else '<p class="note">Receiving Votes: teams outside the 25 that still got points, most first. '
                '▼ = ranked last week.</p>')
        return f'<article class="pc pc-key">{rs._peek(prev, up=True)}<footer class="legend"><h3>Key</h3><dl>{dl}</dl>{note}</footer></article>'

    def deck(k, p):
        ranks, others = p.get("ranks") or [], p.get("others") or []
        if not ranks:
            return f'<article class="pc"><p class="empty-poll">No {esc(p.get("name") or "poll")} yet</p></article>'
        cfp = k == "cfp"
        top = "".join(row(t, i, len(ranks), show_move=True) for i, t in enumerate(ranks, 1))
        first = (f'<article class="pc pc-long"><div class="pc-body"><section class="grp-box">{head("Top 25", not cfp)}{top}</section></div>'
                 f'{rs._peek("Key" if cfp or not others else "Receiving Votes")}</article>')
        if cfp or not others:
            return first + key_card("Top 25", cfp)
        rv = "".join(row(t, i, len(others), rv=True) for i, t in enumerate(others, 1))
        in_rv = {t["team"] for t in others}
        dropped = [t for t in p.get("dropped") or [] if t["team"] not in in_rv]
        drop = ("<p class='drop'><b>Dropped out</b>" + ", ".join(
            f'<span class="school">{esc(t.get("school") or t["team"])}</span> ({t.get("previous")})' for t in dropped) + "</p>") if dropped else ""
        return (first + f'<article class="pc">{rs._peek("Top 25", up=True)}<div class="pc-body"><section class="grp-box rv">'
                f'{head("Receiving votes")}{rv}</section>{drop}</div>{rs._peek("Key")}</article>' + key_card("Receiving Votes"))

    def soon():
        dates = CFP_DATES.get(season)
        if not dates:
            return ('<article class="pc"><div class="soon"><h2>College Football Playoff</h2>'
                    '<p class="lead">The selection committee\'s rankings start in November</p></div></article>')
        (d0, first), rest = dates[0], dates[1:]
        lis = "".join(f'<li{" class=sel" if i == len(rest) - 1 else ""}><span>{"Selection Day" if i == len(rest) - 1 else "Update"}</span>'
                      f'<span>{day[:3]}, {d}</span></li>' for i, (day, d) in enumerate(rest))
        sel = rest[-1] if rest else dates[0]
        return ('<article class="pc"><div class="soon"><h2>College Football Playoff</h2>'
                "<p class='lead'>The selection committee's first Top 25 comes out</p>"
                f'<p class="big">{d0}, {first}</p><p class="sub">on ESPN · the 12-team field is set {sel[0]}, {sel[1]}</p>'
                f'<ol>{lis}</ol></div></article>')

    tabs = "".join(f'<button class="sw-tab{" on" if i == 0 else ""}" type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" '
                   f'data-view="{k}">{label}</button>' for i, (k, label, _p) in enumerate(views))
    panes = "".join(f'<section class="pane" data-pane="{k}" role="tabpanel" aria-label="{label}"><div class="pane-in">'
                    f'{deck(k, p) if p else soon() if k == "cfp" else deck(k, {})}</div></section>' for k, label, p in views)
    week = (rk.get("ap") or {}).get("week")
    sub = "Preseason" if week == 1 else f"Week {week}" if week else ""
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        "<meta name='theme-color' content='#F3F3EE'>"
        f"<script>{theme.THEME_HEAD_JS}</script><title>{esc(season)} Rankings · At A Glance</title>"
        "<meta name='description' content='CFB Top 25 Rankings'>"
        f"{logo.favicon_links()}"
        "<link rel='preconnect' href='https://fonts.googleapis.com'><link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
        f"<style>{theme.THEME_CSS}{theme.MENU_CSS}{theme.HELMET_SHADOW_CSS}{rs.CSS}{RK_CSS}</style></head><body>"
        f"<header class='top'><div class='top-in'><h1 class='title'><span class='yr abbr'>{esc(season)}</span>"
        f"<span class='rs-line'><span class='rs'>Rankings</span><span class='thru'>{esc(sub)}</span></span></h1>"
        f"<div class='sw' role='tablist' aria-label='Poll'>{tabs}</div></div></header>"
        f"<main class='track' id='track'>{panes}</main>"
        "<nav class='bottombar' aria-label='Page controls'><div class='bar-in'>"
        f"{theme.menu_html('', 'standings')}{rs._back(data)}"
        "</div></nav>"
        f"<script>{theme.THEME_JS}</script><script>{rs.JS}</script></body></html>"
    )


# ---------------------------------------------------------------- pointing the NFL pages at college

MENU_KEYS = {"games": "cfb-games", "standings": "cfb-rankings", "leaders": "cfb-leaders"}


def setup(data, site_dir):
    teams = data.get("teams") or {}
    n = data.get("n_fbs") or 138
    week_ranks = {w["key"]: w.get("ranks") or {} for w in data.get("season_weeks") or []}
    week_teams = {w["key"]: set(w.get("tracked") or []) for w in data.get("season_weeks") or []}

    # helmets, pills and chart lines in each school's colors (team_line_colors picks the chart lines from the
    # pill's fill and ring, then the helmet's three)
    write_helmets(teams, site_dir)
    helmets.helmet_filename = helmet_filename
    for a, t in teams.items():
        if t.get("color") or cfb_helmet_colors.HELMET_COLORS.get(t.get("id")):
            shell, mask, ear = team_colors(t)
            helmets.TEAM_COLORS[a] = (shell, mask)
            helmets.EAR_COLORS[a] = ear
            helmets.PILL_COLORS[a] = pill_colors(t)
            helmets.SHADING_OVERRIDES.pop(a, None)
    # names
    for a, t in teams.items():
        rh.TEAM_NAMES[a] = p1.TEAM_NAMES[a] = tp.LOCATION_NAMES[a] = t.get("school") or a
    rl.DIVISIONS = {a: None for a in data.get("player_weeks") or {}}

    # the menu and the favicons, one folder deeper than the NFL's pages
    menu_html, favicons = theme.menu_html, logo.favicon_links
    theme.menu_html = lambda prefix="", current=None: menu_html("../" + prefix, MENU_KEYS.get(current, current))
    logo.favicon_links = lambda prefix="": favicons("../" + prefix)

    # Page 0: poll teams on bye, the ranks on the tiles, bowl names
    rh.bye_teams = lambda games: sorted(next((week_teams[k] for k, gs in week_games.items() if gs is games), set())
                                        - {(m.get(s) or {}).get("team") for m in games for s in ("away", "home")})
    week_games = {w["key"]: w["games"] for w in data.get("season_weeks") or []}
    panel = rh.render_week_panel
    rh.render_week_panel = lambda key, label, games, cur, byes=None: notes(
        badge(panel(key, label, games, cur, byes), week_ranks.get(key, {})), games)

    # Page 1: the team cards, the ranks' scale, the top bar's ranks, neutral sites, icons
    c_team, l_team, p1_block = p1.c_team, p1.l_team, p1.render_p1_block

    def c_team2(side, label, final=False):
        body = f'<div class="c-trend-wrap">{conf_html(side, True)}{trend_html(side, compact=True)}</div>'
        return re.sub(r'<ul class="injuries c-inj">.*?</ul>', lambda _m: body, c_team(side, label, final), count=1, flags=re.S)

    def l_team2(side, final=False):
        return re.sub(r'<ul class="l-inj">.*?</ul>', lambda _m: conf_html(side) + trend_html(side), l_team(side, final), count=1, flags=re.S)

    def block(d, prefix="../"):
        out = p1_block(d, prefix)
        ranks = {(d.get(s) or {}).get("team"): (d.get(s) or {}).get("rank") for s in ("away", "home")}
        out = re.sub(r'(<div class="side (?:away|home)">(?:(?!</div>).)*?<span class="abbr">)([^<]+)</span>',
                     lambda m: f'{m.group(1)}<span class="rk">{ranks[html.unescape(m.group(2))]}</span>{m.group(2)}</span>'
                     if ranks.get(html.unescape(m.group(2))) else m.group(0), out, flags=re.S)
        if d.get("neutral"):
            out = out.replace('<span class="at">@</span>', '<span class="at">vs</span>')
            out = out.replace('</span> @ <span class="abbr">', '</span> vs <span class="abbr">')
        return out

    def rank_color(k):
        """The NFL's 32-step green-to-red scale stretched over the FBS teams."""
        i = round((max(1, min(n, k)) - 1) * 31 / max(1, n - 1))
        return p1.RANK_COLORS[i]
    standalone = p1.render_standalone

    def page(d):
        out = standalone(d)
        if d.get("neutral"):   # the tab's title too: "UNC vs TCU"
            a, h = (d.get("away") or {}).get("team"), (d.get("home") or {}).get("team")
            out = out.replace(f"<title>{esc(a)} @ {esc(h)} ", f"<title>{esc(a)} vs {esc(h)} ", 1)
        return out
    p1.c_team, p1.l_team, p1.render_p1_block, p1.rank_color = c_team2, l_team2, block, rank_color
    p1.render_standalone = page
    p1.P1_CSS += TREND_CSS + BADGE_CSS
    p1.NAV_ICONS["game-info"] = cfb_icons.ICONS["game-info"]
    ps.PS_ICONS.update({k: cfb_icons.ICONS[k] for k in ("passing", "receiving", "kicking")})
    tp.TEAM_ICONS.update({k: cfb_icons.ICONS[k] for k in ("overview", "schedule")})
    tp.SKIP_CARDS = {"injuries"}
    tp._standings_block = standings_block
    college_columns()
    matchup.EDGE_GAP = round(8 / 32 * n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DATA_PATH)
    args = ap.parse_args()
    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    # last build's game pages go, so a game that left the pages doesn't linger (the rest is overwritten)
    game_dir = os.path.join(SITE_DIR, "game")
    for name in os.listdir(game_dir) if os.path.isdir(game_dir) else []:
        if name.endswith(".html"):
            try:
                os.remove(os.path.join(game_dir, name))
            except OSError:
                pass
    os.makedirs(SITE_DIR, exist_ok=True)
    setup(data, SITE_DIR)
    warnings = list(data.get("warnings") or [])

    page0 = rh.render_page0(data)
    page0 = page0.replace("</style>", BADGE_CSS + "</style>", 1).replace("Pro Football Upcoming Game Information",
                                                                         "CFB Top 25 Game Information")
    # no condensed view for a week whose rows would come out smaller than Week 11's on an iPhone (Jason,
    # 2026-10-12: 24 games, rows 26px tall at 390 x 844) -- render_html.PAGE0_JS measures it on the screen
    page0 = page0.replace("<main class='track' id='track' data-sticky-days", f"<main class='track' id='track' data-min-tile='{MIN_TILE}' data-sticky-days", 1)
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(page0)
    count = p1.write_all(data, SITE_DIR, warnings, matchup_weeks=data.get("matchup_weeks") or {})
    with open(os.path.join(SITE_DIR, "rankings.html"), "w", encoding="utf-8") as f:
        f.write(rankings_page(data))
    leaders = rl.render(data).replace("Pro Football Stat Leaders", "CFB Top 25 Stat Leaders")
    with open(os.path.join(SITE_DIR, "leaders.html"), "w", encoding="utf-8") as f:
        f.write(leaders)
    if os.path.isfile(SNAP_PATH):
        shutil.copy(SNAP_PATH, os.path.join(SITE_DIR, "cfb-snapshot.json"))
    print(f"render_cfb: {count} game pages, Page 0 ({len(data.get('season_weeks') or [])} weeks), rankings, leaders "
          f"-> {SITE_DIR}")
    for w in warnings[-10:]:
        print("  warning:", str(w).strip().splitlines()[-1][:300])


if __name__ == "__main__":
    main()

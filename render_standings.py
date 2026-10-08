"""
Standings -- site/standings.html (Jason, 2026-10-07; picked as "D" in mockups/build_standings_mockup.py,
then made into full-screen cards in mockups/build_standings_cards_mockup.py).

A page of its own, outside Page 0 / 1 / 2: reached from the bottom bar's menu (theme.menu_html)
on every page, and from the division title on a team page's Overview card (render_page2team).

  - title: the year (Saira italic, like the team abbreviations) over one line reading "REGULAR
    SEASON · Through Week N" -- the last week with a finished game (Jason, 2026-10-07; they were
    two lines)
  - the title and the buttons stay put at the top; the page itself never scrolls, only the cards
    under the header do
  - three buttons, styled like Player Stats' team switch (the chosen one full strength, the others
    faded): Division / Conference / League. Swiping left / right moves between them too -- the three
    sit side by side and snap, like Page 0's weeks (Jason, 2026-10-07). The choice is in the URL
    (#division, #conference, #league) so it can be linked; #afc-east etc. opens Division at that
    division's card
  - each view is a stack of cards that fill the screen between the header and the bottom bar, and
    snap one at a time swiping up / down, like Page 1's card deck (Jason, 2026-10-07):
      Division   -- AFC (East / North / South / West, each titled on its column-heads line) | NFC | key
      Conference -- AFC seeds 1-16 | NFC 1-16 | key. Division leaders take 1-4, the rest from 5;
                    "Div. leaders" sits on the column-heads line, then "Wild card" over 5-7 and
                    "In the hunt" over 8-16
      League     -- 1-32 in one card that scrolls freely (it's taller than the screen; snapping here
                    is loose, only pulling in near the key) | key
    On Division and Conference the teams spread out to fill the card, whatever the phone's height.
    AFC / NFC are centered at the top of their card. A small "^ AFC" at the top of a card and
    "v NFC" at the bottom name the cards above and below, like Page 1's card slivers.
  - every team is one row: [seed] clinch mark, helmet (18px) + abbreviation, then W, L, T, PCT, DIV,
    CONF, STRK. The team column is only as wide as it needs to be and the stat columns share the
    rest, every value centered under its heading
  - thin lines between teams, none under the last team of a group or a section
  - the key: the columns, then the clinch marks
  - bottom bar: the menu in the left corner, "< Week N" back to Page 0 in the middle

Order is win pct, then conference pct, then division pct, then wins -- NOT the NFL's real
tiebreakers (head-to-head, common games, strength of victory...), which are out of scope here,
the same simplification as the team pages' division table (page1_data._standings_for).

Clinch marks use the NFL's letters (x playoff berth, y division, z first-round bye, * home field
throughout). Nothing in nflverse says who has clinched, so they're kept by hand in CLINCHED below
once that starts mattering in December.

Data: data/matchups.json -> "season_weeks" (every regular-season game with its final score, built
in build_data.py for Page 0), so nothing new is fetched for this page.
"""

import html
import os

import logo
import theme
from divisions import DIVISIONS, normalize_abbr
from render_page1 import CHEV, DOWN, UP, helmet_img

CONFS = ("AFC", "NFC")
DIV_NAMES = ("East", "North", "South", "West")
VIEWS = ("division", "conference", "league")

# Hand-kept clinch marks: team -> "x" | "y" | "z" | "*". Empty until someone clinches.
CLINCHED = {}

LEGEND = (
    ("W", "Wins"), ("L", "Losses"), ("T", "Ties"), ("PCT", "Win percentage, ties count as half a win"),
    ("DIV", "Record against division opponents"), ("CONF", "Record against conference opponents"),
    ("STRK", "Current streak: W3 = three wins in a row"),
)
CLINCH_KEY = (("x", "Clinched a playoff berth"), ("y", "Clinched the division"),
              ("z", "Clinched a first-round bye"), ("*", "Clinched the division and home field throughout the playoffs"))
HEADS = ("W", "L", "T", "PCT", "DIV", "CONF", "STRK")
HELMET = 18


def esc(v):
    return html.escape(str(v), quote=True)


# ---------------------------------------------------------------- data

def _pct(w, l, t):
    gp = w + l + t
    return (w + 0.5 * t) / gp if gp else 0.0


def build(season_weeks):
    """(rows, through_week): one row per team from every finished regular-season game."""
    games = [g for wk in season_weeks or [] if wk.get("game_type") == "REG"
             for g in wk.get("games") or [] if g.get("final")]
    games.sort(key=lambda g: (str(g.get("gameday") or ""), str(g.get("gametime") or ""), str(g.get("game_id") or "")))
    rec = {t: {"w": 0, "l": 0, "t": 0, "dw": 0, "dl": 0, "dt": 0, "cw": 0, "cl": 0, "ct": 0, "results": []}
           for t in DIVISIONS}
    through = 0
    for g in games:
        a, h = normalize_abbr((g.get("away") or {}).get("team")), normalize_abbr((g.get("home") or {}).get("team"))
        sa, sh = (g.get("away") or {}).get("score"), (g.get("home") or {}).get("score")
        if a not in rec or h not in rec or sa is None or sh is None:
            continue
        through = max(through, int(g.get("week") or 0))
        for me, opp, mine, theirs in ((a, h, sa, sh), (h, a, sh, sa)):
            r = rec[me]
            res = "w" if mine > theirs else "l" if mine < theirs else "t"
            r[res] += 1
            r["results"].append(res.upper())
            if DIVISIONS[me] == DIVISIONS[opp]:
                r["d" + res] += 1
            if DIVISIONS[me][:3] == DIVISIONS[opp][:3]:
                r["c" + res] += 1
    rows = []
    for team, r in rec.items():
        streak = ""
        if r["results"]:
            last, n = r["results"][-1], 0
            for x in reversed(r["results"]):
                if x != last:
                    break
                n += 1
            streak = f"{last}{n}"
        rows.append({"team": team, "div": DIVISIONS[team], "conf": DIVISIONS[team][:3], "streak": streak,
                     "pct": _pct(r["w"], r["l"], r["t"]), "cpct": _pct(r["cw"], r["cl"], r["ct"]),
                     "dpct": _pct(r["dw"], r["dl"], r["dt"]),
                     **{k: v for k, v in r.items() if k != "results"}})
    return rows, through


def order(rows):
    return sorted(rows, key=lambda r: (-r["pct"], -r["cpct"], -r["dpct"], -r["w"], r["team"]))


def seeds(rows, conf):
    """Division leaders take 1-4, everyone else from 5 down."""
    mine = [r for r in rows if r["conf"] == conf]
    leaders = [order([r for r in mine if r["div"] == f"{conf} {d}"])[0] for d in DIV_NAMES]
    return order(leaders) + order([r for r in mine if r not in leaders])


# ---------------------------------------------------------------- markup

def _fmt_pct(r):
    p = r["pct"]
    if not r["w"] + r["l"] + r["t"]:
        return ".000"
    return f"{p:.3f}".lstrip("0") if p < 1 else "1.000"


def _rec(w, l, t):
    return f"{w}-{l}-{t}" if t else f"{w}-{l}"


def _row(r, seed=None, end=False):
    mark = CLINCHED.get(r["team"], "")
    lead = f'<span class="seed">{seed}</span>' if seed is not None else ""
    return (
        f'<div class="row{" end" if end else ""}">{lead}'
        f'<span class="who"><span class="mk">{esc(mark)}</span>{helmet_img(r["team"], HELMET, prefix="")}'
        f'<span class="abbr">{esc(r["team"])}</span></span>'
        f'<span class="n">{r["w"]}</span><span class="n">{r["l"]}</span><span class="n">{r["t"]}</span>'
        f'<span class="n">{_fmt_pct(r)}</span>'
        f'<span class="n sub">{_rec(r["dw"], r["dl"], r["dt"])}</span>'
        f'<span class="n sub">{_rec(r["cw"], r["cl"], r["ct"])}</span>'
        f'<span class="n">{esc(r["streak"]) or "—"}</span></div>'
    )


def _group(label, rows, seeded=False, bands=None, gid=None):
    """One table. bands = {position: label} for the section names inside it; a band at 1 goes on
    the column-heads line in place of label. --n (its team count) gives it its share of a card."""
    bands = dict(bands or {})
    label = bands.pop(1, label)
    lead = "<span></span>" if seeded else ""
    head = (f'<div class="row head">{lead}<span class="grp">{esc(label)}</span>'
            + "".join(f'<span class="n">{h}</span>' for h in HEADS) + "</div>")
    body = []
    for i, r in enumerate(rows, 1):
        if i in bands:
            body.append(f'<div class="band">{esc(bands[i])}</div>')
        body.append(_row(r, seed=i if seeded else None, end=(i == len(rows) or (i + 1) in bands)))
    gid_attr = f' id="{gid}"' if gid else ""
    return (f'<section class="grp-box{" seeded" if seeded else ""}"{gid_attr} style="--n:{len(rows)}">'
            f'{head}{"".join(body)}</section>')


def _peek(label, up=False):
    """The name of the card above (^) or below (v), like Page 1's card slivers."""
    if not label:
        return ""
    return f'<div class="peek {"prev" if up else "next"}">{UP if up else DOWN}<span>{esc(label)}</span></div>'


def _card(title, body, prev=None, nxt=None, long=False):
    t = f'<h2 class="conf-h">{esc(title)}</h2>' if title else ""
    return (f'<article class="pc{" pc-long" if long else ""}">{_peek(prev, up=True)}{t}'
            f'<div class="pc-body">{body}</div>{_peek(nxt)}</article>')


def _key_card(prev):
    cols = "".join(f'<div><dt>{k}</dt><dd>{esc(v)}</dd></div>' for k, v in LEGEND)
    marks = "".join(f'<div><dt class="mkk">{k}</dt><dd>{esc(v)}</dd></div>' for k, v in CLINCH_KEY)
    return (f'<article class="pc pc-key">{_peek(prev, up=True)}'
            f'<footer class="legend"><h3>Key</h3><dl>{cols}</dl><h3>Clinched</h3><dl>{marks}</dl>'
            '<p class="note">Seeds 1–4 go to the division winners; 5–7 are the wild cards.</p></footer></article>')


def _division(rows):
    return "".join(
        _card(c, "".join(_group(d, order([r for r in rows if r["div"] == f"{c} {d}"]),
                                gid=f"{c} {d}".lower().replace(" ", "-")) for d in DIV_NAMES),
              prev=None if c == "AFC" else "AFC", nxt="NFC" if c == "AFC" else "Key")
        for c in CONFS) + _key_card("NFC")


def _conference(rows):
    return "".join(
        _card(c, _group("", seeds(rows, c), seeded=True,
                        bands={1: "Div. leaders", 5: "Wild card", 8: "In the hunt"}),
              prev=None if c == "AFC" else "AFC", nxt="NFC" if c == "AFC" else "Key")
        for c in CONFS) + _key_card("NFC")


def _league(rows):
    return _card("", _group("", order(rows), seeded=True), nxt="Key", long=True) + _key_card("League")


def _back(data):
    """"< Week N" back to Page 0's current week (the same week Page 0 opens on)."""
    key = data.get("current_week_key")
    weeks = data.get("season_weeks") or []
    label = next((w.get("label") for w in weeks if w.get("key") == key), None)
    href = f"index.html#week-{key}" if key else "index.html"
    return f'<a class="week" href="{esc(href)}">{CHEV}<span>{esc(label or "Games")}</span></a>'


def render(data):
    season = data.get("season") or ""
    rows, through = build(data.get("season_weeks"))
    thru = f"Through Week {through}" if through else "No games played yet"
    tabs = "".join(
        f'<button class="sw-tab{" on" if v == "division" else ""}" type="button" role="tab" '
        f'aria-selected="{"true" if v == "division" else "false"}" data-view="{v}">{v.title()}</button>'
        for v in VIEWS)
    panes = "".join(f'<section class="pane" data-pane="{v}" role="tabpanel" aria-label="{v.title()}">'
                    f'<div class="pane-in">{body}</div></section>'
                    for v, body in (("division", _division(rows)), ("conference", _conference(rows)),
                                    ("league", _league(rows))))
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        "<meta name='theme-color' content='#F3F3EE'>"
        f"<script>{theme.THEME_HEAD_JS}</script>"
        f"<title>{esc(season)} Standings · At A Glance</title>"
        "<meta name='description' content='Pro Football Standings'>"
        f"{logo.favicon_links()}"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
        f"<style>{theme.THEME_CSS}{theme.MENU_CSS}{theme.HELMET_SHADOW_CSS}{CSS}</style></head><body>"
        f"<header class='top'><div class='top-in'><h1 class='title'><span class='yr abbr'>{esc(season)}</span>"
        f"<span class='rs-line'><span class='rs'>Regular Season</span><span class='thru'>{esc(thru)}</span></span></h1>"
        f"<div class='sw' role='tablist' aria-label='Standings by'>{tabs}</div></div></header>"
        f"<main class='track' id='track'>{panes}</main>"
        "<nav class='bottombar' aria-label='Page controls'><div class='bar-in'>"
        f"{theme.menu_html('', 'standings')}{_back(data)}"
        "</div></nav>"
        f"<script>{theme.THEME_JS}</script><script>{JS}</script>"
        "</body></html>"
    )


def write(data, site_dir):
    path = os.path.join(site_dir, "standings.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(data))
    return path


CSS = """
:root{--bbar:""" + theme.BBAR_HEIGHT + """;--text:var(--aag-text);--text-2:var(--aag-text-2);--text-3:var(--aag-text-3);
  --team-w:74px}
*{box-sizing:border-box;margin:0;padding:0}
/* the page itself never scrolls -- each view scrolls inside the track, under the header */
html,body{height:100%;overflow:hidden;background:var(--aag-bg)}
body{color:var(--text);font-family:Inter,system-ui,-apple-system,sans-serif;font-weight:400;-webkit-font-smoothing:antialiased}
.abbr{line-height:1;font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;font-style:italic;
  font-variation-settings:'wdth' 95;letter-spacing:.02em}

/* title: the year over "REGULAR SEASON · Through Week N", then the buttons */
.top{position:relative;z-index:5;background:var(--aag-bar-bg)}
.top-in{max-width:600px;margin:0 auto;display:flex;flex-direction:column;align-items:center;gap:6px;
  padding:max(12px,env(safe-area-inset-top)) 16px 10px}
.title{display:flex;flex-direction:column;align-items:center;gap:2px;font-weight:700}
.yr{font-size:36px}
.rs{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--text-2)}
.thru{font-size:11px;font-weight:400;color:var(--text-3)}
.rs-line{display:flex;align-items:baseline;gap:6px;white-space:nowrap}
.thru::before{content:"·";margin-right:6px;color:var(--text-3)}
/* Division / Conference / League -- like Player Stats' team switch: the chosen one at full
   strength in a pill outline, the others faded */
.sw{display:flex;justify-content:center;gap:4px;margin-top:4px}
.sw-tab{font:inherit;font-size:14px;font-weight:700;color:var(--text);background:none;border:1px solid transparent;
  border-radius:999px;padding:5px 13px;cursor:pointer;opacity:.45;transition:opacity .16s;-webkit-tap-highlight-color:transparent}
.sw-tab.on{opacity:1;border-color:var(--aag-tile-border)}
.sw-tab:hover{opacity:.8}
.sw-tab.on:hover{opacity:1}
.sw-tab:focus-visible{outline:2px solid var(--aag-focus);outline-offset:2px}

/* the three views side by side, filling the screen between the header (--top-h, set by JS) and the
   bottom bar; swipe (or a button) snaps between them, like Page 0's weeks */
.track{display:flex;height:calc(100vh - var(--top-h,112px) - var(--bbar));height:calc(100dvh - var(--top-h,112px) - var(--bbar));
  overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;overscroll-behavior-x:contain;
  scrollbar-width:none;-webkit-overflow-scrolling:touch}
.track::-webkit-scrollbar{display:none}
/* each view scrolls up / down on its own and snaps card by card, like Page 1's deck */
.pane{flex:0 0 100%;min-width:0;height:100%;scroll-snap-align:start;scroll-snap-stop:always;
  overflow-y:auto;overscroll-behavior-y:contain;scroll-snap-type:y mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.pane::-webkit-scrollbar{display:none}
.pane-in{max-width:600px;height:100%;margin:0 auto;padding:0 16px}

/* a card: the whole height of the view, the teams spreading out to fill it */
.pc{height:100%;scroll-snap-align:start;scroll-snap-stop:always;display:flex;flex-direction:column;
  padding:8px 0 6px;overflow:hidden}
.pc-body{flex:1 1 0;min-height:0;display:flex;flex-direction:column}
.grp-box{flex:var(--n) 1 0;min-height:0;display:flex;flex-direction:column;margin-top:10px}
.grp-box:first-child{margin-top:8px}
.pc .row:not(.head){flex:1 1 0;min-height:0}
.row.head,.band{flex:none}
/* League: one card as tall as its 32 teams, scrolling freely -- the view only snaps near the key */
.pane[data-pane=league]{scroll-snap-type:y proximity}
.pc.pc-long{height:auto;min-height:100%;overflow:visible;scroll-snap-stop:normal}
.pc-long .pc-body,.pc-long .grp-box{flex:none}
.pc-long .row:not(.head){flex:none;padding-top:5px;padding-bottom:5px}

/* AFC / NFC, centered at the top of their card */
.conf-h{flex:none;margin-top:4px;text-align:center;font-size:15px;font-weight:900;letter-spacing:.1em}
/* the cards above (^) and below (v), named like Page 1's card slivers */
.peek{flex:none;display:flex;align-items:center;justify-content:center;gap:6px;font-size:11px;
  font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3)}
.peek.next{padding-top:6px}
.peek.prev{padding-bottom:2px}
.pc-key .peek.prev{padding-bottom:14px}

/* one line per team: [seed] team W L T PCT DIV CONF STRK. The team column is only as wide as mark +
   helmet + abbreviation; the stat columns share the rest (PCT / DIV / CONF a little wider), every
   value centered under its heading */
.row{display:grid;grid-template-columns:var(--team-w) repeat(3,minmax(0,.8fr)) minmax(0,1.25fr) repeat(2,minmax(0,1.15fr)) minmax(0,1fr);
  align-items:center;column-gap:4px;padding:0 4px;font-size:13px;font-variant-numeric:tabular-nums;
  border-bottom:1px solid var(--aag-tile-border-soft)}
.seeded .row{grid-template-columns:16px var(--team-w) repeat(3,minmax(0,.8fr)) minmax(0,1.25fr) repeat(2,minmax(0,1.15fr)) minmax(0,1fr)}
/* no line under the last team of a group or a section */
.row.end,.row.head{border-bottom:0}
.row.head{align-items:end;padding:0 4px 4px;font-size:10px;font-weight:700;letter-spacing:.04em;color:var(--text-3)}
.grp,.band{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2);white-space:nowrap}
.seeded .row.head .grp{grid-column:1/3;white-space:normal;line-height:1.15}
.seeded .row.head>span:first-child{display:none}
.band{padding:10px 4px 2px}
.n{text-align:center}
.sub{color:var(--text-2);font-size:12px}
.who{display:flex;align-items:center;gap:5px;min-width:0}
.who img{width:""" + str(HELMET) + """px;height:""" + str(HELMET) + """px;flex:none;--hs:""" + str(HELMET) + """px}
.who .abbr{font-size:14px}
.seed{font-size:11px;font-weight:700;color:var(--text-3);text-align:right}
/* the clinch letter, in a slot of its own so the helmets line up */
.mk{display:inline-block;width:8px;flex:none;text-align:center;font-size:11px;font-weight:700;color:var(--text-2)}

/* the key */
.legend h3{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-2);margin:0 0 6px}
.legend dl{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px;margin-bottom:14px}
.legend dl>div{display:flex;gap:8px;font-size:12px;align-items:baseline}
.legend dt{flex:none;width:34px;font-weight:700;font-size:11px}
.legend dt.mkk{width:14px;text-align:center;font-size:13px}
.legend dd{color:var(--text-2)}
.legend .note{font-size:11px;color:var(--text-3)}
@media (max-width:420px){.legend dl{grid-template-columns:1fr}}
/* narrow phones (iPhone SE 1st gen): tighter columns, no helmets */
@media (max-width:359px){
  :root{--team-w:48px}
  .row,.seeded .row{column-gap:2px;font-size:12px}
  .seeded .row{grid-template-columns:13px var(--team-w) repeat(3,minmax(0,.8fr)) minmax(0,1.25fr) repeat(2,minmax(0,1.15fr)) minmax(0,1fr)}
  .grp,.band{letter-spacing:.02em}
  .row.head{font-size:9px;letter-spacing:0}
  .who img{display:none}
}
/* short phones (iPhone SE 1st gen): sixteen teams squeezed into one screen would be too tight, so a
   card keeps the usual row height and runs a little taller than the screen, scrolling freely like
   League's */
@media (max-height:600px){
  .pc{height:auto;min-height:100%;overflow:visible}
  .pc-body,.grp-box{flex:none}
  .pc .row:not(.head){flex:none;padding-top:4px;padding-bottom:4px}
}

/* bottom bar: the menu on the left, "< Week N" back to Page 0 in the middle -- Page 0's bar */
.bottombar{position:fixed;left:0;right:0;bottom:0;z-index:10;height:var(--bbar);padding-bottom:env(safe-area-inset-bottom);
  background:var(--aag-bar-bg);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.bar-in{position:relative;max-width:600px;height:52px;margin:0 auto;display:flex;align-items:flex-start;justify-content:center;padding-top:10px}
.week{color:inherit;text-decoration:none;display:inline-flex;align-items:center;gap:6px;font-size:16px;line-height:19px;
  padding:6px 12px;border-radius:999px;transition:background-color .16s}
.week:hover{background:var(--aag-pill-hover)}
.week:focus-visible{outline:2px solid var(--aag-focus);outline-offset:2px}
.week .chev{width:12px;height:12px}
"""

# The three views: a button or a swipe moves between them (the track snaps, like Page 0's weeks --
# render_html.PAGE0_JS, which this follows), and the choice goes in the URL (#division / #conference /
# #league). A division's id (#afc-east, from a team page's division title) opens Division at that
# division's card. --top-h keeps the track filling the screen under the header, whatever its height.
JS = r"""
(function () {
  var track = document.getElementById('track'), top = document.querySelector('.top'),
      panes = [].slice.call(track.querySelectorAll('.pane')), tabs = [].slice.call(document.querySelectorAll('.sw-tab')),
      views = panes.map(function (p) { return p.getAttribute('data-pane'); }), idx = 0;
  function setTop() { document.documentElement.style.setProperty('--top-h', top.offsetHeight + 'px'); }
  function setActive(i, opts) {
    opts = opts || {};
    if (!panes[i]) return;
    idx = i;
    tabs.forEach(function (t) {
      var on = t.getAttribute('data-view') === views[i];
      t.classList.toggle('on', on); t.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    if (opts.scroll) track.scrollTo({ left: i * track.clientWidth, behavior: opts.smooth ? 'smooth' : 'auto' });
    if (opts.updateHash !== false) history.replaceState(null, '', '#' + views[i]);
  }
  tabs.forEach(function (t) {
    t.addEventListener('click', function () {
      var i = views.indexOf(t.getAttribute('data-view'));
      setActive(i, { scroll: true, smooth: Math.abs(i - idx) === 1 });
    });
  });
  var settle;
  track.addEventListener('scroll', function () {
    clearTimeout(settle);
    settle = setTimeout(function () {
      var i = Math.round(track.scrollLeft / track.clientWidth);
      if (i !== idx) setActive(i);
    }, 90);
  }, { passive: true });
  document.addEventListener('keydown', function (e) {
    if (e.altKey || e.metaKey || e.ctrlKey) return;
    if (e.key === 'ArrowRight') setActive(idx + 1, { scroll: true, smooth: true });
    if (e.key === 'ArrowLeft') setActive(idx - 1, { scroll: true, smooth: true });
  });
  function fromHash() {
    var h = location.hash.slice(1), i = views.indexOf(h);
    if (i >= 0) { if (i !== idx) setActive(i, { scroll: true, updateHash: false }); return; }
    var el = h && document.getElementById(h), card = el && el.closest('.pc'), pane = card && card.closest('.pane');
    if (card) {
      setActive(views.indexOf(pane.getAttribute('data-pane')), { scroll: true, updateHash: false });
      pane.scrollTop += card.getBoundingClientRect().top - pane.getBoundingClientRect().top;
    }
  }
  window.addEventListener('hashchange', fromHash);
  window.addEventListener('resize', function () { setTop(); track.scrollLeft = idx * track.clientWidth; });
  if ('ResizeObserver' in window) new ResizeObserver(setTop).observe(top);
  setTop();
  setActive(0, { updateHash: false });
  fromHash();
  // again after the fonts, so the header (and so the cards) are at their final height
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(function () { setTop(); fromHash(); });
})();
"""

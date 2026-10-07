"""
Standings -- site/standings.html (Jason, 2026-10-07; picked as "D" in mockups/build_standings_mockup.py).

A page of its own, outside Page 0 / 1 / 2: reached from the bottom bar's menu (theme.menu_html)
on every page, and from the division title on a team page's Overview card (render_page2team).

  - title: the year (Saira italic, like the team abbreviations) over "REGULAR SEASON", then
    "Through Week N" -- the last week with a finished game
  - three buttons, styled like Player Stats' team switch (the chosen one full strength, the others
    faded): Division / Conference / League. The choice is in the URL (#division, #conference,
    #league) so it can be linked; #afc-east etc. opens Division scrolled to that division
  - every team is one row: [seed] helmet + abbreviation, W, L, T, PCT, DIV, CONF, STRK
  - Division: AFC, then its four divisions (titled East / North / South / West on the column-heads
    line), then NFC
  - Conference: the playoff picture -- AFC 1-16 then NFC 1-16 under the same AFC / NFC titles;
    division leaders take seeds 1-4, the rest from 5. "Division leaders" sits on the column-heads
    line, then "Wild card" over 5-7 and "In the hunt" over 8-16
  - League: 1-32, just the column heads above it
  - thin lines between teams, none under the last team of a group or a section
  - a key at the bottom: the columns, then the clinch marks
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

import helmets
import theme
from divisions import DIVISIONS, normalize_abbr
from render_page1 import CHEV, helmet_img

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
        f'<span class="who"><span class="mk">{esc(mark)}</span>{helmet_img(r["team"], 22, prefix="")}'
        f'<span class="abbr">{esc(r["team"])}</span></span>'
        f'<span class="n">{r["w"]}</span><span class="n">{r["l"]}</span><span class="n">{r["t"]}</span>'
        f'<span class="n pct">{_fmt_pct(r)}</span>'
        f'<span class="n sub">{_rec(r["dw"], r["dl"], r["dt"])}</span>'
        f'<span class="n sub">{_rec(r["cw"], r["cl"], r["ct"])}</span>'
        f'<span class="n">{esc(r["streak"]) or "—"}</span></div>'
    )


def _group(label, rows, seeded=False, bands=None, gid=None):
    """One table. bands = {position: label} for the section names inside it; a band at 1 goes on
    the column-heads line in place of label."""
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
    return f'<section class="grp-box{" seeded" if seeded else ""}"{gid_attr}>{head}{"".join(body)}</section>'


def _division(rows):
    out = []
    for c in CONFS:
        out.append(f'<h2 class="conf-h">{c}</h2>')
        for d in DIV_NAMES:
            name = f"{c} {d}"
            out.append(_group(d, order([r for r in rows if r["div"] == name]), gid=name.lower().replace(" ", "-")))
    return "".join(out)


def _conference(rows):
    out = []
    for c in CONFS:
        out.append(f'<h2 class="conf-h">{c}</h2>')
        out.append(_group("", seeds(rows, c), seeded=True,
                          bands={1: "Division leaders", 5: "Wild card", 8: "In the hunt"}))
    return "".join(out)


def _league(rows):
    return _group("", order(rows), seeded=True)


def _legend():
    cols = "".join(f'<div><dt>{k}</dt><dd>{esc(v)}</dd></div>' for k, v in LEGEND)
    marks = "".join(f'<div><dt class="mkk">{k}</dt><dd>{esc(v)}</dd></div>' for k, v in CLINCH_KEY)
    return (f'<footer class="legend"><h3>Key</h3><dl>{cols}</dl><h3>Clinched</h3><dl>{marks}</dl>'
            '<p class="note">Seeds 1–4 go to the division winners; 5–7 are the wild cards.</p></footer>')


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
    panes = (f'<div class="pane on" data-pane="division" role="tabpanel">{_division(rows)}</div>'
             f'<div class="pane" data-pane="conference" role="tabpanel">{_conference(rows)}</div>'
             f'<div class="pane" data-pane="league" role="tabpanel">{_league(rows)}</div>')
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        "<meta name='theme-color' content='#F3F3EE'>"
        f"<script>{theme.THEME_HEAD_JS}</script>"
        f"<title>{esc(season)} Standings · At A Glance</title>"
        "<meta name='description' content='Pro Football Standings'>"
        f"{helmets.favicon_links()}"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
        f"<style>{theme.THEME_CSS}{theme.MENU_CSS}{theme.HELMET_SHADOW_CSS}{CSS}</style></head><body>"
        "<main class='wrap'>"
        f"<header class='top'><h1 class='title'><span class='yr abbr'>{esc(season)}</span>"
        f"<span class='rs'>Regular Season</span></h1><div class='thru'>{esc(thru)}</div>"
        f"<div class='sw' role='tablist' aria-label='Standings by'>{tabs}</div></header>"
        f"{panes}{_legend()}</main>"
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
:root{--bbar:""" + theme.BBAR_HEIGHT + """;--text:var(--aag-text);--text-2:var(--aag-text-2);--text-3:var(--aag-text-3)}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--aag-bg)}
body{min-height:100vh;color:var(--text);font-family:Inter,system-ui,-apple-system,sans-serif;font-weight:400;
  -webkit-font-smoothing:antialiased}
.abbr{line-height:1;font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;font-style:italic;
  font-variation-settings:'wdth' 95;letter-spacing:.02em}
.wrap{max-width:600px;margin:0 auto;padding:max(12px,env(safe-area-inset-top)) 16px calc(24px + var(--bbar))}

/* title: the year over "REGULAR SEASON", then how far the standings go */
.top{display:flex;flex-direction:column;align-items:center;gap:6px;padding:6px 0 10px}
.title{display:flex;flex-direction:column;align-items:center;gap:2px;font-weight:700}
.yr{font-size:36px}
.rs{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--text-2)}
.thru{font-size:11px;color:var(--text-3)}
/* Division / Conference / League -- like Player Stats' team switch: the chosen one at full
   strength in a pill outline, the others faded */
.sw{display:flex;justify-content:center;gap:4px;margin-top:4px}
.sw-tab{font:inherit;font-size:14px;font-weight:700;color:var(--text);background:none;border:1px solid transparent;
  border-radius:999px;padding:5px 13px;cursor:pointer;opacity:.45;transition:opacity .16s;-webkit-tap-highlight-color:transparent}
.sw-tab.on{opacity:1;border-color:var(--aag-tile-border)}
.sw-tab:hover{opacity:.8}
.sw-tab.on:hover{opacity:1}
.sw-tab:focus-visible{outline:2px solid var(--aag-focus);outline-offset:2px}
.pane{display:none}
.pane.on{display:block}

/* AFC / NFC over their divisions (Division) or their 1-16 (Conference) */
.conf-h{font-size:15px;font-weight:900;letter-spacing:.1em;margin:22px 0 -6px;padding:0 4px}
.pane>.conf-h:first-child{margin-top:8px}

/* one line per team: [seed] team W L T PCT DIV CONF STRK */
/* opened at a division (#afc-east): its AFC / NFC title stays in view above it */
.grp-box{margin-top:18px;scroll-margin-top:44px}
.row{display:grid;grid-template-columns:minmax(0,1fr) 20px 20px 16px 38px 34px 34px 28px;align-items:center;
  column-gap:4px;padding:5px 4px;font-size:13px;font-variant-numeric:tabular-nums;border-bottom:1px solid var(--aag-tile-border-soft)}
.seeded .row{grid-template-columns:16px minmax(0,1fr) 20px 20px 16px 38px 34px 34px 28px}
/* no line under the last team of a group or a section */
.row.end,.row.head{border-bottom:0}
.row.head{padding:0 4px 4px;font-size:10px;font-weight:700;letter-spacing:.04em;color:var(--text-3)}
.grp,.band{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2);white-space:nowrap}
.seeded .row.head .grp{grid-column:1/3}
.seeded .row.head>span:first-child{display:none}
.band{padding:10px 4px 2px}
.n{text-align:center}
.pct{text-align:right}
.sub{color:var(--text-2);font-size:12px}
.who{display:flex;align-items:center;gap:6px;min-width:0}
.who img{width:22px;height:22px;flex:none;--hs:22px}
.who .abbr{font-size:14px}
.seed{font-size:11px;font-weight:700;color:var(--text-3);text-align:right}
/* the clinch letter, in a slot of its own so the helmets line up */
.mk{display:inline-block;width:8px;flex:none;text-align:center;font-size:11px;font-weight:700;color:var(--text-2)}

/* the key */
.legend{margin-top:28px;padding-top:14px;border-top:1px solid var(--aag-tile-border)}
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
  .row,.seeded .row{column-gap:2px;font-size:12px}
  .row{grid-template-columns:minmax(0,1fr) 17px 17px 13px 34px 30px 30px 25px}
  .seeded .row{grid-template-columns:13px minmax(0,1fr) 17px 17px 13px 34px 30px 30px 25px}
  .grp,.band{letter-spacing:.02em}
  .who img{display:none}
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

# The three buttons; the choice goes in the URL (#division / #conference / #league). A division's
# id (#afc-east, from a team page's division title) opens Division at that division.
JS = r"""
(function () {
  var tabs = [].slice.call(document.querySelectorAll('.sw-tab')), panes = document.querySelectorAll('.pane');
  function show(v) {
    tabs.forEach(function (t) { var on = t.getAttribute('data-view') === v; t.classList.toggle('on', on); t.setAttribute('aria-selected', on ? 'true' : 'false'); });
    [].forEach.call(panes, function (p) { p.classList.toggle('on', p.getAttribute('data-pane') === v); });
  }
  tabs.forEach(function (t) {
    t.addEventListener('click', function () {
      var v = t.getAttribute('data-view');
      show(v);
      history.replaceState(null, '', '#' + v);
    });
  });
  function fromHash() {
    var h = location.hash.slice(1);
    if (h === 'conference' || h === 'league' || h === 'division') { show(h); return; }
    var el = h && document.getElementById(h);
    if (el) { show('division'); el.scrollIntoView(); }
  }
  window.addEventListener('hashchange', fromHash);
  fromHash();
})();
"""

"""
Standings as full-screen cards -- mockup (2026-10-07), NOT part of the live build.

SNAPSHOT: Jason picked this; it now lives in the real build (render_standings.py), so running this
script against the current code stops at its asserts (the page it rewrites has already changed).
Kept for reference.

The real standings page (render_standings.py) with each view split into cards that fill the
screen between the frozen header and the bottom bar, and snap one at a time when swiping up / down:

  Division   -- AFC (its four divisions) | NFC | the key
  Conference -- AFC 1-16 | NFC 1-16 | the key
  League     -- 1-32 in one card that scrolls freely (it's taller than the screen) | the key

Each view is its own up / down scroller that snaps (like Page 1's card deck) -- the page itself
doesn't scroll, so the header stays put. (Snap points inside the sideways track belong to the
track, not the page, which is why snapping on the page did nothing.) On Division and Conference
the teams spread out to fill each card, whatever the phone's height; helmets are 18px here, down
from 22. The stat columns spread across the row (the team column no wider than it needs), values
centered under their headings, and AFC / NFC centered. A small "v NFC" / "v Key" at
the bottom of a card says what the next swipe brings, and "^ AFC" / "^ NFC" at the top what's above,
like Page 1's card slivers. Swiping left /
right still moves between Division / Conference / League (render_standings.JS, unchanged).

Run after a normal build (so data/matchups.json exists and site/helmets/ is there):
    python mockups/build_standings_cards_mockup.py [out.html]
Writes site/standings-cards.html by default, next to the real standings.html, so the helmets load.
standings-cards.html?card=1#conference opens on a given card (for screenshots).
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import render_standings as rs  # noqa: E402
from render_page1 import DOWN, UP  # noqa: E402

DIV_NAMES = rs.DIV_NAMES
CONFS = rs.CONFS


def group(label, rows, seeded=False, first_seed=1, bands=None):
    """render_standings._group, but numbering can start past 1 (League's second card) and the
    group stretches to its share of the card (--n = its team count)."""
    bands = dict(bands or {})
    label = bands.pop(1, label)
    lead = "<span></span>" if seeded else ""
    head = (f'<div class="row head">{lead}<span class="grp">{rs.esc(label)}</span>'
            + "".join(f'<span class="n">{h}</span>' for h in rs.HEADS) + "</div>")
    body = []
    for i, r in enumerate(rows, 1):
        if i in bands:
            body.append(f'<div class="band">{rs.esc(bands[i])}</div>')
        body.append(rs._row(r, seed=first_seed + i - 1 if seeded else None,
                            end=(i == len(rows) or (i + 1) in bands)))
    return (f'<section class="grp-box{" seeded" if seeded else ""}" style="--n:{len(rows)}">'
            f'{head}{"".join(body)}</section>')


def peek(label, up=False):
    """The name of the card above (^) or below (v), like Page 1's card slivers."""
    return f'<div class="peek {"prev" if up else "next"}">{UP if up else DOWN}<span>{label}</span></div>' if label else ""


def card(title, body, nxt, prev=None):
    t = f'<h2 class="conf-h">{title}</h2>' if title else ""
    return f'<article class="pc">{peek(prev, up=True)}{t}<div class="pc-body">{body}</div>{peek(nxt)}</article>'


def key_card(prev):
    return f'<article class="pc pc-key">{peek(prev, up=True)}{rs._legend()}</article>'


def division(rows):
    return "".join(
        card(c, "".join(group(d, rs.order([r for r in rows if r["div"] == f"{c} {d}"])) for d in DIV_NAMES),
             "NFC" if c == "AFC" else "Key", None if c == "AFC" else "AFC")
        for c in CONFS) + key_card("NFC")


def conference(rows):
    return "".join(
        card(c, group("", rs.seeds(rows, c), seeded=True,
                      bands={1: "Div. leaders", 5: "Wild card", 8: "In the hunt"}),
             "NFC" if c == "AFC" else "Key", None if c == "AFC" else "AFC")
        for c in CONFS) + key_card("NFC")


def league(rows):
    # one card, as tall as its 32 teams: it scrolls freely, then snaps to the key
    return card("", group("", rs.order(rows), seeded=True), "Key").replace('class="pc"', 'class="pc pc-long"', 1) + key_card("League")


CSS = """
/* MOCKUP: the page doesn't scroll; each view scrolls up / down inside the track and snaps card by card */
html,body{height:100%;overflow:hidden}
.track{height:calc(100dvh - var(--top-h,112px) - var(--bbar)) !important}
.pane{height:100%;overflow-y:auto;overscroll-behavior-y:contain;scroll-snap-type:y mandatory;
  -webkit-overflow-scrolling:touch;scrollbar-width:none}
.pane::-webkit-scrollbar{display:none}
.pane-in{height:100%;padding-bottom:0}
.pc{height:100%;scroll-snap-align:start;scroll-snap-stop:always;
  display:flex;flex-direction:column;padding:8px 0 6px;overflow:hidden}
.pc .conf-h{margin:4px 0 0;flex:none}
.pc-body{flex:1 1 0;min-height:0;display:flex;flex-direction:column}
.pc .grp-box{flex:var(--n) 1 0;min-height:0;display:flex;flex-direction:column;margin-top:10px}
.pc .grp-box:first-child{margin-top:8px}
.pc .row:not(.head){flex:1 1 0;min-height:0;padding-top:0;padding-bottom:0}
.pc .row.head,.pc .band{flex:none}
/* League: as tall as its 32 teams at the usual row height, scrolling freely before the key */
.pc.pc-long{height:auto;min-height:100%;overflow:visible}
.pc-long .pc-body,.pc-long .grp-box{flex:none}
.pc-long .row:not(.head){flex:none;padding-top:5px;padding-bottom:5px}
/* ...and it scrolls freely: League only snaps when the key is close, rather than on every swipe */
.pane[data-pane=league]{scroll-snap-type:y proximity}
.pc.pc-long{scroll-snap-stop:normal}
/* smaller helmets, so the rows fit on shorter phones */
.who img{width:18px;height:18px;--hs:18px}
.who{gap:5px}
.peek{flex:none;display:flex;align-items:center;justify-content:center;gap:6px;font-size:11px;
  font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3)}
.peek.next{padding-top:6px}
.peek.prev{padding-bottom:2px}
.pc-key .peek.prev{padding-bottom:14px}
/* columns spread across the row: the team column only as wide as mark + helmet + abbreviation, the
   stat columns sharing the rest (PCT / DIV / CONF a little wider); every value centered under its
   heading */
.row{grid-template-columns:var(--team-w,74px) repeat(3,minmax(0,.8fr)) minmax(0,1.25fr) repeat(2,minmax(0,1.15fr)) minmax(0,1fr)}
.seeded .row{grid-template-columns:16px var(--team-w,74px) repeat(3,minmax(0,.8fr)) minmax(0,1.25fr) repeat(2,minmax(0,1.15fr)) minmax(0,1fr)}
.pct{text-align:center}
.row.head{align-items:end}
/* a section name on the column-heads line ("Div. leaders") wraps in its corner if it ever runs long */
.seeded .row.head .grp{white-space:normal;line-height:1.15}
.conf-h{text-align:center}
.pc-key .legend{margin-top:0;border-top:0;padding-top:0}
"""

# the cards' height leaves room for the frozen header, whatever its height
JS = r"""
(function () {
  var top = document.querySelector('.top');
  function setTop() { document.documentElement.style.setProperty('--top-h', top.offsetHeight + 'px'); }
  setTop();
  window.addEventListener('resize', setTop);
  if ('ResizeObserver' in window) new ResizeObserver(setTop).observe(top);
  // mockup only: ?card=N opens on the view's Nth card (0 = the first), e.g. ?card=1#conference
  var n = +(new URLSearchParams(location.search).get('card') || 0);
  if (n) {
    var view = location.hash.slice(1) || 'division',
        pane = document.querySelector('.pane[data-pane="' + view + '"]'),
        c = pane && pane.querySelectorAll('.pc')[n];
    if (c) (document.fonts ? document.fonts.ready : Promise.resolve()).then(function () {
      setTop();
      // two frames, so the page has grown to the cards' new height before jumping
      requestAnimationFrame(function () { requestAnimationFrame(function () {
        pane.scrollTop = c.offsetTop - pane.querySelector('.pc').offsetTop;
      }); });
    });
  }
})();
"""


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "site", "standings-cards.html")
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        data = json.load(f)
    rows, _ = rs.build(data.get("season_weeks"))
    page = rs.render(data)
    # swap each view's body for its cards, and drop the shared key (each view has its own key card now)
    for view, fn, body in (("division", division, rs._division(rows)), ("conference", conference, rs._conference(rows)),
                           ("league", league, rs._league(rows))):
        assert page.count(body) == 1, view
        page = page.replace(body, fn(rows))
    legend = f"<div class='wrap'>{rs._legend()}</div>"
    assert page.count(legend) == 1
    page = page.replace(legend, "")
    page = page.replace("</style></head>", CSS + "</style></head>", 1)
    page = page.replace("</body>", f"<script>{JS}</script></body>", 1)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

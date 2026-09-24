"""
Dark mode mockup (2026-09-24) -- NOT part of the live build.

Builds mockups/dark-mode.html: one self-contained page with three phone
frames showing the real rendered pages (Page 0's week list, and one game's
Page 1 in both its condensed and expanded views), with a proposed dark
theme layered on top and a light/dark switch pinned to the LEFT corner of
the persistent bottom bar (mirroring the +/- toggle in the right corner).

Every phone is an iframe running the page's own markup, CSS and script, so
swiping, the +/- toggle and the detail pages all still work. Flip the switch
in any phone and all three change together.

The dark palette and the switch live in DARK_CSS / SWITCH_* below so they
can be lifted into theme.py / render_html.py / render_page1.py if the
mockup is approved.

Run after a normal build (so site/ exists):
    python build_data.py && python render_html.py
    python mockups/build_dark_mode_mockup.py
"""

import base64
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "mockups", "dark-mode.html")

FINAL_GAME = "2026_02_DET_BUF"      # a finished game: scores, winner arrow, W/L colors
UPCOMING_GAME = "2026_03_PHI_CHI"   # an upcoming game: kickoff time, odds, injuries

# ---------------------------------------------------------------- dark palette

# Near-black ground with a slightly lifted tile, so the outlined cards still
# read as objects. Text keeps the same three-step opacity ladder as light mode.
DARK = {
    "bg": "#0B0B0C",
    "tile": "#161618",
    "tile_border": "rgba(255,255,255,.12)",
    "tile_border_soft": "rgba(255,255,255,.07)",
    "tile_hover": "rgba(255,255,255,.04)",
    "tile_border_hover": "rgba(255,255,255,.32)",
    "text": "#F2F2F2",
    "text_2": "rgba(255,255,255,.62)",
    "text_3": "rgba(255,255,255,.4)",
    "bar": "rgba(11,11,12,.9)",
    "pill_hover": "rgba(255,255,255,.08)",
    "dot": "#3A3A3D",
}

DARK_CSS = """
html[data-theme=dark]{color-scheme:dark}
html[data-theme=dark],html[data-theme=dark] body{background:%(bg)s}
/* Page 0 */
html[data-theme=dark]{--bg:%(bg)s;--tile:%(tile)s;--tile-border:%(tile_border)s;--tile-hover:%(tile_hover)s;
  --tile-border-hover:%(tile_border_hover)s;--text:%(text)s;--text-2:%(text_2)s;--text-3:%(text_3)s}
[data-theme=dark] .bottombar{background:%(bar)s}
[data-theme=dark] .week-picker:hover{background:%(pill_hover)s}
[data-theme=dark] .toggle,[data-theme=dark] .tri{color:%(text)s}
[data-theme=dark] .p1-host{background:%(bg)s}
/* Page 1 + Page 2. Status colors are brightened a step so they hold up on black. */
[data-theme=dark] .p1{--ink:%(text)s;--tile:%(tile)s;--tile-border:%(tile_border)s;--tile-border-soft:%(tile_border_soft)s;
  --tile-hover:%(tile_hover)s;--tile-border-hover:%(tile_border_hover)s;--text-2:%(text_2)s;--text-3:%(text_3)s;
  --out:#FF6B6B;--doubt:#FF8A5C;--ques:#E8B93A;--win:#4CC76E;--loss:#FF6B6B;--tie:#E8B93A;background:%(bg)s}
[data-theme=dark] .bar,[data-theme=dark] .bbar{background:%(bar)s}
[data-theme=dark] .week:hover{background:%(pill_hover)s}
[data-theme=dark] .p2{background:%(bg)s}
[data-theme=dark] .slot.below a.card:hover .peek,[data-theme=dark] .slot.above a.card:hover .peek{color:%(text)s}
[data-theme=dark] .dot{background:%(dot)s}
[data-theme=dark] .dot.on{background:%(text)s}
[data-theme=dark] .p1 > .dots .dot svg{color:%(text)s}
[data-theme=dark] :focus-visible,[data-theme=dark] .week-picker:focus-within{outline-color:#fff}
""" % DARK

# ---------------------------------------------------------------- the switch

# Sits in the bottom bar's left corner, vertically centered on the same line
# as the week pill and the +/- toggle (both center at y=26px in the 52px bar).
SWITCH_CSS = """
.theme-switch{position:absolute;left:16px;top:12px;width:48px;height:28px;padding:0;border:0;background:none;cursor:pointer;
  -webkit-tap-highlight-color:transparent;transition:transform .2s cubic-bezier(.22,1,.36,1)}
.theme-switch:hover{transform:scale(1.08)}
.theme-switch:active{transform:scale(1.14)}
.theme-switch:focus-visible{outline:2px solid currentColor;outline-offset:3px;border-radius:999px}
.ts-track{position:absolute;inset:0;border-radius:999px;background:rgba(0,0,0,.1);box-shadow:inset 0 0 0 1px rgba(0,0,0,.06);
  transition:background-color .25s ease}
.ts-knob{position:absolute;top:3px;left:3px;width:22px;height:22px;border-radius:50%;background:#fff;color:#000;
  box-shadow:0 1px 3px rgba(0,0,0,.28);transition:transform .3s cubic-bezier(.22,1,.36,1)}
.ts-knob svg{position:absolute;inset:4px;width:14px;height:14px;transition:opacity .2s ease,transform .3s cubic-bezier(.22,1,.36,1)}
.ts-moon{opacity:0;transform:rotate(-60deg) scale(.6)}
[data-theme=dark] .ts-track{background:rgba(255,255,255,.24);box-shadow:inset 0 0 0 1px rgba(255,255,255,.08)}
[data-theme=dark] .ts-knob{transform:translateX(20px)}
[data-theme=dark] .ts-sun{opacity:0;transform:rotate(60deg) scale(.6)}
[data-theme=dark] .ts-moon{opacity:1;transform:none}
"""

SWITCH_HTML = (
    '<button class="theme-switch" type="button" role="switch" aria-checked="false" aria-label="Dark mode">'
    '<span class="ts-track"></span><span class="ts-knob">'
    '<svg class="ts-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="4.2" fill="currentColor" stroke="none"/>'
    '<path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/></svg>'
    '<svg class="ts-moon" viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M20.5 14.6A8.5 8.5 0 0 1 9.4 3.5a8.5 8.5 0 1 0 11.1 11.1Z" fill="currentColor"/></svg>'
    "</span></button>"
)

# Runs inside every phone. The parent page owns the theme so all phones stay in sync;
# a real build would read/write localStorage here instead.
SWITCH_JS = """
(function () {
  var de = document.documentElement;
  function set(t) {
    de.setAttribute('data-theme', t);
    [].forEach.call(document.querySelectorAll('.theme-switch'), function (b) { b.setAttribute('aria-checked', String(t === 'dark')); });
    var m = document.querySelector('meta[name=theme-color]'); if (m) m.content = t === 'dark' ? '%(bg)s' : '#ffffff';
  }
  window.addEventListener('message', function (e) { if (e.data && e.data.aagTheme) set(e.data.aagTheme); });
  window.addEventListener('click', function (e) {
    var sw = e.target.closest('.theme-switch');
    if (sw) {
      e.preventDefault(); e.stopImmediatePropagation();
      parent.postMessage({ aagThemeReq: de.getAttribute('data-theme') === 'dark' ? 'light' : 'dark' }, '*');
      return;
    }
    // The mockup only carries two game pages, so links that would leave this page are inert.
    var a = e.target.closest('a[href]'), href = a && a.getAttribute('href');
    if (a && href !== '#' && !a.classList.contains('p2-back')) { e.preventDefault(); e.stopImmediatePropagation(); }
  }, true);
  set(window.AAG_THEME || 'dark');
})();
""" % DARK


# The phones are iframes, where env(safe-area-inset-bottom) is 0 -- pad the bottom bar
# the way an iPhone's home indicator would, so the switch sits where it really would.
PHONE_CSS = """
:root,.p1{--bbar:calc(52px + 22px)!important}
.bottombar,.bbar{height:var(--bbar)!important;padding-bottom:22px!important}
"""


def read(path):
    with open(os.path.join(SITE, path), encoding="utf-8") as f:
        return f.read()


def dress(html, bar_class, init_view=None):
    """Inject the dark CSS, the switch and its script into one rendered page."""
    html = html.replace("</head>", f"<style id='dark-mockup'>{DARK_CSS}{SWITCH_CSS}{PHONE_CSS}</style></head>", 1)
    # switch = first child of the bottom bar's inner column, so it shares the week pill's line
    html = re.sub(rf'(<(?:nav|div|footer)[^>]*class=["\']{bar_class}["\'][^>]*>\s*<div class=["\'][^"\']*["\']>)',
                  lambda m: m.group(1) + SWITCH_HTML, html, count=1)
    if SWITCH_HTML not in html:
        raise SystemExit(f"couldn't find the {bar_class} bottom bar to put the switch in")
    if init_view:
        html = html.replace("AAG_P1.init(document);", f"AAG_P1.init(document,{{view:'{init_view}'}});")
    return html.replace("</body>", f"<script>{SWITCH_JS}</script></body>", 1)


def helmets():
    out, folder = {}, os.path.join(SITE, "helmets")
    for name in sorted(os.listdir(folder)):
        if name.endswith(".svg"):
            with open(os.path.join(folder, name), "rb") as f:
                out[name[:-4]] = "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()
    return out


def js_string(s):
    return json.dumps(s).replace("</", "<\\/")


def main():
    index = read("index.html")
    week_bar = re.search(r'class=["\'](bottombar)["\']', index)
    if not week_bar:
        raise SystemExit("site/index.html has no .bottombar -- has the markup changed?")
    pages = {
        "week": dress(index, "bottombar"),
        "final": dress(read(f"game/{FINAL_GAME}.html"), "bbar", "condensed"),
        "upcoming": dress(read(f"game/{UPCOMING_GAME}.html"), "bbar"),
    }
    with open(os.path.join(ROOT, "mockups", "dark_mode_shell.html"), encoding="utf-8") as f:
        shell = f.read()
    data = ("<script>window.MOCK_PAGES = {" + ",".join(f"{k}:{js_string(v)}" for k, v in pages.items()) + "};"
            f"window.MOCK_HELMETS = {js_string(json.dumps(helmets()))};</script>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(shell.replace("<!--MOCK_DATA-->", data))
    print(f"Wrote {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()

"""
Dark mode mockup (2026-09-24) -- NOT part of the live build.

SNAPSHOT: this was the design mockup. The approved version now lives in the real
build (theme.py, helmets.py), so this script only works against a site/ built from
before that change (commit 3bf4628). Kept for reference; the .html beside it still opens.

Builds mockups/dark-mode.html: one self-contained page with three phone
frames showing the real rendered pages (Page 0's week list, and two games'
Page 1), with a proposed dark theme and a light/dark switch pinned to the
LEFT corner of the persistent bottom bar (mirroring the +/- toggle on the
right).

How the theme is meant to work (and how this mockup wires it):

  * One set of theme tokens (--aag-*) lives on the page's root element.
    Light values are the default; dark values apply when the phone is set to
    dark (prefers-color-scheme) unless someone picked light with the switch,
    or whenever someone picked dark. The switch's choice is saved on the
    device; until it's used, the page follows the phone.

  * Reaching Page 1 inside Page 0's overlay: the overlay mounts each game in
    a shadow root and copies only #p1-css into it, so no page-level selector
    like `html[data-theme=dark] .p1` can reach in. Custom properties DO
    inherit through a shadow boundary, though. So Page 1's styles read every
    color from the --aag-* tokens (P1_BRIDGE_CSS below) instead of
    hardcoding them, and whatever theme the root is in flows straight into
    every mounted game -- no script has to find and restyle the shadow roots.
    The same rules work on a standalone game page, where the tokens sit on
    that page's own root.

  * The switch itself is styled from tokens too (knob position, sun/moon),
    so the copy inside a shadow root flips with everything else.

Every phone is an iframe running the page's own markup, CSS and script. The
Week phone opens PHI @ CHI (week 3) and DET @ BUF (week 2) through the real
overlay, which is the shadow-DOM path described above. Other games are inert
because the mockup only carries these two.

In the mockup the "phone setting" comes from the control at the top of the
page instead of the real OS setting, so both paths can be tried: in the live
build THEME_CSS's `:root[data-sys=dark]` becomes a
`@media (prefers-color-scheme:dark)` block (see theme_css(system="media")).

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
UPCOMING_GAME = "2026_03_PHI_CHI"   # an upcoming game: kickoff time, injuries

# ---------------------------------------------------------------- tokens

LIGHT = {
    "bg": "#fff", "tile": "#fff",
    "tile-border": "rgba(0,0,0,.12)", "tile-border-soft": "rgba(0,0,0,.07)",
    "tile-hover": "rgba(0,0,0,.03)", "tile-border-hover": "rgba(0,0,0,.28)",
    "text": "#000", "text-2": "rgba(0,0,0,.62)", "text-3": "rgba(0,0,0,.4)",
    "bar-bg": "rgba(255,255,255,.94)", "pill-hover": "rgba(0,0,0,.05)", "dot": "#CFCFCF", "focus": "#000",
    "out": "#A00000", "doubt": "#A52800", "ques": "#B58900", "win": "#1E8A3C", "loss": "#A00000", "tie": "#B58900",
    "theme-color": "#ffffff",
    # the switch
    "sw-track": "rgba(0,0,0,.1)", "sw-ring": "rgba(0,0,0,.06)", "sw-x": "0px",
    "sw-sun": "1", "sw-moon": "0", "sw-sun-t": "none", "sw-moon-t": "rotate(-60deg) scale(.6)",
}
# Near-black ground with a slightly lifted tile, so the outlined cards still read as objects.
# Text keeps the same three-step opacity ladder; status colors go one step brighter for black.
DARK = dict(LIGHT, **{
    "bg": "#0B0B0C", "tile": "#161618",
    "tile-border": "rgba(255,255,255,.12)", "tile-border-soft": "rgba(255,255,255,.07)",
    "tile-hover": "rgba(255,255,255,.04)", "tile-border-hover": "rgba(255,255,255,.32)",
    "text": "#F2F2F2", "text-2": "rgba(255,255,255,.62)", "text-3": "rgba(255,255,255,.4)",
    "bar-bg": "rgba(11,11,12,.9)", "pill-hover": "rgba(255,255,255,.08)", "dot": "#3A3A3D", "focus": "#fff",
    "out": "#FF6B6B", "doubt": "#FF8A5C", "ques": "#E8B93A", "win": "#4CC76E", "loss": "#FF6B6B", "tie": "#E8B93A",
    "theme-color": "#0B0B0C",
    "sw-track": "rgba(255,255,255,.24)", "sw-ring": "rgba(255,255,255,.08)", "sw-x": "20px",
    "sw-sun": "0", "sw-moon": "1", "sw-sun-t": "rotate(60deg) scale(.6)", "sw-moon-t": "none",
})


def _decls(tokens):
    return ";".join(f"--aag-{k}:{v}" for k, v in tokens.items())


def theme_css(system="attr"):
    """The root tokens. system="media" is the live-site form (follows the phone's setting);
    system="attr" reads a data-sys attribute instead, so the mockup can fake the phone setting."""
    sys_dark = (":root[data-sys=dark]:not([data-theme=light])" if system == "attr"
                else "@media (prefers-color-scheme:dark){:root:not([data-theme=light])")
    close = "" if system == "attr" else "}"
    return (f":root{{{_decls(LIGHT)};color-scheme:light}}\n"
            f"{sys_dark}{{{_decls(DARK)};color-scheme:dark}}{close}\n"
            f":root[data-theme=dark]{{{_decls(DARK)};color-scheme:dark}}\n")


# Page 0's own rules, pointed at the tokens (Page 0 already routes most colors through
# --bg/--tile/--text, so those just alias the shared tokens).
PAGE0_BRIDGE_CSS = """
:root{--bg:var(--aag-bg);--tile:var(--aag-tile);--tile-border:var(--aag-tile-border);--tile-hover:var(--aag-tile-hover);
  --tile-border-hover:var(--aag-tile-border-hover);--text:var(--aag-text);--text-2:var(--aag-text-2);--text-3:var(--aag-text-3)}
html,body,.p1-host{background:var(--aag-bg)}
.bottombar{background:var(--aag-bar-bg)}
.week-picker:hover{background:var(--aag-pill-hover)}
.toggle,.tri{color:var(--aag-text)}
.toggle:focus-visible,.week-picker:focus-within,.game:focus-visible{outline-color:var(--aag-focus)}
"""

# Page 1 / Page 2 rules, pointed at the tokens. This goes INSIDE #p1-css, so the overlay
# copies it into each game's shadow root, where the inherited --aag-* values resolve it.
P1_BRIDGE_CSS = """
.p1{--ink:var(--aag-text);--tile:var(--aag-tile);--tile-border:var(--aag-tile-border);--tile-border-soft:var(--aag-tile-border-soft);
  --tile-hover:var(--aag-tile-hover);--tile-border-hover:var(--aag-tile-border-hover);--text-2:var(--aag-text-2);--text-3:var(--aag-text-3);
  --out:var(--aag-out);--doubt:var(--aag-doubt);--ques:var(--aag-ques);--win:var(--aag-win);--loss:var(--aag-loss);--tie:var(--aag-tie);
  background:var(--aag-bg)}
.bar,.bbar{background:var(--aag-bar-bg)}
.week:hover{background:var(--aag-pill-hover)}
.p2{background:var(--aag-bg)}
.slot.below a.card:hover .peek,.slot.above a.card:hover .peek{color:var(--aag-text)}
.dot{background:var(--aag-dot)}
.dot.on{background:var(--aag-text)}
.p1 > .dots .dot svg{color:var(--aag-text)}
.toggle{color:var(--aag-text)}
a.card:focus-visible,.week:focus-visible,.toggle:focus-visible{outline-color:var(--aag-focus)}
"""

# ---------------------------------------------------------------- the switch

# Sits in the bottom bar's left corner, vertically centered on the same line as the week
# pill and the +/- toggle (both center at y=26px in the 52px bar). Everything that differs
# between themes comes from tokens, so it needs no [data-theme] selector.
SWITCH_CSS = """
.theme-switch{position:absolute;left:16px;top:12px;width:48px;height:28px;padding:0;border:0;background:none;cursor:pointer;
  -webkit-tap-highlight-color:transparent;transition:transform .2s cubic-bezier(.22,1,.36,1)}
.theme-switch:hover{transform:scale(1.08)}
.theme-switch:active{transform:scale(1.14)}
.theme-switch:focus-visible{outline:2px solid var(--aag-focus);outline-offset:3px;border-radius:999px}
.ts-track{position:absolute;inset:0;border-radius:999px;background:var(--aag-sw-track);box-shadow:inset 0 0 0 1px var(--aag-sw-ring);
  transition:background-color .25s ease}
.ts-knob{position:absolute;top:3px;left:3px;width:22px;height:22px;border-radius:50%;background:#fff;color:#000;
  box-shadow:0 1px 3px rgba(0,0,0,.28);transform:translateX(var(--aag-sw-x));transition:transform .3s cubic-bezier(.22,1,.36,1)}
.ts-knob svg{position:absolute;inset:4px;width:14px;height:14px;transition:opacity .2s ease,transform .3s cubic-bezier(.22,1,.36,1)}
.ts-sun{opacity:var(--aag-sw-sun);transform:var(--aag-sw-sun-t)}
.ts-moon{opacity:var(--aag-sw-moon);transform:var(--aag-sw-moon-t)}
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

# The phones are iframes, where env(safe-area-inset-bottom) is 0 -- pad the bottom bar
# the way an iPhone's home indicator would, so the switch sits where it really would.
PHONE_CSS = """
:root,.p1{--bbar:calc(52px + 22px)!important}
.bottombar,.bbar{height:var(--bbar)!important;padding-bottom:22px!important}
"""

# Runs in each phone's <head>. The mockup page owns the state (phone setting + switch
# choice) so all three phones stay in sync; the live version would keep the choice in
# localStorage and read the phone setting from matchMedia instead.
FRAME_JS = r"""
(function () {
  var de = document.documentElement, init = window.AAG_INIT || {}, sys = init.sys || 'dark', choice = init.choice || null;
  var games = window.AAG_GAMES || {};
  function eff() { return choice || sys; }
  function switches() {
    var all = [].slice.call(document.querySelectorAll('.theme-switch'));
    [].forEach.call(document.querySelectorAll('.p1-host'), function (h) {
      if (h.shadowRoot) all = all.concat([].slice.call(h.shadowRoot.querySelectorAll('.theme-switch')));
    });
    return all;
  }
  function apply() {
    de.setAttribute('data-sys', sys);
    if (choice) de.setAttribute('data-theme', choice); else de.removeAttribute('data-theme');
    switches().forEach(function (b) { b.setAttribute('aria-checked', String(eff() === 'dark')); });
    var m = document.querySelector('meta[name=theme-color]');
    if (m) m.content = getComputedStyle(de).getPropertyValue('--aag-theme-color').trim() || '#ffffff';
  }
  // srcdoc frames refuse history.pushState/replaceState; the overlay uses them for its URLs
  ['pushState', 'replaceState'].forEach(function (k) {
    var real = history[k];
    history[k] = function () { try { return real.apply(history, arguments); } catch (e) {} };
  });
  // Page 0 fetches game pages for its overlay; serve the two this mockup carries.
  var realFetch = window.fetch;
  window.fetch = function (url) {
    var m = String(url).match(/game\/([^\/?#]+)\.html/);
    if (m) {
      var html = games[decodeURIComponent(m[1])];
      return html ? Promise.resolve(new Response(html, { headers: { 'Content-Type': 'text/html' } }))
                  : Promise.reject(new Error('not in the mockup'));
    }
    return realFetch.apply(this, arguments);
  };
  window.addEventListener('message', function (e) {
    if (e.data && e.data.aagState) { sys = e.data.aagState.sys; choice = e.data.aagState.choice; apply(); }
  });
  window.addEventListener('click', function (e) {
    var path = e.composedPath ? e.composedPath() : [e.target], sw = null, a = null;
    for (var i = 0; i < path.length && path[i] !== document; i++) {
      var el = path[i];
      if (!el.classList) continue;
      if (!sw && el.classList.contains('theme-switch')) sw = el;
      if (!a && el.tagName === 'A' && el.hasAttribute('href')) a = el;
    }
    if (sw) {
      e.preventDefault(); e.stopImmediatePropagation();
      var next = eff() === 'dark' ? 'light' : 'dark';
      // picking the same thing the phone is already set to goes back to following the phone
      parent.postMessage({ aagChoice: next === sys ? null : next }, '*');
      return;
    }
    if (!a) return;
    var href = a.getAttribute('href');
    if (/^#game-/.test(href)) {
      if (!games[href.slice(6).split('/')[0]]) { e.preventDefault(); e.stopImmediatePropagation(); }
    } else if (href.charAt(0) !== '#') {
      e.preventDefault();   // links out of the mockup do nothing; the page's own handlers still run
    }
    setTimeout(apply, 400);  // a newly opened game's switch picks up the current state
  }, true);
  apply();
  document.addEventListener('DOMContentLoaded', apply);
})();
"""


def read(path):
    with open(os.path.join(SITE, path), encoding="utf-8") as f:
        return f.read()


def add_switch(html, bar_class):
    # switch = first child of the bottom bar's inner column, so it shares the week pill's line
    out = re.sub(rf'(<(?:nav|div|footer)[^>]*class=["\']{bar_class}["\'][^>]*>\s*<div class=["\'][^"\']*["\']>)',
                 lambda m: m.group(1) + SWITCH_HTML, html, count=1)
    if SWITCH_HTML not in out:
        raise SystemExit(f"couldn't find the {bar_class} bottom bar to put the switch in")
    return out


def dress_week(html):
    html = add_switch(html, "bottombar")
    head = (f"<script>{FRAME_JS}</script>"
            f"<style id='aag-theme'>{theme_css()}{PAGE0_BRIDGE_CSS}{SWITCH_CSS}{PHONE_CSS}</style>")
    return html.replace("</head>", head + "</head>", 1)


def dress_game(html, init_view=None):
    html = add_switch(html, "bbar")
    # Page 1's colors + the switch go INSIDE #p1-css -- the only stylesheet the overlay carries
    # into the shadow root.
    html, n = re.subn(r"(<style id='p1-css'>.*?)(</style>)", lambda m: m.group(1) + P1_BRIDGE_CSS + SWITCH_CSS + PHONE_CSS + m.group(2),
                      html, count=1, flags=re.S)
    if not n:
        raise SystemExit("game page has no #p1-css -- has the markup changed?")
    # the tokens themselves sit on the page root, like on Page 0
    html = html.replace("</head>", f"<script>{FRAME_JS}</script><style id='aag-theme'>{theme_css()}html,body{{background:var(--aag-bg)}}</style></head>", 1)
    if init_view:
        html = html.replace("AAG_P1.init(document);", f"AAG_P1.init(document,{{view:'{init_view}'}});")
    return html


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
    final, upcoming = read(f"game/{FINAL_GAME}.html"), read(f"game/{UPCOMING_GAME}.html")
    pages = {
        "week": dress_week(read("index.html")),
        "final": dress_game(final, "condensed"),
        "upcoming": dress_game(upcoming),
        # what the Week phone's overlay fetches: the plain dressed pages, opened in shadow roots
        "g_" + FINAL_GAME: dress_game(final),
        "g_" + UPCOMING_GAME: dress_game(upcoming),
    }
    with open(os.path.join(ROOT, "mockups", "dark_mode_shell.html"), encoding="utf-8") as f:
        shell = f.read()
    data = ("<script>window.MOCK_PAGES = {" + ",".join(f"{json.dumps(k)}:{js_string(v)}" for k, v in pages.items()) + "};"
            f"window.MOCK_HELMETS = {js_string(json.dumps(helmets()))};</script>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(shell.replace("<!--MOCK_DATA-->", data))
    print(f"Wrote {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()

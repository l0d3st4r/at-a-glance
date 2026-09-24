"""
Shared design tokens, and light/dark mode (2026-09-24).

Every color the pages use is a CSS custom property named --aag-<token>, declared once
on the page's root element by THEME_CSS: the light values by default, the dark values
when the phone is set to dark (unless someone picked light with the switch), or when
someone picked dark. Page 0's stylesheet (render_html.py's PAGE0_CSS) and Page 1's
(render_page1.py's P1_CSS, plus Page 2's P2_CSS / P3_CSS) read colors ONLY through
var(--aag-...) -- never a literal color -- for one reason:

Page 0 opens a game by mounting its Page 1 inside a shadow root (render_html.py's
PAGE1_OVERLAY_JS), and copies only #p1-css in there. No page-level selector such as
`[data-theme=dark] .p1` can reach into a shadow root, but custom properties inherit
straight through it. So whatever theme Page 0's root is in flows into every mounted
game with no script restyling anything. A standalone game page (site/game/<id>.html,
opened directly or from a shared link) declares the same tokens on its own root.

The light/dark switch (SWITCH_HTML) sits in the left corner of the bottom bar on every
page. Until it's used the page follows the phone's setting (prefers-color-scheme).
Using it saves a choice on the device (localStorage "aag-theme"); switching back to
whatever the phone is set to clears the choice, so the page follows the phone again.
"""

BBAR_HEIGHT = "calc(52px + env(safe-area-inset-bottom))"

LIGHT = {
    "bg": "#fff", "tile": "#fff",
    "tile-border": "rgba(0,0,0,.12)", "tile-border-soft": "rgba(0,0,0,.07)",
    "tile-hover": "rgba(0,0,0,.03)", "tile-border-hover": "rgba(0,0,0,.28)",
    "text": "#000", "text-2": "rgba(0,0,0,.62)", "text-3": "rgba(0,0,0,.4)",
    "bar-bg": "rgba(255,255,255,.94)",   # the blurred top and bottom bars
    "pill-hover": "rgba(0,0,0,.05)",     # the week pill's hover fill
    "dot": "#CFCFCF",                    # Page 1's inactive card dots
    "focus": "#000",                     # keyboard focus rings
    "out": "#A00000", "doubt": "#A52800", "ques": "#B58900",   # injury statuses
    "win": "#1E8A3C", "loss": "#A00000", "tie": "#B58900",
    "theme-color": "#ffffff",            # the browser's address-bar color (read by THEME_JS)
    # the switch: everything that differs between themes is a token, so the copy inside a
    # shadow root flips with the rest of the page
    "sw-track": "rgba(0,0,0,.1)", "sw-ring": "rgba(0,0,0,.06)", "sw-x": "0px",
    "sw-sun": "1", "sw-moon": "0", "sw-sun-t": "none", "sw-moon-t": "rotate(-60deg) scale(.6)",
}

# Near-black ground with a slightly lifted tile, so the outlined cards still read as
# objects. Text keeps the same three-step opacity ladder; status colors go one step
# brighter so they hold up on black.
DARK = dict(LIGHT, **{
    "bg": "#0B0B0C", "tile": "#161618",
    "tile-border": "rgba(255,255,255,.12)", "tile-border-soft": "rgba(255,255,255,.07)",
    "tile-hover": "rgba(255,255,255,.04)", "tile-border-hover": "rgba(255,255,255,.32)",
    "text": "#F2F2F2", "text-2": "rgba(255,255,255,.62)", "text-3": "rgba(255,255,255,.4)",
    "bar-bg": "rgba(11,11,12,.9)", "pill-hover": "rgba(255,255,255,.08)", "dot": "#3A3A3D", "focus": "#fff",
    "out": "#FF6B6B", "doubt": "#FF8A5C", "ques": "#E8B93A",
    "win": "#4CC76E", "loss": "#FF6B6B", "tie": "#E8B93A",
    "theme-color": "#0B0B0C",
    "sw-track": "rgba(255,255,255,.24)", "sw-ring": "rgba(255,255,255,.08)", "sw-x": "20px",
    "sw-sun": "0", "sw-moon": "1", "sw-sun-t": "rotate(60deg) scale(.6)", "sw-moon-t": "none",
})


def _decls(tokens):
    return ";".join(f"--aag-{k}:{v}" for k, v in tokens.items())


# The page root's tokens. [data-theme] is only set once someone uses the switch.
THEME_CSS = (
    f":root{{{_decls(LIGHT)};color-scheme:light}}"
    f"@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{{_decls(DARK)};color-scheme:dark}}}}"
    f":root[data-theme=dark]{{{_decls(DARK)};color-scheme:dark}}"
)

# Goes in <head> before any stylesheet, so a saved choice applies before the first paint
# (no white flash when someone picked dark on a light-mode phone).
THEME_HEAD_JS = (
    "(function(){try{var t=localStorage.getItem('aag-theme');"
    "if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t)}catch(e){}})();"
)

# The switch. Sits in the bottom bar's left corner, vertically centered on the same line
# as the week pill and the +/- toggle (both center at y=26px in the 52px bar).
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

# Runs once per page (Page 0, or a standalone game page). Handles every switch on the
# page, including the ones inside Page 0's overlay shadow roots (a click in a shadow root
# reaches document with its target retargeted to the host, so it looks at composedPath()).
# window.AAG_THEME.sync() refreshes the switches' state; the overlay calls it after
# mounting a game.
THEME_JS = r"""
(function () {
  var de = document.documentElement, KEY = 'aag-theme';
  var mq = window.matchMedia ? matchMedia('(prefers-color-scheme: dark)') : { matches: false };
  function system() { return mq.matches ? 'dark' : 'light'; }
  function current() { return de.getAttribute('data-theme') || system(); }
  function switches() {
    var all = [].slice.call(document.querySelectorAll('.theme-switch'));
    [].forEach.call(document.querySelectorAll('.p1-host'), function (h) {
      if (h.shadowRoot) all = all.concat([].slice.call(h.shadowRoot.querySelectorAll('.theme-switch')));
    });
    return all;
  }
  function sync() {
    var dark = current() === 'dark';
    switches().forEach(function (b) { b.setAttribute('aria-checked', String(dark)); });
    var m = document.querySelector('meta[name=theme-color]');
    if (m) m.setAttribute('content', getComputedStyle(de).getPropertyValue('--aag-theme-color').trim() || '#ffffff');
  }
  function choose(t) {
    // picking whatever the phone is set to clears the choice, so the page follows the phone again
    if (t === system()) { de.removeAttribute('data-theme'); try { localStorage.removeItem(KEY); } catch (e) {} }
    else { de.setAttribute('data-theme', t); try { localStorage.setItem(KEY, t); } catch (e) {} }
    sync();
  }
  document.addEventListener('click', function (e) {
    var path = e.composedPath ? e.composedPath() : [e.target];
    for (var i = 0; i < path.length && path[i] !== document; i++) {
      if (path[i].classList && path[i].classList.contains('theme-switch')) {
        e.preventDefault(); e.stopPropagation();
        choose(current() === 'dark' ? 'light' : 'dark');
        return;
      }
    }
  }, true);
  if (mq.addEventListener) mq.addEventListener('change', sync); else if (mq.addListener) mq.addListener(sync);
  window.AAG_THEME = { sync: sync };
  sync();
})();
"""

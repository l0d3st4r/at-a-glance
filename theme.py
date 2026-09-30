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
    # softened contrast (2026-09-30): paper #F3F3EE for white, ink #1B1512 for black
    "bg": "#F3F3EE", "tile": "#F3F3EE",
    "tile-border": "rgba(27,21,18,.12)", "tile-border-soft": "rgba(27,21,18,.07)",
    "tile-hover": "rgba(27,21,18,.03)", "tile-border-hover": "rgba(27,21,18,.28)",
    "text": "#1B1512", "text-2": "rgba(27,21,18,.62)", "text-3": "rgba(27,21,18,.4)",
    "bar-bg": "rgba(243,243,238,.94)",   # the blurred top and bottom bars
    "pill-hover": "rgba(27,21,18,.05)",  # the week pill's hover fill
    "dot": "#CFCFCF",                    # Page 1's inactive card dots
    "focus": "#1B1512",                  # keyboard focus rings
    "out": "#A00000", "doubt": "#A52800", "ques": "#B58900",   # injury statuses
    "win": "#1E8A3C", "loss": "#A00000", "tie": "#B58900",
    "theme-color": "#F3F3EE",            # the browser's address-bar color (read by THEME_JS)
    # the switch: which icon shows is a token, so the copy inside a shadow root flips with the
    # rest of the page -- light mode shows the moon (tap for dark)
    "sw-sun": "none", "sw-moon": "flex",
    # temperature colors (temp_colors.py): how much of a number's light-theme shade to use --
    # all of it here, none in dark, where its dark-theme shade shows instead
    "tc-light": "100%",
    # weather icons (render_page1.py's weather_icon): a step deeper than dark mode's so they hold up
    # on the light ground; the sun and lightning keep dark mode's yellow
    "wx-cloud": "#7C7A77", "wx-cloud-light": "#A3A19D", "wx-wind": "#8FA2B4",
    "wx-rain": "#3D93D6", "wx-snow": "#8AA6BE", "wx-sun": "#F2C230",
}

# Dark ground in the same ink as light mode's text (#1B1512, a warm near-black) with a slightly
# lifted tile, so the outlined cards still read as objects. Text is light mode's paper color
# (#F3F3EE) on the same three-step opacity ladder; status colors go one step brighter so they
# hold up on the dark ground.
DARK = dict(LIGHT, **{
    "bg": "#1B1512", "tile": "#26201D",
    "tile-border": "rgba(243,243,238,.12)", "tile-border-soft": "rgba(243,243,238,.07)",
    "tile-hover": "rgba(243,243,238,.04)", "tile-border-hover": "rgba(243,243,238,.32)",
    "text": "#F3F3EE", "text-2": "rgba(243,243,238,.62)", "text-3": "rgba(243,243,238,.4)",
    "bar-bg": "rgba(27,21,18,.9)", "pill-hover": "rgba(243,243,238,.08)", "dot": "#433B36", "focus": "#F3F3EE",
    "out": "#FF6B6B", "doubt": "#FF8A5C", "ques": "#E8B93A",
    "win": "#4CC76E", "loss": "#FF6B6B", "tie": "#E8B93A",
    "theme-color": "#1B1512",
    "sw-sun": "flex", "sw-moon": "none",   # dark mode shows the sun (tap for light)
    "tc-light": "0%",
    "wx-cloud": "#8E8C89", "wx-cloud-light": "#BDBBB8", "wx-wind": "#C7D3DE",
    "wx-rain": "#7EC3F2", "wx-snow": "#FFFFFF", "wx-sun": "#F2C230",
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

# The switch (2026-09-27): one outline icon for the theme you'd switch TO -- the moon in light
# mode, the sun in dark mode; tapping it switches. (Earlier the same day: sun and moon side by
# side, current one lit; before that, a pill toggle with a sliding knob.) Sits in the bottom
# bar's left corner, vertically centered on the same line as the week pill and the +/- toggle
# (both center at y=26px in the 52px bar).
SWITCH_CSS = """
.theme-switch{position:absolute;left:10px;top:12px;display:flex}
.ts-btn{width:28px;height:28px;padding:0;border:0;background:none;cursor:pointer;color:var(--aag-text);
  align-items:center;justify-content:center;-webkit-tap-highlight-color:transparent;
  transition:opacity .2s ease,transform .2s cubic-bezier(.22,1,.36,1)}
.ts-btn svg{width:18px;height:18px;display:block}
.ts-sun{display:var(--aag-sw-sun)}
.ts-moon{display:var(--aag-sw-moon)}
.ts-btn:hover{opacity:.7;transform:scale(1.04)}
.ts-btn:active{transform:scale(1.07)}
.ts-btn:focus-visible{outline:2px solid var(--aag-focus);outline-offset:1px;border-radius:6px}
"""

SWITCH_HTML = (
    '<div class="theme-switch">'
    '<button class="ts-btn ts-sun" type="button" data-pick="light" aria-label="Switch to light mode">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="4"/>'
    '<path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/></svg></button>'
    '<button class="ts-btn ts-moon" type="button" data-pick="dark" aria-label="Switch to dark mode">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/></svg></button>'
    "</div>"
)

# Runs once per page (Page 0, or a standalone game page). Handles every switch on the
# page, including the ones inside Page 0's overlay shadow roots (a click in a shadow root
# reaches document with its target retargeted to the host, so it looks at composedPath()).
# window.AAG_THEME.sync() refreshes the address-bar color; the overlay calls it after
# mounting a game.
THEME_JS = r"""
(function () {
  var de = document.documentElement, KEY = 'aag-theme';
  var mq = window.matchMedia ? matchMedia('(prefers-color-scheme: dark)') : { matches: false };
  function system() { return mq.matches ? 'dark' : 'light'; }
  function current() { return de.getAttribute('data-theme') || system(); }
  function sync() {
    // which icon shows is pure CSS (the --aag-sw-* tokens); only the address-bar color needs script
    var m = document.querySelector('meta[name=theme-color]');
    if (m) m.setAttribute('content', getComputedStyle(de).getPropertyValue('--aag-theme-color').trim() || '#F3F3EE');
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
      if (path[i].classList && path[i].classList.contains('ts-btn')) {
        e.preventDefault(); e.stopPropagation();
        var t = path[i].getAttribute('data-pick');
        if (t !== current()) choose(t);
        return;
      }
    }
  }, true);
  if (mq.addEventListener) mq.addEventListener('change', sync); else if (mq.addListener) mq.addListener(sync);
  window.AAG_THEME = { sync: sync };
  sync();
})();
"""

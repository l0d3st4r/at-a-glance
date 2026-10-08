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

The menu (menu_html) sits in the left corner of the bottom bar on every page: the site's
pages (Games, Standings, Stat Leaders), then the light/dark switch as its last line (Jason, 2026-10-07 --
until then the switch had that corner to itself). Until the switch is used the page follows
the phone's setting (prefers-color-scheme).
Using it saves a choice on the device (localStorage "aag-theme"); switching back to
whatever the phone is set to clears the choice, so the page follows the phone again.
"""

BBAR_HEIGHT = "calc(52px + env(safe-area-inset-bottom))"

LIGHT = {
    # softened contrast (2026-09-30): paper #F3F3EE for white, ink #161510 for black
    "bg": "#F3F3EE", "tile": "#F3F3EE",
    "tile-border": "rgba(22,21,16,.12)", "tile-border-soft": "rgba(22,21,16,.07)",
    "tile-hover": "rgba(22,21,16,.03)", "tile-border-hover": "rgba(22,21,16,.28)",
    "text": "#161510", "text-2": "rgba(22,21,16,.62)", "text-3": "rgba(22,21,16,.4)",
    "bar-bg": "rgba(243,243,238,.94)",   # the blurred top and bottom bars
    "pill-hover": "rgba(22,21,16,.05)",  # the week pill's hover fill
    "dot": "#CFCFCF",                    # Page 1's inactive card dots
    "focus": "#161510",                  # keyboard focus rings
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
    # Page 2's precipitation chance blends from the text color toward this as the chance rises
    # (a deeper blue than the rain icon's, so the number stays readable at 100%)
    "precip": "#2A7BC0",
    # the rookie "R" after a player's position (2026-09-30)
    "rookie": "#009A94",
    # the shadow behind every helmet (2026-10-04, HELMET_SHADOW_CSS): barely there on the light ground
    "helmet-shadow": "rgba(0,0,0,.1)",
}

# Dark ground in the same ink as light mode's text (#161510, a near-neutral near-black with a trace of warmth; was #1B1512 until 2026-09-30). Cards have no fill
# of their own (2026-09-30) -- same color inside as outside, like light mode -- so the outline alone
# marks them. Text is light mode's paper color
# (#F3F3EE) on the same three-step opacity ladder; status colors go one step brighter so they
# hold up on the dark ground.
DARK = dict(LIGHT, **{
    "bg": "#161510", "tile": "#161510",
    "tile-border": "rgba(243,243,238,.12)", "tile-border-soft": "rgba(243,243,238,.07)",
    "tile-hover": "rgba(243,243,238,.04)", "tile-border-hover": "rgba(243,243,238,.32)",
    "text": "#F3F3EE", "text-2": "rgba(243,243,238,.62)", "text-3": "rgba(243,243,238,.4)",
    "bar-bg": "rgba(22,21,16,.9)", "pill-hover": "rgba(243,243,238,.08)", "dot": "#433B36", "focus": "#F3F3EE",
    "out": "#FF6B6B", "doubt": "#FF8A5C", "ques": "#E8B93A",
    "win": "#4CC76E", "loss": "#FF6B6B", "tie": "#E8B93A",
    "theme-color": "#161510",
    "sw-sun": "flex", "sw-moon": "none",   # dark mode shows the sun (tap for light)
    "tc-light": "0%",
    "wx-cloud": "#8E8C89", "wx-cloud-light": "#BDBBB8", "wx-wind": "#C7D3DE",
    "wx-rain": "#7EC3F2", "wx-snow": "#FFFFFF", "wx-sun": "#F2C230",
    "precip": "#7EC3F2",
    "rookie": "#3FE0DA",
    "helmet-shadow": "rgba(0,0,0,.8)",   # much darker on the dark ground, where a faint one wouldn't show
})


# Card outlines (Page 0's game tiles and every Page 1 / Page 2 card) -- one switch.
#   False: no outlines, the cards are only their content (trial started 2026-09-30)
#   True:  the thin outlines from before, in each theme's tile-border colors
# Table rules, the Player Stats team buttons and other lines keep tile-border either way.
CARD_OUTLINES = False

for _t in (LIGHT, DARK):
    _t["card-line"] = _t["tile-border"] if CARD_OUTLINES else "transparent"
    _t["card-line-soft"] = _t["tile-border-soft"] if CARD_OUTLINES else "transparent"
    _t["card-line-hover"] = _t["tile-border-hover"] if CARD_OUTLINES else "transparent"


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

# A slight shadow behind every helmet (Jason, 2026-10-04, picked in the Helmet Shadow mock at 130%
# spread): it sits 4.55% of the helmet's size below it with 7.8% blur, so it grows with the helmet. The
# helmet images carry class "hm"; each place that sizes them sets --hs to that size (48px if not).
# It's a CSS filter on the <img>, not part of the helmet file, so iPhones keep the helmets sharp.
HELMET_SHADOW_CSS = """
img.hm{filter:drop-shadow(0 calc(var(--hs,48px) * .0455) calc(var(--hs,48px) * .078) var(--aag-helmet-shadow))}
"""

# The switch (2026-09-27): one outline icon for the theme you'd switch TO -- the moon in light
# mode, the sun in dark mode; tapping it switches. (Earlier the same day: sun and moon side by
# side, current one lit; before that, a pill toggle with a sliding knob.) Since 2026-10-07 it's
# the last line of the menu ("Dark mode" / "Light mode" beside the icon) rather than its own
# button in the bottom bar's left corner.
SWITCH_CSS = """
.ts-btn{padding:0;border:0;background:none;cursor:pointer;color:var(--aag-text);
  align-items:center;-webkit-tap-highlight-color:transparent}
.ts-btn svg{width:17px;height:17px;display:block;flex:none}
.ts-sun{display:var(--aag-sw-sun)}
.ts-moon{display:var(--aag-sw-moon)}
.ts-btn:focus-visible{outline:2px solid var(--aag-focus);outline-offset:1px;border-radius:9px}
"""

SUN = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">'
       '<circle cx="12" cy="12" r="4"/>'
       '<path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/></svg>')
MOON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/></svg>')
MENU_ICON = ('<svg viewBox="0 0 20 20" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2.2" '
             'stroke-linecap="round" aria-hidden="true"><path d="M3 5h14M3 10h14M3 15h14"/></svg>')

# The menu (Jason, 2026-10-07): three lines in the bottom bar's left corner, vertically centered on
# the same line as the week pill and the +/- toggle (both center at y=26px in the 52px bar). It opens
# a small panel up out of the bar: the site's pages, the one you're on in bold, then the light/dark
# switch. THEME_JS opens and closes it (a tap anywhere else, or Escape, closes it).
MENU_CSS = SWITCH_CSS + """
.menu-btn{position:absolute;left:7px;top:9px;width:34px;height:34px;padding:0;border:0;background:none;color:var(--aag-text);
  display:flex;align-items:center;justify-content:center;cursor:pointer;-webkit-tap-highlight-color:transparent;
  transition:transform .2s cubic-bezier(.22,1,.36,1)}
.menu-btn svg{display:block}
.menu-btn:hover{transform:scale(1.09)}
.menu-btn:active{transform:scale(1.2)}
.menu-btn:focus-visible{outline:2px solid var(--aag-focus);outline-offset:2px;border-radius:50%}
.menu{position:absolute;left:10px;bottom:56px;min-width:180px;padding:6px;border-radius:14px;background:var(--aag-bg);
  border:1px solid var(--aag-tile-border);box-shadow:0 8px 30px rgba(0,0,0,.18);display:none;text-align:left}
.menu.open{display:block}
.menu a,.menu .ts-btn{width:100%;gap:10px;padding:8px 10px;border-radius:9px;font:inherit;font-size:14px;
  line-height:19px;color:var(--aag-text);text-decoration:none}
.menu a{display:flex}
.menu a[aria-current]{font-weight:700;background:var(--aag-tile-hover)}
.menu a:hover,.menu .ts-btn:hover{background:var(--aag-pill-hover)}
.menu a:focus-visible{outline:2px solid var(--aag-focus);outline-offset:1px}
.menu hr{border:0;border-top:1px solid var(--aag-tile-border-soft);margin:6px 4px}
"""

MENU_PAGES = (("games", "Games", "index.html"), ("standings", "Standings", "standings.html"),
              ("leaders", "Stat Leaders", "leaders.html"))


def menu_html(prefix="", current=None):
    """The bottom bar's menu. prefix is the path back to the site root ("../" from site/game/);
    current is the page it's on ("games" / "standings" / "leaders"), shown in bold."""
    links = "".join(
        f'<a href="{prefix}{href}"{" aria-current=page" if key == current else ""}>{label}</a>'
        for key, label, href in MENU_PAGES)
    return (
        '<button class="menu-btn" type="button" aria-label="Menu" aria-expanded="false">' + MENU_ICON + "</button>"
        '<div class="menu" role="menu">' + links + "<hr>"
        '<button class="ts-btn ts-sun" type="button" data-pick="light">' + SUN + "<span>Light mode</span></button>"
        '<button class="ts-btn ts-moon" type="button" data-pick="dark">' + MOON + "<span>Dark mode</span></button>"
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
  // the bottom bar's menu (menu_html): one open at a time, wherever it is (a game mounted in
  // Page 0's overlay has its own, inside a shadow root)
  var openMenu = null;
  function closeMenu() {
    if (!openMenu) return;
    openMenu.classList.remove('open');
    var b = openMenu.parentNode && openMenu.parentNode.querySelector('.menu-btn');
    if (b) b.setAttribute('aria-expanded', 'false');
    openMenu = null;
  }
  document.addEventListener('click', function (e) {
    var path = e.composedPath ? e.composedPath() : [e.target], inMenu = false;
    for (var i = 0; i < path.length && path[i] !== document; i++) {
      var cl = path[i].classList;
      if (!cl) continue;
      if (cl.contains('ts-btn')) {
        e.preventDefault(); e.stopPropagation();
        var t = path[i].getAttribute('data-pick');
        if (t !== current()) choose(t);
        return;
      }
      if (cl.contains('menu-btn')) {
        e.preventDefault(); e.stopPropagation();
        var m = path[i].parentNode.querySelector('.menu'), was = m === openMenu;
        closeMenu();
        if (m && !was) { m.classList.add('open'); path[i].setAttribute('aria-expanded', 'true'); openMenu = m; }
        return;
      }
      if (cl.contains('menu')) inMenu = true;
    }
    if (!inMenu) closeMenu();
  }, true);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenu(); });
  if (mq.addEventListener) mq.addEventListener('change', sync); else if (mq.addListener) mq.addListener(sync);
  window.AAG_THEME = { sync: sync };
  sync();
})();
"""

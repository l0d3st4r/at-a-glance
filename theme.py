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

The menu (menu_html) sits in the left corner of the bottom bar on every page; it opens a pane over
the whole screen with the site's pages (Games, Standings, Stat Leaders) in big type, then the
light/dark switch as its last line (Jason, 2026-10-07 -- until then the switch had that corner to
itself). Until the switch is used the page follows
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
# The winner arrow (Jason, 2026-09-18): a small triangle pointing left, at the team that won -- beside
# FINAL on Page 0's finished tiles, and (2026-10-09) between the scores of a game page's last meeting.
# Mirrored (scaleX(-1)) to point right at the home side.
WIN_TRI = ('<svg viewBox="0 0 8 10" aria-hidden="true"><path d="M8 0 0 5l8 5z" fill="currentColor"/></svg>')

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

CLOSE_ICON = ('<svg viewBox="0 0 20 20" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2.2" '
              'stroke-linecap="round" aria-hidden="true"><path d="M4.5 4.5l11 11M15.5 4.5l-11 11"/></svg>')

# The menu (Jason, 2026-10-07): three lines in the bottom bar's left corner, vertically centered on
# the same line as the week pill and the +/- toggle (both center at y=26px in the 52px bar).
# Tapping it opens a pane over the whole screen (Jason, 2026-10-07: "a pane to cover the screen with
# a similar blur / opacity to the bottom bar") -- the bar's own tint and blur -- with the site's pages
# in big type (Saira italic, like the year and the team abbreviations) rolling up one after another
# from the bottom, near the thumb. Each page has an icon slot ahead of its name (.mnu-ic, MENU_ICONS;
# empty where none is picked); the page you're on is at full strength, the others faded. Under them, a thin
# rule and the light/dark switch, which closes the menu once it's switched. An x where the three
# lines were closes it too, as do a tap on the pane's empty space and Escape.
#
# The pane starts out inside the bottom bar (menu_html) but the first open moves it to the top of
# the page -- or of the game's shadow root on Page 0's overlay: inside the bar, the bar's own
# backdrop-filter would stop it blurring the page behind, and would pin its position:fixed to the bar.
MENU_CSS = SWITCH_CSS + """
.mnu{--mbar:var(--bbar,""" + BBAR_HEIGHT + """)}
.menu-btn{position:absolute;left:7px;top:9px;width:34px;height:34px;padding:0;border:0;background:none;color:var(--aag-text);
  display:flex;align-items:center;justify-content:center;cursor:pointer;-webkit-tap-highlight-color:transparent;
  transition:transform .2s cubic-bezier(.22,1,.36,1)}
.menu-btn svg{display:block}
.menu-btn:hover{transform:scale(1.09)}
.menu-btn:active{transform:scale(1.2)}
.menu-btn:focus-visible{outline:2px solid var(--aag-focus);outline-offset:2px;border-radius:50%}
.mnu{position:fixed;inset:0;z-index:60;background:var(--aag-bar-bg);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  color:var(--aag-text);text-align:left;visibility:hidden;opacity:0;transition:opacity .2s ease,visibility 0s linear .2s;
  -webkit-tap-highlight-color:transparent}
.mnu.open{visibility:visible;opacity:1;transition:opacity .2s ease}
.mnu-in{position:absolute;left:0;right:0;bottom:calc(var(--mbar) + 18px);max-width:600px;margin:0 auto;padding:0 24px}
.mnu-list{list-style:none}
/* each page rolls up into place, a beat after the one above it (--i) */
.mnu-list li,.mnu-foot{opacity:0;transform:translateY(18px);transition:opacity .18s ease,transform .18s ease}
.mnu.open .mnu-list li,.mnu.open .mnu-foot{opacity:1;transform:none;
  transition:opacity .32s ease calc(.06s + var(--i) * .055s),transform .42s cubic-bezier(.22,1,.36,1) calc(.06s + var(--i) * .055s)}
.mnu-list a{display:flex;align-items:center;gap:14px;padding:7px 0;color:var(--aag-text);text-decoration:none;
  font-family:Saira,Inter,system-ui,sans-serif;font-style:italic;font-weight:800;font-variation-settings:'wdth' 95;
  font-size:36px;line-height:1.05;letter-spacing:.01em;opacity:.5;transition:opacity .15s}
.mnu-list a[aria-current]{opacity:1}
/* the NFL / NBA section names (2026-10-08); six pages to a pane, so the names a size down */
.mnu-sec{font-size:11px;font-weight:700;letter-spacing:.14em;color:var(--aag-text-3);padding:10px 0 2px}
.mnu-sec:first-child{padding-top:0}
.mnu-list a{font-size:30px}
@media (max-height:640px){.mnu-list a{font-size:24px;padding:4px 0}.mnu-sec{padding-top:6px}}
.mnu-list a:hover{opacity:.85}
.mnu-list a:focus-visible{outline:2px solid var(--aag-focus);outline-offset:3px;border-radius:8px}
/* the icon ahead of each page's name, fitted inside a 40x32 box whatever its shape (empty where none is
   picked) -- a little wider than tall, so the wide Stat Leaders crowns don't come out tiny */
.mnu-ic{flex:none;width:40px;height:32px;display:flex;align-items:center;justify-content:center}
.mnu-ic svg{display:block;width:100%;height:100%;overflow:visible}   /* as render_page1's .t-ic svg */
.mnu-foot{margin-top:14px;padding-top:12px;border-top:1px solid var(--aag-tile-border)}
.mnu .ts-btn{gap:10px;padding:6px 0;font:inherit;font-size:15px;font-weight:600;color:var(--aag-text-2)}
.mnu .ts-btn svg{width:18px;height:18px}
.mnu .ts-btn:hover{color:var(--aag-text)}
/* the x sits where the menu's three lines are */
.mnu-bar{position:absolute;left:0;right:0;bottom:0;height:var(--mbar)}
.mnu-bar-in{position:relative;max-width:600px;height:52px;margin:0 auto}
.mnu-x{position:absolute;left:7px;top:9px;width:34px;height:34px;padding:0;border:0;background:none;color:var(--aag-text);
  display:flex;align-items:center;justify-content:center;cursor:pointer;transition:transform .2s cubic-bezier(.22,1,.36,1)}
.mnu-x:hover{transform:scale(1.09)}
.mnu-x:focus-visible{outline:2px solid var(--aag-focus);outline-offset:2px;border-radius:50%}
/* No focus ring after a tap (Jason, 2026-10-10): opening the menu moves focus to its first page, and
   closing it moves focus back to the three lines -- on an iPhone, where a tap doesn't focus the
   button first, the browser took that for keyboard use and ringed them in white. .mnu-tap marks a menu
   opened (or closed) by a tap or click; the keyboard -- Enter on the button, Tab, Escape -- keeps
   its rings. */
.mnu.mnu-tap :focus-visible,.menu-btn.mnu-tap:focus-visible{outline:none}
"""

MENU_PAGES = (("games", "Games", "index.html"), ("standings", "Standings", "standings.html"),
              ("leaders", "Stat Leaders", "leaders.html"))
# The menu's sections (2026-10-08): the NFL pages, then the NBA's (site/nba/, render_nba.py). Hrefs
# are from the site root; menu_html's prefix gets there from wherever the page is.
MENU_SECTIONS = (
    ("NFL", MENU_PAGES),
    ("NBA", (("nba-games", "Games", "nba/index.html"), ("nba-standings", "Standings", "nba/standings.html"),
             ("nba-leaders", "Stat Leaders", "nba/leaders.html"))),
)
# Each page's icon (SVG markup) for the slot ahead of its name. The NFL's three (Jason, 2026-10-08):
# his Games and Standings drawings -- only the paths on the drawing's canvas, cropped to their bounds
# (the files also carried a few off-canvas shapes) -- and for Stat Leaders the Leaders crown
# (render_page1.CROWN_SHAPES) drawn as an outline, between two smaller filled crowns peeking out from
# behind it. A thin gap (the mask) keeps the small crowns off the big one's outline. The NBA's Standings and
# Stat Leaders use the same two (2026-10-08); its Games has its own (below).
_CROWN = "M1.38 11.8 1 3.5l5.2 4.2L10 1l3.8 6.7L19 3.5l-.38 8.3z"
_CROWN_PILL = '<rect x="1.4" y="13" width="17.2" height="2.3" rx="1.15"/>'


def _crowns(mid):
    """The Stat Leaders crowns; mid names the mask, one per copy on a page."""
    return (
        '<svg viewBox="-9.9 0 39.8 15.5" fill="currentColor" aria-hidden="true"><defs>'
        f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="-12" y="-2" width="44" height="20">'
        '<rect x="-12" y="-2" width="44" height="20" fill="#fff"/>'
        f'<g fill="#000" stroke="#000" stroke-width="3" stroke-linejoin="round"><path d="{_CROWN}"/>{_CROWN_PILL}</g>'
        f'</mask></defs><g mask="url(#{mid})">'
        f'<g transform="translate(-10.3 5.2) scale(.66)"><path d="{_CROWN}"/>{_CROWN_PILL}</g>'
        f'<g transform="translate(17.1 5.2) scale(.66)"><path d="{_CROWN}"/>{_CROWN_PILL}</g></g>'
        f'<path d="{_CROWN}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>{_CROWN_PILL}'
        '</svg>'
    )


MENU_ICONS = {
    "games": (
        '<svg viewBox="-2000 -1972 4002 3957" fill="currentColor" aria-hidden="true"><path d="M-112.783,1037.07 '
        'C-152.357,1102.23 -189.279,1156.22 -211.926,1185.21 L1.54981,1984.24 L354.833,1253.76 L354.833,1253.76 '
        'C301.834,1226.79 238.343,1188.16 238.343,1188.16 C231.95,1180.12 224.276,1169.85 215.62,1157.71 L42.672,1554.87 '
        'L-112.783,1037.07 L-112.783,1037.07 Z M-596.427,1208.85 L-785.318,1336.22 L-733.36,1142.88 C-769.786,1124.21 '
        '-799.083,1108.1 -814.262,1098.26 C-818.757,1095.35 -823.33,1092.33 -827.965,1089.23 L-986.187,1678 '
        'L-399.495,1279.43 C-428.635,1280.02 -511.458,1247.35 -596.427,1208.85 L-596.427,1208.85 Z M-1102.41,854.005 '
        'L-1448.49,947.674 L-1287.6,751.334 C-1320.68,738.451 -1342.78,729.339 -1344.08,727.507 C-1346.03,724.767 '
        '-1362.33,695.886 -1383.85,657.955 L-1821.53,1190.07 L-992.518,966.24 C-1013.62,949.227 -1031.16,934.631 '
        '-1042.68,924.717 C-1052.72,916.079 -1077.82,886.317 -1102.41,854.005 L-1102.41,854.005 Z M-738.994,-1140.48 '
        'L-785.032,-1370.68 L-233.71,-839.514 L1.56592,-1569.61 L278.546,-917.872 L944.427,-1430.39 L861.08,-1165.54 '
        'C915.111,-1176.45 967.468,-1181.69 1016.95,-1183 L1143.09,-1780.44 L349.793,-1152.65 L1.96652,-1971.08 '
        'L-293.489,-1054.24 L-985.827,-1721.28 L-876.081,-1172.52 C-852.493,-1168.85 -828.517,-1164.15 -804.26,-1158.26 '
        'C-781.754,-1152.8 -760.01,-1146.85 -738.994,-1140.48 L-738.994,-1140.48 Z M-1541.9,-1042.67 L-1914.75,-1185.11 '
        'L-1688.6,-936.22 C-1682.52,-942.263 -1675.67,-949.101 -1667.96,-956.832 C-1652.11,-972.335 -1602.12,-1007.54 '
        '-1541.9,-1042.67 L-1541.9,-1042.67 Z M478.365,1266.82 L971.892,1675.31 L872.218,1075.46 C860.619,1083.53 '
        '849.256,1091.2 838.354,1098.26 C821.262,1109.34 786.27,1128.37 743.355,1150.05 L773.935,1334.08 L621.89,1208.23 '
        'C569.25,1232.12 517.327,1253.82 478.365,1266.82 L478.365,1266.82 Z M1048.13,940.454 L1798.2,1270.76 '
        'L1398.59,674.446 C1381.83,704.005 1369.82,725.18 1368.18,727.507 C1366.61,729.722 1334.64,742.573 '
        '1289.62,759.864 L1458.97,993.095 L1123.26,858.244 C1099.74,888.89 1076.38,916.458 1066.78,924.717 '
        'C1061.67,929.109 1055.38,934.42 1048.13,940.454 L1048.13,940.454 Z M1720.27,-928.715 L1906.87,-1184.16 '
        'L1545.1,-1054.61 C1614.4,-1015.79 1674.4,-974.098 1692.05,-956.832 C1703.14,-945.707 1712.46,-936.433 '
        '1720.27,-928.715 L1720.27,-928.715 Z M-386.127,760.595 C-296.447,790.832 -282.751,794.547 -269.911,797.347 '
        'C-338.91,931.572 -385.368,978.664 -450.85,1065.47 C-450.85,1065.47 -455.828,1065.69 -460.801,1064.36 '
        'C-465.773,1063.02 -470.741,1060.14 -470.741,1060.14 L-470.741,1060.14 C-686.488,952.444 -755.618,905.186 '
        '-893.128,800.198 C-893.128,800.198 -955.374,752.362 -958.87,748.407 C-980.741,723.667 -994.742,598.632 '
        '-998.818,582.282 C-1002.89,565.932 -996.198,561.935 -985.029,555.295 C-979.812,552.194 -972.607,544.002 '
        '-948.389,552.304 C-798.716,603.611 -440.683,740.232 -386.127,760.595 Z M-325.5,626.991 C-217.232,664.873 '
        '-212.999,666.367 -208.619,667.853 C-218.46,690.104 -227.839,710.697 -236.823,729.833 C-245.27,726.773 '
        '-258.814,721.922 -276.399,715.653 C-509.052,633.035 -774.971,539.053 -898.275,495.165 C-902.52,491.678 '
        '-867.854,473.674 -836.834,447.675 C-731.377,484.966 -471.685,575.856 -325.5,626.991 Z M-805.837,372.461 '
        'C-807.577,370.264 -809.019,367.969 -809.301,365.599 C-815.996,309.463 -821.013,248.375 -824.159,218.838 '
        'C-825.347,207.684 -835.245,195.981 -844.946,183.518 C-849.273,177.959 -953.884,93.5682 -939.383,70.8132 '
        'C-931.99,59.2135 -842.214,7.45943 -763.421,-7.61099 C-687.647,-22.104 -622.907,-0.146993 -608.136,-0.274756 '
        'C-593.46,-0.401727 -440.279,29.5684 -322.812,65.4796 C-207.73,100.662 -122.305,139.514 -95.7422,147.996 '
        'C-86.2762,151.018 -77.3616,153.884 -68.2543,144.532 C-59.1471,135.181 -62.4679,98.6754 -64.3425,86.7777 '
        'C-66.217,74.88 -61.5271,65.0495 -87.9967,52.4943 C-169.456,13.8564 -368.855,-42.1507 -376.637,-44.2377 '
        'C-509.29,-79.8181 -678.867,-86.859 -727.291,-91.0384 C-762.058,-94.0391 -768.622,-90.3026 -794.197,-81.4331 '
        'C-880.176,-51.6155 -1015.49,5.77411 -1033.72,16.0747 C-1070.12,36.6519 -1080.49,71.5714 -1043.01,106.736 '
        'C-1005.54,141.901 -937.324,205.914 -937.324,205.914 C-924.052,219.193 -922.785,216.56 -921.276,234.385 '
        'C-919.767,252.21 -912.97,369.339 -911.416,384.175 C-911.061,387.571 -911.103,392.554 -914.101,394.185 '
        'C-931.103,403.438 -1028.14,469.478 -1065.26,494.487 C-1096.6,515.61 -1106.18,530.238 -1095.55,582.299 '
        'C-1094.5,587.47 -1069.44,722.156 -1068.38,727.327 C-1062.43,756.511 -1030.6,789.455 -1008.99,808.038 '
        'C-970.034,841.552 -859.129,922.765 -777.35,975.775 C-714.936,1016.23 -499.115,1148.45 -445.177,1142.5 '
        'C-445.066,1142.51 -444.954,1142.53 -444.841,1142.54 C-416.34,1145.14 -382.419,1098.26 -382.419,1098.26 '
        'C-338.896,1043.48 -238.886,920.295 -171.159,771.728 C-155.289,736.916 -145.048,701.205 -135.174,664.437 '
        'C-127.968,646.001 -133.626,613.63 -158.508,602.548 C-162.601,600.725 -654.359,426.687 -805.837,372.461 Z '
        'M-1761.38,270.475 C-1681.7,266.775 -1567.27,276.428 -1540.52,292.18 C-1494.22,319.445 -1487.74,342.378 '
        '-1472.06,359.773 C-1455.85,377.764 -1322.75,594.919 -1317.78,602.299 C-1313.08,609.286 -1306.46,614.841 '
        '-1299.41,617.857 C-1293.94,620.194 -1150.89,675.225 -1140,677.67 C-1126.96,680.6 -1115.48,678.268 '
        '-1120.92,657.956 L-1142.38,518.92 C-1143.11,514.189 -1141.51,498.259 -1124.7,484.181 C-1124.7,484.181 '
        '-980.32,391.099 -966.895,382.443 C-953.47,373.788 -954.909,362.471 -955.476,358.209 C-958.647,334.396 '
        '-962.022,281.609 -967.494,261.167 C-975.581,230.957 -972.398,234.305 -985.162,220.769 C-1007.39,197.192 '
        '-1078.94,124.746 -1078.94,124.746 C-1100.34,102.835 -1115.91,68.125 -1114.87,50.2625 C-1113.81,32.0893 '
        '-1099.64,3.46662 -1074.53,-11.6762 C-1061.76,-19.3794 -910.24,-79.9933 -828.471,-114.858 C-795.576,-128.884 '
        '-760.192,-132.155 -755.043,-132.222 C-640.668,-133.704 -391.826,-85.0386 -364.693,-77.7608 C-261.042,-49.9598 '
        '-220.86,-36.6096 -194.281,-29.0049 C-181.267,-25.2816 -180.694,-37.3955 -167.767,-85.59 C-166.384,-90.7471 '
        '-153.461,-172.407 -152.087,-186.314 C-151.407,-193.193 -151.819,-189.029 -149.934,-208.106 C-134.578,-363.537 '
        '-278.419,-664.301 -355.956,-750.077 C-453.376,-857.849 -593.095,-982.041 -833.179,-1046.44 C-1073.26,-1110.83 '
        '-1285.03,-1041.79 -1332.22,-1028.74 C-1433.35,-1000.78 -1576.48,-911.898 -1604.38,-885.891 C-1652.08,-840.266 '
        '-1663.67,-830.574 -1664.45,-829.882 C-1708.34,-791.379 -1753.56,-747.489 -1812.23,-674.927 C-1815.77,-670.539 '
        '-1825.1,-659.544 -1829.64,-650.808 C-1841.57,-634.289 -1851.87,-614.335 -1856.52,-606.059 C-1869.97,-582.107 '
        '-1906.99,-522.892 -1910.43,-510.074 C-1915.33,-491.815 -1915.94,-489.544 -1918.32,-480.661 C-1936.75,-411.957 '
        '-1962.56,-247.147 -1973.56,-142.06 C-1983.13,-56.1068 -1983.23,-55.2836 -1983.31,-54.4718 L-1999.28,107.515 '
        'C-2001.52,131.25 -1997.03,143.687 -1985.19,151.627 L-1850.86,244.714 C-1828.38,260.713 -1785.07,270.537 '
        '-1761.38,270.475 L-1761.38,270.475 Z M387.647,760.595 C442.203,740.233 800.236,603.611 949.909,552.304 '
        'C974.127,544.002 981.331,552.194 986.549,555.295 C997.717,561.935 1004.41,565.933 1000.34,582.282 '
        'C996.262,598.632 982.261,723.667 960.39,748.407 C956.894,752.362 894.648,800.199 894.648,800.199 '
        'C757.138,905.186 688.008,952.444 472.261,1060.14 L472.261,1060.14 C472.261,1060.14 467.293,1063.02 '
        '462.32,1064.36 C457.348,1065.69 452.37,1065.47 452.37,1065.47 C386.887,978.664 340.43,931.572 271.431,797.347 '
        'C284.271,794.547 297.966,790.832 387.647,760.595 Z M327.02,626.991 C473.205,575.856 732.897,484.966 '
        '838.354,447.675 C869.374,473.674 904.04,491.678 899.795,495.165 C776.491,539.053 510.572,633.035 277.919,715.653 '
        'C260.334,721.922 246.789,726.773 238.343,729.833 C229.358,710.697 219.979,690.104 210.139,667.853 '
        'C214.519,666.367 218.751,664.873 327.02,626.991 Z M807.357,372.461 C655.879,426.687 164.12,600.725 '
        '160.028,602.548 C135.146,613.63 129.488,646.001 136.694,664.437 C146.568,701.205 156.808,736.916 172.678,771.728 '
        'C240.405,920.295 340.416,1043.48 383.939,1098.26 C383.939,1098.26 417.86,1145.14 446.361,1142.54 '
        'C446.474,1142.53 446.586,1142.51 446.697,1142.5 C500.635,1148.45 716.456,1016.23 778.87,975.775 C860.649,922.765 '
        '971.554,841.552 1010.51,808.038 C1032.12,789.455 1063.95,756.511 1069.9,727.327 C1070.96,722.156 1096.02,587.47 '
        '1097.07,582.299 C1107.7,530.238 1098.12,515.61 1066.78,494.487 C1029.66,469.478 932.623,403.438 915.621,394.185 '
        'C912.622,392.554 912.58,387.571 912.936,384.175 C914.49,369.339 921.287,252.21 922.796,234.385 C924.305,216.56 '
        '925.572,219.193 938.844,205.914 C938.844,205.914 1007.06,141.901 1044.53,106.736 C1082.01,71.5714 '
        '1071.64,36.6519 1035.24,16.0747 C1017.01,5.7741 881.696,-51.6155 795.717,-81.433 C770.142,-90.3026 '
        '763.577,-94.0391 728.811,-91.0385 C680.386,-86.859 510.81,-79.8181 378.156,-44.2377 C370.375,-42.1507 '
        '170.975,13.8564 89.5165,52.4943 C63.0469,65.0495 67.7369,74.88 65.8623,86.7777 C63.9877,98.6754 60.6669,135.181 '
        '69.7742,144.532 C78.8814,153.884 87.796,151.018 97.2621,147.996 C123.825,139.514 209.25,100.662 324.332,65.4796 '
        'C441.799,29.5684 594.98,-0.401719 609.656,-0.274755 C624.427,-0.146987 689.166,-22.104 764.941,-7.611 '
        'C843.734,7.45943 933.51,59.2135 940.902,70.8132 C955.404,93.5682 850.793,177.959 846.465,183.519 '
        'C836.764,195.981 826.867,207.684 825.679,218.838 C822.533,248.375 817.516,309.463 810.821,365.599 '
        'C810.538,367.969 809.097,370.264 807.357,372.461 Z M1762.9,270.475 L1762.9,270.475 C1786.59,270.537 '
        '1829.9,260.713 1852.38,244.714 L1986.71,151.627 C1998.55,143.687 2003.04,131.25 2000.8,107.515 L1984.83,-54.4718 '
        'C1984.75,-55.2837 1984.65,-56.1068 1975.08,-142.06 C1964.08,-247.148 1938.27,-411.957 1919.84,-480.661 '
        'C1917.46,-489.544 1916.85,-491.815 1911.95,-510.074 C1908.51,-522.892 1871.49,-582.107 1858.04,-606.059 '
        'C1853.39,-614.335 1843.09,-634.289 1831.16,-650.808 C1826.62,-659.544 1817.29,-670.539 1813.75,-674.927 '
        'C1755.08,-747.489 1709.86,-791.379 1665.97,-829.882 C1665.19,-830.574 1653.6,-840.266 1605.9,-885.891 '
        'C1578,-911.898 1434.87,-1000.78 1333.74,-1028.74 C1286.54,-1041.79 1074.78,-1110.83 834.699,-1046.44 '
        'C594.614,-982.041 454.896,-857.849 357.476,-750.077 C279.939,-664.301 136.098,-363.537 151.454,-208.106 '
        'C153.339,-189.029 152.927,-193.193 153.607,-186.314 C154.981,-172.407 167.904,-90.7471 169.287,-85.59 '
        'C182.213,-37.3956 182.787,-25.2816 195.8,-29.0049 C222.38,-36.6096 262.562,-49.9598 366.212,-77.7608 '
        'C393.346,-85.0386 642.187,-133.704 756.563,-132.222 C761.711,-132.155 797.095,-128.884 829.991,-114.858 '
        'C911.76,-79.9933 1063.28,-19.3795 1076.05,-11.6762 C1101.16,3.46661 1115.33,32.0892 1116.39,50.2625 '
        'C1117.43,68.125 1101.86,102.835 1080.46,124.746 C1080.46,124.746 1008.91,197.192 986.682,220.769 '
        'C973.918,234.305 977.101,230.957 969.014,261.167 C963.542,281.609 960.166,334.396 956.996,358.209 '
        'C956.428,362.471 954.99,373.788 968.415,382.443 C981.84,391.099 1126.22,484.181 1126.22,484.181 C1143.03,498.259 '
        '1144.63,514.189 1143.9,518.92 L1122.44,657.956 C1117,678.268 1128.48,680.6 1141.52,677.67 C1152.4,675.225 '
        '1295.46,620.194 1300.93,617.857 C1307.97,614.841 1314.6,609.286 1319.3,602.299 C1324.27,594.919 1457.37,377.764 '
        '1473.58,359.773 C1489.26,342.378 1495.74,319.445 1542.04,292.18 C1568.79,276.428 1683.22,266.775 1762.9,270.475 '
        'Z"/></svg>'
    ),
    "standings": (
        '<svg viewBox="-1922 -1909 3844 2742" fill="currentColor" aria-hidden="true"><path d="M-1921.37,-1492.5 '
        'C-1921.37,-1263.6 -1734.47,-1076.7 -1505.58,-1076.7 L1505.58,-1076.7 C1734.47,-1076.7 1921.37,-1263.6 '
        '1921.37,-1492.5 C1921.37,-1721.39 1734.47,-1908.29 1505.58,-1908.29 L-1505.58,-1908.29 C-1734.47,-1908.29 '
        '-1921.37,-1721.39 -1921.37,-1492.5 Z M-1159.43,-1492.5 C-1159.43,-1318.3 -1300.64,-1177.09 -1474.83,-1177.09 '
        'C-1649.02,-1177.09 -1790.23,-1318.3 -1790.23,-1492.5 C-1790.23,-1666.69 -1649.02,-1807.9 -1474.83,-1807.9 '
        'C-1300.64,-1807.9 -1159.43,-1666.69 -1159.43,-1492.5 Z"/><path d="M-1201.57,415.794 C-1201.57,644.691 '
        '-1014.67,831.588 -785.773,831.588 L1473.56,831.588 C1702.46,831.588 1889.36,644.691 1889.36,415.794 '
        'C1889.36,186.897 1702.46,-2.27374e-13 1473.56,-2.27374e-13 L-785.773,-2.27374e-13 C-1014.67,-2.27374e-13 '
        '-1201.57,186.897 -1201.57,415.794 Z M-1081.12,415.794 C-1081.12,239.801 -937.415,96.0997 -761.422,96.0997 '
        'L1449.21,96.0997 C1625.2,96.0997 1768.91,239.801 1768.91,415.794 C1768.91,591.787 1625.2,735.488 1449.21,735.488 '
        'L-761.422,735.488 C-937.415,735.488 -1081.12,591.787 -1081.12,415.794 Z"/><path d="M-1201.57,-538.351 '
        'C-1201.57,-309.454 -1014.67,-122.557 -785.773,-122.557 L1473.56,-122.557 C1702.46,-122.557 1889.36,-309.454 '
        '1889.36,-538.351 C1889.36,-767.248 1702.46,-954.145 1473.56,-954.145 L-785.773,-954.145 C-1014.67,-954.145 '
        '-1201.57,-767.248 -1201.57,-538.351 Z M-1081.12,-538.351 C-1081.12,-714.344 -937.415,-858.045 -761.422,-858.045 '
        'L1449.21,-858.045 C1625.2,-858.045 1768.91,-714.344 1768.91,-538.351 C1768.91,-362.358 1625.2,-218.657 '
        '1449.21,-218.657 L-761.422,-218.657 C-937.415,-218.657 -1081.12,-362.358 -1081.12,-538.351 Z"/><path '
        'd="M-1305.99,-1264.24 L-1365.65,-1460.76 L-1201.57,-1585.28 L-1407.81,-1589.82 L-1475.26,-1784.39 '
        'L-1542.71,-1589.82 L-1748.95,-1585.28 L-1584.86,-1460.76 L-1644.53,-1264.24 L-1475.26,-1381.63 '
        'L-1305.99,-1264.24 Z"/><path d="M-830.226,-422.099 C-856.338,-376.57 -823.53,-320.996 -772.644,-320.327 '
        'L-424.474,-320.327 C-372.249,-320.327 -339.441,-376.57 -365.553,-421.43 L-539.638,-722.73 C-565.081,-767.591 '
        '-630.028,-767.591 -656.141,-722.73 L-830.226,-422.099 Z"/><path d="M1539.19,299.542 C1565.31,254.012 '
        '1532.5,198.439 1481.61,197.77 L1133.44,197.77 C1081.22,197.77 1048.41,254.012 1074.52,298.873 L1248.61,600.173 '
        'C1274.05,645.033 1339,645.033 1365.11,600.173 L1539.19,299.542 Z"/></svg>'
    ),
    "leaders": _crowns("mnu-crowns"),
}
# The NBA's Games (Jason, 2026-10-10): his basketball between two hands -- only the paths on the
# drawing's canvas (the file carried twelve more off it; one more was a copy under the left hand),
# cropped to their bounds (getBBox()), coordinates rounded (a unit is a hundredth of a pixel here).
MENU_ICONS["nba-games"] = (
    '<svg viewBox="-1461 -1577 2741 3258" fill="currentColor" aria-hidden="true"><path d="M-233,1441 C-251,1395 '
    '-268,1346 -289,1300 C-367,1120 -401,699 -383,550 C-371,450 -363,466 -342,397 C-340,390 -338,383 -335,374 '
    'C-413,348 -487,312 -556,269 C-567,300 -583,316 -604,306 C-610,301 -619,268 -630,217 C-743,132 -837,24 -907,-100 '
    'C-880,118 -851,356 -844,384 C-834,426 -983,97 -1042,-86 C-1101,-269 -1145,-382 -1226,-369 C-1293,-358 '
    '-1236,-194 -1125,256 C-1099,364 -995,613 -1065,619 C-1087,633 -1188,402 -1246,266 C-1303,129 -1303,129 -1346,27 '
    'C-1399,-98 -1486,-29 -1454,113 C-1337,534 -1244,732 -1140,954 C-912,1441 -823,1620 -734,1585 C-469,1482 '
    '-433,1429 -233,1441 Z"/><path d="M-313,300 C-289,225 -253,139 -201,125 C-141,108 -73,150 -29,230 L-29,-1120 '
    'C-85,-1119 -141,-1114 -197,-1103 C-193,-1081 -191,-1057 -192,-1034 C-194,-971 -208,-921 -233,-877 C-235,-872 '
    '-238,-867 -241,-863 L-241,-863 C-293,-779 -376,-720 -458,-645 L-458,-645 C-559,-551 -668,-356 -674,-132 '
    'C-675,-34 -659,53 -646,104 C-550,190 -438,258 -313,300 L-313,300 Z M613,-500 C575,-575 529,-636 484,-678 '
    'L484,-678 C402,-752 319,-812 267,-895 L267,-895 C264,-900 261,-905 259,-909 C235,-953 221,-1004 218,-1066 '
    'C218,-1075 218,-1085 218,-1094 C156,-1109 93,-1117 30,-1120 L30,233 C32,226 35,217 38,204 C48,158 102,-156 '
    '137,-287 C202,-528 336,-576 422,-549 C575,-501 516,-407 514,-355 C514,-324 506,-307 535,-399 C549,-445 578,-479 '
    '613,-500 L613,-500 Z M934,-363 C953,-440 964,-520 964,-604 C747,-851 520,-1006 285,-1076 C286,-1073 286,-1069 '
    '286,-1066 L286,-1066 C286,-1063 286,-1060 287,-1057 C291,-1014 304,-970 327,-930 L327,-930 C374,-849 453,-784 '
    '526,-714 L526,-714 C578,-661 627,-596 666,-521 C761,-544 867,-489 854,-355 C841,-216 842,-232 831,-186 '
    'C828,-184 864,-300 934,-363 L934,-363 Z M-29,-1576 C-244,-1570 -442,-1493 -599,-1368 C-546,-1362 -446,-1345 '
    '-359,-1308 L-359,-1308 C-291,-1285 -243,-1234 -216,-1171 C-154,-1183 -91,-1189 -29,-1191 L-29,-1576 L-29,-1576 '
    'Z M568,-1392 C416,-1503 231,-1570 30,-1576 L30,-1190 C97,-1188 163,-1180 229,-1166 C251,-1246 304,-1313 '
    '385,-1340 L385,-1340 C447,-1367 515,-1383 568,-1392 Z M-657,-1318 C-809,-1177 -915,-987 -951,-773 C-736,-972 '
    '-509,-1100 -281,-1157 C-302,-1202 -337,-1239 -387,-1258 L-387,-1258 C-516,-1305 -627,-1320 -657,-1318 Z '
    'M-963,-649 C-964,-637 -964,-624 -964,-612 C-964,-366 -872,-142 -721,28 C-726,-11 -730,-57 -729,-104 C-738,-339 '
    '-631,-549 -500,-682 L-500,-682 C-427,-752 -348,-816 -301,-897 L-301,-897 C-278,-938 -264,-982 -260,-1025 '
    'C-260,-1028 -260,-1031 -260,-1034 L-260,-1034 C-259,-1052 -259,-1071 -262,-1089 C-501,-1029 -739,-882 -963,-649 '
    'L-963,-649 Z M957,-737 C926,-980 804,-1195 627,-1346 C575,-1339 498,-1322 413,-1290 L413,-1291 C349,-1266 '
    '309,-1213 293,-1150 C524,-1087 748,-949 957,-737 Z"/><path d="M54,487 C61,463 76,374 122,204 C167,34 192,-147 '
    '227,-278 C292,-519 369,-463 404,-450 C463,-430 383,-42 372,204 C366,329 357,399 404,377 C429,353 522,-179 '
    '624,-401 C668,-497 797,-445 786,-353 C768,-214 673,428 662,475 C652,517 778,180 838,-3 C897,-186 962,-314 '
    '1043,-300 C1111,-290 1054,-104 943,346 C917,455 813,703 883,710 C905,724 1006,493 1064,356 C1121,220 1122,219 '
    '1164,118 C1217,-7 1304,61 1272,204 C1155,625 1062,823 958,1045 C730,1532 641,1710 552,1676 C276,1568 249,1515 '
    '24,1534 C-131,1547 -137,1369 -215,1189 C-294,1009 -303,686 -285,537 C-272,437 -255,445 -234,377 C-214,308 '
    '-218,242 -177,220 C-147,203 -36,306 -42,455 C-48,605 -42,727 -42,727 C-42,727 -17,667 54,487 Z M137,550 C66,730 '
    '-73,905 -73,905 C-73,905 -145,668 -130,537 C-114,407 -139,360 -152,369 C-162,376 -171,435 -177,455 C-184,476 '
    '-185,471 -196,550 C-226,778 -146,1097 -105,1203 C-65,1310 -8,1428 47,1421 C223,1398 230,1469 516,1551 C565,1565 '
    '624,1520 853,1033 C905,922 997,798 1043,693 C1090,587 1103,537 1172,318 C1233,132 1207,139 1142,309 C1103,412 '
    '1101,401 1043,537 C986,674 898,886 825,836 C740,769 835,438 866,331 C955,21 1004,-115 983,-122 C948,-133 '
    '819,302 803,343 C787,383 703,575 676,609 C663,625 594,680 583,589 C569,480 587,502 600,331 C613,159 685,-193 '
    '692,-243 C704,-335 683,-345 654,-243 C585,7 452,489 422,515 C321,598 272,345 286,221 C314,-21 361,-314 333,-323 '
    'C312,-330 302,-223 286,-146 C258,-13 257,51 216,221 C175,391 144,526 137,550 Z"/></svg>'
)
MENU_ICONS["nba-standings"] = MENU_ICONS["standings"]
MENU_ICONS["nba-leaders"] = _crowns("mnu-crowns-nba")


def menu_html(prefix="", current=None):
    """The bottom bar's menu button, and the pane it opens. prefix is the path back to the site root
    ("../" from site/game/ or site/nba/, "../../" from site/nba/game/); current is the page it's on
    ("games" / "standings" / "leaders", "nba-games" / "nba-standings" / "nba-leaders")."""
    items, i = [], 0
    for name, pages in MENU_SECTIONS:
        items.append(f'<li class="mnu-sec" style="--i:{i}">{name}</li>')
        i += 1
        for key, label, href in pages:
            items.append(f'<li style="--i:{i}"><a href="{prefix}{href}"{" aria-current=page" if key == current else ""}>'
                         f'<span class="mnu-ic" aria-hidden="true">{MENU_ICONS.get(key, "")}</span><span>{label}</span></a></li>')
            i += 1
    return (
        '<button class="menu-btn" type="button" aria-label="Menu" aria-expanded="false">' + MENU_ICON + "</button>"
        '<div class="mnu" role="dialog" aria-modal="true" aria-label="Menu"><div class="mnu-in">'
        '<ul class="mnu-list">' + "".join(items) + "</ul>"
        f'<div class="mnu-foot" style="--i:{i}">'
        '<button class="ts-btn ts-sun" type="button" data-pick="light">' + SUN + "<span>Light mode</span></button>"
        '<button class="ts-btn ts-moon" type="button" data-pick="dark">' + MOON + "<span>Dark mode</span></button>"
        "</div></div>"
        '<div class="mnu-bar"><div class="mnu-bar-in"><button class="mnu-x" type="button" aria-label="Close menu">'
        + CLOSE_ICON + "</button></div></div></div>"
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
  var open = null;   // { pane, btn }
  function paneFor(btn) {
    if (!btn._mnu) {
      // the first time: move the pane out of the bar to the top of its page (or shadow root) --
      // inside the bar, the bar's backdrop-filter would stop it blurring the page and pin it to the bar
      var pane = btn.parentNode.querySelector('.mnu'), root = btn.getRootNode();
      (root === document ? document.body : root).appendChild(pane);
      // touches on the pane stay on the pane (no swiping the weeks or pulling to refresh underneath)
      ['touchstart', 'touchmove'].forEach(function (k) { pane.addEventListener(k, function (e) { e.stopPropagation(); }, { passive: true }); });
      btn._mnu = pane;
      btn.addEventListener('blur', function () { btn.classList.remove('mnu-tap'); });
    }
    return btn._mnu;
  }
  // ptr: opened / closed by a tap or click (a click's detail counts its presses; Enter or Space on a
  // button clicks with 0) -- no focus rings then (MENU_CSS's .mnu-tap; Page 0's .ptr is its pull-to-refresh)
  function openMenu(btn, ptr) {
    var pane = paneFor(btn);
    void pane.offsetWidth;   // a fresh frame, so the roll-up plays the first time too
    pane.classList.toggle('mnu-tap', !!ptr);
    pane.classList.add('open'); btn.setAttribute('aria-expanded', 'true');
    open = { pane: pane, btn: btn };
    var first = pane.querySelector('a[aria-current]') || pane.querySelector('a');
    if (first) first.focus({ preventScroll: true });
  }
  function closeMenu(refocus, ptr) {
    if (!open) return;
    open.pane.classList.remove('open'); open.btn.setAttribute('aria-expanded', 'false');
    if (refocus) { open.btn.classList.toggle('mnu-tap', !!ptr); open.btn.focus({ preventScroll: true }); }
    open = null;
  }
  document.addEventListener('click', function (e) {
    var path = e.composedPath ? e.composedPath() : [e.target], ptr = e.detail > 0;
    for (var i = 0; i < path.length && path[i] !== document; i++) {
      var cl = path[i].classList;
      if (!cl) continue;
      if (cl.contains('ts-btn')) {
        // switching light / dark closes the menu (Jason, 2026-10-07)
        e.preventDefault(); e.stopPropagation();
        var t = path[i].getAttribute('data-pick');
        if (t !== current()) choose(t);
        closeMenu(true, ptr);
        return;
      }
      if (cl.contains('menu-btn')) {
        e.preventDefault(); e.stopPropagation();
        if (open && open.btn === path[i]) closeMenu(true, ptr); else { closeMenu(); openMenu(path[i], ptr); }
        return;
      }
      if (cl.contains('mnu-x')) { e.preventDefault(); e.stopPropagation(); closeMenu(true, ptr); return; }
      if (path[i].tagName === 'A' && open && open.pane.contains(path[i])) return;   // a page: follow it
      if (cl.contains('mnu')) { e.preventDefault(); e.stopPropagation(); closeMenu(true, ptr); return; }   // the pane's empty space
    }
  }, true);
  // Escape closes the menu -- and only the menu, if it's open (Page 1 uses Escape too); Tab in a
  // tapped-open menu brings its focus rings back
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && open) { e.stopPropagation(); closeMenu(true); }
    else if (e.key === 'Tab' && open) open.pane.classList.remove('mnu-tap');
  }, true);
  if (mq.addEventListener) mq.addEventListener('change', sync); else if (mq.addListener) mq.addListener(sync);
  window.AAG_THEME = { sync: sync };
  sync();
})();
"""

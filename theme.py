"""
Shared design tokens -- the color/border values that Page 0's stylesheet
(render_html.py's PAGE0_CSS) and Page 1's stylesheet (render_page1.py's
P1_CSS) both declare as CSS custom properties. Change a color here once
instead of hunting down every place it's hardcoded.

Page 1 has to declare its own copy of these as CSS custom properties (it
can't just inherit Page 0's) because site/game/<id>.html also has to work
as a standalone page with no Page 0 wrapper around it -- opened directly,
or shared as a link. Page 2 (render_page2gameinfo.py) lives inside Page 1's
own markup, so it inherits Page 1's custom properties for free and needs
no copy here.
"""

BG = "#fff"
TEXT = "#000"
TEXT_2 = "rgba(0,0,0,.62)"
TEXT_3 = "rgba(0,0,0,.4)"
TILE = "#fff"
TILE_BORDER = "rgba(0,0,0,.12)"
TILE_HOVER = "rgba(0,0,0,.03)"
TILE_BORDER_HOVER = "rgba(0,0,0,.28)"
BBAR_HEIGHT = "calc(52px + env(safe-area-inset-bottom))"

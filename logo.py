"""
The site's logo (Jason's field-and-eye mark, "sports - at a glance.svg", 2026-10-08) and the favicons
and home-screen icons made from it. Picked in the At A Glance Logo artifact:

  browser tabs   flat: the site's ink (#161510) on a light tab, its paper (#F3F3EE) on a dark one --
                 options A and B. favicon.svg switches by itself with the browser's theme; browsers
                 that only take a PNG get favicon-32.png, or favicon-dark-32.png when they honor the
                 link's dark-mode media query.
  home screen    glass, after iOS's Liquid Glass: a see-through fill, a bright rim where light catches
                 the top-left edge, a soft sheen across the top and a shadow underneath -- smoked glass
                 in the site's ink on paper for light (D), clear glass on ink for dark (C).

Only the paths on the source file's 4096 canvas are kept (it also carried a spare eye and a dot off to
the side). The drawing's own bounds: x -1870..1870, y -1423..1423.

The icons are for the whole site, NFL and NBA alike: every page's <head> takes favicon_links(), and
write_icons() puts the files at the site's root, where every page's links point. Both builds call it
(render_html.py and render_nba.py), so either section has its icons even if the other's build failed.
check_build.py fails the build if any page is missing the links, so a new page can't ship without them.

The build has no SVG rasterizer, so the PNGs are committed in assets/ (see assets/README.md): re-render
them from favicon_png_svg() and home_icon_svg() if the artwork changes.
"""

import os
import shutil

INK, PAPER = "#161510", "#F3F3EE"

PATHS = (
    # the field: border, end boxes
    "M1869.84,837.031 L1869.84,-837.031 L1869.84,-974.406 C1869.84,-1219.98 1671.65,-1422.48 1421.77,-1422.48 L-1421.77,-1422.48 C-1667.35,-1422.48 -1869.84,-1224.29 -1869.84,-974.406 L-1869.84,-837.031 L-1869.84,-837.031 L-1869.84,837.031 L-1869.84,974.406 C-1869.84,1219.98 -1671.65,1422.48 -1421.77,1422.48 L1421.77,1422.48 C1667.35,1422.48 1865.53,1219.98 1869.84,978.714 L1869.84,837.031 L1869.84,837.031 Z M1624.82,-837.031 L1344.36,-837.031 C1234.3,-837.031 1143.55,-748.211 1143.55,-636.221 L1143.55,636.221 C1143.55,746.28 1232.37,837.031 1344.36,837.031 L1624.82,837.031 L1624.82,974.406 C1624.82,1077.93 1543.15,1212.17 1421.77,1212.17 L-1421.77,1212.17 C-1517.42,1212.17 -1635.1,1075.45 -1635.1,974.406 L-1634.37,837.031 L-1344.36,837.031 C-1234.3,837.031 -1145.48,746.28 -1143.55,638.152 L-1143.55,-636.221 C-1143.55,-746.28 -1232.37,-837.031 -1344.36,-837.031 L-1625.55,-837.031 L-1624.82,-974.406 C-1624.82,-1086.83 -1519.94,-1212.17 -1421.77,-1212.17 L1421.77,-1212.17 C1517.32,-1212.17 1624.82,-1092.75 1624.82,-974.406 L1624.82,-837.031 L1624.82,-837.031 Z",
    # the center line, top half
    "M87,-554.478 L87,-1422.48 L-86,-1422.48 L-86,-554.478 L87,-554.478 Z",
    # the center line, bottom half
    "M87,1422.48 L87,554.478 L-86,554.478 L-86,1422.48 L87,1422.48 Z",
    # the eye, with the iris cut out
    "M0.5,-593.574 C-358.526,-593.574 -681.222,-375.813 -926.984,0 C-683.359,361.764 -356.389,593.574 0.5,593.574 C357.389,593.574 682.222,372.301 927.984,0 C684.359,-361.764 355.252,-593.574 0.5,-593.574 Z M-20.1934,481.984 C-286.553,481.984 -502.178,266.36 -502.178,-1.21478e-12 C-502.178,-266.36 -286.553,-481.984 -20.1934,-481.984 C246.166,-481.984 461.791,-266.36 461.791,-1.21478e-12 C461.791,266.36 246.166,481.984 -20.1934,481.984 Z",
    # the pupil
    "M-20.1934,315.248 C154.023,315.248 295.055,174.216 295.055,-4.26326e-14 C295.055,-174.216 154.023,-315.248 -20.1934,-315.248 C-194.41,-315.248 -335.442,-174.216 -335.442,-4.26326e-14 C-335.442,174.216 -194.41,315.248 -20.1934,315.248 Z",
)

_W, _H = 3740, 2846            # the drawing's width and height
_LOGO = "".join(f'<path d="{d}"/>' for d in PATHS)

# The glass, per option: its color (opaque stops, top-left to bottom-right), how see-through it is at the
# top-left and bottom-right, and its shadow. The color is painted through a mask of the whole logo, so
# where the drawing's pieces overlap (the center line over the border) the glass doesn't double up.
GLASS = {
    "clear": {"tint": ("#FFFFFF", "#FFFFFF"), "alpha": (.72, .22), "shadow": ("#000000", .55)},
    "smoke": {"tint": (INK, INK), "alpha": (.82, .48), "shadow": (INK, .28)},
}


def _square(pad):
    """A square viewBox around the drawing, `pad` units clear of its widest side."""
    half = _W / 2 + pad
    return f"{-half:g} {-half:g} {2 * half:g} {2 * half:g}"


def favicon_svg():
    """Options A and B in one file: ink, or paper when the browser is in dark mode."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_square(20)}">'
            f'<style>g{{fill:{INK}}}@media (prefers-color-scheme:dark){{g{{fill:{PAPER}}}}}</style>'
            f"<g>{_LOGO}</g></svg>")


def favicon_png_svg(dark=False):
    """The PNG favicons' source: A, or B for dark tabs, without the media query."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_square(20)}">'
            f'<g fill="{PAPER if dark else INK}">{_LOGO}</g></svg>')


def glass_svg(kind, uid="g"):
    """The logo in glass (no ground): "clear" (C, for dark) or "smoke" (D, for light), in its own bounds
    plus room for the rim and shadow."""
    g = GLASS[kind]
    t0, t1 = g["tint"]
    a0, a1 = (round(a * 255) for a in g["alpha"])
    sc, so = g["shadow"]
    diag = 'gradientUnits="userSpaceOnUse" x1="-1500" y1="-1423" x2="1500" y2="1423"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1990 -1543 3980 3086"><defs>'
        f'<g id="{uid}-l">{_LOGO}</g>'
        f'<clipPath id="{uid}-c"><use href="#{uid}-l"/></clipPath>'
        f'<linearGradient id="{uid}-t" {diag}><stop offset="0" stop-color="{t0}"/><stop offset="1" stop-color="{t1}"/></linearGradient>'
        f'<linearGradient id="{uid}-a" {diag}><stop offset="0" stop-color="rgb({a0},{a0},{a0})"/>'
        f'<stop offset="1" stop-color="rgb({a1},{a1},{a1})"/></linearGradient>'
        f'<mask id="{uid}-m" maskUnits="userSpaceOnUse" x="-1990" y="-1543" width="3980" height="3086">'
        f'<use href="#{uid}-l" fill="url(#{uid}-a)"/></mask>'
        # the rim: light catching the top-left edge, a fainter return on the bottom-right
        f'<linearGradient id="{uid}-r" gradientUnits="userSpaceOnUse" x1="-1870" y1="-1423" x2="1870" y2="1423">'
        '<stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".42" stop-color="#fff" stop-opacity=".10"/>'
        '<stop offset=".72" stop-color="#fff" stop-opacity=".06"/><stop offset="1" stop-color="#fff" stop-opacity=".6"/></linearGradient>'
        # the sheen: a soft highlight across the upper half
        f'<linearGradient id="{uid}-s" gradientUnits="userSpaceOnUse" x1="0" y1="-1423" x2="0" y2="100">'
        '<stop offset="0" stop-color="#fff" stop-opacity=".42"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<filter id="{uid}-d" x="-10%" y="-10%" width="120%" height="125%">'
        f'<feDropShadow dx="0" dy="45" stdDeviation="45" flood-color="{sc}" flood-opacity="{so}"/></filter>'
        "</defs>"
        f'<g filter="url(#{uid}-d)"><rect x="-1990" y="-1543" width="3980" height="3086" fill="url(#{uid}-t)" mask="url(#{uid}-m)"/></g>'
        f'<g clip-path="url(#{uid}-c)"><rect x="-1900" y="-1450" width="3800" height="1550" fill="url(#{uid}-s)"/>'
        f'<use href="#{uid}-l" fill="none" stroke="url(#{uid}-r)" stroke-width="64"/></g>'
        "</svg>"
    )


def home_icon_svg(dark=False, size=180):
    """The iPhone home-screen icon's source: a full square (iOS rounds the corners itself) in the site's
    paper with the smoked glass, or its ink with the clear glass. The logo spans 70% of the width."""
    w = size * .70
    h = w * 3086 / 3980
    inner = glass_svg("clear" if dark else "smoke", "h").replace('<svg xmlns="http://www.w3.org/2000/svg" ',
                                                                    f'<svg x="{(size - w) / 2:g}" y="{(size - h) / 2:g}" width="{w:g}" height="{h:g}" ')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="{INK if dark else PAPER}"/>{inner}</svg>')


# committed in assets/, copied into site/
FAVICON_PNGS = ("favicon-32.png", "favicon-dark-32.png", "apple-touch-icon.png", "apple-touch-icon-dark.png")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def write_icons(site_dir):
    """favicon.svg and the committed PNGs, at the root of the site (site_dir)."""
    os.makedirs(site_dir, exist_ok=True)
    with open(os.path.join(site_dir, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(favicon_svg())
    for name in FAVICON_PNGS:
        src = os.path.join(ASSETS_DIR, name)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(site_dir, name))


def favicon_links(prefix=""):
    """<head> tags; prefix is the path back to the site root ("../" from site/game/). The dark versions
    carry a media query; a browser that ignores it uses the light one listed before it."""
    return (f"<link rel='icon' href='{prefix}favicon-32.png' type='image/png' sizes='32x32'>"
            f"<link rel='icon' href='{prefix}favicon-dark-32.png' type='image/png' sizes='32x32' media='(prefers-color-scheme: dark)'>"
            f"<link rel='icon' href='{prefix}favicon.svg' type='image/svg+xml'>"
            f"<link rel='apple-touch-icon' href='{prefix}apple-touch-icon.png'>"
            f"<link rel='apple-touch-icon' href='{prefix}apple-touch-icon-dark.png' media='(prefers-color-scheme: dark)'>")

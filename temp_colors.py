"""
Temperature colors (added 2026-09-29): every temperature number on the site is colored by
Jason's scale -- deep indigo at -40° through blue, sky, green-yellow and orange to dark red at
130° (the reference image's color bar, sampled every few pixels and mapped to degrees by its
labels 130 / 90 / 60 / 30 / 0 / -40, which sit evenly spaced even though the degrees between
them aren't). Colors blend smoothly between those samples, one shade per degree.

Two shades per temperature, because the pages have two themes:
  * dark  -- the scale's own color, except that the deepest indigos and darkest reds are
             lightened just enough to read on the dark cards (they're near-invisible otherwise)
  * light -- the same hue darkened until it reads on white (the scale's yellows and sky blues
             are too pale as text there)
Both are held to a 3:1 contrast with their card color, the standard for large bold text,
which every temperature on the site is.

The pages carry both on the number (tc_attrs) and CSS picks one per theme through the
--aag-tc-light token (theme.py) -- a token rather than a [data-theme] selector, so it also
reaches the games Page 0 opens inside a shadow root (see theme.py's docstring).
"""

import colorsys

# (degrees F, color), coldest first -- sampled from the reference scale
STOPS = [
    (-40.0, "#3E2A89"), (-39.4, "#3F2C8D"), (-35.8, "#4839A1"), (-32.2, "#4F47B6"), (-28.7, "#5654CB"),
    (-25.1, "#5358D1"), (-21.5, "#4E5BD4"), (-17.9, "#495DD6"), (-14.3, "#4660D9"), (-10.7, "#4262DD"),
    (-7.2, "#3D65E0"), (-3.6, "#3B68E3"), (0.0, "#396BE6"), (2.6, "#376EE9"), (5.3, "#3570ED"),
    (7.9, "#3574F1"), (10.6, "#3476F4"), (13.2, "#3880F4"), (15.9, "#428BF6"), (18.5, "#4C97F4"),
    (21.2, "#57A4F4"), (23.8, "#63B0F5"), (26.5, "#70BCF5"), (29.1, "#79C6F1"), (31.8, "#7AC8ED"),
    (34.5, "#7DCAE5"), (37.2, "#7ECBE1"), (39.9, "#80CED9"), (42.5, "#82CFD4"), (45.2, "#84D1CA"),
    (47.9, "#8CD1BC"), (50.6, "#93D0AD"), (53.3, "#9DD0A0"), (56.0, "#A6CF8F"), (58.7, "#AFCF83"),
    (61.3, "#B8CF74"), (64.0, "#C7CE63"), (66.7, "#D4CE57"), (69.4, "#E6CE49"), (72.1, "#F5CD49"),
    (74.8, "#F4C244"), (77.5, "#F3B641"), (80.1, "#F0AA3C"), (82.8, "#F29C3C"), (85.5, "#EF8A37"),
    (88.2, "#ED7836"), (91.2, "#EB6438"), (94.7, "#E9533D"), (98.2, "#E44B3B"), (101.8, "#D94637"),
    (105.3, "#CF4232"), (108.8, "#C53D2F"), (112.4, "#BB392B"), (115.9, "#B13427"), (119.4, "#A62F24"),
    (122.9, "#9C2B1F"), (126.5, "#91271B"), (130.0, "#882217"),
]
LIGHT_CARD, DARK_CARD = "#FFFFFF", "#161618"   # theme.py's "tile" in each theme
MIN_CONTRAST = 3.0


def _rgb(hex_):
    return tuple(int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _hex(rgb):
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


def _luminance(rgb):
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted((_luminance(_rgb(a)), _luminance(_rgb(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def scale_color(temp_f):
    """The scale's color for a temperature, blended between the nearest samples (clamped to -40..130)."""
    t = max(STOPS[0][0], min(STOPS[-1][0], float(temp_f)))
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            a, b = _rgb(c0), _rgb(c1)
            return _hex(tuple(x + (y - x) * f for x, y in zip(a, b)))
    return STOPS[-1][1]


def _readable(color, card, darken):
    """Walk the color's lightness down (darken) or up until it reaches MIN_CONTRAST on `card`."""
    if contrast(color, card) >= MIN_CONTRAST:
        return color
    h, l, s = colorsys.rgb_to_hls(*_rgb(color))
    for _ in range(100):
        l = max(0.0, l - 0.01) if darken else min(1.0, l + 0.01)
        c = _hex(colorsys.hls_to_rgb(h, l, s))
        if contrast(c, card) >= MIN_CONTRAST:
            return c
    return c


def shades(temp_f):
    """(light-theme color, dark-theme color) for a temperature."""
    base = scale_color(temp_f)
    return _readable(base, LIGHT_CARD, darken=True), _readable(base, DARK_CARD, darken=False)


def tc_attrs(temp_f):
    """(class name, style attribute) for a temperature element -- ("tc", ' style="--tl:…;--td:…"') --
    or ("", "") when there's no number. Separate so callers can merge the class with their own."""
    try:
        light, dark = shades(float(temp_f))
    except (TypeError, ValueError):
        return "", ""
    return "tc", f' style="--tl:{light};--td:{dark}"'


# Appended to Page 1's stylesheet (so it also reaches Page 2 and the Page 0 overlay's shadow root).
# The first `color` is for browsers without color-mix(): they get the light-theme shade in both.
TC_CSS = ".tc{color:var(--tl);color:color-mix(in srgb,var(--tl) var(--aag-tc-light),var(--td))}"

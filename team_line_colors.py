"""
Team colors for the Stat Leaders race chart's lines (Jason, 2026-10-07; worked out in
mockups/build_team_line_colors_mockup.py, option 1 there).

Each of the chart's five lines takes its player's team colors -- separately for the light ground and
the dark one, since a navy that reads on paper vanishes on the dark ground:
  * a team's candidates, in order: its pill fill, its pill ring (helmets.PILL_COLORS, the colors Jason
    picked as each team's identity), then its helmet shell, facemask and ear piece (helmets.TEAM_COLORS,
    EAR_COLORS); a candidate within 8 of one already listed is a repeat and dropped
  * players go in rank order, so the higher-ranked player gets first pick, and each takes his team's
    first candidate that is
      - visible:          WCAG contrast >= 2:1 against the ground (the lines are named at their ends,
                          so the 3:1 graphics bar relaxes to 2 -- the dataviz validator's relief band)
      - distinct:         OKLab Delta E x100 >= 15 from every line already placed (the validator's
                          normal-vision floor)
      - color-blind safe: >= 6 under protanopia and deuteranopia (Machado 2009) from every line
                          already placed (the validator's floor, legal with direct labels)
  * none passes -> a candidate mixed 15 / 30 / 45 / 60% toward white, then black ("adjusted")
  * still none -> the ground's secondary gray, and the line is dashed ("fallback")

The end dot is filled with the line's color and ringed in another of the team's colors -- the first in
the order above that's clearly different from the fill (Jason: "a fill or outline on the end dot to
differentiate even more") -- so two near-black lines, say Carolina's and Cincinnati's, still end in a
blue ring and an orange one.

The color math is the dataviz skill's validator (scripts/validate_palette.js) ported line for line.
"""

import math

import helmets

LIGHT_BG, DARK_BG = "#F3F3EE", "#161510"
CONTRAST_FLOOR, NORMAL_FLOOR, CVD_FLOOR = 2.0, 15.0, 6.0
RING_CONTRAST = 1.5   # the ring only has to show against the ground, beside a dot that already does
REPEAT = 8.0
MIXES = (0.15, 0.30, 0.45, 0.60)
FALLBACK = {LIGHT_BG: "#9C9B97", DARK_BG: "#8A8984"}

# Machado, Oliveira & Fernandes (2009), severity 1.0, linear RGB
MACHADO = {
    "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
}


def _srgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _lin(h):
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in _srgb(h)]


def contrast(a, b):
    lum = lambda h: sum(w * c for w, c in zip((0.2126, 0.7152, 0.0722), _lin(h)))
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _oklab(rgb):
    r, g, b = rgb
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return [0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_]


def _simulate(h, kind):
    r, g, b = _lin(h)
    M = MACHADO[kind]
    return [max(0.0, min(1.0, M[i][0] * r + M[i][1] * g + M[i][2] * b)) for i in range(3)]


def delta_e(h1, h2, kind=None):
    """OKLab Delta E x100; kind = "protan" / "deutan" for simulated color-blind vision."""
    a = _oklab(_simulate(h1, kind) if kind else _lin(h1))
    b = _oklab(_simulate(h2, kind) if kind else _lin(h2))
    return 100 * math.dist(a, b)


def _cvd(h1, h2):
    return min(delta_e(h1, h2, "protan"), delta_e(h1, h2, "deutan"))


def _mix(h, toward, amount):
    a, b = _srgb(h), _srgb(toward)
    return "#" + "".join(f"{round((x + (y - x) * amount) * 255):02X}" for x, y in zip(a, b))


def candidates(team):
    """The team's colors in order of identity: pill fill, pill ring, helmet shell, facemask, ear."""
    fill, ring = helmets.PILL_COLORS.get(team, helmets.FALLBACK_COLORS)
    shell, mask = helmets.TEAM_COLORS.get(team, helmets.FALLBACK_COLORS)
    ear = helmets.EAR_COLORS.get(team, helmets.FALLBACK_EAR)
    out = []
    for c in (fill, ring, shell, mask, ear):
        if all(delta_e(c, o) >= REPEAT for o in out):
            out.append(c.upper())
    return out


def _passes(c, bg, placed):
    return (contrast(c, bg) >= CONTRAST_FLOOR
            and all(delta_e(c, p) >= NORMAL_FLOOR and _cvd(c, p) >= CVD_FLOOR for p in placed))


RING_DE = 25.0


def _ring(team, color, bg):
    """The ring: the team's first candidate (identity order) clearly different from the dot's fill
    (Delta E >= 25) that shows on the ground -- else the most different one that shows."""
    showing = [c for c in candidates(team) if contrast(c, bg) >= RING_CONTRAST]
    first = next((c for c in showing if delta_e(c, color) >= RING_DE), None)
    if first:
        return first
    best = max(showing, key=lambda c: delta_e(c, color), default=None)
    return best if best and delta_e(best, color) >= NORMAL_FLOOR else bg


def assign(teams, bg):
    """Teams in rank order -> [(line color, ring color, kind)] on ground bg; kind is "team",
    "adjusted" or "fallback"."""
    placed, out = [], []
    for team in teams:
        cands, color, kind = candidates(team), None, "team"
        color = next((c for c in cands if _passes(c, bg, placed)), None)
        if color is None:
            kind = "adjusted"
            color = next((m for c in cands for toward in ("#FFFFFF", "#000000") for amt in MIXES
                          for m in (_mix(c, toward, amt),) if _passes(m, bg, placed)), None)
        if color is None:
            color, kind = FALLBACK[bg], "fallback"
        placed.append(color)
        out.append((color, _ring(team, color, bg) if kind != "fallback" else bg, kind))
    return out


def for_both(teams):
    """{"lc", "lr", "ld", "dc", "dr", "dd"} per team (rank order): light / dark line color, ring color,
    and dash ("4 3" for a fallback line, "none" otherwise)."""
    light, dark = assign(teams, LIGHT_BG), assign(teams, DARK_BG)
    dash = lambda kind: "4 3" if kind == "fallback" else "none"
    return [{"lc": l[0], "lr": l[1], "ld": dash(l[2]), "dc": d[0], "dr": d[1], "dd": dash(d[2])}
            for l, d in zip(light, dark)]

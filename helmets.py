"""
Team-colored helmet SVGs for Page 0.

The helmet artwork is the exact vector from Jason's Framer Page 0 design
(two paths: shell + facemask, 100x100 viewBox). Framer's gray version uses:
  shell    -> vertical gradient, lighter at top (#71757F) to darker at bottom (#222326)
  facemask -> vertical gradient, darker at top (#555555) to lighter at bottom (#A9A9A9)
Here we keep that same shading direction but tint it with each team's
colors: shell = official PRIMARY color, facemask = official SECONDARY color.

To change a team's colors, edit TEAM_COLORS below. To give one team
lighter/darker shading than the rest, add it to SHADING_OVERRIDES.

Run directly to export all 32 helmets (plus mirrored versions) as files:
    python helmets.py            -> site/helmets/*.svg
"""

import os

# (primary, secondary) -- official team colors. Keys are the nflverse
# abbreviations used in divisions.py.
# Sources: teamcolorcodes.com NFL table + nflverse teams_colors_logos
# (checked 2026-09-16). Where the two disagreed, see JUDGMENT CALLS below.
TEAM_COLORS = {
    "ARI": ("#97233F", "#000000"),
    "ATL": ("#A71930", "#A5ACAF"),
    "BAL": ("#241773", "#000000"),
    "BUF": ("#00338D", "#C60C30"),
    "CAR": ("#0085CA", "#101820"),
    "CHI": ("#0B162A", "#C83803"),
    "CIN": ("#FB4F14", "#000000"),
    "CLE": ("#311D00", "#FF3C00"),
    "DAL": ("#B0B7BC", "#041E42"),
    "DEN": ("#002244", "#FB4F14"),
    "DET": ("#0076B6", "#B0B7BC"),
    "GB": ("#FFB612", "#203731"),
    "HOU": ("#03202F", "#A71930"),
    "IND": ("#0B4FA0", "#A2AAAD"),
    "JAX": ("#101820", "#006778"),
    "KC": ("#E31837", "#FFB81C"),
    "LAC": ("#0080C6", "#FFC20E"),
    "LAR": ("#003594", "#FFA300"),
    "LV": ("#000000", "#A5ACAF"),
    "MIA": ("#008E97", "#FC4C02"),
    "MIN": ("#4F2683", "#FFC62F"),
    "NE": ("#B0B7BC", "#C60C30"),
    "NO": ("#D3BC8D", "#101820"),
    "NYG": ("#0B2265", "#A71930"),
    "NYJ": ("#125740", "#000000"),
    "PHI": ("#004C54", "#A5ACAF"),
    "PIT": ("#101820", "#FFB612"),
    "SEA": ("#002244", "#69BE28"),
    "SF": ("#B3995D", "#000000"),
    "TB": ("#34302B", "#B1BABF"),
    "TEN": ("#4495D2", "#D50A0A"),
    "WAS": ("#5A1414", "#FFB612"),
}

FALLBACK_COLORS = ("#4A4C53", "#7F7F7F")  # Framer's original gray, for unknown abbreviations


# Jason's final colors for the white background (picked team by team, 2026-09-18):
# (primary, secondary) above = shell + facemask; TERTIARY below = the small ear piece.
TERTIARY = {
    "ARI": "#FFB612",
    "ATL": "#000000",
    "BAL": "#241773",
    "BUF": "#00338D",
    "CAR": "#BFC0BF",
    "CHI": "#0B162A",
    "CIN": "#000000",
    "CLE": "#311D00",
    "DAL": "#041E42",
    "DEN": "#FB4F14",
    "DET": "#B0B7BC",
    "GB": "#FFB612",
    "HOU": "#A5ACAF",
    "IND": "#C8CED3",
    "JAX": "#D7A22A",
    "KC": "#E31837",
    "LAC": "#002A5E",
    "LAR": "#FFD100",
    "LV": "#000000",
    "MIA": "#005778",
    "MIN": "#4F2683",
    "NE": "#002244",
    "NO": "#D3BC8D",
    "NYG": "#A5ACAF",
    "NYJ": "#125740",
    "PHI": "#004C54",
    "PIT": "#101820",
    "SEA": "#A5ACAF",
    "SF": "#AA0000",
    "TB": "#D50A0A",
    "TEN": "#0C2340",
    "WAS": "#5A1414",
}
FALLBACK_TERTIARY = "#9A9A9A"

# The small piece's gray ramp in the Framer file runs light (lower left) to dark (upper right).

SHELL_PATH = "M 10.2 74.82 C 11.591 75.337 12.323 74.66 12.079 74.13 L 9.999 69.444 C 9.718 68.835 9.321 68.448 8.797 67.999 L 1.141 61.432 C 0.169 60.579 -0.09 61.527 0.026 62.207 L 1.34 70.161 C 1.537 71.325 1.912 71.862 2.58 72.09 Z M 77.533 39.899 C 77.929 39.899 78.139 39.791 78.421 39.546 C 78.602 39.389 80.595 37.667 82.02 36.81 C 82.682 36.413 84.239 35.705 85.586 35.463 C 85.79 35.426 86.097 35.458 86.116 34.89 C 86.124 34.626 86.043 33.088 85.931 32.405 C 85.875 32.068 85.909 32.272 85.754 31.335 C 84.494 23.703 73.755 11.162 68.945 8.053 C 62.902 4.148 54.626 0 42.315 0 C 30.004 0 20.76 6.019 18.67 7.249 C 14.192 9.884 7.484 15.995 7.484 17.574 C 7.484 17.725 8.983 17.231 11.396 16.688 C 14.369 16.02 20.305 15.443 22.08 15.328 C 22.223 15.319 23.408 15.193 24.601 15.165 C 25.688 15.139 27.123 15.165 27.238 15.165 C 27.958 15.165 28.526 15.437 27.975 15.755 C 26.653 16.518 25.154 17.104 25.127 17.112 C 24.798 17.204 24.341 17.359 24.083 17.359 C 22.907 17.359 12.239 18.389 7.185 19.94 C 5.788 20.369 5.358 20.981 5.329 21.024 C 3.724 23.429 2.124 26.109 0.249 30.333 C 0.08 30.713 -0.029 30.959 0.249 31.219 C 0.424 31.384 15.052 44.996 21.537 51.179 C 22.23 51.84 23.058 52.475 24.083 52.626 C 25.202 52.791 38.886 54.99 39.124 55.028 C 40.505 55.249 41.449 54.763 42.315 54.053 C 42.627 53.796 51.028 47.219 54.493 44.502 C 55.886 43.409 57.537 42.798 57.782 42.729 C 63.234 41.191 76.142 39.899 77.533 39.899 Z M 34.274 8.244 C 33.773 8.244 33.001 8.189 32.68 7.981 C 32.462 7.839 32.009 7.52 31.778 7.329 C 31.671 7.24 30.816 6.386 32.398 6.158 C 35.537 5.707 43.451 5.767 50.1 7.329 C 56.769 8.896 62.171 11.97 64.489 14.014 C 64.839 14.322 65.175 14.994 64.633 15.272 C 64.401 15.391 64.104 15.546 63.878 15.675 C 63.174 16.078 62.493 15.836 61.62 15.272 C 59.966 14.203 54.737 11.293 48.812 9.77 C 42.888 8.248 36.174 8.244 34.274 8.244 Z M 40.288 85.085 C 40.602 85.359 40.99 85.54 41.366 85.593 C 41.658 85.635 49.207 86.432 49.759 86.409 C 50.42 86.382 50.94 86.123 50.419 85.222 L 47.608 78.846 C 47.512 78.629 47.385 77.847 48.008 76.957 L 54.252 70.066 C 54.783 69.48 54.569 68.957 54.487 68.76 C 54.03 67.662 53.191 65.18 52.667 64.273 C 51.893 62.931 52.088 63.051 51.303 62.567 C 49.938 61.724 44.291 58.664 44.291 58.664 C 43.813 58.398 43.386 58.19 42.991 58.119 L 26.071 55.361 C 25.02 55.19 23.186 55.93 23.941 58.119 C 24.084 58.535 28.734 73.143 28.734 73.143 C 28.984 73.935 29.487 74.929 29.796 75.463 C 30.396 76.502 39.955 84.796 40.288 85.085 Z M 44.303 77.961 C 44.303 79.112 43.37 80.045 42.219 80.045 C 41.068 80.045 40.135 79.112 40.135 77.961 C 40.135 76.81 41.068 75.878 42.219 75.878 C 43.37 75.878 44.303 76.81 44.303 77.961 Z"
MASK_PATH = "M 16.521 25.44 C 16.409 25.357 16.311 25.266 16.267 25.156 C 15.227 22.556 14.203 19.699 13.673 18.326 C 13.473 17.808 12.825 17.192 13.673 16.156 C 14.116 15.616 19.52 7.543 21.196 5.073 C 21.411 4.756 29.608 4.347 35.688 4.558 C 41.644 4.764 46.229 5.527 47.609 5.592 C 48.1 5.615 48.563 5.637 48.879 5.073 C 49.194 4.509 48.567 2.805 48.325 2.26 C 48.083 1.715 48.181 1.185 46.754 0.924 C 42.361 0.121 32.104 0 31.705 0 C 24.903 0 16.701 1.839 14.331 2.26 C 12.63 2.563 12.364 2.826 11.254 3.578 C 7.524 6.108 1.787 10.589 1.048 11.316 C -0.43 12.767 -0.478 14.57 1.766 15.772 L 8.094 19.16 C 8.9 19.625 8.926 19.483 9.227 20.316 C 9.528 21.149 11.356 26.665 11.621 27.355 C 11.681 27.512 11.743 27.751 11.621 27.868 C 10.926 28.529 7.132 32.933 5.677 34.605 C 4.449 36.018 4.178 36.84 5.354 39.194 C 5.471 39.428 8.398 45.549 8.515 45.783 C 9.174 47.103 11.12 48.27 12.391 48.882 C 14.685 49.986 21.032 52.447 25.624 53.934 C 29.129 55.068 41.149 58.624 43.653 57.647 C 43.659 57.646 43.664 57.646 43.669 57.644 C 45.066 57.404 46.087 54.726 46.087 54.726 C 47.466 51.547 50.67 44.371 52.004 36.396 C 52.316 34.527 52.348 32.687 52.348 30.802 C 52.456 29.827 51.77 28.351 50.438 28.14 C 50.219 28.106 24.463 26.09 16.521 25.44 Z M 16.003 29.435 C 21.526 29.866 35.115 30.882 42.764 31.452 C 42.668 32.467 42.516 33.578 42.321 34.75 C 34.061 34.096 20.135 33.013 13.673 32.495 C 13.426 32.383 14.853 31.077 16.003 29.435 Z M 12.009 35.871 C 19.827 36.405 38.707 38.347 41.577 38.621 C 40.426 44.002 38.747 49.852 37.546 53.545 C 29.671 51.652 25.758 50.278 17.833 47.021 C 17.833 47.021 14.242 45.531 14.024 45.387 C 12.66 44.484 10.386 38.682 9.982 37.952 C 9.577 37.223 9.846 36.946 10.295 36.485 C 10.505 36.269 10.744 35.785 12.009 35.871 Z M 48.879 31.907 C 48.694 33.098 48.509 34.203 48.325 35.234 C 47.882 35.196 47.172 35.138 46.25 35.063 C 46.432 33.952 46.6 32.846 46.754 31.75 C 48.429 31.875 48.65 31.892 48.879 31.907 Z M 41.373 54.036 C 43.179 49.432 44.544 44.183 45.567 38.897 C 46.255 38.917 46.958 38.919 47.609 38.888 C 46.03 46.194 44.412 49.043 42.393 54.036 Z M 12.801 10.867 C 12.748 10.945 12.593 11.007 12.497 10.943 C 11.965 10.583 10.266 9.386 9.715 8.784 C 9.568 8.623 9.711 8.404 9.715 8.4 C 10.407 7.788 11.833 6.666 12.528 6.089 C 13.223 5.511 14.695 5.248 15.723 5.466 C 15.729 5.467 16.309 5.63 16 6.089 C 15.117 7.401 12.992 10.581 12.801 10.867 Z M 6.525 14.939 C 5.475 14.939 4.625 14.089 4.625 13.039 C 4.625 11.989 5.475 11.138 6.525 11.138 C 7.575 11.138 8.425 11.989 8.425 13.039 C 8.425 14.089 7.575 14.939 6.525 14.939 Z"
SIDE_PATH = "M 17.42 41.378 C 19.349 40.893 24.735 39.633 27.021 39.058 C 28.002 38.811 28.193 38.779 27.94 37.71 C 26.691 32.43 20.672 17.1 20.672 17.1 C 20.672 17.1 20.355 16.417 19.778 15.864 C 16.836 13.046 6.716 4.124 2.963 0.751 C 1.483 -0.58 1.688 0.142 1.347 0.751 C 0.682 1.938 0 5.377 0 6.034 L 0 7.542 C 0 11.065 1.369 19.295 2.659 24.259 C 2.849 24.988 3.305 25.68 4.149 26.365 C 6.074 27.927 10.773 32.624 12.798 34.099 C 13.06 34.289 13.178 34.453 13.352 34.741 C 14.153 36.061 15.525 39.469 16.095 40.71 C 16.506 41.603 16.699 41.559 17.42 41.378 Z"


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(hex_color, target_rgb, amount):
    """Blend hex_color toward target_rgb by amount (0..1). Returns 'rgb(r, g, b)'."""
    r, g, b = _hex_to_rgb(hex_color)
    tr, tg, tb = target_rgb
    mixed = [round(c + (t - c) * amount) for c, t in ((r, tr), (g, tg), (b, tb))]
    return f"rgb({mixed[0]}, {mixed[1]}, {mixed[2]})"


WHITE, BLACK = (255, 255, 255), (0, 0, 0)

# Gradient strength. Framer's gray shell spans ~+50% to ~-50% brightness
# around its midtone; these amounts give a similar "slight" gradient
# while keeping the true team color readable in the middle of the shape.
SHELL_LIGHTEN_TOP = 0.28
SHELL_DARKEN_BOTTOM = 0.40
MASK_DARKEN_TOP = 0.35
MASK_LIGHTEN_BOTTOM = 0.30

# Updated Framer helmet (2026-09-18, v4): the small piece is a narrow ear piece with a radial
# gradient -- lighter in the middle, darker at its edges.
SIDE_LIGHTEN = 0.22
SIDE_DARKEN = 0.16

# Geometry of the Framer artwork, used to line the two shell pieces' gradients up.
SHELL_SPAN_Y = 86.41   # height of the big shell piece
EAR_OFFSET_Y = 33.444  # how far down the ear piece is drawn

# Per-team shell shading, (lighten_top, darken_bottom). Teams not listed use
# SHELL_LIGHTEN_TOP / SHELL_DARKEN_BOTTOM above.
SHADING_OVERRIDES = {
    "DAL": (0.35, 0.22),  # Jason's pick: softer shading so the silver reads lighter
}


def helmet_svg(team, mirrored=False, id_prefix=None):
    """
    MOCKUP: Jason's 3-color Framer helmet.
      big shell piece  = primary colour    (light at the top, dark at the bottom)
      small shell piece= tertiary colour   (light in the middle, dark at its edges)
      facemask         = secondary colour  (dark at the shell, light at the outer edge)
    mirrored=True flips it horizontally (home team, so the helmets face each other).
    """
    primary, secondary = TEAM_COLORS.get(team, FALLBACK_COLORS)
    tertiary = TERTIARY.get(team, FALLBACK_TERTIARY)
    shell_top, shell_bottom = SHADING_OVERRIDES.get(team, (SHELL_LIGHTEN_TOP, SHELL_DARKEN_BOTTOM))
    pid = id_prefix or f"helmet-{team or 'x'}{'-m' if mirrored else ''}"
    # When the ear piece is the same color as the shell, the two shapes share ONE gradient so the
    # helmet reads as a single piece: the shell's top-to-bottom ramp, mapped in the same place on
    # both paths (the ear path sits 33.444 lower, so its copy starts that much earlier).
    if tertiary.strip().upper() == primary.strip().upper():
        side_gradient = (
            f'<linearGradient id="{pid}-side" gradientUnits="userSpaceOnUse" '
            f'x1="0" x2="0" y1="{-EAR_OFFSET_Y}" y2="{SHELL_SPAN_Y - EAR_OFFSET_Y}">'
            f'<stop offset="0" stop-color="{_mix(primary, WHITE, shell_top)}"/>'
            f'<stop offset="1" stop-color="{_mix(primary, BLACK, shell_bottom)}"/>'
            "</linearGradient>"
        )
    else:
        side_gradient = (
            f'<radialGradient id="{pid}-side" cx="0.5" cy="0.5" r="0.5" '
            'gradientTransform="translate(0.5, 0.5) scale(1 2) translate(-0.5, -0.5)">'
            f'<stop offset="0" stop-color="{_mix(tertiary, WHITE, SIDE_LIGHTEN)}"/>'
            f'<stop offset="1" stop-color="{_mix(tertiary, BLACK, SIDE_DARKEN)}"/>'
            "</radialGradient>"
        )
    flip = ' transform="translate(100 0) scale(-1 1)"' if mirrored else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" '
        f'aria-label="{team} helmet">'
        "<defs>"
        f'<linearGradient id="{pid}-shell" x1="0.4975" x2="0.5025" y1="0" y2="1">'
        f'<stop offset="0" stop-color="{_mix(primary, WHITE, shell_top)}"/>'
        f'<stop offset="1" stop-color="{_mix(primary, BLACK, shell_bottom)}"/>'
        "</linearGradient>"
        f"{side_gradient}"
        f'<linearGradient id="{pid}-mask" x1="1" x2="0" y1="0.5326" y2="0.4674">'
        f'<stop offset="0" stop-color="{_mix(secondary, WHITE, MASK_LIGHTEN_BOTTOM)}"/>'
        f'<stop offset="1" stop-color="{_mix(secondary, BLACK, MASK_DARKEN_TOP)}"/>'
        "</linearGradient>"
        "</defs>"
        f"<g{flip}>"
        f'<path d="{SHELL_PATH}" fill="url(#{pid}-shell)" transform="translate(2.334 0)"/>'
        f'<path d="{SIDE_PATH}" fill="url(#{pid}-side)" transform="translate(0 33.444)"/>'
        f'<path d="{MASK_PATH}" fill="url(#{pid}-mask)" transform="translate(47.641 42.083)"/>'
        "</g></svg>"
    )


def write_all(out_dir):
    """Write <TEAM>.svg (faces right) and <TEAM>-mirrored.svg (faces left) for all 32 teams."""
    os.makedirs(out_dir, exist_ok=True)
    for team in TEAM_COLORS:
        for mirrored in (False, True):
            name = f"{team}-mirrored.svg" if mirrored else f"{team}.svg"
            with open(os.path.join(out_dir, name), "w") as f:
                f.write(helmet_svg(team, mirrored=mirrored))
    # Gray Framer-style fallback for any abbreviation not in TEAM_COLORS
    for mirrored in (False, True):
        name = "_unknown-mirrored.svg" if mirrored else "_unknown.svg"
        with open(os.path.join(out_dir, name), "w") as f:
            f.write(helmet_svg("_unknown", mirrored=mirrored))
    return out_dir


def helmet_filename(team, mirrored=False):
    base = team if team in TEAM_COLORS else "_unknown"
    return f"{base}-mirrored.svg" if mirrored else f"{base}.svg"


if __name__ == "__main__":
    out = write_all(os.path.join(os.path.dirname(os.path.abspath(__file__)), "site", "helmets"))
    print(f"Wrote {len(TEAM_COLORS) * 2} team helmet SVGs (+ gray fallback) to {out}")

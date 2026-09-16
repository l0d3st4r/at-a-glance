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
    "ATL": ("#A71930", "#000000"),
    "BAL": ("#241773", "#000000"),
    "BUF": ("#00338D", "#C60C30"),
    "CAR": ("#0085CA", "#101820"),
    "CHI": ("#0B162A", "#C83803"),
    "CIN": ("#FB4F14", "#000000"),
    "CLE": ("#311D00", "#FF3C00"),  # JUDGMENT CALL: brown primary (nflverse lists orange first)
    "DAL": ("#B0B7BC", "#003594"),  # Jason's pick: lighter silver shell, blue facemask (+ softer shading, see SHADING_OVERRIDES)
    "DEN": ("#FB4F14", "#002244"),
    "DET": ("#0076B6", "#B0B7BC"),
    "GB":  ("#FFB612", "#203731"),  # Jason's pick: gold shell, green facemask
    "HOU": ("#03202F", "#A71930"),
    "IND": ("#0B4FA0", "#A2AAAD"),  # Jason's pick: brighter than official Speed Blue #002C5F
    "JAX": ("#101820", "#006778"),  # Jason's pick: black shell, teal facemask
    "KC":  ("#E31837", "#FFB81C"),
    "LAC": ("#0080C6", "#FFC20E"),
    "LAR": ("#003594", "#FFA300"),
    "LV":  ("#000000", "#A5ACAF"),
    "MIA": ("#008E97", "#FC4C02"),
    "MIN": ("#4F2683", "#FFC62F"),
    "NE":  ("#002244", "#C60C30"),
    "NO":  ("#D3BC8D", "#101820"),
    "NYG": ("#0B2265", "#A71930"),
    "NYJ": ("#125740", "#000000"),  # JUDGMENT CALL: black secondary (white would vanish on a white page)
    "PHI": ("#004C54", "#A5ACAF"),
    "PIT": ("#101820", "#FFB612"),  # JUDGMENT CALL: black primary (some sources list gold first)
    "SEA": ("#002244", "#69BE28"),
    "SF":  ("#B3995D", "#AA0000"),  # Jason's pick: gold shell, red facemask
    "TB":  ("#D50A0A", "#34302B"),
    "TEN": ("#4495D2", "#D50A0A"),  # 2026 rebrand: Titans blue primary (navy demoted); red secondary
    "WAS": ("#5A1414", "#FFB612"),
}

FALLBACK_COLORS = ("#4A4C53", "#7F7F7F")  # Framer's original gray, for unknown abbreviations

SHELL_PATH = "M 12.533 74.896 C 13.925 75.415 14.657 74.736 14.412 74.206 L 12.333 69.515 C 12.051 68.905 11.654 68.518 11.13 68.069 L 3.475 61.495 C 2.503 60.641 2.244 61.59 2.359 62.271 L 3.673 70.233 C 3.871 71.398 4.245 71.936 4.913 72.164 Z M 17.42 74.899 C 19.349 74.413 24.735 73.152 27.021 72.577 C 28.002 72.329 28.193 72.297 27.94 71.227 C 26.691 65.941 20.672 50.596 20.672 50.596 C 20.672 50.596 20.355 49.912 19.778 49.359 C 16.836 46.538 6.716 37.607 2.963 34.23 C 1.483 32.898 1.688 33.621 1.347 34.23 C 0.682 35.418 0 38.861 0 39.519 L 0 41.028 C 0 44.555 1.369 52.794 2.659 57.762 C 2.849 58.492 3.305 59.185 4.149 59.871 C 6.074 61.434 10.773 66.136 12.798 67.612 C 13.06 67.803 13.178 67.967 13.352 68.255 C 14.153 69.576 15.525 72.988 16.095 74.23 C 16.506 75.124 16.699 75.08 17.42 74.899 Z M 42.621 85.172 C 42.936 85.446 43.324 85.627 43.7 85.681 C 43.991 85.723 51.541 86.521 52.093 86.498 C 52.754 86.471 53.273 86.212 52.752 85.309 L 49.942 78.927 C 49.846 78.71 49.719 77.926 50.342 77.036 L 56.585 70.138 C 57.116 69.551 56.902 69.028 56.821 68.831 C 56.363 67.731 55.525 65.247 55.001 64.338 C 54.226 62.996 54.421 63.115 53.637 62.631 C 52.271 61.787 46.624 58.724 46.624 58.724 C 46.147 58.458 45.72 58.25 45.325 58.178 L 28.405 55.418 C 27.353 55.246 25.519 55.988 26.274 58.178 C 26.418 58.595 31.068 73.218 31.068 73.218 C 31.318 74.011 31.821 75.006 32.13 75.54 C 32.729 76.58 42.289 84.883 42.621 85.172 Z M 46.636 78.041 C 46.636 79.193 45.703 80.127 44.553 80.127 C 43.402 80.127 42.469 79.193 42.469 78.041 C 42.469 76.889 43.402 75.955 44.553 75.955 C 45.703 75.955 46.636 76.889 46.636 78.041 Z M 79.867 39.94 C 80.263 39.94 80.472 39.832 80.754 39.587 C 80.936 39.429 82.928 37.705 84.354 36.848 C 85.015 36.451 86.572 35.741 87.92 35.499 C 88.123 35.462 88.431 35.494 88.449 34.926 C 88.458 34.661 88.377 33.122 88.264 32.438 C 88.209 32.1 88.242 32.305 88.088 31.367 C 86.828 23.727 76.089 11.173 71.279 8.062 C 65.236 4.152 56.959 0 44.649 0 C 32.338 0 23.094 6.026 21.004 7.257 C 16.525 9.894 9.818 16.011 9.818 17.592 C 9.818 17.743 11.316 17.249 13.729 16.705 C 16.703 16.036 22.639 15.459 24.414 15.344 C 24.557 15.334 25.742 15.208 26.935 15.18 C 28.022 15.155 29.456 15.18 29.572 15.18 C 30.291 15.18 30.86 15.453 30.309 15.771 C 28.986 16.535 27.488 17.122 27.461 17.129 C 27.132 17.221 26.675 17.376 26.416 17.376 C 25.241 17.376 14.573 18.408 9.519 19.96 C 8.121 20.39 7.692 21.003 7.663 21.046 C 6.058 23.453 4.458 26.136 2.582 30.364 C 2.413 30.745 2.305 30.991 2.582 31.251 C 2.757 31.416 17.386 45.042 23.87 51.231 C 24.564 51.893 25.392 52.529 26.416 52.68 C 27.536 52.845 41.22 55.046 41.457 55.084 C 42.838 55.305 43.783 54.819 44.649 54.108 C 44.961 53.851 53.362 47.267 56.826 44.547 C 58.22 43.453 59.87 42.842 60.116 42.773 C 65.568 41.233 78.475 39.94 79.867 39.94 Z M 36.608 8.252 C 36.106 8.252 35.335 8.198 35.014 7.989 C 34.796 7.847 34.342 7.528 34.112 7.336 C 34.005 7.247 33.149 6.393 34.732 6.165 C 37.87 5.713 45.785 5.772 52.434 7.336 C 59.103 8.905 64.505 11.982 66.823 14.028 C 67.172 14.336 67.509 15.009 66.967 15.287 C 66.735 15.406 66.438 15.562 66.212 15.691 C 65.507 16.095 64.826 15.852 63.954 15.287 C 62.3 14.217 57.071 11.305 51.146 9.78 C 45.222 8.256 38.508 8.252 36.608 8.252 Z"
MASK_PATH = "M 16.521 25.466 C 16.409 25.383 16.311 25.291 16.267 25.182 C 15.227 22.58 14.203 19.719 13.673 18.345 C 13.473 17.826 12.825 17.209 13.673 16.173 C 14.116 15.632 19.52 7.55 21.196 5.078 C 21.411 4.761 29.608 4.352 35.688 4.562 C 41.644 4.769 46.229 5.532 47.609 5.597 C 48.1 5.62 48.563 5.643 48.879 5.078 C 49.194 4.514 48.567 2.808 48.325 2.263 C 48.083 1.717 48.181 1.186 46.754 0.925 C 42.361 0.121 32.104 0 31.705 0 C 24.903 0 16.701 1.841 14.331 2.263 C 12.63 2.565 12.364 2.829 11.254 3.582 C 7.524 6.114 1.787 10.6 1.048 11.327 C -0.43 12.78 -0.478 14.585 1.766 15.788 L 8.094 19.179 C 8.9 19.645 8.926 19.503 9.227 20.337 C 9.528 21.171 11.356 26.692 11.621 27.383 C 11.681 27.541 11.743 27.78 11.621 27.896 C 10.926 28.558 7.132 32.966 5.677 34.641 C 4.449 36.055 4.178 36.878 5.354 39.235 C 5.471 39.469 8.398 45.596 8.515 45.83 C 9.174 47.151 11.12 48.32 12.391 48.932 C 14.685 50.037 21.032 52.501 25.624 53.989 C 29.129 55.125 41.149 58.684 43.653 57.706 C 43.659 57.705 43.664 57.705 43.669 57.703 C 45.066 57.462 46.087 54.782 46.087 54.782 C 47.466 51.6 50.67 44.417 52.004 36.433 C 52.316 34.562 52.348 32.72 52.348 30.833 C 52.456 29.858 51.77 28.38 50.438 28.169 C 50.219 28.135 24.463 26.117 16.521 25.466 Z M 16.003 29.465 C 21.526 29.897 35.115 30.913 42.764 31.484 C 42.668 32.5 42.516 33.612 42.321 34.786 C 34.061 34.131 20.135 33.046 13.673 32.528 C 13.426 32.416 14.853 31.109 16.003 29.465 Z M 12.009 35.908 C 19.827 36.443 38.707 38.386 41.577 38.661 C 40.426 44.047 38.747 49.903 37.546 53.6 C 29.671 51.705 25.758 50.33 17.833 47.069 C 17.833 47.069 14.242 45.578 14.024 45.433 C 12.66 44.529 10.386 38.722 9.982 37.991 C 9.577 37.261 9.846 36.983 10.295 36.522 C 10.505 36.306 10.744 35.822 12.009 35.908 Z M 48.879 31.94 C 48.694 33.132 48.509 34.238 48.325 35.27 C 47.882 35.232 47.172 35.174 46.25 35.099 C 46.432 33.987 46.6 32.879 46.754 31.782 C 48.429 31.908 48.65 31.925 48.879 31.94 Z M 41.373 54.091 C 43.179 49.483 44.544 44.228 45.567 38.936 C 46.255 38.957 46.958 38.959 47.609 38.928 C 46.03 46.241 44.412 49.093 42.393 54.091 Z M 12.801 10.878 C 12.748 10.956 12.593 11.018 12.497 10.954 C 11.965 10.594 10.266 9.396 9.715 8.793 C 9.568 8.631 9.711 8.412 9.715 8.409 C 10.407 7.796 11.833 6.673 12.528 6.095 C 13.223 5.517 14.695 5.253 15.723 5.471 C 15.729 5.472 16.309 5.635 16 6.095 C 15.117 7.408 12.992 10.592 12.801 10.878 Z M 6.525 14.954 C 5.475 14.954 4.625 14.103 4.625 13.052 C 4.625 12.001 5.475 11.15 6.525 11.15 C 7.575 11.15 8.425 12.001 8.425 13.052 C 8.425 14.103 7.575 14.954 6.525 14.954 Z"


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

# Per-team shell shading, (lighten_top, darken_bottom). Teams not listed use
# SHELL_LIGHTEN_TOP / SHELL_DARKEN_BOTTOM above.
SHADING_OVERRIDES = {
    "DAL": (0.35, 0.22),  # Jason's pick: softer shading so the silver reads lighter
}


def helmet_svg(team, mirrored=False, id_prefix=None):
    """
    Return the SVG markup for one team's helmet.
    mirrored=True flips it horizontally (used for the home team on the right,
    so the two helmets face each other).
    id_prefix keeps gradient ids unique if several helmets are inlined on one page.
    """
    primary, secondary = TEAM_COLORS.get(team, FALLBACK_COLORS)
    shell_top, shell_bottom = SHADING_OVERRIDES.get(team, (SHELL_LIGHTEN_TOP, SHELL_DARKEN_BOTTOM))
    pid = id_prefix or f"helmet-{team or 'x'}{'-m' if mirrored else ''}"
    flip = ' transform="translate(100 0) scale(-1 1)"' if mirrored else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" '
        f'aria-label="{team} helmet">'
        "<defs>"
        f'<linearGradient id="{pid}-shell" x1="0.4975" x2="0.5025" y1="0" y2="1">'
        f'<stop offset="0" stop-color="{_mix(primary, WHITE, shell_top)}"/>'
        f'<stop offset="1" stop-color="{_mix(primary, BLACK, shell_bottom)}"/>'
        "</linearGradient>"
        f'<linearGradient id="{pid}-mask" x1="0.4975" x2="0.5025" y1="0" y2="1">'
        f'<stop offset="0" stop-color="{_mix(secondary, BLACK, MASK_DARKEN_TOP)}"/>'
        f'<stop offset="1" stop-color="{_mix(secondary, WHITE, MASK_LIGHTEN_BOTTOM)}"/>'
        "</linearGradient>"
        "</defs>"
        f"<g{flip}>"
        f'<path d="{SHELL_PATH}" fill="url(#{pid}-shell)"/>'
        f'<path d="{MASK_PATH}" fill="url(#{pid}-mask)" transform="translate(47.641 42.126)"/>'
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

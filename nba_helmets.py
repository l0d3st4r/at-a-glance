"""
The NBA pages' team icons and pills (2026-10-08): the NFL helmet drawing (helmets.py), recolored
in each NBA team's colors -- a placeholder until there's NBA art, picked over ESPN's logos.

Same three-part build and shading as the NFL helmets: the shell in the team's primary color, the
facemask in its secondary, the ear piece in a third. The pills are the NFL pills' shape and
shading (helmets.pill_html) with an NBA team's fill and ring and the NBA's abbreviations.

Keys are the NBA's abbreviations (nba_teams.py). Colors are the teams' official ones; the Jazz
follow ESPN's current purple and blue. A team that isn't one of the 30 (a preseason guest from
overseas, say) gets the gray NFL fallback.

Files go to site/nba/helmets/ -- <TEAM>.svg facing right, <TEAM>-mirrored.svg facing left, the
big-spot copies in lg/ -- named exactly like the NFL's, so the pages refer to them the same way.
"""

import contextlib
import html
import os

import helmets

# (shell, facemask, ear piece)
HELMET_COLORS = {
    "ATL": ("#C8102E", "#FDB927", "#26282A"),
    "BOS": ("#007A33", "#BA9653", "#FFFFFF"),
    "BKN": ("#000000", "#FFFFFF", "#777D84"),
    "CHA": ("#1D1160", "#00788C", "#A1A1A4"),
    "CHI": ("#CE1141", "#000000", "#FFFFFF"),
    "CLE": ("#860038", "#FDBB30", "#041E42"),
    "DAL": ("#00538C", "#B8C4CA", "#002B5E"),
    "DEN": ("#0E2240", "#FEC524", "#8B2131"),
    "DET": ("#C8102E", "#1D42BA", "#BEC0C2"),
    "GSW": ("#1D428A", "#FFC72C", "#FFFFFF"),
    "HOU": ("#CE1141", "#C4CED4", "#000000"),
    "IND": ("#002D62", "#FDBB30", "#BEC0C2"),
    "LAC": ("#1D428A", "#C8102E", "#12173F"),
    "LAL": ("#552583", "#FDB927", "#000000"),
    "MEM": ("#5D76A9", "#12173F", "#F5B112"),
    "MIA": ("#98002E", "#F9A01B", "#000000"),
    "MIL": ("#00471B", "#EEE1C6", "#0077C0"),
    "MIN": ("#0C2340", "#78BE20", "#236192"),
    "NOP": ("#0C2340", "#85714D", "#C8102E"),
    "NYK": ("#006BB6", "#F58426", "#BEC0C2"),
    "OKC": ("#007AC1", "#EF3B24", "#002D62"),
    "ORL": ("#0077C0", "#C4CED4", "#000000"),
    "PHI": ("#006BB6", "#ED174C", "#002B5C"),
    "PHX": ("#1D1160", "#E56020", "#63727A"),
    "POR": ("#E03A3E", "#000000", "#FFFFFF"),
    "SAC": ("#5A2D81", "#63727A", "#000000"),
    "SAS": ("#C4CED4", "#000000", "#000000"),
    "TOR": ("#CE1141", "#000000", "#A1A1A4"),
    "UTA": ("#4E008E", "#79A3DC", "#000000"),
    "WAS": ("#002B5C", "#E31837", "#C4CED4"),
}

# (fill, ring) -- letters are white on every pill, as on the NFL's
PILL_COLORS = {
    "ATL": ("#C8102E", "#FDB927"), "BOS": ("#007A33", "#BA9653"), "BKN": ("#000000", "#777D84"),
    "CHA": ("#1D1160", "#00788C"), "CHI": ("#CE1141", "#000000"), "CLE": ("#860038", "#FDBB30"),
    "DAL": ("#00538C", "#B8C4CA"), "DEN": ("#0E2240", "#FEC524"), "DET": ("#C8102E", "#1D42BA"),
    "GSW": ("#1D428A", "#FFC72C"), "HOU": ("#CE1141", "#C4CED4"), "IND": ("#002D62", "#FDBB30"),
    "LAC": ("#1D428A", "#C8102E"), "LAL": ("#552583", "#FDB927"), "MEM": ("#5D76A9", "#12173F"),
    "MIA": ("#98002E", "#F9A01B"), "MIL": ("#00471B", "#EEE1C6"), "MIN": ("#0C2340", "#78BE20"),
    "NOP": ("#0C2340", "#85714D"), "NYK": ("#006BB6", "#F58426"), "OKC": ("#007AC1", "#EF3B24"),
    "ORL": ("#0077C0", "#C4CED4"), "PHI": ("#006BB6", "#ED174C"), "PHX": ("#1D1160", "#E56020"),
    "POR": ("#E03A3E", "#000000"), "SAC": ("#5A2D81", "#63727A"), "SAS": ("#000000", "#C4CED4"),
    "TOR": ("#CE1141", "#000000"), "UTA": ("#4E008E", "#79A3DC"), "WAS": ("#002B5C", "#E31837"),
}


def helmet_filename(team, mirrored=False, large=False):
    base = team if team in HELMET_COLORS else "_unknown"
    name = f"{base}-mirrored.svg" if mirrored else f"{base}.svg"
    return f"{helmets.LARGE_DIR}/{name}" if large else name


def helmet_img(team, size, mirrored=False, prefix="", large=False):
    """The <img> for a team's helmet -- render_page1.helmet_img's markup, NBA files.
    prefix is the path back to site/nba/."""
    src = prefix + "helmets/" + helmet_filename(team, mirrored=mirrored, large=large)
    return f'<img class="hm" src="{html.escape(src)}" alt="" width="{size}" height="{size}">'


def pill_html(team, label=None):
    """The team pill (render_page1's .tpill rules), in the team's colors."""
    fill, ring = PILL_COLORS.get(team, helmets.FALLBACK_COLORS)
    m = helmets._mix
    style = (f"--pf1:{m(fill, helmets.WHITE, helmets.PILL_FILL_LIGHTEN)};--pf2:{m(fill, helmets.BLACK, helmets.PILL_FILL_DARKEN)};"
             f"--pr1:{m(ring, helmets.BLACK, helmets.PILL_RING_DARKEN)};--pr2:{m(ring, helmets.WHITE, helmets.PILL_RING_LIGHTEN)};"
             f"--pl:{helmets.PILL_LETTERS}")
    aria = f' role="img" aria-label="{html.escape(label)}"' if label else ""
    return f'<span class="tpill abbr" style="{style}"{aria}>{html.escape(team or "TBD")}</span>'


def write_all(out_dir):
    """Every team's helmet both ways, at both outline widths, plus the gray fallback."""
    for sub, width in (("", helmets.OUTLINE_WIDTH), (helmets.LARGE_DIR, helmets.LARGE_OUTLINE_WIDTH)):
        folder = os.path.join(out_dir, sub)
        os.makedirs(folder, exist_ok=True)
        for team in list(HELMET_COLORS) + ["_unknown"]:
            colors = HELMET_COLORS.get(team, helmets.FALLBACK_COLORS + (helmets.FALLBACK_EAR,))
            for mirrored in (False, True):
                name = f"{team}-mirrored.svg" if mirrored else f"{team}.svg"
                with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
                    f.write(helmets.helmet_svg(team, mirrored=mirrored, outline_width=width, colors=colors))
    return out_dir


@contextlib.contextmanager
def nba_colors():
    """For code that reads helmets.py's color tables directly (team_line_colors.py, the Stat Leaders
    race lines): while inside, those tables hold the NBA teams' colors. Restored on the way out."""
    saved = (dict(helmets.TEAM_COLORS), dict(helmets.EAR_COLORS), dict(helmets.PILL_COLORS))
    helmets.TEAM_COLORS.clear()
    helmets.TEAM_COLORS.update({t: c[:2] for t, c in HELMET_COLORS.items()})
    helmets.EAR_COLORS.clear()
    helmets.EAR_COLORS.update({t: c[2] for t, c in HELMET_COLORS.items()})
    helmets.PILL_COLORS.clear()
    helmets.PILL_COLORS.update(PILL_COLORS)
    try:
        yield
    finally:
        for table, old in zip((helmets.TEAM_COLORS, helmets.EAR_COLORS, helmets.PILL_COLORS), saved):
            table.clear()
            table.update(old)

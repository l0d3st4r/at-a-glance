"""
The NBA pages' team icons (2026-10-08): Jason's basketball ("basketball home v2.svg"), colored team
by team in the NBA Ball Color Picker artifact. They replace the NFL helmet recolored in NBA colors
(nba_helmets.py, which still has the NBA pills and the colors the Stat Leaders race lines use).

Four colored pieces per ball:
  panels  -- the larger pieces (black in the drawing)
  bands   -- the three curved stripes (gray in the drawing)
  seams   -- the gaps between them: a disc under the panels and bands
  outline -- a ring around the ball, the helmets' sticker outline in the team's pick
Panels and bands get the helmet shell's top-to-bottom shading (helmets.SHELL_LIGHTEN_TOP /
SHELL_DARKEN_BOTTOM), the seams a much fainter version of it; the outline is flat. The page adds the
helmets' drop shadow (theme.HELMET_SHADOW_CSS) -- the balls carry class "hm" like the helmets.

The drawing is the HOME ball. The away team's is mirrored, so in a matchup (away on the left, home
on the right) the two point opposite ways. A ball shown on its own -- standings, a schedule, a team
card -- is the home one.

Jason picked the same colors for the light and dark backgrounds, so one file per ball serves both.
To change a team's colors, edit BALL_COLORS. A team that isn't one of the 30 (a preseason guest from
overseas, say) gets FALLBACK_COLORS: the gray helmet's shell and facemask, black seams and outline.

Files go to site/nba/balls/ -- <TEAM>.svg (home), <TEAM>-away.svg (mirrored), and the big-spot
copies in lg/, with a thinner outline like the helmets'.
"""

import html
import os

import helmets

# (panels, bands, seams, outline) -- Jason's picks, 2026-10-08
BALL_COLORS = {
    "ATL": ("#C8102E", "#FFFFFF", "#FDB927", "#000000"),
    "BKN": ("#000000", "#FFFFFF", "#777D84", "#000000"),
    "BOS": ("#007A33", "#FFFFFF", "#000000", "#000000"),
    "CHA": ("#1D1160", "#00788C", "#A1A1A4", "#000000"),
    "CHI": ("#CE1141", "#FFFFFF", "#000000", "#000000"),
    "CLE": ("#860038", "#FDBB30", "#000000", "#000000"),
    "DAL": ("#00538C", "#B8C4CA", "#FFFFFF", "#000000"),
    "DEN": ("#0E2240", "#FEC524", "#FFFFFF", "#000000"),
    "DET": ("#C8102E", "#1D42BA", "#BEC0C2", "#000000"),
    "GSW": ("#1D428A", "#FFC72C", "#FFFFFF", "#000000"),
    "HOU": ("#CE1141", "#C4CED4", "#FFFFFF", "#000000"),
    "IND": ("#002D62", "#FDBB30", "#BEC0C2", "#000000"),
    "LAC": ("#1D428A", "#C8102E", "#BEC0C2", "#000000"),
    "LAL": ("#552583", "#FDB927", "#FFFFFF", "#000000"),
    "MEM": ("#5D76A9", "#12173F", "#12173F", "#000000"),
    "MIA": ("#98002E", "#F9A01B", "#000000", "#000000"),
    "MIL": ("#00471B", "#EEE1C6", "#FFFFFF", "#000000"),
    "MIN": ("#0C2340", "#9EA2A2", "#78BE20", "#000000"),
    "NOP": ("#0C2340", "#85714D", "#FFFFFF", "#000000"),
    "NYK": ("#005999", "#F58426", "#BEC0C2", "#000000"),
    "OKC": ("#007AC1", "#EF3B24", "#FFFFFF", "#000000"),
    "ORL": ("#0077C0", "#C4CED4", "#000000", "#000000"),
    "PHI": ("#006BB6", "#ED174C", "#FFFFFF", "#000000"),
    "PHX": ("#1D1160", "#E56020", "#63727A", "#000000"),
    "POR": ("#E03A3E", "#C4CED4", "#000000", "#000000"),
    "SAC": ("#5A2D81", "#63727A", "#000000", "#000000"),
    "SAS": ("#C4CED4", "#000000", "#FFFFFF", "#000000"),
    "TOR": ("#CE1141", "#000000", "#A1A1A4", "#000000"),
    "UTA": ("#4E008E", "#FFFFFF", "#79A3DC", "#000000"),
    "WAS": ("#002B5C", "#E31837", "#C4CED4", "#000000"),
}
FALLBACK_COLORS = helmets.FALLBACK_COLORS + ("#000000", "#000000")

PANELS_PATH = "M-1668.16,-1024.77 C-1482.06,-1107.51 -1411.27,-1108.47 -1214.16,-1118.79 L-1429.62,-1334.24 L-1429.62,-1334.24 C-1520.81,-1237.45 -1600.32,-1133.7 -1668.16,-1024.77 L-1668.16,-1024.77 Z M-1033.91,-1658.32 C-1143.52,-1590.23 -1247.89,-1510.34 -1345.23,-1418.63 L-1127.5,-1200.9 C-1127.39,-1203.45 -1127.4,-1204.94 -1127.4,-1204.94 C-1126.92,-1205.9 -1127.88,-1203.98 -1127.4,-1204.94 C-1117.08,-1402.09 -1116.18,-1472.96 -1033.91,-1658.32 L-1033.91,-1658.32 Z M610.799,1879.52 C877.756,1792.47 1129.81,1646.71 1346.84,1442.22 L-181.602,-86.2273 C-224.992,128.831 -237.747,244.795 -247.943,470.205 L-247.546,470.204 C-257.515,750.636 -133.431,1188.97 180.348,1519.3 C312.814,1655.23 493.194,1796.31 610.799,1879.52 Z M1866.42,628.248 C1785.27,508.886 1646.08,323.905 1509.17,190.48 C1178.83,-123.299 740.504,-247.383 460.072,-237.414 L460.073,-237.811 C236.69,-227.707 107.77,-212.957 -92.9595,-166.359 L1431.23,1357.83 L1431.23,1357.83 C1634.07,1142.55 1779.13,892.81 1866.42,628.248 Z M-1962.52,-58.5333 C-1977.59,363.904 -1856.94,790.263 -1600.58,1149.89 C-1576.88,554.204 -1435.23,44.1353 -1188.48,-366.853 C-1283.42,-402.39 -1387.23,-404.41 -1487.43,-360.514 L-1487.18,-359.566 C-1741.58,-242.642 -1922.42,-103.23 -1962.52,-58.5333 Z M-1439.86,1347.04 C-1423.02,1365.18 -1405.78,1383.08 -1388.13,1400.73 C-1034.13,1754.73 -579.065,1945.46 -116.152,1972.91 C-179.741,1923.92 -251.616,1862.57 -317.239,1793.35 C-669.112,1468.16 -817.228,1011.6 -819.989,632.248 L-820.912,632.278 C-815.231,425.68 -794.553,219.241 -844.219,35.2436 L-844.678,35.3667 C-869.133,-55.8994 -912.988,-138.848 -969.676,-206.949 C-973.407,-211.327 -977.221,-215.679 -981.123,-220.006 L-980.985,-220.144 C-1006.4,-248.953 -1034.17,-274.863 -1063.76,-297.333 C-1322.14,134.338 -1453.14,687.465 -1439.86,1347.04 L-1439.86,1347.04 Z M1955.68,-182.076 C1912.62,-618.176 1734.04,-1029.62 1399.71,-1363.95 C732.514,-1406.85 181.531,-1301.98 -257.163,-1066.73 C-252.148,-1061.98 -247.037,-1057.31 -241.83,-1052.72 L-241.692,-1052.86 C-237.365,-1048.95 -233.012,-1045.14 -228.635,-1041.41 C-160.534,-984.721 -77.5852,-940.866 13.6808,-916.411 L13.5577,-915.952 C197.554,-866.287 403.994,-886.963 610.594,-892.646 L610.563,-891.723 C989.92,-888.961 1446.48,-740.846 1771.66,-388.974 C1843,-321.345 1905.98,-247.073 1955.68,-182.076 Z M1198.16,-1545.37 C803.001,-1850.15 318.775,-1983.87 -154.547,-1946.52 C-217.574,-1861.97 -304.286,-1726.38 -381.253,-1558.91 L-382.201,-1559.16 C-438.081,-1431.58 -419.545,-1298.17 -352.173,-1184.65 C70.8096,-1424.76 592.142,-1549.77 1198.16,-1545.37 Z"
BANDS_PATH = "M-1774.54,-830.08 C-1867.79,-633.602 -1926.56,-424.89 -1950.86,-212.992 C-1866.36,-281.012 -1697.26,-400.749 -1518.11,-473.016 L-1518.11,-473.039 C-1388.1,-537.526 -1245.61,-533.732 -1115.69,-480.713 C-1042.96,-587.76 -962.471,-687.321 -874.511,-779.137 L-1105.12,-1009.75 C-1138.25,-993.118 -1173.05,-987.862 -1208.32,-985.559 C-1222.21,-984.359 -1235.72,-983.538 -1248.56,-982.45 L-1248.56,-982.45 C-1455.69,-965.302 -1564.39,-945.074 -1709.2,-872.017 C-1733.8,-859.602 -1755.38,-845.354 -1774.54,-830.08 L-1774.54,-830.08 Z M-840.266,-1763.93 C-854.934,-1745.28 -868.619,-1724.36 -880.599,-1700.61 C-953.656,-1555.81 -974.342,-1446.99 -991.49,-1239.86 C-992.579,-1227.02 -992.94,-1213.63 -994.14,-1199.73 C-996.517,-1163.34 -1002.04,-1127.44 -1019.96,-1093.36 L-789.697,-863.096 C-690.48,-956.225 -582.778,-1040.37 -466.901,-1115.18 C-551.372,-1263 -571.29,-1435.32 -494.576,-1589.99 L-494.553,-1589.99 C-443.398,-1716.81 -368.455,-1838.58 -304.909,-1928.89 C-488.649,-1900.06 -669.094,-1845.07 -840.266,-1763.93 L-840.266,-1763.93 Z M458.281,1922.51 C358.866,1842.75 229.274,1730.89 142.244,1639.09 C-209.629,1313.9 -357.745,857.347 -360.513,477.997 L-361.429,478.021 C-355.75,271.424 -335.167,160.795 -318.019,-46.3322 L-318.019,-46.3322 C-312.204,-89.9196 -306.595,-137.517 -281.552,-186.177 L-773.295,-677.921 C-852.361,-595.968 -924.796,-507.145 -990.39,-411.644 C-952.183,-384.66 -916.148,-353.237 -883.117,-318.011 C-796.9,-224.794 -744.545,-131.819 -716.598,-33.7779 C-713.222,-23.1407 -710.076,-12.3911 -707.167,-1.53407 L-707.167,-1.53407 C-661.483,192.723 -697.152,398.975 -707.349,624.386 L-706.951,624.384 C-716.923,904.819 -592.832,1343.14 -279.055,1673.48 C-139.593,1816.59 9.54191,1918.74 101.831,1973.72 C221.639,1967.58 340.994,1950.51 458.281,1922.51 Z M1910.14,475.021 C1943.78,335.979 1962.03,193.99 1964.91,51.7474 C1913.91,-37.4759 1806.96,-199.876 1651.94,-350.939 C1321.61,-664.715 883.284,-788.807 602.847,-778.833 L602.85,-779.231 C377.439,-769.036 171.188,-733.366 -23.0704,-779.049 L-23.0704,-779.049 C-33.9274,-781.958 -44.6777,-785.104 -55.3142,-788.48 C-153.355,-816.427 -246.33,-868.783 -339.548,-954.999 C-353.565,-968.143 -366.98,-981.763 -379.753,-995.805 C-490.637,-926.68 -593.467,-848.431 -687.948,-761.348 L-196.339,-269.739 C-151.218,-292.222 -106.451,-297.689 -61.8385,-302.513 L-61.8385,-302.513 C119.469,-328.614 261.292,-345.618 467.888,-351.297 L467.865,-350.381 C847.215,-347.613 1303.77,-199.497 1628.96,152.376 C1721.51,240.116 1832.07,373.49 1910.14,475.021 Z"

# The ball's edge is a circle of radius ~1965 centered at (2, 13.5) in the drawing's units.
CX, CY, R = 2, 13.5, 1965
# The box is sized so the ball sits about as big as a helmet in the same <img>; the outline is the
# helmets' width (2.5 units a side, 1.8 on the big spots, in their 106-unit box) scaled to it.
BOX = 5000
OUTLINE_WIDTH = 118
LARGE_OUTLINE_WIDTH = 85
LARGE_DIR = "lg"
SEAM_LIGHTEN_TOP, SEAM_DARKEN_BOTTOM = 0.10, 0.12   # about a third of the shell's shading


def _ramp(gid, color, top, bottom):
    m = helmets._mix
    return (f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" x2="0" y1="{CY - R}" y2="{CY + R}">'
            f'<stop offset="0" stop-color="{m(color, helmets.WHITE, top)}"/>'
            f'<stop offset="1" stop-color="{m(color, helmets.BLACK, bottom)}"/></linearGradient>')


def ball_svg(team, away=False, outline_width=OUTLINE_WIDTH):
    panels, bands, seams, outline = BALL_COLORS.get(team, FALLBACK_COLORS)
    pid = f"ball-{team or 'x'}{'-a' if away else ''}"
    shell = (helmets.SHELL_LIGHTEN_TOP, helmets.SHELL_DARKEN_BOTTOM)
    flip = f' transform="translate({2 * CX} 0) scale(-1 1)"' if away else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{CX - BOX / 2:g} {CY - BOX / 2:g} {BOX} {BOX}" role="img" '
        f'aria-label="{html.escape(team or "")} ball">'
        f"<defs>{_ramp(pid + '-p', panels, *shell)}{_ramp(pid + '-b', bands, *shell)}"
        f"{_ramp(pid + '-s', seams, SEAM_LIGHTEN_TOP, SEAM_DARKEN_BOTTOM)}</defs>"
        f"<g{flip}>"
        f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="{outline}" stroke="{outline}" stroke-width="{2 * outline_width}"/>'
        # the seams disc sits a hair inside the edge so it never shows as a rim outside the panels
        f'<circle cx="{CX}" cy="{CY}" r="{R - 4}" fill="url(#{pid}-s)"/>'
        f'<path d="{PANELS_PATH}" fill="url(#{pid}-p)"/>'
        f'<path d="{BANDS_PATH}" fill="url(#{pid}-b)"/>'
        "</g></svg>"
    )


def ball_filename(team, away=False, large=False):
    base = team if team in BALL_COLORS else "_unknown"
    name = f"{base}-away.svg" if away else f"{base}.svg"
    return f"{LARGE_DIR}/{name}" if large else name


def ball_img(team, size, away=False, prefix="", large=False):
    """The <img> for a team's ball -- the helmets' markup and class. prefix is the path back to site/nba/.
    large=True: the thinner-outline copy, for balls drawn bigger than ~60px."""
    src = prefix + "balls/" + ball_filename(team, away=away, large=large)
    return f'<img class="hm" src="{html.escape(src)}" alt="" width="{size}" height="{size}">'


def write_all(out_dir):
    """Every team's ball both ways, at both outline widths, plus the gray fallback."""
    for sub, width in (("", OUTLINE_WIDTH), (LARGE_DIR, LARGE_OUTLINE_WIDTH)):
        folder = os.path.join(out_dir, sub)
        os.makedirs(folder, exist_ok=True)
        for team in list(BALL_COLORS) + ["_unknown"]:
            for away in (False, True):
                with open(os.path.join(folder, ball_filename(team, away)), "w", encoding="utf-8") as f:
                    f.write(ball_svg(team, away=away, outline_width=width))
    return out_dir


if __name__ == "__main__":
    out = write_all(os.path.join(os.path.dirname(os.path.abspath(__file__)), "site", "nba", "balls"))
    print(f"Wrote {len(BALL_COLORS) * 2} NBA team balls (+ gray fallback) to {out}")

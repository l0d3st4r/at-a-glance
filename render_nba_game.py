"""
NBA game pages (2026-10-08): site/nba/game/<game_id>.html, one per game -- the NFL's Page 1 and its
Page 2 deep dives (render_page1.py, render_page2gameinfo.py, render_page2team.py,
render_page2players.py), built for basketball.

Same page, same markup, same stylesheet and script: the NFL modules' CSS (P1_CSS, P2_CSS, P3_CSS,
P4_CSS) and P1_JS are used as they are, so the deck, the condensed view, the header flight, the deep
dives' open and close, swiping between games and every gesture behave exactly as on the NFL pages.
The NFL card icons stay as placeholders. Only the contents change:

  Page 1   Game Info -- tip-off time and date, national TV (or "Local TV"), the arena where the NFL
           card has its weather; a finished game's line score by quarter (OT1, OT2... when it went
           to overtime). Team cards -- record with the last-game arrow or streak, the top 3 injuries,
           and offense / defense ranks in points and field goal % (a finished game: its box score).
           Leaders -- each team's leader in points, rebounds, assists, steals and blocks per game,
           crowned when top 3 in the league (a finished game: that game's leaders).
  Tip-Off  time, countdown, TV, the last 5 meetings (the NFL page has the last one), crew chief.
  Arena    name, city, the home team (the NFL's Venue card, no surface or roof).
  Team     Overview -- home / road / last-10 records where the NFL has the bye week; rest days
           ("B2B" for a back-to-back) and miles traveled; the last 5 games (the NFL shows 4); the
           division with games behind. Injuries -- the full report (a finished game: who didn't play
           and why, then the pre-game report). Team Stats -- offense and defense per game with league
           ranks. Schedule -- the 10 games before this one, this one, and the 10 after.
  Player Stats  Scoring, Rebounding, Playmaking, Defense: per-game averages for the season to date
           (a finished game: its box score), sortable, top-3-in-the-league bars.

Data: data/nba.json -> game_details (build_nba_data.py) and player_games (nba_stats.py).
Defensive like the NFL pages: a missing value is "—", a failing deep dive is left out, a failing
game is skipped with a warning.
"""

import html
import os
import re
import shutil
import traceback
from datetime import date

import local_time
import logo
import nba_balls
import nba_helmets
import nba_stats
import nba_teams
import render_page1 as p1
import render_page2gameinfo as gi
import render_page2players as ps
import render_page2team as tp
import stadium_icons
import theme

DASH = "—"
MONTHS_UPPER = p1.MONTHS_UPPER
DAY_NAMES = p1.DAY_NAMES


def esc(v):
    return html.escape(str(v), quote=True)


def img(team, size, away=False, prefix="../", large=False):
    """A team's ball: the home one as drawn, the away one mirrored (nba_balls.py)."""
    return nba_balls.ball_img(team, size, away, prefix, large)


# The cards' nav-dot and title icons: the NFL's (render_page1.NAV_ICONS), except the two team cards,
# which get Jason's basketballs (2026-10-08) -- the home team's filled, the away team's outlined, the
# way the NFL page pairs a filled helmet with an outlined one. Only the paths on each drawing's canvas
# are kept (the files also carried the off-canvas art they were drawn from).
NAV_ICONS = dict(p1.NAV_ICONS, **{
    "away-team": (
        '<svg viewBox="-1961 -1964 3928 3928" fill="currentColor" aria-hidden="true"><path d="M1966.1,-2.95753e-06 '
        'C1966.1,-1084.28 1087.12,-1963.25 2.84318,-1963.25 C-1081.43,-1963.25 -1960.41,-1084.28 -1960.41,2.95753e-06 '
        'C-1960.41,1084.28 -1081.43,1963.25 2.84318,1963.25 C1087.12,1963.25 1966.1,1084.28 1966.1,-2.95753e-06 Z '
        'M1840.65,49.1282 C1813.52,1065.69 967.435,1867.78 -49.1282,1840.65 C-1065.69,1813.52 -1867.78,967.435 '
        '-1840.65,-49.1282 C-1813.52,-1065.69 -967.435,-1867.78 49.1282,-1840.65 C1065.69,-1813.52 1867.78,-967.435 '
        '1840.65,49.1282 Z"/><path d="M1157.48,-1587.99 C1049.08,-1569 911.193,-1535.98 786.345,-1482.9 L786.332,-1482.92 '
        'C622.718,-1427.8 514.948,-1291.86 470.154,-1127.61 C335.32,-1156.65 199.665,-1173.31 63.6552,-1177.61 '
        'L63.6554,-1962.33 C43.4599,-1962.95 23.1877,-1963.25 2.84318,-1963.25 C-16.7347,-1963.25 -36.2457,-1962.97 '
        '-55.6858,-1962.4 L-55.6857,-1178.22 C-182.807,-1175.49 -310.118,-1162 -437.243,-1137.74 C-491.622,-1267.1 '
        '-589.694,-1370.54 -727.224,-1416.87 L-727.236,-1416.85 C-904.612,-1492.26 -1108.32,-1527.17 -1216.36,-1538.9 '
        'C-1256.8,-1506.82 -1295.95,-1473.17 -1333.72,-1438.05 C-1272.5,-1440.99 -1046.93,-1411.52 -785.589,-1314.76 '
        'L-785.093,-1315.6 C-683.202,-1275.79 -611.229,-1200.96 -569.224,-1108.7 C-1034.32,-992.563 -1495.15,-732.052 '
        '-1933.12,-327.594 C-1922.25,-392.425 -1908.21,-456.176 -1891.17,-518.682 C-1936.31,-353.456 -1960.41,-179.543 '
        '-1960.41,2.95753e-06 C-1960.41,177.579 -1936.83,349.65 -1892.64,513.256 C-1936.75,349.668 -1960.27,177.602 '
        '-1960.27,0.000172346 C-1960.27,-24.9601 -1959.8,-49.8112 -1958.88,-74.5447 L-1958.88,-74.5435 C-1501.88,-550.322 '
        '-1018.13,-848.813 -530.189,-971.346 C-525.159,-934.539 -523.844,-896.581 -526.242,-858.237 L-526.437,-858.237 '
        'C-526.738,-852.419 -527.118,-846.644 -527.575,-840.91 C-535.646,-752.671 -563.289,-663.008 -610.531,-581.181 '
        'L-610.12,-580.943 C-705.107,-415.718 -865.702,-284.365 -1015.81,-142.295 L-1015.13,-141.664 C-1281.43,128.535 '
        '-1499.53,556.102 -1480.66,1034.85 C-1483.19,1129.87 -1475.81,1223.75 -1465.54,1303.19 C-1417.28,1357.53 '
        '-1366.04,1409.18 -1312.08,1457.87 C-1338.43,1353.63 -1371.47,1176.37 -1368.89,977.094 C-1357.19,521.638 '
        '-1134.99,123.952 -929.641,-67.2945 L-929.925,-67.5746 C-763.325,-219.754 -593.146,-340.885 -488.089,-510.549 '
        'L-487.203,-510.038 C-481.583,-519.772 -476.207,-529.598 -471.073,-539.507 C-421.509,-628.594 -392.786,-731.358 '
        '-387.836,-858.237 C-386.284,-906.502 -389.545,-954.202 -397.481,-1000.3 C-283.57,-1021.45 -169.543,-1033.03 '
        '-55.6857,-1035.08 L-55.6857,1962.4 C-36.2457,1962.97 -16.7347,1963.25 2.84318,1963.25 C23.1878,1963.25 '
        '43.46,1962.95 63.6556,1962.33 L63.6552,-1033.72 C192.041,-1028.49 320.084,-1011.11 447.369,-981.578 '
        'C446.471,-962.617 446.327,-943.499 446.944,-924.294 C451.894,-797.415 480.617,-694.651 530.181,-605.564 '
        'C535.315,-595.656 540.692,-585.829 546.311,-576.095 L547.197,-576.606 C652.255,-406.942 822.434,-285.812 '
        '989.033,-133.631 L988.75,-133.352 C1194.1,57.8948 1416.3,455.581 1428,911.037 C1430.76,1124.71 1392.58,1313.07 '
        '1365.6,1413.25 C1421.68,1359.16 1474.54,1301.77 1523.89,1241.38 C1534.44,1161.06 1542.14,1065.52 1539.55,968.797 '
        'C1558.42,490.046 1340.32,62.4779 1074.03,-207.721 L1074.71,-208.352 C924.599,-350.422 764.003,-481.776 '
        '669.017,-647 L669.428,-647.237 C622.186,-729.065 594.542,-818.728 586.472,-906.968 C586.014,-912.701 '
        '585.634,-918.475 585.333,-924.294 L585.138,-924.294 C584.705,-931.224 584.393,-938.141 584.202,-945.042 '
        'C1060.75,-801.186 1524.52,-485.74 1965.96,16.3752 C1965.96,19.3796 1965.95,22.3818 1965.94,25.3817 '
        'C1966.04,16.9339 1966.1,8.47319 1966.1,-2.95753e-06 C1966.1,-87.0103 1960.44,-172.699 1949.46,-256.717 '
        'L1949.46,-256.716 C1524.7,-687.048 1068.45,-966.529 600.407,-1095.61 C633.038,-1223.52 714.266,-1330.96 '
        '843.99,-1381.66 L844.486,-1380.82 C1015.94,-1444.3 1171.99,-1478.82 1276.35,-1494.22 C1237.98,-1526.96 '
        '1198.33,-1558.24 1157.48,-1587.99 L1157.48,-1587.99 Z"/></svg>'
    ),
    "home-team": (
        '<svg viewBox="-1961 -1964 3928 3928" fill="currentColor" aria-hidden="true"><path d="M-55.686,-1963.25 '
        'C-494.202,-1950.2 -896.436,-1793.68 -1217.1,-1538.98 C-1109.26,-1527.34 -905.021,-1492.43 -727.236,-1416.85 '
        'L-727.224,-1416.87 C-589.694,-1370.54 -491.622,-1267.1 -437.243,-1137.74 C-310.118,-1162 -182.807,-1175.49 '
        '-55.6857,-1178.22 L-55.6857,-1963.25 L-55.686,-1963.25 Z M-1311.87,1458.72 C-977.442,1760.54 -538.561,1948.88 '
        '-55.6857,1963.25 L-55.6857,-1035.08 C-169.543,-1033.03 -283.57,-1021.45 -397.481,-1000.3 C-389.545,-954.202 '
        '-386.284,-906.502 -387.836,-858.237 C-392.786,-731.358 -421.509,-628.594 -471.073,-539.507 C-476.207,-529.598 '
        '-481.583,-519.772 -487.203,-510.038 L-488.089,-510.549 C-593.146,-340.885 -763.325,-219.754 -929.925,-67.5746 '
        'L-929.642,-67.2945 C-1134.99,123.952 -1357.19,521.638 -1368.89,977.094 C-1371.48,1176.91 -1338.25,1354.59 '
        '-1311.87,1458.72 Z M63.6558,1963.25 C568.367,1948.23 1025.02,1743.16 1364.56,1417.08 C1391.59,1317.93 '
        '1430.8,1127.47 1428,911.037 C1416.3,455.581 1194.1,57.8948 988.75,-133.352 L989.033,-133.631 C822.434,-285.812 '
        '652.255,-406.942 547.197,-576.606 L546.311,-576.095 C540.692,-585.829 535.315,-595.656 530.181,-605.564 '
        'C480.617,-694.651 451.894,-797.415 446.944,-924.294 C446.327,-943.499 446.471,-962.617 447.369,-981.578 '
        'C320.084,-1011.11 192.041,-1028.49 63.6552,-1033.72 L63.6555,1963.25 L63.6558,1963.25 Z M1160.08,-1588.44 '
        'C850.787,-1813.85 473.031,-1951.06 63.6554,-1963.25 L63.6552,-1177.61 C199.665,-1173.31 335.32,-1156.65 '
        '470.154,-1127.61 C514.948,-1291.86 622.718,-1427.8 786.332,-1482.92 L786.345,-1482.9 C912.192,-1536.41 '
        '1051.29,-1569.52 1160.08,-1588.44 Z"/><path d="M-1334.57,-1438.01 C-1643.93,-1149.96 -1860.1,-763.167 '
        '-1933.12,-327.594 C-1495.15,-732.052 -1034.32,-992.563 -569.224,-1108.7 C-611.229,-1200.96 -683.202,-1275.79 '
        '-785.093,-1315.6 L-785.589,-1314.76 C-1048.16,-1411.97 -1274.61,-1441.26 -1334.57,-1438.01 Z M-1958.88,-74.5447 '
        'C-1959.8,-49.8112 -1960.27,-24.9601 -1960.27,0.000172346 C-1960.27,500.628 -1773.35,957.274 -1465.44,1304.01 '
        'C-1475.76,1224.41 -1483.2,1130.2 -1480.66,1034.85 C-1499.53,556.102 -1281.43,128.534 -1015.13,-141.664 '
        'L-1015.81,-142.295 C-865.702,-284.365 -705.107,-415.718 -610.12,-580.943 L-610.531,-581.181 C-563.289,-663.008 '
        '-535.646,-752.671 -527.575,-840.91 C-527.118,-846.644 -526.738,-852.419 -526.437,-858.237 L-526.242,-858.237 '
        'C-523.844,-896.581 -525.159,-934.539 -530.189,-971.346 C-1018.13,-848.813 -1501.88,-550.322 -1958.88,-74.5435 '
        'L-1958.88,-74.5447 Z M1523.38,1245.22 C1801.3,906.403 1965.96,489.192 1965.96,16.3752 C1524.52,-485.74 '
        '1060.75,-801.186 584.202,-945.041 C584.393,-938.141 584.705,-931.224 585.138,-924.294 L585.333,-924.294 '
        'C585.634,-918.476 586.014,-912.701 586.472,-906.968 C594.542,-818.728 622.186,-729.065 669.428,-647.237 '
        'L669.017,-647 C764.003,-481.776 924.599,-350.422 1074.71,-208.352 L1074.03,-207.721 C1340.32,62.4779 '
        '1558.42,490.046 1539.55,968.797 C1542.18,1067.06 1534.19,1164.11 1523.38,1245.22 Z M1951.72,-254.426 '
        'C1887.82,-749.36 1639.97,-1186.31 1278.87,-1494.59 C1174.52,-1479.37 1017.33,-1444.81 844.486,-1380.82 '
        'L843.99,-1381.66 C714.266,-1330.96 633.038,-1223.52 600.407,-1095.61 C1069.28,-966.3 1526.32,-686.057 '
        '1951.72,-254.426 Z"/></svg>'
    ),
})


# The NBA team pages' card icons: the NFL's (render_page2team.TEAM_ICONS), except Overview and Schedule,
# which get Jason's basketball versions (2026-10-08) -- the same flag and calendar with a basketball in
# place of the football. Only the paths on each drawing's canvas are kept; the frames match the NFL's.
TEAM_ICONS = dict(tp.TEAM_ICONS, **{
    "overview": (
        '<svg viewBox="-1763 -1303 3200 2617" fill="currentColor" aria-hidden="true"><path d="M-526.405,-1241.3 '
        'C93.5862,-1384.63 664.432,-440.212 1430.12,-921.409 C1431.64,-473.095 1436.29,889.527 1436.29,889.527 '
        'C1436.29,889.527 1091.23,1184.99 674.751,1281.27 C166.281,1398.82 -698.649,513.575 -1276.06,898.77 '
        'C-1278.76,106.511 -1282.23,-912.166 -1282.23,-912.166 C-1282.23,-912.166 -832.168,-1170.62 -526.405,-1241.3 Z '
        'M-526.406,-972.709 C-653.185,-955.866 -1039.24,-750.716 -1039.24,-750.716 C-1039.24,-750.716 -1039.24,-235.568 '
        '-1039.24,566.389 C-416.759,509.593 166.281,1136.95 674.751,1019.4 C945.101,956.902 1166.36,728.84 1166.36,728.84 '
        'C1166.36,728.84 1167.88,-61.9274 1166.35,-510.241 C570.614,-372.517 -3.8051,-1042.14 -526.406,-972.709 Z"/><path '
        'd="M-1761.01,-796.43 L-1762.14,-1128.96 C-1762.46,-1223.68 -1685.39,-1301.29 -1590.66,-1301.61 '
        'C-1495.94,-1301.93 -1418.34,-1224.85 -1418.02,-1130.13 L-1416.88,-797.603 L-1416.26,-614.809 C-1416.26,-614.809 '
        '-1416.26,-614.808 -1416.26,-614.808 L-1411.41,807.702 L-1410.28,1140.26 C-1409.96,1234.99 -1487.03,1312.59 '
        '-1581.76,1312.91 C-1676.48,1313.24 -1754.08,1236.16 -1754.41,1141.44 L-1755.54,808.875 L-1755.54,808.875 '
        'L-1761.01,-796.43 Z"/><path d="M-21.3361,-715.68 C-181.192,-710.92 -327.821,-653.863 -444.716,-561.017 '
        'C-405.403,-556.771 -330.951,-544.047 -266.141,-516.494 L-266.137,-516.501 C-216.002,-499.611 -180.251,-461.905 '
        '-160.428,-414.748 C-114.086,-423.593 -67.6763,-428.51 -21.336,-429.504 L-21.336,-715.68 L-21.3361,-715.68 Z '
        'M-479.262,531.759 C-357.351,641.784 -197.362,710.44 -21.336,715.68 L-21.336,-377.324 C-62.8411,-376.58 '
        '-104.408,-372.355 -145.933,-364.646 C-143.04,-347.843 -141.851,-330.454 -142.417,-312.86 C-144.222,-266.607 '
        '-154.692,-229.146 -172.76,-196.671 C-174.632,-193.058 -176.592,-189.476 -178.64,-185.928 L-178.963,-186.114 '
        'C-217.26,-124.265 -279.297,-80.1086 -340.029,-24.6335 L-339.926,-24.5314 C-414.783,45.185 -495.781,190.157 '
        '-500.05,356.187 C-500.992,429.027 -488.88,493.799 -479.262,531.759 Z M22.1685,715.68 C206.155,710.202 '
        '372.621,635.448 496.397,516.578 C506.25,480.434 520.544,411.005 519.525,332.107 C515.256,166.076 434.258,21.1048 '
        '359.4,-48.6117 L359.503,-48.7137 C298.772,-104.189 236.735,-148.346 198.437,-210.194 L198.115,-210.008 '
        'C196.066,-213.557 194.106,-217.139 192.234,-220.751 C174.166,-253.226 163.696,-290.688 161.891,-336.94 '
        'C161.666,-343.941 161.719,-350.91 162.046,-357.822 C115.646,-368.586 68.9697,-374.922 22.1683,-376.829 '
        'L22.1684,715.68 L22.1685,715.68 Z M421.857,-579.048 C309.107,-661.215 171.401,-711.236 22.1684,-715.68 '
        'L22.1683,-429.284 C71.7488,-427.715 121.2,-421.642 170.352,-411.056 C186.682,-470.933 225.968,-520.487 '
        '285.611,-540.582 L285.616,-540.574 C331.492,-560.079 382.199,-572.15 421.857,-579.048 Z M-487.536,-524.209 '
        'C-600.312,-419.204 -679.114,-278.203 -705.732,-119.42 C-546.075,-266.861 -378.083,-361.827 -208.54,-404.162 '
        'C-223.853,-437.795 -250.089,-465.073 -287.232,-479.587 L-287.413,-479.279 C-383.129,-514.715 -465.678,-525.393 '
        '-487.536,-524.209 Z M-715.123,-27.1744 C-715.456,-18.1581 -715.629,-9.09893 -715.629,4.00821e-05 '
        'C-715.629,182.498 -647.49,348.962 -535.243,475.362 C-539.005,446.342 -541.719,412.002 -540.791,377.243 '
        'C-547.67,202.72 -468.164,46.8556 -371.09,-51.6417 L-371.336,-51.872 C-316.617,-103.662 -258.074,-151.545 '
        '-223.448,-211.776 L-223.598,-211.862 C-206.376,-241.691 -196.299,-274.377 -193.357,-306.543 C-193.191,-308.633 '
        '-193.052,-310.739 -192.942,-312.86 L-192.871,-312.86 C-191.997,-326.837 -192.477,-340.674 -194.31,-354.092 '
        'C-372.183,-309.424 -548.528,-200.613 -715.123,-27.1739 L-715.123,-27.1744 Z M554.292,453.929 C655.605,330.418 '
        '715.629,178.329 715.629,5.96941 C554.707,-177.071 385.648,-292.062 211.927,-344.503 C211.997,-341.988 '
        '212.11,-339.466 212.268,-336.94 L212.34,-336.94 C212.449,-334.819 212.588,-332.714 212.755,-330.624 '
        'C215.697,-298.457 225.774,-265.771 242.995,-235.942 L242.845,-235.856 C277.471,-175.625 336.015,-127.742 '
        '390.734,-75.9521 L390.488,-75.7222 C487.562,22.7755 567.068,178.64 560.189,353.163 C561.146,388.985 '
        '558.234,424.363 554.292,453.929 Z M710.44,-92.748 C687.144,-273.17 596.795,-432.456 465.161,-544.835 '
        'C427.121,-539.287 369.818,-526.688 306.81,-503.359 L306.63,-503.667 C259.34,-485.186 229.73,-446.02 '
        '217.834,-399.391 C388.757,-352.253 555.363,-250.094 710.44,-92.748 Z"/></svg>'
    ),
    "schedule": (
        '<svg viewBox="-1460 -1743 2920 3202" fill="currentColor" aria-hidden="true"><path d="M-401.037,-1457.16 '
        'L-401.037,-1500.74 C-401.037,-1634.89 -509.012,-1742.87 -643.164,-1742.87 C-777.316,-1742.87 -885.292,-1634.89 '
        '-885.292,-1500.74 L-885.292,-1457.16 L-1109.42,-1457.16 C-1301.05,-1457.16 -1459.05,-1302.52 -1459.05,-1107.53 '
        'L-1459.05,1107.95 C-1459.05,1299.58 -1304.41,1457.58 -1109.42,1457.58 L1109.42,1457.58 C1301.05,1457.58 '
        '1455.69,1299.58 1459.05,1111.31 L1459.05,-1107.53 C1459.05,-1299.15 1304.41,-1457.16 1109.42,-1457.16 '
        'L890.583,-1457.16 L890.583,-1457.16 L890.583,-1500.74 C890.583,-1634.89 782.607,-1742.87 648.456,-1742.87 '
        'C514.304,-1742.87 406.328,-1634.89 406.328,-1500.74 L406.328,-1457.16 L-401.037,-1457.16 L-401.037,-1457.16 Z '
        'M-1352.6,-585.374 L1352.6,-582.257 L1352.6,1030.03 C1349.49,1204.56 1206.12,1351.04 1028.48,1351.04 '
        'L-1028.48,1351.04 C-1209.24,1351.04 -1352.6,1204.56 -1352.6,1026.92 L-1352.6,-585.374 L-1352.6,-585.374 '
        'Z"/><path d="M-23.0983,-405.188 C-196.157,-400.035 -354.897,-338.266 -481.447,-237.752 C-438.887,-233.155 '
        '-358.285,-219.38 -288.123,-189.551 L-288.118,-189.559 C-233.842,-171.274 -195.139,-130.453 -173.678,-79.4018 '
        'C-123.509,-88.9769 -73.2659,-94.3003 -23.0982,-95.3761 L-23.0982,-405.188 L-23.0983,-405.188 Z M-518.846,945.281 '
        'C-386.865,1064.39 -213.663,1138.72 -23.0982,1144.39 L-23.0982,-38.8864 C-68.0314,-38.0805 -113.032,-33.5074 '
        '-157.986,-25.1618 C-154.854,-6.96993 -153.567,11.8547 -154.18,30.9024 C-156.133,80.9746 -167.469,121.53 '
        '-187.029,156.688 C-189.055,160.598 -191.177,164.476 -193.395,168.318 L-193.744,168.116 C-235.205,235.073 '
        '-302.365,282.877 -368.113,342.934 L-368.001,343.044 C-449.041,418.519 -536.73,575.464 -541.35,755.208 '
        'C-542.371,834.064 -529.258,904.186 -518.846,945.281 Z M23.9995,1144.39 C223.182,1138.46 403.397,1057.53 '
        '537.396,928.846 C548.063,889.716 563.537,814.553 562.434,729.139 C557.813,549.395 470.125,392.45 389.084,316.975 '
        'L389.196,316.865 C323.448,256.808 256.288,209.004 214.827,142.047 L214.477,142.249 C212.26,138.407 '
        '210.138,134.529 208.112,130.619 C188.551,95.461 177.216,54.9055 175.263,4.83337 C175.019,-2.7461 '
        '175.076,-10.2906 175.43,-17.7736 C125.198,-29.4265 74.6661,-36.2862 23.9992,-38.3505 L23.9993,1144.39 '
        'L23.9995,1144.39 Z M456.699,-257.271 C334.637,-346.225 185.558,-400.377 23.9993,-405.188 L23.9992,-95.1379 '
        'C77.6747,-93.4389 131.211,-86.8649 184.422,-75.4042 C202.1,-140.226 244.631,-193.874 309.201,-215.628 '
        'L309.205,-215.62 C358.871,-236.735 413.766,-249.804 456.699,-257.271 Z M-527.804,-197.903 C-649.894,-84.225 '
        '-735.204,68.4214 -764.02,240.318 C-591.177,80.7007 -409.31,-22.109 -225.764,-67.9411 C-242.341,-104.352 '
        '-270.745,-133.883 -310.956,-149.595 L-311.151,-149.262 C-414.773,-187.625 -504.14,-199.185 -527.804,-197.903 Z '
        'M-774.187,340.183 C-774.548,349.944 -774.735,359.752 -774.735,369.602 C-774.735,567.173 -700.968,747.386 '
        '-579.45,884.226 C-583.523,852.809 -586.461,815.632 -585.456,778.003 C-592.904,589.065 -506.831,420.328 '
        '-401.74,313.695 L-402.006,313.446 C-342.768,257.378 -279.389,205.54 -241.903,140.335 L-242.066,140.242 '
        'C-223.422,107.949 -212.512,72.5634 -209.327,37.7403 C-209.147,35.4775 -208.997,33.1985 -208.878,30.9024 '
        'L-208.801,30.9024 C-207.855,15.7701 -208.374,0.790173 -210.359,-13.7356 C-402.923,34.6217 -593.833,152.42 '
        '-774.187,340.184 L-774.187,340.183 Z M600.073,861.023 C709.754,727.31 774.735,562.659 774.735,376.064 '
        'C600.522,177.907 417.5,53.4173 229.431,-3.35468 C229.506,-0.631402 229.629,2.0982 229.8,4.83337 L229.877,4.83337 '
        'C229.996,7.12948 230.146,9.4085 230.327,11.6709 C233.512,46.4944 244.421,81.8797 263.065,114.172 '
        'L262.903,114.266 C300.389,179.471 363.767,231.309 423.006,287.377 L422.74,287.626 C527.831,394.259 '
        '613.904,562.996 606.456,751.934 C607.492,790.714 604.34,829.014 600.073,861.023 Z M769.117,269.194 '
        'C743.897,73.8703 646.086,-98.5718 503.58,-220.233 C462.398,-214.227 400.362,-200.587 332.151,-175.331 '
        'L331.955,-175.665 C280.76,-155.657 248.704,-113.256 235.826,-62.7765 C420.866,-11.7444 601.232,98.8524 '
        '769.117,269.194 Z"/></svg>'
    ),
})


def loc(team):
    return nba_teams.LOCATION_NAMES.get(team, team or "TBD")


def fmt_record(r):
    r = r or {}
    return f'{r.get("wins", 0)}-{r.get("losses", 0)}'


def f1(v):
    return DASH if v is None else f"{v:.1f}"


def f0(v):
    return DASH if v is None else f"{int(round(v)):,}"


def final_text(d):
    ot = d.get("ot") or 0
    return "FINAL" + ("/OT" if ot == 1 else f"/{ot}OT" if ot > 1 else "")


def mid_text(d):
    """FINAL / FINAL/OT / FINAL/2OT, or a live game's clock ("4:12 - 3rd")."""
    if d.get("live"):
        return (d.get("status_detail") or "LIVE").upper()
    return final_text(d)


def tv(d):
    return d.get("networks") or "Local TV"


# ---------------------------------------------------------------- Page 1: game info card

def game_body_compact(d):
    t, ampm = p1.fmt_time(d.get("gametime"))
    small = f"<small>{ampm}</small>" if ampm else ""
    day, _time = p1.fmt_when(d)
    city = ((d.get("info") or {}).get("arena") or {}).get("city") or ""
    return (
        p1.linescore_html(d, mini=True) +
        '<div class="gc-row gc-1"><div class="gc-when">'
        f'<div class="time"{p1.lt_split(d)}>{esc(t)}{small}</div><div class="date">{esc(day)}</div></div>'
        f'<div class="network">{esc(tv(d))}</div></div>'
        # the arena takes the second line, beside the city, rather than the weather's spot up top --
        # it's longer than a temperature, and there it crowded the date
        f'<div class="gc-row gc-2"><div class="city">{esc(city)}</div>'
        f'<div class="network nba-arena-c">{esc(((d.get("info") or {}).get("arena") or {}).get("name") or "")}</div></div>'
    )


def game_body(d, hero=""):
    t, ampm = p1.fmt_time(d.get("gametime"))
    small = f"<small>{ampm}</small>" if ampm else ""
    final = bool(d.get("final") or d.get("live"))
    note = f'<div class="date nba-note">{esc(d["note"])}</div>' if d.get("note") else ""
    top = (f'<div class="game-top{" final-top" if final else ""}">'
           f'<div><div class="time"{p1.lt_split(d)}>{esc(t)}{small}</div><div class="date">{esc(p1.fmt_date(d.get("gameday")))}</div>{note}</div>'
           f'<div class="network">{esc(tv(d))}</div></div>')
    lead = hero + p1.linescore_html(d) + top if final else top + hero
    city = ((d.get("info") or {}).get("arena") or {}).get("city") or ""
    arena = ((d.get("info") or {}).get("arena") or {}).get("name") or ""
    return (f'{lead}<div class="game-bottom"><div class="city">{esc(city)}</div>'
            f'<div class="weather"><span class="temp temp-word temp-word-long nba-arena">{esc(arena)}</span></div></div>')


# ---------------------------------------------------------------- Page 1: team cards

INJ_CLASS = {"Out": "out", "Doubtful": "doubt", "Questionable": "ques", "Day-To-Day": "ques", "Probable": "ques",
             "Did Not Play": "out"}


def injuries_html(side, full):
    """Page 1's injury list: the top 3, starters first. A finished game lists who didn't play instead
    (injury, illness, rest -- not the coach's decision), from its box score."""
    ga = side.get("game_absences") or {}
    if ga.get("available"):
        rows = ga.get("top") or []
        if not rows:
            return '<li class="inj-none">Everyone available played</li>'
    else:
        rows = side.get("injuries") or []
        if not rows:
            text = "No injuries reported" if side.get("injury_report_out") else "Injury report not available"
            return f'<li class="inj-none">{text}</li>'
    out = []
    for r in rows[:3]:
        status = r.get("status") or ""
        name = r.get("name") if full else r.get("short")
        label = status if full and not r.get("kind") else (r.get("status_short") or status)
        out.append(f'<li>{p1.inj_who_html(r.get("position"), name, r)}'
                   f'<span class="inj-s"><i class="inj-dot inj-{INJ_CLASS.get(status, "ques")}"></i>'
                   f'<span class="inj-status">{esc(label)}</span></span></li>')
    return "".join(out)


def game_stats_html(gs):
    """A finished game's box score for one team, three lines of two like the NFL card's."""
    def ma(m, a):
        return DASH if m is None or a is None else f"{f0(m)}-{f0(a)}"

    def pct(m, a):
        return DASH if not a else f"{100 * m / a:.0f}%"
    cell = lambda label, val: f"<div><dt>{label}</dt><dd><b>{val}</b></dd></div>"
    return (
        '<div class="gstats">'
        f'<dl class="gs-line">{cell("Field Goals", ma(gs.get("fgm"), gs.get("fga")))}{cell("FG %", pct(gs.get("fgm") or 0, gs.get("fga")))}</dl>'
        f'<dl class="gs-line">{cell("3-Pointers", ma(gs.get("tpm"), gs.get("tpa")))}{cell("Rebounds", f0(gs.get("reb")))}</dl>'
        f'<dl class="gs-line">{cell("Assists", f0(gs.get("ast")))}{cell("Turnovers", f0(gs.get("tov")))}</dl>'
        "</div>")


def _ranks_html(r, pts_label, fg_label):
    return ('<div class="ranks">'
            f'<div class="rank-col"><h3>Offense</h3>{p1.big_rank(r.get("off_pts"), pts_label)}{p1.big_rank(r.get("off_fg"), fg_label)}</div>'
            f'<div class="rank-col"><h3>Defense</h3>{p1.big_rank(r.get("def_pts"), pts_label)}{p1.big_rank(r.get("def_fg"), fg_label)}</div>'
            "</div>")


def c_team(side, label, final=False):
    team = side.get("team")
    gs = side.get("game_stats") if final else None
    bottom = game_stats_html(gs) if gs else _ranks_html(side.get("ranks") or {}, "PTS", "FG%")
    return (
        f'<a class="card c-team" tabindex="0" data-detail="{label}-team" aria-label="{esc(team)} team">'
        f'{p1.card_title(team, abbr=True, cid=f"{label}-team", icons=NAV_ICONS)}'
        f'<div class="l-top"><div class="l-id">{img(team, 40)}</div><div class="l-rec">{p1.record_block(side, final)}</div></div>'
        f'<ul class="injuries c-inj">{injuries_html(side, full=False)}</ul>{bottom}</a>'
    )


def l_team(side, final=False):
    team = side.get("team")
    gs = side.get("game_stats") if final else None
    bottom = game_stats_html(gs) if gs else _ranks_html(side.get("ranks") or {}, "POINTS", "FG %")
    return (
        f'<div class="l-top"><div class="l-id">{img(team, 84, large=True)}</div>'
        f'<div class="l-rec">{p1.record_block(side, final)}</div></div>'
        f'<ul class="l-inj">{injuries_html(side, full=True)}</ul>{bottom}'
    )


# ---------------------------------------------------------------- Page 1: leaders card

LEADER_STATS = (("pts", "Points"), ("reb", "Rebounds"), ("ast", "Assists"), ("stl", "Steals"), ("blk", "Blocks"))


def _leader_extra(x, stat, scope):
    """The small line under a leader's name: the rest of the story behind the number."""
    if scope == "game":
        if stat == "pts":
            return f'{f0(x["fgm"])}-{f0(x["fga"])} FG · {f0(x["tpm"])}-{f0(x["tpa"])} 3PT'
        if stat == "reb":
            return f'{f0(x["oreb"])} OFF · {f0(x["dreb"])} DEF'
        if stat == "ast":
            return f'{f0(x["tov"])} TO'
        return f'{f0(x["min"])} MIN'
    if stat == "pts":
        fg = f'{x["fg_pct"]:.0f}% FG · ' if x.get("fg_pct") is not None else ""
        return f'{fg}{f1(x["min"])} MIN'
    if stat == "reb":
        return f'{f1(x["oreb"])} OFF · {f1(x["dreb"])} DEF'
    if stat == "ast":
        return f'{f1(x["tov"])} TO'
    return f'{x["gp"]} GP'


def leaders(lines_by_side, scope, tops, teams, team_games):
    """[{label, away, home}] -- each team's best in each stat (per game for the season, totals for a
    game). Season leaders need 40% of the team's games, so a cameo doesn't top the list."""
    out = []
    for stat, label in LEADER_STATS:
        row = {"key": stat, "label": label}
        for side in ("away", "home"):
            pool = lines_by_side.get(side) or []
            if scope == "season":
                n = team_games.get(side) or 0
                pool = [x for x in pool if x["gp"] >= 0.4 * n] or pool
            best = max(pool, key=lambda x: (x[stat], x["min"]), default=None)
            if not best or best[stat] <= 0:
                row[side] = None
                continue
            first, last = ps.split_name(best["name"])
            row[side] = {"name": f"{first[0]}. {last}" if first else last, "position": best["pos"],
                         "value": f0(best[stat]) if scope == "game" else f1(best[stat]),
                         "league_rank": (tops.get((teams[side], best["id"])) or {}).get(stat) if scope == "season" else None,
                         "extra": _leader_extra(best, stat, scope)}
        out.append(row)
    return out


def leader_cell(p):
    if not p:
        return f'<div class="ldr"><div class="ldr-v na"><span>{DASH}</span></div><div class="ldr-n">&nbsp;</div></div>'
    return (f'<div class="ldr"><div class="ldr-v"><span>{esc(p["value"])}</span>{p1.crown(p.get("league_rank"))}</div>'
            f'<div class="ldr-n"><span class="nm">{ps.esc_name(p["name"])}</span><span class="pos">{esc(p.get("position") or "")}</span></div>'
            f'<div class="ldr-x">{esc(p["extra"])}</div></div>')


def leader_rows(rows):
    return "".join(f'<div class="cmp-row">{leader_cell(r.get("away"))}<div class="cmp-lbl">{esc(r["label"])}</div>'
                   f'{leader_cell(r.get("home"))}</div>' for r in rows)


def pill_row(a, h):
    return (f'<div class="cmp-row cmp-head">{nba_helmets.pill_html(a, nba_teams.full_name(a))}<div></div>'
            f'{nba_helmets.pill_html(h, nba_teams.full_name(h))}</div>')


# ---------------------------------------------------------------- Page 2: Tip-Off and Arena

def _countdown(d, info, cls):
    if d.get("final"):
        return f'<div class="{cls} cd-done"><span class="cd-status">{esc(final_text(d))}</span></div>'
    if d.get("live"):
        return f'<div class="{cls} cd-done"><span class="cd-status">LIVE</span></div>'
    if d.get("postponed"):
        return f'<div class="{cls} cd-done"><span class="cd-status">PPD</span></div>'
    return gi._countdown(d, {"kickoff_utc": info.get("tipoff_utc")}, cls)


def _lose(mine, theirs):
    return " lose" if mine is not None and theirs is not None and mine < theirs else ""


def _meeting_row(a, h, m):
    sa, sh = (m.get("score") or {}).get(a), (m.get("score") or {}).get(h)
    tag = {"POST": "Playoffs", "PLAYIN": "Play-In", "CUP": "NBA Cup"}.get(m.get("phase"), "")
    where = f'@ {m.get("home")}'
    return (f'<li class="mt-row"><span class="mt-date">{esc(gi.fmt_meeting_date(m.get("date")))}'
            f'<small>{esc(where)}{" · " + esc(tag) if tag else ""}</small></span>'
            f'<span class="abbr{_lose(sa, sh)}">{esc(a)}</span><span class="sc{_lose(sa, sh)}">{f0(sa)}</span>'
            f'<span class="sc{_lose(sh, sa)}">{f0(sh)}</span><span class="abbr{_lose(sh, sa)}">{esc(h)}</span></li>')


def _series(a, h, ms):
    """"OKC leads 3-2" over the meetings listed."""
    wa = sum(1 for m in ms if ((m.get("score") or {}).get(a) or 0) > ((m.get("score") or {}).get(h) or 0))
    wh = len(ms) - wa
    if wa == wh:
        return f"Split {wa}-{wh}"
    return f"{a if wa > wh else h} leads {max(wa, wh)}-{min(wa, wh)}"


def tipoff_body(d, info, time_html):
    date_line, weekday = gi._date_parts(d)
    a, h = d["away"]["team"], d["home"]["team"]
    ms = info.get("meetings") or []
    if ms:
        meetings = (f'<p class="ko-line">Last {len(ms)} meeting{"s" if len(ms) > 1 else ""} '
                    f'<span class="ko-date-sm">{esc(_series(a, h, ms))}</span></p>'
                    f'<ul class="mt-list">{"".join(_meeting_row(a, h, m) for m in ms)}</ul>')
    else:
        meetings = '<p class="ko-line na">First meeting</p>'
    ref = info.get("referee")
    ref_html = f'<span>{esc(ref)}</span>' if ref else '<span class="na">TBA</span>'
    return ('<div class="ko-top">'
            f'<div class="ko-when">{time_html}<div class="ko-date">{esc(date_line)}</div><div class="ko-date">{esc(weekday)}</div></div>'
            f'{_countdown(d, info, "cd")}</div>'
            f'<div class="ko-lines"><div class="ko-tv"><span class="ko-net">{esc(tv(d))}</span></div>{meetings}</div>'
            f'<p class="ko-line ko-ref">Crew Chief: {ref_html}</p>')


def tipoff_condensed(d, info, time_html):
    date_line, weekday = gi._date_parts(d)
    a, h = d["away"]["team"], d["home"]["team"]
    ms = info.get("meetings") or []
    if ms:
        m = ms[0]
        sa, sh = (m.get("score") or {}).get(a), (m.get("score") or {}).get(h)
        meet = (f'<span class="mm"><span class="abbr{_lose(sa, sh)}">{esc(a)}</span><span class="sc{_lose(sa, sh)}">{f0(sa)}</span>'
                f'<span class="sc{_lose(sh, sa)}">{f0(sh)}</span><span class="abbr{_lose(sh, sa)}">{esc(h)}</span></span>')
        sub = f'{esc(gi.fmt_meeting_date(m.get("date")))} · {esc(_series(a, h, ms))}'
    else:
        meet, sub = gi._na("First meeting"), ""
    ref = info.get("referee")
    return (f'<div class="cc-top"><div>{time_html}<div class="cc-date">{esc(date_line)} {esc(weekday)}</div></div>'
            f'{_countdown(d, info, "cd-c")}</div>'
            f'<div class="strip">{gi._fact("TV", esc(tv(d)))}{gi._fact("Last Meeting", meet, sub)}'
            f'{gi._fact("Crew Chief", esc(ref) if ref else gi._na("TBA"))}</div>')


def _home_fact(d, a):
    if a.get("neutral"):
        return "Neutral Site", "Yes"
    return "Home Team", nba_teams.full_name(d["home"]["team"])


def arena_body(d):
    a = (d.get("info") or {}).get("arena") or {}
    label, value = _home_fact(d, a)
    return (f'<div class="st-head"><h2 class="st-name">{esc(a.get("name") or "Arena TBD")}</h2>{stadium_icons.svg("dome", "st-icon")}</div>'
            + (f'<div class="st-city"><span class="nb">{esc(a["city"])}</span></div>' if a.get("city") else "") +
            f'<div class="st-facts one"><div class="fact"><b class="nba-fact">{esc(value)}</b><span>{esc(label)}</span></div></div>')


def arena_condensed(d):
    a = (d.get("info") or {}).get("arena") or {}
    label, value = _home_fact(d, a)
    city = f'<div class="cc-city"><span class="nb">{esc(a.get("city"))}</span></div>' if a.get("city") else ""
    return (f'<div class="cc-top"><div class="cc-stn"><div class="st-name">{esc(a.get("name") or "Arena TBD")}</div>{city}</div>'
            f'{stadium_icons.svg("dome", "st-icon")}</div><div class="strip">{gi._fact(label, esc(value))}</div>')


def render_gameinfo_block(d, time_html):
    info = d.get("info")
    if not isinstance(info, dict):
        return ""
    cards = [("kickoff", "Tip-Off", tipoff_body(d, info, time_html), tipoff_condensed(d, info, time_html)),
             ("stadium", "Arena", arena_body(d), arena_condensed(d))]
    slots = "".join(
        f'<section class="slot"><a class="card p2k p2k-{cid}" tabindex="-1" aria-label="{name}">'
        f'<span class="peek peek-top">{p1.DOWN}{gi._title(cid, name)}</span><div class="body">{body}</div>'
        f'<span class="peek peek-bot">{p1.UP}{gi._title(cid, name)}</span></a></section>'
        for cid, name, body, _c in cards)
    dots = "".join(f'<button class="dot" type="button" aria-label="{name}">{gi.P2_ICONS.get(cid, "")}</button>'
                   for cid, name, _b, _c in cards)
    condensed = "".join(f'<a class="card cc cc-{cid}" tabindex="0" aria-label="{name}"><span class="card-title">'
                        f'{gi._title(cid, name)}</span>{c}</a>' for cid, name, _b, c in cards)
    return ('<div class="p2" data-page="game-info" aria-label="Game info" role="region">'
            f'<div class="p2-view p2-l deck">{slots}</div><nav class="dots p2-dots ic-dots" aria-label="Cards">{dots}</nav>'
            f'<div class="p2-view p2-c n{len(cards)}">{condensed}</div></div>')


# ---------------------------------------------------------------- Page 2: team pages

def _fmt_day(gameday):
    try:
        d = date.fromisoformat(str(gameday)[:10])
    except (TypeError, ValueError):
        return "Date TBD", ""
    return f"{MONTHS_UPPER[d.month - 1]} {d.day}", DAY_NAMES[d.weekday()]


def _fmt_time(gametime):
    t, ampm = p1.fmt_time(gametime)
    return "TBD" if t == "TBD" else f"{t} {ampm}"


def team_bar_head(side, opp, which, prefix):
    team = side.get("team")
    opp_abbr = f'<span class="abbr">{esc(opp or "TBD")}</span>'
    opp_html = f"@ {opp_abbr}" if which == "away" else f"{opp_abbr} @"
    return (f'<div class="tp-head tp-{which}" aria-hidden="true">{img(team, 46, which == "away", prefix)}'
            f'<span class="tp-name">{esc(loc(team))}</span>'
            f'<span class="tp-rec">{esc(fmt_record(side.get("record")))}</span><span class="tp-opp">{opp_html}</span></div>')


def _next_block(tpage, which, prefix):
    nxt = tpage.get("next") or {}
    opp = nxt.get("opponent")
    date_line, weekday = _fmt_day(nxt.get("gameday"))
    rest = nxt.get("rest_days")
    rest_html = DASH if rest is None else "B2B" if rest <= 0 else f'{rest}<small> DAY{"S" if rest != 1 else ""}</small>'
    miles = nxt.get("miles_traveled")
    facts = [("REST", rest_html), ("TRAVELED", DASH if miles is None else f"{miles:,}<small> MI</small>")]
    fact_html = "".join(f'<div class="ov-fact"><b>{v}</b><span>{esc(k)}</span></div>' for k, v in facts)
    vs = "@" if which == "away" else "vs"
    return ('<div class="ov-top"><div class="ov-next">'
            f'{img(opp, 40, prefix=prefix)}<div class="ov-next-txt"><span class="ov-next-lbl">THIS GAME</span>'
            f'<span class="ov-next-vs">{vs} <span class="abbr">{esc(opp or "TBD")}</span></span>'
            f'<span class="ov-next-date">{esc(date_line)} {esc(weekday).upper()}</span></div></div>'
            f'<div class="ov-facts">{fact_html}</div></div>')


def _recent(recent):
    if not recent:
        return '<p class="ov-empty">No games played yet</p>'
    rows = []
    for e in recent:
        date_line, _wd = _fmt_day(e.get("gameday"))
        res = e.get("result") or ""
        sc = e.get("score") or {}
        rows.append(f'<li class="rg-row"><span class="rg-date">{esc(date_line)}</span><span class="rg-vs">{"vs" if e.get("home") else "@"}</span>'
                    f'<span class="rg-opp abbr">{esc(e.get("opponent") or "")}</span>'
                    f'<span class="rg-res rg-{"win" if res == "W" else "loss"}">{esc(res)}</span>'
                    f'<span class="rg-score">{f0(sc.get("team"))}-{f0(sc.get("opp"))}</span></li>')
    return f'<ul class="rg-list">{"".join(rows)}</ul>'


def _gb(v):
    return "–" if not v else (f"{v:.1f}".rstrip("0").rstrip(".") if v % 1 == 0 else f"{v:.1f}")


def _pct(v):
    return f"{v:.3f}".lstrip("0") if v < 1 else "1.000"


def _division(standings, team, prefix):
    if not standings or not standings.get("rows"):
        return ""
    rows = "".join(
        f'<li class="st-row{" is-you" if r["team"] == team else ""}">{img(r["team"], 22, prefix=prefix)}'
        f'<span class="st-team abbr">{esc(r["team"])}</span><span class="st-w">{r["wins"]}</span>'
        f'<span class="st-l">{r["losses"]}</span><span class="st-t">{_pct(r["pct"])}</span>'
        f'<span class="st-pct">{esc(_gb(r["gb"]))}</span></li>' for r in standings["rows"])
    head = ('<div class="st-headrow" aria-hidden="true"><span></span><span></span>'
            '<span>W</span><span>L</span><span>PCT</span><span>GB</span></div>')
    conf = standings["division"].split(" · ")[0]
    href = f'{prefix}standings.html#{conf.lower()}-{standings["div"].lower()}'
    return (f'<div class="ov-standings nba-div"><h3><span class="st-link" role="link" tabindex="0" data-href="{esc(href)}">'
            f'{esc(standings["div"])}{tp.STANDINGS_CHEV}</span></h3>{head}<ul class="st-list">{rows}</ul></div>')


def overview_body(side, tpage, which, prefix):
    sp = tpage.get("splits") or {}
    lead = "".join(f'<div class="ov-byebig"><b>{esc(sp[k])}</b><span>{label}</span></div>'
                   for k, label in (("home", "HOME"), ("road", "ROAD"), ("l10", "LAST 10")) if sp.get(k))
    return ((f'<div class="ov-lead nba-lead">{lead}</div>' if lead else "")
            + _next_block(tpage, which, prefix)
            + '<h3 class="ov-h">Last 5 Games</h3>' + _recent(tpage.get("recent"))
            + _division(tpage.get("standings"), side.get("team"), prefix))


def _inj_items(rows):
    items = []
    for r in rows:
        status = r.get("status") or ""
        detail = r.get("designation")
        label = f"{r.get('status_short') or status} · {detail}" if detail else status
        label = tp._fit_status(r.get("name") or "", [f"{status} · {detail}", label, r.get("status_short") or status]
                               if detail else [status, r.get("status_short") or status])
        items.append(f'<li><span class="inj-who"><span class="inj-pos">{esc(r.get("position") or "")}</span>'
                     f'<span class="inj-name">{ps.esc_name(r.get("name"))}</span></span>'
                     f'<span class="inj-s"><i class="inj-dot inj-{INJ_CLASS.get(status, "ques")}"></i>{esc(label)}</span></li>')
    return f'<ul class="l-inj full-inj">{"".join(items)}</ul>'


def injuries_body(tpage, absences=None):
    rows = tpage.get("injuries_full") or []
    report = _inj_items(rows) if rows else '<p class="ov-empty">No injuries reported</p>'
    ga = absences or {}
    if not ga.get("available"):
        return f'<div class="inj-sections inj-fit"><h3 class="ov-h inj-h">Injury Report</h3>{report}</div>'
    dnp = ga.get("dnp") or []
    return ('<div class="inj-sections inj-fit"><h3 class="ov-h inj-h">Did Not Play</h3>'
            + (_inj_items(dnp) if dnp else '<p class="ov-empty">Everyone available played</p>')
            + f'<h3 class="ov-h inj-h">Pre-game Injury Report</h3>{report}</div>')


STAT_ROWS = [("points", "Points", "per game", f1, False), ("fg_pct", "Field Goal %", None, f1, True),
             ("three_pct", "3-Point %", None, f1, True), ("threes", "3-Pointers Made", "per game", f1, False),
             ("rebounds", "Rebounds", "per game", f1, False), ("assists", "Assists", "per game", f1, False),
             ("turnovers", "Turnovers", "per game · forced", f1, False)]
SINGLE_STATS = [("diff", "Point Diff.", True), ("pace", "Pace", False), ("steals", "Steals", False), ("blocks", "Blocks", False)]


def _stat_cell(value, rank, fmt=f1, pct=False, signed=False):
    if value is None or rank is None:
        return f'<div class="stat"><span class="stat-v na">{DASH}</span></div>'
    disp = f"{value:+.1f}" if signed else fmt(value) + ("%" if pct else "")
    return (f'<div class="stat"><span class="stat-v">{esc(disp)}</span>'
            f'<span class="stat-rank" style="color:{p1.rank_color(rank)}">{rank}{esc(p1.ordinal(rank))}</span></div>')


def stats_body(stats):
    stats = stats or {}
    rows = []
    for key, label, sub, fmt, pct in STAT_ROWS:
        s = stats.get(key) or {}
        rows.append(tp._stat_row(label, sub, _stat_cell(s.get("off_value"), s.get("off_rank"), fmt, pct),
                                 _stat_cell(s.get("def_value"), s.get("def_rank"), fmt, pct)))
    singles = [(label, _stat_cell((stats.get(k) or {}).get("value"), (stats.get(k) or {}).get("rank"), signed=sg))
               for k, label, sg in SINGLE_STATS]
    rows.append(tp._stat_row_singles(singles))
    return ('<div class="stat-head"><span>Offense</span><span></span><span>Defense</span></div>'
            f'<div class="stat-list nba-stats">{"".join(rows)}</div>')


def schedule_body(tpage, prefix):
    rows = []
    for e in tpage.get("schedule") or []:
        try:
            d = date.fromisoformat(str(e.get("gameday"))[:10])
            date_html = f'<span class="sc-date">{DAY_NAMES[d.weekday()][:3].upper()} {d.month}/{d.day}</span>'
        except (TypeError, ValueError):
            date_html = '<span class="sc-date na">DATE TBD</span>'
        opp = e.get("opponent")
        if e.get("postponed"):
            mid = '<span class="sc-time">Postponed</span>'
        elif e.get("final"):
            res = e.get("result") or ""
            sc = e.get("score") or {}
            mid = (f'<span class="sc-res sc-{"win" if res == "W" else "loss"}">{esc(res)}</span>'
                   f'<span class="sc-score">{f0(sc.get("team"))}-{f0(sc.get("opp"))}</span>')
        else:
            mid = f'<span class="sc-time"{local_time.attrs(e.get("gameday"), e.get("gametime"))}>{esc(_fmt_time(e.get("gametime")))}</span>'
        rec = fmt_record(e["record_after"]) if e.get("final") and e.get("record_after") and e.get("phase") == "REG" else ""
        rows.append(f'<li class="sc-row{" sc-this" if e.get("this") else ""}"><span class="sc-wk">{esc(e.get("number") or "")}</span>'
                    f'{date_html}<span class="sc-vs">{"vs" if e.get("home") else "@"}</span>{img(opp, 20, prefix=prefix)}'
                    f'<span class="sc-opp abbr">{esc(opp or "")}</span>{mid}<span class="sc-rec">{esc(rec)}</span></li>')
    return f'<ul class="sc-list" style="--n:{len(rows)}">{"".join(rows)}</ul>'


def render_team_block(side, which, prefix="../"):
    tpage = side.get("team_page")
    if not isinstance(tpage, dict):
        return ""
    cards = [("overview", "Overview", overview_body(side, tpage, which, prefix)),
             ("injuries", "Injuries", injuries_body(tpage, side.get("game_absences"))),
             ("stats", "Team Stats", stats_body(tpage.get("stats"))),
             ("schedule", "Schedule", schedule_body(tpage, prefix))]
    slots = "".join(
        f'<section class="slot"><a class="card p2k p2k-{cid}" tabindex="-1" aria-label="{esc(name)}">'
        f'<span class="peek peek-top">{p1.DOWN}{tp._title(cid, name, TEAM_ICONS)}</span><div class="body">{body}</div>'
        f'<span class="peek peek-bot">{p1.UP}{tp._title(cid, name, TEAM_ICONS)}</span></a></section>' for cid, name, body in cards)
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(name)}">{TEAM_ICONS.get(cid, "")}</button>'
                   for cid, name, _b in cards)
    return (f'<div class="p2 p2-team" data-page="{which}-team" aria-label="{esc(side.get("team") or "Team")} team info" role="region">'
            f'<div class="p2-view p2-l deck">{slots}</div><nav class="dots p2-dots ic-dots" aria-label="Cards">{dots}</nav></div>')


# ---------------------------------------------------------------- Page 2: player stats

def _ma(m, a, scope):
    return f"{f0(m)}-{f0(a)}" if scope == "game" else f"{f1(m)}-{f1(a)}"


def _num(scope):
    return f0 if scope == "game" else f1


def _pc(v):
    return DASH if v is None else f"{v:.1f}"


# (label, value text, sort value) per column; scope decides totals (a game) or per-game averages
def scoring_cols(scope):
    """A game: made-attempted for each kind of shot. The season: the percentages -- averaged
    made-attempted pairs ("10.2-20.6") don't fit a phone's width beside the rest; the 3-Pointers
    leaders are on the Stat Leaders page."""
    n = _num(scope)
    if scope == "game":
        return [("MIN", lambda r: n(r["min"]), lambda r: r["min"]), ("PTS", lambda r: n(r["pts"]), lambda r: r["pts"]),
                ("FG", lambda r: _ma(r["fgm"], r["fga"], scope), lambda r: r["fgm"]),
                ("3PT", lambda r: _ma(r["tpm"], r["tpa"], scope), lambda r: r["tpm"]),
                ("FT", lambda r: _ma(r["ftm"], r["fta"], scope), lambda r: r["ftm"]),
                ("+/-", lambda r: f'{r["pm"]:+.0f}', lambda r: r["pm"])]
    return [("GP", lambda r: f0(r["gp"]), lambda r: r["gp"]), ("MIN", lambda r: n(r["min"]), lambda r: r["min"]),
            ("PTS", lambda r: n(r["pts"]), lambda r: r["pts"]), ("FG%", lambda r: _pc(r["fg_pct"]), lambda r: r["fg_pct"]),
            ("3P%", lambda r: _pc(r["tp_pct"]), lambda r: r["tp_pct"]), ("FT%", lambda r: _pc(r["ft_pct"]), lambda r: r["ft_pct"])]


def rebounding_cols(scope):
    n = _num(scope)
    return [("REB", lambda r: n(r["reb"]), lambda r: r["reb"]), ("OREB", lambda r: n(r["oreb"]), lambda r: r["oreb"]),
            ("DREB", lambda r: n(r["dreb"]), lambda r: r["dreb"]), ("MIN", lambda r: n(r["min"]), lambda r: r["min"])]


def playmaking_cols(scope):
    n = _num(scope)
    ratio = lambda r: r["ast_t"] / r["tov_t"] if r["tov_t"] else None
    return [("AST", lambda r: n(r["ast"]), lambda r: r["ast"]), ("TO", lambda r: n(r["tov"]), lambda r: r["tov"]),
            ("A/TO", lambda r: DASH if ratio(r) is None else f"{ratio(r):.1f}", ratio),
            ("MIN", lambda r: n(r["min"]), lambda r: r["min"])]


def defense_cols(scope):
    n = _num(scope)
    pm = (lambda r: f'{r["pm"]:+.0f}') if scope == "game" else (lambda r: f'{r["pm"]:+.1f}')
    return [("STL", lambda r: n(r["stl"]), lambda r: r["stl"]), ("BLK", lambda r: n(r["blk"]), lambda r: r["blk"]),
            ("PF", lambda r: n(r["pf"]), lambda r: r["pf"]), ("+/-", pm, lambda r: r["pm"])]


# (card id -- the NFL's, so its icon and styles come along -- title, columns, starting order,
#  {column: stat that earns a league top-3 bar}, how many the condensed view shows)
PS_CARDS = [
    ("passing", "Scoring", scoring_cols, lambda r: (-r["pts"], -r["min"]), {"PTS": "pts"}, 3),
    ("rushing", "Rebounding", rebounding_cols, lambda r: (-r["reb"], -r["min"]), {"REB": "reb"}, 2),
    ("receiving", "Playmaking", playmaking_cols, lambda r: (-r["ast"], -r["min"]), {"AST": "ast"}, 2),
    ("defense", "Defense", defense_cols, lambda r: (-(r["stl"] + r["blk"]), -r["min"]), {"STL": "stl", "BLK": "blk"}, 2),
]
PLACES = {1: "1st", 2: "2nd", 3: "3rd"}


def _name(r):
    first, last = ps.split_name(r["name"])
    top = f'<span class="ps-fn">{ps.esc_name(first)}</span> ' if first else '<span class="ps-fn"></span>'
    num = f'#{r["jersey"]}' if r.get("jersey") not in (None, "") else ""
    return (f'<span class="ps-nm">{top}<span class="ps-no">{esc(num)}</span>'
            f'<span class="ps-ln"><span class="ps-lt">{"&nbsp;".join(ps.esc_name(w) for w in last.split())}</span></span> '
            f'<span class="ps-pos">{esc(r["pos"])}</span></span>')


def _short_name(r):
    first, last = ps.split_name(r["name"])
    who = f"{esc(first[0])}.&nbsp;{ps.esc_name(last)}" if first else ps.esc_name(last)
    return f'<span class="ps-nm ps-nm1"><span class="ps-ln">{who}</span></span>'


def _meta(r):
    num = f'#{r["jersey"]}' if r.get("jersey") not in (None, "") else ""
    return f'{f"<span class=ps-no>{esc(num)}</span> " if num else ""}<span class="ps-pos">{esc(r["pos"])}</span>'


def _cell(text, value, place):
    inner = (f'<span class="ps-md ps-md{place}" title="{PLACES[place]} in the NBA">{esc(text)}</span>' if place else esc(text))
    return f'<td data-v="{value:g}">{inner}</td>' if isinstance(value, (int, float)) else f"<td>{inner}</td>"


def _table(rows, cols, empty, medals, sortable=True, short=False):
    if not rows:
        return f'<p class="ps-empty">{esc(empty)}</p>'
    head = "".join(f'<th scope="col" aria-sort="none"><button type="button" class="ps-sort">{esc(c[0])}</button></th>' if sortable
                   else f'<th scope="col"><span class="ps-lbl">{esc(c[0])}</span></th>' for c in cols)
    meta_head = '<th scope="col" class="ps-mh"><span class="vh">Number and position</span></th>' if short else ""
    body = "".join(
        f'<tr data-i="{i}"><th scope="row">{_short_name(r) if short else _name(r)}</th>'
        + (f'<td class="ps-meta">{_meta(r)}</td>' if short else "")
        + "".join(_cell(fmt(r), val(r), (r.get("medals") or {}).get(medals.get(label)) if medals.get(label) else None)
                  for label, fmt, val in cols) + "</tr>"
        for i, r in enumerate(rows))
    return (f'<div class="ps-tw"><table class="ps-t"><thead><tr><th scope="col"><span class="vh">Player</span></th>{meta_head}{head}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def render_players_block(d, stats, scope):
    """stats = {abbr: [player lines]} -- the hidden .p2 layer for Player Stats."""
    away, home = d["away"]["team"], d["home"]["team"]
    teams = (away, home)
    empty = "None this game" if scope == "game" else ("No games played yet" if not any(stats.values()) else "None this season")
    scope_lbl = lambda extra="": f'<span class="ps-scope{extra}">{"Game Stats" if scope == "game" else "Season Stats · Per Game"}</span>'
    tabs = "".join(f'<button type="button" class="ps-tab{" on" if i == 0 else ""}" data-team="{esc(t)}" '
                   f'aria-pressed="{"true" if i == 0 else "false"}">{nba_helmets.pill_html(t)}</button>' for i, t in enumerate(teams))
    slots, cards = [], []
    for cid, title, colf, key, medals, n_cond in PS_CARDS:
        cols = colf(scope)
        panes = "".join(f'<div class="ps-pane{" on" if i == 0 else ""}" data-team="{esc(t)}">'
                        f'{_table(sorted(stats.get(t) or [], key=key), cols, empty, medals)}</div>' for i, t in enumerate(teams))
        slots.append(f'<section class="slot"><a class="card p2k p2k-ps p2k-{cid}" tabindex="-1" aria-label="{esc(title)}">'
                     f'<span class="peek peek-top">{p1.DOWN}{ps._title(cid, title)}</span>'
                     f'<div class="body">{scope_lbl()}<div class="ps-sw">{tabs}</div><div class="ps-scroll">{panes}</div></div>'
                     f'<span class="peek peek-bot">{p1.UP}{ps._title(cid, title)}</span></a></section>')
        short_cols = [c for c in cols if c[0] not in ("GP", "MIN")][:6]
        cpanes = "".join(f'<div class="pc-p{" on" if i == 0 else ""}" data-team="{esc(t)}">'
                         f'{_table(sorted(stats.get(t) or [], key=key)[:n_cond], short_cols, empty, medals, sortable=False, short=True)}</div>'
                         for i, t in enumerate(teams))
        cards.append(f'<a class="card cc pc-{cid} pc-row" tabindex="0" aria-label="{esc(title)}">'
                     f'<span class="card-title">{ps._title(cid, title)}</span>{cpanes}</a>')
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(t)}">{ps.PS_ICONS.get(c, "")}</button>' for c, t, *_ in PS_CARDS)
    return ('<div class="p2 p2-ps" data-page="leaders" aria-label="Player stats" role="region">'
            f'<div class="p2-view p2-l deck">{"".join(slots)}</div><nav class="dots p2-dots ic-dots" aria-label="Cards">{dots}</nav>'
            f'<div class="p2-view p2-c pc"><div class="ps-sw pc-sw">{tabs}</div>{scope_lbl(" pc-scope")}{"".join(cards)}</div></div>')


# ---------------------------------------------------------------- the page

def header_scores(d):
    score = d.get("score") if (d.get("final") or d.get("live")) else None
    if not score:
        return "", ""
    a_s, h_s = score.get("away"), score.get("home")
    a_cls = h_cls = "hscore"
    if d.get("final") and a_s is not None and h_s is not None:
        if a_s > h_s:
            h_cls += " lose"
        elif h_s > a_s:
            a_cls += " lose"
    return f'<span class="{a_cls}">{f0(a_s)}</span>', f'<span class="{h_cls}">{f0(h_s)}</span>'


def win_side(d):
    s = d.get("score") if d.get("final") else None
    if not s or s.get("away") is None or s.get("home") is None:
        return None
    return "away" if s["away"] > s["home"] else "home" if s["home"] > s["away"] else None


def final_label_html(d):
    return f'<span class="tri tri-a">{p1.WIN_TRI}</span>{esc(mid_text(d))}<span class="tri tri-h">{p1.WIN_TRI}</span>'


def render_p1_block(d, stats, scope, tops, team_games, prefix="../", root="../../"):
    """prefix: the path back to site/nba/; root: back to site/ (the menu reaches the NFL pages too)."""
    away, home = d.get("away") or {}, d.get("home") or {}
    a, h = away.get("team") or "TBD", home.get("team") or "TBD"
    final = bool(d.get("final") or d.get("live"))
    a_score, h_score = header_scores(d)
    when_day, when_time = p1.fmt_when(d)
    lead = leaders({"away": stats.get(a) or [], "home": stats.get(h) or []}, scope, tops, {"away": a, "home": h}, team_games)
    rows = leader_rows(lead)
    leaders_name = "Game Leaders" if scope == "game" else "Season Leaders"
    row_html = lambda big: (
        f'<div class="side away">{img(a, 44, True, large=big, prefix=prefix)}<span class="abbr">{esc(a)}</span>{a_score}</div>'
        f'<div class="mid"><span class="at{" at-final" if final else ""}">{final_label_html(d) if final else "@"}</span>'
        f'<span class="when"><span>{esc(when_day)}</span><span{local_time.attrs(d.get("gameday"), d.get("gametime"))}>{esc(when_time)}</span></span>'
        f'<span class="final-lbl">{final_label_html(d)}</span></div>'
        f'<div class="side home">{h_score}<span class="abbr">{esc(h)}</span>{img(h, 44, large=big, prefix=prefix)}</div>')
    hero = f'<div class="hero" aria-hidden="true"><div class="teams">{row_html(True)}</div></div>'
    day_href = f"{prefix}index.html#day-{d.get('week_key')}"
    bar = ('<header class="bar"><div class="bar-in">'
           f'<div class="teams" aria-label="{esc(nba_teams.full_name(a))} at {esc(nba_teams.full_name(h))}">{row_html(False)}</div>'
           f'{team_bar_head(away, h, "away", prefix)}{team_bar_head(home, a, "home", prefix)}</div></header>'
           '<nav class="bbar" aria-label="Page controls"><div class="bbar-in">' + theme.menu_html(root, "nba-games")
           + f'<a class="week" href="{esc(day_href)}">{p1.CHEV}<span>{esc(d.get("week_label") or "")}</span></a>'
           f'<a class="week p2-back" href="#" aria-label="Back to {esc(a)} at {esc(h)}">{p1.CHEV}'
           f'<span><span class="abbr">{esc(a)}</span> @ <span class="abbr">{esc(h)}</span></span></a>'
           f'<button class="toggle" type="button"><span class="i-plus">{p1.PLUS}</span><span class="i-minus">{p1.MINUS}</span></button>'
           "</div></nav>")
    condensed = ('<div class="view view-c" aria-label="Condensed matchup">'
                 f'<a class="card c-game" tabindex="0" data-detail="game-info" aria-label="Game info">{p1.card_title("Game Info", cid="game-info", icons=NAV_ICONS)}{game_body_compact(d)}</a>'
                 f'<div class="c-teams">{c_team(away, "away", final and d.get("final"))}{c_team(home, "home", final and d.get("final"))}</div>'
                 f'<a class="card c-cmp" tabindex="0" data-detail="leaders" aria-label="{leaders_name}">{p1.card_title(leaders_name, cid="leaders", icons=NAV_ICONS)}'
                 f'<div class="c-cmp-in">{pill_row(a, h)}{rows}</div></a></div>')
    cards = [("game-info", "Game Info", "game", game_body(d, hero)),
             ("away-team", loc(a), "team", l_team(away, bool(d.get("final")))),
             ("home-team", loc(h), "team", l_team(home, bool(d.get("final")))),
             ("leaders", leaders_name, "compare", pill_row(a, h) + rows)]
    slots = "".join(
        f'<section class="slot"><a class="card {kind}" tabindex="-1" data-detail="{cid}" aria-label="{esc(name)}">'
        f'<span class="peek peek-top">{p1.DOWN}<span class="ttl">{p1.title_icon(cid, NAV_ICONS)}<span class="{"abbr" if kind == "team" else ""}">{esc(name)}</span></span></span>'
        f'<div class="body">{body}</div>'
        f'<span class="peek peek-bot">{p1.UP}<span class="ttl">{p1.title_icon(cid, NAV_ICONS)}<span class="{"abbr" if kind == "team" else ""}">{esc(name)}</span></span></span></a></section>'
        for cid, name, kind, body in cards)
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(name)}">{NAV_ICONS.get(cid, "")}</button>' for cid, name, _k, _b in cards)
    large = f'<div class="view view-l deck" aria-label="Expanded matchup">{slots}</div><nav class="dots" aria-label="Cards">{dots}</nav>'
    t, ampm = p1.fmt_time(d.get("gametime"))
    time_html = f'<div class="time"{p1.lt_split(d)}>{esc(t)}{f"<small>{ampm}</small>" if ampm else ""}</div>'
    blocks = {}
    for key, make in (("game-info", lambda: render_gameinfo_block(d, time_html)),
                      ("away-team", lambda: render_team_block(away, "away", prefix)),
                      ("home-team", lambda: render_team_block(home, "home", prefix)),
                      ("leaders", lambda: render_players_block(d, stats, scope))):
        try:
            blocks[key] = make()
        except Exception:   # a deep dive's trouble never costs the game its page
            blocks[key] = ""
    has = " ".join(k for k, b in blocks.items() if b)
    win = win_side(d)
    attrs = (" data-final" if final else "") + (f' data-win="{win}"' if win else "") + (f' data-has-detail="{has}"' if has else "")
    return (f'<div class="p1" data-view="large" data-head="card"{attrs} data-game="{esc(d.get("game_id"))}">'
            f'{bar}{condensed}{large}{"".join(blocks.values())}</div>')


# NBA-only touches, appended to the NFL stylesheet: the arena's name where the weather was, the
# last 5 meetings, three record splits where the bye week was, this game's row on the schedule
EXTRA_CSS = """
.p1 .weather .nba-arena{display:block;max-width:12em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:15px;font-weight:600;line-height:1.2}
.p1 .nba-arena-c{min-width:0;overflow:hidden;text-overflow:ellipsis}
.p1 .game-bottom .weather,.p1 .gc-1 .weather{min-width:0;flex:0 1 auto}
.p1 .game-bottom .city{flex:1 1 auto;min-width:0;margin-right:10px}
.nba-note{font-size:12px;color:var(--aag-text-2);margin-top:2px}
.mt-list{list-style:none;display:flex;flex-direction:column;gap:2px;margin:6px auto 0;max-width:340px}
.mt-row{display:grid;grid-template-columns:1fr 3.2em 2.4em 2.4em 3.2em;align-items:center;gap:4px;font-size:15px}
.mt-row .abbr{font-size:16px;text-align:center}
.mt-row .sc{font-family:Teko,Inter,system-ui,sans-serif;font-weight:700;font-size:20px;text-align:center;font-variant-numeric:tabular-nums}
.mt-row .lose{opacity:.3}
.mt-date{display:flex;flex-direction:column;text-align:left;font-size:12px;line-height:1.15;white-space:nowrap}
.mt-date small{font-size:10px;color:var(--aag-text-3)}
.nba-lead{display:flex;justify-content:space-around;gap:8px}
.nba-lead .ov-byebig{margin-left:0}
.nba-lead .ov-byebig b{font-size:32px}
.sc-row.sc-this{font-weight:700;background:var(--aag-tile-hover);border-radius:6px}
/* three-digit scores and records like 41-26: wider columns than the NFL's */
.p1 .sc-row{grid-template-columns:18px 54px 14px 20px 1fr 12px 58px 40px;gap:5px}
.p1 .sc-rec{white-space:nowrap}
.p1 .rg-score{width:62px;white-space:nowrap}
.p1 .game-bottom .city{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nba-div .st-row,.nba-div .st-headrow{grid-template-columns:22px 1fr 24px 24px 40px 32px}
.fact b.nba-fact{font-size:22px}
"""


_SVG_RE = re.compile(r"<svg\b([^>]*)>(.*?)</svg>", re.S)
_NUM_RE = re.compile(r"-?\d+\.\d+")
_D_RE = re.compile(r'\bd="([^"]*)"')


def compact_svgs(block, min_len=600):
    """Each game page carries the NFL's card icons several times over (titles, slivers, nav dots) --
    over half its weight. Each big one goes in once, as a group at the top of the block, and every
    use of it becomes a <use> pointing there; their drawings, thousands of units across, lose the
    decimals in their coordinates (a 20px icon can't show them). The block is mounted in a shadow root
    of its own in Page 0's overlay, so the ids never meet another game's."""
    symbols, ids = [], {}

    def swap(m):
        attrs, inner = m.group(1), m.group(2)
        if len(m.group(0)) < min_len or "viewBox" not in attrs:
            return m.group(0)
        inner = _D_RE.sub(lambda d: 'd="' + _NUM_RE.sub(lambda n: str(round(float(n.group(0)))), d.group(1)) + '"', inner)
        key = (attrs, inner)
        if key not in ids:
            ids[key] = f"s{len(ids)}"
            symbols.append(f'<g id="{ids[key]}">{inner}</g>')
        return f'<svg{attrs}><use href="#{ids[key]}"/></svg>'

    body = _SVG_RE.sub(swap, block)
    if not symbols:
        return block
    # plain groups, not <symbol>s: a <use> draws a group in the using <svg>'s own coordinates, so each
    # icon keeps its viewBox exactly as before
    sprite = f'<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>{"".join(symbols)}</defs></svg>'
    i = body.index(">") + 1   # just inside the .p1 block
    return body[:i] + sprite + body[i:]


def p1_css():
    """The stylesheet every game page uses (and Page 0 hands its overlay), the NFL's plus EXTRA_CSS."""
    import temp_colors
    return p1.P1_CSS + gi.P2_CSS + tp.P3_CSS + ps.P4_CSS + temp_colors.TC_CSS + EXTRA_CSS


def render_standalone(d, block):
    a, h = d["away"]["team"], d["home"]["team"]
    title = f"{a} @ {h} · {d.get('week_label') or ''} · NBA · At A Glance"
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            "<meta name='theme-color' content='#F3F3EE'>"
            f"<script>{theme.THEME_HEAD_JS}</script><title>{esc(title)}</title>"
            f"{logo.favicon_links('../../')}"
            "<link rel='preconnect' href='https://fonts.googleapis.com'><link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
            "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
            "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
            # the stylesheet and script are shared files here (1,300 games' worth of copies would
            # outweigh the pages); Page 0 hands its overlay the same stylesheet from its own copy
            "<link id='p1-css' rel='stylesheet' href='game.css'>"
            f"<style>{theme.THEME_CSS}html,body{{margin:0;background:var(--aag-bg)}}</style></head><body>"
            f"{block}<script>{theme.THEME_JS}</script><script>{local_time.JS}</script><script src='game.js'></script><script>AAG_P1.init(document);</script>"
            "</body></html>")


def write_all(data, site_dir, warnings):
    """site/nba/game/<id>.html for every game, plus the shared game.css / game.js. Returns the count."""
    out_dir = os.path.join(site_dir, "game")
    shutil.rmtree(out_dir, ignore_errors=True)   # no pages left over from a game that's gone (or another season)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "game.css"), "w", encoding="utf-8") as f:
        f.write(p1_css())
    with open(os.path.join(out_dir, "game.js"), "w", encoding="utf-8") as f:
        f.write(p1.P1_JS)
    season = nba_stats.Season(data.get("player_games"))
    pg = data.get("player_games") or {}
    count = 0
    for gid, d in (data.get("game_details") or {}).items():
        try:
            a, h = d["away"]["team"], d["home"]["team"]
            day = d.get("gameday") or "9999-12-31"
            before = day if d.get("game_type") in ("REG", "CUP", "PRE") else "9999-12-31"
            scope = "season"
            stats = {}
            if d.get("final") and d.get("game_type") != "PRE":
                game = {t: nba_stats.game_lines(pg.get(t), gid) for t in (a, h)}
                if any(game.values()):
                    scope, stats = "game", game
            if scope == "season":
                if d.get("game_type") == "PRE":
                    stats = {a: [], h: []}
                else:
                    tops = season.tops(before)
                    stats = {t: season.lines(t, before) for t in (a, h)}
                    for t, lines in stats.items():
                        for x in lines:
                            x["medals"] = tops.get((t, x["id"]), {})
            tops = season.tops(before) if d.get("game_type") != "PRE" else {}
            team_games = {"away": season.team_games(a, before), "home": season.team_games(h, before)}
            block = compact_svgs(render_p1_block(d, stats, scope, tops, team_games))
            safe = "".join(ch for ch in str(gid) if ch.isalnum() or ch in "_-")
            with open(os.path.join(out_dir, f"{safe}.html"), "w", encoding="utf-8") as f:
                f.write(render_standalone(d, block))
            count += 1
        except Exception:
            warnings.append(f"render_nba_game {gid}: {traceback.format_exc(limit=2)}")
    return count

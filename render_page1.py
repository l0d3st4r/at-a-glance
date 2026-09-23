"""
Page 1 -- the matchup page. One standalone file per game: site/game/<game_id>.html

Design = Jason's approved v8 preview (2026-09-16):
  - two views of the same page, switched with the +/− button in the top bar
      * expanded (default every time the page opens): pinned top bar with
        mini helmets + AWAY @ HOME, and a pinned bottom bar with "‹ Week N"
        and the +/− toggle (moved to the bottom 2026-09-17); one card per screen that
        snaps while scrolling, slivers of the cards above/below with a label,
        position dots on the right
      * condensed: every card on one screen, same top bar
  - finished games: final score in the top bar next to each abbreviation (loser
    faded), and the Leaders card shows each team's leaders in THAT game, no crowns
  - cards: Game Info, away team, home team, Leaders
  - team cards: last-game arrow (green up = W, red down = L, yellow line = T),
    record, top 3 injuries (starters first), offense/defense ranks
  - leaders: each team's leader in 5 stats, crown when top 3 in the league
  - cards, borders, hover, top bar, week pill, 600px column, Bold abbreviations
    all match Page 0

How it opens from Page 0: render_html.py adds a script to index.html that zooms
into the tapped tile, flies its helmets/abbreviations/scores up into this page's
top bar, then brings the cards in. It fetches this file and shows its .p1 block
inside a shadow root (so Page 0's CSS and Page 1's CSS can't clash). Swiping
left/right moves between the week's games; pinching in minimizes back into the tile.
Opened directly (shared link), the file works on its own too.

Data comes from data/matchups.json -> "game_details" (see page1_data.py).
Defensive like render_html.py: a missing value shows "—", and a game that
fails to render is skipped with a warning instead of breaking the build.
"""

import html
import os
import traceback
from datetime import date

import helmets
import render_page2gameinfo
import render_page2team
import theme

MONTHS_UPPER = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TEAM_NAMES = {
    "ARI": "Cardinals", "ATL": "Falcons", "BAL": "Ravens", "BUF": "Bills", "CAR": "Panthers", "CHI": "Bears",
    "CIN": "Bengals", "CLE": "Browns", "DAL": "Cowboys", "DEN": "Broncos", "DET": "Lions", "GB": "Packers",
    "HOU": "Texans", "IND": "Colts", "JAX": "Jaguars", "KC": "Chiefs", "LAC": "Chargers", "LAR": "Rams",
    "LV": "Raiders", "MIA": "Dolphins", "MIN": "Vikings", "NE": "Patriots", "NO": "Saints", "NYG": "Giants",
    "NYJ": "Jets", "PHI": "Eagles", "PIT": "Steelers", "SEA": "Seahawks", "SF": "49ers", "TB": "Buccaneers",
    "TEN": "Titans", "WAS": "Commanders",
}
DASH = "—"


def esc(v):
    return html.escape(str(v), quote=True)


# ---------------------------------------------------------------- icons

CHEV = ('<svg class="chev" viewBox="0 0 10 16" width="9" height="14" fill="none" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 2 2 8l6 6"/></svg>')
UP = ('<svg viewBox="0 0 12 8" width="10" height="7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
      'stroke-linejoin="round" aria-hidden="true"><path d="M1 6.5 6 1.5l5 5"/></svg>')
DOWN = ('<svg viewBox="0 0 12 8" width="10" height="7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true"><path d="M1 1.5 6 6.5l5-5"/></svg>')
# Heavier glyphs (2026-09-17): stroke 2 -> 2.75, 14 -> 17px. Page 0 imports these, so both
# pages draw the same button.
PLUS = ('<svg viewBox="0 0 16 16" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2.75" '
        'stroke-linecap="round" aria-hidden="true"><path d="M8 1.9v12.2M1.9 8h12.2"/></svg>')
MINUS = ('<svg viewBox="0 0 16 16" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2.75" '
         'stroke-linecap="round" aria-hidden="true"><path d="M1.9 8h12.2"/></svg>')

TREND = {
    "W": ('<svg class="trend t-w" viewBox="0 0 18 12" width="18" height="12" fill="none" stroke="currentColor" stroke-width="3" '
          'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Won last game"><path d="M2.5 10 9 3.5l6.5 6.5"/></svg>'),
    "L": ('<svg class="trend t-l" viewBox="0 0 18 12" width="18" height="12" fill="none" stroke="currentColor" stroke-width="3" '
          'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Lost last game"><path d="M2.5 2 9 8.5 15.5 2"/></svg>'),
    "T": ('<svg class="trend t-t" viewBox="0 0 18 12" width="18" height="12" fill="none" stroke="currentColor" stroke-width="3" '
          'stroke-linecap="round" role="img" aria-label="Tied last game"><path d="M3 6h12"/></svg>'),
}

MEDALS = {1: ("gold", "1st"), 2: ("silver", "2nd"), 3: ("bronze", "3rd")}


def crown(rank):
    if rank not in MEDALS:
        return ""
    key, word = MEDALS[rank]
    return (f'<svg class="crown" viewBox="0 0 20 16" width="17" height="14" role="img" aria-label="{word} in the league">'
            f'<path d="M1.5 14.5 1 3.5l5.2 4.2L10 1l3.8 6.7L19 3.5l-.5 11z" fill="var(--{key})"/></svg>')


# Nav-dot icons for the expanded deck (Jason's icons, 2026-09-23), one per card. Each source
# file also carried a few paths the design tool left far outside its own viewBox -- invisible
# in the original (off-canvas) but wasted weight here, so only the paths that actually draw
# something are kept. Leaders has no source icon; it reuses the same crown glyph shown inside
# the Leaders card, in plain black instead of a medal color.
NAV_ICONS = {
    "game-info": (
        '<svg viewBox="-1576 -1700 3103 3092" aria-hidden="true"><path d="'
        'M-1320.29,1132.06 L-662.293,474.064 C-678.313,437.858 -671.529,393.836 -641.942,364.249 L-538.084,260.39 L-572.774,225.7 '
        'C-611.163,187.311 -611.163,124.621 -572.774,86.2327 C-534.386,47.8441 -471.696,47.8441 -433.307,86.2327 L-398.617,120.923 '
        'L-398.617,120.923 L-294.192,16.4991 L-328.883,-18.1916 C-367.272,-56.5802 -367.272,-119.27 -328.883,-157.659 '
        'C-290.494,-196.047 -227.805,-196.047 -189.416,-157.659 L-154.725,-122.968 L-50.3011,-227.392 L-84.9918,-262.083 '
        'C-123.38,-300.471 -123.38,-363.161 -84.9917,-401.55 C-46.6031,-439.938 16.0866,-439.938 54.4752,-401.55 L89.1659,-366.859 '
        'L193.59,-471.283 L158.899,-505.974 C120.511,-544.363 120.511,-607.052 158.9,-645.441 C197.288,-683.83 259.978,-683.83 '
        '298.366,-645.441 L333.057,-610.75 L433.462,-711.156 C463.049,-740.742 507.071,-747.526 543.277,-731.507 L1281.75,-1469.98 '
        'C1009.68,-1699.95 -132.906,-1580.23 -783.647,-930.35 C-1436.47,-278.391 -1575.14,850.812 -1320.29,1132.06 L-1320.29,1132.06 Z '
        'M-1262.49,1179.72 C-926.912,1391.2 127.829,1246.67 773.592,601.761 C1407.75,-31.558 1527.45,-1060.6 1340.15,-1396.47 '
        'C1336.95,-1402.2 1330.29,-1413.06 1330.29,-1413.06 L1312.51,-1395.28 L594.885,-677.657 C608.795,-642.22 601.476,-600.235 '
        '572.929,-571.689 L472.524,-471.283 L507.215,-436.593 C545.603,-398.204 545.603,-335.514 507.215,-297.126 '
        'C468.826,-258.737 406.136,-258.737 367.748,-297.126 L333.057,-331.816 L333.057,-331.816 L228.633,-227.392 L263.323,-192.702 '
        'C301.712,-154.313 301.712,-91.6232 263.323,-53.2346 C224.935,-14.8459 162.245,-14.8459 123.857,-53.2346 L89.1659,-87.9252 '
        'L89.1659,-87.9252 L-15.2584,16.4991 L19.4322,51.1897 C57.8208,89.5784 57.8209,152.268 19.4322,190.657 '
        'C-18.9564,229.045 -81.6461,229.045 -120.035,190.657 L-154.725,155.966 L-154.725,155.966 L-259.15,260.39 L-224.459,295.081 '
        'C-186.07,333.47 -186.07,396.159 -224.459,434.548 C-262.848,472.937 -325.537,472.937 -363.926,434.548 L-398.617,399.857 '
        'L-502.475,503.716 C-531.022,532.263 -573.007,539.581 -608.444,525.672 L-1262.49,1179.72 L-1262.49,1179.72 Z" '
        'fill="currentColor"/></svg>'
    ),
    "away-team": (
        '<svg viewBox="-1265 -1304 2657 2673" aria-hidden="true">'
        '<path d="M-809.349,684.15 C-709.45,652.32 -560.895,625.612 -521.574,636.501 C-453.513,655.349 -437.475,682.255 '
        '-411.649,698.999 C-384.937,716.318 -142.03,946.677 -133.208,954.354 C-124.856,961.622 -114.556,966.419 -104.58,967.846 '
        'C-96.8473,968.953 103.502,990.104 118.151,989.502 C135.704,988.781 149.484,981.912 135.665,957.977 L61.0714,788.78 '
        'C58.5328,783.022 55.1485,762.251 71.693,738.656 C71.693,738.656 223.288,571.326 237.384,555.766 C251.48,540.207 245.8,526.33 '
        '243.629,521.113 C231.495,491.961 209.235,426.097 195.328,402.01 C174.776,366.411 179.956,369.577 159.143,356.74 '
        'C122.892,334.379 7.39338,266.771 7.39338,266.771 C-27.2345,246.241 -58.812,207.477 -63.5789,184.447 '
        'C-68.4285,161.018 -60.1786,119.854 -33.458,92.0803 C-19.865,77.9514 151.845,-50.5901 243.78,-122.694 '
        'C280.765,-151.701 324.571,-167.902 331.085,-169.74 C475.78,-210.568 818.324,-244.841 855.249,-244.841 '
        'C1011.3,-244.841 999.224,-247.611 1042.08,-244.841 C1063.09,-243.483 1090.18,-242.778 1090.18,-281.711 '
        'C1090.18,-288.729 1081.11,-425.598 1078.12,-443.721 C1076.64,-452.685 1077.54,-447.259 1073.43,-472.119 '
        'C1040,-674.668 754.984,-1007.51 627.344,-1090 C466.971,-1193.65 247.31,-1303.73 -79.4055,-1303.73 '
        'C-406.121,-1303.73 -651.444,-1143.98 -706.919,-1111.34 C-825.774,-1041.41 -977.22,-879.837 -1003.78,-837.323 '
        'C-1048.81,-763.157 -1060.21,-746.909 -1060.98,-745.761 C-1103.57,-681.94 -1146.04,-610.822 -1195.81,-498.729 '
        'C-1198.82,-491.951 -1206.92,-474.816 -1209.7,-462.18 C-1219.22,-437.147 -1225.51,-408.307 -1228.59,-396.219 '
        'C-1237.51,-361.231 -1264.34,-273.452 -1264.34,-256.009 C-1264.34,-231.162 -1264.34,-228.071 -1264.34,-215.983 '
        'C-1264.34,-122.487 -1241,95.5282 -1219.17,232.682 C-1202.05,345.058 -1201.91,346.14 -1201.73,347.196 L-1166.85,558.279 '
        'C-1161.61,589.174 -1151.67,603.431 -1133.94,609.479 L-931.717,681.916 C-897.72,694.569 -839.397,692.295 -809.349,684.15 '
        'L-809.349,684.15 Z M-775.091,490.995 L-775.091,490.995 C-799.344,497.568 -846.42,499.404 -873.861,489.191 '
        'L-932.752,461.652 C-947.066,456.771 -955.094,445.263 -959.321,420.326 L-987.473,249.948 C-987.618,249.095 -987.735,248.222 '
        '-1001.55,157.516 C-1019.17,46.8105 -1038.01,-129.164 -1038.01,-204.63 C-1038.01,-214.387 -1038.01,-216.882 -1038.01,-236.937 '
        'C-1038.01,-251.017 -1016.35,-321.869 -1009.15,-350.11 C-1006.67,-359.867 -1001.59,-383.145 -993.908,-403.351 '
        'C-991.658,-413.551 -985.121,-427.381 -982.692,-432.852 C-942.524,-523.33 -908.244,-580.734 -873.861,-632.248 '
        'C-873.243,-633.174 -864.038,-646.289 -827.694,-706.153 C-806.257,-740.468 -684.015,-870.882 -588.08,-927.329 '
        'C-543.302,-953.675 -345.287,-1082.62 -81.5738,-1082.62 C182.139,-1082.62 359.441,-993.764 488.888,-910.105 '
        'C591.915,-843.521 746.523,-685.83 795.332,-556.319 C800.561,-542.446 837.763,-421.275 837.58,-415.613 '
        'C837.187,-403.453 830.598,-404.133 826.245,-403.351 C628.418,-398.103 623.923,-395.791 615.438,-395.791 '
        'C585.634,-395.791 309.145,-368.127 192.352,-335.172 C187.095,-333.688 151.736,-320.611 121.883,-297.198 '
        'C47.6766,-238.999 -90.9216,-135.245 -101.893,-123.84 C-123.461,-101.422 -276.469,-24.4959 -276.469,121.987 '
        'C-276.469,242.361 -177.02,345.345 -36.6468,420.326 C-19.8476,430.688 38.7351,485.344 38.7351,533.824 '
        'C38.7351,539.4 -36.6468,653.636 -36.6468,653.636 C-50.0009,672.681 -68.7851,702.675 -115.952,720.245 '
        'C-130.478,725.656 -141.897,721.532 -165.705,701.712 C-172.959,695.673 -325.785,518.356 -476.488,442.991 '
        'C-505.943,428.26 -694.455,465.302 -775.091,490.995 Z" fill="currentColor"/>'
        '<path d="M1103.43,838.076 C1227.58,845.925 1246.23,845.978 1263.49,845.16 C1221.6,1039.05 1178.65,1114.66 1125.08,1247.16 '
        'C1125.08,1247.16 1118.84,1249.13 1112.07,1249.13 C1105.3,1249.13 1098.01,1247.16 1098.01,1247.16 L1098.01,1247.16 '
        'C787.451,1183.9 683.598,1147.45 473.281,1060.99 C473.281,1060.99 377.969,1021.46 372.185,1017.63 C335.996,993.666 '
        '275.646,839.7 264.905,820.332 C254.164,800.964 261.303,793.609 273.221,781.377 C278.788,775.663 285.145,762.811 '
        '318.716,765.103 C526.198,779.273 1027.24,830.803 1103.43,838.076 Z M1134.91,647.822 C1285.25,659.046 1291.14,659.502 '
        '1297.2,659.897 C1292.29,691.496 1287.39,720.832 1282.5,748.185 C1270.74,747.176 1251.89,745.63 1227.43,743.659 '
        'C903.946,717.995 534.359,689.231 362.88,675.502 C356.304,672.52 394.182,637.86 424.709,594.291 C571.286,605.724 '
        '931.914,632.683 1134.91,647.822 Z M438.449,488.253 C435.492,486.056 432.881,483.634 431.714,480.72 C404.1,411.735 '
        '376.931,335.892 362.88,299.466 C357.573,285.71 341.023,274.224 324.465,261.706 C317.077,256.121 155.538,184.608 '
        '166.2,150.782 C171.635,133.539 267.983,37.2681 362.88,-8.69347 C454.141,-52.894 543.804,-47.0637 562.512,-52.2554 '
        'C581.101,-57.414 785.769,-71.5258 947.122,-65.9346 C1105.2,-60.4568 1226.88,-40.2216 1263.49,-38.4991 '
        'C1276.53,-37.8853 1288.82,-37.283 1297.2,-52.2554 C1305.58,-67.2279 1288.93,-112.441 1282.5,-126.907 '
        'C1276.07,-141.373 1278.68,-155.45 1240.8,-162.376 C1124.23,-183.689 852.021,-186.894 841.432,-186.894 '
        'C660.912,-186.894 443.237,-138.09 380.339,-126.907 C335.181,-118.878 328.12,-111.9 298.672,-91.9313 '
        'C199.674,-24.8013 47.4356,94.1299 27.8049,113.413 C-11.4105,151.933 -12.6738,199.792 46.8723,231.674 '
        'C106.418,263.555 214.815,321.592 214.815,321.592 C236.186,333.931 236.898,330.157 244.883,352.272 C252.868,374.388 '
        '301.38,520.768 308.405,539.074 C310.012,543.263 311.656,549.604 308.405,552.696 C289.972,570.232 189.265,687.113 '
        '150.667,731.499 C118.068,768.987 110.886,790.82 142.102,853.293 C145.203,859.499 222.877,1021.95 225.978,1028.16 '
        'C243.477,1063.18 295.106,1094.16 328.857,1110.4 C389.729,1139.68 558.177,1205.01 680.046,1244.46 C773.057,1274.57 '
        '1092.06,1368.93 1158.51,1343.02 C1158.66,1342.99 1158.8,1342.97 1158.95,1342.94 C1196.02,1336.55 1223.12,1265.49 '
        '1223.12,1265.49 C1259.72,1181.12 1344.74,990.679 1380.13,779.012 C1388.42,729.413 1389.26,680.591 1389.28,630.552 '
        'C1392.15,604.694 1373.94,565.525 1338.58,559.929 C1332.77,559.009 649.215,505.513 438.449,488.253 Z" fill="currentColor"/></svg>'
    ),
    "home-team": (
        '<svg viewBox="-1265 -1304 2657 2673" aria-hidden="true">'
        '<path d="M1103.43,838.076 C1227.58,845.925 1246.23,845.978 1263.49,845.16 C1221.6,1039.05 1178.65,1114.66 1125.08,1247.16 '
        'C1125.08,1247.16 1118.84,1249.13 1112.07,1249.13 C1105.3,1249.13 1098.01,1247.16 1098.01,1247.16 L1098.01,1247.16 '
        'C787.451,1183.9 683.598,1147.45 473.281,1060.99 C473.281,1060.99 377.969,1021.46 372.185,1017.63 C335.996,993.666 '
        '275.646,839.7 264.905,820.332 C254.164,800.964 261.303,793.609 273.221,781.377 C278.788,775.663 285.145,762.811 '
        '318.716,765.103 C526.198,779.273 1027.24,830.803 1103.43,838.076 Z M1134.91,647.822 C1285.25,659.046 1291.14,659.502 '
        '1297.2,659.897 C1292.29,691.496 1287.39,720.832 1282.5,748.185 C1270.74,747.176 1251.89,745.63 1227.43,743.659 '
        'C903.946,717.995 534.359,689.231 362.88,675.502 C356.304,672.52 394.182,637.86 424.709,594.291 C571.286,605.724 '
        '931.914,632.683 1134.91,647.822 Z M438.449,488.253 C435.492,486.056 432.881,483.634 431.714,480.72 C404.1,411.735 '
        '376.931,335.892 362.88,299.466 C357.573,285.71 341.023,274.224 324.465,261.706 C317.077,256.121 155.538,184.608 '
        '166.2,150.782 C171.635,133.539 267.983,37.2681 362.88,-8.69347 C454.141,-52.894 543.804,-47.0637 562.512,-52.2554 '
        'C581.101,-57.414 785.769,-71.5258 947.122,-65.9346 C1105.2,-60.4568 1226.88,-40.2216 1263.49,-38.4991 '
        'C1276.53,-37.8853 1288.82,-37.283 1297.2,-52.2554 C1305.58,-67.2279 1288.93,-112.441 1282.5,-126.907 '
        'C1276.07,-141.373 1278.68,-155.45 1240.8,-162.376 C1124.23,-183.689 852.021,-186.894 841.432,-186.894 '
        'C660.912,-186.894 443.237,-138.09 380.339,-126.907 C335.181,-118.878 328.12,-111.9 298.672,-91.9313 '
        'C199.674,-24.8013 47.4356,94.1299 27.8049,113.413 C-11.4105,151.933 -12.6738,199.792 46.8723,231.674 '
        'C106.418,263.555 214.815,321.592 214.815,321.592 C236.186,333.931 236.898,330.157 244.883,352.272 C252.868,374.388 '
        '301.38,520.768 308.405,539.074 C310.012,543.263 311.656,549.604 308.405,552.696 C289.972,570.232 189.265,687.113 '
        '150.667,731.499 C118.068,768.987 110.886,790.82 142.102,853.293 C145.203,859.499 222.877,1021.95 225.978,1028.16 '
        'C243.477,1063.18 295.106,1094.16 328.857,1110.4 C389.729,1139.68 558.177,1205.01 680.046,1244.46 C773.057,1274.57 '
        '1092.06,1368.93 1158.51,1343.02 C1158.66,1342.99 1158.8,1342.97 1158.95,1342.94 C1196.02,1336.55 1223.12,1265.49 '
        '1223.12,1265.49 C1259.72,1181.12 1344.74,990.679 1380.13,779.012 C1388.42,729.413 1389.26,680.591 1389.28,630.552 '
        'C1392.15,604.694 1373.94,565.525 1338.58,559.929 C1332.77,559.009 649.215,505.513 438.449,488.253 Z" fill="currentColor"/>'
        '<path d="M-809.349,684.15 C-709.45,652.32 -560.895,625.612 -521.574,636.501 C-453.513,655.349 -437.475,682.255 '
        '-411.649,698.999 C-384.937,716.318 -142.03,946.677 -133.208,954.354 C-124.856,961.622 -114.556,966.419 -104.579,967.846 '
        'C-96.8472,968.953 103.502,990.104 118.151,989.502 C135.704,988.781 149.484,981.912 135.665,957.977 L61.0714,788.78 '
        'C58.5329,783.022 55.1485,762.251 71.693,738.656 C71.693,738.656 223.288,571.326 237.384,555.766 C251.48,540.207 245.801,526.33 '
        '243.629,521.113 C231.496,491.961 209.235,426.097 195.329,402.01 C174.776,366.411 179.956,369.577 159.143,356.74 '
        'C122.892,334.379 7.39342,266.771 7.39342,266.771 C-27.2344,246.241 -58.812,207.477 -63.5788,184.447 '
        'C-68.4285,161.018 -60.1786,119.854 -33.458,92.0803 C-19.865,77.9514 151.845,-50.5901 243.78,-122.694 '
        'C280.765,-151.701 324.571,-167.902 331.085,-169.74 C475.78,-210.568 808.256,-233.518 845.18,-233.518 '
        'C986.231,-233.518 1041.79,-230.253 1078.12,-229.649 C1095.91,-229.354 1092.51,-244.927 1092.51,-310.512 '
        'C1092.51,-317.53 1081.11,-425.598 1078.12,-443.721 C1076.64,-452.685 1077.54,-447.259 1073.43,-472.119 '
        'C1040,-674.668 754.984,-1007.51 627.344,-1090 C466.971,-1193.65 247.31,-1303.73 -79.4055,-1303.73 '
        'C-406.121,-1303.73 -651.444,-1143.98 -706.919,-1111.34 C-825.774,-1041.41 -977.22,-879.837 -1003.78,-837.323 '
        'C-1048.81,-763.157 -1060.21,-746.909 -1060.97,-745.761 C-1103.57,-681.94 -1146.04,-610.822 -1195.81,-498.729 '
        'C-1198.82,-491.951 -1206.92,-474.816 -1209.7,-462.18 C-1219.22,-437.147 -1225.51,-408.307 -1228.59,-396.219 '
        'C-1237.51,-361.231 -1264.34,-273.452 -1264.34,-256.009 C-1264.34,-231.162 -1264.34,-228.071 -1264.34,-215.983 '
        'C-1264.34,-122.487 -1241,95.5282 -1219.17,232.682 C-1202.05,345.058 -1201.91,346.14 -1201.73,347.196 L-1166.85,558.279 '
        'C-1161.61,589.174 -1151.67,603.431 -1133.94,609.479 L-931.717,681.916 C-897.72,694.569 -839.397,692.295 -809.349,684.15 '
        'L-809.349,684.15 Z" fill="currentColor"/></svg>'
    ),
    "leaders": (
        '<svg viewBox="0 0 20 16" aria-hidden="true">'
        '<path d="M1.5 14.5 1 3.5l5.2 4.2L10 1l3.8 6.7L19 3.5l-.5 11z" fill="currentColor"/></svg>'
    ),
}


def _wx(paths, label):
    return (f'<svg class="wx" viewBox="0 0 64 48" width="60" height="45" fill="none" stroke="currentColor" stroke-width="3.5" '
            f'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="{label}">{paths}</svg>')


_CLOUD = '<path d="M17 40a9 9 0 0 1-1-17.9A13 13 0 0 1 41 18.5 10.5 10.5 0 1 1 47 40z"/>'
_CLOUD_HIGH = '<path d="M17 32a9 9 0 0 1-1-17.9A13 13 0 0 1 41 10.5 10.5 10.5 0 1 1 47 32z"/>'
WEATHER_ICONS = {
    "sun": _wx('<circle cx="32" cy="24" r="9"/><path d="M32 5v5M32 38v5M13 24h5M46 24h5M18.6 10.6l3.5 3.5M41.9 33.9l3.5 3.5'
               'M18.6 37.4l3.5-3.5M41.9 14.1l3.5-3.5"/>', "Sunny"),
    "partly": _wx('<circle cx="22" cy="17" r="7"/><path d="M22 3v3M8 17h3M12.1 7.1l2.1 2.1M31.9 7.1l-2.1 2.1"/>'
                  '<path d="M23 42a8 8 0 0 1-.8-16A12 12 0 0 1 45 23a9.5 9.5 0 1 1 5 19z"/>', "Partly cloudy"),
    "cloud": _wx(_CLOUD, "Cloudy"),
    "rain": _wx(_CLOUD_HIGH + '<path d="M22 38l-3 6M33 38l-3 6M44 38l-3 6"/>', "Rain"),
    "snow": _wx(_CLOUD_HIGH + '<path d="M21 40h.01M32 43h.01M43 40h.01" stroke-width="5"/>', "Snow"),
    "storm": _wx(_CLOUD_HIGH + '<path d="M34 34l-6 8h8l-5 6"/>', "Thunderstorms"),
    "fog": _wx('<path d="M8 16h40M16 26h40M8 36h36"/>', "Fog"),
    "wind": _wx('<path d="M4 14h34a7 7 0 1 0-7-7"/><path d="M4 24h48a7 7 0 1 1-7 7"/><path d="M4 34h26a6 6 0 1 1-6 6"/>', "Windy"),
    "indoor": _wx('<path d="M8 38a24 24 0 0 1 48 0M4 38h56M32 14v24M20 18l4 20M44 18l-4 20"/>', "Indoors"),
}


# ---------------------------------------------------------------- formatting

def fmt_time(gametime):
    """'20:15' -> ('8:15', 'PM ET'); missing -> ('TBD', '')."""
    try:
        hh, mm = (int(x) for x in str(gametime).split(":")[:2])
    except (TypeError, ValueError):
        return "TBD", ""
    return f"{hh % 12 or 12}:{mm:02d}", ("AM ET" if hh < 12 else "PM ET")


def fmt_date(gameday):
    """'2026-10-19' -> 'OCT 19 Monday'."""
    try:
        d = date.fromisoformat(str(gameday)[:10])
    except (TypeError, ValueError):
        return "Date TBD"
    return f"{MONTHS_UPPER[d.month - 1]} {d.day} {DAY_NAMES[d.weekday()]}"


def fmt_network(networks):
    if isinstance(networks, str) and networks.strip():
        return networks.strip()
    if isinstance(networks, list) and networks:
        return ", ".join(str(n) for n in networks)
    return "TV TBD"


def fmt_record(r):
    r = r or {}
    w, l, t = r.get("wins", 0), r.get("losses", 0), r.get("ties", 0)
    return f"{w}-{l}-{t}" if t else f"{w}-{l}"


def fmt_value(v):
    if v is None:
        return DASH
    if float(v).is_integer():
        return f"{int(v):,}"
    return f"{v:,.1f}"


def ordinal(n):
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def helmet_img(team, size, mirrored=False, prefix="../"):
    src = prefix + "helmets/" + helmets.helmet_filename(team, mirrored=mirrored)
    return f'<img src="{esc(src)}" alt="" width="{size}" height="{size}">'


# ---------------------------------------------------------------- pieces

def fmt_when(d):
    """Two lines for the expanded header: ('MON OCT 19', '8:15 PM ET')."""
    t, ampm = fmt_time(d.get("gametime"))
    try:
        day = date.fromisoformat(str(d.get("gameday"))[:10])
        when = f"{DAY_NAMES[day.weekday()][:3].upper()} {MONTHS_UPPER[day.month - 1]} {day.day}"
    except (TypeError, ValueError):
        when = "DATE TBD"
    return when, (f"{t} {ampm}".strip() if t != "TBD" else "TIME TBD")


def game_body(d, hero=""):
    t, ampm = fmt_time(d.get("gametime"))
    w, venue = d.get("weather") or {}, d.get("venue") or {}
    if w.get("indoor"):
        weather = f'<span class="temp temp-word">Indoors</span>{WEATHER_ICONS["indoor"]}'
    elif w.get("available") and w.get("temp_f") is not None:
        weather = f'<span class="temp">{esc(w["temp_f"])}°</span>{WEATHER_ICONS.get(w.get("condition"), "")}'
    else:
        weather = f'<span class="temp temp-na" title="Forecast not available yet">{DASH}°</span>'
    small = f"<small>{ampm}</small>" if ampm else ""
    headline = f'<div class="time">{esc(t)}{small}</div>'
    corner = f'<div class="network">{esc(fmt_network(d.get("networks")))}</div>'
    return (
        '<div class="game-top">'
        f'<div>{headline}<div class="date">{esc(fmt_date(d.get("gameday")))}</div></div>'
        f'{corner}</div>'
        f'{hero}'
        f'<div class="game-bottom"><div class="city">{esc(venue.get("city") or "")}</div><div class="weather">{weather}</div></div>'
    )


def injuries_html(side, full):
    """
    Status reads as a colored dot + neutral-colored text (Jason, 2026-09-20 -- was colored
    text alone); the expanded card also shows nflverse's injury designation (Knee, Ankle, ...)
    next to the status where there's room for it.
    """
    rows = side.get("injuries") or []
    if not rows:
        text = "No injuries reported" if side.get("injury_report_out") else "Injury report not available"
        return f'<li class="inj-none">{text}</li>'
    out = []
    for r in rows[:3]:
        status = r.get("status") or ""
        cls = {"Out": "out", "Doubtful": "doubt", "Questionable": "ques"}.get(status, "ques")
        name = r.get("name") if full else r.get("short")
        label = status if full else r.get("status_short") or status
        if full and r.get("designation"):
            label = f"{label} · {r['designation']}"
        out.append(
            f'<li><span class="inj-name">{esc(name or "")}</span>'
            f'<span class="inj-s"><i class="inj-dot inj-{cls}"></i><span class="inj-status">{esc(label)}</span></span></li>'
        )
    return "".join(out)


# Offense/defense rank colors (Jason, 2026-09-17, revised): green #1E8A3C for 1st through grey
# #6E6E6E to red #A00000 for 32nd, weighted instead of even steps. Top 5 / bottom 5 carry almost
# the full green / red, ranks 6-10 and 23-27 a clearly lighter tint, and the middle 12 (11-22)
# stay close to grey with only small differences. Blended in OKLab; every color is 4.4:1 or
# better on white.
RANK_COLORS = [
    "#1E8A3C", "#27893F", "#2E8842", "#348645", "#3A8548",   # 1-5
    "#498052", "#4F7E55", "#537C59", "#577B5C", "#5B795E",   # 6-10
    "#637565", "#657466", "#677268", "#69716A", "#6B706C", "#6D6F6D",   # 11-16
    "#706D6C", "#736A69", "#766865", "#786562", "#7B635E", "#7E605B",   # 17-22
    "#86564F", "#895149", "#8C4D44", "#8F473D", "#924136",   # 23-27
    "#992D23", "#9B261D", "#9D1E15", "#9E130C", "#A00000",   # 28-32
]


def rank_color(n):
    return RANK_COLORS[max(1, min(len(RANK_COLORS), n)) - 1]


def big_rank(n, label):
    """Rank number + ordinal colored on the green-to-red scale; POINTS/YARDS label stays black.
    Used on the expanded team cards and (smaller, via CSS) on the condensed ones."""
    if not isinstance(n, int):
        return f'<div class="rank"><span class="rank-n na">{DASH}</span><span class="rank-sfx"></span><span class="rank-lbl">{label}</span></div>'
    c = rank_color(n)
    return (f'<div class="rank"><span class="rank-n" style="color:{c}">{n}</span>'
            f'<span class="rank-sfx" style="color:{c}">{ordinal(n)}</span><span class="rank-lbl">{label}</span></div>')


def record_block(side, final):
    """
    Record with its last-game indicator (Jason, 2026-09-17):
      - finished game: the indicator sits on the column this game changed -- green
        chevron above the wins, red chevron under the losses, yellow bar under the
        ties -- and that number takes the same color
      - upcoming game: the current streak length, colored like its indicator, beside
        the record; green chevron above the number for a win streak, red chevron /
        yellow bar below it for a losing / tie streak
    """
    rec = side.get("record") or {}
    text = fmt_record(rec)
    size = record_size(text)
    last = side.get("last")
    if final and last in TREND:
        col = {"W": 0, "L": 1, "T": 2}[last]
        vals = [rec.get("wins", 0), rec.get("losses", 0)] + ([rec.get("ties", 0)] if rec.get("ties") else [])
        parts = []
        for i, v in enumerate(vals):
            if i:
                parts.append('<span class="rc-dash">-</span>')
            if i == col:
                where = "above" if last == "W" else "below"
                parts.append(f'<span class="rc rc-hit t-{last.lower()}">{v}<span class="rc-mark {where}">{TREND[last]}</span></span>')
            else:
                parts.append(f'<span class="rc">{v}</span>')
        return f'<span class="record rec-split{size}" aria-label="Record {esc(text)}">{"".join(parts)}</span>'
    streak = side.get("streak") or 0
    if last in TREND and streak:
        mark = TREND[last]
        inner = f'{mark}<b>{streak}</b>' if last == "W" else f'<b>{streak}</b>{mark}'
        word = {"W": "win", "L": "losing", "T": "tie"}[last]
        return (f'<span class="streak t-{last.lower()}" role="img" aria-label="{streak}-game {word} streak">{inner}</span>'
                f'<span class="record{size}">{esc(text)}</span>')
    return f'<span class="record{size}">{esc(text)}</span>'


def record_size(record_text):
    """Longer records ("10-6", "2-2-1", "10-6-1") get a smaller size class so they fit next to the helmet."""
    n = len(record_text)
    return "" if n <= 3 else " rec-4" if n == 4 else " rec-5" if n == 5 else " rec-6"


def team_pill(team):
    """A flat pill in the team's helmet-shell color (the PRIMARY color in helmets.py, no gradient)."""
    primary, _secondary = helmets.TEAM_COLORS.get(team, helmets.FALLBACK_COLORS)
    return f'<span class="pill" style="background:{primary}" role="img" aria-label="{esc(TEAM_NAMES.get(team, team))}"></span>'


def pill_row(a, h):
    """Leaders card column heads: away team's pill over the left column, home team's over the right."""
    return f'<div class="cmp-row cmp-head">{team_pill(a)}<div></div>{team_pill(h)}</div>'


def card_title(name, abbr=False):
    """The card's name at the top center of the card -- the same label its peeking sliver shows.
    abbr=True for a team-code title (Saira, matching every other abbreviation on the site)."""
    cls = "card-title abbr" if abbr else "card-title"
    return f'<span class="{cls}">{esc(name)}</span>'


def c_team(side, label, final=False):
    r = side.get("ranks") or {}
    team = side.get("team")
    rec = fmt_record(side.get("record"))
    return (
        f'<a class="card c-team" tabindex="0" data-detail="{label}-team" aria-label="{esc(team)} team">'
        f'{card_title(team, abbr=True)}'
        '<div class="l-top">'
        f'<div class="l-id">{helmet_img(team, 40)}</div>'
        f'<div class="l-rec">{record_block(side, final)}</div>'
        "</div>"
        f'<ul class="injuries c-inj">{injuries_html(side, full=False)}</ul>'
        '<div class="ranks">'
        f'<div class="rank-col"><h3>Offense</h3>{big_rank(r.get("off_points"), "PTS")}{big_rank(r.get("off_yards"), "YDS")}</div>'
        f'<div class="rank-col"><h3>Defense</h3>{big_rank(r.get("def_points"), "PTS")}{big_rank(r.get("def_yards"), "YDS")}</div>'
        "</div></a>"
    )


def l_team(side, final=False):
    r = side.get("ranks") or {}
    team = side.get("team")
    return (
        '<div class="l-top">'
        f'<div class="l-id">{helmet_img(team, 84)}</div>'
        f'<div class="l-rec">{record_block(side, final)}</div>'
        "</div>"
        f'<ul class="l-inj">{injuries_html(side, full=True)}</ul>'
        '<div class="ranks">'
        f'<div class="rank-col"><h3>Offense</h3>{big_rank(r.get("off_points"), "POINTS")}{big_rank(r.get("off_yards"), "YARDS")}</div>'
        f'<div class="rank-col"><h3>Defense</h3>{big_rank(r.get("def_points"), "POINTS")}{big_rank(r.get("def_yards"), "YARDS")}</div>'
        "</div>"
    )


def leader_cell(p):
    if not p:
        return f'<div class="ldr"><div class="ldr-v na"><span>{DASH}</span></div><div class="ldr-n">&nbsp;</div></div>'
    return (
        f'<div class="ldr"><div class="ldr-v"><span>{esc(fmt_value(p.get("value"))).replace(",", "<i class=cm>,</i>")}</span>{crown(p.get("league_rank"))}</div>'
        f'<div class="ldr-n"><span class="nm">{esc(p.get("name") or "")}</span><span class="pos">{esc(p.get("position") or "")}</span></div></div>'
    )


def leader_rows(d):
    return "".join(
        f'<div class="cmp-row">{leader_cell(row.get("away"))}'
        f'<div class="cmp-lbl">{esc(row.get("label", "")).replace(" ", "<br>")}</div>'
        f'{leader_cell(row.get("home"))}</div>'
        for row in d.get("leaders") or []
    )


# ---------------------------------------------------------------- page

def header_scores(d):
    """Finished game -> (away_html, home_html) score spans for the header, loser faded like Page 0. Else ('', '')."""
    score = d.get("score") if d.get("final") else None
    if not score:
        return "", ""
    a_s, h_s = score.get("away"), score.get("home")
    a_cls = h_cls = "hscore"
    try:
        if float(a_s) > float(h_s):
            h_cls += " lose"
        elif float(h_s) > float(a_s):
            a_cls += " lose"
    except (TypeError, ValueError):
        pass
    return (f'<span class="{a_cls}">{esc(fmt_value(a_s))}</span>', f'<span class="{h_cls}">{esc(fmt_value(h_s))}</span>')


def win_side(d):
    """Finished game -> "away" | "home" | None (tie or not yet final) -- same rule as Page 0's triangle."""
    score = d.get("score") if d.get("final") else None
    if not score:
        return None
    try:
        a_s, h_s = float(score.get("away")), float(score.get("home"))
    except (TypeError, ValueError):
        return None
    return "away" if a_s > h_s else "home" if h_s > a_s else None


# Winner triangle next to "FINAL" (Jason, 2026-09-17 on Page 0; 2026-09-21 everywhere else "FINAL"
# shows). Same shape as Page 0's, duplicated here rather than imported to avoid a circular import
# (render_html.py already imports this module).
WIN_TRI = ('<svg viewBox="0 0 8 10" aria-hidden="true"><path d="M8 0 0 5l8 5z" fill="currentColor"/></svg>')


def final_label_html(d):
    """"FINAL"/"FINAL/OT" flanked by two triangle slots -- only the winner's side is visible
    (CSS keys off data-win on .p1), same convention as Page 0."""
    text = "FINAL/OT" if d.get("overtime") else "FINAL"
    return (f'<span class="tri tri-a">{WIN_TRI}</span>{esc(text)}<span class="tri tri-h">{WIN_TRI}</span>')


def render_p1_block(d, prefix="../"):
    """The <div class="p1"> block (shared by the standalone page and the Page 0 overlay)."""
    away, home = d.get("away") or {}, d.get("home") or {}
    a, h = away.get("team") or "TBD", home.get("team") or "TBD"
    week_href = f"{prefix}index.html#week-{d.get('week_key')}"
    week_label = d.get("week_label") or ""
    rows = leader_rows(d)
    img = lambda team, size, mir=False: helmet_img(team, size, mir, prefix)
    a_score, h_score = header_scores(d)
    game_scope = d.get("leaders_scope") == "game"
    final = bool(d.get("final"))
    leaders_name = "Game Leaders" if game_scope else "Leaders"

    when_day, when_time = fmt_when(d)
    # One header row, drawn twice (top bar + the middle of the Game Info card) and morphed between the two.
    # Each team is a unit: helmet plus its abbreviation (and final score) — side by side when condensed,
    # stacked and pushed to the edges of the screen in the expanded view (2026-09-17).
    row = (
        f'<div class="side away">{img(a, 44)}<span class="abbr">{esc(a)}</span>{a_score}</div>'
        # finished games say FINAL / FINAL/OT where the "@" was (Jason, 2026-09-19) -- same element, so every
        # header animation that moves the "@" carries the label instead. The winner triangle
        # (2026-09-21) rides along inside both copies since they're just cloned for the animation.
        f'<div class="mid"><span class="at{" at-final" if final else ""}">{final_label_html(d) if final else "@"}</span>'
        f'<span class="when"><span>{esc(when_day)}</span><span>{esc(when_time)}</span></span>'
        f'<span class="final-lbl">{final_label_html(d)}</span></div>'
        f'<div class="side home">{h_score}<span class="abbr">{esc(h)}</span>{img(h, 44, True)}</div>'
    )
    hero = f'<div class="hero" aria-hidden="true"><div class="teams">{row}</div></div>'
    bar = (
        '<header class="bar"><div class="bar-in">'
        f'<div class="teams" aria-label="{esc(TEAM_NAMES.get(a, a))} at {esc(TEAM_NAMES.get(h, h))}">{row}</div>'
        "</div></header>"
        # back button + view toggle live at the bottom of the screen (2026-09-17)
        '<nav class="bbar" aria-label="Page controls"><div class="bbar-in">'
        f'<a class="week" href="{esc(week_href)}">{CHEV}<span>{esc(week_label)}</span></a>'
        # Page 2's back button takes the week pill's place while Game Info is open (2026-09-19)
        f'<a class="week p2-back" href="#" aria-label="Back to {esc(a)} at {esc(h)}">{CHEV}'
        f'<span><span class="abbr">{esc(a)}</span> @ <span class="abbr">{esc(h)}</span></span></a>'
        f'<button class="toggle" type="button"><span class="i-plus">{PLUS}</span><span class="i-minus">{MINUS}</span></button>'
        "</div></nav>"
    )
    condensed = (
        '<div class="view view-c" aria-label="Condensed matchup">'
        f'<a class="card c-game" tabindex="0" data-detail="game-info" aria-label="Game info">{card_title("Game Info")}{game_body(d)}</a>'
        f'<div class="c-teams">{c_team(away, "away", final)}{c_team(home, "home", final)}</div>'
        f'<a class="card c-cmp" tabindex="0" data-detail="leaders" aria-label="{leaders_name}">{card_title(leaders_name)}<div class="c-cmp-in">{pill_row(a, h)}{rows}</div></a>'
        "</div>"
    )
    cmp_head = pill_row(a, h)  # team-color pills replace the helmets + abbreviations (2026-09-17)
    cards = [("game-info", "Game Info", "game", game_body(d, hero)),
             ("away-team", a, "team", l_team(away, final)),
             ("home-team", h, "team", l_team(home, final)),
             ("leaders", leaders_name, "compare", cmp_head + rows)]
    slots = "".join(
        f'<section class="slot"><a class="card {kind}" tabindex="-1" data-detail="{cid}" aria-label="{esc(name)}">'
        f'<span class="peek peek-top">{DOWN}<span class="{"abbr" if kind == "team" else ""}">{esc(name)}</span></span>'
        f'<div class="body">{body}</div>'
        f'<span class="peek peek-bot">{UP}<span class="{"abbr" if kind == "team" else ""}">{esc(name)}</span></span></a></section>'
        for cid, name, kind, body in cards
    )
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(name)}">{NAV_ICONS.get(cid, "")}</button>' for cid, name, _k, _b in cards)
    large = f'<div class="view view-l deck" aria-label="Expanded matchup">{slots}</div><nav class="dots" aria-label="Cards">{dots}</nav>'
    t, ampm = fmt_time(d.get("gametime"))
    time_html = f'<div class="time">{esc(t)}{f"<small>{ampm}</small>" if ampm else ""}</div>'
    try:
        page2 = render_page2gameinfo.render_p2_block(d, time_html, WEATHER_ICONS)
    except Exception:  # Page 2 trouble never costs the game its Page 1
        page2 = ""
    try:
        away_page = render_page2team.render_team_block(away, "away", prefix)
    except Exception:
        away_page = ""
    try:
        home_page = render_page2team.render_team_block(home, "home", prefix)
    except Exception:
        home_page = ""
    has_detail = " ".join(k for k, block in
                           (("game-info", page2), ("away-team", away_page), ("home-team", home_page)) if block)
    has_detail_attr = f' data-has-detail="{esc(has_detail)}"' if has_detail else ""
    win = win_side(d)
    win_attr = f' data-win="{win}"' if win else ""
    return (f'<div class="p1" data-view="large" data-head="card"{" data-final" if final else ""}{win_attr}{has_detail_attr} '
            f'data-game="{esc(d.get("game_id"))}">{bar}{condensed}{large}{page2}{away_page}{home_page}</div>')


def render_standalone(d):
    a = (d.get("away") or {}).get("team") or "TBD"
    h = (d.get("home") or {}).get("team") or "TBD"
    title = f"{a} @ {h} · {d.get('week_label') or ''} · At A Glance"
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        "<meta name='theme-color' content='#ffffff'>"
        f"<title>{esc(title)}</title>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'><link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
        f"<style id='p1-css'>{P1_CSS}{render_page2gameinfo.P2_CSS}{render_page2team.P3_CSS}</style>"
        "<style>html,body{margin:0;background:#fff}</style></head><body>"
        f"{render_p1_block(d)}"
        f"<script>{P1_JS}</script><script>AAG_P1.init(document);</script>"
        "</body></html>"
    )


def write_all(data, site_dir, warnings=None):
    """Write site/game/<game_id>.html for every game in data['game_details']. Returns the count."""
    details = data.get("game_details") or {}
    out_dir = os.path.join(site_dir, "game")
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    for gid, d in details.items():
        try:
            safe = "".join(ch for ch in str(gid) if ch.isalnum() or ch in "_-")
            with open(os.path.join(out_dir, f"{safe}.html"), "w", encoding="utf-8") as f:
                f.write(render_standalone(d))
            count += 1
        except Exception:
            if warnings is not None:
                warnings.append(f"render_page1 {gid}: {traceback.format_exc(limit=1)}")
    return count


# ---------------------------------------------------------------- script (shared with the Page 0 overlay)

P1_JS = r"""
window.AAG_P1 = window.AAG_P1 || { init: function (root, opts) {
  opts = opts || {};
  var wrap = root.querySelector('.p1'); if (!wrap) return { destroy: function () {} };
  var deck = root.querySelector('.view-l'), slots = [].slice.call(root.querySelectorAll('.view-l > .slot')),
      dots = [].slice.call(root.querySelectorAll('.p1 > .dots .dot')), toggle = root.querySelector('.toggle'),
      week = root.querySelector('.week'), active = -1, bound = [], morphing = false;
  // Motion always plays, whatever the device's Reduce Motion setting (Jason, 2026-09-17).
  // Speed/easing taken from yeezy.com: 200-300ms moves on cubic-bezier(.22,1,.36,1), 150ms fades.
  var reduce = false;
  var smooth = 'smooth', EASE = 'cubic-bezier(.22,1,.36,1)';
  var lastCard = Math.max(0, Math.min(slots.length - 1, opts.card || 0));  // expanded card to return to
  function on(t, type, fn, o) { t.addEventListener(type, fn, o); bound.push([t, type, fn, o]); }
  function large() { return wrap.getAttribute('data-view') === 'large'; }
  function setActive(i) {
    if (i === active) return; active = i; lastCard = i;
    slots.forEach(function (s, k) {
      s.classList.toggle('active', k === i); s.classList.toggle('above', k === i - 1); s.classList.toggle('below', k === i + 1);
      var c = s.querySelector('a.card'); c.tabIndex = k === i ? 0 : -1; c.setAttribute('aria-hidden', k === i ? 'false' : 'true');
    });
    dots.forEach(function (d, k) { d.classList.toggle('on', k === i); });
  }
  function current() {
    var mid = deck.scrollTop + deck.clientHeight / 2, best = 0, bd = 1e9;
    slots.forEach(function (s, k) { var d = Math.abs(s.offsetTop + s.offsetHeight / 2 - mid); if (d < bd) { bd = d; best = k; } });
    return best;
  }
  function go(i, instant) {
    i = Math.max(0, Math.min(slots.length - 1, i)); var s = slots[i];
    deck.scrollTo({ top: s.offsetTop - (deck.clientHeight - s.offsetHeight) / 2, behavior: instant ? 'auto' : smooth });
  }
  // ---- header: in the Game Info card on the first card, condensing into the top bar as you scroll on (2026-09-17).
  // Every piece travels on its own (helmets, abbreviations, scores), because the three layouts arrange them
  // differently; the middle crossfades between the card's "@" and the bar's date and time.
  var barRow = root.querySelector('.bar .teams'), heroRow = root.querySelector('.hero .teams');
  var flyBox = null, flyAtoms = [], flyAt = null, flyWhen = null;
  function atoms(row) { return [].slice.call(row.querySelectorAll('img, .abbr, .hscore')); }
  function shown(el) { return !!(el && el.getClientRects().length); }
  function sizeOf(el) { return el.tagName === 'IMG' ? el.offsetWidth : parseFloat(getComputedStyle(el).fontSize) || 1; }
  function rectOf(el) { return el.getBoundingClientRect(); }
  function park(el, r) { Object.assign(el.style, { left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px' }); }
  function toward(el, r, from, e, scale) {
    // el is parked on its own rect r; put its centre e of the way from "from" to r, at the given scale
    var cx = from.left + from.width / 2 + (r.left + r.width / 2 - (from.left + from.width / 2)) * e;
    var cy = from.top + from.height / 2 + (r.top + r.height / 2 - (from.top + from.height / 2)) * e;
    el.style.transform = 'translate(' + (cx - r.left - r.width * scale / 2) + 'px,' + (cy - r.top - r.height * scale / 2) + 'px) scale(' + scale + ')';
  }
  function copyOf(src) {
    var c = src.cloneNode(true), cs = getComputedStyle(src);
    c.className = (src.className || '') + ' hf';
    c.style.fontSize = cs.fontSize;
    if (src.tagName === 'IMG') { c.style.width = src.offsetWidth + 'px'; c.style.height = src.offsetHeight + 'px'; }
    // the date keeps its two stacked lines; FINAL keeps its triangle beside the text (2026-09-21)
    else if (src.classList.contains('when')) c.style.display = 'flex';
    else if (src.classList.contains('at-final') || src.classList.contains('final-lbl')) c.style.display = 'inline-flex';
    else c.style.display = 'block';
    return c;
  }
  if (barRow && heroRow) {
    flyBox = document.createElement('div');
    flyBox.className = 'teams head-fly';   // .teams so the copies keep the header's own styling
    flyBox.setAttribute('aria-hidden', 'true');
    atoms(barRow).forEach(function (el) { var c = copyOf(el); flyBox.appendChild(c); flyAtoms.push(c); });
    flyAt = copyOf(heroRow.querySelector('.at'));
    flyWhen = copyOf(barRow.querySelector(wrap.hasAttribute('data-final') ? '.final-lbl' : '.when'));
    flyBox.appendChild(flyAt);
    flyBox.appendChild(flyWhen);
    wrap.appendChild(flyBox);
  }
  function centerTop(s) { return s.offsetTop - (deck.clientHeight - s.offsetHeight) / 2; }
  function headProgress() {  // 0 with the Game Info card in the middle, 1 once the next card is
    if (slots.length < 2) return 0;
    var a = centerTop(slots[0]), step = centerTop(slots[1]) - a;
    return step > 0 ? Math.max(0, Math.min(1, (deck.scrollTop - a) / step)) : 0;
  }
  function setHead(mode) { if (wrap.getAttribute('data-head') !== mode) wrap.setAttribute('data-head', mode); }
  function updateHead() {
    if (!flyBox || !large() || wrap.hasAttribute('data-detail')) return;
    var p = headProgress(), e = 1 - (1 - p) * (1 - p);  // ease-out: the header settles before the next card does
    if (p <= 0.001) { setHead('card'); return; }
    if (p >= 0.999) { setHead('bar'); return; }
    var ba = atoms(barRow), ha = atoms(heroRow);
    if (!ba.length || rectOf(ba[0]).width === 0) return;
    ba.forEach(function (el, k) {
      var f = flyAtoms[k], src = ha[k];
      if (!f || !src) return;
      var r = rectOf(el), sc = sizeOf(src) / sizeOf(el);
      park(f, r);
      toward(f, r, rectOf(src), e, sc + (1 - sc) * e);
    });
    var at = heroRow.querySelector('.at'), when = barRow.querySelector(wrap.hasAttribute('data-final') ? '.final-lbl' : '.when');
    var scale = sizeOf(ha[0]) / sizeOf(ba[0]), mid = rectOf(barRow.querySelector('.mid'));
    if (shown(at)) {
      var ar = rectOf(at);
      park(flyAt, ar);
      toward(flyAt, ar, mid, 1 - e, 1 - (1 - 1 / scale) * e);   // shrinks with the units as it fades out
      flyAt.style.opacity = Math.max(0, 1 - e / 0.5);
      flyAt.style.display = 'block';
    } else flyAt.style.display = 'none';
    if (shown(when)) {
      var wr = rectOf(when);
      park(flyWhen, wr);
      toward(flyWhen, wr, mid, e, 1 + (scale - 1) * (1 - e));
      flyWhen.style.opacity = Math.max(0, (e - 0.6) / 0.4);
      flyWhen.style.display = when.classList.contains('when') ? 'flex' : 'block';
    } else flyWhen.style.display = 'none';
    setHead('moving');
  }
  function midPiece(row, mode) {  // the middle shows "@" in the card and when condensed, the date or FINAL in the expanded bar
    if (mode === 'card') return row.querySelector('.at');
    var el = row.querySelector(wrap.hasAttribute('data-final') ? '.final-lbl' : '.when');
    return shown(el) ? el : row.querySelector('.at');
  }
  function headShot() {  // where every header piece is right now, and which middle piece is showing
    var mode = large() ? wrap.getAttribute('data-head') : 'cond';
    var row = mode === 'card' ? heroRow : barRow;
    if (mode === 'moving') {
      var mv = flyAtoms.map(function (el) { return { rect: rectOf(el), size: sizeOf(el) * (el.tagName === 'IMG' ? 1 : 1) }; });
      return { mode: mode, row: barRow, list: mv, midEl: shown(flyAt) ? flyAt : flyWhen, mid: rectOf(shown(flyAt) ? flyAt : flyWhen) };
    }
    var mid = midPiece(row, mode);
    return {
      mode: mode, row: row,
      list: atoms(row).map(function (el) { return { rect: rectOf(el), size: sizeOf(el) }; }),
      midEl: shown(mid) ? mid : null, mid: shown(mid) ? rectOf(mid) : null
    };
  }
  function ghost(el, r) {  // a free copy of one piece, parked exactly on top of it
    var box = document.createElement('div'), c = copyOf(el);
    box.className = 'teams hf-box';
    Object.assign(box.style, { position: 'fixed', left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px',
      margin: '0', display: 'block', zIndex: '12', pointerEvents: 'none', transformOrigin: '0 0', fontSize: getComputedStyle(el).fontSize });
    Object.assign(c.style, { position: 'absolute', left: '0', top: '0' });
    box.appendChild(c);
    wrap.appendChild(box);
    return box;
  }
  function slide(g, from, to, scale, D, fade) {
    var a = { transform: 'translate(' + (from.left + from.width / 2 - to.left - to.width * scale / 2) + 'px,' +
                (from.top + from.height / 2 - to.top - to.height * scale / 2) + 'px) scale(' + scale + ')' },
        b = { transform: 'none' };
    if (fade) { a.opacity = fade[0]; b.opacity = fade[1]; }
    return g.animate([a, b], { duration: D, easing: EASE, fill: 'forwards' });
  }
  function flipHead(from, D) {  // the pieces fly between two header layouts when the view changes
    var to = headShot(), out = [];
    if (!from || !to.list.length || from.mode === to.mode) return out;
    atoms(to.row).forEach(function (el, k) {
      var r = to.list[k], f = from.list[k];
      if (!r || !f || !r.rect.width || !f.rect.width) return;
      var g = ghost(el, r.rect);
      el.style.visibility = 'hidden';
      out.push({ el: el, g: g, anim: slide(g, f.rect, r.rect, f.size / r.size, D) });
    });
    var ratio = to.list[0].size / from.list[0].size;
    if (to.midEl && to.mid) {   // the middle swaps content, so the new copy fades in on the way
      var gIn = ghost(to.midEl, to.mid);
      to.midEl.style.visibility = 'hidden';
      out.push({ el: to.midEl, g: gIn, anim: slide(gIn, from.mid || to.mid, to.mid, 1 / ratio, D, [0, 1]) });
    }
    if (from.midEl && from.mid) {   // ...and the old one fades out
      var gOut = ghost(from.midEl, from.mid);
      gOut.style.left = from.mid.left + 'px'; gOut.style.top = from.mid.top + 'px';
      var target = to.mid || from.mid;
      out.push({ g: gOut, anim: gOut.animate([{ transform: 'none', opacity: 1 },
        { transform: 'translate(' + (target.left + target.width / 2 - from.mid.left - from.mid.width * ratio / 2) + 'px,' +
          (target.top + target.height / 2 - from.mid.top - from.mid.height * ratio / 2) + 'px) scale(' + ratio + ')', opacity: 0 }],
        { duration: Math.round(D * 0.6), easing: EASE, fill: 'forwards' }) });
    }
    return out;
  }
  function endFlip(list) { list.forEach(function (o) { if (o.el) o.el.style.visibility = ''; o.g.remove(); }); }
  function visibleHead() { return large() && flyBox ? (wrap.getAttribute('data-head') === 'card' ? heroRow : wrap.getAttribute('data-head') === 'moving' ? flyBox : barRow) : barRow; }

  var ticking = false;
  on(deck, 'scroll', function () { if (!ticking && large() && !morphing) { ticking = true; requestAnimationFrame(function () { if (large()) { setActive(current()); updateHead(); } ticking = false; }); } }, { passive: true });
  // Tapping a peeking card brings it in; tapping the active card opens its deep dive, if it
  // has one -- Game Info, away team and home team each do; Leaders doesn't yet (2026-09-20).
  function availableKeys() { return (wrap.getAttribute('data-has-detail') || '').split(' ').filter(Boolean); }
  function opensDetail(card) {
    var key = card && card.getAttribute('data-detail');
    return !!(key && availableKeys().indexOf(key) > -1);
  }
  slots.forEach(function (s, k) {
    var c = s.querySelector('a.card');
    on(c, 'click', function (e) { e.preventDefault(); if (k !== active) go(k); else if (opensDetail(c)) openDetail(c.getAttribute('data-detail')); });
    on(c, 'keydown', function (e) { if ((e.key === 'Enter' || e.key === ' ') && k === active && opensDetail(c)) { e.preventDefault(); openDetail(c.getAttribute('data-detail')); } });
  });
  // Condensed view: any card carrying data-detail can open its deep dive the same way (c-game,
  // and now the two c-team cards; c-cmp/leaders has no data-has-detail entry so opensDetail stays false for it).
  [].slice.call(root.querySelectorAll('.view-c [data-detail]')).forEach(function (c) {
    on(c, 'click', function (e) { e.preventDefault(); if (opensDetail(c)) openDetail(c.getAttribute('data-detail')); });
    on(c, 'keydown', function (e) { if ((e.key === 'Enter' || e.key === ' ') && opensDetail(c)) { e.preventDefault(); openDetail(c.getAttribute('data-detail')); } });
  });
  dots.forEach(function (d, k) { on(d, 'click', function () { go(k); }); });

  // Condensed card for each expanded card: game info, away team, home team, leaders
  function condensedCards() { return [root.querySelector('.c-game')].concat([].slice.call(root.querySelectorAll('.c-team')), [root.querySelector('.c-cmp')]); }
  function labelToggle(v) {
    toggle.setAttribute('aria-label', v === 'large' ? 'Switch to condensed view' : 'Switch to expanded view');
    toggle.setAttribute('aria-pressed', v === 'large' ? 'true' : 'false');
  }
  function place(v, card) {
    wrap.setAttribute('data-view', v);
    labelToggle(v);
    if (v === 'large') { active = -1; go(card, true); setActive(card); updateHead(); }
  }
  // A plain card-shaped box holding a frozen copy of a card, used to morph between the two views.
  function morphFrom(el) {
    var r = el.getBoundingClientRect(), box = document.createElement('div'), copy = el.cloneNode(true);
    box.className = 'morph';
    Object.assign(box.style, { left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px' });
    copy.removeAttribute('tabindex');
    var h = copy.querySelector('.hero .teams'); if (h) h.style.visibility = 'hidden';
    Object.assign(copy.style, { width: r.width + 'px', height: r.height + 'px' });
    box.appendChild(copy);
    wrap.appendChild(box);
    return { box: box, copy: copy, r: r };
  }
  function geo(r) { return { left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px' }; }
  function fin(a) { return a.finished.catch(function () {}); }

  function switchView(v) {
    if (morphing || v === wrap.getAttribute('data-view')) return;
    var card = lastCard;
    if (reduce || !Element.prototype.animate) { place(v, card); return; }
    morphing = true;
    var toLarge = v === 'large', D = 300;
    var headFrom = headShot();
    var fromEl = toLarge ? condensedCards()[card] : slots[card].querySelector('a.card');
    var others = toLarge ? condensedCards().filter(function (_, k) { return k !== card; }) : [];
    var ghosts = others.map(function (el) { return morphFrom(el); });   // condensed neighbours zoom past and fade
    var m = morphFrom(fromEl);
    place(v, card);
    var toEl = toLarge ? slots[card].querySelector('a.card') : condensedCards()[card];
    var r1 = toEl.getBoundingClientRect();
    toEl.style.opacity = '0';
    var flips = flipHead(headFrom, D), anims = flips.map(function (o) { return o.anim; });
    anims.push(m.box.animate([geo(m.r), geo(r1)], { duration: D, easing: EASE, fill: 'forwards' }));
    m.copy.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 120, fill: 'forwards' });
    ghosts.forEach(function (g) {
      g.box.animate([{ transform: 'scale(1)', opacity: 1 }, { transform: 'scale(1.12)', opacity: 0 }], { duration: 160, easing: EASE, fill: 'forwards' });
    });
    if (toLarge) {
      // the peeking neighbours and dots arrive once the card has nearly filled its spot
      [slots[card - 1], slots[card + 1]].forEach(function (s) {
        if (s) s.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, delay: D - 90, easing: 'ease-out', fill: 'backwards' });
      });
      dots.forEach(function (d) { d.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, delay: D - 90, fill: 'backwards' }); });
    } else {
      // the other condensed cards settle into place from slightly larger, as if zooming out
      condensedCards().forEach(function (el, k) {
        if (k === card) return;
        el.animate([{ transform: 'scale(1.08)', opacity: 0 }, { transform: 'none', opacity: 1 }], { duration: 240, delay: 50, easing: EASE, fill: 'backwards' });
      });
    }
    Promise.all(anims.map(fin)).then(function () {
      toEl.style.opacity = '';
      var inAnim = toEl.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 120, easing: 'ease-out' });
      m.box.remove();
      ghosts.forEach(function (g) { g.box.remove(); });
      morphing = false;
      // the header copies stay put until the card around them has faded in
      fin(inAnim).then(function () { endFlip(flips); });
    });
  }
  on(toggle, 'click', function () {
    if (detailOpen()) detailView(large() ? 'condensed' : 'large');
    else switchView(large() ? 'condensed' : 'large');
  });

  // ---- Page 2: Game Info deep dive (2026-09-19; deck + condensed views v4) -------------------
  // Page 2 has the same two views as Page 1 and shares its data-view attribute: it opens in
  // whichever view Page 1 is in, and the +/− button flips both.
  //   expanded  = a deck like Page 1's: one card per screen, slivers, dots, ↑/↓ keys
  //   condensed = every card on one screen; tapping a card switches to the deck on that card
  // Open  = the Game Info card grows to fill the space between the bars (the same zoom Page 0 ->
  //         Page 1 uses), the header pieces move into the top bar if they were in the card, then
  //         Page 2's cards rise in one after another.
  // Close = "‹ AWAY @ HOME", Esc, browser back, or (in the Page 0 overlay) a pull down from the
  //         first card: Page 2 fades while a card outline shrinks back onto the Game Info card.
  // URL: "/game-info" is added to the hash (#game-<id>/game-info, or #/game-info on the standalone
  // page) and pushed to history, so back closes it and a shared link opens straight into it.
  // Detail registry: up to three nested deep-dives can live inside this .p1 (Game Info,
  // away team, home team -- render_page2gameinfo.py / render_page2team.py), each its own
  // .p2[data-page=<key>] with its own deck/slots/dots (and, Game Info only, a condensed
  // layer). Only one is ever open at a time (wrap's data-detail names which), so the
  // functions below all look it up fresh via curDetail() rather than closing over a single
  // fixed set of elements the way this used to when Game Info was the only one (2026-09-20).
  var DETAIL_KEYS = ['game-info', 'away-team', 'home-team'];
  var p2Back = root.querySelector('.p2-back');
  var details = {};
  DETAIL_KEYS.forEach(function (key) {
    var el = root.querySelector('.p2[data-page="' + key + '"]');
    if (!el) return;
    details[key] = {
      key: key, hash: '/' + key, el: el,
      deck: el.querySelector('.p2-l'),
      slots: [].slice.call(el.querySelectorAll('.p2-l > .slot')),
      dots: [].slice.call(el.querySelectorAll('.p2-dots .dot')),
      cond: [].slice.call(el.querySelectorAll('.p2-c > .cc')),
      active: -1
    };
  });
  var detailBusy = false, headBefore = null, RISE = 'translateY(56px) scale(.96)';
  function detailOpen() { return wrap.hasAttribute('data-detail'); }
  function curDetail() { return details[wrap.getAttribute('data-detail')]; }
  function keyFromHash() {
    var h = location.hash || '';
    for (var i = 0; i < DETAIL_KEYS.length; i++) {
      var d = details[DETAIL_KEYS[i]];
      if (d && h.slice(h.length - d.hash.length) === d.hash) return d.key;
    }
    return null;
  }
  function detailInHash() { return !!keyFromHash(); }
  function hashBase() {
    var key = keyFromHash();
    return key ? location.hash.slice(0, location.hash.length - details[key].hash.length) : (location.hash || '');
  }
  function sourceCard(key) {
    if (large()) {
      var found = null;
      slots.forEach(function (s) { var c = s.querySelector('a.card'); if (c && c.getAttribute('data-detail') === key) found = c; });
      return found;
    }
    return root.querySelector('.view-c [data-detail="' + key + '"]');
  }
  function shellFrame(r, radius, border) { return Object.assign({ borderRadius: radius, borderColor: border }, geo(r)); }
  // One detail's deck (generalized from the single Game-Info-only version this used to be)
  function detailSetActive(d, i) {
    if (i === d.active) return; d.active = i;
    d.slots.forEach(function (s, k) {
      s.classList.toggle('active', k === i); s.classList.toggle('above', k === i - 1); s.classList.toggle('below', k === i + 1);
      var c = s.querySelector('a.card'); c.tabIndex = k === i ? 0 : -1; c.setAttribute('aria-hidden', k === i ? 'false' : 'true');
    });
    d.dots.forEach(function (dot, k) { dot.classList.toggle('on', k === i); });
  }
  function detailCurrent(d) {
    var mid = d.deck.scrollTop + d.deck.clientHeight / 2, best = 0, bd = 1e9;
    d.slots.forEach(function (s, k) { var dist = Math.abs(s.offsetTop + s.offsetHeight / 2 - mid); if (dist < bd) { bd = dist; best = k; } });
    return best;
  }
  function detailGo(d, i, instant) {
    if (!d.slots.length) return;
    i = Math.max(0, Math.min(d.slots.length - 1, i)); var s = d.slots[i];
    d.deck.scrollTo({ top: s.offsetTop - (d.deck.clientHeight - s.offsetHeight) / 2, behavior: instant ? 'auto' : smooth });
  }
  function detailPlace(d, i) { d.active = -1; detailGo(d, i, true); detailSetActive(d, i); }
  Object.keys(details).forEach(function (key) {
    var d = details[key];
    if (!d.deck) return;
    var tick = false;
    on(d.deck, 'scroll', function () {
      if (!tick && detailOpen() && curDetail() === d && large()) { tick = true; requestAnimationFrame(function () { detailSetActive(d, detailCurrent(d)); tick = false; }); }
    }, { passive: true });
    d.slots.forEach(function (s, k) { on(s.querySelector('a.card'), 'click', function (e) { e.preventDefault(); if (k !== d.active) detailGo(d, k); }); });
    d.dots.forEach(function (dot, k) { on(dot, 'click', function () { detailGo(d, k); }); });
    d.cond.forEach(function (c, k) {
      on(c, 'click', function (e) { e.preventDefault(); detailView('large', k); });
      on(c, 'keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); detailView('large', k); } });
    });
  });
  function detailCards(d) { return large() ? d.slots.map(function (s) { return s.querySelector('a.card'); }) : d.cond; }
  function riseIn(list) {
    list.forEach(function (el, i) {
      el.animate([{ opacity: 0, transform: RISE }, { opacity: 1, transform: 'none' }], { duration: 300, delay: 20 + i * 35, easing: EASE, fill: 'backwards' });
    });
  }
  // +/− while Page 2 is open: the same card morphs between the two views (like Page 1's switchView)
  function detailView(v, card) {
    var d = curDetail();
    if (!d || !detailOpen() || detailBusy || morphing || v === wrap.getAttribute('data-view')) return;
    if (v === 'condensed' && !d.cond.length) return;   // no condensed layer for the team pages
    var k = card != null ? card : Math.max(0, d.active), toLarge = v === 'large';
    var instant = !Element.prototype.animate;
    var headFrom = headShot(), fromEl = toLarge ? d.cond[k] : d.slots[k] && d.slots[k].querySelector('a.card');
    var m = !instant && fromEl ? morphFrom(fromEl) : null;
    var others = !instant && toLarge ? d.cond.filter(function (_, j) { return j !== k; }).map(morphFrom) : [];
    wrap.setAttribute('data-view', v);
    labelToggle(v);
    lastCard = 0;   // Page 1 underneath follows along, parked on its first card for the way back
    if (toLarge) { active = -1; go(0, true); setActive(0); setHead('bar'); detailPlace(d, k); }
    if (!m) return;
    detailBusy = true;
    var D = 300, toEl = toLarge ? d.slots[k].querySelector('a.card') : d.cond[k], r1 = toEl.getBoundingClientRect();
    toEl.style.opacity = '0';
    var flips = flipHead(headFrom, D), anims = flips.map(function (o) { return o.anim; });
    anims.push(m.box.animate([geo(m.r), geo(r1)], { duration: D, easing: EASE, fill: 'forwards' }));
    m.copy.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 120, fill: 'forwards' });
    others.forEach(function (g) {
      g.box.animate([{ transform: 'scale(1)', opacity: 1 }, { transform: 'scale(1.12)', opacity: 0 }], { duration: 160, easing: EASE, fill: 'forwards' });
    });
    if (toLarge) {
      [d.slots[k - 1], d.slots[k + 1]].forEach(function (s) {
        if (s) s.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, delay: D - 90, easing: 'ease-out', fill: 'backwards' });
      });
      d.dots.forEach(function (dot) { dot.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, delay: D - 90, fill: 'backwards' }); });
    } else {
      d.cond.forEach(function (el, j) {
        if (j !== k) el.animate([{ transform: 'scale(1.08)', opacity: 0 }, { transform: 'none', opacity: 1 }], { duration: 240, delay: 50, easing: EASE, fill: 'backwards' });
      });
    }
    Promise.all(anims.map(fin)).then(function () {
      toEl.style.opacity = '';
      var inAnim = toEl.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 120, easing: 'ease-out' });
      m.box.remove();
      others.forEach(function (g) { g.box.remove(); });
      detailBusy = false;
      fin(inAnim).then(function () { endFlip(flips); });
    });
  }
  function clearPull() {
    var d = curDetail();
    if (!d) return;
    ['transform', 'borderRadius', 'boxShadow', 'overflow', 'opacity'].forEach(function (k) { d.el.style[k] = ''; });
    wrap.removeAttribute('data-pulling');
  }
  function openDetail(key, o) {
    if (typeof key === 'object') { o = key; key = keyFromHash() || availableKeys()[0]; }   // reopening without knowing which (shared link, popstate)
    o = o || {};
    var d = details[key];
    if (!d || detailOpen() || detailBusy || morphing) return;
    // The team pages have no condensed layer -- opening one from the condensed view would
    // otherwise show nothing at all, so force Page 1 (and it) into the expanded view first.
    if (!d.cond.length && !large()) { wrap.setAttribute('data-view', 'large'); labelToggle('large'); go(lastCard, true); setActive(lastCard); }
    var src = sourceCard(key), instant = o.instant || !Element.prototype.animate || !src;
    var headFrom = large() ? headShot() : null, m = instant ? null : morphFrom(src);
    headBefore = wrap.getAttribute('data-head');
    wrap.setAttribute('data-detail', key);
    if (large()) { setHead('bar'); detailPlace(d, 0); }
    if (o.push !== false) history.pushState(Object.assign({}, history.state, { p2: key }), '', (hashBase() || '#') + d.hash);
    if (instant) return;
    detailBusy = true;
    var D = 300, area = d.el.getBoundingClientRect(), flips = headFrom ? flipHead(headFrom, D) : [];
    d.el.style.opacity = '0';
    m.copy.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 120, fill: 'forwards' });
    var grow = m.box.animate([shellFrame(m.r, '20px', 'rgba(0,0,0,.12)'), shellFrame(area, '0px', 'rgba(0,0,0,0)')],
                             { duration: D, easing: EASE, fill: 'forwards' });
    Promise.all([grow].concat(flips.map(function (f) { return f.anim; })).map(fin)).then(function () {
      d.el.style.opacity = '';
      m.box.remove();
      endFlip(flips);
      riseIn(detailCards(d));
      if (large()) d.dots.forEach(function (dot) { dot.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, delay: 40, fill: 'backwards' }); });
      if (p2Back) p2Back.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, easing: 'ease-out' });
      detailBusy = false;
    });
  }
  function closeDetail(o) {
    o = o || {};
    var d = curDetail();
    if (!d || !detailOpen() || detailBusy) return;
    if (!o.fromHistory && history.state && history.state.p2 && detailInHash()) { history.back(); return; }  // popstate brings us back here
    if (!o.fromHistory && detailInHash()) {   // opened from a shared link: nothing to go back to, just drop it from the URL
      var st = Object.assign({}, history.state); delete st.p2;
      history.replaceState(st, '', hashBase() || location.pathname + location.search);
    }
    var src = sourceCard(d.key), instant = o.instant || !Element.prototype.animate || !src;
    function finish() {
      wrap.removeAttribute('data-detail');
      wrap.removeAttribute('data-closing');
      clearPull();
      d.active = -1;
    }
    function restoreHead() { if (large()) { setHead(headBefore === 'card' && active === 0 ? 'card' : 'bar'); } }
    if (instant) { finish(); restoreHead(); updateHead(); return; }
    detailBusy = true;
    var D = 280, from = d.el.getBoundingClientRect(), radius = d.el.style.borderRadius || '0px', headFrom = large() ? headShot() : null;
    // Page 1 shows again underneath; an outline shrinks from the detail's frame onto its source card
    // while the detail (on top of it) fades out
    wrap.setAttribute('data-closing', '');
    var box = document.createElement('div');
    box.className = 'morph';
    Object.assign(box.style, geo(from), { borderRadius: radius });
    wrap.insertBefore(box, d.el);
    restoreHead();
    var r1 = src.getBoundingClientRect();
    src.style.opacity = '0';
    var flips = headFrom ? flipHead(headFrom, D) : [];
    var fade = d.el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 140, fill: 'forwards' });
    var shrink = box.animate([shellFrame(from, radius, 'rgba(0,0,0,.12)'), shellFrame(r1, '20px', 'rgba(0,0,0,.12)')],
                             { duration: D, easing: EASE, fill: 'forwards' });
    Promise.all([shrink, fade].concat(flips.map(function (f) { return f.anim; })).map(fin)).then(function () {
      fade.cancel();
      finish();
      src.style.opacity = '';
      var inAnim = src.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 120, easing: 'ease-out' });
      box.remove();
      detailBusy = false;
      updateHead();
      fin(inAnim).then(function () { endFlip(flips); });
    });
  }
  // Pull-to-close support for the Page 0 overlay's gesture code: follow the finger (dy px), or spring back.
  function pullDetail(dy, spring) {
    var d = curDetail();
    if (!d || !detailOpen()) return;
    if (spring) {
      var cur = d.el.style.transform || 'none';
      var a = d.el.animate([{ transform: cur }, { transform: 'none' }], { duration: 200, easing: EASE });
      d.el.style.transform = '';
      fin(a).then(function () { if (!d.el.style.transform) clearPull(); });
      return;
    }
    var pp = Math.min(1, dy / (innerHeight * 0.55)), sc = 1 - 0.25 * pp;
    wrap.setAttribute('data-pulling', '');
    Object.assign(d.el.style, { transform: 'translateY(' + (dy * 0.55) + 'px) scale(' + sc + ')', borderRadius: (20 / sc) + 'px',
      boxShadow: '0 0 0 ' + (1 / sc) + 'px rgba(0,0,0,.12)', overflow: 'hidden' });
  }
  if (p2Back) on(p2Back, 'click', function (e) { e.preventDefault(); closeDetail(); });
  on(window, 'popstate', function () {
    var key = keyFromHash();
    if (key && !detailOpen()) openDetail(key, { push: false });
    else if (!key && detailOpen()) closeDetail({ fromHistory: true });
  });

  // Kickoff countdowns on Page 2 (one per view): tick every second while the page is open,
  // showing only two units at a time -- days+hours with more than a day to go, hours+minutes
  // with less than a day but more than an hour, minutes+seconds inside the final hour. There's
  // no live score feed, so once kickoff passes there's nothing left to count down to and it just
  // reads LIVE until the next data refresh marks the game final.
  var cds = [].slice.call(root.querySelectorAll('[data-kickoff]')), cdTimer = null;
  function tick() {
    cds.forEach(function (cd) {
      var ko = Date.parse(cd.getAttribute('data-kickoff')), left = ko - Date.now();
      if (isNaN(ko)) return;
      var status = cd.querySelector('.cd-status'), rows = [].slice.call(cd.querySelectorAll('.cd-row'));
      if (left <= 0) {
        rows.forEach(function (r) { r.hidden = true; });
        status.hidden = false;
        status.textContent = 'LIVE';
        return;
      }
      status.hidden = true;
      var secs = Math.floor(left / 1000);
      var v = { d: Math.floor(secs / 86400), h: Math.floor(secs % 86400 / 3600), m: Math.floor(secs % 3600 / 60), s: secs % 60 };
      var show = v.d >= 1 ? ['d', 'h'] : (v.h >= 1 ? ['h', 'm'] : ['m', 's']);
      rows.forEach(function (r) {
        var key = r.getAttribute('data-u'), visible = show.indexOf(key) !== -1;
        r.hidden = !visible;
        if (!visible) return;
        var n = r.querySelector('.cd-n'), u = r.querySelector('.cd-u'), val = v[key];
        if (n.textContent !== String(val)) n.textContent = val;
        var w = u.getAttribute('data-w') + (val === 1 ? '' : 'S');
        if (u.textContent !== w) u.textContent = w;
      });
    });
  }
  if (cds.length) { tick(); cdTimer = setInterval(tick, 1000); }
  function back() { if (opts.onBack) opts.onBack(); else location.href = week.href; }
  on(week, 'click', function (e) { if (opts.onBack) { e.preventDefault(); opts.onBack(); } });
  on(window, 'keydown', function (e) {
    if (e.key === 'Escape') { if (detailOpen()) closeDetail(); else back(); return; }
    if (!large()) return;
    if (detailOpen()) {
      var cd = curDetail();
      if (!cd) return;
      if (e.key === 'ArrowDown' || e.key === 'PageDown') { e.preventDefault(); detailGo(cd, cd.active + 1); }
      else if (e.key === 'ArrowUp' || e.key === 'PageUp') { e.preventDefault(); detailGo(cd, cd.active - 1); }
      return;
    }
    if (e.key === 'ArrowDown' || e.key === 'PageDown') { e.preventDefault(); go(active + 1); }
    else if (e.key === 'ArrowUp' || e.key === 'PageUp') { e.preventDefault(); go(active - 1); }
  });
  on(window, 'resize', function () {
    if (!large()) return;
    if (wrap.hasAttribute('data-detail')) {
      var d = curDetail();
      if (d) { var k = Math.max(0, d.active); d.active = -1; detailGo(d, k, true); detailSetActive(d, k); }
    } else { go(active, true); updateHead(); }
  });
  // Opens expanded unless told otherwise; opts.card keeps the same card when swiping between games.
  var startView = opts.view === 'condensed' ? 'condensed' : 'large';
  wrap.setAttribute('data-view', startView);
  labelToggle(startView);
  if (startView === 'large') { setHead(lastCard === 0 ? 'card' : 'bar'); requestAnimationFrame(function () { go(lastCard, true); setActive(lastCard); updateHead(); }); }
  if (opts.detail === undefined ? keyFromHash() : opts.detail) {
    var openKey = keyFromHash() || availableKeys()[0];
    if (openKey) {
      if (large()) { headBefore = 'card'; }
      openDetail(openKey, { instant: true, push: false });
    }
  }
  // Pinch to toggle expanded/condensed (2026-09-21, replaces pinch-to-close): scale < 1 is a
  // pinch in (go condensed), > 1 is a pinch out (go expanded); a small wobble around 1 does
  // nothing. Whichever detail (if any) is open decides for itself -- Game Info has a condensed
  // layout to switch to, the team pages don't, so pinching there is a no-op.
  function pinchToggle(scale) {
    var goCondensed = scale < 0.82, goExpanded = scale > 1.18;
    if (!goCondensed && !goExpanded) return;
    var d = curDetail();
    if (d) { if (d.cond.length) detailView(goCondensed ? 'condensed' : 'large'); return; }
    switchView(goCondensed ? 'condensed' : 'large');
  }
  // Standalone page only (opts.onBack is how the Page 0 overlay always calls in -- it wires this
  // same pinchToggle to its own two-finger gesture instead, see PAGE1_OVERLAY_JS).
  if (!opts.onBack) {
    var pinchD0 = 0, pinchScale = 1, pinching = false;
    function twoFingerDist(t) { return Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY); }
    on(root, 'touchstart', function (e) {
      if (e.touches.length === 2) { pinching = true; pinchD0 = twoFingerDist(e.touches); pinchScale = 1; }
    }, { passive: true });
    on(root, 'touchmove', function (e) {
      if (!pinching || e.touches.length !== 2) return;
      if (e.cancelable) e.preventDefault();
      pinchScale = twoFingerDist(e.touches) / pinchD0;
    }, { passive: false });
    function endPinch(e) {
      if (!pinching || (e.touches && e.touches.length >= 2)) return;
      pinching = false;
      pinchToggle(pinchScale);
    }
    on(root, 'touchend', endPinch);
    on(root, 'touchcancel', endPinch);
  }
  return {
    view: function () { return wrap.getAttribute('data-view'); },
    card: function () { return lastCard; },
    head: visibleHead,
    detail: detailOpen,
    detailAtTop: function () { var d = curDetail(); return !large() || !d || !d.deck || d.deck.scrollTop <= 1; },
    closeDetail: closeDetail,
    pullDetail: pullDetail,
    pinch: pinchToggle,
    destroy: function () {
      if (cdTimer) clearInterval(cdTimer);
      bound.forEach(function (b) { b[0].removeEventListener(b[1], b[2], b[3]); }); bound = [];
    }
  };
} };
"""

# ---------------------------------------------------------------- styles (ported 1:1 from the approved v8 preview)

P1_CSS = "\n:host{display:block}\n" + (
    f".p1{{--ink:{theme.TEXT};--tile:{theme.TILE};--tile-border:{theme.TILE_BORDER};--tile-border-soft:rgba(0,0,0,.07);"
    f"--tile-hover:{theme.TILE_HOVER};--tile-border-hover:{theme.TILE_BORDER_HOVER};--text-2:{theme.TEXT_2};--text-3:{theme.TEXT_3};\n"
    "  --out:#A00000;--doubt:#A52800;--ques:#B58900;--win:#1E8A3C;--loss:#A00000;--tie:#B58900;--gold:#D4A20A;--silver:#A2A7AD;"
    f"--bronze:#B5702F;--bar:64px;--bbar:{theme.BBAR_HEIGHT};--peek:40px;--gap:12px;--col:600px;--ctitle:clamp(22px,3.2vh,30px)}}"
) + r"""
*{box-sizing:border-box;margin:0;padding:0}
.p1{min-height:100%;background:#fff;color:var(--ink);font-family:Inter,system-ui,-apple-system,sans-serif;font-weight:400;-webkit-font-smoothing:antialiased}
.view{display:none}
.p1[data-view=condensed] .view-c{display:grid}
.p1[data-view=large] .view-l,.p1[data-view=large] .dots{display:block}
/* Team abbreviations: Saira italic, width 95, weight 800, 20 tracking (Jason, 2026-09-18) --
   matches Page 0. The "‹ Week N" pill, records, times and every label stay Inter. */
.abbr{line-height:1;font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;font-style:italic;
  font-variation-settings:'wdth' 95;letter-spacing:.02em}
a.card{position:relative;display:block;color:inherit;text-decoration:none;background:var(--tile);border:1px solid var(--tile-border);border-radius:20px;
  transition:transform .16s,background-color .16s,border-color .16s}
a.card:focus-visible{outline:2px solid #000;outline-offset:2px}

/* ===== Top bar ===== */
.bar{position:fixed;inset:0 0 auto;height:var(--bar);z-index:10;background:rgba(255,255,255,.94);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.bar-in{position:relative;max-width:var(--col);height:100%;margin:0 auto;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px}
/* Bottom bar (2026-09-17): "‹ Week N" back button centered + the +/− toggle on the right, in the same
   spot and size as Page 0's bottom week picker */
.bbar{position:fixed;inset:auto 0 0;height:var(--bbar);padding-bottom:env(safe-area-inset-bottom);z-index:10;background:rgba(255,255,255,.94);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.bbar-in{position:relative;max-width:var(--col);height:52px;margin:0 auto;display:flex;align-items:flex-start;justify-content:center;padding-top:10px}
.week{color:inherit;text-decoration:none;display:inline-flex;align-items:center;gap:6px;font-size:16px;font-weight:400;line-height:19px;padding:6px 12px;border-radius:999px;transition:background-color .16s}
.week:hover{background:rgba(0,0,0,.05)}
.week:focus-visible{outline:2px solid #000;outline-offset:2px}
.week .chev{width:12px;height:12px}
/* The header row is sized in em so the same row can be drawn at any size and scale cleanly between them:
   20px in the condensed bar (44px helmets, unchanged), smaller in the expanded bar, larger in the Game Info card. */
.teams{display:flex;align-items:center;gap:.4em;font-size:20px}
.side,.mid{display:flex;align-items:center;gap:.4em}
.teams .abbr{font-size:1em}
.teams .at{font-size:.8em;padding:0 .25em}
.teams .at-final{font-weight:700;letter-spacing:.04em;white-space:nowrap;padding:0 .3em;
  display:inline-flex;align-items:center;gap:.22em}   /* 16px in the 20px bar = Page 0's FINAL */
.hero .teams .at-final{font-size:.44em;padding:0 .35em}   /* in the Game Info card: label-sized (~16px), so the teams keep their room */
@media (max-width:400px){.bar .teams .at-final{font-size:.58em;padding:0 .2em}}   /* Page 0 drops FINAL to 11px here too */
@media (max-width:344px){.p1:not([data-view=large]) .bar .teams{font-size:17px}}
.teams img{display:block;width:2.2em;height:2.2em}
.bar .teams{pointer-events:none}
.when{display:none;flex-direction:column;align-items:center;font-size:11px;font-weight:700;letter-spacing:.1em;line-height:1.35;color:var(--text-2);white-space:nowrap}
.final-lbl{display:none;align-items:center;gap:5px;font-size:16px;font-weight:700;letter-spacing:.04em;line-height:1.2;white-space:nowrap}   /* same as Page 0's FINAL */
/* Winner triangle next to every "FINAL"/"FINAL/OT" in the header (2026-09-21, matches Page 0):
   one shape, mirrored for the home side, only the winner's copy shown. */
.tri{display:inline-flex;visibility:hidden;flex:none;color:currentColor}
.tri svg{display:block;width:.4em;height:.5em}
.tri-h svg{transform:scaleX(-1)}
.p1[data-win=away] .tri-a,.p1[data-win=home] .tri-h{visibility:visible}
/* ===== Expanded view header (2026-09-17) =====
   Game Info card: each team stacks — final score on top, then the helmet, then the abbreviation.
   Top bar, game still to come: helmet + abbreviation (abbreviation on the inside) at opposite edges of
   the screen, with the date and time in the middle.
   Top bar, game final: one line — away helmet, abbreviation, score, then the home score, abbreviation,
   helmet; the date and time aren't needed once a game is over. */
.p1[data-view=large] .hero .side{flex-direction:column;gap:.08em}
.p1[data-view=large] .hero .side img{order:2;width:2.6em;height:2.6em}
.p1[data-view=large] .hero .side .hscore{order:1;font-size:2.2em;margin-bottom:.14em}   /* the score sits high above the helmet (2026-09-21: bumped up from 1.6em) */
.p1[data-view=large] .hero .side .abbr{order:3}
.p1[data-view=large] .bar .teams{font-size:17px;width:100%;padding:0 16px;justify-content:space-between}
.p1[data-view=large] .bar .side img{width:2.4em;height:2.4em}
.p1[data-view=large] .bar .at{display:none}
.p1[data-view=large]:not([data-final]) .bar .when{display:flex}
.p1[data-view=large][data-final] .bar .final-lbl{display:inline-flex}
/* which copy of the header shows in the expanded view: in the card (data-head=card), in the bar (bar),
   or neither while the moving copies (.head-fly) travel between them (moving) */
.p1[data-view=large][data-head=card] .bar .teams,.p1[data-view=large][data-head=card] .when{visibility:hidden}
.p1[data-view=large][data-head=bar] .hero .teams,.p1[data-view=large][data-head=moving] .hero .teams,.p1[data-view=large][data-head=moving] .bar .teams{visibility:hidden}
/* The winner triangle's own visibility:visible (further down) would otherwise win the cascade
   over an ancestor's visibility:hidden above -- re-hide it in whichever copy the rules above
   already hid, so a "won" triangle doesn't float on screen on its own during the flip (2026-09-21). */
.p1[data-view=large][data-head=card] .bar .tri,
.p1[data-view=large][data-head=bar] .hero .tri,
.p1[data-view=large][data-head=moving] .hero .tri,
.p1[data-view=large][data-head=moving] .bar .tri{visibility:hidden}
.head-fly{position:fixed;inset:0;display:block;margin:0;z-index:12;pointer-events:none}
.head-fly .hf{position:fixed;margin:0;transform-origin:0 0;will-change:transform,opacity}
.p1:not([data-view=large]) .head-fly,.p1[data-view=large]:not([data-head=moving]) .head-fly{display:none}
/* +/- toggle (2026-09-17): no circle and no hover fill -- hovering or pressing only enlarges it.
   Page 0's bottom bar uses the same rules, so the button is identical on both pages. */
.toggle{position:absolute;right:16px;top:9px;width:34px;height:34px;border:0;background:none;color:#000;padding:0;
  display:flex;align-items:center;justify-content:center;cursor:pointer;-webkit-tap-highlight-color:transparent;
  transition:transform .2s cubic-bezier(.22,1,.36,1)}
.toggle:hover{transform:scale(1.18)}
.toggle:active{transform:scale(1.30)}
.toggle:focus-visible{outline:2px solid #000;outline-offset:2px;border-radius:50%}
.toggle .i-minus,.p1[data-view=large] .toggle .i-plus{display:none}
.p1[data-view=large] .toggle .i-minus{display:block}

/* ===== Condensed view: everything on one screen ===== */
/* Row heights (2026-09-17, Jason): the comparison card is the one worth reading, so it takes
   height from the other two. Was .74 / 1.3 / 1.38. */
.view-c{max-width:var(--col);margin:0 auto;height:100dvh;min-height:720px;padding:calc(var(--bar) + 12px) 16px calc(var(--bbar) + 12px);gap:12px;
  grid-template-rows:minmax(0,.62fr) minmax(0,1.18fr) minmax(0,1.62fr)}
.view-c a.card:hover,.view-c a.card:focus-visible{transform:scale(1.03);border-color:var(--tile-border-hover);z-index:1}

/* Game info: content pulled in from the edges, centered vertically */
a.card.c-game{padding:var(--ctitle) clamp(22px,7%,32px) clamp(16px,2.6vh,24px);display:flex;flex-direction:column;justify-content:center;gap:clamp(4px,1vh,14px);overflow:hidden}
.c-game .time{font-size:clamp(25px,3.7vh,40px)} .c-game .time small{font-size:12px}
.c-game .date{font-size:clamp(14px,2.1vh,22px);margin-top:2px}
.c-game .network{font-size:12px;margin-top:6px}
/* (2026-09-21) city/weather were flush with the card's bottom corners -- the bigger bottom
   padding above buys room from the edge; this adds a little more air between the two of them */
.c-game .game-bottom{gap:16px;margin-top:2px}
.c-game .city{font-size:13px;padding-left:0}
.c-game .temp{font-size:clamp(20px,3vh,28px)}
.c-game .weather{gap:7px} .c-game .weather svg{width:32px;height:24px}

/* Team cards: centered column — trend + record, 3 injuries, spaced ranks */
.c-teams{display:grid;grid-template-columns:1fr 1fr;gap:12px;min-height:0}
a.card.c-team{padding:var(--ctitle) 10px clamp(8px,1.4vh,14px);display:flex;flex-direction:column;align-items:center;justify-content:space-evenly;text-align:center;overflow:hidden;min-width:0;container-type:inline-size}
/* helmet + abbreviation left, last-game arrow + record right -- same as the expanded card (2026-09-17) */
.c-team .l-top{width:100%;display:flex;align-items:center;justify-content:center;gap:10px;padding:0 2px}
.c-team .l-id{gap:1px}
.c-team .l-id img{width:clamp(26px,3.7vh,36px);height:clamp(26px,3.7vh,36px);display:block}
.c-team .l-id .abbr{font-size:12px}
.c-team .l-rec{gap:6px;min-width:0}
.c-team .streak{gap:1px}
.c-team .streak b{font-size:clamp(12px,1.7vh,15px)}
.c-team .streak .trend{width:12px;height:8px}
.c-team .l-top{padding-top:6px;padding-bottom:5px}
.c-team .record{font-weight:900;line-height:1;letter-spacing:-.01em;white-space:nowrap;
  font-size:clamp(26px,3.9vh,38px);font-size:min(clamp(26px,3.9vh,38px),calc((100cqi - 92px) / 1.8))}
.c-team .record.rec-4{font-size:28px;font-size:min(clamp(22px,3.5vh,34px),calc((100cqi - 92px) / 2.4))}
.c-team .record.rec-5{font-size:24px;font-size:min(clamp(20px,3.2vh,31px),calc((100cqi - 92px) / 2.85))}
.c-team .record.rec-6{font-size:20px;font-size:min(clamp(18px,2.9vh,27px),calc((100cqi - 92px) / 3.5))}
.trend{flex:none;display:block}
.t-w{color:var(--win)} .t-l{color:var(--loss)} .t-t{color:var(--tie)}
.rc-hit.t-w,.rc-hit.t-l,.rc-hit.t-t{font:inherit}
/* (2026-09-21, Jason) name/dot/status as one centered block instead of spread edge to edge:
   a 3-column grid (li and .inj-s both unboxed via display:contents so the dot gets its own
   column) with names flush left, statuses flush right, dots in a shared middle column. */
.c-inj{font-size:12px;line-height:1.28;width:fit-content;max-width:calc(100% - 24px);margin:0 auto;
  display:grid;grid-template-columns:auto auto auto;column-gap:10px;row-gap:6px;align-items:center}
.c-inj li:not(.inj-none){display:contents}
.c-inj .inj-name{overflow:hidden;text-overflow:ellipsis;text-align:left}
.c-inj .inj-s{display:contents}
.c-inj .inj-dot{justify-self:center}
.c-inj .inj-status{text-align:right;color:var(--text-2)}
.c-inj .inj-none{grid-column:1/-1;text-align:center}
/* (2026-09-17, Jason) the names were 700 like the rank headings below them; Regular separates
   the two and buys back a few pixels of height */
.c-inj .inj-name{font-weight:400}
/* condensed ranks use the expanded layout: ordinal top-right of the number, PTS/YDS under it */
.c-team .ranks{column-gap:clamp(12px,4cqi,26px)}
.c-team .rank-col{gap:clamp(2px,.7vh,7px)}
.c-team .rank-col h3{font-size:13px}
.c-team .rank{width:auto;column-gap:3px}
/* (2026-09-21) grown to actually span the ordinal + label stacked beside it, matching the
   expanded card's proportions instead of reading small and cramped */
.c-team .rank-n{font-size:clamp(28px,3.8vh,36px);min-width:1.25em}
.c-team .rank-sfx{font-size:13px;padding-top:2px}
.c-team .rank-lbl{font-size:10px;letter-spacing:.05em}

/* Leaders: bigger numbers, columns pulled toward the center, league-rank crowns */
/* (2026-09-17, Jason) taller card, and the extra height goes into the gaps between rows --
   no new elements, same number sizes. Each row is its own flex item so space-between can
   spread them; the name still hugs its own stat (v15). */
a.card.c-cmp{display:flex;align-items:center;justify-content:center;padding:var(--ctitle) 0 clamp(10px,1.7vh,18px);overflow:hidden}
.c-cmp-in{width:84%;height:100%;display:flex;flex-direction:column;justify-content:space-between;
  padding:clamp(6px,1.1vh,12px) 0}
.c-cmp-in>.cmp-row:not(.cmp-head){flex:0 0 auto}
.c-cmp .cmp-row{grid-template-columns:1fr 76px 1fr}
.c-cmp .ldr-v{position:relative;display:inline-block;font-size:clamp(18px,2.65vh,26px);font-weight:700;line-height:1}
.c-cmp .ldr-n{font-size:11.5px;line-height:1.1;margin-top:-1px}   /* the name hugs its own stat; the gap to the next row stays larger */
.cm{font-style:normal}
.c-cmp .cm{position:relative;top:-.1em}   /* lift thousands commas so their tails clear the name below */
.c-cmp .cmp-lbl{font-size:10px}
.crown{position:absolute;left:100%;top:50%;transform:translate(4px,-62%);overflow:visible}

/* ===== Large view: one card per screen ===== */
.deck{position:fixed;inset:var(--bar) 0 var(--bbar);overflow-y:auto;overscroll-behavior:contain;scroll-snap-type:y mandatory;scrollbar-width:none;padding:calc(var(--peek) + var(--gap)) 0}
.deck::-webkit-scrollbar{display:none}
.slot{height:100%;min-height:520px;max-width:var(--col);margin:0 auto var(--gap);padding:0 16px;scroll-snap-align:center;scroll-snap-stop:always}
.slot:last-child{margin-bottom:0}
.slot a.card{height:100%;overflow:hidden;transition:transform .2s cubic-bezier(.22,1,.36,1),border-color .15s,background-color .15s}
.body{height:100%;display:flex;flex-direction:column;transition:opacity .15s}
.slot.active a.card{transition:transform .16s,background-color .16s,border-color .16s}
.slot.active a.card:hover,.slot.active a.card:focus-visible{transform:scale(1.03);border-color:var(--tile-border-hover)}
.slot:not(.active) a.card{border-color:var(--tile-border-soft);transform:scale(.96)}
.slot:not(.active) .body{opacity:0}
.peek{position:absolute;left:0;right:0;height:calc(var(--peek) - 1px);display:flex;align-items:center;justify-content:center;gap:7px;font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--text-2);opacity:0;transition:opacity .15s;pointer-events:none}
.peek-top{top:0}.peek-bot{bottom:0}
.slot.below .peek-top,.slot.above .peek-bot{opacity:1}
/* the card in the middle keeps its name at the top, where its sliver showed it (no arrow) */
.slot.active .peek-top{opacity:1}
.slot.active .peek-top svg{display:none}
.slot.below a.card:hover,.slot.above a.card:hover{border-color:var(--tile-border-hover)}
.slot.below a.card:hover .peek,.slot.above a.card:hover .peek{color:#000}
.dots{display:none;position:fixed;right:calc(max(16px,(100vw - var(--col)) / 2 + 16px) / 2 - 3px);top:calc(var(--bar) + (100% - var(--bar) - var(--bbar)) / 2);transform:translateY(-50%);z-index:10}
.dots{flex-direction:column;align-items:center;gap:8px}
.p1[data-view=large] .dots{display:flex}
.dot{width:6px;height:6px;border-radius:3px;border:0;background:#CFCFCF;cursor:pointer;padding:0;transition:height .2s,background-color .2s}
.dot.on{height:18px;background:#000}
/* Page 1's own deck nav (2026-09-23): icons instead of plain dots, selection read as opacity
   (plus a slight scale-up) rather than size/color. Scoped to ".p1 > .dots" (the exact nav this
   page renders) so Page 2's sub-deck navs -- Game Info's own cards, the team pages -- keep the
   plain small dots above, since their ".p2-dots .dot" buttons carry no icon markup and this
   rule never touches them.
   Sized small below 680px on purpose: the card there runs edge to edge behind a flat 16px
   gutter (".slot{padding:0 16px}"), the same gutter the old 6px dot already lived in, so a
   much bigger icon has nowhere to go without either overlapping the card or hanging off the
   physical screen edge. A 10px icon with "right:3px" splits that 16px gutter into a real ~3px
   clearance on both sides of the icon -- sized to still clear both edges once the active icon's
   scale(1.15) below grows it a couple pixels past its own box (transforms don't affect layout,
   only what's painted, so that growth eats directly into this margin). Past 680px the card is
   capped at --col (600px) and the gutter opens right up, so the icon grows to something more
   legible there with room to spare. Gap is inverted on purpose: the smaller the icon, the more
   room it gets, so a tight cluster of small marks doesn't read as one blob -- 18px apart at the
   small mobile size, down to 14px once the icons are big enough to stay legible closer
   together. */
.p1 > .dots{right:3px;gap:18px}
.p1 > .dots .dot{width:10px;height:10px;border-radius:0;background:none;opacity:.4;
  display:flex;align-items:center;justify-content:center;transition:opacity .2s}
.p1 > .dots .dot svg{display:block;width:10px;height:auto;color:#000;transition:transform .2s}
.p1 > .dots .dot.on{height:10px;background:none;opacity:1}
.p1 > .dots .dot.on svg{transform:scale(1.15)}
.p1 > .dots .dot:not(.on):hover{opacity:.7}
@media (min-width:680px){
  .dots{right:calc(50% - 300px - 22px)}
  .p1 > .dots{gap:14px}
  .p1 > .dots .dot{width:24px;height:24px}
  .p1 > .dots .dot svg{width:22px}
  .p1 > .dots .dot.on{height:24px}
  .p1 > .dots .dot.on svg{transform:scale(1.15)}
}

.game .body{padding:44px 24px 32px;justify-content:space-between;container-type:inline-size}
/* the header, big, in the middle of the Game Info card; sized to fit the card (a final-score row is ~15.5em wide) */
.hero{display:flex;justify-content:center}
.hero .teams{gap:.5em;font-size:min(38px,12cqi)}   /* the stacked row is ~7.5em wide, so it can fill the card */
.game-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.time{white-space:nowrap;font-size:63px;font-weight:700;line-height:1;letter-spacing:-.01em}
.time small{font-size:16px;font-weight:400;letter-spacing:0;margin-left:6px}
.date{white-space:nowrap;font-size:34px;font-weight:700;line-height:1.15;margin-top:4px}
.network{font-size:16px;margin-top:40px;text-align:right;min-width:0}
.game-bottom{display:flex;justify-content:space-between;align-items:center}
.city{font-size:18px;padding-left:8px}
.weather{display:flex;align-items:center;gap:14px}
.temp{font-size:43px;font-weight:700;line-height:1}

.team .body{padding:44px 0 30px;justify-content:space-evenly;align-items:center}
.team .body>*{width:min(272px,calc(100% - 80px))}
.l-top{display:flex;align-items:center;justify-content:center;gap:28px}
.l-id{display:flex;flex-direction:column;align-items:center;gap:2px}
.l-id .abbr{font-size:30px}
.l-id img,.l-id-s img{display:block}
.l-rec{display:flex;align-items:center;gap:12px}
.l-rec .trend{width:28px;height:19px}
/* upcoming: streak number with its indicator (chevron above a win streak, chevron/bar below the others) */
.streak{display:flex;flex-direction:column;align-items:center;gap:2px;flex:none;line-height:1}
.streak b{font-size:22px;font-weight:900;line-height:1;font-variant-numeric:tabular-nums}
.streak .trend{width:18px;height:12px}
/* finished: indicator sits on the column this game changed, and that number takes its color */
.rec-split{display:inline-flex;align-items:baseline}
.rc{position:relative;display:inline-block}
.rc-mark{position:absolute;left:50%;transform:translateX(-50%);line-height:0}
/* the same clear ~.12em gap above or below the digit (the line box leaves .115em of space above the numerals and .145em below) */
.rc-mark.above{bottom:calc(100% + .005em)}
.rc-mark.below{top:calc(100% - .025em)}
.rc-mark .trend.t-t{margin-top:-.06em}   /* the tie bar is drawn mid-box, so pull it up to match */
.rc-mark .trend{width:.26em;height:.17em;min-width:11px;min-height:7px}
.team .record{font-size:70px;font-weight:900;line-height:1;letter-spacing:-.01em;white-space:nowrap}
.team .record.rec-4{font-size:52px}.team .record.rec-5{font-size:46px}.team .record.rec-6{font-size:38px}
.l-inj{list-style:none;display:flex;flex-direction:column;gap:9px;font-size:15px;line-height:1.2}
.l-inj li{display:flex;justify-content:space-between;align-items:baseline;gap:12px;white-space:nowrap}
.l-inj .inj-name{font-weight:700;overflow:hidden;text-overflow:ellipsis}
.l-inj .inj-s{font-weight:700;flex:none}
.l-inj .inj-none{font-weight:400;justify-content:center}
.injuries{list-style:none;font-weight:700;min-width:0}
.team .injuries{font-size:16px;line-height:1.3}
.injuries li{display:flex;gap:5px;white-space:nowrap}
.inj-name{overflow:hidden;text-overflow:ellipsis}
.inj-s{flex:none;display:inline-flex;align-items:center;gap:5px;color:var(--ink)}
/* Status reads as a colored dot, not colored text (Jason, 2026-09-20) */
.inj-dot{width:8px;height:8px;border-radius:50%;flex:none}
.inj-dot.inj-out{background:var(--out)}.inj-dot.inj-doubt{background:var(--doubt)}.inj-dot.inj-ques{background:var(--ques)}
.inj-none{font-weight:400}
.ranks{display:grid;grid-template-columns:1fr 1fr}
.rank-col{display:flex;flex-direction:column;align-items:center;gap:12px}
.rank-col h3{font-size:24px;font-weight:700;line-height:1.2}
/* row2 is 1fr (2026-09-21, was auto) so it absorbs the extra height rank-n's span needs, which
   pushes rank-lbl (align-self:end below) down to sit right at rank-n's own bottom edge instead
   of floating in a gap above it. */
.rank{display:grid;grid-template-columns:auto auto;grid-template-rows:auto 1fr;column-gap:3px;align-items:start;width:112px}
/* Ranks are stats -> Teko (Jason, 2026-09-18); the PTS/YDS labels stay Inter. */
.rank-n{grid-row:1/3;font-size:44px;line-height:1;text-align:right;min-width:52px;
  font-family:Teko,Inter,system-ui,sans-serif;font-weight:700}
.rank-sfx{font-size:16px;line-height:1;padding-top:3px;font-family:Teko,Inter,system-ui,sans-serif;font-weight:700}
.rank-lbl{font-size:12px;font-weight:300;line-height:1;align-self:end;letter-spacing:.02em}

.compare .body{padding:46px 0 20px;justify-content:space-evenly;align-items:center}
.compare .body>.cmp-row{width:90%}
.compare .cmp-row{grid-template-columns:1fr 84px 1fr}
.cmp-row{display:grid;grid-template-columns:1fr 104px 1fr;align-items:center}
.cmp-head{justify-items:center}
.pill{display:block;width:56px;height:14px;border-radius:999px}
.c-cmp .pill{width:36px;height:9px}
.c-cmp .cmp-head{padding-bottom:4px}
.ldr{text-align:center;min-width:0}
/* Leader values are stats -> Teko; the player names under them stay Inter. */
.ldr-v{font-size:20px;line-height:1.2;font-family:Teko,Inter,system-ui,sans-serif;font-weight:700}
.compare .ldr-v{position:relative;display:inline-block;font-size:clamp(28px,8.2vw,36px);line-height:1.05}
.compare .ldr-v .crown{width:20px;height:16px;transform:translate(5px,-64%)}
/* home column: crown in front of the number, so crowns sit toward the middle of the chart */
.cmp-row>.ldr:last-child .crown{left:auto;right:100%;transform:translate(-4px,-62%)}
.compare .cmp-row>.ldr:last-child .ldr-v .crown{transform:translate(-5px,-64%)}
.compare .ldr-n{margin-top:2px}
.ldr-n{font-size:14px;white-space:nowrap;display:flex;justify-content:center;min-width:0}
.ldr-n .nm{overflow:hidden;text-overflow:ellipsis;min-width:0}
.ldr-n .pos{font-weight:200;flex:none;margin-left:.28em}   /* position never gets cut off */
.cmp-lbl{font-size:12px;text-align:center;line-height:1.2}

@media (max-width:400px){.final-lbl{font-size:11px}.view-l .time{font-size:54px}.view-l .date{font-size:29px}.team .record{font-size:62px}.team .record.rec-4{font-size:48px}.team .record.rec-5{font-size:42px}.team .record.rec-6{font-size:35px}
  .game .body{padding-left:16px;padding-right:16px}.team .body>*{width:min(272px,calc(100% - 64px))}}
@media (max-height:700px){.p1{--peek:28px}.l-id img{width:64px;height:64px}}
/* no prefers-reduced-motion override: motion always plays (Jason, 2026-09-17) */
/* ===== Production additions (not in the preview) ===== */
/* Finished games: final score sits in the header next to each abbreviation */
.teams .hscore{font-size:1.35em;line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-.01em;padding:0 .1em;
  font-family:Teko,Inter,system-ui,sans-serif;font-weight:700}   /* final score in the header -> Teko (2026-09-21: bumped up from 1em) */
.teams .hscore.lose{opacity:.3}
a.card{cursor:pointer}
/* condensed cards: name at the top center, same type as the expanded slivers */
.card-title{position:absolute;left:0;right:0;top:0;height:var(--ctitle);display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--text-2);pointer-events:none;line-height:1}
/* view toggle: a card-shaped box that grows/shrinks between the two views */
.morph{position:fixed;z-index:9;background:var(--tile);border:1px solid var(--tile-border);border-radius:20px;overflow:hidden;pointer-events:none}
.morph>.card{position:absolute;left:0;top:0;border:0;border-radius:0;background:transparent;transform:none;transition:none}
.temp-word{font-size:26px}
.c-game .temp-word{font-size:clamp(18px,2.6vh,22px)}
.temp-na,.rank-n.na,.crank b.na,.ldr-v.na{color:var(--text-3)}
.inj-none{color:var(--text-2)}
.l-inj .inj-none{font-weight:400}

"""

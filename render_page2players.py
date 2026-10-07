"""
Page 2 -- Player Stats (2026-09-28), reached by tapping the Leaders card on Page 1 (which
already carried data-detail="leaders"). Like the team pages, it's a hidden .p2 layer inside
each game's Page 1 block (data-page="leaders"), expanded view only, opened and closed by
render_page1.P1_JS's detail registry.

Six cards, each the season to date for both teams (player_stats.season_totals: regular-season
weeks before this game; playoffs use the whole regular season):
  1. Passing   -- everyone with a pass attempt          both teams stacked
  2. Rushing   -- everyone with a rush attempt          team switch
  3. Receiving -- everyone with a target or catch       team switch
  4. Defense   -- everyone with any defensive stat      team switch
  5. Kicking   -- field goals / PATs, then punting      both teams stacked
  6. Returns   -- kick returns, then punt returns       both teams stacked, or the team switch
                                                        once a team has 2+ of either (2026-10-07)

Layout (Jason, 2026-09-28, from the mockups' three versions): a box-score table with the
player column pinned on the left. The short cards (Passing, Kicking, Returns: usually a
player or two per team) stack both teams on one card; the long ones (Rushing, Receiving,
Defense: 25-40 players a team on Defense) put the two teams behind a switch. Long lists
scroll inside the card; a table wider than the card (Defense) scrolls sideways, with a fade
on its right edge while there's more to see (the .more class, set by P1_JS).

Tables start sorted by the card's main stat (yards for Passing, Rushing and Receiving; tackles
for Defense). Tapping a column header sorts by that stat and only then highlights the column
(P1_JS). A number in the league's top 3 for one of player_stats.MEDAL_STATS gets a gold, silver
or bronze bar under it (Jason, 2026-09-28) -- season to date only; a finished game's own stats
have none (2026-10-03).

Data: game_details[<id>]["player_stats"] = {"away": [...], "home": [...]}, attached by
render_page1.write_all from data/matchups.json's "player_weeks" (player_stats.py), each
player's row carrying "medals" = {stat: 1 | 2 | 3} (player_stats.league_medals).
A finished regular-season game shows that game's stats instead of the season's (Jason,
2026-09-29): same cards, columns and rules, minus the top-3 bars
(player_stats.season_totals with week=...). Until nflverse publishes the game's
player stats, and for playoff games, it stays season to date (render_page1.write_all).

Missing data never breaks the page: a team with nobody in a card reads "None this season"
("None this game" on a finished game; "No games played yet" in Week 1).
"""

import html

import helmets

DASH = "—"


def esc_name(name):
    """A person's name for the page, each hyphen in its own .hy span (Jason, 2026-10-07): Inter's
    hyphen carries wide side bearings, so "Smith-Njigba" read as "Smith - Njigba"; .hy pulls them in.
    Used wherever a player's or coach's name is shown, site-wide."""
    return esc(name or "").replace("-", '<span class="hy">-</span>')


def esc(v):
    return html.escape(str(v), quote=True)


# ---------------------------------------------------------------- formatting

def _n(v):
    return f"{int(round(v)):,}" if v is not None else DASH


def _avg(num, den):
    return f"{num / den:.1f}" if den else DASH


def _pct(num, den):
    return f"{num / den * 100:.0f}" if den else DASH


def _sacks(v):
    return f"{v:g}"


def _rating(r):
    """NFL passer rating."""
    att = r["att"]
    if not att:
        return DASH
    clamp = lambda x: max(0.0, min(2.375, x))
    parts = (clamp((r["cmp"] / att - 0.3) * 5), clamp((r["pyds"] / att - 3) * 0.25),
             clamp(r["ptd"] / att * 20), clamp(2.375 - r["int"] / att * 25))
    return f"{sum(parts) / 6 * 100:.1f}"


SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
PARTICLES = {"st.", "st", "van", "von", "de", "del", "della", "da", "di", "du", "la", "le", "dos", "das"}


def split_name(name):
    """('J. Michael', 'Sturdivant'), ('Amon-Ra', 'St. Brown'), ('Ennis', 'Rakestraw Jr.'): the last name is the
    final word, plus a suffix after it or a particle before it; everything ahead of that is the first name."""
    words = (name or "").split()   # any whitespace, non-breaking included
    if len(words) < 2:
        return "", " ".join(words)
    i = len(words) - 1
    if words[i].lower() in SUFFIXES and i > 1:
        i -= 1
    if words[i - 1].lower() in PARTICLES and i > 1:
        i -= 1
    return " ".join(words[:i]), " ".join(words[i:])


ROOKIE_MARK = ' · <span class="rk">R</span>'   # render_page1 shows these too, through marks()
IR_MARK = ' · <span class="ir">IR</span>'       # injured reserve (2026-10-03, reserve.py), after the R if both


def marks(r):
    """The rookie R and the IR tag a player row carries, in that order."""
    r = r or {}
    return (ROOKIE_MARK if r.get("rookie") else "") + (IR_MARK if r.get("ir") else "")


def name_html(r):
    """The player's full name, first name over last name (Jason, 2026-09-30: full names, stacked,
    so the tables grow down rather than sideways), and beside them his jersey number over his
    position (2026-10-03)."""
    first, last = split_name(r["name"])
    top = f'<span class="ps-fn">{esc_name(first)}</span> ' if first else ""
    # the last name stays on one line ("St. Brown") except after a hyphen or before a suffix ("Jr.")
    words = last.split()
    if len(words) > 1 and words[-1].lower() in SUFFIXES:
        last = "&nbsp;".join(esc_name(w) for w in words[:-1]) + " " + esc(words[-1])
    else:
        last = "&nbsp;".join(esc_name(w) for w in words)
    num = f'#{r["jersey"]}' if r.get("jersey") is not None else ""
    return (f'<span class="ps-nm">{top or "<span class=ps-fn></span>"}<span class="ps-no">{num}</span>'
            f'<span class="ps-ln"><span class="ps-lt">{last}</span></span> '
            f'<span class="ps-pos">{esc(r["pos"])}{marks(r)}</span></span>')


def short_name_html(r):
    """The condensed view's name (Jason, 2026-10-07): one line, first initial and last name, then
    jersey number and position -- "L. Jackson #8 QB" -- so the view fits a phone with no scrolling
    (the stacked full name above takes two lines a row)."""
    first, last = split_name(r["name"])
    name = f"{first[0]}. {last}" if first else last
    num = f'#{r["jersey"]}' if r.get("jersey") is not None else ""
    return (f'<span class="ps-nm ps-nm1"><span class="ps-ln">{esc_name(name)}</span>'
            f'{f"<span class=ps-no>{num}</span>" if num else ""}'
            f'<span class="ps-pos">{esc(r["pos"])}{marks(r)}</span></span>')


# ---------------------------------------------------------------- the cards
# A section: (heading or None, who's in it, starting order, columns [(label, value)],
# {column label: stat that earns a league top-3 medal -- player_stats.MEDAL_STATS}).
#
# Tapping a column header re-sorts that table by it (P1_JS): most first, then least, then back,
# and highlights that column -- only once tapped; a table opens in its starting order with no
# column marked (Jason, 2026-09-28). Each cell carries its number in data-v for that;
# "made/attempts" cells sort by attempts, and a "—" (no value) always sorts last.
_SORT_BY = {"C/ATT": "att", "FG": "fga", "XP": "xpa"}

PASSING = (None, lambda r: r["att"] > 0, lambda r: (-r["pyds"], -r["att"]), [
    ("C/ATT", lambda r: f'{_n(r["cmp"])}/{_n(r["att"])}'), ("YDS", lambda r: _n(r["pyds"])),
    ("Y/A", lambda r: _avg(r["pyds"], r["att"])), ("TD", lambda r: _n(r["ptd"])),
    ("INT", lambda r: _n(r["int"])), ("SCK", lambda r: _n(r["sk"])), ("RTG", _rating)],
    {"YDS": "pyds", "Y/A": "ypa", "TD": "ptd"})
RUSHING = (None, lambda r: r["car"] > 0, lambda r: (-r["ryds"], -r["car"]), [
    ("ATT", lambda r: _n(r["car"])), ("YDS", lambda r: _n(r["ryds"])), ("AVG", lambda r: _avg(r["ryds"], r["car"])),
    ("TD", lambda r: _n(r["rtd"])), ("1D", lambda r: _n(r["r1d"])), ("FUM", lambda r: _n(r["rfum"]))],
    {"ATT": "car", "YDS": "ryds", "TD": "rtd"})
RECEIVING = (None, lambda r: r["tgt"] > 0 or r["rec"] > 0, lambda r: (-r["reyds"], -r["rec"]), [
    ("REC", lambda r: _n(r["rec"])), ("TGT", lambda r: _n(r["tgt"])), ("YDS", lambda r: _n(r["reyds"])),
    ("AVG", lambda r: _avg(r["reyds"], r["rec"])), ("TD", lambda r: _n(r["retd"])), ("1D", lambda r: _n(r["re1d"]))],
    {"REC": "rec", "YDS": "reyds", "TD": "retd"})
_DEF_KEYS = ("solo", "ast", "tfl", "dsk", "qbh", "dint", "pd", "ff", "fr", "dtd")
DEFENSE = (None, lambda r: any(r[k] for k in _DEF_KEYS), lambda r: (-(r["solo"] + r["ast"]), -r["dsk"]), [
    ("TKL", lambda r: _n(r["solo"] + r["ast"])), ("SOLO", lambda r: _n(r["solo"])), ("TFL", lambda r: _n(r["tfl"])),
    ("SCK", lambda r: _sacks(r["dsk"])), ("QBH", lambda r: _n(r["qbh"])), ("INT", lambda r: _n(r["dint"])),
    ("PD", lambda r: _n(r["pd"])), ("FF", lambda r: _n(r["ff"])), ("FR", lambda r: _n(r["fr"])), ("TD", lambda r: _n(r["dtd"]))],
    {"TKL": "tkl", "TFL": "tfl", "SCK": "dsk", "INT": "dint", "FF": "ff"})
KICKING = [
    ("Field Goals & PATs", lambda r: r["fga"] > 0 or r["xpa"] > 0, lambda r: (-r["fga"], -r["xpa"]), [
        ("FG", lambda r: f'{_n(r["fgm"])}/{_n(r["fga"])}'), ("PCT", lambda r: _pct(r["fgm"], r["fga"])),
        ("LNG", lambda r: _n(r["fglng"]) if r["fglng"] else DASH), ("XP", lambda r: f'{_n(r["xpm"])}/{_n(r["xpa"])}'),
        ("PTS", lambda r: _n(r["fgm"] * 3 + r["xpm"]))], {}),
    ("Punting", lambda r: r["p"] > 0, lambda r: -r["p"], [
        ("P", lambda r: _n(r["p"])), ("YDS", lambda r: _n(r["pyd"])), ("AVG", lambda r: _avg(r["pyd"], r["p"])),
        ("NET", lambda r: _avg(r["pnet"], r["p"])), ("IN20", lambda r: _n(r["p20"]))], {}),
]
RETURNS = [
    ("Kick Returns", lambda r: r["kr"] > 0, lambda r: -r["kr"], [
        ("KR", lambda r: _n(r["kr"])), ("YDS", lambda r: _n(r["kryds"])), ("AVG", lambda r: _avg(r["kryds"], r["kr"]))], {}),
    ("Punt Returns", lambda r: r["pr"] > 0, lambda r: -r["pr"], [
        ("PR", lambda r: _n(r["pr"])), ("YDS", lambda r: _n(r["pryds"])), ("AVG", lambda r: _avg(r["pryds"], r["pr"]))], {}),
]

# (card id, title, sections, layout) -- layout "stack" = both teams on the card, "switch" = one at a time
CARDS = [
    ("passing", "Passing", [PASSING], "stack"),
    ("rushing", "Rushing", [RUSHING], "switch"),
    ("receiving", "Receiving", [RECEIVING], "switch"),
    ("defense", "Defense", [DEFENSE], "switch"),
    ("kicking", "Kicking", KICKING, "stack"),
    ("returns", "Returns", RETURNS, "stack"),
]


# Each card's icon (Jason's icons, 2026-10-07), working like the team pages' TEAM_ICONS: in front
# of the card's title (expanded and condensed) and as its nav dot. Cropped to each drawing's
# bounds (measured with getBBox()). Most of the files also carried colored or black paths the
# drawing app left off the canvas -- invisible in the original, so only the paths that draw the
# icon are kept.
PS_ICONS = {
    "passing": (
        '<svg viewBox="-1633 -1673 3266 3345" fill="currentColor" aria-hidden="true">'
        '<path d="M1254.52,-208.975 C1219.11,-45.8512 1105.05,313.468 748.155,705.591 L708.545,582.897 C708.545,582.897 '
        '750.819,502.352 342.949,910.222 L341.544,712.436 C341.544,712.436 -236.684,951.859 -513.691,1180.91 '
        'L-122.244,582.897 C-122.244,582.897 -301.154,623.708 -1347.35,1360.05 C-607.23,310.079 -804.988,270.17 '
        '-804.988,270.17 L-1309.49,582.897 C-1080.44,305.89 -804.988,-299.841 -804.988,-299.841 L-1002.77,-301.245 '
        'C-594.905,-709.115 -588.783,-688.546 -588.783,-688.546 L-711.478,-728.156 C-332.348,-1073.23 -29.0797,-1211.11 '
        '114.843,-1262.04 C95.8565,-1245.2 77.3405,-1227.8 59.3513,-1209.84 C-406.387,-744.715 -505.318,60.8823 '
        '-323.5,261.53 L145.927,-207.897 C134.499,-233.728 139.338,-265.134 160.446,-286.242 L234.541,-360.337 '
        'L209.792,-385.086 C182.405,-412.473 182.405,-457.197 209.792,-484.585 C237.18,-511.972 281.904,-511.972 '
        '309.291,-484.585 L334.04,-459.836 L408.539,-534.334 L383.789,-559.083 C356.402,-586.471 356.402,-631.195 '
        '383.79,-658.582 C411.177,-685.969 455.901,-685.969 483.288,-658.582 L508.037,-633.833 L582.536,-708.331 '
        'L557.787,-733.081 C530.399,-760.468 530.4,-805.192 557.787,-832.579 C585.174,-859.967 629.898,-859.967 '
        '657.286,-832.579 L682.035,-807.83 L756.533,-882.329 L731.784,-907.078 C704.397,-934.465 704.397,-979.189 '
        '731.784,-1006.58 C759.171,-1033.96 803.896,-1033.96 831.283,-1006.58 L856.032,-981.828 L927.663,-1053.46 '
        'C948.771,-1074.57 980.177,-1079.41 1006.01,-1067.98 L1532.85,-1594.82 C1361.95,-1739.28 709.538,-1690.32 '
        '239.141,-1360.05 L164.589,-1360.05 C164.589,-1360.05 -387.216,-1178.69 -921.03,-692.824 L-798.336,-653.215 '
        'C-798.336,-653.215 -786.039,-628.095 -1193.91,-220.225 L-996.123,-218.82 C-996.123,-218.82 -1365.08,617.503 '
        '-1594.14,894.51 L-996.123,503.063 C-996.123,503.063 -891.875,621.692 -1632,1671.67 C-585.799,935.321 '
        '-406.889,894.51 -406.889,894.51 L-798.336,1492.53 C-521.329,1263.47 252.422,894.51 252.422,894.51 '
        'L253.826,1092.3 C661.696,684.426 687.43,697.921 687.43,697.921 L727.04,820.616 C1212.9,286.801 1325.23,-220.225 '
        '1325.23,-220.225 L1325.23,-301.006 C1640.9,-747.111 1691.17,-1333.19 1574.51,-1542.38 C1572.23,-1546.47 '
        '1567.48,-1554.21 1567.48,-1554.21 L1554.8,-1541.53 L1042.83,-1029.56 C1052.75,-1004.28 1047.53,-974.326 '
        '1027.16,-953.96 L955.531,-882.329 L980.28,-857.58 C1007.67,-830.192 1007.67,-785.468 980.28,-758.081 '
        'C952.892,-730.694 908.168,-730.694 880.781,-758.081 L856.032,-782.83 L781.533,-708.332 L806.282,-683.582 '
        'C833.67,-656.195 833.67,-611.471 806.282,-584.084 C778.895,-556.696 734.171,-556.696 706.784,-584.084 '
        'L682.035,-608.833 L607.536,-534.334 L632.285,-509.585 C659.672,-482.198 659.672,-437.474 632.285,-410.086 '
        'C604.898,-382.699 560.174,-382.699 532.786,-410.086 L508.037,-434.835 L433.539,-360.337 L458.288,-335.588 '
        'C485.675,-308.201 485.675,-263.476 458.288,-236.089 C430.901,-208.702 386.176,-208.702 358.789,-236.089 '
        'L334.04,-260.838 L259.945,-186.743 C239.579,-166.377 209.626,-161.156 184.345,-171.079 L-282.265,295.531 '
        'C-42.8575,446.406 709.618,343.294 1170.32,-116.796 C1199.95,-146.384 1228,-177.183 1254.52,-208.975 '
        'L1254.52,-208.975 Z"/>'
        '</svg>'
    ),
    "rushing": (
        '<svg viewBox="-1757 -1389 3582 2766" fill="currentColor" aria-hidden="true">'
        '<path d="M579.665,182.152 C559.249,160.311 537.73,136.827 516.911,115.58 C513.62,99.249 504.034,84.1989 '
        '489.016,74.4675 L408.976,22.6043 L426.3,-4.13028 C445.469,-33.7148 436.966,-73.5233 407.381,-92.6932 '
        'C377.797,-111.863 337.988,-103.359 318.818,-73.7748 L301.495,-47.0402 L221.02,-99.1858 L238.343,-125.92 '
        'C257.513,-155.505 249.009,-195.313 219.425,-214.483 C189.84,-233.653 150.032,-225.149 130.862,-195.565 '
        'L113.539,-168.83 L33.0632,-220.976 L50.3864,-247.71 C69.5562,-277.295 61.0525,-317.103 31.468,-336.273 '
        'C1.88354,-355.443 -37.925,-346.939 -57.0949,-317.355 L-74.4181,-290.62 L-154.893,-342.766 L-137.57,-369.5 '
        'C-118.4,-399.085 -126.904,-438.894 -156.489,-458.063 C-186.073,-477.233 -225.882,-468.729 -245.051,-439.145 '
        'L-262.375,-412.41 L-339.753,-462.549 C-362.554,-477.323 -391.428,-475.66 -412.247,-460.576 L-806.674,-716.153 '
        'C-788.235,-712.504 -767.123,-708.629 -742.655,-704.523 C-551.607,-672.367 89.1737,-666.325 170.067,-654.039 '
        'C286.1,-636.417 386.575,-621.154 537.306,-530.019 C588.942,-506.542 642.045,-508.01 681.544,-524.011 '
        'C990.712,-172.734 1121.97,301.044 1023.92,470.018 L579.665,182.152 Z M29.7293,-70.5273 C10.3904,-43.2828 '
        '-7.37794,-4.26527 -6.13742,38.5453 C-6.63613,49.8881 -4.51491,63.8529 1.58295,80.8921 C3.01829,85.0547 '
        '4.66991,89.2279 6.55205,93.4053 C12.5185,107.14 20.8507,122.627 32.1031,140.051 C76.4274,208.684 214.055,287.471'
        ' 271.626,357.482 C295.349,386.331 290.508,422.533 283.136,442.221 L283.136,442.221 C276.063,443.59 '
        '268.959,444.753 261.838,445.726 C156.734,439.416 64.4655,405.144 41.2992,396.341 C-68.4123,354.655 '
        '-151.287,297.195 -279.419,176.334 C-288.069,169.905 -296.43,164.451 -304.49,159.882 C-307.486,156.982 '
        '-310.542,154.061 -313.661,151.119 C-435.375,74.91 -577.11,136.233 -622.061,211.978 C-928.47,-113.749 '
        '-1061.33,-557.129 -1012.67,-759.321 L-1012.67,-759.321 C-985.37,-757.409 -966.546,-754.488 -948.758,-750.521 '
        'L-437.714,-419.38 C-441.739,-394.991 -431.397,-369.323 -409.397,-355.068 L-332.019,-304.929 L-349.342,-278.195 '
        'C-368.512,-248.61 -360.009,-208.802 -330.424,-189.632 C-300.84,-170.462 -261.031,-178.966 -241.861,-208.55 '
        'L-224.538,-235.285 L-144.063,-183.139 L-161.386,-156.404 C-180.556,-126.82 -172.052,-87.0115 -142.467,-67.8416 '
        'C-112.883,-48.6718 -73.0744,-57.1755 -53.9045,-86.76 L-36.5814,-113.495 L29.7293,-70.5273 Z M991.677,506.821 '
        'L993.685,508.122 C993.539,508.265 993.392,508.407 993.245,508.55 C992.731,507.979 992.208,507.403 '
        '991.677,506.821 L991.677,506.821 Z M534.104,-629.836 C383.374,-720.971 282.899,-736.234 166.865,-753.856 '
        'C85.9718,-766.142 -554.809,-772.183 -745.857,-804.34 C-938.543,-836.676 -923.146,-854.709 -1032.58,-860.127 '
        'C-1177.69,-867.311 -1648.04,-823.349 -1682.12,-849.781 C-1716.21,-876.212 -1798.21,-993.055 -1728.07,-1192.99 '
        'C-1712.02,-1238.73 -1520.14,-1362.29 -1286.74,-1386.55 C-1129.83,-1402.86 -723.572,-1284.27 -655.713,-1286.44 '
        'C-408.298,-1294.38 -348.875,-1316.71 -185.56,-1301.52 C-83.2166,-1274.98 -85.3336,-1230.5 -27.5493,-1203.58 '
        'C30.2348,-1176.65 203.59,-1078.89 309.501,-1041.1 C371.412,-1019.01 365.284,-967.321 423.712,-929.324 '
        'C563.726,-855.617 550.627,-854.295 656.778,-798.94 C843.66,-701.486 682.799,-562.228 534.104,-629.836 Z '
        'M-353.395,236.04 C-225.263,356.902 -142.388,414.361 -32.6769,456.048 C5.56579,470.579 232.119,554.518 '
        '393.867,467.497 C401.252,463.524 423.821,408.902 390.695,368.618 C333.124,298.608 195.497,219.82 151.172,151.187'
        ' C81.3446,43.064 123.974,9.52013 146.527,6.36992 C168.931,3.4451 317.798,74.4117 382.751,120.955 '
        'C449.374,168.695 553.294,307.295 594.224,321.048 C695.807,355.181 890.258,529.31 932,583.278 C1012.96,687.953 '
        '1053.64,730.663 1159.47,759.028 C1299.81,796.64 1740.67,843.085 1768.42,876.108 C1796.17,909.131 1870.68,1091.61'
        ' 1781.5,1283.8 C1756.56,1337.53 1544.89,1395.64 1311.62,1370.15 C1154.8,1353.02 750.301,1152.12 683.508,1139.94 '
        'C439.98,1095.55 391.77,1079.44 235.326,1030.17 C140.877,982.655 116.86,942.686 81.3066,892.324 C45.7532,841.962 '
        '-106.606,733.417 -202.17,674.15 C-258.034,639.505 -233.634,580.793 -282.739,531.333 C-404.069,429.767 '
        '-425.973,388.063 -510.615,303.399 C-548.956,265.049 -484.497,138.607 -353.395,236.04 Z"/>'
        '</svg>'
    ),
    "receiving": (
        '<svg viewBox="-1587 -1838 3155 3667" fill="currentColor" aria-hidden="true">'
        '<path d="M-1404.12,998.49 C-1387.08,1063.9 -1402.7,1351.55 -1401.68,1602.62 C-1400.67,1853.69 -939.266,1832.75 '
        '-848.452,1822.86 C-663.455,1802.7 -714.334,1761.47 -663.892,1645.5 C-663.892,1645.5 -586.151,1347.35 '
        '-570.416,1287.01 C-562.055,1254.94 -519.149,1084.69 -570.416,934.644 C-621.683,784.597 -722.256,596.124 '
        '-736.308,530.59 C-751.761,458.523 -758.463,138.039 -848.452,29.5983 C-893.216,-24.343 -924.516,-65.3211 '
        '-1022.13,28.9905 C-1119.74,123.302 -921.31,707.092 -1035.87,657.266 C-1093.58,632.164 -1107,425.243 '
        '-1142.44,238.782 C-1177.89,52.3215 -1211.69,-84.7118 -1206.89,-101.097 C-1175.29,-208.778 -1120.67,-434.01 '
        '-1087.84,-528.802 C-1022.09,-718.605 -1146.8,-958.618 -1208.19,-851.569 C-1363.64,-580.514 -1461.91,-405.438 '
        '-1481.42,-258.542 C-1501.4,-108.078 -1542.22,293.328 -1560.71,338.583 C-1658.36,577.676 -1450.11,821.933 '
        '-1404.12,998.49 Z"/><path d="M1383.91,998.49 C1366.87,1063.9 1382.49,1351.55 1381.48,1602.62 C1380.47,1853.69 '
        '919.061,1832.75 828.248,1822.86 C643.25,1802.7 694.129,1761.47 643.687,1645.5 C643.687,1645.5 565.946,1347.35 '
        '550.211,1287.01 C541.85,1254.94 498.944,1084.69 550.211,934.644 C601.478,784.597 702.051,596.124 716.103,530.59 '
        'C731.556,458.523 738.258,138.039 828.248,29.5983 C873.011,-24.343 904.311,-65.3211 1001.92,28.9905 '
        'C1099.53,123.302 901.105,707.092 1015.66,657.266 C1073.37,632.164 1086.79,425.243 1122.24,238.782 '
        'C1157.69,52.3215 1191.49,-84.7118 1186.68,-101.097 C1155.09,-208.778 1100.47,-434.01 1067.63,-528.802 '
        'C1001.89,-718.605 1126.59,-958.618 1187.99,-851.569 C1343.44,-580.514 1441.71,-405.438 1461.21,-258.542 '
        'C1481.19,-108.078 1522.02,293.328 1540.5,338.583 C1638.15,577.676 1429.91,821.933 1383.91,998.49 Z"/><path '
        'd="M9.74552,-1836.51 L9.74553,-1158.2 C36.6645,-1147.8 55.8584,-1121.61 55.8584,-1091.11 L55.8584,-984.046 '
        'L91.6198,-984.046 C131.193,-984.046 163.506,-951.733 163.506,-912.16 C163.506,-872.586 131.193,-840.274 '
        '91.6198,-840.274 L55.8584,-840.274 L55.8584,-840.274 L55.8584,-732.626 L91.6198,-732.626 C131.193,-732.626 '
        '163.506,-700.314 163.506,-660.74 C163.506,-621.167 131.193,-588.854 91.6198,-588.854 L55.8584,-588.854 '
        'L55.8584,-481.207 L91.6198,-481.207 C131.193,-481.207 163.506,-448.894 163.506,-409.321 C163.506,-369.747 '
        '131.193,-337.435 91.6198,-337.435 L55.8584,-337.435 L55.8584,-229.787 L91.6198,-229.787 C131.193,-229.787 '
        '163.506,-197.475 163.506,-157.901 C163.506,-118.327 131.193,-86.0151 91.6198,-86.0151 L55.8583,-86.0151 '
        'L55.8583,17.4893 C55.8583,47.9894 36.6645,74.1763 9.74556,84.5813 L9.74558,845.854 C268.514,824.154 '
        '795.733,173.513 796.177,-496.87 C796.623,-1169.4 286.07,-1822.9 9.74552,-1836.51 L9.74552,-1836.51 Z '
        'M-44.6109,-1831.28 C-326.583,-1767.32 -795.736,-1149.17 -796.177,-483.918 C-796.611,169.383 -327.908,761.483 '
        '-58.244,838.059 C-53.6405,839.366 -44.6108,841.528 -44.6108,841.528 L-44.6108,823.204 L-44.6109,83.4258 '
        'C-70.0456,72.3297 -87.9136,46.9172 -87.9136,17.4893 L-87.9136,-86.0151 L-123.675,-86.0151 C-163.249,-86.0151 '
        '-195.561,-118.327 -195.561,-157.901 C-195.561,-197.475 -163.249,-229.787 -123.675,-229.787 L-87.9136,-229.787 '
        'L-87.9136,-229.787 L-87.9136,-337.435 L-123.675,-337.435 C-163.249,-337.435 -195.561,-369.747 -195.561,-409.321 '
        'C-195.561,-448.894 -163.249,-481.207 -123.675,-481.207 L-87.9136,-481.207 L-87.9136,-481.207 L-87.9136,-588.854 '
        'L-123.675,-588.854 C-163.249,-588.854 -195.561,-621.167 -195.561,-660.74 C-195.561,-700.314 -163.249,-732.626 '
        '-123.675,-732.626 L-87.9136,-732.626 L-87.9136,-732.626 L-87.9136,-840.274 L-123.675,-840.274 C-163.249,-840.274'
        ' -195.561,-872.586 -195.561,-912.16 C-195.561,-951.733 -163.249,-984.046 -123.675,-984.046 L-87.9136,-984.046 '
        'L-87.9136,-1091.11 C-87.9136,-1120.54 -70.0456,-1145.95 -44.6109,-1157.05 L-44.6109,-1831.28 L-44.6109,-1831.28 '
        'Z"/>'
        '</svg>'
    ),
    "defense": (
        '<svg viewBox="-1999 -1737 3999 3474" fill="currentColor" aria-hidden="true">'
        '<path d="M467.599,837.014 L1412.49,1416.42 L827.291,535.95 L1796.18,763.168 L1202.97,121.276 L1998.29,-230.912 '
        'L943.191,-344.521 L1614.62,-906.886 L827.291,-844.401 L935.198,-1690.79 L239.794,-929.608 L-59.9486,-1736.23 '
        'L-239.794,-929.608 L-935.198,-1696.47 L-803.311,-850.081 L-1654.58,-1094.34 L-939.194,-344.521 '
        'L-1998.29,-242.273 L-999.143,104.235 L-1550.67,763.168 L-827.291,530.269 L-1196.13,1416.42 L-467.599,831.333 '
        'L-435.626,1416.42 L0,944.942 L467.599,1736.23 L467.599,837.014 Z M-675.066,-724.399 C-528.072,-857.599 '
        '62.1098,-785.123 402.858,-443.922 C742.518,-103.811 805.094,493.368 684.899,635.566 L298.932,249.599 '
        'C307.304,230.675 303.759,207.667 288.295,192.203 L235.818,139.726 L253.949,121.595 C274.013,101.531 '
        '274.013,68.7663 253.949,48.7023 C233.885,28.6384 201.12,28.6384 181.057,48.7023 L162.925,66.8335 '
        'L108.348,12.2558 L126.479,-5.87534 C146.543,-25.9393 146.543,-58.7043 126.479,-78.7682 C106.415,-98.8321 '
        '73.65,-98.8321 53.586,-78.7682 L35.4548,-60.637 L-19.1228,-115.215 L-0.991652,-133.346 C19.0723,-153.41 '
        '19.0723,-186.175 -0.991657,-206.239 C-21.0556,-226.303 -53.8205,-226.303 -73.8845,-206.239 L-92.0157,-188.108 '
        'L-146.593,-242.685 L-128.462,-260.816 C-108.398,-280.88 -108.398,-313.645 -128.462,-333.709 C-148.526,-353.773 '
        '-181.291,-353.773 -201.355,-333.709 L-219.486,-315.578 L-273.768,-369.86 C-289.232,-385.324 -312.24,-388.869 '
        '-331.164,-380.497 L-675.066,-724.399 Z M-699.975,-694.191 L-358.137,-352.352 C-365.406,-333.831 '
        '-361.581,-311.887 -346.661,-296.967 L-292.379,-242.685 L-310.51,-224.554 C-330.574,-204.49 -330.574,-171.725 '
        '-310.51,-151.661 C-290.446,-131.597 -257.681,-131.597 -237.617,-151.661 L-219.486,-169.792 L-164.909,-115.215 '
        'L-183.04,-97.0835 C-203.104,-77.0196 -203.104,-44.2546 -183.04,-24.1907 C-162.976,-4.12671 -130.211,-4.12674 '
        '-110.147,-24.1907 L-92.0157,-42.3218 L-37.438,12.2558 L-55.5692,30.387 C-75.6331,50.451 -75.6331,83.2159 '
        '-55.5692,103.28 C-35.5052,123.344 -2.74027,123.344 17.3237,103.28 L35.4548,85.1487 L90.0325,139.726 '
        'L71.9013,157.858 C51.8374,177.921 51.8374,210.686 71.9013,230.75 C91.9653,250.814 124.73,250.814 144.794,230.75 '
        'L162.925,212.619 L215.402,265.096 C230.322,280.016 252.266,283.841 270.787,276.572 L645.857,651.642 '
        'L655.147,660.932 C655.147,660.932 649.473,664.414 646.476,666.085 C470.932,763.981 -66.8985,701.419 '
        '-397.905,369.973 C-734.967,32.4634 -810.506,-518.801 -699.975,-694.191 Z"/>'
        '</svg>'
    ),
    "kicking": (
        '<svg viewBox="-1947 -1547 3794 3095" fill="currentColor" aria-hidden="true">'
        '<path d="M-1236.48,601.741 C-1228.25,637.066 -1155.66,769.761 -1143.52,762.752 C-1103.4,739.589 -1005.84,719.808'
        ' -965.547,789.6 C-956.828,804.702 -946.5,889.848 -1021.79,933.316 C-1039.55,943.57 -922.351,1097.92 '
        '-911.02,1091.38 C-851.186,1056.83 -769.285,1049.75 -731.583,1095.2 C-693.882,1140.64 -722.823,1233.59 '
        '-760.993,1282.04 C-772.725,1296.92 -647.399,1435.08 -631.046,1425.64 C-509.048,1355.2 -453.742,1399.9 '
        '-437.127,1409.73 C-403.369,1431.94 -379.707,1456.98 -284.878,1509.9 C-80.5749,1611.43 34.4148,1492.69 '
        '-9.1747,1250.16 C-108.481,848.196 -95.9638,935.814 -175.276,585.242 C-275.078,-79.9956 -266.858,-322.733 '
        '-265.257,-505.129 C-278.683,-554.012 -204.549,-695.009 -330.862,-743.989 C-668.451,-803.832 -856.378,-861.971 '
        '-992.732,-1000.64 C-1196.73,-1198.2 -733.555,-1535.01 -984.7,-1535.31 C-1199.25,-1593.53 -1885.64,-1421.31 '
        '-1853.15,-989.949 C-1859.13,-957.385 -1842.08,-912.511 -1946.27,-816.086 C-1915.12,-745.002 -1915.22,-728.83 '
        '-1865.82,-643.265 C-1668,-688.105 -1674.67,-567.701 -1769.5,-438.974 C-1742.99,-374.669 -1717.49,-327.322 '
        '-1680.01,-283.973 C-1539.03,-338.645 -1501.06,-289.718 -1486.24,-267.578 C-1384.44,-91.2498 -1224.9,206.514 '
        '-1154.17,437.915 C-1176.34,502.032 -1165.43,549.376 -1236.48,601.741 Z M-1130.64,600.329 C-1052.69,545.708 '
        '-1052.8,450.504 -1073.29,381.582 C-1144.02,150.181 -1303.55,-147.583 -1405.36,-323.911 C-1420.18,-346.051 '
        '-1485.71,-436.113 -1626.69,-381.441 C-1664.17,-424.79 -1646.53,-397.421 -1673.04,-461.727 C-1578.21,-590.454 '
        '-1595.43,-772.344 -1793.26,-727.504 C-1808.58,-761.246 -1817.26,-780.35 -1829.66,-807.655 C-1725.47,-904.08 '
        '-1742.53,-948.953 -1736.54,-981.518 C-1721.83,-1260.66 -1441.23,-1390.8 -1123.64,-1428.89 C-991.455,-1442.18 '
        '-1301.37,-1124.4 -1097.37,-926.836 C-961.013,-788.169 -807.411,-704.276 -469.822,-644.433 C-343.509,-595.453 '
        '-417.643,-454.456 -404.217,-405.573 C-405.818,-223.178 -407.31,-138.552 -307.508,526.686 C-228.195,877.258 '
        '-218.465,846.4 -119.159,1248.37 C-89.2385,1413.82 -146.951,1446.46 -259.638,1390.26 C-354.468,1337.33 '
        '-405.963,1286.86 -439.72,1264.64 C-456.336,1254.82 -483.664,1241.94 -605.662,1312.38 C-622.015,1321.82 '
        '-655.314,1278.68 -643.582,1263.79 C-605.412,1215.35 -605.991,1085.61 -643.693,1040.17 C-681.394,994.723 '
        '-798.276,960.861 -858.11,995.406 C-869.441,1001.95 -910.706,919.7 -904.041,915.852 C-828.752,872.384 '
        '-863.823,744.381 -872.542,729.279 C-912.837,659.487 -1048.93,655.166 -1094.64,662.676 C-1098.54,663.316 '
        '-1122.41,635.654 -1130.64,600.329 Z"/><path d="M455.753,1429.73 L672.19,678.245 C645.687,658.128 632.778,622.991'
        ' 642.51,589.2 L676.673,470.584 L637.053,459.174 C593.21,446.546 567.722,400.437 580.349,356.594 C592.977,312.751'
        ' 639.086,287.263 682.929,299.89 L722.549,311.301 L722.549,311.301 L756.897,192.039 L717.278,180.628 '
        'C673.434,168.001 647.946,121.892 660.574,78.0487 C673.201,34.2055 719.31,8.71732 763.153,21.3447 '
        'L802.773,32.7556 L837.122,-86.5061 L797.502,-97.9171 C753.659,-110.544 728.17,-156.653 740.798,-200.497 '
        'C753.425,-244.34 799.534,-269.828 843.377,-257.201 L882.997,-245.79 L917.346,-365.051 L877.726,-376.462 '
        'C833.883,-389.09 808.395,-435.199 821.022,-479.042 C833.649,-522.885 879.758,-548.373 923.602,-535.746 '
        'L963.221,-524.335 L996.248,-639.006 C1005.98,-672.797 1035.6,-695.685 1068.74,-698.623 L1311.65,-1542.03 '
        'C1018.04,-1600.56 226.333,-1047.95 11.9315,-305.378 C-203.157,439.567 153.957,1326.49 455.753,1429.73 '
        'L455.753,1429.73 Z M517.642,1441.29 C850.445,1460.4 1567.46,925.258 1780.22,188.37 C1989.16,-535.278 '
        '1658.82,-1340.82 1384.49,-1511.7 C1379.81,-1514.62 1370.5,-1519.89 1370.5,-1519.89 L1364.65,-1499.59 '
        'L1128.6,-679.999 C1153.23,-659.59 1164.92,-625.734 1155.53,-593.131 L1122.5,-478.459 L1162.12,-467.048 '
        'C1205.97,-454.421 1231.46,-408.312 1218.83,-364.469 C1206.2,-320.626 1160.09,-295.138 1116.25,-307.765 '
        'L1076.63,-319.176 L1076.63,-319.176 L1042.28,-199.914 L1081.9,-188.503 C1125.74,-175.876 1151.23,-129.767 '
        '1138.6,-85.9237 C1125.98,-42.0804 1079.87,-16.5923 1036.02,-29.2196 L996.405,-40.6306 L996.405,-40.6306 '
        'L962.056,78.6311 L1001.68,90.0421 C1045.52,102.669 1071.01,148.778 1058.38,192.622 C1045.75,236.465 '
        '999.644,261.953 955.801,249.326 L916.181,237.915 L916.181,237.915 L881.832,357.176 L921.452,368.587 '
        'C965.295,381.215 990.783,427.324 978.156,471.167 C965.529,515.01 919.42,540.498 875.576,527.871 L835.957,516.46 '
        'L801.794,635.076 C792.404,667.679 764.499,690.132 732.78,694.309 L517.642,1441.29 L517.642,1441.29 Z"/>'
        '</svg>'
    ),
    "returns": (
        '<svg viewBox="-1840 -1859 3664 3669" fill="currentColor" aria-hidden="true">'
        '<path d="M1136.88,683.309 C1140.16,663.273 1202.56,597.671 1186.38,555.716 C1167.56,506.914 1106.3,517.496 '
        '1058.86,513.771 L1012.44,409.985 C1058.49,379.926 1076.35,340.596 1052.06,285.659 C1023.84,227.712 '
        '974.502,226.621 918.122,232.969 L857.82,104.645 C904.093,73.5638 925.654,38.5664 908.165,-16.9784 '
        'C887.821,-72.2314 825.798,-90.6267 770.264,-85.4459 L687.076,-260.691 C736.201,-287.354 753.646,-325.014 '
        '726.459,-375.389 C695.572,-428.808 649.543,-432.991 590.101,-428.408 C565.371,-481.033 530.875,-532.607 '
        '518.324,-581.148 C480.022,-646.54 528.458,-1104.84 327.11,-1126.7 C-183.524,-1082.49 -332.447,-872.639 '
        '-582.996,-1020.12 C-954.012,-1226.47 -464.025,-1946.28 -826.795,-1849.54 C-1169.94,-1753.01 -2018.44,-1370.54 '
        '-1804.61,-760.226 C-1800.65,-710.886 -1716.85,-617.247 -1830,-437.696 C-1807.18,-333.033 -1785.38,-297.415 '
        '-1680.94,-192.973 C-1412.63,-334.264 -1400.2,-131.101 -1487.33,91.4738 C-1424.17,174.073 -1369.03,232.576 '
        '-1298.14,280.671 C-1115.71,147.176 -1011.46,153.158 -981.482,179.393 C-823.434,426.88 -476.747,806.758 '
        '-155.725,1010.84 C-68.2034,1081.27 -38.1678,1245.45 -120.51,1348.56 C-94.9501,1396.38 77.6947,1552.89 '
        '92.5129,1538.08 C141.485,1489.1 235.22,1358.78 333.012,1422.89 C354.814,1437.18 372.794,1560.08 352.664,1682.92 '
        'C347.705,1713.17 549.607,1750.23 563.437,1736.4 C636.472,1663.36 681.482,1539.36 765.7,1553.16 C849.918,1566.96 '
        '900.72,1703.96 918.122,1788.61 C923.828,1816.37 1123.44,1813.43 1136.88,1788.61 C1214.83,1644.68 1206.29,1612.06'
        ' 1234.83,1607.75 C1296.08,1598.49 1473.56,1602.25 1614.02,1553.16 C1924.12,1444.77 1901.08,1103.79 '
        '1471.14,926.684 C1418.43,904.973 1128.34,735.434 1136.88,683.309 Z M-661.399,285.659 L-972.644,-67.4073 '
        'L356.925,-516.926 L563.437,-134.157 L-661.399,285.659 Z M-1704.88,-1013.78 C-1670.46,-1249.34 -1321.08,-1493.36 '
        '-1292.91,-1500.79 C-1192.32,-1527.33 -1191.49,-1474.69 -1214.91,-1384.61 C-1296.88,-1069.28 -1327.33,-951.853 '
        '-1287.08,-536.332 C-1277.01,-432.298 -1367.02,-494.344 -1435.53,-565.937 L-1556.42,-692.263 C-1642.59,-783.403 '
        '-1723.88,-883.737 -1704.88,-1013.78 Z M1340.25,1000.13 C1640.65,1194.28 1729.39,1348.28 1486.15,1418.76 '
        'C1375.97,1450.68 1142.14,1457.32 1092.93,1457.32 C1070.68,1457.32 904.844,1436.79 736.961,1388.96 '
        'C659.243,1355.89 533.436,1327.63 394.71,1243.33 C316.244,1195.65 152.484,1079.14 33.8403,989.169 '
        'C-166.306,846.126 -396.999,769.539 574.506,989.169 C711.547,1020.15 1007.19,960.37 1092.93,897.934 '
        'C1115.13,881.769 1119.12,857.216 1340.25,1000.13 Z"/>'
        '</svg>'
    ),
}


# ---------------------------------------------------------------- markup

def _title(cid, name):
    """A card's title: its icon (PS_ICONS) in front of its name, like the team pages' own _title."""
    icon = PS_ICONS.get(cid)
    return f'<span class="ttl">{f"<span class=t-ic>{icon}</span>" if icon else ""}{esc(name)}</span>'


def _pill(team):
    return helmets.pill_html(team)


def _sort_value(label, shown, r):
    """The number a column sorts by, or None for a "—"."""
    if label in _SORT_BY:
        return r[_SORT_BY[label]]
    try:
        return float(shown.replace(",", ""))
    except ValueError:
        return None


PLACES = {1: "1st", 2: "2nd", 3: "3rd"}


def _cell(label, f, r, medal_stat):
    shown = f(r)
    v = _sort_value(label, shown, r)
    place = (r.get("medals") or {}).get(medal_stat) if medal_stat else None
    inner = (f'<span class="ps-md ps-md{place}" title="{PLACES[place]} in the NFL">{esc(shown)}</span>'
             if place else esc(shown))
    return f'<td data-v="{v:g}">{inner}</td>' if v is not None else f"<td>{inner}</td>"


def _table(rows, cols, empty, medals, sortable=True, corner=None, name=name_html):
    """corner: a section heading to sit in the header row's empty top-left cell, over the names.
    name: how a player's name is written (short_name_html in the condensed view)."""
    if not rows:
        return f'<p class="ps-empty">{esc(empty)}</p>'
    head = "".join(
        f'<th scope="col" aria-sort="none"><button type="button" class="ps-sort">{esc(label)}</button></th>' if sortable
        else f'<th scope="col"><span class="ps-lbl">{esc(label)}</span></th>'
        for label, _f in cols)
    body = "".join(
        f'<tr data-i="{i}"><th scope="row">{name(r)}</th>'
        + "".join(_cell(label, f, r, medals.get(label)) for label, f in cols) + "</tr>"
        for i, r in enumerate(rows))
    first = f'<span class="ps-corner">{esc(corner)}</span>' if corner else '<span class="vh">Player</span>'
    return (f'<div class="ps-tw"><table class="ps-t"><thead><tr><th scope="col">{first}</th>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


# Kicking's and Returns' section headings sit in each table's top-left corner, not on a line of
# their own (Jason, 2026-10-07): with one kicker and one punter a team, Kicking then fits a phone
# with no scrolling. A short name there, the corner being only as wide as the player names.
CORNER_CARDS = {"kicking", "returns"}
CORNER_LABELS = {"Field Goals & PATs": "Kicking", "Kick Returns": "Kickoffs", "Punt Returns": "Punts"}


def _layout(cid, sections, layout, stats):
    """Returns stacks both teams only while each has at most one kick returner and one punt
    returner; any more and it takes the team switch like Rushing / Receiving (Jason, 2026-10-07)."""
    if cid == "returns" and any(sum(1 for r in players if keep(r)) > 1
                                for players in stats.values() for _h, keep, *_ in sections):
        return "switch"
    return layout


def _team_tables(players, sections, empty, corner=False):
    out = []
    for heading, keep, order, cols, medals in sections:
        rows = sorted((r for r in players if keep(r)), key=order)
        if heading and corner and rows:
            out.append(_table(rows, cols, empty, medals, corner=CORNER_LABELS.get(heading, heading)))
            continue
        if heading:
            out.append(f'<h3 class="ps-sec">{esc(heading)}</h3>')
        out.append(_table(rows, cols, empty, medals))
    return "".join(out)


SCOPE_LABELS = {"game": "Game Stats", "season": "Season Stats"}


def _scope_label(scope, extra=""):
    """Which numbers the page is showing (Jason, 2026-09-29): this game's, or the season's."""
    return f'<span class="ps-scope{extra}">{esc(SCOPE_LABELS.get(scope, SCOPE_LABELS["season"]))}</span>'


def _empty_text(stats, scope):
    """What a card says for a team with nobody in it. scope: "game" on a finished game, else "season"."""
    if scope == "game":
        return "None this game"
    # before either team has played (Week 1), say so rather than "None this season" everywhere
    return "None this season" if any(stats.values()) else "No games played yet"


def card_body(sections, layout, teams, stats, scope="season", corner=False):
    """teams = (away, home) abbreviations; stats = {abbr: [player totals]}."""
    empty = _empty_text(stats, scope)
    if layout == "stack":
        blocks = "".join(
            f'<div class="ps-team"><div class="ps-th">{_pill(t)}</div>'
            f"{_team_tables(stats.get(t) or [], sections, empty, corner)}</div>" for t in teams)
        return f'<div class="ps-scroll">{blocks}</div>'
    tabs = "".join(
        f'<button type="button" class="ps-tab{" on" if i == 0 else ""}" data-team="{esc(t)}" aria-pressed="{"true" if i == 0 else "false"}">'
        f'{_pill(t)}</button>' for i, t in enumerate(teams))
    panes = "".join(
        f'<div class="ps-pane{" on" if i == 0 else ""}" data-team="{esc(t)}">{_team_tables(stats.get(t) or [], sections, empty, corner)}</div>'
        for i, t in enumerate(teams))
    return f'<div class="ps-sw">{tabs}</div><div class="ps-scroll">{panes}</div>'


# ---------------------------------------------------------------- condensed view
# Everything on one screen (Jason, 2026-09-28), one team at a time behind a single switch at the
# top. Passing, Rushing, Receiving and Defense are full-width cards, one per row, each a small
# version of the expanded card's table (the same columns, top-3 bars included) holding just the
# team's top players; Kicking and Returns sit side by side, the one player's every stat as a
# wrap of number-over-label pairs. Tapping a card opens it expanded; headers don't sort here.

def _top(players, keep, order, n):
    return sorted((r for r in players if keep(r)), key=order)[:n]


def _leaders(players, picks):
    """One row per pick (the top player by each), a player listed once even if he leads twice."""
    out = []
    for keep, order in picks:
        for r in _top(players, keep, order, 1):
            if r not in out:
                out.append(r)
    return out


_TKL = (lambda r: r["solo"] + r["ast"] > 0, lambda r: -(r["solo"] + r["ast"]))
_SCK = (lambda r: r["dsk"] > 0, lambda r: -r["dsk"])
_INT = (lambda r: r["dint"] > 0, lambda r: -r["dint"])

# (card id, title, section whose columns it shows, who: players -> rows, width, columns left out here)
# Defense drops SOLO / QBH / PD / FR and Kicking drops PTS in this view (Jason, 2026-09-28).
CONDENSED = [
    ("passing", "Passing", PASSING, lambda ps: _top(ps, PASSING[1], lambda r: -r["pyds"], 1), "row", ()),
    ("rushing", "Rushing", RUSHING, lambda ps: _top(ps, RUSHING[1], lambda r: -r["ryds"], 2), "row", ()),
    ("receiving", "Receiving", RECEIVING, lambda ps: _top(ps, RECEIVING[1], lambda r: -r["reyds"], 3), "row", ()),
    ("defense", "Defense", DEFENSE, lambda ps: _leaders(ps, (_TKL, _SCK, _INT)), "row", ("SOLO", "QBH", "PD", "FR")),
    ("kicking", "Kicking", KICKING[0], lambda ps: _top(ps, lambda r: r["fga"] > 0, lambda r: (-r["fga"], -r["fgm"]), 1), "half", ("PTS",)),
    ("returns", "Punt Returns", RETURNS[1], lambda ps: _top(ps, RETURNS[1][1], lambda r: (-r["pryds"], -r["pr"]), 1), "half", ()),
]


def _pairs(rows, cols, empty):
    """A half-width card: the player's name, then every stat as number over label."""
    if not rows:
        return f'<p class="ps-empty">{esc(empty)}</p>'
    r = rows[0]
    stats = "".join(f'<span class="pc-st"><b>{esc(f(r))}</b><small>{esc(label)}</small></span>' for label, f in cols)
    return f'<div class="pc-who">{short_name_html(r)}</div><div class="pc-sts">{stats}</div>'


def condensed_view(teams, stats, scope="season"):
    empty = _empty_text(stats, scope)
    tabs = "".join(
        f'<button type="button" class="ps-tab{" on" if i == 0 else ""}" data-team="{esc(t)}" aria-pressed="{"true" if i == 0 else "false"}">'
        f'{_pill(t)}</button>' for i, t in enumerate(teams))
    cards = []
    for cid, title, section, who, width, left_out in CONDENSED:
        _h, _keep, _order, cols, medals = section
        cols = [c for c in cols if c[0] not in left_out]
        panes = "".join(
            f'<div class="pc-p{" on" if i == 0 else ""}" data-team="{esc(t)}">'
            + (_table(who(stats.get(t) or []), cols, empty, medals, sortable=False, name=short_name_html) if width == "row"
               else _pairs(who(stats.get(t) or []), cols, empty))
            + "</div>"
            for i, t in enumerate(teams))
        cards.append(f'<a class="card cc pc-{cid} pc-{width}" tabindex="0" aria-label="{esc(title)}">'
                     f'<span class="card-title">{_title(cid, title)}</span>{panes}</a>')
    return (f'<div class="p2-view p2-c pc"><div class="ps-sw pc-sw">{tabs}</div>{_scope_label(scope, " pc-scope")}'
            f'{"".join(cards)}</div>')


def render_players_block(d):
    """The hidden .p2 layer for this game's Player Stats; "" if there's no player data at all."""
    ps = d.get("player_stats")
    if not isinstance(ps, dict):
        return ""
    away, home = (d.get("away") or {}).get("team"), (d.get("home") or {}).get("team")
    if not (away and home):
        return ""
    from render_page1 import UP, DOWN
    stats = {away: ps.get("away") or [], home: ps.get("home") or []}
    scope = ps.get("scope") or "season"
    slots = "".join(
        f'<section class="slot"><a class="card p2k p2k-ps p2k-{cid}" tabindex="-1" aria-label="{esc(title)}">'
        f'<span class="peek peek-top">{DOWN}{_title(cid, title)}</span>'
        f'<div class="body">{_scope_label(scope)}{card_body(sections, _layout(cid, sections, layout, stats), (away, home), stats, scope, cid in CORNER_CARDS)}</div>'
        f'<span class="peek peek-bot">{UP}{_title(cid, title)}</span></a></section>'
        for cid, title, sections, layout in CARDS)
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(title)}">{PS_ICONS.get(cid, "")}</button>'
                   for cid, title, _s, _l in CARDS)
    return ('<div class="p2 p2-ps" data-page="leaders" aria-label="Player stats" role="region">'
            f'<div class="p2-view p2-l deck">{slots}</div><nav class="dots p2-dots ic-dots" aria-label="Cards">{dots}</nav>'
            f'{condensed_view((away, home), stats, scope)}</div>')


# ---------------------------------------------------------------- styles
# Appended to Page 1's stylesheet (same <style id="p1-css">), like P2_CSS / P3_CSS.

P4_CSS = r"""
/* ===== Page 2: Player Stats (2026-09-28) -- the Leaders card's deep dive =====
   Reuses the .p2 shell and deck; expanded view only, like the team pages. */
.p1[data-detail="leaders"] .p2[data-page="leaders"]{display:block}
/* The card title sits at the top; the stats fill the rest and scroll inside the card when
   they don't fit (a team's Defense runs 25-40 players). */
.p2 .slot .p2k-ps .body{padding:44px 14px 14px;justify-content:flex-start;gap:12px;min-height:0}
.ps-scroll{flex:1;min-height:0;overflow-y:auto;-webkit-overflow-scrolling:touch;margin:0 -14px;padding:0 14px 6px}
/* Team switch (Rushing, Receiving, Defense, and Returns when it's long): the two teams' pills,
   the chosen one at full strength and the other faded. Just the pills -- no outlined pill around
   each one (Jason, 2026-10-07). */
.ps-sw{display:flex;justify-content:center;gap:12px;flex:none}
.ps-tab{display:flex;align-items:center;border:0;background:none;color:var(--text);
  border-radius:999px;padding:0;font:inherit;cursor:pointer}
.ps-tab .tpill{height:26px;min-width:68px;font-size:15px}
.ps-tab:not(.on){opacity:.55}
.ps-pane{display:none}
.ps-pane.on{display:block}
/* Both teams stacked (Passing, Kicking, and Returns while each team has one returner of each
   kind): each under its pill + abbreviation */
.ps-team+.ps-team{margin-top:18px}
.ps-th{display:flex;align-items:center;gap:8px;padding:2px 0 4px}
.ps-th .tpill{height:26px;min-width:68px;font-size:15px}
.ps-sec{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2);margin:12px 0 2px}
.ps-th+.ps-sec,.ps-pane>.ps-sec:first-child{margin-top:4px}
.ps-empty{font-size:13px;color:var(--text-2);padding:6px 0}
/* Kicking and Returns (2026-10-07): each section's name in its table's top-left corner, styled
   like the column headers beside it, and everything a little closer together -- one kicker and
   one punter a team fit a phone screen with no scrolling (more than that can still scroll) */
.ps-corner{display:block;text-align:left;font-size:11px;letter-spacing:.06em;text-transform:uppercase;padding:4px 0}
:is(.p2k-kicking,.p2k-returns) .ps-team+.ps-team{margin-top:12px}
:is(.p2k-kicking,.p2k-returns) .ps-th{padding:0 0 2px}
:is(.p2k-kicking,.p2k-returns) :is(.ps-tw+.ps-tw,.ps-tw+.ps-sec,.ps-empty+.ps-tw){margin-top:6px}
:is(.p2k-kicking,.p2k-returns) .ps-t :is(td,tbody th){padding-top:4px;padding-bottom:4px}
@media (max-height:600px){   /* iPhone SE (1st gen)-short screens */
  :is(.p2k-kicking,.p2k-returns) .ps-team+.ps-team{margin-top:8px}
  :is(.p2k-kicking,.p2k-returns) .ps-t :is(td,tbody th){padding-top:2px;padding-bottom:2px}
  :is(.p2k-kicking,.p2k-returns) .ps-corner{padding:2px 0}
}
/* Condensed view: the team switch across the top, then Passing / Rushing / Receiving / Defense
   one per row and Kicking + Punt Returns side by side; rows share the height by how many players
   each holds, but never get shorter than their contents. It all fits a phone with no scrolling
   (Jason, 2026-10-07): one-line names (short_name_html), 6px between cards and tighter rows --
   down to an iPhone SE (1st gen) with the steps below. It can still scroll as a last resort (a
   phone on its side), and P1_JS's detailAtTop keeps a pull-down from closing the page until it's
   back at the top. Each card shows the chosen team's pane (.pc-p.on). */
.p2-c.pc{grid-template-columns:1fr 1fr;overflow-y:auto;-webkit-overflow-scrolling:touch;row-gap:6px;
  grid-template-rows:auto auto minmax(min-content,1.1fr) minmax(min-content,1.5fr) minmax(min-content,2fr)
    minmax(min-content,2fr) minmax(min-content,1.2fr)}
.pc-sw{grid-column:1/-1}
/* "Season Stats" / "Game Stats": small type under each expanded card's title, and one line under
   the condensed view's team switch (Jason, 2026-09-29). Its pill outline moved to the cards' own
   titles (Jason, 2026-10-03; .ttl in render_page1.P1_CSS, shared with every page's titles). */
.ps-scope{align-self:center;flex:none;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:var(--text-2);padding:3px 9px;line-height:1.1;white-space:nowrap}
.p2 .slot .p2k-ps .body>.ps-scope{margin-top:-14px}
.pc-scope{grid-column:1/-1;justify-self:center;margin:-4px 0 -2px}
.p2-c.pc a.card.cc{justify-content:flex-start;padding:var(--ctitle) 12px 4px;gap:0}
.p2-c.pc a.card.pc-row{grid-column:1/-1}
/* "safe": if a pane ever overflows, it's the bottom that's cut, never the player's name */
.pc-p{display:none;flex-direction:column;justify-content:safe center;flex:1;min-height:0}
.pc-p.on{display:flex}
.pc .ps-tw{margin:0 -12px;padding:0 12px}
/* a little tighter than the expanded tables, so Defense's ten columns need less sideways scrolling */
.pc .ps-t{font-size:11.5px}
.pc .ps-t td{padding:2px}
.pc .ps-t tbody th{padding:2px 4px 2px 0}
.pc .ps-t thead th{padding:0 3px;font-size:9px}
.ps-nm.ps-nm1{display:inline-flex;align-items:baseline;gap:4px;white-space:nowrap}
.ps-lbl{display:block}
.pc-who{margin-bottom:2px}
/* a name too long for its line ("K. Abrams-Draine #31 CB", "R. Spears-Jennings #28 SAF · R")
   takes its number and position down to a second line rather than running past the card */
.pc .ps-nm.ps-nm1{flex-wrap:wrap;column-gap:4px;row-gap:0;white-space:normal}
.pc .ps-nm1>*{white-space:nowrap}
.pc-who .ps-nm.ps-nm1{display:flex}
.pc-who .ps-nm{font-weight:700}
/* Kicking / Punt Returns: the stats always on one line (Jason, 2026-09-28), spread across the card */
.pc-sts{display:flex;flex-wrap:nowrap;justify-content:space-between;gap:6px}
.pc-st{display:flex;flex-direction:column;line-height:1.1;white-space:nowrap}
.pc-st b{font-size:14px;font-variant-numeric:tabular-nums}
@media (max-width:370px){.pc-st b{font-size:13px}.pc .ps-t{font-size:11px}.pc .ps-t td{padding:2px}.pc .ps-t tbody th{padding-right:3px}}
/* iPhone SE (1st gen)-small: 4px between cards, rows and stats a step smaller, and the narrowest
   type for the widest table (Passing's seven columns) */
@media (max-height:600px){
  .p2-c.pc{row-gap:4px}
  .pc .ps-t td,.pc .ps-t tbody th{padding-top:1px;padding-bottom:1px}
  .pc-scope{margin:-4px 0 -4px}
  .pc-st b{font-size:12px}
}
@media (max-width:370px){.pc .ps-no{display:none}}   /* no jersey number, so a long name still leaves Passing room */
@media (max-width:340px){.pc .ps-t,.pc .ps-nm{font-size:10px}.pc .ps-t thead th{font-size:8px}.pc .ps-t td{padding:1px 1.5px}
  .pc-sts{gap:3px}.pc-st b{font-size:12px}}
.pc-st small{font-size:9px;font-weight:700;letter-spacing:.05em;color:var(--text-2)}
.pc .ps-empty{padding:0;font-size:12px}
/* The table: player column pinned on the left; a table wider than the card scrolls sideways,
   and fades out at the right edge while there's more to see (.more, set by P1_JS) */
.ps-tw{overflow-x:auto;margin:0 -14px;padding:0 14px}
.ps-tw.more{-webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 36px),transparent);mask-image:linear-gradient(90deg,#000 calc(100% - 36px),transparent)}
.ps-t{border-collapse:separate;border-spacing:0;width:100%;font-size:12px;font-variant-numeric:tabular-nums}
.ps-t thead th{font-size:10px;font-weight:700;letter-spacing:.05em;color:var(--text-2);text-align:right;padding:0;white-space:nowrap}
/* Column headers are sort buttons (P1_JS): the sorted one is full strength with an arrow --
   down for most first, up for least first */
.ps-sort{background:none;border:0;margin:0;padding:4px 1.5px;font:inherit;letter-spacing:inherit;color:inherit;cursor:pointer;white-space:nowrap}
.ps-t th[aria-sort=descending],.ps-t th[aria-sort=ascending]{color:var(--text)}
/* League top 3 in the stats that count (player_stats.MEDAL_STATS): a gold / silver / bronze bar
   under the number (Jason, 2026-09-28) */
.ps-md{display:inline-block;padding-bottom:1px;border-bottom:3px solid}
.ps-md1{border-color:#d4a72c}
.ps-md2{border-color:#a3a9b0}
.ps-md3{border-color:#b87333}
/* The sorted column is highlighted the way the division table highlights a team's own row
   (render_page2team .st-row.is-you): tinted, bold, rounded ends -- only after a header is
   tapped; nothing is highlighted when the page opens (Jason, 2026-09-28) */
.ps-t .ps-on{background:var(--tile-hover);font-weight:700}
.ps-t thead .ps-on{border-radius:8px 8px 0 0}
.ps-t tbody tr:last-child .ps-on{border-radius:0 0 8px 8px}
.ps-t th[aria-sort=descending] .ps-sort::after{content:"\25BE";margin-left:2px}
.ps-t th[aria-sort=ascending] .ps-sort::after{content:"\25B4";margin-left:2px}
.ps-t td{text-align:right;padding:6px 2px;white-space:nowrap;border-top:1px solid var(--tile-border-soft)}
.ps-t tbody th{text-align:left;font-weight:700;padding:6px 5px 6px 0;border-top:1px solid var(--tile-border-soft);
  position:sticky;left:0;z-index:1;background:var(--tile)}
.ps-t thead th:first-child{position:sticky;left:0;z-index:1;background:var(--tile)}
/* first name over last name, and beside them the jersey number over the position (2026-10-03):
   a two-by-two grid, so "#7" sits right above "QB" whatever the names' lengths -- names break only
   after a hyphen, so the tables grow down instead of sideways */
.ps-nm{display:inline-grid;grid-template-columns:auto auto;column-gap:5px;align-items:baseline;font-size:12px;line-height:1.2;text-align:left}
.ps-fn,.ps-ln{display:block}
.ps-fn,.ps-nm .ps-pos,.ps-no{white-space:nowrap}
.ps-no{font-size:10px;font-weight:400;color:var(--text-2);font-variant-numeric:tabular-nums}
@media (max-width:370px){.p2-l .ps-t,.p2-l .ps-nm{font-size:11px}}   /* small Android phones: Defense still fits */
.ps-pos{display:inline;font-size:10px;font-weight:400;color:var(--text-2);letter-spacing:.04em}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
/* a hyphen inside a person's name (esc_name), site-wide: Inter's hyphen has ~.06em of empty side
   on each side, plus the letters' own, which read as a space either side of it ("Smith - Njigba");
   .08em in from each side closes it without the hyphen touching the letters */
.hy{margin:0 -.08em}
"""

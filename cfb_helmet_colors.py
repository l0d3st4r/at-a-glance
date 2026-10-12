"""
Jason's helmet colors for the college teams (2026-10-12), picked in the CFB Helmet Color Picker artifact
(https://claude.ai/artifact/MRprJkx9UPZeywvdj5UoZ8): every team in the Week 7 AP and Coaches polls, ranked
or receiving votes. Keyed by ESPN team id (abbreviations can change), the abbreviation alongside.

(shell, facemask, ear piece). His light and dark picks were the same for every team, so one set serves
both themes (render_cfb.py draws one helmet file a team). A school not listed here -- a team new to the
polls, an opponent -- keeps cfb_team_info's colors: its primary on the shell, its alternate on the rest.
"""

HELMET_COLORS = {
    61: ("#BA0C2F", "#2C2A29", "#000000"),     # UGA
    87: ("#C99700", "#A5ACAF", "#0C2340"),     # ND
    2390: ("#FFFFFF", "#005030", "#F47321"),   # MIA
    194: ("#A7B1B7", "#A7B1B7", "#BA0C2F"),    # OSU
    84: ("#990000", "#A5ACAF", "#FFFFFF"),     # IU
    333: ("#9E1B32", "#A5ACAF", "#FFFFFF"),    # ALA
    251: ("#BF5700", "#A5ACAF", "#FFFFFF"),    # TEX
    252: ("#003DA5", "#002E5D", "#FFFFFF"),    # BYU
    145: ("#006BA6", "#A5ACAF", "#CF142B"),    # MISS
    2641: ("#C30020", "#000000", "#000000"),   # TTU
    254: ("#BE0000", "#A5ACAF", "#FFFFFF"),    # UTAH
    26: ("#F2A900", "#2774AE", "#FFFFFF"),     # UCLA
    142: ("#000000", "#000000", "#F1B82D"),    # MIZ
    2633: ("#FFFFFF", "#FF8200", "#FF8200"),   # TENN
    96: ("#0033A0", "#A5ACAF", "#FFFFFF"),     # UK
    344: ("#5D1725", "#C1C6C8", "#C1C6C8"),    # MSST
    2294: ("#000000", "#FFCD00", "#FFCD00"),   # IOWA
    197: ("#FE5C00", "#000000", "#000000"),    # OKST
    30: ("#990000", "#A5ACAF", "#FFCC00"),     # USC
    248: ("#C8102E", "#A5ACAF", "#FFFFFF"),    # HOU
    154: ("#CEB888", "#2C2A29", "#000000"),    # WAKE
    99: ("#FDD023", "#461D7C", "#461D7C"),     # LSU
    68: ("#0033A0", "#D64309", "#FFFFFF"),     # BOIS
    2567: ("#FFFFFF", "#D70000", "#0033A1"),   # SMU
    77: ("#582C83", "#A5ACAF", "#FFFFFF"),     # NU
    275: ("#FFFFFF", "#A00000", "#A00000"),    # WIS
    2483: ("#007030", "#FEE11A", "#FFFFFF"),   # ORE
    12: ("#CC0033", "#003366", "#FFFFFF"),     # ARIZ
    158: ("#FFFFFF", "#D00000", "#E31937"),    # NEB
    201: ("#990000", "#A5ACAF", "#FFFFFF"),    # OU
    256: ("#CBB677", "#450084", "#450084"),    # JMU
    57: ("#FA4616", "#0021A5", "#FFFFFF"),     # FLA
    150: ("#00539B", "#A5ACAF", "#FFFFFF"),    # DUKE
    167: ("#BA0C2F", "#A7A8AA", "#FFFFFF"),    # UNM
    204: ("#FFFFFF", "#000000", "#DC4405"),    # ORST
    221: ("#FFB81C", "#003594", "#003594"),    # PITT
    2636: ("#0C2340", "#F15A22", "#FFFFFF"),   # UTSA
    239: ("#154734", "#000000", "#FFB81C"),    # BAY
    235: ("#00498F", "#9C9EA1", "#FFFFFF"),    # MEM
    153: ("#7BAFD4", "#13294B", "#FFFFFF"),    # UNC
}

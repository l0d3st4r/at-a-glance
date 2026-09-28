"""
Static reference: each team's head coach and who actually calls its offensive and defensive
plays (added 2026-09-28 for Page 2's team Overview card).

Hand-maintained, like divisions.py and stadiums.py, because no data source the pipeline uses
has it: nflverse has no play-caller field at all, and its schedule's home_coach/away_coach
columns lag hires (for 2026 they still list McDermott at BUF, Gannon at ARI and Morris at ATL,
plus a "Kubliak" typo at LV). So this table is the source of truth for the head coach too.

Check it every offseason (hires and play-calling announcements land January-March) and after
any in-season firing or play-calling change. Built from 2026 reporting (team sites, NFL.com,
ESPN, PFT) as of Week 4.

Keyed by nflverse team abbreviation (the Rams are "LA", as everywhere in the pipeline).
"off" / "def" are (name, role): role is "HC" when the head coach calls that side himself,
else the coordinator's title ("OC" / "DC").
"""

COACHES = {
    # AFC East
    "BUF": {"hc": "Joe Brady", "off": ("Joe Brady", "HC"), "def": ("Jim Leonhard", "DC")},
    "MIA": {"hc": "Jeff Hafley", "off": ("Bobby Slowik", "OC"), "def": ("Jeff Hafley", "HC")},
    "NE": {"hc": "Mike Vrabel", "off": ("Josh McDaniels", "OC"), "def": ("Zak Kuhr", "DC")},
    "NYJ": {"hc": "Aaron Glenn", "off": ("Frank Reich", "OC"), "def": ("Aaron Glenn", "HC")},
    # AFC North
    "BAL": {"hc": "Jesse Minter", "off": ("Declan Doyle", "OC"), "def": ("Jesse Minter", "HC")},
    "CIN": {"hc": "Zac Taylor", "off": ("Zac Taylor", "HC"), "def": ("Al Golden", "DC")},
    "CLE": {"hc": "Todd Monken", "off": ("Todd Monken", "HC"), "def": ("Mike Rutenberg", "DC")},
    "PIT": {"hc": "Mike McCarthy", "off": ("Mike McCarthy", "HC"), "def": ("Patrick Graham", "DC")},
    # AFC South
    "HOU": {"hc": "DeMeco Ryans", "off": ("Nick Caley", "OC"), "def": ("Matt Burke", "DC")},
    "IND": {"hc": "Shane Steichen", "off": ("Shane Steichen", "HC"), "def": ("Lou Anarumo", "DC")},
    "JAX": {"hc": "Liam Coen", "off": ("Liam Coen", "HC"), "def": ("Anthony Campanile", "DC")},
    "TEN": {"hc": "Robert Saleh", "off": ("Brian Daboll", "OC"), "def": ("Robert Saleh", "HC")},
    # AFC West
    "DEN": {"hc": "Sean Payton", "off": ("Davis Webb", "OC"), "def": ("Vance Joseph", "DC")},
    "KC": {"hc": "Andy Reid", "off": ("Andy Reid", "HC"), "def": ("Steve Spagnuolo", "DC")},
    "LV": {"hc": "Klint Kubiak", "off": ("Klint Kubiak", "HC"), "def": ("Rob Leonard", "DC")},
    "LAC": {"hc": "Jim Harbaugh", "off": ("Mike McDaniel", "OC"), "def": ("Chris O'Leary", "DC")},
    # NFC East
    "DAL": {"hc": "Brian Schottenheimer", "off": ("Brian Schottenheimer", "HC"), "def": ("Christian Parker", "DC")},
    "NYG": {"hc": "John Harbaugh", "off": ("Matt Nagy", "OC"), "def": ("Dennard Wilson", "DC")},
    "PHI": {"hc": "Nick Sirianni", "off": ("Sean Mannion", "OC"), "def": ("Vic Fangio", "DC")},
    "WAS": {"hc": "Dan Quinn", "off": ("David Blough", "OC"), "def": ("Daronte Jones", "DC")},
    # NFC North
    "CHI": {"hc": "Ben Johnson", "off": ("Ben Johnson", "HC"), "def": ("Dennis Allen", "DC")},
    "DET": {"hc": "Dan Campbell", "off": ("Drew Petzing", "OC"), "def": ("Kelvin Sheppard", "DC")},
    "GB": {"hc": "Matt LaFleur", "off": ("Matt LaFleur", "HC"), "def": ("Jonathan Gannon", "DC")},
    "MIN": {"hc": "Kevin O'Connell", "off": ("Kevin O'Connell", "HC"), "def": ("Brian Flores", "DC")},
    # NFC South
    "ATL": {"hc": "Kevin Stefanski", "off": ("Tommy Rees", "OC"), "def": ("Jeff Ulbrich", "DC")},
    "CAR": {"hc": "Dave Canales", "off": ("Brad Idzik", "OC"), "def": ("Ejiro Evero", "DC")},
    "NO": {"hc": "Kellen Moore", "off": ("Kellen Moore", "HC"), "def": ("Brandon Staley", "DC")},
    "TB": {"hc": "Todd Bowles", "off": ("Zac Robinson", "OC"), "def": ("Todd Bowles", "HC")},
    # NFC West
    "ARI": {"hc": "Mike LaFleur", "off": ("Mike LaFleur", "HC"), "def": ("Nick Rallis", "DC")},
    "LA": {"hc": "Sean McVay", "off": ("Sean McVay", "HC"), "def": ("Chris Shula", "DC")},
    "SF": {"hc": "Kyle Shanahan", "off": ("Kyle Shanahan", "HC"), "def": ("Raheem Morris", "DC")},
    "SEA": {"hc": "Mike Macdonald", "off": ("Brian Fleury", "OC"), "def": ("Mike Macdonald", "HC")},
}

# A few sources spell some teams differently; map them onto the keys above.
ABBR_ALIASES = {"LAR": "LA", "WSH": "WAS", "JAC": "JAX"}


def coaches_for(abbr):
    """{"head_coach", "off_caller": {"name", "role"}, "def_caller": {...}} or None if unknown."""
    row = COACHES.get(ABBR_ALIASES.get(abbr, abbr))
    if not row:
        return None
    return {
        "head_coach": row["hc"],
        "off_caller": {"name": row["off"][0], "role": row["off"][1]},
        "def_caller": {"name": row["def"][0], "role": row["def"][1]},
    }

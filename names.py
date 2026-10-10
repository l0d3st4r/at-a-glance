"""
Players' names, split the one way the whole site uses (2026-10-10): Page 1's leaders and injuries,
Player Stats, the Stat Leaders page (its race labels and condensed tiles too) and the NBA's pages.
Before this each place found the last name its own way, and some lost part of it: "A. Brown" for
Amon-Ra St. Brown, "K. Noy" for Kyle Van Noy, "Michael Sturdivant" for J. Michael Sturdivant.
"""

SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
PARTICLES = {"st.", "st", "van", "von", "den", "der", "de", "del", "della", "da", "di", "du", "la", "le", "dos", "das"}


def split_name(name):
    """('J. Michael', 'Sturdivant'), ('Amon-Ra', 'St. Brown'), ('Ennis', 'Rakestraw Jr.'),
    ('Jordan', 'van den Berg'): the last name is the final word, plus a suffix after it and any
    particles before it; everything ahead of that is the first name."""
    words = (name or "").split()   # any whitespace, non-breaking included
    if len(words) < 2:
        return "", " ".join(words)
    i = len(words) - 1
    if words[i].lower() in SUFFIXES and i > 1:
        i -= 1
    while i > 1 and words[i - 1].lower() in PARTICLES:
        i -= 1
    return " ".join(words[:i]), " ".join(words[i:])


def short_name(name):
    """"A. St. Brown", "M. Harrison Jr.": the first initial and the last name."""
    first, last = split_name(name)
    return f"{first[0]}. {last}" if first else last


def bare_last(name):
    """The last name without its suffix -- "Harrison" for Marvin Harrison Jr. -- where there's room
    for nothing more (the Stat Leaders race labels and condensed tiles)."""
    words = split_name(name)[1].split()
    return " ".join(words[:-1]) if len(words) > 1 and words[-1].lower() in SUFFIXES else " ".join(words)

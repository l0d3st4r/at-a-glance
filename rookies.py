"""
Rookies (added 2026-09-30): every player in his first NFL season gets a small "R" after his
position wherever his name shows -- Player Stats, the Leaders card, the injury lists.

Who counts: nflverse's season roster marks each player's first season (rookie_year); a rookie
is anyone whose rookie_year is this season (drafted or not). Players are matched by gsis id
where the data carries one (player stats, injury rows), otherwise by full name -- but only for
names no veteran on the roster shares, so a rookie's namesake never gets the mark.
"""

import re


def _key(name):
    return re.sub(r"[^a-z]", "", (name or "").lower())


def build(roster_rows, season, warnings):
    """{"ids": set of gsis ids, "names": set of name keys} for this season's rookies."""
    ids, names, veteran_names = set(), set(), set()
    for r in roster_rows or []:
        try:
            first = int(r.get("rookie_year"))
        except (TypeError, ValueError):
            first = None
        key = _key(r.get("full_name"))
        if first == int(season):
            if r.get("gsis_id"):
                ids.add(r["gsis_id"])
            if key:
                names.add(key)
        elif key:
            veteran_names.add(key)
    if not ids and roster_rows:
        warnings.append("rookies: no player on the roster has this season as his rookie_year")
    return {"ids": ids, "names": names - veteran_names}


def is_rookie(rookies, gsis_id=None, name=None):
    if not rookies:
        return False
    return bool(gsis_id and gsis_id in rookies["ids"]) or bool(name and _key(name) in rookies["names"])


def mark(game_details, player_weeks, rookies):
    """Sets "rookie": True on every rookie's player-stats rows, leaders and injury rows, in place."""
    if not rookies or not (rookies["ids"] or rookies["names"]):
        return
    flag(game_details, player_weeks, "rookie", lambda gsis_id, name: is_rookie(rookies, gsis_id, name))


def flag(game_details, player_weeks, key, hit):
    """Sets `key`: True on every player row hit(gsis_id, name) picks out -- player-stats rows,
    leaders and injury / absence rows -- in place. Shared with reserve.py's IR tag."""
    for rows in (player_weeks or {}).values():
        for r in rows:
            if hit(r.get("id"), r.get("name")):
                r[key] = True

    def walk(node):
        if isinstance(node, dict):
            # a player entry: a leader ({name, full_name, position, value}) or an injury / absence row
            if "position" in node and ("full_name" in node or "name" in node):
                if hit(node.get("gsis_id"), node.get("full_name") or node.get("name")):
                    node[key] = True
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(game_details)

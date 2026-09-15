"""
League-wide rank computation -- generic version.

Since we don't have 100%-confirmed column names for nflverse's team_stats
output yet (see nflverse_client.py's docstring), this computes a rank for
EVERY numeric column it finds across all teams, rather than a hardcoded
list of expected stat names. That way, whatever the real column names
turn out to be once this runs for real, ranks come along automatically --
nothing to update here after the first live run.

Caveat: ranks descending (higher value = better/rank 1) for every column,
which is right for offensive production stats (more yards = better) but
backwards for defensive/"allowed" stats (fewer yards allowed = better).
Flagging this rather than guessing which columns are which -- worth a
follow-up pass once we can see the real column names and split them into
offense/defense-allowed groups properly.
"""


def compute_ranks(team_stats_by_abbr):
    """
    team_stats_by_abbr: {team_abbr: {stat_name: value, ...}, ...}
    Returns: {team_abbr: {stat_name: rank_int}}
    """
    if not team_stats_by_abbr:
        return {}

    all_keys = set()
    for stats in team_stats_by_abbr.values():
        all_keys.update(stats.keys())

    ranks = {abbr: {} for abbr in team_stats_by_abbr}

    for key in all_keys:
        rows = []
        for abbr, stats in team_stats_by_abbr.items():
            value = stats.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                rows.append((abbr, value))
        if len(rows) < len(team_stats_by_abbr) * 0.5:
            continue  # not consistently numeric/present across teams, skip
        rows.sort(key=lambda r: r[1], reverse=True)
        for i, (abbr, _value) in enumerate(rows, start=1):
            ranks[abbr][key] = i

    return ranks

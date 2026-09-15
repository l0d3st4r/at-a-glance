"""
League-wide rank computation.

ESPN's per-team statistics endpoint does not reliably return each team's
own league rank for a given stat (confirmed during research -- team-level
responses omit it even though some opponent-comparison views include
ranks). Rather than depend on finding an ESPN endpoint that returns ranks
directly, we compute them ourselves: pull every team's raw stats once per
run and sort.

This trades 1 extra pass over all 32 teams (we're already fetching each
team's own statistics for the matchup pages, so this mostly reuses that
data) for a rank we can trust and control the definition of.
"""

STAT_KEYS_HIGHER_IS_BETTER = {
    "totalPointsPerGame", "totalYards", "yardsPerGame", "netPassingYards",
    "netPassingYardsPerGame", "rushingYards", "rushingYardsPerGame",
    "totalTouchdowns", "redzoneScoringPct", "redzoneTouchdownPct",
}
# For defensive splits, "better" usually means allowing fewer -- caller should
# pass the right stat dict (defense vs offense) and flag with higher_is_better
# accordingly. Default assumption above covers offensive categories.


def compute_ranks(all_team_stats, stat_names, higher_is_better=True):
    """
    all_team_stats: {team_abbr: {stat_name: {"value": float, ...}, ...}, ...}
    stat_names: list of stat_name keys to rank (must match keys used by
        espn_client.get_team_statistics, e.g. "totalPointsPerGame")
    Returns: {team_abbr: {stat_name: rank_int}} where rank 1 = best.
    """
    ranks = {abbr: {} for abbr in all_team_stats}
    for stat_name in stat_names:
        rows = []
        for abbr, stats in all_team_stats.items():
            entry = stats.get(stat_name)
            value = entry.get("value") if entry else None
            if value is not None:
                rows.append((abbr, value))
        rows.sort(key=lambda r: r[1], reverse=higher_is_better)
        for i, (abbr, _value) in enumerate(rows, start=1):
            ranks[abbr][stat_name] = i
    return ranks

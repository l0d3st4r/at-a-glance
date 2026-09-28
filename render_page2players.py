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
  6. Returns   -- kick returns, then punt returns       both teams stacked

Layout (Jason, 2026-09-28, from the mockups' three versions): a box-score table with the
player column pinned on the left. The short cards (Passing, Kicking, Returns: usually a
player or two per team) stack both teams on one card; the long ones (Rushing, Receiving,
Defense: 25-40 players a team on Defense) put the two teams behind a switch. Long lists
scroll inside the card; a table wider than the card (Defense) scrolls sideways, with a fade
on its right edge while there's more to see (the .more class, set by P1_JS).

Tables start sorted by the card's main stat (yards for Passing, Rushing and Receiving; tackles
for Defense). Tapping a column header sorts by that stat and only then highlights the column
(P1_JS). A number in the league's top 3 for one of player_stats.MEDAL_STATS gets a gold, silver
or bronze bar under it (Jason, 2026-09-28).

Data: game_details[<id>]["player_stats"] = {"away": [...], "home": [...]}, attached by
render_page1.write_all from data/matchups.json's "player_weeks" (player_stats.py), each
player's row carrying "medals" = {stat: 1 | 2 | 3} (player_stats.league_medals).
Missing data never breaks the page: a team with nobody in a card reads "None this season"
("No games played yet" in Week 1, before either team has any stats).
"""

import html

import helmets

DASH = "—"


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


def short_name(name):
    """'Dak Prescott' -> 'D. Prescott' (box-score style); one-word names stay as they are."""
    parts = (name or "").split()
    return f"{parts[0][0]}. {' '.join(parts[1:])}" if len(parts) > 1 else (name or "")


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


# ---------------------------------------------------------------- markup

def _pill(team):
    primary, _secondary = helmets.TEAM_COLORS.get(team, helmets.FALLBACK_COLORS)
    return f'<span class="pill" style="background:{primary}"></span>'


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


def _table(rows, cols, empty, medals, sortable=True):
    if not rows:
        return f'<p class="ps-empty">{esc(empty)}</p>'
    head = "".join(
        f'<th scope="col" aria-sort="none"><button type="button" class="ps-sort">{esc(label)}</button></th>' if sortable
        else f'<th scope="col"><span class="ps-lbl">{esc(label)}</span></th>'
        for label, _f in cols)
    body = "".join(
        f'<tr data-i="{i}"><th scope="row"><span class="ps-nm">{esc(short_name(r["name"]))}</span>'
        f'<span class="ps-pos">{esc(r["pos"])}</span></th>'
        + "".join(_cell(label, f, r, medals.get(label)) for label, f in cols) + "</tr>"
        for i, r in enumerate(rows))
    return (f'<div class="ps-tw"><table class="ps-t"><thead><tr><th scope="col"><span class="vh">Player</span></th>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def _team_tables(players, sections, empty):
    out = []
    for heading, keep, order, cols, medals in sections:
        rows = sorted((r for r in players if keep(r)), key=order)
        if heading:
            out.append(f'<h3 class="ps-sec">{esc(heading)}</h3>')
        out.append(_table(rows, cols, empty, medals))
    return "".join(out)


def card_body(sections, layout, teams, stats):
    """teams = (away, home) abbreviations; stats = {abbr: [player totals]}."""
    # before either team has played (Week 1), say so rather than "None this season" everywhere
    empty = "None this season" if any(stats.values()) else "No games played yet"
    if layout == "stack":
        blocks = "".join(
            f'<div class="ps-team"><div class="ps-th">{_pill(t)}<span class="abbr">{esc(t)}</span></div>'
            f"{_team_tables(stats.get(t) or [], sections, empty)}</div>" for t in teams)
        return f'<div class="ps-scroll">{blocks}</div>'
    tabs = "".join(
        f'<button type="button" class="ps-tab{" on" if i == 0 else ""}" data-team="{esc(t)}" aria-pressed="{"true" if i == 0 else "false"}">'
        f'{_pill(t)}<span class="abbr">{esc(t)}</span></button>' for i, t in enumerate(teams))
    panes = "".join(
        f'<div class="ps-pane{" on" if i == 0 else ""}" data-team="{esc(t)}">{_team_tables(stats.get(t) or [], sections, empty)}</div>'
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
    return (f'<div class="pc-who"><span class="ps-nm">{esc(short_name(r["name"]))}</span>'
            f'<span class="ps-pos">{esc(r["pos"])}</span></div><div class="pc-sts">{stats}</div>')


def condensed_view(teams, stats):
    empty = "None this season" if any(stats.values()) else "No games played yet"
    tabs = "".join(
        f'<button type="button" class="ps-tab{" on" if i == 0 else ""}" data-team="{esc(t)}" aria-pressed="{"true" if i == 0 else "false"}">'
        f'{_pill(t)}<span class="abbr">{esc(t)}</span></button>' for i, t in enumerate(teams))
    cards = []
    for cid, title, section, who, width, left_out in CONDENSED:
        _h, _keep, _order, cols, medals = section
        cols = [c for c in cols if c[0] not in left_out]
        panes = "".join(
            f'<div class="pc-p{" on" if i == 0 else ""}" data-team="{esc(t)}">'
            + (_table(who(stats.get(t) or []), cols, empty, medals, sortable=False) if width == "row"
               else _pairs(who(stats.get(t) or []), cols, empty))
            + "</div>"
            for i, t in enumerate(teams))
        cards.append(f'<a class="card cc pc-{cid} pc-{width}" tabindex="0" aria-label="{esc(title)}">'
                     f'<span class="card-title">{esc(title)}</span>{panes}</a>')
    return f'<div class="p2-view p2-c pc"><div class="ps-sw pc-sw">{tabs}</div>{"".join(cards)}</div>'


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
    slots = "".join(
        f'<section class="slot"><a class="card p2k p2k-ps p2k-{cid}" tabindex="-1" aria-label="{esc(title)}">'
        f'<span class="peek peek-top">{DOWN}<span>{esc(title)}</span></span>'
        f'<div class="body">{card_body(sections, layout, (away, home), stats)}</div>'
        f'<span class="peek peek-bot">{UP}<span>{esc(title)}</span></span></a></section>'
        for cid, title, sections, layout in CARDS)
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(title)}"></button>' for _c, title, _s, _l in CARDS)
    return ('<div class="p2 p2-ps" data-page="leaders" aria-label="Player stats" role="region">'
            f'<div class="p2-view p2-l deck">{slots}</div><nav class="dots p2-dots" aria-label="Cards">{dots}</nav>'
            f'{condensed_view((away, home), stats)}</div>')


# ---------------------------------------------------------------- styles
# Appended to Page 1's stylesheet (same <style id="p1-css">), like P2_CSS / P3_CSS.

P4_CSS = r"""
/* ===== Page 2: Player Stats (2026-09-28) -- the Leaders card's deep dive =====
   Reuses the .p2 shell and deck; expanded view only, like the team pages. */
.p1[data-detail="leaders"] .p2[data-page="leaders"]{display:block}
.p2-ps .p2-l a.card{cursor:default}
.p2-ps .p2-l a.card:focus-visible{outline:none}
.p2-ps .slot.active a.card:hover,.p2-ps .slot.active a.card:focus-visible{transform:none;border-color:var(--tile-border)}
.p2-ps .slot.below a.card:hover,.p2-ps .slot.above a.card:hover{border-color:var(--tile-border-soft)}
/* The card title sits at the top; the stats fill the rest and scroll inside the card when
   they don't fit (a team's Defense runs 25-40 players). */
.p2 .slot .p2k-ps .body{padding:44px 14px 14px;justify-content:flex-start;gap:12px;min-height:0}
.ps-scroll{flex:1;min-height:0;overflow-y:auto;-webkit-overflow-scrolling:touch;margin:0 -14px;padding:0 14px 6px}
/* Team switch (Rushing, Receiving, Defense): the two teams' pills, the chosen one filled in */
.ps-sw{display:flex;justify-content:center;gap:8px;flex:none}
.ps-tab{display:flex;align-items:center;gap:8px;border:1px solid var(--tile-border-soft);background:none;color:var(--text);
  border-radius:999px;padding:6px 14px;font:inherit;cursor:pointer}
.ps-tab .pill{width:26px;height:8px}
.ps-tab .abbr{font-size:18px}
.ps-tab.on{background:var(--tile-hover);border-color:var(--tile-border)}
.ps-tab:not(.on){opacity:.55}
.ps-pane{display:none}
.ps-pane.on{display:block}
/* Both teams stacked (Passing, Kicking, Returns): each under its pill + abbreviation */
.ps-team+.ps-team{margin-top:18px}
.ps-th{display:flex;align-items:center;gap:8px;padding:2px 0 4px}
.ps-th .pill{width:26px;height:8px}
.ps-th .abbr{font-size:20px}
.ps-sec{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2);margin:12px 0 2px}
.ps-th+.ps-sec,.ps-pane>.ps-sec:first-child{margin-top:4px}
.ps-empty{font-size:13px;color:var(--text-2);padding:6px 0}
/* Condensed view: the team switch across the top, then Passing / Rushing / Receiving / Defense
   one per row and Kicking + Punt Returns side by side; rows share the height by how many players
   each holds, but never get shorter than their contents -- on a short phone (iPhone SE) that's
   more than the screen, so the view scrolls there instead of cutting rows off (P1_JS's
   detailAtTop keeps a pull-down from closing the page until it's scrolled back to the top).
   Each card shows the chosen team's pane (.pc-p.on). */
.p2-c.pc{grid-template-columns:1fr 1fr;overflow-y:auto;-webkit-overflow-scrolling:touch;
  grid-template-rows:auto minmax(min-content,1.1fr) minmax(min-content,1.5fr) minmax(min-content,2fr)
    minmax(min-content,2fr) minmax(min-content,1.2fr)}
.pc-sw{grid-column:1/-1}
.p2-c.pc a.card.cc{justify-content:flex-start;padding:var(--ctitle) 12px 6px;gap:0}
.p2-c.pc a.card.pc-row{grid-column:1/-1}
/* "safe": if a pane ever overflows, it's the bottom that's cut, never the player's name */
.pc-p{display:none;flex-direction:column;justify-content:safe center;flex:1;min-height:0}
.pc-p.on{display:flex}
.pc .ps-tw{margin:0 -12px;padding:0 12px}
/* a little tighter than the expanded tables, so Defense's ten columns need less sideways scrolling */
.pc .ps-t{font-size:11.5px}
.pc .ps-t td{padding:3px}
.pc .ps-t tbody th{padding:3px 6px 3px 0}
.pc .ps-t thead th{padding:0 3px 2px;font-size:9px}
.pc .ps-t tbody th .ps-nm{display:inline}
.pc .ps-t tbody th .ps-pos{display:inline;margin-left:4px}
.ps-lbl{display:block}
.pc-who{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px}
.pc-who .ps-nm{display:inline;font-weight:700}
.pc-who .ps-pos{display:inline;margin-left:4px}
/* Kicking / Punt Returns: the stats always on one line (Jason, 2026-09-28), spread across the card */
.pc-sts{display:flex;flex-wrap:nowrap;justify-content:space-between;gap:6px}
.pc-st{display:flex;flex-direction:column;line-height:1.1;white-space:nowrap}
.pc-st b{font-size:14px;font-variant-numeric:tabular-nums}
@media (max-width:370px){.pc-st b{font-size:13px}.pc .ps-t{font-size:11px}.pc .ps-t td{padding:3px 2px}.pc .ps-t tbody th{padding-right:3px}}
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
.ps-sort{background:none;border:0;margin:0;padding:4px;font:inherit;letter-spacing:inherit;color:inherit;cursor:pointer;white-space:nowrap}
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
.ps-t td{text-align:right;padding:6px 4px;white-space:nowrap;border-top:1px solid var(--tile-border-soft)}
.ps-t tbody th{text-align:left;font-weight:700;padding:6px 8px 6px 0;white-space:nowrap;border-top:1px solid var(--tile-border-soft);
  position:sticky;left:0;z-index:1;background:var(--tile)}
.ps-t thead th:first-child{position:sticky;left:0;z-index:1;background:var(--tile)}
.ps-nm{display:block;font-size:12px}
.ps-pos{display:block;font-size:10px;font-weight:400;color:var(--text-2);letter-spacing:.04em}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
"""

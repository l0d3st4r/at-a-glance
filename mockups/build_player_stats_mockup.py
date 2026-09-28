"""
Player Stats mockup (2026-09-28) -- NOT part of the live build.

A new Page 2 layer, "Player Stats", that the Leaders card on Page 1 would open (that card
already carries data-detail="leaders" but has no page behind it yet). Six cards, each the
season to date (regular season, every week before this game) for both teams in the matchup:

  1. Passing   -- everyone with a pass attempt
  2. Rushing   -- everyone with a rush attempt
  3. Receiving -- everyone with a target
  4. Defense   -- everyone with any defensive stat
  5. Kicking   -- field goals / PATs, plus punting
  6. Returns   -- kick and punt returns

Three versions of the layout, same data:
  V1 "Team switch + table"  -- the two teams' pills at the top switch between them; a box-score
                               table below, name column pinned, wide cards (Defense) scroll
                               sideways.
  V2 "Both teams stacked"   -- no switch: the away team's table, then the home team's, each
                               under its own pill + abbreviation header.
  V3 "Player rows"          -- no table: one row per player, name + position over a one-line
                               stat summary, the card's headline number big on the right. Same
                               team switch as V1.

Long lists scroll inside the card (a team's Defense card runs 25-40 players).

How it's built: the markup replaces the Game Info Page 2 layer in a copy of a real game page,
so it opens with the page's own deck, dots, peeks, top bar and theme (at #/game-info). Data
comes live from nflverse's weekly player stats, the same source the Leaders card uses.

Run after a normal build (so site/ exists):
    python mockups/build_player_stats_mockup.py <scratch folder for the mock site>
Writes game/ps-v1.html, ps-v2.html, ps-v3.html there (copies of GAME with the swap).
"""

import html
import os
import re
import shutil
import sys

import nflreadpy as nfl
import polars as pl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import helmets  # noqa: E402

SITE = os.path.join(ROOT, "site")
GAME = "2026_04_DAL_HOU"
SEASON, WEEK, AWAY, HOME = 2026, 4, "DAL", "HOU"
DASH = "—"


def esc(v):
    return html.escape(str(v), quote=True)


# ---------------------------------------------------------------- data

SUM_COLS = [
    "completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions", "sacks_suffered",
    "carries", "rushing_yards", "rushing_tds", "rushing_fumbles_lost", "rushing_first_downs",
    "receptions", "targets", "receiving_yards", "receiving_tds", "receiving_first_downs",
    "def_tackles_solo", "def_tackle_assists", "def_tackles_for_loss", "def_sacks", "def_qb_hits",
    "def_interceptions", "def_pass_defended", "def_fumbles_forced", "fumble_recovery_opp", "def_tds",
    "fg_made", "fg_att", "pat_made", "pat_att", "pt_att", "pt_yards", "pt_net_yards", "pt_inside_20",
    "kickoff_returns", "kickoff_return_yards", "punt_returns", "punt_return_yards",
]


def season_stats():
    df = nfl.load_player_stats(seasons=[SEASON], summary_level="week")
    df = df.filter((pl.col("season_type") == "REG") & (pl.col("week") < WEEK) & pl.col("team").is_in([AWAY, HOME]))
    agg = df.group_by(["team", "player_id"]).agg(
        [pl.col("player_display_name").last(), pl.col("position").last()]
        + [pl.col(c).fill_null(0).sum() for c in SUM_COLS]
        + [pl.col("fg_long").max()])
    out = {AWAY: [], HOME: []}
    for r in agg.to_dicts():
        out[r["team"]].append(r)
    return out


def short(name):
    parts = (name or "").split()
    return f"{parts[0][0]}. {' '.join(parts[1:])}" if len(parts) > 1 else (name or "")


def n(v):
    return f"{int(round(v)):,}" if v is not None else DASH


def avg(num, den):
    return f"{num / den:.1f}" if den else DASH


def rating(r):
    att = r["attempts"]
    if not att:
        return DASH
    clamp = lambda x: max(0.0, min(2.375, x))
    a = clamp((r["completions"] / att - 0.3) * 5)
    b = clamp((r["passing_yards"] / att - 3) * 0.25)
    c = clamp(r["passing_tds"] / att * 20)
    d = clamp(2.375 - r["passing_interceptions"] / att * 25)
    return f"{(a + b + c + d) / 6 * 100:.1f}"


def sacks(v):
    return f"{v:g}" if v else "0"


# Each card: rows (filter + sort), table columns (label, fn), V3 headline (label, fn), V3 summary fn.
CARDS = [
    ("passing", "Passing",
     lambda r: r["attempts"] > 0, lambda r: -r["attempts"],
     [("C/ATT", lambda r: f'{n(r["completions"])}/{n(r["attempts"])}'), ("YDS", lambda r: n(r["passing_yards"])),
      ("Y/A", lambda r: avg(r["passing_yards"], r["attempts"])), ("TD", lambda r: n(r["passing_tds"])),
      ("INT", lambda r: n(r["passing_interceptions"])), ("SCK", lambda r: n(r["sacks_suffered"])), ("RTG", rating)],
     ("YDS", lambda r: n(r["passing_yards"])),
     lambda r: (f'{n(r["completions"])}/{n(r["attempts"])} · {n(r["passing_tds"])} TD · {n(r["passing_interceptions"])} INT'
                f' · {avg(r["passing_yards"], r["attempts"])} Y/A · {rating(r)} RTG')),
    ("rushing", "Rushing",
     lambda r: r["carries"] > 0, lambda r: -r["carries"],
     [("ATT", lambda r: n(r["carries"])), ("YDS", lambda r: n(r["rushing_yards"])),
      ("AVG", lambda r: avg(r["rushing_yards"], r["carries"])), ("TD", lambda r: n(r["rushing_tds"])),
      ("1D", lambda r: n(r["rushing_first_downs"])), ("FUM", lambda r: n(r["rushing_fumbles_lost"]))],
     ("YDS", lambda r: n(r["rushing_yards"])),
     lambda r: (f'{n(r["carries"])} ATT · {avg(r["rushing_yards"], r["carries"])} AVG · {n(r["rushing_tds"])} TD'
                f' · {n(r["rushing_first_downs"])} 1D')),
    ("receiving", "Receiving",
     lambda r: r["targets"] > 0 or r["receptions"] > 0, lambda r: -r["receiving_yards"],
     [("REC", lambda r: n(r["receptions"])), ("TGT", lambda r: n(r["targets"])), ("YDS", lambda r: n(r["receiving_yards"])),
      ("AVG", lambda r: avg(r["receiving_yards"], r["receptions"])), ("TD", lambda r: n(r["receiving_tds"])),
      ("1D", lambda r: n(r["receiving_first_downs"]))],
     ("YDS", lambda r: n(r["receiving_yards"])),
     lambda r: (f'{n(r["receptions"])} REC · {n(r["targets"])} TGT · {avg(r["receiving_yards"], r["receptions"])} AVG'
                f' · {n(r["receiving_tds"])} TD')),
    ("defense", "Defense",
     lambda r: any(r[c] for c in ("def_tackles_solo", "def_tackle_assists", "def_sacks", "def_qb_hits", "def_interceptions",
                                  "def_pass_defended", "def_fumbles_forced", "fumble_recovery_opp", "def_tackles_for_loss")),
     lambda r: -(r["def_tackles_solo"] + r["def_tackle_assists"]),
     [("TKL", lambda r: n(r["def_tackles_solo"] + r["def_tackle_assists"])), ("SOLO", lambda r: n(r["def_tackles_solo"])),
      ("TFL", lambda r: n(r["def_tackles_for_loss"])), ("SCK", lambda r: sacks(r["def_sacks"])),
      ("QBH", lambda r: n(r["def_qb_hits"])), ("INT", lambda r: n(r["def_interceptions"])),
      ("PD", lambda r: n(r["def_pass_defended"])), ("FF", lambda r: n(r["def_fumbles_forced"])),
      ("FR", lambda r: n(r["fumble_recovery_opp"])), ("TD", lambda r: n(r["def_tds"]))],
     ("TKL", lambda r: n(r["def_tackles_solo"] + r["def_tackle_assists"])),
     lambda r: " · ".join(x for x in (
         f'{sacks(r["def_sacks"])} SCK' if r["def_sacks"] else "", f'{n(r["def_tackles_for_loss"])} TFL' if r["def_tackles_for_loss"] else "",
         f'{n(r["def_qb_hits"])} QBH' if r["def_qb_hits"] else "", f'{n(r["def_interceptions"])} INT' if r["def_interceptions"] else "",
         f'{n(r["def_pass_defended"])} PD' if r["def_pass_defended"] else "", f'{n(r["def_fumbles_forced"])} FF' if r["def_fumbles_forced"] else "",
         f'{n(r["fumble_recovery_opp"])} FR' if r["fumble_recovery_opp"] else "") if x) or f'{n(r["def_tackles_solo"])} SOLO'),
]
KICK_COLS = [("FG", lambda r: f'{n(r["fg_made"])}/{n(r["fg_att"])}'), ("PCT", lambda r: f'{r["fg_made"] / r["fg_att"] * 100:.0f}' if r["fg_att"] else DASH),
             ("LNG", lambda r: n(r["fg_long"]) if r["fg_long"] else DASH), ("XP", lambda r: f'{n(r["pat_made"])}/{n(r["pat_att"])}'),
             ("PTS", lambda r: n(r["fg_made"] * 3 + r["pat_made"]))]
PUNT_COLS = [("P", lambda r: n(r["pt_att"])), ("YDS", lambda r: n(r["pt_yards"])), ("AVG", lambda r: avg(r["pt_yards"], r["pt_att"])),
             ("NET", lambda r: avg(r["pt_net_yards"], r["pt_att"])), ("IN20", lambda r: n(r["pt_inside_20"]))]
KR_COLS = [("KR", lambda r: n(r["kickoff_returns"])), ("YDS", lambda r: n(r["kickoff_return_yards"])),
           ("AVG", lambda r: avg(r["kickoff_return_yards"], r["kickoff_returns"]))]
PR_COLS = [("PR", lambda r: n(r["punt_returns"])), ("YDS", lambda r: n(r["punt_return_yards"])),
           ("AVG", lambda r: avg(r["punt_return_yards"], r["punt_returns"]))]
SECTIONS = {
    "kicking": ("Kicking", [("Field Goals & PATs", lambda r: r["fg_att"] > 0 or r["pat_att"] > 0, lambda r: -r["fg_att"], KICK_COLS,
                             ("PTS", lambda r: n(r["fg_made"] * 3 + r["pat_made"])),
                             lambda r: f'{n(r["fg_made"])}/{n(r["fg_att"])} FG · LNG {n(r["fg_long"]) if r["fg_long"] else DASH} · {n(r["pat_made"])}/{n(r["pat_att"])} XP'),
                            ("Punting", lambda r: r["pt_att"] > 0, lambda r: -r["pt_att"], PUNT_COLS,
                             ("AVG", lambda r: avg(r["pt_yards"], r["pt_att"])),
                             lambda r: f'{n(r["pt_att"])} P · {n(r["pt_yards"])} YDS · {avg(r["pt_net_yards"], r["pt_att"])} NET · {n(r["pt_inside_20"])} IN20')]),
    "returns": ("Returns", [("Kick Returns", lambda r: r["kickoff_returns"] > 0, lambda r: -r["kickoff_returns"], KR_COLS,
                             ("YDS", lambda r: n(r["kickoff_return_yards"])),
                             lambda r: f'{n(r["kickoff_returns"])} KR · {avg(r["kickoff_return_yards"], r["kickoff_returns"])} AVG'),
                            ("Punt Returns", lambda r: r["punt_returns"] > 0, lambda r: -r["punt_returns"], PR_COLS,
                             ("YDS", lambda r: n(r["punt_return_yards"])),
                             lambda r: f'{n(r["punt_returns"])} PR · {avg(r["punt_return_yards"], r["punt_returns"])} AVG')]),
}


def all_cards():
    """[(cid, title, [(section title or None, keep, sort, cols, headline, summary)])]"""
    out = [(cid, title, [(None, keep, sort, cols, head, summ)]) for cid, title, keep, sort, cols, head, summ in CARDS]
    out += [(cid, title, secs) for cid, (title, secs) in SECTIONS.items()]
    return out


# ---------------------------------------------------------------- markup

def pill(team):
    primary, _s = helmets.TEAM_COLORS.get(team, helmets.FALLBACK_COLORS)
    return f'<span class="pill" style="background:{primary}"></span>'


def table(rows, cols):
    if not rows:
        return '<p class="ps-empty">None this season</p>'
    head = "".join(f"<th>{esc(c)}</th>" for c, _f in cols)
    body = "".join(
        f'<tr><th scope="row"><span class="ps-nm">{esc(short(r["player_display_name"]))}</span>'
        f'<span class="ps-pos">{esc(r["position"] or "")}</span></th>'
        + "".join(f"<td>{esc(f(r))}</td>" for _c, f in cols) + "</tr>"
        for r in rows)
    return f'<div class="ps-tw"><table class="ps-t"><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def plist(rows, headline, summary):
    if not rows:
        return '<p class="ps-empty">None this season</p>'
    hl, hf = headline
    return '<ul class="ps-l">' + "".join(
        f'<li><div class="ps-who"><span class="ps-nm">{esc(short(r["player_display_name"]))}</span>'
        f'<span class="ps-pos">{esc(r["position"] or "")}</span><span class="ps-sum">{esc(summary(r))}</span></div>'
        f'<div class="ps-hl"><b>{esc(hf(r))}</b><span>{esc(hl)}</span></div></li>'
        for r in rows) + "</ul>"


def team_block(team, players, sections, mode):
    parts = []
    for stitle, keep, sort, cols, head, summ in sections:
        rows = sorted((r for r in players if keep(r)), key=sort)
        if stitle:
            parts.append(f'<h3 class="ps-sec">{esc(stitle)}</h3>')
        parts.append(plist(rows, head, summ) if mode == "rows" else table(rows, cols))
    return "".join(parts)


def switch(active):
    return ('<div class="ps-sw" role="tablist">' + "".join(
        f'<button type="button" class="ps-tab{" on" if t == active else ""}" data-team="{t}">{pill(t)}<span class="abbr">{t}</span></button>'
        for t in (AWAY, HOME)) + "</div>")


def card_body(title, sections, stats, version):
    if version == "v2":
        inner = "".join(
            f'<div class="ps-team"><div class="ps-th">{pill(t)}<span class="abbr">{t}</span></div>'
            f'{team_block(t, stats[t], sections, "table")}</div>' for t in (AWAY, HOME))
        return f'<div class="ps-scroll">{inner}</div>'
    mode = "rows" if version == "v3" else "table"
    panes = "".join(
        f'<div class="ps-pane{" on" if t == AWAY else ""}" data-team="{t}">{team_block(t, stats[t], sections, mode)}</div>'
        for t in (AWAY, HOME))
    return f'{switch(AWAY)}<div class="ps-scroll">{panes}</div>'


def layer(stats, version):
    from render_page1 import UP, DOWN
    cards = all_cards()
    slots = "".join(
        f'<section class="slot"><a class="card p2k p2k-ps" tabindex="-1" aria-label="{esc(title)}">'
        f'<span class="peek peek-top">{DOWN}<span>{esc(title)}</span></span>'
        f'<div class="body">{card_body(title, secs, stats, version)}</div>'
        f'<span class="peek peek-bot">{UP}<span>{esc(title)}</span></span></a></section>'
        for _cid, title, secs in cards)
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(t)}"></button>' for _c, t, _s in cards)
    return ('<div class="p2" data-page="game-info" aria-label="Player stats" role="region">'
            f'<div class="p2-view p2-l deck">{slots}</div><nav class="dots p2-dots" aria-label="Cards">{dots}</nav>'
            '<div class="p2-view p2-c n0"></div></div>')


CSS = """
.p1[data-detail] .toggle{visibility:hidden}
.p2 .slot .body.ps-body,.p2 .p2k-ps .body{padding:40px 14px 14px;justify-content:flex-start;gap:10px;display:flex;flex-direction:column;min-height:0}
.ps-scroll{flex:1;min-height:0;overflow:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;margin:0 -14px;padding:0 14px}
.ps-sw{display:flex;justify-content:center;gap:8px}
.ps-tab{display:flex;align-items:center;gap:8px;border:1px solid var(--tile-border-soft);background:none;color:var(--text);
  border-radius:999px;padding:6px 14px;font:inherit;cursor:pointer}
.ps-tab .pill{width:26px;height:8px}
.ps-tab .abbr{font-size:18px}
.ps-tab.on{background:var(--tile-hover);border-color:var(--tile-border)}
.ps-tab:not(.on){opacity:.55}
.ps-pane{display:none}.ps-pane.on{display:block}
.ps-sec{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2);margin:14px 0 4px}
.ps-sec:first-child{margin-top:4px}
.ps-empty{font-size:13px;color:var(--text-2);padding:6px 0}
.ps-tw{overflow-x:auto;margin:0 -14px;padding:0 14px}
.ps-t{border-collapse:collapse;width:100%;font-size:12px;font-variant-numeric:tabular-nums}
/* a table wider than the card scrolls sideways; a fade on the right edge says there's more */
.ps-tw.more{-webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 36px),transparent);mask-image:linear-gradient(90deg,#000 calc(100% - 36px),transparent)}
.ps-t thead th{font-size:10px;font-weight:700;letter-spacing:.05em;color:var(--text-2);text-align:right;padding:4px 4px;white-space:nowrap;
  position:sticky;top:0;background:var(--tile)}
.ps-t td{text-align:right;padding:6px 4px;white-space:nowrap;border-top:1px solid var(--tile-border-soft)}
.ps-t tbody th{text-align:left;font-weight:700;padding:6px 8px 6px 0;white-space:nowrap;border-top:1px solid var(--tile-border-soft);
  position:sticky;left:0;background:var(--tile)}
.ps-t thead th:first-child{left:0;z-index:1}
.ps-nm{display:block;font-size:12px}
.ps-pos{display:block;font-size:10px;font-weight:400;color:var(--text-2);letter-spacing:.04em}
.ps-team+.ps-team{margin-top:18px}
.ps-th{display:flex;align-items:center;gap:8px;padding:2px 0 6px}
.ps-th .pill{width:26px;height:8px}.ps-th .abbr{font-size:20px}
.ps-l{list-style:none;margin:0;padding:0}
.ps-l li{display:flex;align-items:center;gap:12px;padding:8px 0;border-top:1px solid var(--tile-border-soft)}
.ps-l li:first-child{border-top:0}
.ps-who{flex:1;min-width:0;display:grid;grid-template-columns:auto 1fr;column-gap:6px;align-items:baseline}
.ps-who .ps-nm{font-weight:700;font-size:15px}
.ps-who .ps-pos{font-size:11px}
.ps-sum{grid-column:1/-1;font-size:12px;color:var(--text-2);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ps-hl{text-align:right;flex:none}
.ps-hl b{display:block;font-size:22px;font-weight:700;line-height:1;font-variant-numeric:tabular-nums}
.ps-hl span{font-size:10px;font-weight:700;letter-spacing:.05em;color:var(--text-2)}
"""

JS = """
<script>function psMore(){document.querySelectorAll('.ps-tw').forEach(function(w){w.classList.toggle('more',w.scrollWidth>w.clientWidth+2&&w.scrollLeft+w.clientWidth<w.scrollWidth-2)})}
document.addEventListener('scroll',psMore,true);window.addEventListener('load',psMore);window.addEventListener('resize',psMore);
document.addEventListener('click',function(e){var b=e.target.closest('.ps-tab');if(!b)return;e.preventDefault();e.stopPropagation();
var c=b.closest('.card');c.querySelectorAll('.ps-tab').forEach(function(x){x.classList.toggle('on',x===b)});
c.querySelectorAll('.ps-pane').forEach(function(p){p.classList.toggle('on',p.dataset.team===b.dataset.team)});psMore();},true);
setInterval(psMore,500);</script>
"""


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: build_player_stats_mockup.py <scratch folder for the mock site>")
    out = sys.argv[1]
    if os.path.exists(out):
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    stats = season_stats()
    with open(os.path.join(SITE, "game", f"{GAME}.html"), encoding="utf-8") as f:
        page = f.read()
    start = page.index('<div class="p2" data-page="game-info"')
    end = page.index('<div class="p2 p2-team"', start)
    for v in ("v1", "v2", "v3"):
        html_v = page[:start] + layer(stats, v) + page[end:]
        html_v = re.sub(r"(<style id='p1-css'>.*?)(</style>)", lambda m: m.group(1) + CSS + m.group(2), html_v, count=1, flags=re.S)
        html_v = html_v.replace("</body>", JS + "</body>", 1)
        with open(os.path.join(out, "game", f"ps-{v}.html"), "w", encoding="utf-8") as f:
            f.write(html_v)
    print(f"Wrote {out}/game/ps-v1.html, ps-v2.html, ps-v3.html")


if __name__ == "__main__":
    main()

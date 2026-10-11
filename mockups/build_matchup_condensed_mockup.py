"""
Condensed view + the game's biggest matchup edge -- mockup (2026-10-11), NOT part of the live build.

SNAPSHOT: this was the design mockup. Jason picked option C; it now lives in the real build
(matchup.strip_html and MATCHUP_CSS, placed by render_page1), with "EPA" after the ranks, the line
kept together in the middle on wide screens, and the space budget re-tuned (a 760px floor on phones
under 760px tall). Kept for reference.

The condensed view (every card on one screen) has no Matchups card. Game Info is as tall as its two
lines, the team cards have a fixed share of the height, and Season Leaders takes the rest. The room
for anything new, measured with three injuries a team: Leaders has ~40px to spare at 375x812 (~17px
at 375x667, the page's 720px floor), its rows' gaps can close up ~18px, and the team cards can give
~10px everywhere (their text grows with the screen, so they have little more on tall phones). That's
~68px at 375x812 and ~37px on a short phone -- beyond it, the short phones' floor goes up.

What's shown: the single biggest edge in the game -- the largest EPA rank gap among both halves'
edges (matchup.py; Pass rush by sack rate) -- favored side first:

  A "Game Info line"   -- a third line in the Game Info card: bolt, the favored team's pill, what the
                          edge is, the two ranks. No new card. (~33px)
  C "One-line strip"   -- the same line as its own slim card between the team cards and Leaders, no
                          title pill. (~38px + the 8px gap; short phones' floor 732px)
  D "Track strip"      -- a slim card: the stat and "BAL O vs CLE D" on the left, the Page 1 chart's
                          1-32 track with the O and X on the right. (~52px + 8; short phones' floor 750px)

(B, the full "Matchups" card holding one row of the Page 1 chart, was ~96px -- too tall: Leaders lost
its last row even at 375x812.)

The injury report isn't out for the week used here, so each team card gets three made-up injuries
(copied from another game) to look like a normal week. Each variant is the real game page
(render_page1.write_all, its HTML patched), written into the folder given on the command line as
game/mu-<a|c|d>-<game id>.html. The strips are tappable like the expanded card (data-detail="matchup").
Nothing in the real build changes.

Run after a normal build (so site/ and data/ exist):
    py mockups/build_matchup_condensed_mockup.py <folder>     (site/ itself is fine: the files are new)
"""

import copy
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import helmets  # noqa: E402
import matchup as mu  # noqa: E402
import render_page1 as p1  # noqa: E402

GAMES = ["2026_06_BAL_CLE", "2026_06_CHI_ATL"]
INJURY_SOURCE = "2026_05_TB_DAL"   # three injuries a team, borrowed for the look of a normal week
esc = p1.esc
ORIG_COMPACT, ORIG_STANDALONE = p1.game_body_compact, p1.render_standalone

# what the edge is about: the favored side's unit, then the other team
OFF_WORDS = {"pass": "passing", "rb": "run game", "wr": "receivers", "te": "tight ends", "qb": "protection"}
DEF_WORDS = {"pass": "pass D", "rb": "run D", "wr": "coverage", "te": "TE coverage", "qb": "pass rush"}


def biggest(m):
    """(offense, defense, group) for the game's biggest edge -- the largest rank gap -- or None."""
    best = None
    for o, d, groups in (m or {}).get("halves", []):
        for g in groups:
            if g["edge"] and (best is None or abs(g["orr"] - g["drr"]) > abs(best[2]["orr"] - best[2]["drr"])):
                best = (o, d, g)
    return best


def line(o, d, g):
    """bolt, the favored team's pill, 'receivers vs CLE', '3rd vs 24th' (the favored side's rank first)."""
    words = f'{OFF_WORDS[g["key"]]} vs {d}' if g["edge"] == o else f'{DEF_WORDS[g["key"]]} vs {o}'
    a, b = (g["orr"], g["drr"]) if g["edge"] == o else (g["drr"], g["orr"])
    rk = lambda n: f'<b style="color:{p1.rank_color(n)}">{mu.ordinal(n)}</b>'
    return (f'<span class="mx-bolt">{mu.BOLT}</span>{helmets.pill_html(g["edge"])}'
            f'<span class="mx-t">{esc(words)}</span><span class="mx-r">{rk(a)} <span class="mx-vs">vs</span> {rk(b)}</span>')


# ---------------------------------------------------------------- A: a line in Game Info
def variant_a(d):
    out = ORIG_COMPACT(d)
    b = biggest(d.get("matchup"))
    return out + f'<div class="gc-mu mx-line">{line(*b)}</div>' if b else out


# ---------------------------------------------------------------- C, D: a strip before Leaders
def card_c(o, d, g):
    return (f'<a class="card c-mu c-mu-c mx-line" tabindex="0" data-detail="matchup" aria-label="Biggest matchup edge">'
            f'{line(o, d, g)}</a>')


def card_d(o, d, g):
    oc, dc = mu._colors(o, d)
    px = lambda rank: (rank - 1) / max(1, g["n"] - 1) * 100
    po, pd = px(g["orr"]), px(g["drr"])
    gap = oc if g["edge"] == o else dc
    marks = (f'<i class="mu-mk" style="left:{po:.1f}%">{mu.tie_mark(oc, dc)}</i>' if g["orr"] == g["drr"] else
             f'<i class="mu-mk mu-c" style="left:{pd:.1f}%;{dc}">{mu.X_MARK}</i><i class="mu-mk mu-c" style="left:{po:.1f}%;{oc}">{mu.O_MARK}</i>')
    return (f'<a class="card c-mu c-mu-d" tabindex="0" data-detail="matchup" aria-label="Biggest matchup edge">'
            f'<span class="mx-left"><span class="mx-nm">{esc(g["name"])}<span class="mx-bolt mu-c" style="{gap}">{mu.BOLT}</span></span>'
            f'<span class="mx-who"><b class="mu-c" style="{oc}">{esc(o)} O</b> <span class="mx-vs">vs</span> <b class="mu-c" style="{dc}">{esc(d)} D</b></span></span>'
            f'<span class="mu-line"><span class="mu-tk">1</span><span class="mu-track">'
            f'<i class="mu-gap mu-c" style="left:{min(po, pd):.1f}%;width:{abs(po - pd):.1f}%;{gap}"></i>{marks}'
            f'{mu._rank_labels(po, pd, g, oc, dc)}</span><span class="mu-tk">{g["n"]}</span></span></a>')


CARDS = {"c": card_c, "d": card_d}
VARIANT = {"tag": "a"}


def standalone(d):
    html = ORIG_STANDALONE(d)
    fn = CARDS.get(VARIANT["tag"])
    b = biggest(d.get("matchup"))
    if not fn or not b:
        return html
    at = html.index('<a class="card c-cmp"')
    return html[:at] + fn(*b) + html[at:]


TEAMS = "(max(100dvh, 720px) - var(--bar) - var(--bbar) - 48px) * 1.18 / 3.42"
CSS = f"""
/* where the height comes from: the team cards give 10px (never below the 184px they need on a short
   phone), the Leaders rows close up (gaps of 4-7px instead of 6-10px), and on short phones, where
   that isn't enough, the page's 720px floor goes up a little (those phones already scroll) */
.view-c:has(.gc-mu){{grid-template-rows:auto max(calc({TEAMS} - 10px),184px) minmax(0,1fr)}}
.view-c:has(>.c-mu-c){{grid-template-rows:auto max(calc({TEAMS} - 10px),184px) auto minmax(0,1fr);min-height:732px}}
.view-c:has(>.c-mu-d){{grid-template-rows:auto max(calc({TEAMS} - 10px),184px) auto minmax(0,1fr);min-height:750px}}
.view-c:has(.gc-mu,.c-mu) .c-cmp-in{{gap:clamp(4px,calc(2.4vh - 15px),14px)}}
.mx-bolt{{display:inline-block;flex:none;width:9px;height:12px;color:var(--aag-text-3)}}
.mx-bolt svg{{display:block;width:100%;height:100%}}
.mx-vs{{color:var(--aag-text-3);font-weight:400}}
.mx-line .tpill{{height:18px;min-width:44px;padding:0 5px;border-width:2px;font-size:10px;flex:none}}
/* A and C: one line */
.mx-line{{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:700;white-space:nowrap;min-width:0}}
.mx-t{{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}}
.mx-r{{flex:none;font-size:12.5px}}
.c-game .gc-mu{{margin-top:3px;padding-top:6px;border-top:1px solid var(--tile-border-soft)}}
a.card.c-mu-c{{display:flex;align-items:center;gap:7px;padding:9px 16px}}
/* D */
a.card.c-mu-d{{display:grid;grid-template-columns:auto 1fr;align-items:center;column-gap:12px;padding:6px 14px 16px}}
.mx-left{{display:flex;flex-direction:column;gap:2px;line-height:1.15}}
.mx-nm{{font-size:13px;font-weight:700;display:flex;align-items:center;gap:5px}}
.mx-nm .mx-bolt{{color:var(--c)}}
.mx-who{{font-size:10.5px;white-space:nowrap}}
.mx-who b{{color:var(--c)}}
.c-mu-d .mu-line{{margin:0}}
@media (max-width:340px){{ .mx-line{{gap:5px;font-size:12px}} .mx-r{{font-size:11.5px}} }}
"""


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: build_matchup_condensed_mockup.py <folder>")
    out = sys.argv[1]
    if not os.path.exists(out):
        shutil.copytree(os.path.join(ROOT, "site"), out)
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        data = json.load(f)
    src = data["game_details"][INJURY_SOURCE]
    games = {}
    for gid in GAMES:
        g = copy.deepcopy(data["game_details"][gid])
        for side in ("away", "home"):
            g[side]["injuries"] = src[side]["injuries"][:3]
            g[side]["injury_report_out"] = True
        games[gid] = g
    p1.P1_CSS += CSS
    p1.render_standalone = standalone
    for tag in ("base", "a", "c", "d"):
        VARIANT["tag"] = tag
        p1.game_body_compact = variant_a if tag == "a" else ORIG_COMPACT
        details = {f"mu-{tag}-{gid}": g for gid, g in games.items()}
        warnings = []
        p1.write_all(dict(data, game_details=details), out, warnings)
        if warnings:
            raise SystemExit("\n".join(warnings))
    print(f"Wrote {out}/game/mu-[base|a|c|d]-<game>.html for {', '.join(GAMES)}")


if __name__ == "__main__":
    main()

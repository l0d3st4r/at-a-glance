"""
A finished game's Matchups card (Page 1) -- three layouts, mockup (2026-10-11), NOT part of the live build.

SNAPSHOT: this was the design mockup. Jason picked C for Page 1 (with the bars in the team colors and
the EPA labeled) and A for Page 2; both now live in the real build (matchup._final_chart and
matchup._final_numbers), so running this script against the current code changes nothing the live
page doesn't already show for C. Kept for reference.

The card shows, for each offense against the other's defense, the one number from the game and how it
compares with each unit's season average (matchup.final_data). The live layout -- a bar from zero to
the game's number with an O and an X at the two averages, and two bare differences at the right --
doesn't say whose difference is whose, or why one is green and the other red (a defense allowing
"+.14" more than usual is red). All three options here say it the same way: each unit's difference
from its own point of view, ▲ better than its usual and ▼ worse, the arrow and the color agreeing.

  A "Table"            -- no bars: a column for the game, then one for each unit (PIT O, CLE D): ▲/▼
                          and the amount, its usual average under it.
  B "Bar, labeled"     -- the live bar, the differences at the right labeled with each unit's mark:
                          O ▲.52  X ▼.14.
  C "Vs average bars"  -- a small bar for each unit, centered on its own average: to the right (green)
                          when it did better than usual, to the left (red) when worse.

Each variant is the real game page (render_page1.write_all into a scratch copy, then the games below
copied into the folder given on the command line as game/mf-<a|b|c>-<game id>.html). Nothing in the
real build changes.

Run after a normal build (so site/ and data/ exist):
    py mockups/build_final_matchup_mockup.py <folder>     (site/ itself is fine: the files are new)
"""

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import helmets  # noqa: E402
import matchup as mu  # noqa: E402
import render_page1 as p1  # noqa: E402

GAMES = ["2026_04_PIT_CLE", "2026_03_PHI_CHI"]
esc = mu.esc
ORIG_BODY = mu.card_body
UP, DOWN, LEVEL = "▲", "▼", "="


def _f(g):
    return next(r[6] for r in mu.ROWS if r[0] == g["ekey"])


def verdict(g, side):
    """(arrow, amount, color, share) for one unit -- its difference from its own average, from its
    own point of view; None without an average."""
    avg = g["oa"] if side == "o" else g["da"]
    if avg is None:
        return None
    hb = next(r[5] for r in mu.ROWS if r[0] == g["ekey"])
    share = mu._share(g["ekey"], g["game"], avg, hb if side == "o" else not hb)
    amount = mu._fmt_diff(g["ekey"], abs(g["game"] - avg)).lstrip("+")
    capped = max(-1.0, min(1.0, share))
    color = mu._rank_color(round(16.5 - capped * 15.5))
    arrow = LEVEL if abs(share) < 0.03 else UP if share > 0 else DOWN
    return arrow, amount, color, capped


def chip(g, side):
    v = verdict(g, side)
    if not v:
        return '<span class="mf-v mf-na">–</span>'
    arrow, amount, color, _ = v
    return f'<span class="mf-v" style="color:{color}"><i>{arrow}</i>{esc(amount)}</span>'


def head(o, d, oc, dc):
    return (f'<div class="mu-blk-h"><span>{helmets.pill_html(o)} offense <i class="mu-lg mu-c" style="{oc}">{mu.O_MARK}</i></span>'
            f'<span class="mu-vs">vs</span><span>{helmets.pill_html(d)} defense <i class="mu-lg mu-c" style="{dc}">{mu.X_MARK}</i></span></div>')


def name(g, o, d, oc, dc):
    bar = oc if g["edge"] == o else dc if g["edge"] == d else "--lc:var(--aag-text-3);--dc:var(--aag-text-3)"
    return f'<span class="mf-nm">{esc(g["name"])}{mu._bolt(g, bar)}</span>'


# ---------------------------------------------------------------- A: a table
def chart_a(o, d, groups, oc, dc):
    rows = "".join(
        f'<div class="mf-a{" top" if g["top"] else ""}">{name(g, o, d, oc, dc)}<b class="mf-g">{esc(_f(g)(g["game"]))}</b>'
        f'<span class="mf-c">{chip(g, "o")}<small>avg {esc(_f(g)(g["oa"])) if g["oa"] is not None else "–"}</small></span>'
        f'<span class="mf-c">{chip(g, "d")}<small>avg {esc(_f(g)(g["da"])) if g["da"] is not None else "–"}</small></span></div>'
        for g in groups)
    cols = (f'<div class="mf-a mf-hd"><span></span><span>Game</span>'
            f'<span><i class="mu-lg mu-c" style="{oc}">{mu.O_MARK}</i>{esc(o)} O</span>'
            f'<span><i class="mu-lg mu-c" style="{dc}">{mu.X_MARK}</i>{esc(d)} D</span></div>')
    return f'<div class="mu-blk">{head(o, d, oc, dc)}{cols}{rows}</div>'


# ---------------------------------------------------------------- B: the live bar, the differences labeled
def chart_b(o, d, groups, oc, dc):
    html = mu._final_chart(o, d, groups, oc, dc)
    for g in groups:   # swap each row's bare differences for labeled ones
        od, dd = mu._diffs(g)
        old = (f'<span class="mu-fb-d"><span class="mu-c" style="{oc}">{od or "–"}</span>'
               f'<span class="mu-c" style="{dc}">{dd or "–"}</span></span>')
        new = (f'<span class="mf-b"><span><i class="mu-lg mu-c" style="{oc}">{mu.O_MARK}</i>{chip(g, "o")}</span>'
               f'<span><i class="mu-lg mu-c" style="{dc}">{mu.X_MARK}</i>{chip(g, "d")}</span></span>')
        html = html.replace(old, new, 1)
    return html


# ---------------------------------------------------------------- C: a bar for each unit, centered on its average
def chart_c(o, d, groups, oc, dc):
    def unit(g, side, c, mark):
        v = verdict(g, side)
        if not v:
            return f'<span class="mf-u"><i class="mu-lg mu-c" style="{c}">{mark}</i><span class="mf-tr"></span><span class="mf-v mf-na">–</span></span>'
        arrow, amount, color, share = v
        w = abs(share) * 50
        left = 50 if share >= 0 else 50 - w
        return (f'<span class="mf-u"><i class="mu-lg mu-c" style="{c}">{mark}</i><span class="mf-tr"><i class="mf-mid"></i>'
                f'<i class="mf-bar" style="left:{left:.1f}%;width:{w:.1f}%;background:{color}"></i></span>'
                f'<span class="mf-v" style="color:{color}"><i>{arrow}</i>{esc(amount)}</span></span>')
    rows = "".join(
        f'<div class="mf-cr{" top" if g["top"] else ""}"><span class="mf-l">{name(g, o, d, oc, dc)}<b class="mf-g">{esc(_f(g)(g["game"]))}</b></span>'
        f'<span class="mf-us">{unit(g, "o", oc, mu.O_MARK)}{unit(g, "d", dc, mu.X_MARK)}</span></div>'
        for g in groups)
    return f'<div class="mu-blk">{head(o, d, oc, dc)}{rows}</div>'


VARIANTS = {
    "a": (chart_a, "This game, and each unit vs its season average",
          '<div class="mu-fk"><span>▲ better than its average</span><span>▼ worse</span></div>'),
    "b": (chart_b, "This game vs each unit's season average",
          '<div class="mu-fk"><span><i class="mu-fk-b"></i>this game</span><span>O X its averages</span><span>▲ better ▼ worse</span></div>'),
    "c": (chart_c, "Each unit vs its own season average",
          '<div class="mu-fk"><span>| its average</span><span>▶ better</span><span>◀ worse</span></div>'),
}
STATE = {"tag": "a"}


def card_body(data):
    if not data or not data.get("final"):
        return ORIG_BODY(data)
    fn, sub, key = VARIANTS[STATE["tag"]]
    chart = "".join(fn(o, d, groups, *mu._colors(o, d)) for o, d, groups in data["halves"])
    return f'<div class="mu"><div class="mu-sub">{esc(sub)}</div>{key}{chart}</div>'


CSS = """
.mf-v{font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
.mf-v i{font-style:normal;font-size:.8em;margin-right:1px}
.mf-na{color:var(--aag-text-3)}
.mf-nm{position:relative;display:inline-flex;align-items:center;font-size:12px;font-weight:700;white-space:nowrap}
.mf-nm .mu-bolt{position:static;transform:none;margin-left:3px}
.mf-g{font-size:12.5px;font-variant-numeric:tabular-nums}
/* A */
.mf-a{display:grid;grid-template-columns:1fr 40px 72px 72px;align-items:center;column-gap:6px;padding:4px 0;border-top:1px solid var(--tile-border-soft)}
.mf-a.mf-hd{border-top:0;padding:0 0 2px;font-size:9.5px;font-weight:700;color:var(--aag-text-3);text-align:center}
.mf-a.mf-hd>span{display:inline-flex;align-items:center;justify-content:center;gap:3px}
.mf-a .mf-g{text-align:center}
.mf-c{display:flex;flex-direction:column;align-items:center;line-height:1.1}
.mf-c .mf-v{font-size:13px}
.mf-c small{font-size:9px;color:var(--aag-text-3)}
.mf-a.top{background:var(--tile-hover);border-radius:10px;border-top-color:transparent;margin:0 -8px;padding-left:8px;padding-right:8px}
/* B */
.mf-b{display:flex;gap:6px;justify-content:flex-end;font-size:10.5px}
.mf-b>span{display:inline-flex;align-items:center;gap:2px}
.mf-b .mu-lg{width:9px;height:9px}
.mu-fr:has(.mf-b){grid-template-columns:70px 1fr 32px auto}
/* C */
.mf-cr{display:grid;grid-template-columns:92px 1fr;align-items:center;column-gap:8px;padding:4px 0;border-top:1px solid var(--tile-border-soft)}
.mf-cr.top{background:var(--tile-hover);border-radius:10px;border-top-color:transparent;margin:0 -8px;padding-left:8px;padding-right:8px}
.mf-l{display:flex;flex-direction:column;line-height:1.15}
.mf-us{display:flex;flex-direction:column;gap:3px}
.mf-u{display:grid;grid-template-columns:10px 1fr 40px;align-items:center;column-gap:5px}
.mf-u .mu-lg{width:10px;height:10px}
.mf-tr{position:relative;height:6px;border-radius:2px;background:var(--tile-border-soft)}
.mf-mid{position:absolute;left:50%;top:-3px;bottom:-3px;width:1.5px;margin-left:-.75px;background:var(--aag-text-3)}
.mf-bar{position:absolute;top:0;bottom:0;border-radius:2px}
.mf-u .mf-v{font-size:11px;text-align:right}
@media (max-width:340px){ .mf-a{grid-template-columns:1fr 34px 62px 62px;column-gap:4px} .mf-cr{grid-template-columns:80px 1fr} }
"""


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: build_final_matchup_mockup.py <folder>")
    out = sys.argv[1]
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        data = json.load(f)
    mu.card_body = card_body
    mu.MATCHUP_CSS += CSS
    with tempfile.TemporaryDirectory() as tmp:
        for tag in VARIANTS:
            STATE["tag"] = tag
            # every game (a defense's averages come from its opponents), then only the ones shown are kept
            details = {gid: data["game_details"][gid] for gid in data["game_details"] if gid.startswith(("2026_01", "2026_02", "2026_03", "2026_04", "2026_05"))}
            warnings = []
            p1.write_all(dict(data, game_details=details), tmp, warnings)
            for gid in GAMES:
                shutil.copy(os.path.join(tmp, "game", f"{gid}.html"), os.path.join(out, "game", f"mf-{tag}-{gid}.html"))
    print(f"Wrote {out}/game/mf-[abc]-<game>.html for {', '.join(GAMES)}")


if __name__ == "__main__":
    main()

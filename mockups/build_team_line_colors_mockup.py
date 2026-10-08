"""
Race chart lines in team colors -- feasibility check + mockup (2026-10-07), NOT part of the live build.

Jason: can the Stat Leaders race chart color each line with the player's team colors, using a team's
secondary and tertiary colors when its first color is too close to a higher-ranked player's line?

How a line gets its color, separately for the light ground (#F3F3EE) and the dark one (#161510):
  * a team's candidates, in order: its pill fill, its pill ring (helmets.PILL_COLORS -- the colors Jason
    picked as each team's identity), then its helmet shell, facemask and ear piece (TEAM_COLORS,
    EAR_COLORS); a candidate within 8 of one already on the list is dropped as a repeat
  * players go in rank order, so the higher-ranked player gets first pick, and each takes his team's
    first candidate that passes all three checks:
      - visible:  WCAG contrast >= 2:1 against the ground (lines are 2px and every line is named at its
                  end, so the 3:1 graphics bar can relax to 2 -- the dataviz validator's "relief" band)
      - distinct: OKLab Delta E x100 >= 15 from every line already placed (the validator's
                  normal-vision floor -- a hard minimum)
      - color-blind safe: >= 6 under protanopia and deuteranopia (Machado 2009, severity 1) from every
                  line already placed (the validator's floor, allowed with direct labels; 8 is its target)
  * none passes -> "adjusted": the team's candidates mixed 15 / 30 / 45 / 60% toward white, then toward
    black, first that passes
  * still none -> "fallback": the ground's secondary text color, dashed

The color math is the dataviz skill's validator (scripts/validate_palette.js) ported line for line:
sRGB -> linear -> OKLab, Machado matrices, WCAG relative luminance.

Writes mockups/team-line-colors.html: the rules, then every race stat's current top 5 on both grounds
(chart + which color each line got and why), then hand-made edge cases. Run after build_data.py:
    python mockups/build_team_line_colors_mockup.py [out.html]
"""

import html
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import helmets  # noqa: E402
import render_leaders  # noqa: E402
import theme  # noqa: E402

LIGHT_BG, DARK_BG = "#F3F3EE", "#161510"
CONTRAST_FLOOR, NORMAL_FLOOR, CVD_FLOOR, CVD_TARGET = 2.0, 15.0, 6.0, 8.0
REPEAT = 8.0
MIXES = (0.15, 0.30, 0.45, 0.60)


def esc(v):
    return html.escape(str(v), quote=True)


# ---------------------------------------------------------------- color math (validate_palette.js, ported)

MACHADO = {
    "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def srgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def s2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin(h):
    return [s2lin(c) for c in srgb(h)]


def rel_lum(h):
    r, g, b = lin(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((rel_lum(a), rel_lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def oklab_from_lin(rgb):
    r, g, b = rgb
    l_ = math.copysign(abs(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3), 1)
    m_ = math.copysign(abs(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3), 1)
    s_ = math.copysign(abs(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3), 1)
    return [0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_]


def simulate(h, kind):
    r, g, b = lin(h)
    M = MACHADO[kind]
    return [max(0, min(1, M[i][0] * r + M[i][1] * g + M[i][2] * b)) for i in range(3)]


def delta_e(h1, h2, kind=None):
    a = oklab_from_lin(simulate(h1, kind) if kind else lin(h1))
    b = oklab_from_lin(simulate(h2, kind) if kind else lin(h2))
    return 100 * math.dist(a, b)


def cvd_de(h1, h2):
    return min(delta_e(h1, h2, "protan"), delta_e(h1, h2, "deutan"))


def mix(h, toward, amount):
    a, b = srgb(h), srgb(toward)
    return "#" + "".join(f"{round((x + (y - x) * amount) * 255):02X}" for x, y in zip(a, b))


# ---------------------------------------------------------------- the assignment

def candidates(team):
    """The team's colors in order of identity: pill fill, pill ring, helmet shell, facemask, ear."""
    fill, ring = helmets.PILL_COLORS.get(team, helmets.FALLBACK_COLORS)
    shell, mask = helmets.TEAM_COLORS.get(team, helmets.FALLBACK_COLORS)
    ear = helmets.EAR_COLORS.get(team, helmets.FALLBACK_EAR)
    out = []
    for name, c in (("pill fill", fill), ("pill ring", ring), ("helmet shell", shell), ("facemask", mask), ("ear", ear)):
        if all(delta_e(c, o) >= REPEAT for o, _n in out):
            out.append((c.upper(), name))
    return out


def check(c, bg, placed):
    """(passes, contrast, worst normal Delta E, worst color-blind Delta E) against the lines already placed."""
    con = contrast(c, bg)
    dn = min((delta_e(c, p["color"]) for p in placed), default=99)
    dc = min((cvd_de(c, p["color"]) for p in placed), default=99)
    return con >= CONTRAST_FLOOR and dn >= NORMAL_FLOOR and dc >= CVD_FLOOR, con, dn, dc


def assign(teams, bg):
    """teams in rank order -> [{team, color, source, kind, contrast, de, cvd, tried}]."""
    placed = []
    for team in teams:
        cands, tried, pick = candidates(team), [], None
        for c, name in cands:
            ok, con, dn, dc = check(c, bg, placed)
            tried.append((c, name, con, dn, dc, ok))
            if ok:
                pick = dict(color=c, source=name, kind="team", contrast=con, de=dn, cvd=dc)
                break
        if not pick:
            for c, name in cands:
                for toward, word in (("#FFFFFF", "lighter"), ("#000000", "darker")):
                    for amt in MIXES:
                        m = mix(c, toward, amt)
                        ok, con, dn, dc = check(m, bg, placed)
                        if ok:
                            pick = dict(color=m, source=f"{name}, {int(amt * 100)}% {word}", kind="adjusted",
                                        contrast=con, de=dn, cvd=dc)
                            break
                    if pick:
                        break
                if pick:
                    break
        if not pick:
            g = "#9C9B97" if bg == LIGHT_BG else "#8A8984"
            _ok, con, dn, dc = check(g, bg, placed)
            pick = dict(color=g, source="no team color works -- gray, dashed", kind="fallback", contrast=con, de=dn, cvd=dc)
        pick.update(team=team, tried=tried)
        placed.append(pick)
    return placed


# ---------------------------------------------------------------- drawing

W, H, PL, PR, PT, PB = 330, 140, 30, 64, 8, 18


def chart(series, picks, bg, dec):
    """series: [(label, [running totals by week])] in rank order."""
    n = len(series[0][1])
    hi = max(max(r) for _l, r in series) or 1
    fg2 = "rgba(22,21,16,.4)" if bg == LIGHT_BG else "rgba(243,243,238,.4)"
    fg = "#161510" if bg == LIGHT_BG else "#F3F3EE"
    grid = "rgba(22,21,16,.07)" if bg == LIGHT_BG else "rgba(243,243,238,.07)"
    x = lambda i: PL + (W - PL - PR) * i / max(1, n - 1)
    y = lambda v: PT + (H - PT - PB) * (1 - v / hi)
    out = []
    for t in (0, hi / 2, hi):
        out.append(f'<line x1="{PL}" x2="{W - PR}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{grid}"/>'
                   f'<text x="{PL - 6}" y="{y(t) + 3:.1f}" text-anchor="end" font-size="9" fill="{fg2}">{t:,.{dec}f}</text>')
    for i in range(n):
        out.append(f'<text x="{x(i):.1f}" y="{H - 4}" text-anchor="middle" font-size="9" fill="{fg2}">Wk {i + 1}</text>')
    ends = sorted((y(r[-1]), i) for i, (_l, r) in enumerate(series))
    placed, prev = {}, -99
    for ly, i in ends:
        placed[i] = max(ly, prev + 11)
        prev = placed[i]
    for i, ((label, run), p) in enumerate(zip(series, picks)):
        pts = " ".join(f"{x(j):.1f},{y(v):.1f}" for j, v in enumerate(run))
        dash = ' stroke-dasharray="4 3"' if p["kind"] == "fallback" else ""
        out.append(f'<polyline points="{pts}" fill="none" stroke="{p["color"]}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"{dash}/>'
                   f'<circle cx="{x(n - 1):.1f}" cy="{y(run[-1]):.1f}" r="4" fill="{p["color"]}" stroke="{bg}" stroke-width="2"/>'
                   f'<text x="{x(n - 1) + 8:.1f}" y="{placed[i] + 3:.1f}" font-size="10" font-weight="700" fill="{fg}">{esc(label)}</text>')
    return f'<svg viewBox="0 0 {W} {H}" class="race">{"".join(out)}</svg>'


def legend(rows, picks, bg):
    """rows: [(place, name, team)] -> one line each: swatch, pill, name, where the color came from, the numbers."""
    cls = "lt" if bg == LIGHT_BG else "dk"
    out = []
    for (place, name, team), p in zip(rows, picks):
        flag = {"team": "", "adjusted": ' <b class="adj">adjusted</b>', "fallback": ' <b class="fb">fallback</b>'}[p["kind"]]
        cvd_note = "" if p["cvd"] >= CVD_TARGET or p["cvd"] == 99 else ' <b class="adj">CVD under 8</b>'
        nums = (f'contrast {p["contrast"]:.1f}'
                + ("" if p["de"] == 99 else f' · ΔE {p["de"]:.0f} · CVD {p["cvd"]:.0f}'))
        skipped = [t for t in p["tried"] if not t[5]]
        why = ""
        if skipped:
            why = '<span class="why">skipped: ' + ", ".join(
                f'<i class="sw" style="background:{c}"></i>{esc(n)} ('
                + ("contrast " + f"{con:.1f}" if con < CONTRAST_FLOOR else ("ΔE " + f"{dn:.0f}" if dn < NORMAL_FLOOR else "CVD " + f"{dc:.0f}"))
                + ")" for c, n, con, dn, dc, _ok in skipped) + "</span>"
        out.append(f'<li><span class="pl">{place}</span><i class="sw line" style="background:{p["color"]}"></i>'
                   f'{helmets.pill_html(team, team)}<span class="who"><b>{esc(name)}</b>'
                   f'<span class="src">{esc(p["source"])}{flag}{cvd_note} · {nums}</span>{why}</span></li>')
    return f'<ol class="leg {cls}">{"".join(out)}</ol>'


def panel(title, series, rows, dec):
    teams = [t for _p, _n, t in rows]
    out = []
    for bg, word in ((LIGHT_BG, "Light"), (DARK_BG, "Dark")):
        picks = assign(teams, bg)
        out.append(f'<div class="pn {"lt" if bg == LIGHT_BG else "dk"}" style="background:{bg}"><div class="mode">{word}</div>'
                   f'{chart(series, picks, bg, dec)}{legend(rows, picks, bg)}</div>')
    return f'<section class="case"><h2>{esc(title)}</h2>{"".join(out)}</section>'


# ---------------------------------------------------------------- the page

EDGE = [
    ("Five blues", ["BUF", "NYG", "IND", "LAR", "DET"],
     "Every primary is blue -- the later teams have to fall back to their red, silver or gold."),
    ("Five reds", ["KC", "ARI", "SF", "ATL", "TB"], "Every team's identity color is red or near it."),
    ("Navy in the dark", ["CHI", "DEN", "SEA", "NE", "HOU"],
     "Navy pills nearly vanish on the dark ground -- each team has to lean on its orange / green / red / silver."),
    ("One team three times", ["DAL", "DAL", "DAL", "PHI", "NYG"],
     "Three Cowboys in the top 5 (receptions, say) -- they share one set of colors."),
    ("Greens", ["PHI", "NYJ", "GB", "SEA", "MIA"], "Midnight green, gang green, Packers green, action green, aqua."),
    ("Silver and black", ["LV", "PIT", "NO", "ATL", "CIN"], "Black pills and silver rings -- hard on both grounds."),
]


def fake_series(n_weeks, k=5):
    """Lines that bunch up, for the edge cases (only the colors matter there)."""
    return [[round((w + 1) * (60 - i * 4) + (i % 2) * 8 * w, 1) for w in range(n_weeks)] for i in range(k)]


def page():
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        data = json.load(f)
    d = render_leaders.build(data.get("player_weeks"))
    P = d["players"]
    real, summary = [], {"team": 0, "adjusted": 0, "fallback": 0, "cvd_under_target": 0, "lines": 0}
    for s in d["stats"]:
        if not s["race"] or not s["rows"]:
            continue
        top = s["rows"][:5]
        series = [(render_leaders.short(P[r[1]][1]).split(". ")[-1][:10], r[4]) for r in top]
        rows = [(r[0], P[r[1]][1], P[r[1]][3]) for r in top]
        real.append(panel(s["name"], series, rows, s["dec"]))
        for bg in (LIGHT_BG, DARK_BG):
            for p in assign([t for _a, _b, t in rows], bg):
                summary["lines"] += 1
                summary[p["kind"]] += 1
                summary["cvd_under_target"] += 1 if p["cvd"] != 99 and p["cvd"] < CVD_TARGET else 0
    edges = []
    for title, teams, note in EDGE:
        series = [(f"{t} {i + 1}", run) for i, (t, run) in enumerate(zip(teams, fake_series(max(2, d["through"]))))]
        rows = [(i + 1, f"{t} player {i + 1}", t) for i, t in enumerate(teams)]
        edges.append(panel(title, series, rows, 0).replace("</h2>", f'</h2><p class="note">{esc(note)}</p>', 1))
        for bg in (LIGHT_BG, DARK_BG):
            for p in assign(teams, bg):
                summary.setdefault("edge_" + p["kind"], 0)
                summary["edge_" + p["kind"]] += 1
    rules = (
        '<section class="rules"><h1>Race lines in team colors</h1><p>Each line takes its player\'s team colors, in this order: '
        'pill fill, pill ring, helmet shell, facemask, ear piece. Players go in rank order, so the higher-ranked player picks first. '
        'A color is used only if it is <b>visible</b> (2:1 contrast on that ground), <b>distinct</b> (ΔE ≥ 15 from every line above it) '
        'and <b>color-blind safe</b> (≥ 6 under red-green color blindness; 8 is the target). If none of a team\'s colors pass, '
        'a lighter or darker shade of one is tried (<b class="adj">adjusted</b>), then a gray dashed line (<b class="fb">fallback</b>). '
        'Each card shows both grounds, and under each player which colors were skipped and why.</p>'
        f'<p class="tot">Today\'s top 5s, {summary["lines"]} lines across both grounds: {summary["team"]} straight team colors, '
        f'{summary["adjusted"]} adjusted shades, {summary["fallback"]} fallbacks; {summary["cvd_under_target"]} pass color-blind '
        'checks only in the 6–8 floor band.</p></section>')
    css = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,system-ui,sans-serif;background:var(--aag-bg);color:var(--aag-text);-webkit-font-smoothing:antialiased;padding:12px 12px 40px}
.wrap{max-width:720px;margin:0 auto}
h1{font-size:18px;font-weight:900;margin-bottom:6px}
h2{font-size:14px;font-weight:900;letter-spacing:.06em;text-transform:uppercase;margin:22px 0 6px}
h3{font-size:12px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;margin:26px 0 0;color:var(--aag-text-2)}
.rules p{font-size:12px;line-height:1.45;color:var(--aag-text-2);margin-bottom:6px}
.rules .tot{color:var(--aag-text);font-weight:600}
.note{font-size:11px;color:var(--aag-text-2);margin:-2px 0 6px}
.adj{color:#B07600}.fb{color:#C0392B}
.case{margin-bottom:6px}
.pn{border-radius:12px;padding:8px 10px 6px;margin-bottom:6px}
.pn.lt{color:#161510}.pn.dk{color:#F3F3EE}
.mode{font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;opacity:.5}
.race{width:100%;height:auto;display:block;overflow:visible}
.leg{list-style:none;margin-top:4px}
.leg li{display:grid;grid-template-columns:14px 16px 36px minmax(0,1fr);gap:6px;align-items:start;padding:4px 0;font-size:11px;
  border-top:1px solid rgba(128,128,128,.18)}
.pl{font-weight:700;opacity:.5;text-align:right;padding-top:2px}
.sw{display:inline-block;width:10px;height:10px;border-radius:3px;vertical-align:-1px;margin-right:3px}
.sw.line{width:16px;height:4px;border-radius:2px;margin-top:7px}
.tpill{display:inline-flex;align-items:center;justify-content:center;height:16px;min-width:36px;padding:0 4px;border-radius:999px;
  border:2px solid transparent;color:var(--pl);font-size:9px;white-space:nowrap;margin-top:1px;
  background:linear-gradient(var(--pf1),var(--pf2)) padding-box,linear-gradient(var(--pr1),var(--pr2)) border-box}
.abbr{line-height:1;font-family:Saira,Inter,sans-serif;font-weight:800;font-style:italic}
.who b{font-size:12px}
.src,.why{display:block;font-size:10px;opacity:.7;margin-top:1px}
.why{opacity:.6}
@media (min-width:700px){.case{display:grid;grid-template-columns:1fr 1fr;column-gap:10px}.case h2,.case .note{grid-column:1/-1}}
"""
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Race lines in team colors</title><script>{theme.THEME_HEAD_JS}</script>"
            "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=Saira:ital,wdth,wght@1,95,800&display=swap' rel='stylesheet'>"
            f"<style>{theme.THEME_CSS}{css}</style></head><body><div class='wrap'>{rules}"
            f"<h3>Today's leaders</h3>{''.join(real)}<h3>Edge cases</h3>{''.join(edges)}</div></body></html>"), summary


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mockups", "team-line-colors.html")
    html_, summary = page()
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_)
    print(f"Wrote {out}")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

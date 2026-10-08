"""
Stat Leaders page mockup, round 3 (2026-10-07) -- NOT part of the live build. Expanded view, then
(further down) the condensed view on the +/- toggle.

Jason (2026-10-07): the expanded view should work like Player Stats' expanded view -- one card per
category (Passing, Rushing, Receiving, Defense, Kicking, Returns) in a deck that snaps up / down, the
category icons down the right side as its nav, the slivers of the cards above and below named like
every other deck on the site. Inside a card, swipe left / right between that category's stats
(Passing: Pass Yds, Pass TD, Y/A), with small tabs under the title saying which one is showing.

Each stat is a hybrid of round 2's E ("The race") and B ("One stat deep"):
  * on top, the race: the top 5's running totals week by week (FG long the longest so far), each line
    named at its end, a crosshair + tooltip on touch -- not for the averages (Y/A, Y/C, punt average,
    kick / punt return averages), whose list fills the card (Jason, 2026-10-07)
  * under it, the ranked list: place, helmet, name, and the number, with a faint bar behind the row
    as long as the number (from zero) -- so the gaps show, as in B -- and the rest of the player's
    stat line on a small second line (passing: C/A, TD, INT, Y/A, SK ...), so the full stats are there.
    The chart's five carry their line's color by the place number. The list scrolls inside the card
    and grows with "Show 10 more" (to each stat's top 100), like round 2.

Each row names the team with its pill (Jason, 2026-10-07: "how would this look with the team pills
instead of the abbreviation and helmet") -- a mockup-only switch in the top-left corner flips back to
helmet + abbreviation to compare.

Data, qualifiers and the race palette are round 2's (build_stat_leaders_v2_mockup.build_data), except
Returns: kick and punt return averages (at least one return a team game) in place of return yards.

Run after build_data.py (needs data/matchups.json):
    python mockups/build_stat_leaders_v3_mockup.py [out.html]
Writes mockups/stat-leaders-3.html. #defense opens on that card, #defense-2 on its third stat,
#condensed on the condensed view.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import build_stat_leaders_v2_mockup as v2  # noqa: E402
import helmets  # noqa: E402
import theme  # noqa: E402
from divisions import DIVISIONS  # noqa: E402
from render_page1 import CHEV, DOWN, MINUS, PLUS, UP  # noqa: E402

SEASON = 2026
esc = v2.esc

CSS = """
:root{--bbar:""" + theme.BBAR_HEIGHT + """;--text:var(--aag-text);--text-2:var(--aag-text-2);--text-3:var(--aag-text-3);
  --line:var(--aag-tile-border);--line-soft:var(--aag-tile-border-soft);--gold:#D4A20A;--silver:#A2A7AD;--bronze:#B5702F;
  --peek:40px;--gap:12px;--col:600px;--top-h:72px;
  --s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181}}
:root[data-theme=dark]{--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;background:var(--aag-bg)}
body{color:var(--text);font-family:Inter,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
button{font:inherit;color:inherit}
.abbr{line-height:1;font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;font-style:italic;font-variation-settings:'wdth' 95;letter-spacing:.02em}
.hl{display:inline-block;flex:none;vertical-align:middle;background-position:center;background-size:contain;background-repeat:no-repeat}
.t-ic{display:inline-flex;align-items:center;flex:none}
.t-ic svg{display:block;width:auto;height:1em}

/* the header: the year over "STAT LEADERS · Through Week N" */
.top{display:flex;flex-direction:column;align-items:center;gap:2px;padding:max(10px,env(safe-area-inset-top)) 16px 6px;height:var(--top-h)}
.yr{font-size:34px}
.rs-line{display:flex;gap:6px;align-items:baseline;font-size:11px;white-space:nowrap}
.rs{letter-spacing:.12em;text-transform:uppercase;color:var(--text-2);font-weight:700}
.thru{color:var(--text-3)}
.thru::before{content:"·";margin-right:6px}

/* the deck: one category card in the middle, slivers of its neighbours above and below (Page 1's deck) */
.deck{height:calc(100dvh - var(--top-h) - var(--bbar));overflow-y:auto;scroll-snap-type:y mandatory;
  padding:calc(var(--peek) + var(--gap)) 0;scrollbar-width:none;overscroll-behavior-y:contain}
.deck::-webkit-scrollbar{display:none}
.slot{height:100%;max-width:var(--col);margin:0 auto var(--gap);padding:0 28px 0 16px;
  scroll-snap-align:center;scroll-snap-stop:always}
.slot:last-child{margin-bottom:0}
.card{position:relative;height:100%;display:flex;flex-direction:column;transition:transform .2s cubic-bezier(.22,1,.36,1)}
.slot:not(.active) .card{transform:scale(.96)}
.slot.below .card{transform:translateY(-2%) scale(.96)}
.slot.above .card{transform:translateY(2%) scale(.96)}
.body{flex:1;min-height:0;display:flex;flex-direction:column;transition:opacity .15s}
.slot:not(.active) .body{opacity:0}
.peek{display:flex;align-items:center;justify-content:center;gap:7px;font-size:11px;font-weight:700;letter-spacing:.12em;
  text-transform:uppercase;color:var(--text-2);height:calc(var(--peek) - 1px);flex:none}
.peek-top{position:relative}
.peek-bot{position:absolute;left:0;right:0;bottom:0;opacity:0;pointer-events:none}
.slot.above .peek-bot{opacity:1}
.slot.above .peek-top{opacity:0}
.peek-top>svg{display:none}
.slot.below .peek-top>svg{display:block}
.slot.active .peek-top{font-size:13px;color:var(--text)}
.ttl{display:inline-flex;align-items:center;gap:6px}
.slot.active .peek-top .ttl{border:1px solid var(--line);border-radius:999px;padding:4px calc(11px - .12em) 4px 11px;line-height:1.1}

/* the category icons down the right side (Page 1 / Page 2's .ic-dots) */
.ic-dots{position:fixed;right:calc((max(0px, 50% - var(--col) / 2) + 8px) / 2);top:calc(var(--top-h) + (100dvh - var(--top-h) - var(--bbar)) / 2);
  transform:translateY(-50%);z-index:10;display:flex;flex-direction:column;align-items:center;gap:36px}
.dot{width:20px;height:20px;border:0;background:none;opacity:.4;display:flex;align-items:center;justify-content:center;cursor:pointer;padding:0;transition:opacity .2s}
.dot svg{display:block;width:20px;height:auto;color:var(--text);transition:transform .2s}
.dot.on{opacity:1}.dot.on svg{transform:scale(1.15)}
.dot:not(.on):hover{opacity:.7}

/* inside a card: the stat tabs, then the stats side by side (swipe left / right) */
.tabs{display:flex;justify-content:center;gap:2px;flex:none;margin:2px 0 4px;overflow-x:auto;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab{background:none;border:1px solid transparent;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:700;opacity:.45;cursor:pointer;white-space:nowrap}
.tab.on{opacity:1;border-color:var(--line)}
.strack{flex:1;min-height:0;display:flex;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;scrollbar-width:none;overscroll-behavior-x:contain}
.strack::-webkit-scrollbar{display:none}
.stat{flex:0 0 100%;min-width:0;scroll-snap-align:start;scroll-snap-stop:always;display:flex;flex-direction:column}
.qual{text-align:center;font-size:10px;color:var(--text-3);flex:none;height:13px}

/* the race */
.e-chart{position:relative;flex:none}
.race{width:100%;height:auto;display:block;overflow:visible}
.gl{stroke:var(--line-soft);stroke-width:1}
.ax{font-size:9px;fill:var(--text-3)}
.ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.dt{stroke:var(--aag-bg);stroke-width:2}
.lb{font-size:10px;font-weight:700;fill:var(--text)}
.s1{stroke:var(--s1)}.s2{stroke:var(--s2)}.s3{stroke:var(--s3)}.s4{stroke:var(--s4)}.s5{stroke:var(--s5)}
circle.s1{fill:var(--s1)}circle.s2{fill:var(--s2)}circle.s3{fill:var(--s3)}circle.s4{fill:var(--s4)}circle.s5{fill:var(--s5)}
.xh{stroke:var(--text-3);stroke-width:1;stroke-dasharray:2 3;opacity:0}
.race.hover .xh{opacity:1}
.tip{position:absolute;top:0;pointer-events:none;background:var(--aag-bg);border:1px solid var(--line);border-radius:8px;
  padding:5px 8px;font-size:11px;box-shadow:0 4px 14px rgba(0,0,0,.15);white-space:nowrap;z-index:2}
.tip b{display:block;margin-bottom:2px}

/* the ranked list: a faint bar behind each row, as long as the number */
.list{flex:1;min-height:0;overflow-y:auto;margin-top:4px;scrollbar-width:none}
.list::-webkit-scrollbar{display:none}
.list ol{list-style:none}
/* who's who: the team pill (body[data-id=pills], the default) or helmet + abbreviation -- the mockup's
   corner switch flips them. --lead is where a row's bar starts (after the place and the team) */
body{--id-w:44px;--lead:76px}
body[data-id=helmets]{--id-w:20px;--lead:52px}
body[data-id=pills] .id-h,body[data-id=helmets] .id-p{display:none}
.id{display:flex;align-items:center}
.tpill{display:inline-flex;align-items:center;justify-content:center;height:18px;min-width:44px;padding:0 5px;border-radius:999px;
  border:2px solid transparent;color:var(--pl);font-size:10px;white-space:nowrap;
  background:linear-gradient(var(--pf1),var(--pf2)) padding-box,linear-gradient(var(--pr1),var(--pr2)) border-box}
.idsw{position:fixed;left:8px;top:max(8px,env(safe-area-inset-top));z-index:30;display:flex;gap:2px;font-size:10px;
  border:1px dashed var(--line);border-radius:999px;padding:2px;background:var(--aag-bg)}
.idsw button{background:none;border:0;border-radius:999px;padding:2px 8px;cursor:pointer;color:var(--text-3);font-weight:700}
.idsw button.on{background:var(--text);color:var(--aag-bg)}
.list li{position:relative;display:grid;grid-template-columns:20px var(--id-w) minmax(0,1fr) 46px;gap:6px;align-items:center;
  padding:5px 4px;border-bottom:1px solid var(--line-soft)}
.list li:last-child{border-bottom:0}
.list .fill{position:absolute;left:var(--lead);top:3px;bottom:3px;background:var(--aag-tile-hover);border-radius:0 4px 4px 0;z-index:0}
.list li>*:not(.fill){position:relative;z-index:1}
.pl{font-size:11px;font-weight:700;color:var(--text-3);text-align:right;font-variant-numeric:tabular-nums}
.pk{display:inline-block;padding-bottom:1px;border-bottom:3px solid transparent}
.pk.c1{border-color:var(--s1)}.pk.c2{border-color:var(--s2)}.pk.c3{border-color:var(--s3)}.pk.c4{border-color:var(--s4)}.pk.c5{border-color:var(--s5)}
.who{min-width:0}
.nm{display:block;font-size:13px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nm .abbr{font-size:11px;color:var(--text-2);margin-left:4px}
/* the rest of the stat line wraps to a second line rather than losing its end (a long passing line) --
   whole stats at a time, the two lines balanced */
.ln2{display:block;font-size:10px;line-height:1.3;color:var(--text-3);font-variant-numeric:tabular-nums;text-wrap:balance}
.ln2 .it{white-space:nowrap}
.ln2 b{font-weight:700;color:var(--text-2)}
.v{font-variant-numeric:tabular-nums;font-weight:700;text-align:right;font-size:14px}
.more-row{display:flex;justify-content:center;align-items:center;gap:10px;padding:8px 0 4px}
.more{background:none;border:1px solid var(--line);border-radius:999px;padding:4px 12px;font-size:12px;font-weight:700;cursor:pointer}
.cnt{font-size:10px;color:var(--text-3)}

/* CONDENSED (body[data-view=condensed], the +/- toggle): round 2's "At a glance" tiles, as Jason liked them
   in its expanded view -- two a row, each stat's icon, name and leading number over its leader: the small
   pill and the full name (up to three tied for first).
   All 21 share the screen between the header and the bottom bar, the way the site's condensed views
   fit one screen; on a phone too short for that they keep a minimum height and the grid scrolls.
   Tapping a tile opens the expanded view at that category's card, turned to that stat. */
.cview{display:none;height:calc(100dvh - var(--top-h) - var(--bbar));max-width:var(--col);margin:0 auto;padding:4px 16px 8px;
  overflow-y:auto;grid-template-columns:1fr 1fr;grid-auto-rows:minmax(55px,1fr);gap:4px;scrollbar-width:none}
.cview::-webkit-scrollbar{display:none}
body[data-view=condensed] .cview{display:grid}
body[data-view=condensed] .deck,body[data-view=condensed] .ic-dots{display:none}
.ct{display:flex;flex-direction:column;justify-content:center;gap:1px;min-width:0;text-align:left;background:var(--aag-tile-hover);
  border:0;border-radius:10px;padding:2px 7px;cursor:pointer}
.ct-l{display:flex;align-items:center;gap:4px;font-size:9.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2)}
.ct-s{flex:1;min-width:0}
.ct-v{font-family:Teko,Inter,sans-serif;font-size:19px;line-height:.9;font-weight:600;letter-spacing:0;color:var(--text)}
.ct-more{display:block;font-size:9.5px;color:var(--text-3)}
.ct ol{list-style:none}
.ct li{display:grid;grid-template-columns:30px minmax(0,1fr);gap:5px;align-items:center;font-size:11px;line-height:14px}
.ct .pl{font-size:9px}
.ct .pk{border-bottom-width:2px;padding-bottom:0}
.pk.m1{border-color:var(--gold)}.pk.m2{border-color:var(--silver)}.pk.m3{border-color:var(--bronze)}
.ct .tpill{height:12px;min-width:30px;padding:0 3px;border-width:1.5px;font-size:7.5px}
.ct .nm{font-size:11.5px;font-weight:600}
.ct .v{font-size:11px}
.toggle{position:absolute;right:16px;top:9px;width:34px;height:34px;border:0;background:none;padding:0;display:flex;
  align-items:center;justify-content:center;cursor:pointer;color:var(--text)}
.toggle .i-plus{display:none}
body[data-view=condensed] .toggle .i-plus{display:block}
body[data-view=condensed] .toggle .i-minus{display:none}

/* bottom bar: menu left, back pill middle, +/- right */
.bottombar{position:fixed;left:0;right:0;bottom:0;z-index:16;height:var(--bbar);padding-bottom:env(safe-area-inset-bottom);
  background:var(--aag-bar-bg);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.bar-in{position:relative;max-width:600px;height:52px;margin:0 auto;display:flex;align-items:flex-start;justify-content:center;padding-top:10px}
.week{color:inherit;text-decoration:none;display:inline-flex;align-items:center;gap:6px;font-size:16px;line-height:19px;padding:6px 12px}
.week .chev{width:12px;height:12px}
@media (min-width:780px){
  .ic-dots{right:calc(50% - var(--col) / 2 + 16px - 24px - 48px);gap:28px}
  .dot{width:48px;height:48px}.dot svg{width:44px}
}
@media (max-width:779.98px){.slot{padding-right:28px}}
""" + theme.MENU_CSS + theme.HELMET_SHADOW_CSS

JS = r"""
(function () {
  var D = JSON.parse(document.getElementById('data').textContent), P = D.players, S = {};
  D.stats.forEach(function (s) { S[s.key] = s; });
  var deck = document.querySelector('.deck'), slots = [].slice.call(deck.querySelectorAll('.slot')),
      dots = [].slice.call(document.querySelectorAll('.dot')), active = -1, shown = {};
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function helmet(team, n) { n = n || 18; return '<i class="hm hl h-' + team + '" style="--hs:' + n + 'px;width:' + n + 'px;height:' + n + 'px"></i>'; }
  function num(t) { return parseFloat(String(t).replace(/,/g, '')) || 0; }
  function fmt(s, v) { return s.dec ? v.toFixed(1) : Math.round(v).toLocaleString(); }

  // a line's end label: the last name, no Jr. / Sr. / II, short enough to stay inside the chart
  function endName(nm) { return nm.split('. ').pop().replace(/\s+(Jr\.?|Sr\.?|II|III|IV|V)$/, '').slice(0, 10); }
  // ---- the race (round 2's E)
  var W = 330, H = 150, PL = 30, PR = 62, PT = 8, PB = 18;
  function chart(s) {
    var top = s.rows.slice(0, 5), n = D.through, hi = 0, lo = Infinity;
    top.forEach(function (r) { r[4].forEach(function (v) { hi = Math.max(hi, v); }); });
    hi = hi || 1;
    var x = function (i) { return PL + (W - PL - PR) * i / Math.max(1, n - 1); }, y = function (v) { return PT + (H - PT - PB) * (1 - v / hi); };
    var g = [0, hi / 2, hi].map(function (t) { return '<line class="gl" x1="' + PL + '" x2="' + (W - PR) + '" y1="' + y(t) + '" y2="' + y(t) + '"/><text class="ax" x="' + (PL - 6) + '" y="' + (y(t) + 3) + '" text-anchor="end">' + fmt(s, t) + '</text>'; }).join('');
    for (var i = 0; i < n; i++) g += '<text class="ax" x="' + x(i) + '" y="' + (H - 4) + '" text-anchor="middle">Wk ' + (i + 1) + '</text>';
    var ends = top.map(function (r, i) { return [y(r[4][n - 1]), i]; }).sort(function (a, b) { return a[0] - b[0]; }), placed = {}, last = -99;
    ends.forEach(function (e) { var ly = Math.max(e[0], last + 11); placed[e[1]] = ly; last = ly; });
    var lines = top.map(function (r, i) {
      return '<polyline class="ln s' + (i + 1) + '" points="' + r[4].map(function (v, j) { return x(j) + ',' + y(v); }).join(' ') + '"/>'
        + '<circle class="dt s' + (i + 1) + '" cx="' + x(n - 1) + '" cy="' + y(r[4][n - 1]) + '" r="4"/>'
        + '<text class="lb" x="' + (x(n - 1) + 8) + '" y="' + (placed[i] + 3) + '">' + esc(endName(P[r[1]][0])) + '</text>';
    }).join('');
    return '<div class="e-chart"><svg class="race" viewBox="0 0 ' + W + ' ' + H + '" data-stat="' + s.key + '" role="img" aria-label="' + esc(s.name)
      + ': running totals by week for the top five">' + g + lines + '<line class="xh" y1="' + PT + '" y2="' + (H - PB) + '"/></svg><div class="tip" hidden></div></div>';
  }
  // ---- the ranked list (round 2's B), each row's full stat line on a second line
  function line2(s, r) {
    return D.lines[s.line].map(function (c, i) { return i === s.col ? '' : '<span class="it">' + c + ' <b>' + r[3][i] + '</b></span>'; }).filter(Boolean).join(' · ');
  }
  function list(s) {
    var n = shown[s.key] || (shown[s.key] = 10), hi = num(s.rows[0][2]), total = s.rows.length;
    var rows = s.rows.slice(0, n).map(function (r, i) {
      var p = P[r[1]], w = Math.max(1, num(r[2]) / hi * 100);
      return '<li title="' + esc(p[1]) + ' (' + p[3] + '): ' + r[2] + '"><span class="fill" style="width:calc((100% - var(--lead)) * ' + (w / 100).toFixed(3) + ')"></span>'
        + '<span class="pl"><span class="pk' + (s.race && i < 5 ? ' c' + (i + 1) : '') + '">' + r[0] + '</span></span>'
        + '<span class="id"><span class="id-h">' + helmet(p[3]) + '</span><span class="id-p">' + D.pills[p[3]] + '</span></span>'
        + '<span class="who"><span class="nm">' + esc(p[0]) + '<span class="abbr id-h">' + p[3] + '</span></span><span class="ln2">' + line2(s, r) + '</span></span>'
        + '<span class="v">' + r[2] + '</span></li>';
    }).join('');
    var ctl = total > 10 ? '<div class="more-row">' + (n < total ? '<button class="more" data-more="' + s.key + '">Show ' + Math.min(10, total - n) + ' more</button>' : '')
      + (n > 10 ? '<button class="more" data-fewer="' + s.key + '">Show fewer</button>' : '')
      + '<span class="cnt">' + Math.min(n, total) + ' of ' + total + (s.count > total ? ' (top ' + total + ' of ' + s.count + ')' : '') + '</span></div>' : '';
    return '<ol>' + rows + '</ol>' + ctl;
  }
  function drawStat(el) {
    var s = S[el.getAttribute('data-stat')];
    // averages have no race chart (Jason, 2026-10-07) -- their list gets the whole card
    el.innerHTML = '<div class="qual">' + (s.qual || '') + '</div>' + (s.race ? chart(s) : '') + '<div class="list">' + list(s) + '</div>';
    if (s.race) hook(el.querySelector('.race'));
  }
  function hook(svg) {
    var s = S[svg.getAttribute('data-stat')], top = s.rows.slice(0, 5), n = D.through, tip = svg.parentNode.querySelector('.tip'), xh = svg.querySelector('.xh');
    function show(ev) {
      var b = svg.getBoundingClientRect(), px = (ev.clientX - b.left) / b.width * W,
          i = Math.max(0, Math.min(n - 1, Math.round((px - PL) / ((W - PL - PR) / Math.max(1, n - 1))))), x = PL + (W - PL - PR) * i / Math.max(1, n - 1);
      xh.setAttribute('x1', x); xh.setAttribute('x2', x); svg.classList.add('hover');
      tip.innerHTML = '<b>Through week ' + (i + 1) + '</b>' + top.map(function (r) { return esc(P[r[1]][0]) + ' &nbsp;' + fmt(s, r[4][i]); }).join('<br>');
      tip.hidden = false;
      var left = x / W * b.width + 10; if (left + 150 > b.width) left = x / W * b.width - 160; tip.style.left = left + 'px';
    }
    svg.addEventListener('pointermove', show); svg.addEventListener('pointerdown', show);
    svg.addEventListener('pointerleave', function () { svg.classList.remove('hover'); tip.hidden = true; });
  }
  document.querySelectorAll('.stat').forEach(drawStat);

  // ---- the deck: which card is in the middle, its neighbours as slivers, the icons following
  function setActive(i) {
    if (i === active) return;
    active = i;
    slots.forEach(function (s, k) { s.classList.toggle('active', k === i); s.classList.toggle('above', k < i); s.classList.toggle('below', k > i); });
    dots.forEach(function (d, k) { d.classList.toggle('on', k === i); });
  }
  function current() {
    var mid = deck.scrollTop + deck.clientHeight / 2, best = 0, bd = Infinity;
    slots.forEach(function (s, k) { var c = s.offsetTop + s.offsetHeight / 2 - deck.offsetTop, d = Math.abs(c - mid); if (d < bd) { bd = d; best = k; } });
    return best;
  }
  function go(i, smooth) {
    var s = slots[i]; if (!s) return;
    deck.scrollTo({ top: s.offsetTop - deck.offsetTop - (deck.clientHeight - s.offsetHeight) / 2, behavior: smooth ? 'smooth' : 'auto' });
  }
  var tick = false;
  deck.addEventListener('scroll', function () { if (!tick) { tick = true; requestAnimationFrame(function () { setActive(current()); tick = false; }); } }, { passive: true });
  dots.forEach(function (d, k) { d.addEventListener('click', function () { go(k, true); }); });
  slots.forEach(function (s, k) { s.querySelector('.card').addEventListener('click', function (e) { if (k !== active && !e.target.closest('button')) go(k, true); }); });

  // ---- inside a card: tabs and the sideways swipe between its stats
  function tabsFollow(card) {
    var tr = card.querySelector('.strack'), i = Math.round(tr.scrollLeft / tr.clientWidth);
    card.querySelectorAll('.tab').forEach(function (t, k) { t.classList.toggle('on', k === i); });
  }
  document.querySelectorAll('.card').forEach(function (card) {
    var tr = card.querySelector('.strack'), settle;
    tr.addEventListener('scroll', function () { clearTimeout(settle); settle = setTimeout(function () { tabsFollow(card); }, 80); }, { passive: true });
  });
  document.addEventListener('click', function (e) {
    var t;
    if ((t = e.target.closest('.tab'))) {
      var tr = t.closest('.card').querySelector('.strack');
      tr.scrollTo({ left: +t.getAttribute('data-i') * tr.clientWidth, behavior: 'smooth' }); return;
    }
    if ((t = e.target.closest('[data-more]'))) { var k = t.getAttribute('data-more'); shown[k] += 10; redraw(k); return; }
    if ((t = e.target.closest('[data-fewer]'))) { var k2 = t.getAttribute('data-fewer'); shown[k2] = 10; redraw(k2); return; }
  });
  document.querySelectorAll('[data-id-pick]').forEach(function (b) {
    b.addEventListener('click', function () {
      document.body.setAttribute('data-id', b.getAttribute('data-id-pick'));
      document.querySelectorAll('[data-id-pick]').forEach(function (x) { x.classList.toggle('on', x === b); });
    });
  });
  function redraw(k) {
    var el = document.querySelector('.stat[data-stat="' + k + '"]'), l = el.querySelector('.list'), y = l.scrollTop;
    l.innerHTML = list(S[k]); l.scrollTop = y;
  }

  // ---- condensed: every stat's top 3 in a tile
  var cv = document.querySelector('.cview');
  // first place only (Jason, 2026-10-07) -- up to three when they're tied, "+N more tied" past that. Tied
  // leaders share the number, so it sits on the title line and each row is just the pill + full name.
  cv.innerHTML = D.stats.map(function (s) {
    var first = s.rows.filter(function (r) { return r[0] === 1; }), extra = first.length - 3;
    return '<button class="ct" type="button" data-open="' + s.key + '"><span class="ct-l"><span class="t-ic">' + (D.icons[s.cat] || '') + '</span>'
      + '<span class="ct-s">' + esc(s.short) + '</span><span class="ct-v">' + first[0][2] + '</span></span><ol>'
      + first.slice(0, 3).map(function (r) {
        var p = P[r[1]];
        return '<li>' + D.pills[p[3]] + '<span class="nm">' + esc(p[1]) + '</span></li>';
      }).join('') + (extra > 0 ? '<li class="ct-more">+' + extra + ' more tied</li>' : '') + '</ol></button>';
  }).join('');
  function setView(v) {
    document.body.setAttribute('data-view', v);
    var t = document.querySelector('.toggle');
    t.setAttribute('aria-label', v === 'condensed' ? 'Switch to expanded view' : 'Switch to condensed view');
    if (v === 'expanded') go(active, false);
  }
  // open the expanded view at a stat: its category's card, turned to it
  function openStat(key) {
    var s = S[key], i = slots.findIndex(function (x) { return x.getAttribute('data-cat') === s.cat; }), slot = slots[i];
    setView('expanded'); setActive(i); go(i, false);
    var tr = slot.querySelector('.strack'), j = [].slice.call(tr.children).findIndex(function (x) { return x.getAttribute('data-stat') === key; });
    tr.scrollLeft = j * tr.clientWidth; tabsFollow(slot.querySelector('.card'));
  }
  document.querySelector('.toggle').addEventListener('click', function () { setView(document.body.getAttribute('data-view') === 'condensed' ? 'expanded' : 'condensed'); });
  cv.addEventListener('click', function (e) { var t = e.target.closest('[data-open]'); if (t) openStat(t.getAttribute('data-open')); });

  // #defense opens on that card; #defense-2 on its third stat; #condensed on the condensed view
  var h = location.hash.slice(1).split('-'), start = Math.max(0, slots.findIndex(function (s) { return s.getAttribute('data-cat') === h[0]; }));
  setActive(start); go(start, false);
  if (h[1]) { var tr0 = slots[start].querySelector('.strack'); tr0.scrollLeft = +h[1] * tr0.clientWidth; tabsFollow(slots[start].querySelector('.card')); }
  if (h[0] === 'condensed') setView('condensed');
  window.addEventListener('resize', function () { go(active, false); });
})();
"""


def page(data):
    icons = data["icons"]
    cats = data["cats"]
    slots, dots = [], []
    for i, (cat, name) in enumerate(cats):
        stats = [s for s in data["stats"] if s["cat"] == cat]
        ic = f'<span class="t-ic">{icons.get(cat, "")}</span>'
        title = f'<span class="ttl">{ic}<span>{esc(name)}</span></span>'
        tabs = "".join(f'<button class="tab{" on" if j == 0 else ""}" type="button" data-i="{j}">{esc(s["short"])}</button>'
                       for j, s in enumerate(stats))
        panes = "".join(f'<section class="stat" data-stat="{s["key"]}" aria-label="{esc(s["name"])}"></section>' for s in stats)
        slots.append(
            f'<section class="slot" data-cat="{cat}"><div class="card">'
            f'<div class="peek peek-top">{DOWN}{title}</div>'
            f'<div class="body"><div class="tabs" role="tablist">{tabs}</div><div class="strack">{panes}</div></div>'
            f'<div class="peek peek-bot">{UP}{title}</div></div></section>')
        dots.append(f'<button class="dot" type="button" aria-label="{esc(name)}">{icons.get(cat, "")}</button>')
    menu = theme.menu_html("", None).replace('<a href="standings.html">Standings</a>',
                                             '<a href="standings.html">Standings</a><a href="#" aria-current="page">Stat Leaders</a>')
    bar = ('<nav class="bottombar"><div class="bar-in">' + menu
           + f'<a class="week" href="#">{CHEV}<span>Week {data["through"] + 1}</span></a>'
           + f'<button class="toggle" type="button" aria-label="Switch to condensed view"><span class="i-plus">{PLUS}</span>'
           + f'<span class="i-minus">{MINUS}</span></button></div></nav>')
    data = dict(data, pills={t: helmets.pill_html(t, t) for t in DIVISIONS})
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        f"<title>{SEASON} Stat Leaders mockup 3</title><script>{theme.THEME_HEAD_JS}</script>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
        f"<style>{theme.THEME_CSS}{CSS}{v2.helmet_css()}</style></head><body data-id='pills' data-view='expanded'>"
        "<div class='idsw' aria-label='Mockup: team marks'><button class='on' data-id-pick='pills'>Pills</button>"
        "<button data-id-pick='helmets'>Helmets</button></div>"
        f"<header class='top'><span class='yr abbr'>{SEASON}</span><span class='rs-line'><span class='rs'>Stat Leaders</span>"
        f"<span class='thru'>Through Week {data['through']}</span></span></header>"
        f"<main class='deck'>{''.join(slots)}</main><section class='cview' aria-label='Every stat, condensed'></section><nav class='ic-dots' aria-label='Categories'>{''.join(dots)}</nav>{bar}"
        f"<script type='application/json' id='data'>{blob}</script>"
        f"<script>{theme.THEME_JS}</script><script>{JS}</script></body></html>"
    )


AVERAGES = {"ypa", "ypc", "pavg", "kravg", "pravg"}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "stat-leaders-3.html")
    # Returns are averages, not yards (Jason, 2026-10-07), qualified like the other averages: at least
    # one return a team game -- an assumption, not the NFL's published minimum
    v2.STATS[:] = [s for s in v2.STATS if s[0] not in ("kryds", "pryds")] + [
        ("kravg", "returns", "Kick Return Average", "KR Avg", lambda r: v2._div(r["kryds"], r["kr"]), 1, ("kr", 1), "kr", "AVG"),
        ("pravg", "returns", "Punt Return Average", "PR Avg", lambda r: v2._div(r["pryds"], r["pr"]), 1, ("pr", 1), "pr", "AVG"),
    ]
    v2.QUAL_WORD.update(kr="kick returns", pr="punt returns")
    # every stat gets its race, except the averages (Jason, 2026-10-07)
    v2.RACE_KEYS[:] = [s[0] for s in v2.STATS if s[0] not in AVERAGES]
    data = v2.build_data()
    for st in data["stats"]:   # "1 kick returns" -> "1 kick return"
        st["qual"] = st["qual"].replace(" 1 kick returns ", " 1 kick return ").replace(" 1 punt returns ", " 1 punt return ")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page(data))
    print(f"Wrote {out} ({len(data['players'])} players across {len(data['stats'])} stats, through week {data['through']})")


if __name__ == "__main__":
    main()

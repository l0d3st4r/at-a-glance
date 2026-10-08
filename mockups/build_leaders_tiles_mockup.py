"""
Stat Leaders condensed tiles -- arrangement mockup (2026-10-07), NOT part of the live build.

The real page (render_leaders.render) with a small mockup-only switch above the bottom bar that redraws
the three-across tiles (passing, rushing, receiving, defense) four ways. Kicking and returns stay as
they are (stat name over number, then pill + first initial and last name). "Now" is the current tile.

  A "Hero number"  -- centered: the stat's name, a big number, then pill + last name
  B "Mirror"       -- like kicking / returns: name over number on the left, the leader on the right
                      (pill over last name)
  C "Player first" -- pill + last name on top, then the stat's name left and the
                      number right
  D "Number right" -- pill + last name with the stat's name under it on the left, a big number on the
                      right spanning both

Up to three tied leaders, as on the page. Run after build_data.py:
    python mockups/build_leaders_tiles_mockup.py [out.html]
Writes mockups/leaders-tiles.html (self-contained). #b opens on arrangement B.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import render_leaders  # noqa: E402

CSS = """
/* MOCKUP: the switch sits just above the bottom bar; the condensed view gives it room */
.tsw{position:fixed;left:0;right:0;bottom:var(--bbar);z-index:17;display:flex;justify-content:center;gap:4px;padding:4px 8px;
  background:var(--aag-bg);border-top:1px dashed var(--line);font-size:11px}
.tsw button{background:none;border:1px solid var(--line);border-radius:999px;padding:2px 9px;cursor:pointer;color:var(--text)}
.tsw button.on{background:var(--text);color:var(--aag-bg);border-color:var(--text)}
.cview{height:calc(100dvh - var(--top-h) - var(--bbar) - 30px) !important}
body:not([data-view=condensed]) .tsw{display:none}

.ct:not(.one) .nm{font-size:11px}
/* A: hero number, everything centered */
body[data-tile=a] .ct:not(.one){align-items:center;justify-content:center;text-align:center;gap:1px}
.ta-v{font-family:Teko,Inter,sans-serif;font-size:30px;line-height:.85;font-weight:600}
.ta-ls{display:flex;flex-direction:column;align-items:center;gap:2px;margin-top:2px}
/* B: mirror of kicking / returns -- name over number left, leaders (pill over name) right */
body[data-tile=b] .ct:not(.one){flex-direction:row;align-items:center;gap:4px;padding:4px 5px}
.tb-left{display:flex;flex-direction:column;gap:1px;flex:none}
.tb-right{flex:1;min-width:0;display:flex;flex-direction:column;align-items:flex-start;gap:3px}
.tb-p{display:flex;flex-direction:column;align-items:flex-start;gap:1px;min-width:0;max-width:100%}
.tb-p .nm{line-height:12px;font-size:10px}
/* C: player first */
body[data-tile=c] .ct:not(.one){justify-content:space-between;gap:3px}
.tc-ls{display:flex;flex-direction:column;gap:2px}
.tc-bot{display:flex;align-items:baseline;justify-content:space-between;gap:4px}
.tc-bot .ct-v{font-size:24px;line-height:1}
/* D: number right */
body[data-tile=d] .ct:not(.one){flex-direction:row;align-items:center;gap:4px}
.td-left{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.td-v{font-family:Teko,Inter,sans-serif;font-size:28px;line-height:.85;font-weight:600;flex:none}
.td-left .ct-l{margin-top:1px}
"""

JS = r"""
(function () {
  var D = JSON.parse(document.getElementById('data').textContent), P = D.players, S = {};
  D.stats.forEach(function (s) { S[s.key] = s; });
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function lastName(full) { var t = full.replace(/\s+(Jr\.?|Sr\.?|II|III|IV|V)$/, ''), i = t.indexOf(' '); return i < 0 ? t : t.slice(i + 1); }
  function first(s) { return s.rows.filter(function (r) { return r[0] === 1; }); }
  function val(s) { var f = first(s); return f.length ? f[0][2] : '—'; }
  function more(s) { var x = first(s).length - 3; return x > 0 ? '<span class="ct-more">+' + x + ' more tied</span>' : ''; }
  function lab(s) { return '<span class="ct-l">' + esc(s.short) + '</span>'; }
  function ld(r, form) { var p = P[r[1]]; return '<span class="ld">' + D.pills[p[3]] + '<span class="nm">' + esc(form === 'short' ? p[0] : lastName(p[1])) + '</span></span>'; }
  var T = {
    a: function (s) {
      return lab(s) + '<span class="ta-v">' + val(s) + '</span><span class="ta-ls">' + first(s).slice(0, 3).map(function (r) { return ld(r); }).join('') + more(s) + '</span>';
    },
    b: function (s) {
      return '<span class="tb-left">' + lab(s) + '<span class="ct-v">' + val(s) + '</span></span><span class="tb-right">'
        + first(s).slice(0, 3).map(function (r) { var p = P[r[1]]; return '<span class="tb-p">' + D.pills[p[3]] + '<span class="nm">' + esc(lastName(p[1])) + '</span></span>'; }).join('') + more(s) + '</span>';
    },
    c: function (s) {
      return '<span class="tc-ls">' + first(s).slice(0, 3).map(function (r) { return ld(r); }).join('') + more(s) + '</span>'
        + '<span class="tc-bot">' + lab(s) + '<span class="ct-v">' + val(s) + '</span></span>';
    },
    d: function (s) {
      return '<span class="td-left">' + first(s).slice(0, 3).map(function (r) { return ld(r); }).join('') + more(s) + lab(s) + '</span><span class="td-v">' + val(s) + '</span>';
    }
  };
  var tiles = [].slice.call(document.querySelectorAll('.cview .ct:not(.one)'));
  tiles.forEach(function (t) { t.setAttribute('data-orig', t.innerHTML); });
  function pick(k) {
    document.body.setAttribute('data-tile', k);
    tiles.forEach(function (t) { t.innerHTML = T[k] ? T[k](S[t.getAttribute('data-open')]) : t.getAttribute('data-orig'); });
    document.querySelectorAll('[data-tile-pick]').forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-tile-pick') === k); });
  }
  document.querySelectorAll('[data-tile-pick]').forEach(function (b) { b.addEventListener('click', function () { pick(b.getAttribute('data-tile-pick')); }); });
  document.body.setAttribute('data-view', 'condensed');
  pick(location.hash.slice(1) || 'a');
})();
"""

NAMES = (("a", "A · Hero"), ("b", "B · Mirror"), ("c", "C · Player first"), ("d", "D · Number right"), ("now", "Now"))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mockups", "leaders-tiles.html")
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        data = json.load(f)
    page = render_leaders.render(data)
    strip = "<div class='tsw'>" + "".join(f"<button data-tile-pick='{k}'>{n}</button>" for k, n in NAMES) + "</div>"
    page = page.replace("</style></head>", CSS + "</style></head>", 1)
    page = page.replace("</body>", f"{strip}<script>{JS}</script></body>", 1)
    page = page.replace("<title>", "<title>Tiles mockup · ", 1)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

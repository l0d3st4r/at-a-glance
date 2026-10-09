"""
Game days and times in the viewer's own time zone (Jason, 2026-10-09).

The schedules give every start time in US Eastern ("13:00" on "2026-10-11"). The pages are built
ahead of time, so they can't know where the viewer is: each day and time is written into the page in
Eastern (the time still marked "ET", in case the script never runs), tagged with the actual moment the
game starts, and JS below rewrites it for wherever the viewer is -- 10:00 AM in California, 1:00 PM in
New York, and a Monday-night game is Tuesday morning in London. Page 0 moves games to the right day
too (PAGE0_JS's localDays).

  attrs(gameday, gametime, mode)  -> the tag for one element ("" when the time isn't known, which
                                     leaves the Eastern day on it)
      mode  "t"    the time as text: "10:00 AM"                 (Page 0 tiles, schedules, top bar)
            "s"    "10:00<small>AM</small>"                     (the game pages' big time)
            "a"    the aria-label, from aria with {t} for the time  (Page 0 tiles)
            "k"    nothing rewritten -- just the moment, for Page 0 to sort games into days
            "bar"  "SUN OCT 11"     "long" "OCT 11 Sunday"     "md" "OCT 11"
            "wd"   "Sunday"         "mdw"  "OCT 11 SUNDAY"     "sc" "SUN 10/11"
  JS  -- defines window.AAG_LT(root) and runs it on the page once; Page 0's overlay runs it again
         on each game page it mounts. AAG_LT.parts(iso) gives the local day and time pieces.
"""

import html
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    EASTERN = ZoneInfo("America/New_York")
except Exception:   # no time zone database (e.g. Windows without tzdata)
    EASTERN = None


def _eastern_offset(naive):
    """US Eastern's UTC offset at a local time, by the US rule since 2007: daylight time from the
    second Sunday of March to the first Sunday of November, 2 AM. Only used without zoneinfo."""
    y = naive.year
    march1, nov1 = datetime(y, 3, 1), datetime(y, 11, 1)
    start = march1 + timedelta(days=(6 - march1.weekday()) % 7 + 7, hours=2)
    end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7, hours=2)
    return timedelta(hours=-4 if start <= naive < end else -5)


def eastern_to_utc(gameday, gametime):
    """'2026-10-11' + '13:00' (US Eastern) -> aware UTC datetime, or None."""
    try:
        naive = datetime.fromisoformat(f"{str(gameday)[:10]}T{str(gametime)[:5]}")
    except (TypeError, ValueError):
        return None
    if EASTERN is not None:
        return naive.replace(tzinfo=EASTERN).astimezone(timezone.utc)
    return (naive - _eastern_offset(naive)).replace(tzinfo=timezone.utc)


def attrs(gameday, gametime, mode="t", aria=None):
    ko = eastern_to_utc(gameday, gametime)
    if ko is None:
        return ""
    out = f' data-ko="{ko.strftime("%Y-%m-%dT%H:%M:00Z")}" data-lt="{mode}"'
    if aria:
        out += f' data-aria="{html.escape(aria, quote=True)}"'
    return out


JS = r"""
window.AAG_LT = (function () {
  var ok = !!(window.Intl && Intl.DateTimeFormat && Intl.DateTimeFormat.prototype.formatToParts);
  var fmt = ok && new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'numeric', day: 'numeric', weekday: 'long',
                                                       hour: 'numeric', minute: '2-digit', hour12: true });
  var MON = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  // iso -> the moment's day and time where the viewer is: {key: '2026-10-11', y, m (1-12), d, wd: 'Sunday', hm: '10:00', ap: 'AM'}
  function parts(iso) {
    var t = new Date(iso);
    if (!fmt || isNaN(t)) return null;
    var p = {};
    fmt.formatToParts(t).forEach(function (x) { p[x.type] = x.value; });
    var y = +p.year, m = +p.month, d = +p.day;
    return { key: y + '-' + pad(m) + '-' + pad(d), y: y, m: m, d: d, wd: p.weekday,
             hm: (+p.hour) + ':' + p.minute, ap: String(p.dayPeriod || '').toUpperCase() };
  }
  var MODES = {
    t: function (el, q) { el.textContent = q.hm + ' ' + q.ap; },
    s: function (el, q) { el.innerHTML = q.hm + '<small>' + q.ap + '</small>'; },
    a: function (el, q) { el.setAttribute('aria-label', (el.getAttribute('data-aria') || '').replace('{t}', q.hm + ' ' + q.ap)); },
    k: function () {},
    bar: function (el, q) { el.textContent = q.wd.slice(0, 3).toUpperCase() + ' ' + MON[q.m - 1] + ' ' + q.d; },
    long: function (el, q) { el.textContent = MON[q.m - 1] + ' ' + q.d + ' ' + q.wd; },
    md: function (el, q) { el.textContent = MON[q.m - 1] + ' ' + q.d; },
    wd: function (el, q) { el.textContent = q.wd; },
    mdw: function (el, q) { el.textContent = MON[q.m - 1] + ' ' + q.d + ' ' + q.wd.toUpperCase(); },
    sc: function (el, q) { el.textContent = q.wd.slice(0, 3).toUpperCase() + ' ' + q.m + '/' + q.d; }
  };
  function run(root) {
    if (!ok) return;
    // the tags stay on: rewriting again gives the same result, and Page 0 reads them to sort games into days
    [].forEach.call((root || document).querySelectorAll('[data-ko]'), function (el) {
      var q = parts(el.getAttribute('data-ko')), f = MODES[el.getAttribute('data-lt')];
      if (q && f) f(el, q);
    });
  }
  run.parts = parts;
  return run;
})();
AAG_LT(document);
"""

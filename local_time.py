"""
Game times in the viewer's own time zone (Jason, 2026-10-09).

The schedules give every start time in US Eastern ("13:00" on "2026-10-11"). The pages are built
ahead of time, so they can't know where the viewer is: each time is written into the page in Eastern
(still marked "ET", in case the script never runs), tagged with the actual moment it starts, and JS
below rewrites it in the viewer's local time without the "ET" -- 10:00 AM in California, 1:00 PM in
New York.

  attrs(gameday, gametime, mode)  -> the tag for one element (or "" when the time isn't known)
      mode "t": the element's text becomes "10:00 AM"            (Page 0 tiles, schedules, top bar)
           "s": "10:00<small>AM</small>"                         (the game pages' big time)
           "a": its aria-label, from aria with {t} for the time  (Page 0 tiles)
  JS  -- defines window.AAG_LT(root) and runs it on the page once; Page 0's overlay runs it again
         on each game page it mounts.

Day headers and dates stay on the Eastern day: in the US no game crosses midnight either way.
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
window.AAG_LT = function (root) {
  if (!window.Intl || !Intl.DateTimeFormat || !Intl.DateTimeFormat.prototype.formatToParts) return;
  var fmt = new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  [].forEach.call((root || document).querySelectorAll('[data-ko]'), function (el) {
    var d = new Date(el.getAttribute('data-ko'));
    if (isNaN(d)) return;
    var hm = '', ap = '';
    fmt.formatToParts(d).forEach(function (p) {
      if (p.type === 'dayPeriod') ap = p.value.toUpperCase();
      else if (p.type === 'hour' || p.type === 'minute' || (p.type === 'literal' && p.value === ':')) hm += p.value;
    });
    var mode = el.getAttribute('data-lt');
    if (mode === 's') el.innerHTML = hm + '<small>' + ap + '</small>';
    else if (mode === 'a') el.setAttribute('aria-label', (el.getAttribute('data-aria') || '').replace('{t}', hm + ' ' + ap));
    else el.textContent = hm + ' ' + ap;
    el.removeAttribute('data-ko');
  });
};
AAG_LT(document);
"""

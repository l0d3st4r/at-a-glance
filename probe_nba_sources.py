"""
Which NBA data sources can a GitHub Actions runner actually read? (2026-10-08)

A one-off probe for planning the NBA section, run by .github/workflows/nba-probe.yml.
It doesn't build anything; it tries each candidate source from the runner and
reports what came back: HTTP status, how long it took, file sizes, column names,
row counts, how fresh the data is, and one sample row. The report goes to stdout
and, in Actions, to the run's summary page.

Sources tried, best bet first:

  hoopR / sportsdataverse   ESPN data that sportsdataverse scrapes and posts as
                            files on GitHub releases (sportsdataverse/sportsdataverse-data),
                            the same model as nflverse. Tag names are discovered from
                            the releases list rather than guessed.
  cdn.nba.com               NBA.com's own live JSON (scoreboard, schedule, box score).
                            Said to be reachable from cloud servers; the candidate for
                            same-night scores.
  stats.nba.com             What nba_api reads. Widely reported to hang for cloud IPs.
  ESPN site API             Blocked by Akamai for the NFL side (2026-09-16); checked
                            here for the NBA in case it differs.
  Kaggle                    eoinamoore/historical-nba-data-and-player-box-scores.
                            Scripted downloads need a Kaggle token; this only checks
                            whether its metadata answers without one.
  NBA injury report         official.nba.com's page linking the daily injury PDFs.

Usage:
    python probe_nba_sources.py [--summary report.md]
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import time

import requests

SDV_API = "https://api.github.com/repos/sportsdataverse/sportsdataverse-data"
# NBA seasons are keyed by the year they end in: 2027 = 2026-27 (just starting), 2026 = 2025-26 (complete)
SEASONS = [2027, 2026]
MAX_DOWNLOAD_MB = 60  # play-by-play files run to hundreds of MB; size alone tells us enough about those
TIMEOUT = 25

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
# the headers nba_api sends to stats.nba.com
STATS_NBA_HEADERS = dict(BROWSER_HEADERS, **{
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
})

lines = []


def say(text=""):
    print(text, flush=True)
    lines.append(text)


def fetch(url, headers=None, timeout=TIMEOUT, github=False):
    """(response or None, seconds, error text or None). Never raises."""
    h = dict(headers or {"User-Agent": "at-a-glance-nba-probe"})
    if github and os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
        h["Accept"] = "application/vnd.github+json"
    start = time.monotonic()
    try:
        r = requests.get(url, headers=h, timeout=timeout)
        return r, time.monotonic() - start, None
    except requests.RequestException as e:
        return None, time.monotonic() - start, f"{type(e).__name__}: {e}"


def status_line(label, r, secs, err):
    if err:
        say(f"- **{label}**: FAILED after {secs:.1f}s ({err[:200]})")
    else:
        size = len(r.content)
        say(f"- **{label}**: HTTP {r.status_code} in {secs:.1f}s, {size:,} bytes, "
            f"content-type `{r.headers.get('content-type', '?')}`")
    return not err and r.status_code == 200


def show_keys(label, obj, depth=0, max_depth=2):
    """Print a JSON object's shape: keys and list lengths, a couple of levels down."""
    pad = "  " * depth
    if isinstance(obj, dict):
        say(f"{pad}- {label}: {{{', '.join(list(obj)[:40])}}}")
        if depth < max_depth:
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    show_keys(k, v, depth + 1, max_depth)
    elif isinstance(obj, list):
        say(f"{pad}- {label}: list of {len(obj)}")
        if obj and depth < max_depth:
            show_keys(f"{label}[0]", obj[0], depth + 1, max_depth)


# ---------- hoopR / sportsdataverse ----------

def sdv_nba_releases():
    releases, page = [], 1
    while True:
        r, _, err = fetch(f"{SDV_API}/releases?per_page=100&page={page}", github=True)
        if err or r.status_code != 200:
            say(f"- releases list page {page}: {err or f'HTTP {r.status_code}: {r.text[:200]}'}")
            return releases
        batch = r.json()
        releases += [x for x in batch if "nba" in x.get("tag_name", "") and "wnba" not in x["tag_name"]]
        if len(batch) < 100:
            return releases
        page += 1


def release_assets(release):
    assets, page = [], 1
    while True:
        r, _, err = fetch(f"{SDV_API}/releases/{release['id']}/assets?per_page=100&page={page}", github=True)
        if err or r.status_code != 200:
            return assets
        batch = r.json()
        assets += batch
        if len(batch) < 100:
            return assets
        page += 1


def describe_csv(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    cols = list(rows[0].keys()) if rows else []
    say(f"    - {len(rows):,} rows, {len(cols)} columns: `{', '.join(cols)}`")
    for key in ("game_date", "date", "game_date_time", "start_date"):
        if cols and key in cols:
            dates = sorted({r[key][:10] for r in rows if r.get(key)})
            if dates:
                say(f"    - `{key}` runs {dates[0]} to {dates[-1]}")
            break
    for key in ("season_type", "type_abbreviation"):
        if cols and key in cols:
            counts = {}
            for r in rows:
                counts[r[key]] = counts.get(r[key], 0) + 1
            say(f"    - `{key}` counts: {counts}")
            break
    if rows:
        sample = {k: v for k, v in rows[-1].items() if v not in ("", "NA")}
        say(f"    - last row: `{json.dumps(sample)[:1500]}`")


def probe_sportsdataverse():
    say("## hoopR / sportsdataverse (GitHub releases)")
    releases = sdv_nba_releases()
    if not releases:
        say("- no NBA releases found")
        say()
        return
    say(f"- {len(releases)} NBA release tags: `{', '.join(sorted(x['tag_name'] for x in releases))}`")
    say()
    for rel in sorted(releases, key=lambda x: x["tag_name"]):
        tag = rel["tag_name"]
        assets = release_assets(rel)
        seasons = sorted({int(m.group(1)) for a in assets for m in [re.search(r"_(\d{4})\.", a["name"])] if m})
        newest = max((a["updated_at"] for a in assets), default="?")
        say(f"### `{tag}`")
        say(f"- {len(assets)} files, newest upload {newest}, seasons "
            f"{seasons[0] if seasons else '?'}-{seasons[-1] if seasons else '?'}")
        names = sorted({re.sub(r"_\d{4}\.", "_YYYY.", a["name"]) for a in assets})
        say(f"- file patterns: `{', '.join(names[:12])}`")
        stamp = next((a for a in assets if a["name"] == "timestamp.txt"), None)
        if stamp:
            r, _, err = fetch(stamp["browser_download_url"])
            if not err and r.status_code == 200:
                say(f"- timestamp.txt: `{r.text.strip()[:100]}`")
        if not tag.startswith("espn_nba"):
            say()
            continue
        for season in SEASONS:
            a = next((a for a in assets if re.search(rf"_{season}\.csv$", a["name"])), None)
            if not a:
                say(f"- {season}: no CSV")
                continue
            mb = a["size"] / 1e6
            say(f"- `{a['name']}`: {mb:.1f} MB, uploaded {a['updated_at']}")
            if mb > MAX_DOWNLOAD_MB:
                say(f"    - skipped download (over {MAX_DOWNLOAD_MB} MB)")
                continue
            r, secs, err = fetch(a["browser_download_url"], timeout=120)
            if err or r.status_code != 200:
                say(f"    - download failed: {err or r.status_code}")
                continue
            say(f"    - downloaded in {secs:.1f}s")
            describe_csv(r.content.decode("utf-8", errors="replace"))
        say()


# ---------- cdn.nba.com ----------

def probe_cdn_nba():
    say("## cdn.nba.com (NBA.com live JSON)")
    r, secs, err = fetch("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
                         headers=BROWSER_HEADERS)
    if status_line("today's scoreboard", r, secs, err):
        try:
            sb = r.json().get("scoreboard", {})
            games = sb.get("games", [])
            say(f"  - gameDate {sb.get('gameDate')}, {len(games)} games")
            if games:
                show_keys("games[0]", games[0], max_depth=1)
        except ValueError:
            say("  - not JSON")

    last_final = None
    r, secs, err = fetch("https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
                         headers=BROWSER_HEADERS, timeout=60)
    if status_line("full-season schedule", r, secs, err):
        try:
            ls = r.json().get("leagueSchedule", {})
            dates = ls.get("gameDates", [])
            games = [g for d in dates for g in d.get("games", [])]
            say(f"  - season {ls.get('seasonYear')}, {len(dates)} dates, {len(games)} games")
            if games:
                show_keys("games[0]", games[0], max_depth=1)
            finals = [g for g in games if g.get("gameStatus") == 3]
            if finals:
                last_final = finals[-1]
                say(f"  - {len(finals)} finished; latest {last_final.get('gameId')} "
                    f"{last_final.get('awayTeam', {}).get('teamTricode')} @ "
                    f"{last_final.get('homeTeam', {}).get('teamTricode')} on {last_final.get('gameDateEst')}")
        except ValueError:
            say("  - not JSON")

    if last_final:
        gid = last_final["gameId"]
        r, secs, err = fetch(f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{gid}.json",
                             headers=BROWSER_HEADERS)
        if status_line(f"box score {gid}", r, secs, err):
            try:
                game = r.json().get("game", {})
                show_keys("game", game, max_depth=1)
                players = game.get("homeTeam", {}).get("players", [])
                if players:
                    say(f"  - player stat keys: `{', '.join(players[0].get('statistics', {}))}`")
            except ValueError:
                say("  - not JSON")
    say()


# ---------- stats.nba.com, ESPN, Kaggle, injury report ----------

def probe_stats_nba():
    say("## stats.nba.com (what nba_api reads)")
    url = ("https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season=2025-26"
           "&SeasonType=Regular%20Season")
    r, secs, err = fetch(url, headers=STATS_NBA_HEADERS, timeout=30)
    if status_line("standings 2025-26", r, secs, err):
        try:
            rs = r.json()["resultSets"][0]
            say(f"  - {len(rs['rowSet'])} teams, headers `{', '.join(rs['headers'][:30])}`")
        except (ValueError, KeyError, IndexError):
            say(f"  - unexpected body: `{r.text[:200]}`")
    say()


def probe_espn():
    say("## ESPN site API (direct)")
    for label, url in [
        ("scoreboard", "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"),
        ("standings", "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"),
    ]:
        r, secs, err = fetch(url, headers=BROWSER_HEADERS)
        if status_line(label, r, secs, err):
            try:
                show_keys(label, r.json(), max_depth=0)
            except ValueError:
                say(f"  - not JSON: `{r.text[:200]}`")
    say()


def probe_kaggle():
    say("## Kaggle (eoinamoore/historical-nba-data-and-player-box-scores)")
    ref = "eoinamoore/historical-nba-data-and-player-box-scores"
    for label, url in [
        ("dataset metadata", f"https://www.kaggle.com/api/v1/datasets/view/{ref}"),
        ("file list", f"https://www.kaggle.com/api/v1/datasets/list/{ref}"),
    ]:
        r, secs, err = fetch(url, headers=BROWSER_HEADERS)
        if status_line(f"{label} (no token)", r, secs, err):
            try:
                body = r.json()
                if label == "file list":
                    for f in (body.get("datasetFiles") or body.get("files") or [])[:30]:
                        say(f"  - `{f.get('name') or f.get('nameNullable')}` "
                            f"{(f.get('totalBytes') or f.get('totalBytesNullable') or 0) / 1e6:.1f} MB")
                else:
                    keep = ("title", "lastUpdated", "licenseName", "totalBytes", "usabilityRating", "currentVersionNumber")
                    say(f"  - `{json.dumps({k: body.get(k) for k in keep if k in body})}`")
            except ValueError:
                say(f"  - not JSON: `{r.text[:200]}`")
        elif r is not None:
            say(f"  - body: `{r.text[:200]}`")
    say()


def probe_injuries():
    say("## NBA injury report (official.nba.com)")
    for season in ("2026-27", "2025-26"):
        r, secs, err = fetch(f"https://official.nba.com/nba-injury-report-{season}-season/", headers=BROWSER_HEADERS)
        if status_line(f"{season} page", r, secs, err):
            pdfs = re.findall(r"https://[^\"']+?Injury-Report[^\"']+?\.pdf", r.text)
            say(f"  - {len(pdfs)} PDF links" + (f", latest `{pdfs[-1]}`" if pdfs else ""))
            if pdfs:
                p, psecs, perr = fetch(pdfs[-1], headers=BROWSER_HEADERS)
                status_line("  latest PDF", p, psecs, perr)
    say()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", help="also write the report (markdown) to this file")
    args = ap.parse_args()

    say(f"# NBA data source probe ({time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())})")
    say()
    for probe in (probe_sportsdataverse, probe_cdn_nba, probe_stats_nba, probe_espn, probe_kaggle, probe_injuries):
        try:
            probe()
        except Exception as e:  # one broken probe shouldn't hide the others' results
            say(f"- probe {probe.__name__} crashed: {type(e).__name__}: {e}")
            say()

    if args.summary:
        with open(args.summary, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())

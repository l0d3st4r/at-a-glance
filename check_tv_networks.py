"""
Weekly check of tv_networks.csv against the published schedule (2026-09-29).

Never edits the file -- it lists what to change, and the tv-check workflow posts that list as
a GitHub issue ("TV networks to review"). Run by hand with: python check_tv_networks.py

Sources, for games that haven't been played yet:
  - CBS Sports' weekly schedule (cbssports.com/nfl/schedule/<season>/regular/<week>/) lists a
    network for every announced game; CBS's own games carry a CBS logo instead of text
  - NFL.com's schedule page, which has the official networks but only for the current week;
    where the two disagree, NFL.com wins

It also watches the "time_tbd" marks (games whose kickoff time the NFL hasn't set): CBS Sports
leaves a game off its weekly schedule until its time is set, so a marked game that now appears
there has a time, and an unmarked game that's missing may not have one.

A source that only has part of a simulcast doesn't count as a change (CBS Sports shows Monday
night ESPN/ABC games as just "ESPN"), and a game a source doesn't list or has no network for yet
is left alone.

Writes the report to stdout and, with --out, to a Markdown file; exit code 0 either way (a
fetch problem is reported in the file, so the workflow still says what went wrong).
"""

import argparse
import csv
import os
import re
import time
import urllib.request
from datetime import date, datetime, timezone

import tv_networks
from divisions import normalize_abbr

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}
CBS_URL = "https://www.cbssports.com/nfl/schedule/{season}/regular/{week}/"
NFL_URL = "https://www.nfl.com/schedules/{season}/REG{week}/"
LABELS = {"FOX": "FOX", "CBS": "CBS", "NBC": "NBC", "AMZN": "Prime Video", "PRIME VIDEO": "Prime Video",
          "ESPN": "ESPN", "ABC": "ABC", "NFLN": "NFL Network", "NFL NETWORK": "NFL Network",
          "NFLX": "Netflix", "NETFLIX": "Netflix", "YOUTUBE": "YouTube"}
ABBR = {"JAC": "JAX", "AZ": "ARI", "WSH": "WAS"}   # CBS Sports / NFL.com spellings -> nflverse


def _team(a):
    return normalize_abbr(ABBR.get(a, a))


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8", "ignore")


def cbs_week(season, week):
    """({frozenset(teams): network}, {frozenset(teams), ...} every game listed with a time) for
    one week of CBS Sports' schedule."""
    html = _get(CBS_URL.format(season=season, week=week))
    out, listed = {}, set()
    for m in re.finditer(r'/nfl/gametracker/(?:live|preview|recap)/NFL_\d{8}_([A-Z]+)@([A-Z]+)/"[^>]*>[^<]*</a>(.*?)</td>', html, re.S):
        away, home, cell = m.groups()
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cell)).strip().upper()
        net = LABELS.get(text) or ("CBS" if re.search(r"icon-moon-CBSIcon", cell) else None)
        listed.add(frozenset((_team(home), _team(away))))
        if net:
            out[frozenset((_team(home), _team(away)))] = net
    return out, listed


def nfl_current_week(season):
    """(week, {frozenset(teams): network}) from NFL.com, which serves the current week's networks."""
    html = _get(NFL_URL.format(season=season, week=1)).replace('\\"', '"')
    pat = re.compile(r'"homeTeam":\{"id":"[^"]*","currentLogo":"[^"]*?logos/([A-Z]+)","fullName":"[^"]*"\},'
                     r'"awayTeam":\{"id":"[^"]*","currentLogo":"[^"]*?logos/([A-Z]+)","fullName":"[^"]*"\},'
                     r'"category":[^,]*,"date":"[^"]+","time":"[^"]+",'
                     r'"broadcastInfo":\{"homeNetworkChannels":\[([^\]]*)\]')
    weeks = [int(w) for w in re.findall(r'"week":(\d+),"weekType":"REG"', html)]
    out = {}
    for home, away, chans in pat.findall(html):
        nets = [LABELS.get(c.upper()) for c in re.findall(r'"([^"]+)"', chans)]
        nets = [n for n in nets if n]
        if {"ESPN", "ABC"} <= set(nets):
            net = "ESPN/ABC"
        else:
            net = nets[0] if nets else None
        if net:
            out[frozenset((_team(home), _team(away)))] = net
    week = max(set(weeks), key=weeks.count) if weeks else None
    return week, out


def same(file_net, source_net):
    """True when the source agrees, including a source that lists only part of a simulcast."""
    split = lambda n: {p.strip().upper() for p in n.split("/")}
    return split(source_net) <= split(file_net)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="also write the report to this Markdown file")
    args = ap.parse_args()

    today = datetime.now(timezone.utc).date()
    with open(tv_networks.PATH, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f)
                if r.get("gameday") and date.fromisoformat(r["gameday"][:10]) >= today and r.get("week", "").isdigit()]
    season = int(rows[0]["game_id"][:4]) if rows else today.year

    source, problems, listed = {}, [], {}   # listed: week -> games CBS Sports shows with a time
    for week in sorted({int(r["week"]) for r in rows}):
        if week > 18:
            continue
        try:
            nets, listed[week] = cbs_week(season, week)
            for teams, net in nets.items():
                source[(week, teams)] = (net, "CBS Sports")
        except Exception as e:
            problems.append(f"CBS Sports week {week}: {e}")
        time.sleep(1.5)
    try:
        nfl_week, nfl = nfl_current_week(season)
        for teams, net in nfl.items():
            source[(nfl_week, teams)] = (net, "NFL.com")
    except Exception as e:
        problems.append(f"NFL.com: {e}")
    if not source:
        problems.append("no networks found in either source -- the page layout may have changed, so this check needs fixing")

    changed, announced, timed, untimed = [], [], [], []
    for r in rows:
        key = (int(r["week"]), frozenset((_team(r["away"]), _team(r["home"]))))
        marked = tv_networks._yes(r.get("time_tbd"))
        game = f"| {r['week']} | {r['gameday']} | {r['away']} @ {r['home']} |"
        if key[0] in listed:
            if marked and key[1] in listed[key[0]]:
                timed.append(game)
            elif not marked and listed[key[0]] and key[1] not in listed[key[0]]:
                untimed.append(game)
        if key not in source:
            continue
        net, where = source[key]
        have = (r.get("network") or "").strip()
        line = f"| {r['week']} | {r['gameday']} | {r['away']} @ {r['home']} | {have or '(blank)'} | **{net}** | {where} |"
        if not have:
            announced.append(line)
        elif not same(have, net):
            changed.append(line)

    head = "| Week | Date | Game | tv_networks.csv | Schedule says | Source |\n|---|---|---|---|---|---|"
    parts = [f"Checked {len(rows)} upcoming games on {today.isoformat()}."]
    if changed:
        parts += ["### Network changed", "The schedule now shows a different network (a flex, or a CBS/FOX swap).",
                  "\n".join([head, *changed])]
    if announced:
        parts += ["### Newly announced", "These games are blank in the file and now have a network.",
                  "\n".join([head, *announced])]
    short = "| Week | Date (nflverse) | Game |\n|---|---|---|"
    if timed:
        parts += ["### Kickoff time announced", "These games are marked `time_tbd` but now have a time on the schedule. "
                  "Clear their `time_tbd` cells so the site shows the time.", "\n".join([short, *timed])]
    if untimed:
        parts += ["### Kickoff time may not be set", "CBS Sports doesn't list a time for these games. If the NFL hasn't "
                  "set one, put `yes` in their `time_tbd` cells so the site shows TBD.", "\n".join([short, *untimed])]
    if not (changed or announced or timed or untimed):
        parts.append("Everything matches -- nothing to update.")
    if problems:
        parts += ["### Couldn't check everything", "\n".join(f"- {p}" for p in problems)]
    parts.append("To update: open `tv_networks.csv` on GitHub, click the pencil, fix the cells and commit.")
    report = "\n\n".join(parts) + "\n"

    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
    if os.environ.get("GITHUB_OUTPUT"):   # tells the workflow whether to open/update the issue or close it
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"changes={len(changed) + len(announced) + len(timed) + len(untimed)}\nproblems={len(problems)}\n")


if __name__ == "__main__":
    main()

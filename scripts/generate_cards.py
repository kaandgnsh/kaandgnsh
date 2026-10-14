#!/usr/bin/env python3
"""Render live GitHub telemetry as SVG in the profile's design system.

Runs daily in GitHub Actions (see .github/workflows/profile-assets.yml).
Reads public data from the GitHub GraphQL API, so the profile does not depend
on any third-party stats service.

    GITHUB_TOKEN=... python scripts/generate_cards.py --user kaandgnsh --out dist
    python scripts/generate_cards.py --demo --out preview   # watermarked sample data
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import (DIM, G, G2, G3, GTXT, LINE, LINE2, MUTE, RED, TXT, TXT2,  # noqa: E402
                    crop_marks, finalize, panel, t, width)

API = "https://api.github.com/graphql"
W = 900
LANG_RAMP = [G, G2, "#15803d", "#166534", "#8b949e", "#4b5560", "#2f363d"]
IGNORED_LANGS = {"HTML", "CSS", "Jupyter Notebook", "Makefile", "Dockerfile"}


# ---- data ------------------------------------------------------------------
def gql(token: str, query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], indent=2))
    return payload["data"]


Q_PROFILE = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    contributionsCollection { contributionYears }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC,
                 first: 100, after: $cursor) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

Q_YEAR = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch(user: str, token: str) -> dict:
    repos, cursor, first = [], None, None
    while True:
        data = gql(token, Q_PROFILE, {"login": user, "cursor": cursor})["user"]
        if data is None:
            sys.exit(f"GitHub user '{user}' not found")
        first = first or data
        page = data["repositories"]
        repos.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    langs: dict[str, int] = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name not in IGNORED_LANGS:
                langs[name] = langs.get(name, 0) + edge["size"]

    days: dict[str, int] = {}
    commits = total = 0
    for year in first["contributionsCollection"]["contributionYears"]:
        cc = gql(token, Q_YEAR, {"login": user, "from": f"{year}-01-01T00:00:00Z",
                                 "to": f"{year}-12-31T23:59:59Z"})["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"]
        total += cc["contributionCalendar"]["totalContributions"]
        for week in cc["contributionCalendar"]["weeks"]:
            for d in week["contributionDays"]:
                days[d["date"]] = d["contributionCount"]

    return {"repos": first["repositories"]["totalCount"],
            "stars": sum(r["stargazerCount"] for r in repos),
            "followers": first["followers"]["totalCount"],
            "commits": commits, "total": total, "langs": langs, "days": days,
            "since": first["createdAt"][:10]}


def demo_data() -> dict:
    import random
    rnd = random.Random(7)
    today = dt.date.today()
    days = {(today - dt.timedelta(days=i)).isoformat():
            (0 if rnd.random() < 0.35 else rnd.randint(1, 9)) for i in range(400)}
    for i in range(6):
        days[(today - dt.timedelta(days=i)).isoformat()] = rnd.randint(1, 5)
    return {"repos": 4, "stars": 3, "followers": 12, "commits": 128, "total": sum(days.values()),
            "langs": {"Python": 92000, "Shell": 6000, "C": 2500},
            "days": days, "since": (today - dt.timedelta(days=400)).isoformat()}


def streaks(days: dict[str, int]) -> dict:
    today = dt.date.today()
    dates = sorted(dt.date.fromisoformat(k) for k in days if dt.date.fromisoformat(k) <= today)
    longest, long_range, run, run_start = 0, None, 0, None
    for d in dates:
        if days[d.isoformat()] > 0:
            if run == 0:
                run_start = d
            run += 1
            if run > longest:
                longest, long_range = run, (run_start, d)
        else:
            run = 0
    # Today may still be empty, so the current streak can end yesterday.
    cursor = today if days.get(today.isoformat(), 0) > 0 else today - dt.timedelta(days=1)
    current, end = 0, cursor
    while days.get(cursor.isoformat(), 0) > 0:
        current += 1
        cursor -= dt.timedelta(days=1)
    cur_range = (cursor + dt.timedelta(days=1), end) if current else None
    return {"current": current, "cur_range": cur_range, "longest": longest, "long_range": long_range}


def last_n(days: dict[str, int], n: int) -> list[tuple[dt.date, int]]:
    today = dt.date.today()
    return [(today - dt.timedelta(days=i), days.get((today - dt.timedelta(days=i)).isoformat(), 0))
            for i in range(n - 1, -1, -1)]


# ---- rendering -------------------------------------------------------------
def fmt_range(r) -> str:
    if not r:
        return "no active streak"
    a, b = r
    if a == b:
        return a.strftime("%b %d, %Y")
    if a.year == b.year:
        return f"{a.strftime('%b %d')} – {b.strftime('%b %d, %Y')}"
    return f"{a.strftime('%b %d, %Y')} – {b.strftime('%b %d, %Y')}"


def head(label: str, stamp: str, demo: bool) -> list[str]:
    out = [t(36, 48, label, "mono-m", 11.5, GTXT, tracking=2.5),
           f'<line x1="1" y1="68" x2="{W-1}" y2="68" stroke="{LINE}"/>']
    if demo:
        out.append(t(W - 36, 48, "PREVIEW · SAMPLE DATA", "mono-m", 11.5, RED, "end", 2))
    else:
        out.append(t(W - 36, 48, f"synced {stamp}", "mono", 11.5, MUTE, "end", 0.5))
    return out


def metric_row(y: int, items: list[tuple[str, str, str | None]]) -> list[str]:
    out, colw = [], (W - 72) / len(items)
    for i, (value, label, sub) in enumerate(items):
        x = 36 + i * colw + (24 if i else 0)
        if i:
            out.append(f'<line x1="{36 + i*colw:.1f}" y1="{y-44}" x2="{36 + i*colw:.1f}" y2="{y+34}" stroke="{LINE}"/>')
        color = GTXT if label.startswith("CURRENT") else TXT
        fill = "url(#silver)" if color == TXT else color
        out.append(t(x, y, value, "display", 40, fill, tracking=-1))
        out.append(t(x, y + 26, label, "mono-m", 10.5, MUTE, tracking=2))
        if sub:
            out.append(t(x, y + 44, sub, "mono", 11, DIM, tracking=0.3))
    return out


def telemetry(d: dict, stamp: str, demo: bool) -> str:
    last12 = sum(v for day, v in last_n(d["days"], 365))
    b = head("TELEMETRY  ·  GITHUB API", stamp, demo)
    b += metric_row(140, [(f"{last12:,}", "CONTRIBUTIONS · 12 MO", None),
                          (f"{d['commits']:,}", "COMMITS · ALL TIME", None),
                          (f"{d['repos']:,}", "PUBLIC REPOS", None),
                          (f"{d['stars']:,}", "STARS EARNED", None)])
    y = 222
    b.append(f'<line x1="36" y1="{y-26}" x2="{W-36}" y2="{y-26}" stroke="{LINE}"/>')
    b.append(t(36, y, "LANGUAGES  ·  BY BYTES ACROSS PUBLIC REPOS", "mono-m", 10.5, MUTE, tracking=2))
    total = sum(d["langs"].values())
    top = sorted(d["langs"].items(), key=lambda kv: kv[1], reverse=True)
    if len(top) > 7:
        top = top[:6] + [("Other", sum(v for _, v in top[6:]))]
    bar_y, bar_w = y + 18, W - 72
    if total:
        b.append(f'<clipPath id="bar"><rect x="36" y="{bar_y}" width="{bar_w}" height="10" rx="5"/></clipPath>')
        b.append(f'<rect x="36" y="{bar_y}" width="{bar_w}" height="10" rx="5" fill="#11161a"/>')
        b.append('<g clip-path="url(#bar)">')
        x = 36.0
        for i, (_, size) in enumerate(top):
            seg = bar_w * size / total
            b.append(f'<rect x="{x:.2f}" y="{bar_y}" width="{max(seg - 2, 1):.2f}" height="10" fill="{LANG_RAMP[i]}"/>')
            x += seg
        b.append("</g>")
        lx, ly = 36.0, bar_y + 44
        for i, (name, size) in enumerate(top):
            pct = f"{100*size/total:.1f}%"
            item_w = 18 + width(name, "sans-m", 14.5) + 8 + width(pct, "mono", 12.5) + 28
            if lx + item_w > W - 36:
                lx, ly = 36.0, ly + 28
            b.append(f'<rect x="{lx:.1f}" y="{ly-10}" width="10" height="10" rx="2" fill="{LANG_RAMP[i]}"/>')
            b.append(t(lx + 18, ly, name, "sans-m", 14.5, TXT))
            b.append(t(lx + 18 + width(name, "sans-m", 14.5) + 8, ly, pct, "mono", 12.5, MUTE))
            lx += item_w
        h = int(ly + 40)
    else:
        b.append(t(36, bar_y + 30, "No language data yet.", "sans", 14, MUTE))
        h = bar_y + 70
    body = panel(W, h, rx=16) + crop_marks(W, h, 12, 9) + "\n".join(b)
    return finalize(body, W, h, "GitHub telemetry: contributions, commits, repositories, stars and languages")


def streak(d: dict, stamp: str, demo: bool) -> str:
    s = streaks(d["days"])
    since = dt.date.fromisoformat(d["since"]).strftime("%b %Y")
    plural = lambda n: f"{n} day" + ("" if n == 1 else "s")  # noqa: E731
    b = head("STREAK  ·  CONTRIBUTION CALENDAR", stamp, demo)
    b += metric_row(140, [(plural(s["current"]), "CURRENT STREAK", fmt_range(s["cur_range"])),
                          (plural(s["longest"]), "LONGEST STREAK", fmt_range(s["long_range"])),
                          (f"{d['total']:,}", "TOTAL CONTRIBUTIONS", f"since {since}")])
    y0 = 232
    b.append(f'<line x1="36" y1="{y0-20}" x2="{W-36}" y2="{y0-20}" stroke="{LINE}"/>')
    b.append(t(36, y0 + 6, "LAST 30 DAYS", "mono-m", 10.5, MUTE, tracking=2))
    series = last_n(d["days"], 30)
    peak = max((v for _, v in series), default=0) or 1
    gap, top, base = 6, y0 + 28, y0 + 96
    bw = (W - 72 - gap * 29) / 30
    for i, (day, v) in enumerate(series):
        x = 36 + i * (bw + gap)
        if v:
            hgt = max(6, (base - top) * v / peak)
            fill = G if day == dt.date.today() else (G2 if v / peak > 0.5 else "#166534")
            b.append(f'<rect x="{x:.1f}" y="{base-hgt:.1f}" width="{bw:.1f}" height="{hgt:.1f}" rx="2" fill="{fill}"/>')
        else:
            b.append(f'<rect x="{x:.1f}" y="{base-3}" width="{bw:.1f}" height="3" rx="1.5" fill="{LINE2}"/>')
    b.append(t(36, base + 24, series[0][0].strftime("%b %d"), "mono", 11, DIM))
    b.append(t(W - 36, base + 24, "today", "mono", 11, DIM, "end"))
    b.append(t(W / 2, base + 24, f"peak {peak} / day", "mono", 11, DIM, "middle"))
    h = base + 52
    body = panel(W, h, rx=16) + crop_marks(W, h, 12, 9) + "\n".join(b)
    return finalize(body, W, h, "Contribution streak and last 30 days of activity")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", ""))
    ap.add_argument("--out", default="dist")
    ap.add_argument("--demo", action="store_true", help="render watermarked sample data")
    args = ap.parse_args()

    if args.demo:
        data = demo_data()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token or not args.user:
            sys.exit("GITHUB_TOKEN and --user are required (or use --demo)")
        data = fetch(args.user, token)

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "telemetry.svg").write_text(telemetry(data, stamp, args.demo), encoding="utf-8")
    (out / "streak.svg").write_text(streak(data, stamp, args.demo), encoding="utf-8")
    print(f"wrote telemetry.svg, streak.svg to {out}/")


if __name__ == "__main__":
    main()

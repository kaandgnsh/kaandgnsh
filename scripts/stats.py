#!/usr/bin/env python3
"""
stats.py — generates assets/card-numbers.svg and assets/card-langs.svg
from live GitHub API data. Written to replace github-readme-stats /
streak-stats / github-readme-activity-graph: those are free shared
Vercel instances that routinely rate-limit or 503 under load (see
https://github.com/anuraghazra/github-readme-stats/issues/2130), which
took the whole `~/activity` section down with them. Self-hosting the
generation here means the only thing that can fail is the GitHub API
itself, and even then main() keeps the previous card untouched.
"""
import html
import json
import os
import sys
import urllib.request
import urllib.error

USERNAME = "kaandgnsh"
API = "https://api.github.com"

BG = "#0D1117"
BORDER = "#30363D"
TEXT_PRIMARY = "#E6EDF3"
TEXT_SECONDARY = "#8B949E"
GREEN = "#3FB950"
RED = "#8B0000"
DOT_GRAY1 = "#484F58"
DOT_GRAY2 = "#6E7681"
FONT = "SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace"


def esc(s):
    return html.escape(s, quote=True)


def api_get(path, token=None):
    req = urllib.request.Request(f"{API}{path}", headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


def fetch_account_stats(token):
    """Returns dict with public_repos, followers, total_stars, top_langs
    (list of (lang, bytes) sorted desc) — or None on any failure."""
    try:
        user = api_get(f"/users/{USERNAME}", token)
        repos = []
        page = 1
        while True:
            batch = api_get(f"/users/{USERNAME}/repos?per_page=100&page={page}&type=owner", token)
            if not batch:
                break
            repos.extend(batch)
            if len(batch) < 100:
                break
            page += 1

        total_stars = sum(r.get("stargazers_count", 0) for r in repos)
        lang_bytes = {}
        for r in repos:
            if r.get("fork"):
                continue
            try:
                langs = api_get(f"/repos/{USERNAME}/{r['name']}/languages", token)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
                print(f"warn: languages fetch failed for {r['name']}: {e}", file=sys.stderr)
                continue
            for lang, n in langs.items():
                lang_bytes[lang] = lang_bytes.get(lang, 0) + n

        top_langs = sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)[:5]
        return {
            "public_repos": user.get("public_repos", 0),
            "followers": user.get("followers", 0),
            "total_stars": total_stars,
            "top_langs": top_langs,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"warn: could not fetch account stats: {e}", file=sys.stderr)
        return None


def terminal_frame(w, h, path_label):
    return [
        f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="8" fill="{BG}" stroke="{BORDER}"/>',
        f'<rect x="0.5" y="0.5" width="{w-1}" height="30" rx="8" fill="#161B22" stroke="{BORDER}"/>',
        f'<rect x="0.5" y="22" width="{w-1}" height="8" fill="#161B22"/>',
        f'<circle cx="20" cy="15.5" r="5" fill="{RED}"/>',
        f'<circle cx="36" cy="15.5" r="5" fill="{DOT_GRAY1}"/>',
        f'<circle cx="52" cy="15.5" r="5" fill="{DOT_GRAY2}"/>',
        f'<text x="{w/2}" y="19.5" text-anchor="middle" font-family="{FONT}" font-size="12" '
        f'fill="{TEXT_SECONDARY}">{esc(path_label)}</text>',
    ]


def build_numbers_card(stats):
    w, h = 320, 210
    svg = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-label="account stats">']
    svg += terminal_frame(w, h, "~$ stat kaandgnsh")

    rows = [
        ("public repos", stats["public_repos"]),
        ("followers", stats["followers"]),
        ("total stars", stats["total_stars"]),
    ]
    y = 68
    svg.append(f'<text x="24" y="56" font-family="{FONT}" font-size="13" fill="{GREEN}">$ whoami --stats</text>')
    for label, value in rows:
        svg.append(f'<text x="24" y="{y}" font-family="{FONT}" font-size="13" fill="{TEXT_SECONDARY}">{esc(label)}</text>')
        svg.append(f'<text x="{w-24}" y="{y}" text-anchor="end" font-family="{FONT}" font-size="13" '
                    f'font-weight="700" fill="{TEXT_PRIMARY}">{value}</text>')
        y += 28

    svg.append(f'<line x1="24" y1="{y-6}" x2="{w-24}" y2="{y-6}" stroke="{BORDER}"/>')
    svg.append(f'<text x="24" y="{y+18}" font-family="{FONT}" font-size="11" fill="{TEXT_SECONDARY}">'
                f'updated automatically via <tspan fill="{GREEN}">GitHub Actions</tspan></text>')
    svg.append("</svg>")
    return "\n".join(svg)


def build_langs_card(stats):
    w = 320
    top_langs = stats["top_langs"] or [("Python", 1)]
    total = sum(n for _, n in top_langs) or 1
    row_h = 26
    h = 70 + row_h * len(top_langs) + 20

    svg = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-label="most used languages">']
    svg += terminal_frame(w, h, "~$ lang --top")
    svg.append(f'<text x="24" y="56" font-family="{FONT}" font-size="13" fill="{GREEN}">$ du -h --by-lang</text>')

    y = 70
    bar_max_w = w - 48 - 60
    for lang, n in top_langs:
        pct = n / total
        bar_w = max(4, int(bar_max_w * pct))
        svg.append(f'<text x="24" y="{y+13}" font-family="{FONT}" font-size="11.5" fill="{TEXT_PRIMARY}">{esc(lang)}</text>')
        svg.append(f'<rect x="24" y="{y+18}" width="{bar_max_w}" height="5" rx="2.5" fill="{BORDER}"/>')
        svg.append(f'<rect x="24" y="{y+18}" width="{bar_w}" height="5" rx="2.5" fill="{GREEN}"/>')
        svg.append(f'<text x="{w-24}" y="{y+13}" text-anchor="end" font-family="{FONT}" font-size="11" '
                    f'fill="{TEXT_SECONDARY}">{pct*100:.1f}%</text>')
        y += row_h
    svg.append("</svg>")
    return "\n".join(svg)


def main():
    token = os.environ.get("GITHUB_TOKEN")
    out_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    os.makedirs(out_dir, exist_ok=True)

    stats = fetch_account_stats(token)
    if stats is None:
        print("skip: keeping existing stats cards (API call failed)")
        return

    with open(os.path.join(out_dir, "card-numbers.svg"), "w") as f:
        f.write(build_numbers_card(stats))
    with open(os.path.join(out_dir, "card-langs.svg"), "w") as f:
        f.write(build_langs_card(stats))
    print(f"wrote stats cards: {stats}")


if __name__ == "__main__":
    main()

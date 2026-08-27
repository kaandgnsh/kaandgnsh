#!/usr/bin/env python3
"""
cards.py — generates the terminal-style project card SVGs under assets/
from live data pulled off the GitHub REST API (stars, forks, primary
language). Written for kaandgnsh/kaandgnsh; no code shared with any
other profile's generator.

Run manually:
    GITHUB_TOKEN=... python3 scripts/cards.py

In CI it's invoked by .github/workflows/cards.yml on a schedule, using
the workflow's own GITHUB_TOKEN, and any changed SVGs are committed back.
"""
import html
import json
import os
import sys
import urllib.request
import urllib.error

USERNAME = "kaandgnsh"
API = "https://api.github.com"

# Curated list: (repo, display title, description lines, tags, filename).
# Repos are picked by hand, not auto-listed — see README `~/projects`
# for why the rest of the account isn't shown here.
FEATURED = [
    {
        "repo": "hider",
        "title": "hider",
        "desc": [
            "Automated IP-rotation utility for Linux.",
            "Cycles network identity on a timer to keep",
            "long-running sessions from sitting on one exit node.",
        ],
        "tags": ["PYTHON", "LINUX", "PRIVACY"],
        "filename": "hider.py",
    },
    {
        "repo": "m-finder",
        "title": "m-finder",
        "desc": [
            "Admin-panel discovery tool for authorized",
            "web reconnaissance. Threaded scanning against",
            "a wordlist, protocol auto-detection.",
        ],
        "tags": ["PYTHON", "RECON", "WEB-SECURITY"],
        "filename": "m-finder-v4.py",
    },
    {
        "repo": "m-copy",
        "title": "m-copy",
        "desc": [
            "Grabs and saves the rendered source of a",
            "given URL under a name and path you choose.",
            "Small utility for quick page snapshots.",
        ],
        "tags": ["PYTHON", "AUTOMATION"],
        "filename": "m-copy.py",
    },
]

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


def fetch_repo(repo):
    """Best-effort live lookup. Falls back to None on any failure
    (rate limit, network hiccup, repo renamed) so a bad API day never
    breaks the build — the card just keeps its last committed stats."""
    url = f"{API}/repos/{USERNAME}/{repo}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"warn: could not fetch {repo}: {e}", file=sys.stderr)
        return None


def build_card(entry, stars, lang):
    w = 460
    y = 56
    body = []
    body.append((24, y, 13, GREEN, f"$ cat {entry['filename']}", False))
    y += 26
    body.append((24, y, 15, TEXT_PRIMARY, entry["title"], True))
    y += 22
    for line in entry["desc"]:
        body.append((24, y, 12, TEXT_SECONDARY, line, False))
        y += 17
    y += 10
    tags_top = y - 13
    divider_y = tags_top + 20 + 14
    footer_y = divider_y + 20
    h = footer_y + 14

    svg = [
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="{esc(entry["title"])} project card">',
        f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="8" fill="{BG}" stroke="{BORDER}"/>',
        f'<rect x="0.5" y="0.5" width="{w-1}" height="30" rx="8" fill="#161B22" stroke="{BORDER}"/>',
        f'<rect x="0.5" y="22" width="{w-1}" height="8" fill="#161B22"/>',
        f'<circle cx="20" cy="15.5" r="5" fill="{RED}"/>',
        f'<circle cx="36" cy="15.5" r="5" fill="{DOT_GRAY1}"/>',
        f'<circle cx="52" cy="15.5" r="5" fill="{DOT_GRAY2}"/>',
        f'<text x="{w/2}" y="19.5" text-anchor="middle" font-family="{FONT}" font-size="12" '
        f'fill="{TEXT_SECONDARY}">~/projects/{esc(entry["repo"])}</text>',
    ]
    for x, ty, size, color, text, bold in body:
        weight = ' font-weight="700"' if bold else ""
        svg.append(f'<text x="{x}" y="{ty}" font-family="{FONT}" font-size="{size}"{weight} '
                    f'fill="{color}">{esc(text)}</text>')

    x = 24
    for tag in entry["tags"]:
        tw = 14 + len(tag) * 7
        svg.append(f'<rect x="{x}" y="{tags_top}" width="{tw}" height="20" rx="4" fill="none" '
                    f'stroke="{GREEN}" stroke-opacity="0.55"/>')
        svg.append(f'<text x="{x+tw/2}" y="{tags_top+14}" text-anchor="middle" font-family="{FONT}" '
                    f'font-size="10.5" fill="{GREEN}">{esc(tag)}</text>')
        x += tw + 8

    svg.append(f'<line x1="0.5" y1="{divider_y}" x2="{w-0.5}" y2="{divider_y}" stroke="{BORDER}"/>')
    svg.append(f'<text x="24" y="{footer_y}" font-family="{FONT}" font-size="11" '
                f'fill="{TEXT_SECONDARY}">lang: <tspan fill="{TEXT_PRIMARY}">{esc(lang)}</tspan></text>')
    svg.append(f'<text x="{w-24}" y="{footer_y}" text-anchor="end" font-family="{FONT}" '
                f'font-size="11" fill="{GREEN}">&#9733; {stars}</text>')
    svg.append("</svg>")
    return "\n".join(svg)


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    os.makedirs(out_dir, exist_ok=True)

    for entry in FEATURED:
        data = fetch_repo(entry["repo"])
        if data:
            stars = data.get("stargazers_count", 0)
            lang = data.get("language") or "Python"
        else:
            # keep previous card untouched if the API call failed
            path = os.path.join(out_dir, f"card-{entry['repo']}.svg")
            if os.path.exists(path):
                print(f"skip: keeping existing card for {entry['repo']}")
                continue
            stars, lang = 0, "Python"

        svg = build_card(entry, stars, lang)
        path = os.path.join(out_dir, f"card-{entry['repo']}.svg")
        with open(path, "w") as f:
            f.write(svg)
        print(f"wrote {path} (stars={stars}, lang={lang})")


if __name__ == "__main__":
    main()

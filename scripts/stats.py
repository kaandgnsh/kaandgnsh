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

import sys
import urllib.error
import html
import json
import os
import urllib.request
import urllib.parse
import html
from collections import Counter
from datetime import datetime

USERNAME = "kaandgnsh"
API = "https://api.github.com"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")

BG = "#0D1117"
BORDER = "#30363D"
PRIMARY = "#E6EDF3"
SECONDARY = "#8B949E"
GREEN = "#3FB950"
RED = "#8B0000"
FONT = "SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace"

TOKEN = os.environ.get("GITHUB_TOKEN")


def api_get(url):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "kaandgnsh-profile-stats",
        },
    )

    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")

    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def esc(value):
    return html.escape(str(value), quote=True)


def rect(x, y, w, h, fill=BG, stroke=BORDER, rx=8):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
        f'rx="{rx}" fill="{fill}" stroke="{stroke}"/>'
    )


def text(x, y, value, size=12, color=SECONDARY, bold=False):
    weight = ' font-weight="700"' if bold else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" '
        f'font-size="{size}"{weight} fill="{color}">{esc(value)}</text>'
    )


def get_user():
    return api_get(f"{API}/users/{USERNAME}")


def get_repositories():
    repos = []
    page = 1

    while True:
        url = (
            f"{API}/users/{USERNAME}/repos"
            f"?per_page=100&page={page}&type=owner"
        )

        batch = api_get(url)

        if not batch:
            break

        repos.extend(batch)

        if len(batch) < 100:
            break

        page += 1

    return [r for r in repos if not r.get("fork", False)]


def generate_stats(user, repos):
    stars = sum(r.get("stargazers_count", 0) for r in repos)

    width = 495
    height = 190

    svg = [
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img">',
        rect(0, 0, width, height),
        text(24, 32, "~/github/stats", 13, GREEN),
        text(24, 70, "Public repositories", 12, SECONDARY),
        text(24, 96, user.get("public_repos", 0), 20, PRIMARY, True),
        text(180, 70, "Followers", 12, SECONDARY),
        text(180, 96, user.get("followers", 0), 20, PRIMARY, True),
        text(320, 70, "Stars", 12, SECONDARY),
        text(320, 96, stars, 20, PRIMARY, True),
        f'<line x1="24" y1="120" x2="471" y2="120" stroke="{BORDER}"/>',
        text(24, 148, "Account", 11, SECONDARY),
        text(100, 148, f"@{USERNAME}", 11, PRIMARY),
        text(24, 173, "Updated", 11, SECONDARY),
        text(
            100,
            173,
            datetime.utcnow().strftime("%Y-%m-%d"),
            11,
            PRIMARY,
        ),
        "</svg>",
    ]

    return "\n".join(svg)


def generate_languages(repos):
    languages = Counter()

    for repo in repos:
        try:
            data = api_get(repo["languages_url"])

            for language, amount in data.items():
                languages[language] += amount

        except Exception as error:
            print(
                f"warning: language lookup failed for "
                f"{repo['name']}: {error}"
            )

    total = sum(languages.values())

    width = 495
    height = 190

    svg = [
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img">',
        rect(0, 0, width, height),
        text(24, 32, "~/github/languages", 13, GREEN),
    ]

    top = languages.most_common(6)

    if not top:
        svg.append(text(24, 75, "No language data available", 12))
    else:
        y = 65

        for language, amount in top:
            percentage = amount / total * 100 if total else 0

            svg.append(
                text(
                    24,
                    y,
                    language,
                    12,
                    PRIMARY,
                    True,
                )
            )

            svg.append(
                text(
                    440,
                    y,
                    f"{percentage:.1f}%",
                    12,
                    GREEN,
                )
            )

            svg.append(
                f'<rect x="24" y="{y + 9}" width="420" height="6" '
                f'rx="3" fill="{BORDER}"/>'
            )

            bar_width = max(2, 420 * percentage / 100)

            svg.append(
                f'<rect x="24" y="{y + 9}" width="{bar_width:.1f}" '
                f'height="6" rx="3" fill="{GREEN}"/>'
            )

            y += 27

    svg.append("</svg>")

    return "\n".join(svg)


def generate_activity():
    """
    Download GitHub's own public contribution graph and wrap it
    inside our local SVG.

    GitHub exposes the public contribution calendar at:
    /users/<username>/contributions
    """

    url = f"https://github.com/users/{USERNAME}/contributions"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "kaandgnsh-profile-stats",
        },
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8")

    start = raw.find("<svg")
    end = raw.rfind("</svg>")

    if start == -1 or end == -1:
        raise RuntimeError("Could not find contribution SVG")

    contribution_svg = raw[start:end + len("</svg>")]

    width = 1000
    height = 190

    svg = [
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img">',
        rect(0, 0, width, height),
        text(24, 32, "~/github/activity", 13, GREEN),
        f'<g transform="translate(20, 48) scale(1.25)">',
        contribution_svg,
        "</g>",
        "</svg>",
    ]

    return "\n".join(svg)


def main():
    os.makedirs(OUT, exist_ok=True)

    print("Fetching GitHub profile...")
    user = get_user()

    print("Fetching repositories...")
    repos = get_repositories()

    print(f"Found {len(repos)} repositories.")

    print("Generating stats.svg...")
    with open(
        os.path.join(OUT, "stats.svg"),
        "w",
        encoding="utf-8",
    ) as file:
        file.write(generate_stats(user, repos))

    print("Generating languages.svg...")
    with open(
        os.path.join(OUT, "languages.svg"),
        "w",
        encoding="utf-8",
    ) as file:
        file.write(generate_languages(repos))

    print("Generating activity.svg...")
    with open(
        os.path.join(OUT, "activity.svg"),
        "w",
        encoding="utf-8",
    ) as file:
        file.write(generate_activity())

    print("Done.")


if __name__ == "__main__":
    main()

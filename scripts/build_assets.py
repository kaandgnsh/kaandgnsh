#!/usr/bin/env python3
"""Build every static SVG in assets/ from one place.

Edit the CONTENT section below (text, projects, links), then run:

    pip install fonttools
    python scripts/build_assets.py

Live stats are not built here; see generate_cards.py (runs in GitHub Actions).
"""

from __future__ import annotations

import math
import random
from html import escape
from pathlib import Path

from svgkit import (DIM, G, G2, G3, GTXT, INK, LINE, LINE2, MUTE, PANEL, PANEL2,
                    RED, ROOT, TXT, TXT2, chip, crop_marks, finalize, panel, t,
                    width, wrap)

OUT = ROOT / "assets"
W = 900  # content width shared by every module

# =============================================================================
# CONTENT — everything a person would want to edit lives here
# =============================================================================
NAME = "Kaan Doğan"
HANDLE = "kaandgnsh"
ROLE = "Software Engineering Student"
ROLE2 = "Security-focused Developer"

SPECS = [  # header spec row: label, value, sub-value
    ("FOCUS", "Secure software", "development"),
    ("IN TRAINING", "Penetration testing", "Web & network security"),
    ("BASE", "OSTİM Technical University", "Ankara, Türkiye"),
]

RADAR_TARGETS = [  # label, angle in degrees (0 = east, clockwise), radius fraction
    ("WEB", -38, 0.72), ("NET", 205, 0.86), ("SYS", 128, 0.52), ("SEC", 300, 0.34),
]

TERMINAL = [  # ("cmd", text) are typed; ("out", [(text, color), ...]) appear
    ("cmd", "whoami"),
    ("out", [("Kaan Doğan", TXT), (" · Software Engineering Student · OSTİM Technical University", TXT2)]),
    ("cmd", "cat mission.txt"),
    ("out", [("Understand how systems work, how they break, and how to make them secure.", TXT2)]),
    ("cmd", "ls focus/"),
    ("out", [("secure-software/   web-security/   ", TXT), ("pentesting/*   networking/*", GTXT)]),
    ("out", [("* in training", MUTE)]),
    ("cmd", "./status --projects"),
    ("out", [("[ ", MUTE), ("OK", GTXT), (" ] ", MUTE), ("argus", TXT), ("  osint framework · 32 providers · 37 tests in CI", TXT2)]),
    ("out", [("[ ", MUTE), ("OK", GTXT), (" ] ", MUTE), ("safe defaults", TXT), ("  validate input · ask before acting · fail closed", TXT2)]),
    ("out", [("[ ", MUTE), ("..", RED), (" ] ", MUTE), ("training", TXT), ("  pentesting · web & network security", TXT2)]),
]

PRINCIPLES = [  # index, word, colour, line
    ("01", "build", TXT, "Small tools that do one job well, tested from the first commit."),
    ("02", "break", RED, "Learn where systems fail: inputs, protocols and trust boundaries."),
    ("03", "secure", GTXT, "Ship safe defaults: validate, ask before acting, fail closed."),
]

SECTIONS = {  # file stem: (index, title, path label)
    "s-about": ("01", "About", "~/about.md"),
    "s-arsenal": ("02", "Arsenal", "~/stack --all"),
    "s-operations": ("03", "Operations", "~/projects"),
    "s-telemetry": ("04", "Telemetry", "gh api /users/kaandgnsh"),
    "s-channels": ("05", "Channels", "~/contact"),
}

ARSENAL = {
    "LANGUAGES": ["Python", "C", "C++", "Java", "JavaScript", "SQL"],
    "SYSTEMS & TOOLING": ["Linux · CachyOS", "Terminal / Bash", "Git & GitHub",
                          "GitHub Actions", "Docker", "VS Code"],
    "SECURITY": [("Security fundamentals", True), ("Web security", True),
                 ("Penetration testing", False), ("System & network security", False)],
}

FEATURED = {
    "id": "OP-01", "name": "Argus", "url": "github.com/kaandgnsh/Argus",
    "tagline": ("Modular OSINT and reconnaissance framework for public-source research, "
                "entity correlation and local reporting."),
    "pipeline": [  # label, value, sub
        ("INPUT", "10 target types", "domain · ip · email · user"),
        ("PROVIDERS", "32 modules", "dns · rdap · ct · threat intel"),
        ("CORRELATE", "entity graph", "sqlite · cases · evidence"),
        ("REPORT", "5 formats", "json · html · csv · md · dot"),
    ],
    "points": [
        "SSRF guard: private-address blocking with pinned DNS against rebinding",
        "Redirects re-validated, default response-size cap on every request",
        "Archive inspection bounded by member, size and path limits",
        "Untrusted content escaped before it reaches Markdown reports",
    ],
    "meta": [("LANGUAGE", "Python 3.10+"), ("SIZE", "~9k lines"),
             ("ARCHITECTURE", "16 modules · 32 providers"), ("TESTS", "37 · pytest · CI"),
             ("PLATFORMS", "Linux · macOS · Win · Termux"), ("LICENSE", "MIT")],
    "chips": ["PYTHON", "OSINT", "SQLITE", "SSRF-HARDENED", "PYTEST", "CI"],
    "note": "authorized research only",
}

PROJECTS = [
    {"id": "OP-02", "name": "m-dos", "file": "p-m-dos", "meta": "loopback-only · ≤ 60 req · ≤ 30 s",
     "desc": ("HTTP response-time analyzer for local labs. Bounded sampling on one worker, "
              "latency summary as JSON, and strict target validation that rejects remote "
              "hosts, odd schemes and embedded credentials."),
     "chips": ["PYTHON", "STDLIB ONLY", "UNIT TESTS", "CI"]},
    {"id": "OP-03", "name": "hider", "file": "p-hider", "meta": "tor · anonsurf · proxy",
     "desc": ("IP-rotation utility for controlled privacy labs. Speaks Tor's control protocol "
              "over a raw socket with SAFECOOKIE + HMAC verification, asks before touching "
              "torrc, and ships a hardened systemd unit."),
     "chips": ["PYTHON", "TOR CONTROL PROTOCOL", "SYSTEMD", "UNIT TESTS", "CI"]},
]

ARCHIVE = [  # smaller tiles under the main operations
    {"name": "all-pip-installer", "file": "a-all-pip", "line": "Dry-run-first installer for curated Python package profiles."},
    {"name": "m-info-get", "file": "a-m-info-get", "line": "Early OSINT experiment with phone-number and username lookups."},
]

CHANNELS = [  # file stem, glyph, label, handle   (add more and re-run)
    ("c-email", "@", "Email", "dogankaan217@gmail.com"),
    ("c-linkedin", "in", "LinkedIn", "in/kaan-doğan"),
    ("c-instagram", "ig", "Instagram", "@kaandgn.sh"),
    # ("c-tryhackme", "th", "TryHackMe", "USERNAME"),
    # ("c-htb", "htb", "Hack The Box", "USERNAME"),
    # ("c-site", "www", "Website", "example.com"),
]


# =============================================================================
# MODULES
# =============================================================================
def save(stem: str, svg: str) -> None:
    path = OUT / f"{stem}.svg"
    path.write_text(svg, encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}  {len(svg) / 1024:.1f} KB")


def tspans(parts, cls=None) -> str:
    c = f' class="{cls}"' if cls else ""
    return "".join(f'<tspan fill="{col}"{c}>{escape(txt, quote=False)}</tspan>' for txt, col in parts)


def header() -> None:
    w, h = 1200, 470
    b = [panel(w, h, rx=18), crop_marks(w, h, 16, 12)]

    # top bar
    b.append(f'<text x="44" y="38" class="mono-m" font-size="12" letter-spacing="3" fill="{TXT2}">'
             f'<tspan fill="{G}">◆</tspan> {HANDLE.upper()}<tspan fill="{DIM}">  /  PROFILE.SYS</tspan></text>')
    b.append(t(w - 44, 38, "SESSION ESTABLISHED", "mono-m", 12, GTXT, "end", 2.5))
    sx = w - 44 - width("SESSION ESTABLISHED", "mono-m", 12, 2.5) - 16
    b.append(f'<circle cx="{sx:.1f}" cy="34" r="4" fill="{G}" class="pulse"/>')
    b.append(t(sx - 18, 38, "39.93°N  32.86°E", "mono", 12, MUTE, "end", 1.5))
    b.append(f'<line x1="1" y1="58" x2="{w-1}" y2="58" stroke="{LINE}"/>')

    # identity
    x0 = 68
    b.append(t(x0, 132, "// OPERATOR", "mono-m", 13, GTXT, tracking=3.5))
    size = 94
    nw = width(NAME, "display", size, -2.5)
    b.append(f'<clipPath id="reveal"><rect x="{x0-6}" y="150" width="0" height="120">'
             f'<animate attributeName="width" from="0" to="{nw+30:.0f}" begin="0.45s" dur="1.35s" '
             f'fill="freeze" calcMode="spline" keySplines="0.65 0 0.35 1" keyTimes="0;1"/></rect></clipPath>')
    b.append(f'<g clip-path="url(#reveal)">'
             + t(x0 - 3, 242, NAME, "display", size, "url(#silver)", tracking=-2.5) + "</g>")
    # decrypt band: scrambled glyphs riding the reveal edge
    rnd = random.Random(42)
    pool = "01#$%&*/<>?@[]{}=+~^ABCDEFGHKXZ"
    frames = ["".join(rnd.choice(pool) for _ in range(14)) for _ in range(3)]
    band = (f'<clipPath id="band"><rect x="{x0-6}" y="150" width="96" height="120">'
            f'<animate attributeName="x" from="{x0-6}" to="{x0+nw+24:.0f}" begin="0.45s" dur="1.35s" '
            f'fill="freeze" calcMode="spline" keySplines="0.65 0 0.35 1" keyTimes="0;1"/></rect></clipPath>')
    b.append(band)
    b.append('<g clip-path="url(#band)" opacity="1">'
             + "".join(f'<text x="{x0}" y="236" class="mono-m f{i+1}" font-size="74" fill="{G}" '
                       f'letter-spacing="2">{escape(f, quote=False)}</text>' for i, f in enumerate(frames))
             + '<animate attributeName="opacity" from="1" to="0" begin="1.65s" dur="0.3s" fill="freeze"/></g>')
    b.append(f'<rect x="{x0-6}" y="160" width="2" height="96" fill="{G}" opacity="0">'
             f'<animate attributeName="x" from="{x0-6}" to="{x0+nw+24:.0f}" begin="0.45s" dur="1.35s" '
             f'fill="freeze" calcMode="spline" keySplines="0.65 0 0.35 1" keyTimes="0;1"/>'
             f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.85;1" begin="0.45s" dur="1.5s" fill="freeze"/></rect>')

    role_size = 24
    while width(f"{ROLE}  ·  {ROLE2}", "sans", role_size) > 740:
        role_size -= 1
    b.append(f'<text x="{x0}" y="290" class="sans" font-size="{role_size}" fill="{TXT2}">'
             f'{escape(ROLE)}<tspan fill="{DIM}">  ·  </tspan>{escape(ROLE2)}</text>')

    # spec row
    b.append(f'<line x1="{x0}" y1="330" x2="800" y2="330" stroke="{LINE2}"/>')
    colw = (800 - x0) / 3
    for i, (label, val, sub) in enumerate(SPECS):
        cx = x0 + i * colw + (22 if i else 0)
        if i:
            b.append(f'<line x1="{x0 + i*colw:.1f}" y1="348" x2="{x0 + i*colw:.1f}" y2="412" stroke="{LINE}"/>')
        b.append(t(cx, 362, label, "mono-m", 11, MUTE, tracking=2.5))
        b.append(t(cx, 388, val, "sans-m", 16, TXT))
        b.append(t(cx, 410, sub, "sans", 14.5, TXT2))

    # bottom bar
    b.append(f'<line x1="1" y1="432" x2="{w-1}" y2="432" stroke="{LINE}"/>')
    b.append(f'<text x="44" y="456" class="mono" font-size="12.5" letter-spacing="1" fill="{MUTE}">'
             f'<tspan fill="{TXT}">build</tspan>  →  <tspan fill="{RED}">break</tspan>  →  '
             f'<tspan fill="{GTXT}">secure</tspan></text>')
    b.append(f'<text x="{w-44}" y="456" class="mono" font-size="12.5" letter-spacing="1" fill="{MUTE}" '
             f'text-anchor="end">learning in public<tspan class="blink" fill="{G}"> ▍</tspan></text>')

    # radar
    cx, cy, r = 1000, 228, 150
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{r+14}" fill="none" stroke="{DIM}" '
             f'stroke-dasharray="1 {2*math.pi*(r+14)/120 - 1:.3f}"/>')
    for rr, col in ((r, LINE2), (r * 0.66, LINE), (r * 0.33, LINE)):
        b.append(f'<circle cx="{cx}" cy="{cy}" r="{rr:.1f}" fill="none" stroke="{col}"/>')
    b.append(f'<path d="M{cx-r-24} {cy}H{cx+r+24}M{cx} {cy-r-24}V{cy+r+24}" stroke="{LINE}"/>')
    # sweep wedge (40°) rotating
    a1 = math.radians(-40)
    wx, wy = cx + r * math.cos(a1), cy + r * math.sin(a1)
    b.append(f'<linearGradient id="sweep" gradientUnits="userSpaceOnUse" x1="{cx+r}" y1="{cy}" '
             f'x2="{wx:.1f}" y2="{wy:.1f}"><stop offset="0" stop-color="{G}" stop-opacity="0.28"/>'
             f'<stop offset="1" stop-color="{G}" stop-opacity="0"/></linearGradient>')
    b.append(f'<g><path d="M{cx} {cy}L{cx+r} {cy}A{r} {r} 0 0 0 {wx:.1f} {wy:.1f}Z" fill="url(#sweep)"/>'
             f'<line x1="{cx}" y1="{cy}" x2="{cx+r}" y2="{cy}" stroke="{G}" stroke-opacity="0.8"/>'
             f'<animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" '
             f'to="360 {cx} {cy}" dur="9s" repeatCount="indefinite"/></g>')
    for i, (label, deg, frac) in enumerate(RADAR_TARGETS):
        a = math.radians(deg)
        px, py = cx + r * frac * math.cos(a), cy + r * frac * math.sin(a)
        right = math.cos(a) >= 0
        lx = px + (14 if right else -14)
        b.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="9" fill="none" stroke="{G}" stroke-opacity="0.35" '
                 f'class="ping" style="animation-delay:{i*0.7:.1f}s"/>')
        b.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="{GTXT}"/>')
        b.append(t(lx, py + 4, label, "mono-m", 11, TXT2, "start" if right else "end", 2))
    b.append(f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="{TXT}"/>')
    b.append(t(cx, cy + r + 36, "SCAN · FOCUS AREAS", "mono", 10.5, DIM, "middle", 3))

    css = """
.blink{animation:blink 1.1s step-end infinite}
@keyframes blink{50%{opacity:0}}
.pulse{animation:pulse 2.4s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.ping{transform-box:fill-box;transform-origin:center;animation:ping 2.8s ease-out infinite}
@keyframes ping{0%{transform:scale(.4);opacity:0}25%{opacity:1}100%{transform:scale(2.2);opacity:0}}
.f1,.f2,.f3{animation:flick .21s step-end infinite}
.f2{animation-delay:-.07s}.f3{animation-delay:-.14s}
@keyframes flick{0%{opacity:1}33.3%{opacity:0}}
"""
    save("header", finalize("\n".join(b), w, h,
                            f"{NAME} — {ROLE}, {ROLE2}",
                            "Profile banner: name, role, focus areas and a radar of security focus areas.",
                            extra_css=css))


def terminal() -> None:
    size, lh, x0, y0 = 15, 30, 32, 92
    cw = width("M", "mono", size)
    h = y0 + lh * (len(TERMINAL) + 1) + 6
    b = [panel(W, h, rx=14, glow=False)]
    b.append(f'<rect x="1" y="1" width="{W-2}" height="{h-2}" rx="14" fill="url(#scan)" opacity="0.5"/>')
    for i in range(3):
        b.append(f'<circle cx="{28 + i*18}" cy="24" r="5" fill="{LINE2}"/>')
    b.append(t(W / 2, 29, f"kaan@ostim — zsh — {HANDLE}", "mono", 12, MUTE, "middle", 1))
    b.append(f'<line x1="1" y1="48" x2="{W-1}" y2="48" stroke="{LINE}"/>')

    prompt = [("kaan@ostim", GTXT), (" ~ $ ", MUTE)]
    pw = width("kaan@ostim ~ $ ", "mono", size)
    clock, step = 0.35, 0.045
    for i, (kind, val) in enumerate(TERMINAL):
        y = y0 + i * lh
        if kind == "cmd":
            n = len(val)
            widths = ";".join(f"{k*cw:.1f}" for k in range(n + 1))
            dur = max(n * step, 0.1)
            b.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{clock:.2f}s" fill="freeze"/>'
                     f'<text x="{x0}" y="{y}" class="mono" font-size="{size}">{tspans(prompt)}</text></g>')
            clock += 0.25
            b.append(f'<clipPath id="c{i}"><rect x="{x0+pw:.1f}" y="{y-20}" width="0" height="28">'
                     f'<animate attributeName="width" values="{widths}" calcMode="discrete" '
                     f'begin="{clock:.2f}s" dur="{dur:.2f}s" fill="freeze"/></rect></clipPath>')
            b.append(f'<g clip-path="url(#c{i})">' + t(x0 + pw, y, val, "mono", size, TXT) + "</g>")
            clock += dur + 0.3
        else:
            b.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{clock:.2f}s" fill="freeze"/>'
                     f'<text x="{x0}" y="{y}" class="mono" font-size="{size}">{tspans(val)}</text></g>')
            clock += 0.12
    y = y0 + len(TERMINAL) * lh
    b.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{clock:.2f}s" fill="freeze"/>'
             f'<text x="{x0}" y="{y}" class="mono" font-size="{size}">{tspans(prompt)}'
             f'<tspan class="blink" fill="{G}">▍</tspan></text></g>')
    css = ".blink{animation:blink 1.1s step-end infinite}@keyframes blink{50%{opacity:0}}"
    save("terminal", finalize("\n".join(b), W, h, "Terminal session: whoami",
                              "whoami: Kaan Doğan, Software Engineering Student at OSTİM Technical University. "
                              "Mission: understand how systems work, how they break, and how to make them secure.",
                              extra_css=css))


def section(stem: str, idx: str, title: str, path: str) -> None:
    h = 64
    b = [panel(W, h, rx=12, glow=False, grid=False)]
    b.append(t(26, 40, idx, "mono-m", 13, GTXT, tracking=1))
    b.append(t(54, 40, "/", "mono", 13, DIM))
    b.append(t(74, 41, title.upper(), "display", 21, TXT, tracking=4))
    tx = 74 + width(title.upper(), "display", 21, 4) + 22
    px = W - 26 - width(path, "mono", 12, 0.5) - 22
    b.append(f'<line x1="{tx:.1f}" y1="36" x2="{px:.1f}" y2="36" stroke="{LINE2}"/>')
    b.append(f'<rect x="{px-4:.1f}" y="33.5" width="5" height="5" fill="{G}"/>')
    b.append(t(W - 26, 40, path, "mono", 12, MUTE, "end", 0.5))
    save(stem, finalize("\n".join(b), W, h, f"{idx} — {title}"))


def arsenal() -> None:
    pad, gap = 36, 28
    colw = (W - 2 * pad - 2 * gap) / 3
    h = 380
    b = [panel(W, h, rx=16), crop_marks(W, h, 12, 9)]
    for ci, (head, items) in enumerate(ARSENAL.items()):
        x = pad + ci * (colw + gap)
        b.append(t(x, 52, head, "mono-m", 11.5, GTXT, tracking=2.5))
        b.append(f'<line x1="{x}" y1="68" x2="{x+colw:.1f}" y2="68" stroke="{LINE2}"/>')
        b.append(f'<rect x="{x}" y="66.5" width="18" height="3" fill="{G}"/>')
        y = 106
        for k, item in enumerate(items):
            b.append(t(x, y, f"{k+1:02d}", "mono", 11.5, DIM))
            if isinstance(item, tuple):
                name, active = item
                b.append(t(x + 32, y, name, "sans-m", 16.5, TXT))
                label = "● active" if active else "○ in training"
                b.append(t(x + 32, y + 21, label, "mono", 11.5, GTXT if active else MUTE, tracking=0.5))
                y += 50
            else:
                b.append(t(x + 32, y, item, "sans-m", 16.5, TXT))
                y += 38
    b.append(f'<line x1="{pad}" y1="{h-50}" x2="{W-pad}" y2="{h-50}" stroke="{LINE}"/>')
    b.append(f'<text x="{pad}" y="{h-24}" class="mono" font-size="11.5" fill="{MUTE}" letter-spacing="0.5">'
             f'<tspan fill="{GTXT}">●</tspan> active   ○ in training</text>')
    b.append(t(W - pad, h - 24, "no skill bars, just what I actually use", "mono", 11.5, DIM, "end", 0.5))
    save("arsenal", finalize("\n".join(b), W, h, "Arsenal: languages, tooling and security skills",
                             "Languages: Python, C, C++, Java, JavaScript, SQL. Tooling: Linux (CachyOS), "
                             "terminal, Git, GitHub Actions, Docker, VS Code. Security: fundamentals and web "
                             "security active; penetration testing and system/network security in training."))


def chips_row(x, y, labels, active=True, gap=8):
    out, cx = [], x
    for lab in labels:
        svg, cw = chip(cx, y, lab, active, 11)
        out.append(svg)
        cx += cw + gap
    return "\n".join(out)


def featured() -> None:
    p = FEATURED
    pad = 44
    inner = W - 2 * pad
    tag = wrap(p["tagline"], "sans", 18, inner)
    y_tag = 170
    # pipeline geometry
    y_pipe = y_tag + (len(tag) - 1) * 27 + 40
    n, gap = len(p["pipeline"]), 30
    node_w, node_h = (inner - gap * (n - 1)) / n, 118
    # lower columns
    y_low = y_pipe + node_h + 50
    left_w, meta_x = 452, 540
    pts = [wrap(s, "sans", 15, left_w - 26) for s in p["points"]]
    y = y_low + 34
    for lines in pts:
        y += len(lines) * 22 + 16
    meta_h = len(p["meta"]) * 48 + 18
    h = int(max(y, y_low + meta_h) + 74)

    b = [panel(W, h, rx=18), crop_marks(W, h, 14, 10)]
    b.append(t(pad, 54, f"FLAGSHIP  ·  {p['id']}", "mono-m", 12, GTXT, tracking=3))
    b.append(t(W - pad, 54, f"{p['url']}  ↗", "mono", 12, MUTE, "end", 0.5))
    b.append(t(pad - 3, 130, p["name"], "display", 66, "url(#silver)", tracking=-1.5))
    for i, line in enumerate(tag):
        b.append(t(pad, y_tag + i * 27, line, "sans", 18, TXT2))

    # pipeline: input → providers → correlate → report
    for i, (label, value, sub) in enumerate(p["pipeline"]):
        x = pad + i * (node_w + gap)
        b.append(f'<rect x="{x:.1f}" y="{y_pipe}" width="{node_w:.1f}" height="{node_h}" rx="12" '
                 f'fill="{PANEL2}" stroke="{LINE2}"/>')
        b.append(f'<rect x="{x:.1f}" y="{y_pipe}" width="3" height="{node_h}" rx="1.5" fill="{G2}" opacity="0.9"/>')
        b.append(t(x + 18, y_pipe + 28, f"{i+1:02d}  {label}", "mono-m", 10.5, GTXT, tracking=2))
        b.append(t(x + 18, y_pipe + 58, value, "sans-m", 18, TXT))
        sub_lines, cur = [], ""
        for tok in sub.split(" · "):
            trial = f"{cur} · {tok}" if cur else tok
            if cur and width(trial, "mono", 11.5) > node_w - 30:
                sub_lines.append(cur)
                cur = tok
            else:
                cur = trial
        sub_lines.append(cur)
        for j, line in enumerate(sub_lines[:2]):
            b.append(t(x + 18, y_pipe + 84 + j * 17, line, "mono", 11.5, MUTE))
        if i < n - 1:
            x1, x2, cy = x + node_w + 4, x + node_w + gap - 4, y_pipe + node_h / 2
            b.append(f'<line x1="{x1:.1f}" y1="{cy}" x2="{x2:.1f}" y2="{cy}" stroke="{G2}" '
                     f'stroke-dasharray="3 3" class="flow"/>')
            b.append(f'<path d="M{x2-5:.1f} {cy-4}L{x2:.1f} {cy}L{x2-5:.1f} {cy+4}" fill="none" stroke="{G}"/>')
            b.append(f'<circle r="2.2" fill="{GTXT}"><animateMotion dur="1.6s" repeatCount="indefinite" '
                     f'begin="{i*0.5:.1f}s" path="M{x1:.1f} {cy}H{x2-6:.1f}"/></circle>')

    # hardening column
    b.append(t(pad, y_low, "HARDENING", "mono-m", 11, MUTE, tracking=2.5))
    b.append(f'<line x1="{pad}" y1="{y_low+12}" x2="{pad+left_w}" y2="{y_low+12}" stroke="{LINE}"/>')
    y = y_low + 42
    for lines in pts:
        b.append(f'<rect x="{pad+1}" y="{y-10}" width="7" height="7" fill="{G}" transform="rotate(45 {pad+4.5} {y-6.5})"/>')
        for j, line in enumerate(lines):
            b.append(t(pad + 24, y + j * 22, line, "sans", 15, TXT))
        y += len(lines) * 22 + 16

    # meta panel
    mw = W - pad - meta_x
    b.append(f'<rect x="{meta_x}" y="{y_low-14}" width="{mw}" height="{meta_h}" rx="12" fill="{PANEL2}" stroke="{LINE}"/>')
    for i, (k, v) in enumerate(p["meta"]):
        yy = y_low - 14 + 30 + i * 48
        b.append(t(meta_x + 20, yy, k, "mono-m", 10, MUTE, tracking=2))
        b.append(t(meta_x + 20, yy + 20, v, "mono-m", 13.5, TXT))
        if i < len(p["meta"]) - 1:
            b.append(f'<line x1="{meta_x+20}" y1="{yy+32}" x2="{W-pad-20}" y2="{yy+32}" stroke="{LINE}"/>')

    b.append(f'<line x1="{pad}" y1="{h-64}" x2="{W-pad}" y2="{h-64}" stroke="{LINE}"/>')
    b.append(chips_row(pad, h - 46, p["chips"]))
    b.append(t(W - pad, h - 29, p["note"], "mono", 11, DIM, "end", 1))
    css = ".flow{animation:flow 1s linear infinite}@keyframes flow{to{stroke-dashoffset:-12}}"
    save("p-argus", finalize("\n".join(b), W, h, f"Flagship project: {p['name']}",
                             p["tagline"] + " " + " ".join(p["points"]), extra_css=css))


def principles() -> None:
    pad, gap = 36, 36
    colw = (W - 2 * pad - 2 * gap) / 3
    lines = [wrap(line, "sans", 15, colw) for *_, line in PRINCIPLES]
    h = int(118 + max(len(l) for l in lines) * 23 + 34)
    b = [panel(W, h, rx=16), crop_marks(W, h, 12, 9)]
    for i, (idx, word, color, _) in enumerate(PRINCIPLES):
        x = pad + i * (colw + gap)
        b.append(t(x, 48, idx, "mono", 11.5, DIM, tracking=1))
        b.append(f'<line x1="{x+28}" y1="44" x2="{x+colw:.1f}" y2="44" stroke="{LINE}"/>')
        b.append(f'<text x="{x}" y="92" class="mono-m" font-size="30" fill="{color}">'
                 f'<tspan fill="{DIM}">./</tspan>{word}</text>')
        for j, line in enumerate(lines[i]):
            b.append(t(x, 124 + j * 23, line, "sans", 15, TXT2))
        if i < 2:
            b.append(t(x + colw + gap / 2, 92, "→", "sans", 20, DIM, "middle"))
    save("principles", finalize("\n".join(b), W, h, "Principles: build, break, secure",
                                " ".join(f"{w}: {l}" for _, w, _, l in PRINCIPLES)))


def archive_tile(a: dict) -> None:
    w = 440
    desc = wrap(a["line"], "sans", 14, w - 110)
    h = 86 + len(desc) * 20
    b = [panel(w, h, rx=14, glow=False)]
    b.append(t(24, 36, "ARCHIVE", "mono-m", 10, MUTE, tracking=2.5))
    b.append(t(24, 64, a["name"], "mono-m", 19, TXT))
    for i, line in enumerate(desc):
        b.append(t(24, 90 + i * 20, line, "sans", 14, TXT2))
    cx = w - 40
    b.append(f'<circle cx="{cx}" cy="40" r="18" fill="{PANEL2}" stroke="{LINE2}"/>')
    b.append(t(cx, 45.5, "↗", "sans-m", 15, TXT, "middle"))
    save(a["file"], finalize("\n".join(b), w, h, f"Archived project: {a['name']}", a["line"]))


def project(p: dict) -> None:
    pad = 40
    desc = wrap(p["desc"], "sans", 16, 680)
    h = 118 + len(desc) * 24 + 66
    b = [panel(W, h, rx=16, glow=False)]
    b.append(t(pad, 48, p["id"], "mono-m", 12, GTXT, tracking=3))
    b.append(t(W - pad - 70, 48, p["meta"], "mono", 12, MUTE, "end", 0.5))
    b.append(t(pad - 1, 94, p["name"], "mono-m", 30, TXT, tracking=-0.5))
    for i, line in enumerate(desc):
        b.append(t(pad, 128 + i * 24, line, "sans", 16, TXT2))
    b.append(chips_row(pad, h - 50, p["chips"]))
    cx, cy = W - pad - 22, 44
    b.append(f'<circle cx="{cx}" cy="{cy}" r="22" fill="{PANEL2}" stroke="{LINE2}"/>')
    b.append(t(cx, cy + 6, "↗", "sans-m", 17, TXT, "middle"))
    save(p["file"], finalize("\n".join(b), W, int(h), f"Project: {p['name']}", p["desc"]))


def button(stem: str, glyph: str, label: str, handle: str) -> None:
    w, h = 280, 76
    b = [panel(w, h, rx=14, glow=True, grid=False)]
    b.append(f'<rect x="16" y="16" width="44" height="44" rx="10" fill="{G3}" stroke="{G2}"/>')
    gs = 15 if len(glyph) <= 2 else 12
    b.append(t(38, 43, glyph, "mono-m", gs, GTXT, "middle"))
    b.append(t(76, 35, label, "sans-m", 16, TXT))
    hs = 12
    while width(handle, "mono", hs) > w - 76 - 40 and hs > 9:
        hs -= 0.5
    b.append(t(76, 56, handle, "mono", hs, MUTE))
    b.append(t(w - 20, 44, "↗", "sans-m", 16, MUTE, "end"))
    save(stem, finalize("\n".join(b), w, h, f"{label}: {handle}"))


def footer() -> None:
    h = 170
    b = [panel(W, h, rx=18), crop_marks(W, h, 12, 9)]
    b.append(f'<line x1="60" y1="66" x2="{W/2-50}" y2="66" stroke="{LINE2}"/>')
    b.append(f'<line x1="{W/2+50}" y1="66" x2="{W-60}" y2="66" stroke="{LINE2}"/>')
    b.append(t(W / 2, 71, "EOF", "mono-m", 14, GTXT, "middle", 6))
    b.append(f'<text x="{W/2}" y="108" class="mono" font-size="14" fill="{MUTE}" text-anchor="middle" '
             f'letter-spacing="1"><tspan fill="{TXT}">build</tspan>  →  <tspan fill="{RED}">break</tspan>  →  '
             f'<tspan fill="{GTXT}">secure</tspan></text>')
    b.append(t(W / 2, 136, f"connection to {HANDLE} closed.", "mono", 12, DIM, "middle", 1))
    save("footer", finalize("\n".join(b), W, h, "End of profile — build, break, secure"))


def main() -> None:
    OUT.mkdir(exist_ok=True)
    print("building assets/")
    header()
    terminal()
    for stem, (idx, title, path) in SECTIONS.items():
        section(stem, idx, title, path)
    arsenal()
    principles()
    featured()
    for p in PROJECTS:
        project(p)
    for a in ARCHIVE:
        archive_tile(a)
    for c in CHANNELS:
        button(*c)
    footer()


if __name__ == "__main__":
    main()

"""Shared design system for every SVG in this profile.

One palette, one type system, one set of textures. Fonts are embedded as
per-file subsets so the artwork renders identically on every OS (an <img>
SVG cannot load web fonts, but it can use fonts embedded as data URIs).

Requires: fontTools  (pip install fonttools)
"""

from __future__ import annotations

import base64
import io
import re
from functools import lru_cache
from html import escape, unescape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"

# ---- palette ---------------------------------------------------------------
INK = "#050607"       # page / outer canvas
PANEL = "#0a0d0f"     # card surface
PANEL2 = "#0e1215"    # raised surface
LINE = "#161c21"      # hairline
LINE2 = "#222a31"     # stronger hairline
TXT = "#eef1f3"       # primary text
TXT2 = "#b3bcc4"      # secondary text
MUTE = "#6c7680"      # labels
DIM = "#3b444c"       # decorative text
G = "#22c55e"         # terminal green (accent)
G2 = "#16a34a"        # deeper green
G3 = "#0d3b22"        # green wash
GTXT = "#4ade80"      # green for small text (contrast)
RED = "#ff4d4d"       # rare alert accent

# ---- type ------------------------------------------------------------------
FACES = {
    # css family name      file stem                  weight
    "display": ("KD Display", "inter-display-semibold", 600),
    "sans": ("KD Sans", "inter-regular", 400),
    "sans-m": ("KD Sans", "inter-medium", 500),
    "mono": ("KD Mono", "jbm-regular", 400),
    "mono-m": ("KD Mono", "jbm-medium", 500),
}
FALLBACK = {
    "KD Display": "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif",
    "KD Sans": "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif",
    "KD Mono": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
}


@lru_cache(maxsize=None)
def _font(stem: str) -> TTFont:
    return TTFont(FONT_DIR / f"{stem}.woff")


def width(text: str, face: str, size: float, tracking: float = 0.0) -> float:
    """Advance width of `text` in px. `tracking` is letter-spacing in px."""
    font = _font(FACES[face][1])
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    upm = font["head"].unitsPerEm
    total = 0
    for ch in text:
        glyph = cmap.get(ord(ch)) or ".notdef"
        total += hmtx[glyph][0]
    return total * size / upm + tracking * max(len(text) - 1, 0)


def wrap(text: str, face: str, size: float, max_w: float) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if width(trial, face, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _subset_b64(stem: str, chars: str) -> str:
    font = TTFont(FONT_DIR / f"{stem}.woff")
    opts = subset.Options()
    opts.flavor = "woff"
    opts.layout_features = ["kern", "calt", "case", "tnum", "zero"]
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(text=chars + " ")
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


_TEXT_RE = re.compile(r"<text\b[^>]*>(.*?)</text>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _chars_by_family(svg: str) -> dict[str, set[str]]:
    """Every glyph that appears in a <text>, grouped by font class used."""
    used: dict[str, set[str]] = {}
    for m in re.finditer(r"<text\b([^>]*)>(.*?)</text>", svg, re.S):
        attrs, inner = m.group(1), m.group(2)
        content = unescape(_TAG_RE.sub("", inner))
        classes = re.findall(r'class="([^"]+)"', attrs)
        keys = set()
        for c in (classes[0].split() if classes else []):
            if c in FACES:
                keys.add(c)
        # tspans may switch face
        for t in re.finditer(r'<tspan\b[^>]*class="([^"]+)"[^>]*>(.*?)</tspan>', inner, re.S):
            for c in t.group(1).split():
                if c in FACES:
                    used.setdefault(c, set()).update(unescape(_TAG_RE.sub("", t.group(2))))
        for k in keys or {"sans"}:
            used.setdefault(k, set()).update(content)
    return used


def finalize(svg_body: str, w: int, h: int, title: str, desc: str = "",
             extra_css: str = "", defs: str = "") -> str:
    """Wrap body in an <svg> with embedded font subsets and shared CSS."""
    used = _chars_by_family(svg_body)
    faces_css, class_css = [], []
    for key, chars in used.items():
        family, stem, weight = FACES[key]
        b64 = _subset_b64(stem, "".join(sorted(chars)))
        faces_css.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:font/woff;base64,{b64}) format('woff');}}"
        )
    for key, (family, _, weight) in FACES.items():
        class_css.append(f".{key}{{font-family:'{family}',{FALLBACK[family]};font-weight:{weight};}}")
    css = "\n".join(faces_css + class_css) + """
text{white-space:pre;font-variant-numeric:tabular-nums;}
@media (prefers-reduced-motion: reduce){*{animation:none!important;}}
""" + extra_css
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">\n'
        f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc or title)}</desc>\n'
        f"<defs>\n<style>\n{css}\n</style>\n{common_defs()}\n{defs}\n</defs>\n"
        f"{svg_body}\n</svg>\n"
    )


def common_defs() -> str:
    return f"""<filter id="grain" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch"/>
  <feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.035 0"/>
</filter>
<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
  <path d="M32 0H0V32" fill="none" stroke="#ffffff" stroke-opacity="0.025"/>
</pattern>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
  <rect width="4" height="1" fill="#000" opacity="0.18"/>
</pattern>
<linearGradient id="silver" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#ffffff"/>
  <stop offset="1" stop-color="#9aa5ae"/>
</linearGradient>
<radialGradient id="glow" cx="0.15" cy="0" r="0.9">
  <stop offset="0" stop-color="{G}" stop-opacity="0.10"/>
  <stop offset="1" stop-color="{G}" stop-opacity="0"/>
</radialGradient>"""


def panel(w: int, h: int, rx: int = 16, glow: bool = True, grid: bool = True) -> str:
    """Card surface: base, optional grid + glow, grain, hairline border."""
    parts = [f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="{rx}" fill="{PANEL}"/>']
    if grid:
        parts.append(f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="{rx}" fill="url(#grid)"/>')
    if glow:
        parts.append(f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="{rx}" fill="url(#glow)"/>')
    parts.append(f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="{rx}" filter="url(#grain)"/>')
    parts.append(f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="{rx}" fill="none" stroke="{LINE2}"/>')
    return "\n".join(parts)


def crop_marks(w: int, h: int, inset: int = 14, size: int = 10, color: str = DIM) -> str:
    """Print-style registration corners."""
    i, s = inset, size
    d = (f"M{i} {i+s}V{i}H{i+s} M{w-i-s} {i}H{w-i}V{i+s} "
         f"M{w-i} {h-i-s}V{h-i}H{w-i-s} M{i+s} {h-i}H{i}V{h-i-s}")
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1"/>'


def t(x, y, text, cls="sans", size=16, fill=TXT, anchor="start", tracking=0, extra=""):
    ls = f' letter-spacing="{tracking}"' if tracking else ""
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-size="{size}" '
            f'fill="{fill}"{a}{ls}{extra}>{escape(text, quote=False)}</text>')


def chip(x, y, label, active=True, size=12):
    """Small mono pill. Returns (svg, width)."""
    tw = width(label, "mono-m", size, 1.2)
    w = tw + 20
    stroke = G2 if active else LINE2
    fill = G3 if active else PANEL2
    color = GTXT if active else MUTE
    svg = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{size+12}" rx="{(size+12)/2}" '
           f'fill="{fill}" stroke="{stroke}"/>'
           + t(x + 10, y + size + 3.5, label, "mono-m", size, color, tracking=1.2))
    return svg, w

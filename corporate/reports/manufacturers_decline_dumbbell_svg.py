# corporate/reports/manufacturers_decline_dumbbell_svg.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any


def _d(x: Any) -> Decimal:
    if isinstance(x, Decimal):
        return x
    try:
        return Decimal(str(x or "0"))
    except Exception:
        return Decimal("0")


def _escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = (h or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join([c + c for c in h])
    if len(h) != 6:
        return (0, 0, 0)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _text_color_for(bg_hex: str) -> str:
    r, g, b = _hex_to_rgb(bg_hex)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#ffffff" if lum < 150 else "#111827"


def _mix(c1: str, c2: str, t: float) -> str:
    t = _clamp(t, 0.0, 1.0)
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _as_int_year(x: Any) -> int | None:
    if x is None:
        return None
    try:
        s = str(x).strip()
        if not s:
            return None
        digits = "".join(ch for ch in s if ch.isdigit())
        if len(digits) >= 4:
            return int(digits[:4])
        return None
    except Exception:
        return None


def _safe_disp(v: Any, fallback: str = "0 ₽") -> str:
    s = str(v or "").strip()
    return s if s else fallback


@dataclass
class DumbbellStyle:
    # base canvas (viewBox width). Actual on-page width is responsive (100%).
    width: int = 1120
    row_h: int = 54
    top_pad: int = 98
    bottom_pad: int = 28
    left_pad: int = 18
    right_pad: int = 18

    name_x: int = 18

    # timeline anchors (fixed)
    col_start_x: int = 360   # 2022
    col_mid_x: int = 650     # last closed year
    col_end_x: int = 900     # current year YTD

    # dots
    r_start: float = 6.0
    r_mid: float = 6.2
    r_ytd: float = 6.0

    # typography
    text_main: str = "#0f172a"
    text_muted: str = "#64748b"
    text_soft: str = "#94a3b8"

    # grid / axis
    grid: str = "#e2e8f0"
    axis: str = "#cbd5e1"

    # decline color scale (light -> dark)
    c_light: str = "#fee2e2"
    c_dark: str = "#991b1b"
    neutral_line: str = "#94a3b8"

    # YTD zone: airy, minimal
    ytd_fill: str = "#0f172a"
    ytd_fill_opacity: float = 0.03
    ytd_border: str = "#e2e8f0"
    ytd_border_opacity: float = 0.9

    # YTD line/dot
    ytd_line: str = "#94a3b8"
    ytd_dot: str = "#64748b"

    bg: str = "transparent"


def build_decline_dumbbell_svg(
    decline_rows: list[dict[str, Any]],
    *,
    year_start: int = 2022,
    last_closed_year: int | None = None,
    current_year: int | None = None,
    title: str | None = None,
    max_rows: int = 15,
    style: DumbbellStyle | None = None,
) -> str:
    """
    Timeline-style dumbbell:

    LEFT -> RIGHT:
      2022 (start) -> last closed year -> current year (YTD) in a subtle zone

    This avoids confusing "value-based scaling" and reads cleanly.
    """
    style = style or DumbbellStyle()
    rows = list(decline_rows or [])[: max(0, int(max_rows))]
    if not rows:
        return ""

    cy = int(current_year or date.today().year)
    ys = int(year_start)

    if last_closed_year is None:
        candidates: list[int] = []
        for r in rows:
            for k in ("last_closed_year", "last_year", "year_end", "closed_year", "last_closed_year_str"):
                y = _as_int_year(r.get(k))
                if y:
                    candidates.append(y)
        last_closed_year = max(candidates) if candidates else (cy - 1)
    ye = int(last_closed_year)

    # normalize fields
    norm: list[dict[str, Any]] = []
    for r in rows:
        name = str(r.get("name") or "—")

        a = _d(r.get("first_val"))
        b = _d(r.get("last_closed_val"))

        a_disp = _safe_disp(r.get("first_disp"))
        b_disp = _safe_disp(r.get("last_closed_disp"))

        now_val = _d(
            r.get("now_val")
            if "now_val" in r
            else r.get("current_val")
            if "current_val" in r
            else r.get("cy_val")
        )
        now_disp = _safe_disp(
            r.get("now_disp")
            if "now_disp" in r
            else r.get("current_disp")
            if "current_disp" in r
            else r.get("cy_disp"),
            fallback="",
        )
        has_now = (now_disp != "") or (now_val != 0)

        pct: float | None
        if a and a != 0:
            pct = float((b / a) - Decimal("1"))
        else:
            pct = None

        norm.append(
            dict(
                name=name,
                first_val=a,
                last_closed_val=b,
                first_disp=a_disp,
                last_closed_disp=b_disp,
                now_val=now_val,
                now_disp=now_disp,
                has_now=bool(has_now),
                pct=pct,
            )
        )

    # sort by biggest 2022
    norm = sorted(norm, key=lambda r: _d(r.get("first_val")), reverse=True)

    # color intensity for declines
    mags: list[float] = []
    for r in norm:
        p = r.get("pct")
        if isinstance(p, float) and p < 0:
            mags.append(-p)
    dmax = max(mags) if mags else 1.0
    if dmax <= 0:
        dmax = 1.0

    def line_color(p: float | None) -> str:
        if p is None:
            return style.neutral_line
        if p >= 0:
            return style.neutral_line
        t = _clamp((-p) / dmax, 0.0, 1.0)
        t = t ** 0.65
        return _mix(style.c_light, style.c_dark, t)

    def fmt_pct(p: float | None) -> str:
        if p is None:
            return "—"
        sign = "+" if p > 0 else ""
        return f"{sign}{p*100:.0f}%"

    has_any_now = any(bool(r.get("has_now")) for r in norm)

    # layout
    h = style.top_pad + style.row_h * len(norm) + style.bottom_pad
    # ttl = title or f"Устойчивое снижение выручки ({ys}→{ye})"
    ttl = ''

    out: list[str] = []

    # Responsive SVG: never overflow page
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" '
        f'viewBox="0 0 {style.width} {h}" preserveAspectRatio="xMinYMin meet" '
        f'style="max-width:100%;height:auto;display:block;">'
    )

    if style.bg != "transparent":
        out.append(f'<rect x="0" y="0" width="{style.width}" height="{h}" fill="{style.bg}"/>')

    # Title
    out.append(
        f'<text x="{style.left_pad}" y="34" fill="{style.text_main}" font-size="18" font-weight="900">'
        f'{_escape(ttl)}</text>'
    )

    # --- YTD subtle zone: no "bubble", no heavy rounding, just a soft band + light borders
    if has_any_now:
        band_w = 170
        band_x = style.col_end_x - band_w / 2
        band_y = style.top_pad - 42
        band_h = h - band_y - style.bottom_pad + 10

        # soft fill
        out.append(
            f'<rect x="{band_x:.2f}" y="{band_y:.2f}" width="{band_w:.2f}" height="{band_h:.2f}" '
            f'rx="12" ry="12" fill="{style.ytd_fill}" opacity="{style.ytd_fill_opacity}"/>'
        )
        # # subtle border (no heavy frame)
        # out.append(
        #     f'<rect x="{band_x:.2f}" y="{band_y:.2f}" width="{band_w:.2f}" height="{band_h:.2f}" '
        #     f'rx="12" ry="12" fill="none" stroke="{style.ytd_border}" stroke-width="1" opacity="{style.ytd_border_opacity}"/>'
        # )
        # vertical guide lines (super light, makes it feel like "column")
        out.append(
            f'<line x1="{band_x:.2f}" y1="{band_y+8:.2f}" x2="{band_x:.2f}" y2="{band_y+band_h-8:.2f}" '
            f'stroke="{style.ytd_border}" stroke-width="1" opacity="0.45"/>'
        )
        out.append(
            f'<line x1="{band_x+band_w:.2f}" y1="{band_y+8:.2f}" x2="{band_x+band_w:.2f}" y2="{band_y+band_h-8:.2f}" '
            f'stroke="{style.ytd_border}" stroke-width="1" opacity="0.45"/>'
        )

    # Header labels
    out.append(
        f'<text x="{style.col_start_x}" y="64" fill="{style.text_muted}" font-size="12" font-weight="900" text-anchor="middle">{ys}</text>'
    )
    out.append(
        f'<text x="{style.col_mid_x}" y="64" fill="{style.text_muted}" font-size="12" font-weight="900" text-anchor="middle">{ye}</text>'
    )
    if has_any_now:
        out.append(
            f'<text x="{style.col_end_x}" y="64" fill="{style.text_soft}" font-size="12" font-weight="900" text-anchor="middle">{cy} YTD</text>'
        )

    # Baseline
    out.append(
        f'<line x1="{style.col_start_x}" y1="{style.top_pad-16}" x2="{style.col_end_x}" y2="{style.top_pad-16}" stroke="{style.axis}"/>'
    )

    # Rows
    for i, r in enumerate(norm):
        y_row_top = style.top_pad + i * style.row_h
        y = y_row_top + 22

        name = _escape(str(r.get("name") or "—"))
        p = r.get("pct")
        col = line_color(p if isinstance(p, float) else None)

        # grid line
        out.append(
            f'<line x1="{style.left_pad}" y1="{y_row_top}" x2="{style.width-style.right_pad}" y2="{y_row_top}" '
            f'stroke="{style.grid}" stroke-dasharray="2 10" opacity="0.85"/>'
        )

        # name
        out.append(
            f'<text x="{style.name_x}" y="{y+6}" fill="{style.text_main}" font-size="14" font-weight="900">{name}</text>'
        )

        x_start = float(style.col_start_x)
        x_mid = float(style.col_mid_x)
        x_ytd = float(style.col_end_x)

        # 2022 -> last closed (main red line)
        out.append(
            f'<line x1="{x_start:.2f}" y1="{y:.2f}" x2="{x_mid:.2f}" y2="{y:.2f}" '
            f'stroke="{col}" stroke-width="4.2" stroke-linecap="round" opacity="0.96"/>'
        )

        # dots
        out.append(
            f'<circle cx="{x_start:.2f}" cy="{y:.2f}" r="{style.r_start}" fill="#ffffff" stroke="{col}" stroke-width="3.2"/>'
        )
        out.append(
            f'<circle cx="{x_mid:.2f}" cy="{y:.2f}" r="{style.r_mid}" fill="#ffffff" stroke="{col}" stroke-width="3.2"/>'
        )

        # values (above)
        a_disp = _escape(_safe_disp(r.get("first_disp"), "0 ₽"))
        b_disp = _escape(_safe_disp(r.get("last_closed_disp"), "0 ₽"))

        out.append(
            f'<text x="{x_start:.2f}" y="{y - 12:.2f}" fill="{style.text_muted}" font-size="13" font-weight="900" text-anchor="middle">{a_disp}</text>'
        )
        out.append(
            f'<text x="{x_mid:.2f}" y="{y - 12:.2f}" fill="{style.text_muted}" font-size="13" font-weight="900" text-anchor="middle">{b_disp}</text>'
        )

        # YTD connector
        if has_any_now and bool(r.get("has_now")):
            # thin & elegant
            out.append(
                f'<line x1="{x_mid:.2f}" y1="{y:.2f}" x2="{x_ytd:.2f}" y2="{y:.2f}" '
                f'stroke="{style.ytd_line}" stroke-width="1.35" stroke-linecap="round" '
                f'stroke-dasharray="2 7" opacity="0.55"/>'
            )
            out.append(
                f'<circle cx="{x_ytd:.2f}" cy="{y:.2f}" r="{style.r_ytd}" fill="#ffffff" stroke="{style.ytd_dot}" stroke-width="2.6" opacity="0.95"/>'
            )

            now_disp = _escape(_safe_disp(r.get("now_disp"), ""))
            if now_disp:
                out.append(
                    f'<text x="{x_ytd:.2f}" y="{y + 18:.2f}" fill="{style.text_soft}" font-size="13" font-weight="900" text-anchor="middle">{now_disp}</text>'
                )

        # Δ% badge
        badge_w = 66
        badge_h = 20
        bx = style.width - style.right_pad - badge_w
        by = y - 16
        badge_fill = col
        badge_text = _text_color_for(badge_fill)

        out.append(
            f'<rect x="{bx}" y="{by}" width="{badge_w}" height="{badge_h}" rx="10" fill="{badge_fill}" opacity="0.96"/>'
        )
        out.append(
            f'<text x="{bx + badge_w/2:.2f}" y="{by + 14:.2f}" fill="{badge_text}" font-size="12" font-weight="900" text-anchor="middle">'
            f'{_escape(fmt_pct(p if isinstance(p, float) else None))}</text>'
        )

    # bottom axis
    out.append(
        f'<line x1="{style.left_pad}" y1="{h-style.bottom_pad}" x2="{style.width-style.right_pad}" y2="{h-style.bottom_pad}" stroke="{style.axis}"/>'
    )

    out.append("</svg>")
    return "".join(out)
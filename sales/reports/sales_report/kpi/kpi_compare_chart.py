# sales/reports/sales_report/kpi/kpi_compare_chart.py
from __future__ import annotations

from typing import Dict, List, Optional
import math


def _is_num(x) -> bool:
    try:
        return x is not None and math.isfinite(float(x))
    except Exception:
        return False


def _fmt_pp(p: Optional[float]) -> str:
    if p is None or not math.isfinite(p):
        return "—"
    sign = "+" if p > 0 else ""
    return f"{sign}{p:.1f}%"


def _fmt_abs(v) -> str:
    """
    Универсальный формат для "абсолютных" дельт.
    Ожидаем, что v уже в нужных единицах (руб/шт).
    Если хочешь формат "тыс/млн" — лучше передавать уже отформатированную строку.
    """
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()

    try:
        x = float(v)
    except Exception:
        return ""

    sign = "+" if x > 0 else ""
    return f"{sign}{x:,.0f}".replace(",", " ")


def build_compare_delta_bar_svg(compare: Dict, width: int = 1080, height: int = 340) -> str:
    """
    Δ% — аккуратный lollipop chart:
    - 2 “палочки” на метрику (prev / ly)
    - 0% ось
    - минимум цветов/обводок, как в “взрослых” finance графиках
    - цвет точки = хорошо/плохо с учетом invert (для Возвратов)
    - абсолютные Δ выводим ДВУМЯ СТРОКАМИ (prev / ly), чтобы ничего не накладывалось
    """

    items: List[Dict] = compare.get("chart") or []
    if not items:
        return ""

    # --- диапазон процентов ---
    vals: List[float] = []
    for it in items:
        for k in ("prev_pct", "ly_pct"):
            v = it.get(k)
            if _is_num(v):
                vals.append(float(v))
    if not vals:
        return ""

    vmax = max(vals)
    vmin = min(vals)
    bound = max(abs(vmax), abs(vmin))
    if bound < 1e-9:
        bound = 1.0
    bound *= 1.25  # воздух

    # --- layout ---
    pad = 22
    axis_left = 86
    top = 34
    bottom = 118  # было 92, увеличили под 2 строки абсолютов + примечание

    plot_x = axis_left
    plot_y = top
    plot_w = width - axis_left - pad
    plot_h = height - top - bottom

    def sy(pct: float) -> float:
        return plot_y + (bound - pct) / (2 * bound) * plot_h

    y0 = sy(0.0)

    # --- palette ---
    BG = "#ffffff"
    FRAME = "#e7eef8"
    GRID = "#eef3fb"
    ZERO = "#cbd5e1"
    TXT = "#0f172a"
    MUTED = "#64748b"

    GOOD = "#0a7a3d"  # темный green
    BAD = "#c81e1e"   # темный red
    NEU = "#94a3b8"   # slate

    PREV_SER = "#0b1f3b"  # темный navy
    LY_SER = "#64748b"    # slate

    def is_good(v: float, invert: bool) -> bool:
        # обычно: рост = хорошо; для возвратов: падение = хорошо
        return (v < 0) if invert else (v > 0)

    def tone(v: float, invert: bool) -> str:
        if abs(v) < 1e-12:
            return NEU
        return GOOD if is_good(v, invert) else BAD

    # --- frame ---
    frame = (
        f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" '
        f'rx="14" ry="14" fill="{BG}" stroke="{FRAME}"/>'
    )

    # --- grid + axis labels ---
    grid = []
    labels = []

    levels = [-bound, -bound / 2, 0.0, bound / 2, bound]
    for level in levels:
        y = sy(level)
        is_zero = abs(level) < 1e-6
        grid.append(
            f'<line x1="{plot_x}" y1="{y:.1f}" x2="{plot_x+plot_w}" y2="{y:.1f}" '
            f'stroke="{ZERO if is_zero else GRID}" stroke-width="{1.6 if is_zero else 1.0}"/>'
        )
        labels.append(
            f'<text class="axis" x="{plot_x-12}" y="{y+4:.1f}" text-anchor="end">{_fmt_pp(level)}</text>'
        )

    # --- legend ---
    prev_label = (compare.get("prev") or {}).get("label", "предыдущая неделя")
    ly_label = (compare.get("ly") or {}).get("label", "прошлый год")
    legend = f"""
    <g class="legend">
      <circle cx="{plot_x+8}" cy="{plot_y-18}" r="5" fill="{PREV_SER}"/>
      <text x="{plot_x+20}" y="{plot_y-14}" class="legendText">{prev_label}</text>

      <circle cx="{plot_x+280}" cy="{plot_y-18}" r="5" fill="{LY_SER}"/>
      <text x="{plot_x+292}" y="{plot_y-14}" class="legendText">{ly_label}</text>
    </g>
    """

    # --- lollipops ---
    n = len(items)
    group_w = plot_w / n
    offset = min(18, group_w * 0.16)  # разнос двух серий
    dot_r = 6

    shapes = []
    xlabels = []
    abs_lines = []

    title_y = plot_y + plot_h + 34
    abs_y1 = plot_y + plot_h + 56   # строка prev
    abs_y2 = plot_y + plot_h + 74   # строка ly
    foot_y = plot_y + plot_h + 102

    for i, it in enumerate(items):
        cx = plot_x + (i + 0.5) * group_w
        title = str(it.get("title", ""))
        invert = bool(it.get("invert", False))

        xlabels.append(
            f'<text class="title" x="{cx:.1f}" y="{title_y}" text-anchor="middle">{title}</text>'
        )

        # --- абсолюты: 2 строки (не накладываются) ---
        pa = (it.get("prev_abs") or "").strip()
        la = (it.get("ly_abs") or "").strip()

        if pa and pa != "—":
            abs_lines.append(
                f'<text class="abs" x="{cx:.1f}" y="{abs_y1}" text-anchor="middle">'
                f'<tspan class="absTag">prev:</tspan> Δ {pa}</text>'
            )

        if la and la != "—":
            abs_lines.append(
                f'<text class="abs" x="{cx:.1f}" y="{abs_y2}" text-anchor="middle">'
                f'<tspan class="absTag">ly:</tspan> Δ {la}</text>'
            )

        # --- prev ---
        pv = it.get("prev_pct")
        if _is_num(pv):
            v = float(pv)
            x = cx - offset
            y = sy(v)

            shapes.append(
                f'<line x1="{x:.1f}" y1="{y0:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
                f'stroke="{PREV_SER}" stroke-width="3" stroke-linecap="round"/>'
            )
            shapes.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{dot_r}" fill="{tone(v, invert)}" '
                f'stroke="#ffffff" stroke-width="2"/>'
            )
            ty = y - 10 if v >= 0 else y + 18
            shapes.append(
                f'<text class="pct" x="{x:.1f}" y="{ty:.1f}" text-anchor="middle">{_fmt_pp(v)}</text>'
            )

        # --- ly ---
        lv = it.get("ly_pct")
        if _is_num(lv):
            v = float(lv)
            x = cx + offset
            y = sy(v)

            shapes.append(
                f'<line x1="{x:.1f}" y1="{y0:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
                f'stroke="{LY_SER}" stroke-width="3" stroke-linecap="round"/>'
            )
            shapes.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{dot_r}" fill="{tone(v, invert)}" '
                f'stroke="#ffffff" stroke-width="2"/>'
            )
            ty = y - 10 if v >= 0 else y + 18
            shapes.append(
                f'<text class="pct" x="{x:.1f}" y="{ty:.1f}" text-anchor="middle">{_fmt_pp(v)}</text>'
            )

    style = f"""
    <style>
      .axis {{
        font: 500 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,Arial,sans-serif;
        fill: {MUTED};
      }}
      .title {{
        font: 700 13px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,Arial,sans-serif;
        fill: {TXT};
      }}
      .pct {{
        font: 700 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,Arial,sans-serif;
        fill: {TXT};
      }}
      .abs {{
        font: 500 11px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,Arial,sans-serif;
        fill: {MUTED};
      }}
      .absTag {{
        fill: {NEU};
        font-weight: 600;
      }}
      .legendText {{
        font: 500 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,Arial,sans-serif;
        fill: {MUTED};
      }}
      .footnote {{
        font: 400 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,Arial,sans-serif;
        fill: {MUTED};
      }}
    </style>
    """

    footnote = (
        f'<text class="footnote" x="{plot_x}" y="{foot_y}">'
        f'Примечание: Δ% — отклонение относительно базовых периодов. '
        f'prev — аналогичный период прошлого цикла; '
        f'ly — аналогичный период прошлого года. '
        f'</text>'
    )

    return f"""
<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet"
     xmlns="http://www.w3.org/2000/svg">
  {style}
  {legend}
  {frame}
  {''.join(grid)}
  {''.join(labels)}
  {''.join(shapes)}
  {''.join(xlabels)}
  {''.join(abs_lines)}
  {footnote}
</svg>
""".strip()




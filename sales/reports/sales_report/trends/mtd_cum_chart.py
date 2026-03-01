# sales/reports/sales_report/trends/mtd_cum_chart.py
from typing import Dict, List
import math

def build_mtd_cum_chart_svg(
    ctx: Dict,
    width: int = 1100,
    height: int = 320,
    padding: int = 28,
    axis_gutter: int = 52,
    grid_lines: int = 4,
) -> str:
    series_cur: List[Dict] = ctx.get("series_cur") or []
    series_ly: List[Dict] = ctx.get("series_ly") or []
    if not series_cur:
        return ""

    # выравниваем по длине (по day-of-month)
    n = len(series_cur)
    ly_vals = [p["cum_raw"] for p in series_ly[:n]] if series_ly else [0.0]*n
    cur_vals = [p["cum_raw"] for p in series_cur]

    values_all = cur_vals + ly_vals
    vmin = min(values_all)
    vmax = max(values_all)
    if math.isclose(vmin, vmax):
        vmax = vmin + 1.0

    top_h = 26
    foot_h = 18

    plot_x = axis_gutter + padding
    plot_y = padding + top_h
    plot_w = width - plot_x - padding
    plot_h = height - plot_y - padding - foot_h

    def sx(i: int) -> float:
        if n == 1:
            return plot_x + plot_w / 2
        return plot_x + i * (plot_w / (n - 1))

    def sy(v: float) -> float:
        return plot_y + (vmax - v) / (vmax - vmin) * plot_h

    def fmt_axis(v: float) -> str:
        av = abs(v)
        if av >= 1_000_000:
            return f"{v/1_000_000:.1f} млн"
        if av >= 1_000:
            return f"{v/1_000:.0f} тыс"
        return f"{v:.0f}"

    # сетка + подписи
    grid = []
    ylabels = []
    for k in range(grid_lines + 1):
        y = plot_y + (plot_h * k / grid_lines)
        grid.append(
            f'<line x1="{plot_x}" y1="{y:.1f}" x2="{plot_x+plot_w}" y2="{y:.1f}" '
            f'stroke="#e9eef6" stroke-width="1"/>'
        )
        val = vmax - (vmax - vmin) * (k / grid_lines)
        ylabels.append(
            f'<text x="{plot_x-12}" y="{y+4:.1f}" text-anchor="end" '
            f'font-size="12" fill="#7a8699">{fmt_axis(val)}</text>'
        )

    # линии
    cur_path = "M " + " L ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(cur_vals))
    ly_path  = "M " + " L ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(ly_vals))

    # точки (последняя)
    last_i = n - 1
    cur_dot = f'<circle cx="{sx(last_i):.1f}" cy="{sy(cur_vals[last_i]):.1f}" r="7" fill="#e91e63" stroke="#fff" stroke-width="2"/>'
    ly_dot  = f'<circle cx="{sx(last_i):.1f}" cy="{sy(ly_vals[last_i]):.1f}" r="5" fill="#94a3b8" stroke="#fff" stroke-width="2"/>'

    # заголовок-строка (коротко)
    title = (
        f'<text x="{padding}" y="{padding+14}" font-size="14" fill="#0f172a">'
        f'Накопленная чистая выручка месяца (MTD): '
        f'<tspan font-weight="700">{ctx.get("cum_cur")}</tspan>'
        f' vs LY <tspan font-weight="700">{ctx.get("cum_ly")}</tspan>'
        f'</text>'
    )

    # frame
    frame = (
        f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" '
        f'rx="16" ry="16" fill="#ffffff" stroke="#eef2f8"/>'
    )

    # легенда (простая)
    legend = f"""
      <g>
        <circle cx="{plot_x+16}" cy="{plot_y+18}" r="4" fill="#4da3ff"/>
        <text x="{plot_x+26}" y="{plot_y+22}" font-size="12" fill="#334155">Текущий год</text>

        <circle cx="{plot_x+120}" cy="{plot_y+18}" r="4" fill="#94a3b8"/>
        <text x="{plot_x+130}" y="{plot_y+22}" font-size="12" fill="#334155">Прошлый год</text>
      </g>
    """

    # подпись X (не обязательно, но аккуратно): покажем 1, 10, 20, last
    ticks = set([0, min(9, n-1), min(19, n-1), n-1])
    xlabels = []
    for i in sorted(ticks):
        lab = series_cur[i]["label"]
        xlabels.append(
            f'<text x="{sx(i):.1f}" y="{plot_y+plot_h+16:.1f}" text-anchor="middle" '
            f'font-size="11" fill="#7a8699">{lab}</text>'
        )

    svg = f"""
<svg width="100%" height="{height}" viewBox="0 0 {width} {height}"
     preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
  {title}
  {frame}
  {''.join(grid)}
  {''.join(ylabels)}
  {legend}

  <path d="{ly_path}" fill="none" stroke="#94a3b8" stroke-width="2.5"
        stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="4 4"/>
  <path d="{cur_path}" fill="none" stroke="#4da3ff" stroke-width="3"
        stroke-linecap="round" stroke-linejoin="round"/>

  {ly_dot}
  {cur_dot}

  {''.join(xlabels)}
</svg>
""".strip()

    return svg
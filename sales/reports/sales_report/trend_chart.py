from typing import List, Dict, Optional
import math




def _parse_number(v):
    if v in (None, "", "—"):
        return None
    s = str(v)
    s = s.replace("\u00A0", "").replace(" ", "")
    s = s.replace("₽", "").replace("%", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _fmt(v):
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"{v/1_000:.0f}K"
    return f"{v:.0f}"





from typing import List, Dict, Optional
import math


def build_trend_chart_svg(
    trend: List[Dict],
    metric: str = "amount_raw",
    width: int = 1100,          # более дружелюбно к A4
    height: int = 340,
    padding: int = 28,
    axis_gutter: int = 42,     # место слева под подписи оси Y
    grid_lines: int = 4,
) -> str:
    """
    SVG-график тренда (report-friendly):
    - сетка
    - avg линия
    - мягкая заливка под линией
    - выделение текущей точки
    - компактные KPI-бейджи сверху
    - сноска снизу
    - подписи Y-оси НЕ режутся (axis_gutter)
    - SVG адаптивный по ширине (width="100%")
    """

    # --- собираем значения (RAW) ---
    values: List[float] = []
    labels: List[str] = []
    current_idx: Optional[int] = None

    for t in trend:
        v = t.get(metric)
        if v is None:
            continue
        try:
            v = float(v)
        except Exception:
            continue

        values.append(v)
        labels.append(str(t.get("label", "")))

        if t.get("is_current"):
            current_idx = len(values) - 1

    if not values:
        return ""

    n = len(values)
    if current_idx is None:
        current_idx = n - 1

    vmin = min(values)
    vmax = max(values)
    if math.isclose(vmin, vmax):
        vmax = vmin + 1.0

    vavg = sum(values) / n
    curr = values[current_idx]
    prev = values[current_idx - 1] if current_idx - 1 >= 0 else None

    # Δ к среднему
    delta_to_avg_pct = None
    if vavg not in (0, None):
        delta_to_avg_pct = (curr - vavg) / vavg * 100

    # Δ к предыдущему периоду (в ряду)
    delta_to_prev_pct = None
    if prev not in (None, 0):
        delta_to_prev_pct = (curr - prev) / prev * 100

    # --- layout ---
    top_badges_h = 34
    foot_h = 22

    plot_x = axis_gutter + padding
    plot_y = padding + top_badges_h
    plot_w = width - plot_x - padding
    plot_h = height - plot_y - padding - foot_h

    def sx(i: int) -> float:
        if n == 1:
            return plot_x + plot_w / 2
        return plot_x + i * (plot_w / (n - 1))

    def sy(v: float) -> float:
        return plot_y + (vmax - v) / (vmax - vmin) * plot_h

    # --- formatting ---
    def fmt_axis(v: float) -> str:
        av = abs(v)
        if av >= 1_000_000:
            return f"{v/1_000_000:.1f} млн"
        if av >= 1_000:
            return f"{v/1_000:.0f} тыс"
        return f"{v:.0f}"

    def fmt_pp(p: Optional[float]) -> str:
        if p is None or not math.isfinite(p):
            return "—"
        sign = "+" if p > 0 else ""
        return f"{sign}{p:.1f}%"

    def tone(p: Optional[float]) -> str:
        if p is None or not math.isfinite(p):
            return "neu"
        if p > 0:
            return "pos"
        if p < 0:
            return "neg"
        return "neu"

    # компактный pill-бейдж
    def pill(x: float, y: float, title: str, value: str, t: str) -> str:
        if t == "pos":
            dot = "#16a34a"
            fg = "#0f172a"
            bg = "#f8fafc"
            stroke = "#e2e8f0"
        elif t == "neg":
            dot = "#ef4444"
            fg = "#0f172a"
            bg = "#fef2f2"
            stroke = "#fecaca"
        else:
            dot = "#64748b"
            fg = "#0f172a"
            bg = "#f8fafc"
            stroke = "#e2e8f0"

        w = 230
        h = 22          # ⬅️ ниже
        r = 8           # ⬅️ не pill

        return f"""
        <g class="trend-pill">
        <rect
            x="{x:.1f}" y="{y:.1f}"
            rx="{r}" ry="{r}"
            width="{w}" height="{h}"
            fill="{bg}" stroke="{stroke}"
        />
        <circle
            cx="{x + 12:.1f}"
            cy="{y + h / 2:.1f}"
            r="4"
            fill="{dot}"
        />
        <text
            x="{x + 22:.1f}"
            y="{y + h / 2 + 4:.1f}"
            font-size="12"
            fill="{fg}"
        >
            {title}: <tspan font-weight="600">{value}</tspan>
        </text>
        </g>
        """


    # --- grid + Y labels ---
    grid = []
    ylabels = []

    for k in range(grid_lines + 1):
        y = plot_y + (plot_h * k / grid_lines)
        grid.append(
            f'<line x1="{plot_x}" y1="{y:.1f}" x2="{plot_x+plot_w}" y2="{y:.1f}" stroke="#e9eef6" stroke-width="1"/>'
        )

        val = vmax - (vmax - vmin) * (k / grid_lines)
        ylabels.append(
            f'<text x="{plot_x-12}" y="{y+4:.1f}" text-anchor="end" font-size="12" fill="#7a8699">{fmt_axis(val)}</text>'
        )

    # --- avg line ---
    yavg = sy(vavg)
    avg_line = (
        f'<line x1="{plot_x}" y1="{yavg:.1f}" x2="{plot_x+plot_w}" y2="{yavg:.1f}" '
        f'stroke="#c7d2e5" stroke-width="1" stroke-dasharray="4 4"/>'
        f'<text x="{plot_x+plot_w}" y="{yavg-8:.1f}" text-anchor="end" font-size="12" fill="#7a8699">среднее</text>'
    )

    # --- paths ---
    line_path = "M " + " L ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(values))
    area_path = (
        f"M {sx(0):.1f},{plot_y+plot_h:.1f} "
        + " L ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(values))
        + f" L {sx(n-1):.1f},{plot_y+plot_h:.1f} Z"
    )

    # --- dots ---
    dots = []
    for i, v in enumerate(values):
        is_curr = (i == current_idx)
        r = 8 if is_curr else 4.5
        fill = "#e91e63" if is_curr else "#4da3ff"
        dots.append(
            f'<circle cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="{r}" fill="{fill}" stroke="#ffffff" stroke-width="2"/>'
        )

    # --- current label bubble (справа снизу аккуратно) ---
    period_txt = labels[current_idx]
    if len(period_txt) > 28:
        period_txt = period_txt[:28] + "…"
    curr_val_txt = fmt_axis(values[current_idx])

    # bubble разместим внизу справа внутри plot
    bub_w = 320
    bub_h = 34
    bx = plot_x + plot_w - bub_w
    by = plot_y + plot_h - bub_h - 8

    bubble = f"""
    <rect x="{bx:.1f}" y="{by:.1f}" rx="14" ry="14" width="{bub_w}" height="{bub_h}" fill="#ffffff" stroke="#e9eef6"/>
    <text x="{bx+16:.1f}" y="{by+22:.1f}" font-size="14" fill="#0f172a">
      {period_txt}: <tspan font-weight="700">{curr_val_txt}</tspan>
    </text>
    """

    # --- badges top ---
    badges = (
        pill(padding, padding, "К среднему", fmt_pp(delta_to_avg_pct), tone(delta_to_avg_pct))
        + pill(padding + 250, padding, "К прошлому периоду", fmt_pp(delta_to_prev_pct), tone(delta_to_prev_pct))
    )

    # --- frame ---
    frame = f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" rx="16" ry="16" fill="#ffffff" stroke="#eef2f8"/>'

    # --- footnote ---
    footnote = (
        f'<text x="{padding}" y="{height-padding-4}" font-size="11" fill="#7a8699">'
        f'Примечание: «К среднему» — отклонение текущего значения от среднего за {n} периодов; '
        f'«К прошлому периоду» — отклонение от предыдущего значения в ряду.'
        f'</text>'
    )

    svg = f"""
<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet"
     xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0%" stop-color="#4da3ff" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#4da3ff" stop-opacity="0.00"/>
    </linearGradient>
  </defs>

  {badges}

  {frame}
  {''.join(grid)}
  {''.join(ylabels)}
  {avg_line}

  <path d="{area_path}" fill="url(#trendFill)"/>
  <path d="{line_path}" fill="none" stroke="#4da3ff" stroke-width="3"
        stroke-linecap="round" stroke-linejoin="round"/>

  {''.join(dots)}
  {bubble}

  {footnote}
</svg>
""".strip()

    return svg

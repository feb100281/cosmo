from __future__ import annotations

from typing import Dict, List
import math
import pandas as pd

from .formatters import fmt_delta_short


def _fmt_axis(v: float) -> str:
    av = abs(v)
    if av >= 1_000_000:
        return f"{v/1_000_000:.1f} млн"
    if av >= 1_000:
        return f"{v/1_000:.0f} тыс"
    return f"{v:.0f}"


def _fmt_qty(v: float) -> str:
    if v is None:
        return "—"
    v = float(v)
    if not math.isfinite(v):
        return "—"

    if v == 0:
        return "0 шт"

    sign = "+" if v > 0 else "−"
    a = abs(v)

    if a >= 1000:
        return f"{sign}{a/1000:.1f} тыс шт".replace(".", ",")
    return f"{sign}{int(round(a))} шт"


def build_ytd_categories_waterfall_svg(
    df_raw: pd.DataFrame,
    top_n: int = 10,
    width: int = 1100,
    height: int = 380,
    padding: int = 28,
    axis_gutter: int = 70,
    grid_lines: int = 4,
) -> str:
    """
    Waterfall: вклад категорий в Δ YTD (текущий год vs прошлый год за тот же период).
    Подпись на баре:
      Δ₽
      (Δшт)   <-- для "Прочие" не выводим

    Изменения по стилю (как просили):
    - без "скреплений" между барами (connectors убраны)
    - без скруглений у баров и у рамки графика (rx/ry = 0)
    - бейджи без рамки (stroke="none") и без скруглений (rx/ry = 0)
    """

    if df_raw is None or df_raw.empty:
        return ""

    df = df_raw.copy()

    for c in ("year", "cat_name", "amount", "quant"):
        if c not in df.columns:
            return ""

    df["amount"] = pd.to_numeric(df.get("amount"), errors="coerce").fillna(0.0)
    df["quant"] = pd.to_numeric(df.get("quant"), errors="coerce").fillna(0.0)
    df["cat_name"] = df["cat_name"].fillna("Без категории").astype(str)

    years = sorted(df["year"].dropna().unique())
    if len(years) < 2:
        return ""

    y_prev, y_curr = years[-2], years[-1]

    # --- amount pivot ---
    ga = (
        df.groupby(["year", "cat_name"], as_index=False)["amount"].sum()
        .pivot(index="cat_name", columns="year", values="amount")
        .fillna(0.0)
    )
    for y in (y_prev, y_curr):
        if y not in ga.columns:
            ga[y] = 0.0
    ga["delta"] = ga[y_curr] - ga[y_prev]

    # --- quant pivot ---
    gq = (
        df.groupby(["year", "cat_name"], as_index=False)["quant"].sum()
        .pivot(index="cat_name", columns="year", values="quant")
        .fillna(0.0)
    )
    for y in (y_prev, y_curr):
        if y not in gq.columns:
            gq[y] = 0.0
    ga["delta_qty"] = gq[y_curr] - gq[y_prev]

    total_delta = float(ga["delta"].sum())
    total_delta_qty = float(ga["delta_qty"].sum())

    # Top N по абсолютному вкладу (по деньгам)
    g2 = ga.sort_values("delta", key=lambda s: s.abs(), ascending=False)
    main = g2.head(top_n).copy()
    rest = g2.iloc[top_n:].copy()

    items: List[Dict] = []
    for name, row in main.iterrows():
        items.append(
            {
                "label": str(name),
                "delta": float(row["delta"]),
                "delta_qty": float(row.get("delta_qty", 0.0)),
            }
        )

    if not rest.empty:
        # qty НЕ показываем для "Прочие"
        items.append(
            {
                "label": "Прочие",
                "delta": float(rest["delta"].sum()),
                "delta_qty": 0.0,
            }
        )

    n = len(items)
    if n == 0:
        return ""

    # уровни waterfall по деньгам
    levels = [0.0]
    for it in items:
        levels.append(levels[-1] + it["delta"])

    vmin = min(levels + [0.0])
    vmax = max(levels + [0.0])
    if math.isclose(vmin, vmax):
        vmax = vmin + 1.0

    # layout
    title_h = 24
    plot_x = axis_gutter + padding
    plot_y = padding + title_h
    plot_w = width - plot_x - padding

    bottom_values_h = 22
    bottom_labels_h = 38
    plot_h = height - plot_y - padding - bottom_values_h - bottom_labels_h

    def sy(v: float) -> float:
        return plot_y + (vmax - v) / (vmax - vmin) * plot_h

    gap = 10
    bar_w = (plot_w - gap * (n - 1)) / n
    bar_w = max(26, bar_w)

    # grid + y labels
    grid = []
    ylabels = []
    for k in range(grid_lines + 1):
        y = plot_y + (plot_h * k / grid_lines)
        grid.append(
            f'<line x1="{plot_x}" y1="{y:.1f}" x2="{plot_x+plot_w}" y2="{y:.1f}" '
            f'stroke="#eef2f7" stroke-width="1"/>'
        )
        val = vmax - (vmax - vmin) * (k / grid_lines)
        ylabels.append(
            f'<text x="{plot_x-12}" y="{y+4:.1f}" text-anchor="end" font-size="12" fill="#94a3b8">{_fmt_axis(val)}</text>'
        )

    # рамка графика: прямые углы
    frame = (
        f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" '
        f'rx="0" ry="0" fill="#ffffff" stroke="#eef2f7"/>'
    )

    # title
    title = (
        f'<text x="{padding}" y="{padding+14}" font-size="14" fill="#0f172a">'
        f'Вклад категорий в изменение YTD: '
        f'<tspan font-weight="700">{fmt_delta_short(total_delta)}</tspan>'
        f' <tspan fill="#64748b">(объём: {_fmt_qty(total_delta_qty)})</tspan>'
        f'</text>'
    )

    # zero line
    y0 = sy(0.0)
    zero_line = (
        f'<line x1="{plot_x}" y1="{y0:.1f}" x2="{plot_x+plot_w}" y2="{y0:.1f}" '
        f'stroke="#cbd5e1" stroke-width="1"/>'
    )

    bars = []
    labels = []
    x = plot_x
    cat_y = plot_y + plot_h + bottom_values_h + 26

    for i, it in enumerate(items):
        dlt = float(it["delta"])
        dq = float(it.get("delta_qty", 0.0))

        start = levels[i]
        end = levels[i + 1]

        y_start = sy(start)
        y_end = sy(end)

        y_top = min(y_start, y_end)
        h = max(1.0, abs(y_end - y_start))

        fill = "#15803d" if dlt >= 0 else "#ef4444"

        # БАРЫ: без скруглений
        bars.append(
            f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{fill}"/>'
        )

        # --- аккуратные бейджи (без рамки и без скруглений) ---
        money_txt = fmt_delta_short(dlt)
        is_other = str(it.get("label", "")) == "Прочие"
        qty_txt = "" if is_other else f"({_fmt_qty(dq)})"

        line1_h = 14
        line2_h = 13 if qty_txt else 0
        pad = 6
        block_h = line1_h + line2_h + pad * 2

        cx = x + bar_w / 2

        def draw_badge(top_y: float) -> None:
            bw = min(bar_w * 0.90, 160)
            bx = cx - bw / 2

            # Плашка: БЕЗ рамки и БЕЗ скруглений
            bars.append(
                f'<rect x="{bx:.1f}" y="{top_y:.1f}" width="{bw:.1f}" height="{block_h:.1f}" '
                f'rx="0" ry="0" fill="#ffffff" stroke="none"/>'
            )

            ty = top_y + pad + 11
            bars.append(
                f'<text x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle" '
                f'font-size="12" fill="#0f172a" font-weight="800">{money_txt}</text>'
            )
            if qty_txt:
                bars.append(
                    f'<text x="{cx:.1f}" y="{ty+14:.1f}" text-anchor="middle" '
                    f'font-size="11" fill="#475569">{qty_txt}</text>'
                )

        # Позиционирование:
        # - положительные всегда бейдж над баром
        # - отрицательные: если бар высокий, пишем внутри; иначе бейдж над баром
        if dlt >= 0:
            by = max(plot_y + 4, y_top - block_h - 6)
            draw_badge(by)
        else:
            if h >= 34:
                vy = y_top + h / 2 - (7 if qty_txt else 0)
                bars.append(
                    f'<text x="{cx:.1f}" y="{vy:.1f}" text-anchor="middle" '
                    f'font-size="12" fill="#ffffff" font-weight="900">{money_txt}</text>'
                )
                if qty_txt:
                    bars.append(
                        f'<text x="{cx:.1f}" y="{vy+14:.1f}" text-anchor="middle" '
                        f'font-size="11" fill="#ffffff" opacity="0.9">{qty_txt}</text>'
                    )
            else:
                by = max(plot_y + 4, y_top - block_h - 6)
                draw_badge(by)

        # category label
        lab = str(it["label"])
        if len(lab) > 14:
            lab = lab[:14] + "…"
        labels.append(
            f'<text x="{cx:.1f}" y="{cat_y:.1f}" text-anchor="middle" '
            f'font-size="11" fill="#64748b">{lab}</text>'
        )

        # ВАЖНО: скрепления (connectors) убраны полностью

        x += bar_w + gap

    svg = f"""
<svg width="100%" height="{height}" viewBox="0 0 {width} {height}"
     preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
  {title}
  {frame}
  {''.join(grid)}
  {''.join(ylabels)}
  {zero_line}
  {''.join(bars)}
  {''.join(labels)}
</svg>
""".strip()

    return svg
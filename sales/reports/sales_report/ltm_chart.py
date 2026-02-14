# sales/reports/sales_report/ltm_chart.py
from __future__ import annotations

import io
from datetime import date
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
import matplotlib.patheffects as pe


RU_MONTHS_SHORT = {
    1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
    7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
}


def _to_svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def build_revenue_13m_svg(
    df_raw: pd.DataFrame,
    report_date: date,
    title: str = "Динамика чистой выручки за 13 месяцев",
) -> str:
    """
    df_raw ожидает колонки: date, amount (дневной ряд)
    На выходе: SVG с месячными барами + 3M MA + YoY-box (последний месяц vs -12).
    Окно: последние 13 месяцев по MS (старт месяца), последний столбик — текущий месяц (MTD).
    """

    if df_raw is None or df_raw.empty:
        return ""

    df = df_raw.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    # агрегируем по месяцам (MS = start of month)
    m = df.set_index("date")["amount"].resample("MS").sum().reset_index()
    if m.empty:
        return ""

    # последние 13 месяцев (включая месяц report_date)
    end_ms = pd.Timestamp(report_date).replace(day=1)
    start_ms = (end_ms - pd.DateOffset(months=12)).replace(day=1)
    m = m[(m["date"] >= start_ms) & (m["date"] <= end_ms)].copy()
    m = m.sort_values("date")

    if len(m) < 2:
        return ""

    # метки
    m["label"] = m["date"].dt.month.map(RU_MONTHS_SHORT) + " " + m["date"].dt.strftime("%y")
    x = np.arange(len(m))
    vals = m["amount"].to_numpy(dtype=float)

    # 3M moving average
    ma = pd.Series(vals).rolling(3, min_periods=1).mean().to_numpy()

    # YoY (последний месяц vs -12)
    yoy_abs = None
    yoy_pct = None
    if len(vals) >= 13:
        base = float(vals[-13])
        curr = float(vals[-1])
        yoy_abs = curr - base
        yoy_pct = (yoy_abs / base * 100) if base else None

    # стиль
    col_brand = "#002FA7"
    col_prev = "#94A3B8"
    col_ma = "#0B1220"      # чуть темнее для линии
    col_pos = "#0b6b2f"
    col_neg = "#b00000"
    grid_col = "#E6E8EE"
    text_muted = "#6b7280"

    fig = plt.figure(figsize=(11.2, 4.2), dpi=150)
    ax = fig.add_subplot(111)

    ax.set_title(title, pad=12, fontsize=18, fontweight="bold")

    # сетка/оси
    ax.grid(True, axis="y", color=grid_col, linewidth=0.9, alpha=0.9)
    ax.grid(False, axis="x")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_alpha(0.35)
    ax.spines["bottom"].set_alpha(0.35)

    # бары: прошлые месяцы серые, текущий месяц — бренд
    colors = [col_prev] * len(x)
    colors[-1] = col_brand
    ax.bar(x, vals, width=0.72, color=colors, alpha=0.92, zorder=2)

    # --- 3M MA линия: делаем заметнее (толще + halo) ---
    line, = ax.plot(
        x, ma,
        linewidth=2.0,
        marker="o",
        markersize=5.2,
        color=col_ma,
        zorder=4,
    )
    # белая обводка под линией (дорогой “BI”-эффект)
    line.set_path_effects([
        pe.Stroke(linewidth=6.2, foreground="white", alpha=0.9),
        pe.Normal()
    ])

    ax.text(
        0.99, 0.93, "3M MA",
        transform=ax.transAxes,
        ha="right", va="top",
        fontsize=12,
        color=col_ma,
        fontweight="bold",
    )

    # x labels
    ax.set_xticks(x)
    ax.set_xticklabels(m["label"].tolist(), fontsize=12)
    if len(x) > 10:
        for i, lab in enumerate(ax.get_xticklabels()):
            if i % 2 == 1:
                lab.set_visible(False)

    # y-axis: млн ₽
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _pos: f"{v/1_000_000:,.0f}".replace(",", " ")))
    ax.set_ylabel("млн руб.", fontsize=12, color=text_muted)

    # чтобы подписи баров не упирались в верх
    y_max = float(np.nanmax(vals)) if len(vals) else 1.0
    ax.set_ylim(0, y_max * 1.18)

    # подписи на столбиках (млн, 1 знак) — НО последний пропускаем (он будет отдельно справа)
    def _fmt_mln(v: float) -> str:
        return f"{v/1_000_000:,.1f}".replace(",", " ").replace(".", ",")

    y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
    dy = 0.012 * y_range

    for i, v in enumerate(vals):
        is_last = (i == len(vals) - 1)
        if is_last:
            continue  # ✅ иначе будет дубликат с annotate справа
        if np.isnan(v):
            continue

        ax.text(
            x[i],
            float(v) + dy,
            _fmt_mln(float(v)),
            ha="center",
            va="bottom",
            fontsize=10.5,
            color="#111827",
            zorder=5,
        )


    # акцент последнего месяца: точка + подпись СВЕРХУ
    last_val = float(vals[-1])
    ax.scatter([x[-1]], [last_val], s=70, color=col_brand, zorder=6)

    ax.text(
        x[-1],
        last_val + dy,                     
        f"{_fmt_mln(last_val)} млн",
        ha="center",
        va="bottom",
        fontsize=13,
        color=col_brand,
        fontweight="bold",
        zorder=7,
        path_effects=[pe.Stroke(linewidth=4, foreground="white", alpha=0.9), pe.Normal()],
    )


    # YoY box
    if yoy_abs is not None and yoy_pct is not None:
        sign = "+" if yoy_abs > 0 else ""
        col = col_pos if yoy_abs >= 0 else col_neg

        yoy_text = (
            f"YoY (к {m['label'].iloc[-13]}):\n"
            f"Δ: {sign}{yoy_abs/1_000_000:,.1f} млн\n"
            f"Δ%: {sign}{yoy_pct:.1f}%"
        ).replace(",", " ").replace(".", ",")

        ax.text(
            0.015, 0.96,
            yoy_text,
            transform=ax.transAxes,
            ha="left", va="top",
            fontsize=11.5,
            color=col,
            bbox=dict(
                boxstyle="round,pad=0.40,rounding_size=0.12",
                facecolor="white",
                edgecolor=grid_col,
                linewidth=1.0,
                alpha=0.95,
            ),
            zorder=10,
        )

    fig.tight_layout()
    return _to_svg(fig)


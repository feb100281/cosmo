# sales/reports/sales_report/prophet_fy_chart.py
from __future__ import annotations

import io
from datetime import date as dt_date

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
from matplotlib.patches import Patch


RU_MONTHS = {
    1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
    7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
}


def _to_svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _fmt_mln(v: float) -> str:
    """Подпись в млн, 1 знак после запятой (русский формат)."""
    return f"{v/1_000_000:,.1f}".replace(",", " ").replace(".", ",")


def build_prophet_fy_bar_svg(
    df_fact_daily: pd.DataFrame,
    df_forecast_daily: pd.DataFrame,
    report_date,
    title: str = "Прогноз на текущий год: факт и план",
) -> str:
    """
    График на текущий год (12 месяцев):
      - прошлые месяцы: Факт (закрытые месяцы)
      - текущий месяц: stacked (Факт MTD + остаток прогноза до конца месяца)
      - будущие месяцы: Прогноз (полный месяц)
    Ожидает:
      df_fact_daily: date, amount (факт дневной)
      df_forecast_daily: ds, yhat (прогноз дневной)
    """

    if df_fact_daily is None or df_fact_daily.empty:
        return ""
    if df_forecast_daily is None or df_forecast_daily.empty:
        return ""

    # --- normalize dates ---
    report_ts = pd.to_datetime(report_date).normalize()
    year = int(report_ts.year)
    curr_month = int(report_ts.month)

    # fact daily
    df_f = df_fact_daily.copy()
    df_f["date"] = pd.to_datetime(df_f["date"], errors="coerce").dt.normalize()
    df_f["amount"] = pd.to_numeric(df_f["amount"], errors="coerce").fillna(0.0)
    df_f = df_f.dropna(subset=["date"])
    df_f = df_f[df_f["date"].dt.year == year].copy()

    # forecast daily
    df_p = df_forecast_daily.copy()
    df_p["ds"] = pd.to_datetime(df_p["ds"], errors="coerce").dt.normalize()
    df_p["yhat"] = pd.to_numeric(df_p["yhat"], errors="coerce").fillna(0.0)
    df_p = df_p.dropna(subset=["ds"])
    df_p = df_p[df_p["ds"].dt.year == year].copy()

    if df_f.empty or df_p.empty:
        return ""

    # --- monthly aggregations ---
    fact_monthly = (
        df_f.set_index("date")["amount"]
        .resample("MS")
        .sum()
        .reset_index()
    )
    fact_monthly["month"] = fact_monthly["date"].dt.month

    plan_monthly = (
        df_p.set_index("ds")["yhat"]
        .resample("MS")
        .sum()
        .reset_index()
    )
    plan_monthly["month"] = plan_monthly["ds"].dt.month

    months = np.arange(1, 13)
    fact_map = dict(zip(fact_monthly["month"], fact_monthly["amount"]))
    plan_map = dict(zip(plan_monthly["month"], plan_monthly["yhat"]))

    # --- base arrays ---
    fact_full_month = np.array([float(fact_map.get(m, 0.0)) for m in months], dtype=float)
    plan_full_month = np.array([float(plan_map.get(m, 0.0)) for m in months], dtype=float)

    # --- split current month into MTD fact + remaining forecast ---
    ms = report_ts.replace(day=1)
    this_eom = (report_ts + pd.offsets.MonthEnd(0)).normalize()

    # факт с начала месяца по report_date
    mtd_fact = float(df_f[(df_f["date"] >= ms) & (df_f["date"] <= report_ts)]["amount"].sum())

    # прогноз только на оставшиеся дни текущего месяца
    rest_start = (report_ts + pd.Timedelta(days=1)).normalize()
    remaining_forecast = float(
        df_p[(df_p["ds"] >= rest_start) & (df_p["ds"] <= this_eom)]["yhat"].sum()
    )

    # полный прогноз закрытия месяца для высоты столбика
    curr_month_forecast = mtd_fact + remaining_forecast

    # --- build plot series (what we actually draw) ---
    # Past months (strictly < current): fact
    fact_draw = fact_full_month.copy()
    plan_draw = np.zeros_like(plan_full_month)

    # Future months (> current): forecast
    for m in months:
        if m > curr_month:
            fact_draw[m - 1] = 0.0
            plan_draw[m - 1] = plan_full_month[m - 1]

    # Current month: stacked
    fact_draw[curr_month - 1] = mtd_fact
    plan_draw[curr_month - 1] = remaining_forecast  # only the remaining part

    # For safety: closed months should not show forecast
    for m in months:
        if m < curr_month:
            plan_draw[m - 1] = 0.0

    # Total height per month for labels
    total_draw = fact_draw + plan_draw

    # --- style (keep your colors) ---
    col_fact = "#002FA7"
    col_plan = "#002FA7"
    grid_col = "#E6E8EE"
    text_muted = "#6b7280"

    fig = plt.figure(figsize=(11.2, 4.0), dpi=150)
    ax = fig.add_subplot(111)

    ax.set_title(title, pad=12, fontsize=15, fontweight="bold")

    width = 0.62

    # bars
    ax.bar(months, fact_draw, width=width, color=col_fact, alpha=0.90, label="Факт", zorder=3)
    ax.bar(
        months, plan_draw, width=width, bottom=fact_draw,
        color=col_plan, alpha=0.35, label="План (прогноз)", zorder=3
    )


    # axes / grid
    ax.set_xticks(months)
    ax.set_xticklabels([RU_MONTHS[m] for m in months], fontsize=11)

    ax.grid(True, axis="y", color=grid_col, alpha=0.55, linewidth=0.9, zorder=1)
    ax.grid(False, axis="x")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_alpha(0.35)
    ax.spines["bottom"].set_alpha(0.35)

    ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1_000_000:,.0f}".replace(",", " ")))
    ax.set_ylabel("млн руб.", fontsize=11, color=text_muted)

    # y-limits for labels
    ymax = float(np.nanmax(total_draw)) if len(total_draw) else 1.0
    ax.set_ylim(0, ymax * 1.18)

    # --- labels above bars: total month value ---
    y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
    dy = 0.012 * y_range

    for m in months:
        v = float(total_draw[m - 1])
        if v <= 0:
            continue
        ax.text(
            m, v + dy,
            _fmt_mln(v),
            ha="center", va="bottom",
            fontsize=10.5,
            color="#111827",
            zorder=5,
        )

    # --- label for remaining part in current month (inside top segment) ---
    if remaining_forecast > 0:
        ax.text(
            curr_month,
            mtd_fact + remaining_forecast / 2,
            f"+{_fmt_mln(remaining_forecast)}",
            ha="center", va="center",
            fontsize=10.5,
            color="white",
            fontweight="bold",
            zorder=6,
        )

    # legend (custom: show that current month is stacked)
    legend_handles = [
        Patch(facecolor=col_fact, alpha=0.90, label="Факт"),
        Patch(facecolor=col_plan, alpha=0.35, label="План (прогноз)"),
    ]
    ax.legend(handles=legend_handles, frameon=False, loc="upper left")

    fig.tight_layout()
    return _to_svg(fig)

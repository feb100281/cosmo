# sales/reports/newspaper/charts/cash_ytd.py
"""
Графики страницы "Год к дате" (YTD): тот же визуальный язык, что и
charts/cash.py для месяца — просто на годовом горизонте.

  - build_cash_ytd_pace_chart:   такой же bullet-chart "план/факт", что и
    build_cash_pace_chart, но факт/план — накопительные с начала года, и
    вместо прогноза до конца месяца — прогноз до конца года по текущему
    среднедневному темпу.
  - build_cash_ytd_monthly_chart: помесячные бары факта (в этом году,
    сплошным) на фоне факта того же месяца прошлого года (контур) — чтобы
    сезонность и динамика год-к-году были видны на одной картинке, а не
    только в цифрах таблицы.
"""

from __future__ import annotations

from ..config import (
    COLOR_ACCENT,
    COLOR_INK,
    COLOR_INK_SOFT,
    COLOR_NEGATIVE,
    COLOR_POSITIVE,
    COLOR_RULE,
)
from ..render.helpers import fmt_money_short, to_decimal
from .common import apply_style, fig_to_svg, new_figure


def build_cash_ytd_pace_chart(ytd_data: dict) -> str:
    totals = ytd_data["totals"]

    plan_to_date = float(to_decimal(totals["plan_to_date"]))
    plan_year_full = float(to_decimal(totals["plan_year_full"]))
    fact = float(to_decimal(totals["fact"]))
    forecast = float(to_decimal(totals["projected_year_fact"]))

    max_value = max(plan_to_date, plan_year_full, fact, forecast, 1.0) * 1.1

    fig, ax = new_figure(width_in=7.4, height_in=1.5)

    bar_height = 0.5

    # Прогноз на конец года — светлый фон-бар, как и на месячном графике.
    ax.barh(0, forecast, height=bar_height, color="#e5ded0", zorder=2)

    is_on_track = totals["is_on_track"]
    fact_color = COLOR_POSITIVE if is_on_track else COLOR_ACCENT
    ax.barh(0, fact, height=bar_height, color=fact_color, zorder=3)

    # Метка "план на сегодня" (накопительно) — основная риска, как в месяце.
    if plan_to_date > 0:
        plan_color = COLOR_NEGATIVE if fact < plan_to_date else COLOR_INK
        ax.plot([plan_to_date, plan_to_date], [-0.32, 0.42], color=plan_color, linewidth=1.8, zorder=4)
        ax.text(
            plan_to_date, 0.56, f"План на сегодня {fmt_money_short(plan_to_date)}",
            ha="center", va="bottom", fontsize=8.4, color=plan_color, fontweight="bold",
        )

    # Годовой план — вторая, более тонкая риска правее (ориентир на весь год).
    if plan_year_full > plan_to_date > 0 or (plan_year_full > 0 and plan_to_date == 0):
        ax.plot(
            [plan_year_full, plan_year_full], [-0.32, 0.42],
            color=COLOR_INK_SOFT, linewidth=1.2, linestyle=(0, (2, 2)), zorder=4,
        )
        ax.text(
            plan_year_full, -0.42, f"План на год {fmt_money_short(plan_year_full)}",
            ha="center", va="top", fontsize=7.6, color=COLOR_INK_SOFT,
        )

    summary = (
        f"Факт с начала года {fmt_money_short(fact)}   ·   "
        f"Прогноз на конец года {fmt_money_short(forecast)}"
    )
    ax.text(
        0, -0.62, summary,
        ha="left", va="top", fontsize=8.6, color=COLOR_INK_SOFT,
    )

    ax.set_xlim(0, max_value)
    ax.set_ylim(-1.05, 0.95)
    ax.set_yticks([])
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    return fig_to_svg(fig)


def build_cash_ytd_monthly_chart(ytd_data: dict) -> str:
    """
    Помесячный факт с начала года — один ряд баров (без сравнения с прошлым
    годом: качество прошлогодних данных под вопросом, поэтому в отчёт не
    выводим). Текущий (ещё не закончившийся) месяц — акцентным цветом,
    завершённые месяцы — основным зелёным, как и в остальных графиках
    отчёта (build_store_pace_chart использует ту же логику).
    """
    import matplotlib.pyplot as plt

    apply_style()

    months = ytd_data["monthly"]
    if not months:
        return ""

    labels = [m["month_name"] for m in months]
    fact_values = [float(to_decimal(m["fact"])) for m in months]
    colors = [COLOR_ACCENT if m["is_current"] else COLOR_POSITIVE for m in months]

    fig, ax = plt.subplots(figsize=(7.4, 2.1), dpi=150)
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_RULE)

    x = range(len(months))
    ax.bar(list(x), fact_values, width=0.55, color=colors, zorder=3)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8.4)
    ax.set_yticks([])

    max_v = max(fact_values + [1.0])
    for i, v in enumerate(fact_values):
        ax.text(
            i, v + max_v * 0.02, fmt_money_short(v),
            ha="center", va="bottom", fontsize=7.4, color=COLOR_INK,
        )

    ax.set_ylim(0, max_v * 1.18)

    return fig_to_svg(fig)

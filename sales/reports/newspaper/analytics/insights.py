# sales/reports/newspaper/analytics/insights.py
"""
Автоматический аналитический слой.

Правила детерминированные (обычный Python, без LLM/внешних API). Каждое
правило проверяет конкретное условие на уже посчитанных данных и, если
условие выполняется, добавляет короткое профессиональное наблюдение.
Если условие не выполняется — наблюдение не добавляется: отчёт не должен
придумывать причины, которых нет в данных.

Формат одного insight:
    {
        "level": "negative" | "positive" | "neutral",
        "text": str,
    }
"""

from __future__ import annotations

from ..config import (
    CASH_STRONG_DEVIATION_PCT,
    STOCK_TOP_CATEGORY_CONCENTRATION_PCT,
)
from ..render.helpers import fmt_money_short, fmt_pct, fmt_pp


def _cash_insights(cash_data: dict, cash_analytics: dict) -> list:
    insights = []
    totals = cash_data["totals"]

    exec_pct = float(totals["exec_pct"])
    expected = cash_analytics["expected_pace_pct"]
    gap = cash_analytics["pace_gap_pp"]

    if cash_analytics["is_behind_pace"]:
        insights.append({
            "level": "negative",
            "text": (
                f"Темп сбора кэша отстаёт от календарного плана месяца: "
                f"выполнение {fmt_pct(totals['exec_pct'])} при ожидаемых "
                f"по темпу {expected:.0f}% ({fmt_pp(gap)})."
            ),
        })
    elif cash_analytics["is_ahead_pace"]:
        insights.append({
            "level": "positive",
            "text": (
                f"Темп сбора кэша опережает календарный план месяца: "
                f"выполнение {fmt_pct(totals['exec_pct'])} против ожидаемых "
                f"по темпу {expected:.0f}% ({fmt_pp(gap)})."
            ),
        })

    if not totals["is_on_track"] and totals["plan"] > 0:
        gap_amount = totals["plan"] - totals["projected_month_fact"]
        gap_pct = float(abs(totals["projected_diff"])) / float(totals["plan"]) * 100 if totals["plan"] else 0
        if gap_pct >= CASH_STRONG_DEVIATION_PCT:
            insights.append({
                "level": "negative",
                "text": (
                    f"При текущей динамике прогноз на конец месяца ниже плана "
                    f"на {fmt_money_short(abs(gap_amount))} ({gap_pct:.0f}%)."
                ),
            })

    worst = cash_analytics["worst_store"]
    if worst is not None and float(worst["exec_pct"]) < exec_pct:
        insights.append({
            "level": "negative",
            "text": (
                f"Основное отрицательное отклонение по выполнению плана "
                f"приходится на «{worst['store_name']}»: "
                f"{fmt_pct(worst['exec_pct'])} выполнения плана."
            ),
        })

    lagging = cash_analytics["lagging_stores"]
    if len(lagging) >= 2:
        names = "; ".join(r["store_name"] for r in lagging[:3])
        insights.append({
            "level": "negative",
            "text": (
                f"{len(lagging)} магазин(ов) заметно отстают от среднего "
                f"темпа сети по выполнению плана: {names}."
            ),
        })

    return insights


def _stocks_insights(stocks_data: dict, stocks_analytics: dict) -> list:
    insights = []

    if stocks_analytics["is_concentrated"]:
        top3_names = ", ".join(
            c["cat_name"] for c in stocks_analytics["top3_categories"]
        )
        insights.append({
            "level": "neutral",
            "text": (
                f"Высокая концентрация остатков: топ-3 категории "
                f"({top3_names}) формируют "
                f"{stocks_analytics['top3_share_pct_fmt']} остатков по количеству."
            ),
        })

    return insights


def _store_insights(store_sections: list) -> list:
    insights = []

    overstocked = [s for s in store_sections if s["is_overstocked"]]
    overstocked.sort(key=lambda s: s["imbalance_pp"], reverse=True)

    for section in overstocked[:2]:
        insights.append({
            "level": "neutral",
            "text": (
                f"«{section['store_name']}» имеет непропорционально большой "
                f"остаток: {section['stock']['qty_share_pct_fmt']} остатков "
                f"компании при {section['cash_share_pct']:.0f}% кэша сети "
                f"({fmt_pp(section['imbalance_pp'])})."
            ),
        })

    return insights


def build_insights(cash_data, cash_analytics, stocks_data, stocks_analytics, store_sections) -> list:
    insights = []
    insights.extend(_cash_insights(cash_data, cash_analytics))
    insights.extend(_stocks_insights(stocks_data, stocks_analytics))
    insights.extend(_store_insights(store_sections))
    return insights

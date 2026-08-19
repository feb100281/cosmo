# sales/reports/newspaper/charts/cash.py
"""
График "План / Факт / Прогноз" по кэшу компании.

Один компактный bullet-chart: факт — сплошной бар поверх более светлого
бара прогноза (прогноз виден как "довесок" справа от факта), план —
вертикальная метка-цель над баром. Числовые значения вынесены отдельной
строкой под графиком, чтобы подписи никогда не пересекались с линией
плана — это то, что ломало читаемость в первой версии графика.
"""

from __future__ import annotations

from decimal import Decimal

from ..config import (
    CHART_PALETTE,
    COLOR_ACCENT,
    COLOR_INK,
    COLOR_INK_SOFT,
    COLOR_NEGATIVE,
    COLOR_POSITIVE,
)
from ..render.helpers import fmt_money_short, fmt_pct, to_decimal
from .common import apply_style, fig_to_svg, new_figure


def build_cash_pace_chart(cash_data: dict) -> str:
    totals = cash_data["totals"]

    plan = float(to_decimal(totals["plan"]))
    fact = float(to_decimal(totals["fact"]))
    forecast = float(to_decimal(totals["projected_month_fact"]))

    max_value = max(plan, fact, forecast, 1.0) * 1.1

    fig, ax = new_figure(width_in=7.4, height_in=1.5)

    bar_height = 0.5

    # Прогноз — светлый фон-бар (виден как продолжение бара факта)
    ax.barh(0, forecast, height=bar_height, color="#e5ded0", zorder=2)

    # Факт — основной цвет, поверх
    is_on_track = totals["is_on_track"]
    fact_color = COLOR_POSITIVE if is_on_track else COLOR_ACCENT
    ax.barh(0, fact, height=bar_height, color=fact_color, zorder=3)

    # Метка плана — короткая вертикальная риска над баром, без пересечения
    # с текстом.
    if plan > 0:
        plan_color = COLOR_NEGATIVE if fact < plan else COLOR_INK
        ax.plot([plan, plan], [-0.32, 0.42], color=plan_color, linewidth=1.8, zorder=4)
        ax.text(
            plan, 0.56, f"План {fmt_money_short(plan)}",
            ha="center", va="bottom", fontsize=8.4, color=plan_color, fontweight="bold",
        )

    # Значения факта/прогноза — отдельной строкой под графиком, чтобы никогда
    # не пересекаться с линией плана или барами.
    summary = f"Факт {fmt_money_short(fact)}   ·   Прогноз на конец месяца {fmt_money_short(forecast)}"
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


def build_store_pace_chart(cash_data: dict) -> str:
    """
    Горизонтальные бары выполнения плана по каждому магазину — визуальный
    аналог таблицы на следующей странице, но без цифр по каждой колонке:
    сразу видно, кто идёт с опережением (зелёный, дальше отметки 100%),
    а кто отстаёт (терракотовый, не дотягивает до пунктирной линии плана).
    """
    apply_style()

    rows = [r for r in cash_data["rows"] if r["has_plan"]]
    if not rows:
        return ""

    rows = sorted(rows, key=lambda r: float(to_decimal(r["exec_pct"])), reverse=True)

    labels = [r["store_name"] for r in rows]
    values = [float(to_decimal(r["exec_pct"])) for r in rows]
    colors = [COLOR_POSITIVE if v >= 100 else COLOR_ACCENT for v in values]

    # Высота графика ограничена сверху: при большом числе магазинов страница
    # 1 не резиновая (альбомная A4, там же шапка + "Главное" + KPI + лид-
    # абзац + этот график) — если высота росла бы линейно без потолка, при
    # 7+ магазинах весь блок с графиками переставал помещаться на первую
    # страницу целиком (break-inside: avoid) и целиком уезжал на вторую.
    height_in = min(0.34 * len(rows) + 0.5, 2.6)
    fig, ax = new_figure(width_in=3.4, height_in=height_in)

    y_pos = range(len(rows))
    ax.barh(list(y_pos), values, color=colors, height=0.6, zorder=3)

    max_x = max(values + [100.0]) * 1.2
    ax.axvline(100, color=COLOR_INK, linewidth=1.0, linestyle=(0, (2, 2)), zorder=2)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=8.2)
    ax.invert_yaxis()
    ax.set_xlim(0, max_x)
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    for i, v in enumerate(values):
        ax.text(
            v + max_x * 0.015, i, f"{v:.0f}%",
            va="center", ha="left", fontsize=7.6, color=COLOR_INK_SOFT,
        )

    ax.text(
        100, -0.75, "план", ha="center", va="bottom", fontsize=6.6, color=COLOR_INK_SOFT,
    )

    return fig_to_svg(fig)


def build_cash_share_donut(cash_data: dict, max_slices: int = 6) -> str:
    """
    Структура кэша по магазинам — донат-диаграмма с легендой (магазин,
    доля, факт). Мелкие магазины сверх max_slices агрегируются в
    "Остальные", чтобы диаграмма оставалась читаемой, а не превращалась
    в десяток тонких сегментов.
    """
    import matplotlib.pyplot as plt

    apply_style()

    rows = [r for r in cash_data["rows"] if r["fact"] and r["fact"] > 0]
    rows = sorted(rows, key=lambda r: r["fact"], reverse=True)

    total_fact = sum((r["fact"] for r in rows), Decimal("0"))
    if total_fact <= 0 or not rows:
        return ""

    head = rows[:max_slices]
    tail = rows[max_slices:]

    labels = [r["store_name"] for r in head]
    values = [float(r["fact"]) for r in head]

    if tail:
        tail_sum = float(sum((r["fact"] for r in tail), Decimal("0")))
        labels.append(f"Остальные ({len(tail)})")
        values.append(tail_sum)

    colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(2.9, 2.9), dpi=150)
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    wedges, _ = ax.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "#faf8f4", "linewidth": 1.2},
    )
    ax.set_aspect("equal")

    total_fact_f = float(total_fact)
    ax.text(
        0, 0.06, "Факт МТД", ha="center", va="center", fontsize=7.4, color=COLOR_INK_SOFT,
    )
    ax.text(
        0, -0.08, fmt_money_short(total_fact_f), ha="center", va="center",
        fontsize=10.5, color=COLOR_INK, fontweight="bold",
    )

    legend_labels = [
        f"{label} — {fmt_pct(Decimal(str(value)) / total_fact * 100)}"
        for label, value in zip(labels, values)
    ]
    ax.legend(
        wedges, legend_labels,
        loc="center left", bbox_to_anchor=(1.0, 0.5),
        frameon=False, fontsize=10.5, labelspacing=1.1,
        handlelength=1.1, handleheight=1.1,
    )

    return fig_to_svg(fig)

# sales/reports/store_plan/charts.py
"""
График плана по магазинам — горизонтальные бары, отсортированные по
убыванию, как в Newspaper. Строится через ту же инфраструктуру Matplotlib
(new_figure/fig_to_svg), чтобы график выглядел как часть одной системы
отчётов, а не как отдельная картинка со своим стилем.

Для одного магазина график не строится (сравнивать не с чем) — печать
одного магазина показывает только KPI и таблицу из одной строки.
"""

from __future__ import annotations

from ..newspaper.charts.common import fig_to_svg, new_figure
from ..newspaper.config import CHART_PALETTE, COLOR_INK_SOFT
from ..newspaper.render.helpers import fmt_money_short


def build_plan_chart(rows: list) -> str:
    """
    График всегда рисуется под левую колонку страницы (см. .plan-columns в
    report.css — двухколоночная вёрстка: график слева, таблица справа,
    таблица при необходимости продолжается на следующей странице).
    Ширина и высота графика поэтому фиксированы под размер колонки, а не
    зависят от числа магазинов.
    """
    items = [(r["store_name"], float(r["amount"] or 0)) for r in rows if r["amount"]]
    if len(items) < 2:
        return ""

    items.sort(key=lambda x: x[1], reverse=True)

    labels = [name for name, _ in items]
    values = [value for _, value in items]
    max_value = max(values) or 1.0

    width_in = 5.0
    # Высота держится в жёстком потолке независимо от числа магазинов:
    # график стоит в начале страницы вместе с KPI и лидом — если он выше
    # оставшегося места, целиком уезжает на следующую страницу, а с ним и
    # вся колоночная вёрстка (получается пустая страница). Больше строк —
    # бары просто чуть тоньше, а не выше общая высота картинки.
    height_in = min(0.22 * len(items) + 0.4, 3.4)
    fig, ax = new_figure(width_in=width_in, height_in=height_in)

    y_positions = range(len(items))
    colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(items))]

    ax.barh(list(y_positions), values, color=colors, height=0.62, zorder=3)
    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(labels, fontsize=8.2)
    ax.invert_yaxis()
    ax.set_xlim(0, max_value * 1.3)
    ax.set_xticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    for i, value in enumerate(values):
        label = fmt_money_short(value)
        ax.text(
            value + max_value * 0.02, i,
            label, va="center", ha="left", fontsize=7.6, color=COLOR_INK_SOFT,
        )

    return fig_to_svg(fig)

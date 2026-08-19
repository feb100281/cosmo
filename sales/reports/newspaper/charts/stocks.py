# sales/reports/newspaper/charts/stocks.py
"""
График распределения остатков по магазинам/складам (по количеству —
денежной оценки остатков в отчёте нет, см. data/stocks.py).

Горизонтальные бары долей — читаются быстрее и компактнее, чем pie/donut,
и лучше подходят для печатного документа, где нужно сравнить 5-10 точек.
"""

from __future__ import annotations

from ..config import CHART_PALETTE, COLOR_INK_SOFT
from .common import fig_to_svg, new_figure


def build_stock_distribution_chart(stocks_data: dict, unassigned_label: str) -> str:
    """
    Берёт ВСЕ подразделения (магазины и физические склады) напрямую из
    stocks_data["by_store"] — то же самое место хранения, что показано в
    таблице ниже, без группировки в общий "склад". "Не распределено"
    (позиции без разбивки по местам хранения) добавляется отдельным
    пунктом, если такие остатки есть.
    """
    items = []

    for name, values in stocks_data.get("by_store", {}).items():
        qty = float(values.get("qty_available") or 0)
        if qty <= 0:
            continue
        items.append((name, qty))

    unassigned = stocks_data.get("unassigned_bucket") or {}
    un_qty = float(unassigned.get("qty_available") or 0)
    if un_qty > 0:
        items.append((unassigned_label, un_qty))

    if not items:
        return ""

    items.sort(key=lambda x: x[1], reverse=True)
    items = items[:8]

    labels = [name for name, _ in items]
    values = [qty for _, qty in items]
    max_value = max(values) or 1.0

    fig, ax = new_figure(width_in=6.4, height_in=0.42 * len(items) + 0.4)

    y_positions = range(len(items))
    colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(items))]

    ax.barh(list(y_positions), values, color=colors, height=0.62, zorder=3)

    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(labels, fontsize=8.4)
    ax.invert_yaxis()
    ax.set_xlim(0, max_value * 1.22)
    ax.set_xticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    for i, qty in enumerate(values):
        label = f"{qty:,.0f} шт.".replace(",", " ")
        ax.text(
            qty + max_value * 0.02, i,
            label, va="center", ha="left", fontsize=7.8, color=COLOR_INK_SOFT,
        )

    return fig_to_svg(fig)

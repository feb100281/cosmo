# sales/reports/newspaper/charts/common.py
"""
Общая инфраструктура для графиков Newspaper.

Графики рендерятся через Matplotlib напрямую в SVG (не PNG, чтобы в PDF
они оставались идеально чёткими при любом масштабе) и встраиваются в HTML
как инлайн-разметка. Никакого JavaScript/Plotly в браузере — PDF не
зависит от клиентского рендеринга.

Здесь — единый визуальный стиль (шрифты, цвета, отступы), чтобы все графики
отчёта выглядели как одна система, а не как случайный набор картинок.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("SVG")

import matplotlib.pyplot as plt  # noqa: E402

from ..config import (  # noqa: E402
    COLOR_INK,
    COLOR_INK_SOFT,
    COLOR_RULE,
)

_STYLE_APPLIED = False


def apply_style() -> None:
    global _STYLE_APPLIED
    if _STYLE_APPLIED:
        return

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
        "font.size": 9,
        "text.color": COLOR_INK,
        "axes.edgecolor": COLOR_RULE,
        "axes.labelcolor": COLOR_INK_SOFT,
        "xtick.color": COLOR_INK_SOFT,
        "ytick.color": COLOR_INK_SOFT,
        "axes.linewidth": 0.6,
        "svg.fonttype": "path",
    })
    _STYLE_APPLIED = True


def new_figure(width_in: float, height_in: float):
    apply_style()
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=150)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_RULE)
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    return fig, ax


def fig_to_svg(fig) -> str:
    """Рендерит фигуру в строку SVG (для встраивания в HTML) и закрывает её."""
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)
    svg = buf.getvalue()

    # Убираем XML-пролог/DOCTYPE — внутри HTML-документа они не нужны и
    # WeasyPrint от них не выигрывает, а вложенный <svg> должен идти сразу.
    marker = "<svg"
    idx = svg.find(marker)
    if idx > 0:
        svg = svg[idx:]
    return svg

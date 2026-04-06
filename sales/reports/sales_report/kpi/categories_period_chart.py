# sales/reports/sales_report/kpi/categories_period_chart.py

from __future__ import annotations

import io
import re
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


# ----------------- helpers -----------------

def _fig_to_svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return _make_svg_responsive(buf.getvalue())


def _make_svg_responsive(svg: str) -> str:
    if not svg:
        return svg
    svg = re.sub(r'<svg([^>]*?)\swidth="[^"]+"', r'<svg\1 width="100%"', svg, count=1)
    svg = re.sub(r'<svg([^>]*?)\sheight="[^"]+"', r'<svg\1 height="auto"', svg, count=1)
    return svg


def _human_money(x: float) -> str:
    x = float(x)
    ax = abs(x)
    if ax >= 1_000_000_000:
        return f"{x/1_000_000_000:.2f} млрд"
    if ax >= 1_000_000:
        return f"{x/1_000_000:.2f} млн"
    if ax >= 1_000:
        return f"{x/1_000:.1f} тыс"
    return f"{x:.0f}"


def _human_qty(x: float) -> str:
    x = float(x)
    ax = abs(x)
    if ax >= 1_000_000:
        return f"{x/1_000_000:.2f} млн шт"
    if ax >= 1_000:
        return f"{x/1_000:.1f} тыс шт"
    return f"{x:.0f} шт"


def _money_formatter(_):
    return FuncFormatter(lambda v, _pos: _human_money(v))


# ----------------- main -----------------

def build_categories_pareto_svg(
    df: pd.DataFrame,
    title: str,
    top_n: int = 10,
) -> Optional[str]:
    """
    Категории за период (понятно собственнику + полезно операционщикам):
      - Горизонтальные бары: выручка по Top-N + "Прочие"
      - Линия: накопительная доля (Pareto), вторичная
      - Инсайт: "80% выручки = N катег." — в виде заметного бейджа
      - Сноска "* Прочее включает: ..." внутри SVG снизу
      - Минималистичный стиль как в orders_chart (без боковых рамок)
    """
    if df is None or df.empty:
        return None

    required = {"cat_name", "amount", "quant"}
    if not required.issubset(df.columns):
        return None

    x = df.copy()
    x["cat_name"] = x["cat_name"].fillna("Без категории").astype(str)
    x["amount"] = pd.to_numeric(x["amount"], errors="coerce").fillna(0.0)
    x["quant"] = pd.to_numeric(x["quant"], errors="coerce").fillna(0.0)

    x = x.loc[x["amount"].abs() > 1e-9].copy()
    if x.empty:
        return None

    x = x.sort_values("amount", ascending=False)
    total = float(x["amount"].sum())
    if total == 0:
        return None

    # Top-N + Прочие
    has_other = False
    other_note = ""
    # if top_n is not None and top_n > 0 and len(x) > top_n:
    #     has_other = True
    #     top = x.head(top_n).copy()
    #     rest = x.iloc[top_n:].copy()

    #     other_amount = float(rest["amount"].sum())
    #     other = pd.DataFrame([{"cat_name": "Прочие", "amount": other_amount}])
    #     x = pd.concat([top, other], ignore_index=True)
    
    if top_n is not None and top_n > 0 and len(x) > top_n:
        has_other = True
        top = x.head(top_n).copy()
        rest = x.iloc[top_n:].copy()

        other_amount = float(rest["amount"].sum())
        other_quant = float(rest["quant"].sum())
        other = pd.DataFrame([{"cat_name": "Прочие", "amount": other_amount, "quant": other_quant}])
        x = pd.concat([top, other], ignore_index=True)

        # Сноска: что включено в "Прочие"
        # Берём самые крупные категории из хвоста, чтобы ответить на вопрос "что там"
        rest = rest.sort_values("amount", ascending=False)
        tail_names = rest["cat_name"].astype(str).head(5).tolist()
        n_tail = int(len(rest))
        if tail_names:
            other_note = f"* Прочее включает: {', '.join(tail_names)}"
            if n_tail > 5:
                other_note += f" и ещё {n_tail - 5} катег."
        else:
            other_note = "* Прочее включает категории вне Top-N."
    else:
        x = x.head(top_n).copy()

    # доли
    x["share"] = x["amount"] / total
    x["cum_share"] = x["share"].cumsum()

    labels = x["cat_name"].tolist()
    vals = x["amount"].to_numpy(dtype=float)
    qty = x["quant"].to_numpy(dtype=float)
    cum = x["cum_share"].to_numpy(dtype=float)

    n = len(labels)

    # --- стиль (в духе orders_chart) ---
    COLOR_BAR = "#2563EB"
    COLOR_LINE = "#6B7280"
    GRID_COLOR = "#D1D5DB"
    TEXT_COLOR = "#111827"
    LABEL_FADED = "#6B7280"  # бледный как подпись Pareto

    fig_h = max(3.9, 0.45 * n + 1.5)  # чуть больше, чтобы влезла сноска
    fig_w = 11.2

    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_subplot(111)
    y = np.arange(n)

    # бары
    ax.barh(
        y,
        vals,
        color=COLOR_BAR,
        edgecolor="white",
        linewidth=0.8,
    )

    ax.set_title(title, loc="left", pad=12, fontsize=13, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()

    # подпись оси X — бледная
    ax.set_xlabel("Чистая выручка за период", labelpad=8, color=LABEL_FADED)
    ax.xaxis.set_major_formatter(_money_formatter(ax))

    ax.grid(axis="x", linestyle="-", linewidth=0.8, color=GRID_COLOR, alpha=0.7)
    ax.set_axisbelow(True)

    # ✅ убираем рамки по бокам / сверху (оставляем низ слегка)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_alpha(0.25)

    # подписи справа у баров
    max_total = float(np.max(vals)) if len(vals) else 0.0
    right_pad = max(1.0, max_total * 0.14)
    ax.set_xlim(0, max_total + right_pad)

    for i, v in enumerate(vals):
        label = f"{_human_money(v)} · {_human_qty(qty[i])}"
        ax.text(
            v + right_pad * 0.02,
            i,
            label,
            va="center",
            ha="left",
            fontsize=10,
            color=TEXT_COLOR,
            fontweight="bold",
        )
    # --- Pareto линия (вторичная) ---
    ax2 = ax.twiny()
    ax2.set_xlim(0, 1.05)
    ax2.set_xlabel("Накопительная доля (Pareto)", labelpad=6, color=LABEL_FADED)
    ax2.xaxis.set_major_formatter(FuncFormatter(lambda v, _pos: f"{int(round(v*100))}%"))

    ax2.plot(
        cum,
        y,
        marker="o",
        linewidth=1.15,
        markersize=4,
        color=COLOR_LINE,
        alpha=0.9,
        zorder=3,
    )

    # ✅ рамку у верхней оси тоже убираем
    for spine in ["top", "right", "left", "bottom"]:
        ax2.spines[spine].set_visible(False)

    ax2.tick_params(axis="x", colors=LABEL_FADED)

    # --- 80% инсайт (бейдж) ---
    target = 0.80
    idx_80 = None
    for i, v in enumerate(cum):
        if v >= target:
            idx_80 = i
            break

    if idx_80 is not None:
        n_cats = idx_80 + 1

        # вертикальная линия 80% — тонкая/бледная
        ax2.axvline(target, color=COLOR_LINE, linewidth=1.0, alpha=0.25, linestyle="--", zorder=2)

        # точка
        ax2.scatter([target], [idx_80], s=34, color=COLOR_LINE, alpha=0.95, zorder=5)

        # Бейдж (плашка) — чтобы бросалось в глаза
        badge_text = f"80% выручки = {n_cats} катег."
        ax2.text(
            min(target + 0.03, 1.01),
            idx_80,
            badge_text,
            va="center",
            ha="left",
            fontsize=10.5,
            fontweight="bold",
            color=TEXT_COLOR,
            bbox=dict(
                boxstyle="round,pad=0.25,rounding_size=0.8",
                fc="#EEF2FF",   # очень светлая синяя плашка
                ec="none",
                alpha=0.95,
            ),
            zorder=6,
        )

    # --- Сноска про "Прочее" снизу (внутри SVG) ---
    if has_other and other_note:
        # немного места снизу под сноску
        ax.margins(y=0.06)
        # координаты фигуры (в процентах): x=0.01, y=0.01 — низ слева
        fig.text(
            0.01,
            0.01,
            other_note,
            ha="left",
            va="bottom",
            fontsize=9.5,
            color=LABEL_FADED,
        )

    fig.tight_layout()
    return _fig_to_svg(fig)

from __future__ import annotations

import io
import re
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


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


def _money_formatter(_):
    return FuncFormatter(lambda v, _pos: _human_money(v))


def build_manufacturers_pareto_svg(
    df: pd.DataFrame,
    title: str,
    top_n: int = 7,
) -> Optional[str]:
    """
    Производители за период:
      - Горизонтальные бары: выручка по Top-N + "Прочие"
      - Линия: накопительная доля (Pareto)
      - Инсайт: "80% выручки = N производителей"
      - Сноска "* Прочее включает: ..." внутри SVG снизу
      - Минималистичный стиль (как у твоего categories_period_chart)
    """
    if df is None or df.empty:
        return None

    required = {"manufacturer_name", "amount"}
    if not required.issubset(df.columns):
        return None

    x = df.copy()
    x["manufacturer_name"] = x["manufacturer_name"].fillna("Производитель не указан").astype(str)
    x["amount"] = pd.to_numeric(x["amount"], errors="coerce").fillna(0.0)

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

    if top_n is not None and top_n > 0 and len(x) > top_n:
        has_other = True
        top = x.head(top_n).copy()
        rest = x.iloc[top_n:].copy()

        other_amount = float(rest["amount"].sum())
        other = pd.DataFrame([{"manufacturer_name": "Прочие", "amount": other_amount}])
        x = pd.concat([top, other], ignore_index=True)

        rest = rest.sort_values("amount", ascending=False)
        tail_names = rest["manufacturer_name"].astype(str).head(5).tolist()
        n_tail = int(len(rest))
        if tail_names:
            other_note = f"* Прочее включает: {', '.join(tail_names)}"
            if n_tail > 5:
                other_note += f" и ещё {n_tail - 5} произв."
        else:
            other_note = "* Прочее включает производителей вне Top-N."
    else:
        x = x.head(top_n).copy()

    # доли
    x["share"] = x["amount"] / total
    x["cum_share"] = x["share"].cumsum()

    labels = x["manufacturer_name"].tolist()
    vals = x["amount"].to_numpy(dtype=float)
    cum = x["cum_share"].to_numpy(dtype=float)

    n = len(labels)

    # стиль
    COLOR_BAR = "#2563EB"
    COLOR_LINE = "#6B7280"
    GRID_COLOR = "#D1D5DB"
    TEXT_COLOR = "#111827"
    LABEL_FADED = "#6B7280"

    fig_h = max(3.9, 0.45 * n + 1.5)
    fig_w = 11.2

    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_subplot(111)
    y = np.arange(n)

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

    ax.set_xlabel("Чистая выручка за период", labelpad=8, color=LABEL_FADED)
    ax.xaxis.set_major_formatter(_money_formatter(ax))

    ax.grid(axis="x", linestyle="-", linewidth=0.8, color=GRID_COLOR, alpha=0.7)
    ax.set_axisbelow(True)

    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_alpha(0.25)

    max_total = float(np.max(vals)) if len(vals) else 0.0
    right_pad = max(1.0, max_total * 0.14)
    ax.set_xlim(0, max_total + right_pad)

    for i, v in enumerate(vals):
        ax.text(
            v + right_pad * 0.02,
            i,
            _human_money(v),
            va="center",
            ha="left",
            fontsize=10,
            color=TEXT_COLOR,
            fontweight="bold",
        )

    # Pareto
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

    for spine in ["top", "right", "left", "bottom"]:
        ax2.spines[spine].set_visible(False)

    ax2.tick_params(axis="x", colors=LABEL_FADED)

    # 80% бейдж
    target = 0.80
    idx_80 = None
    for i, v in enumerate(cum):
        if v >= target:
            idx_80 = i
            break

    if idx_80 is not None:
        n_mf = idx_80 + 1
        ax2.axvline(target, color=COLOR_LINE, linewidth=1.0, alpha=0.25, linestyle="--", zorder=2)
        ax2.scatter([target], [idx_80], s=34, color=COLOR_LINE, alpha=0.95, zorder=5)

        badge_text = f"80% выручки = {n_mf} произв."
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
                fc="#EEF2FF",
                ec="none",
                alpha=0.95,
            ),
            zorder=6,
        )

    # Сноска "Прочие"
    if has_other and other_note:
        ax.margins(y=0.06)
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
# sales/reports/meeting_brief/charts.py
"""Графики отчёта: Matplotlib → инлайн-SVG (чётко и в браузере, и в PDF)."""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("SVG")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from . import fmt as F  # noqa: E402

INK = "#1c2321"
INK_SOFT = "#5b6b63"
RULE = "#d7ddd3"
GREEN = "#1e6b4f"
GREEN_SOFT = "#9fc3b0"
ACCENT = "#c1663a"
GHOST = "#cfd6cc"


def _style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
        "font.size": 8.5,
        "text.color": INK,
        "axes.edgecolor": RULE,
        "xtick.color": INK_SOFT,
        "ytick.color": INK_SOFT,
        "axes.linewidth": 0.6,
        "svg.fonttype": "path",
    })


def _svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)
    s = buf.getvalue()
    i = s.find("<svg")
    return s[i:] if i > 0 else s


def _mln(v, _pos=None) -> str:
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.1f}".replace(".", ",") + " млн"
    if abs(v) >= 1_000:
        return f"{v / 1_000:.0f} тыс."
    return f"{v:.0f}"


def cash_by_day(cash: dict, width_in: float = 10.6, height_in: float = 2.5) -> str:
    daily = cash["daily"]
    if not daily or not any(d["cash_in"] for d in daily):
        return '<p class="empty-note">Поступлений за период нет</p>'
    _style()
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=150)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    n = len(daily)
    xs = list(range(n))
    vals = [d["cash_in"] for d in daily]
    prev = cash["daily_prev"][:n]
    best = cash["best_day"]["date"] if cash["best_day"] else None
    worst = cash["worst_day"]["date"] if cash["worst_day"] else None
    colors = [GREEN if d["date"] == best else (ACCENT if d["date"] == worst else GREEN_SOFT) for d in daily]

    w = 0.62 if n <= 14 else 0.72
    if prev:
        ax.bar([x - w * 0.18 for x in xs[:len(prev)]], prev, width=w, color=GHOST, zorder=1,
               label="Прошлый период")
    ax.bar(xs, vals, width=w * (0.64 if prev else 1), color=colors, zorder=2, label="Текущий период")
    ax.axhline(cash["avg_day"], color=INK_SOFT, lw=0.7, ls=(0, (3, 3)), zorder=3)
    ax.text(n - 0.5, cash["avg_day"], f"  в среднем {_mln(cash['avg_day'])}", va="bottom", ha="right",
            fontsize=7.5, color=INK_SOFT)

    if n <= 16:
        for x, v in zip(xs, vals):
            if v > 0:
                ax.text(x, v, _mln(v), ha="center", va="bottom", fontsize=7, color=INK)
        labels = [F.day_short(d["date"]) for d in daily]
    else:
        labels = [d["date"].strftime("%d") for d in daily]
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.yaxis.set_major_formatter(FuncFormatter(_mln))
    ax.tick_params(axis="y", labelsize=7, length=0)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color=RULE, lw=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlim(-0.6, n - 0.4)
    return _svg(fig)

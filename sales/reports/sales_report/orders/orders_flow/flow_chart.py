import io
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


def _fig_to_svg(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


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


def _money_formatter():
    return FuncFormatter(lambda v, _pos: _human_money(v))


def _bucket_sort_key(label: str) -> float:
    s = str(label).replace("–", "-").replace("—", "-")
    m = re.search(r"(\d+)", s)
    return float(m.group(1)) if m else 1e9


def build_aging_svg(aging_df: pd.DataFrame):

    if aging_df is None or aging_df.empty:
        return None

    df = aging_df.copy()

    df["aging_bucket"] = df["aging_bucket"].astype(str)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    # сортируем по возрасту
    df["_k"] = df["aging_bucket"].map(_bucket_sort_key)
    df = df.sort_values("_k").drop(columns="_k")

    # подписи по оси Y сразу в днях
    y_labels = [f"{b} дн." if not b.endswith("+") else f"{b} дн." for b in df["aging_bucket"]]
    values = df["amount"].to_numpy(dtype=float)

    total = float(values.sum()) if len(values) else 0.0

    n = len(y_labels)
    fig_h = max(3.8, 0.48 * n + 1.2)
    fig = plt.figure(figsize=(11, fig_h))
    ax = fig.add_subplot(111)

    y = np.arange(n)

    BASE_COLOR = "#2563EB"
    TAIL_COLOR = "#DC2626"   # акцент на длинные хвосты
    GRID_COLOR = "#D1D5DB"
    TEXT_COLOR = "#111827"

    # если бакет содержит "60" или "+" — считаем длинным хвостом
    def _is_long_tail(label):
        return "+" in label or "61" in label or "90" in label

    colors = [TAIL_COLOR if _is_long_tail(lbl) else BASE_COLOR for lbl in df["aging_bucket"]]


    ax.barh(y, values, color=colors, edgecolor="white", linewidth=0.8)

    ax.set_yticks(y)
    ax.set_yticklabels(y_labels, fontsize=10)
    ax.invert_yaxis()

    ax.set_title(
        "Возраст отгруженных заказов (на момент отгрузки)",
        loc="left",
        fontsize=13,
        fontweight="bold",
        pad=10,
    )
    fig.text(
        0.125,   # выравнивание по левому краю графика
        0.90,    # вертикальная позиция под заголовком
        "Возраст = от даты заказа до последней отгрузки в периоде",
        fontsize=10,
        color="#6B7280",
        ha="left",
        va="top",
    )


    ax.set_xlabel("Чистая выручка за период")
    ax.xaxis.set_major_formatter(_money_formatter())

    # сетка
    ax.grid(axis="x", linestyle="-", linewidth=0.8, color=GRID_COLOR, alpha=0.7)
    ax.set_axisbelow(True)

    # убираем рамки
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_alpha(0.3)

    # подписи: сумма + доля %
    max_val = float(np.max(values)) if len(values) else 0.0
    pad = max_val * 0.08 if max_val else 1
    ax.set_xlim(0, max_val + pad)

    for i, v in enumerate(values):
        pct = (v / total * 100) if total else 0
        ax.text(
            v + pad * 0.1,
            i,
            f"{_human_money(v)}  •  {pct:.1f}%",
            va="center",
            ha="left",
            fontsize=10,
            color=TEXT_COLOR,
            fontweight="bold",
        )

    ax.margins(y=0.06)
    fig.tight_layout()

    return _fig_to_svg(fig)

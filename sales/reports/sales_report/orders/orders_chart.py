# # sales/reports/sales_report/orders/orders_chart.py

# from __future__ import annotations

# import io
# from datetime import date
# from typing import Optional

# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt


# def _fig_to_svg(fig) -> str:
#     buf = io.StringIO()
#     fig.savefig(buf, format="svg", bbox_inches="tight")
#     plt.close(fig)
#     return buf.getvalue()


# def build_orders_carryover_by_type_svg(
#     df_orders: pd.DataFrame,
#     period_start: date,
#     period_end: date,
#     top_n: int = 8,
# ) -> Optional[str]:
#     """
#     Stacked bar: Net amount_period по типам заказов
#     разложение на:
#       - New (order_date внутри периода)
#       - Carryover (order_date раньше периода)
#     """
#     if df_orders is None or df_orders.empty:
#         return None

#     df = df_orders.copy()
#     df["is_new"] = df["client_order_date"].dt.date.between(period_start, period_end)
#     df["bucket"] = np.where(df["is_new"], "New", "Carryover")

#     pt = (
#         df.pivot_table(
#             index="client_order_type",
#             columns="bucket",
#             values="amount_period",
#             aggfunc="sum",
#             fill_value=0,
#         )
#         .reset_index()
#     )

#     # обеспечим колонки
#     if "New" not in pt.columns:
#         pt["New"] = 0.0
#     if "Carryover" not in pt.columns:
#         pt["Carryover"] = 0.0

#     pt["Total"] = pt["New"] + pt["Carryover"]
#     pt = pt.sort_values("Total", ascending=False).head(top_n)

#     labels = pt["client_order_type"].tolist()
#     new_vals = pt["New"].to_numpy()
#     carry_vals = pt["Carryover"].to_numpy()

#     fig = plt.figure(figsize=(10.5, 4.6))
#     ax = fig.add_subplot(111)

#     x = np.arange(len(labels))

#     ax.bar(x, carry_vals, label="Carryover (заказы до периода)")
#     ax.bar(x, new_vals, bottom=carry_vals, label="New (заказы периода)")

#     ax.set_title("Сквозные заказы: отгрузка периода = New + Carryover (по типам)")
#     ax.set_xticks(x)
#     ax.set_xticklabels(labels, rotation=20, ha="right")

#     ax.set_ylabel("Чистая выручка за период (dt − cr)")

#     ax.legend(loc="upper right")

#     # немного воздуха
#     ax.margins(x=0.02)

#     return _fig_to_svg(fig)




# sales/reports/sales_report/orders/orders_chart.py

from __future__ import annotations

import io
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


def _fig_to_svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _human_money(x: float) -> str:
    """
    1 234 -> 1.2k
    1 234 567 -> 1.23m
    """
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


def _safe_date_between(s: pd.Series, start: date, end: date) -> pd.Series:
    """
    s: datetime-like
    """
    s = pd.to_datetime(s, errors="coerce")
    return s.dt.date.between(start, end)


def build_orders_carryover_by_type_svg(
    df_orders: pd.DataFrame,
    period_start: date,
    period_end: date,
    top_n: int = 8,
) -> Optional[str]:
    """
    Горизонтальный stacked bar:
      Total amount_period по типам заказов
      разложение на:
        - New (order_date внутри периода)
        - Carryover (order_date раньше периода)

    Визуальные улучшения:
      - горизонтальные бары
      - сортировка по Total
      - подпись Total справа
      - доля Carryover и New в %
      - проценты с 1 знаком после запятой
      - human-readable шкала (тыс/млн/млрд)
      - аккуратная сетка и минимализм
      - "Прочие" для хвоста (если типов больше top_n)
    """
    if df_orders is None or df_orders.empty:
        return None

    required = {"client_order_date", "client_order_type", "amount_period"}
    missing = required - set(df_orders.columns)
    if missing:
        return None

    df = df_orders.copy()

    # типы / суммы
    df["client_order_type"] = df["client_order_type"].fillna("Не указан").astype(str)
    df["amount_period"] = pd.to_numeric(df["amount_period"], errors="coerce").fillna(0.0)

    # new / carryover
    is_new = _safe_date_between(df["client_order_date"], period_start, period_end)
    df["bucket"] = np.where(is_new, "New", "Carryover")

    pt = (
        df.pivot_table(
            index="client_order_type",
            columns="bucket",
            values="amount_period",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    # обеспечим колонки
    if "New" not in pt.columns:
        pt["New"] = 0.0
    if "Carryover" not in pt.columns:
        pt["Carryover"] = 0.0

    pt["Total"] = pt["New"] + pt["Carryover"]

    # уберём нулевые строки, если вдруг есть
    pt = pt.loc[pt["Total"].abs() > 1e-9].copy()
    if pt.empty:
        return None

    # сортировка
    pt = pt.sort_values("Total", ascending=False)

    # top_n + "Прочие"
    if top_n is not None and top_n > 0 and len(pt) > top_n:
        top = pt.head(top_n).copy()
        rest = pt.iloc[top_n:].copy()
        other = pd.DataFrame(
            {
                "client_order_type": ["Прочие"],
                "New": [rest["New"].sum()],
                "Carryover": [rest["Carryover"].sum()],
            }
        )
        other["Total"] = other["New"] + other["Carryover"]
        pt = pd.concat([top, other], ignore_index=True)

    # данные для графика
    labels = pt["client_order_type"].tolist()
    carry_vals = pt["Carryover"].to_numpy(dtype=float)
    new_vals = pt["New"].to_numpy(dtype=float)
    total_vals = pt["Total"].to_numpy(dtype=float)

    # --- Визуальный стиль ---
    COLOR_CARRY = "#6B7280"  # slate/gray
    COLOR_NEW = "#2563EB"    # blue
    COLOR_TOTAL_TEXT = "#111827"
    GRID_COLOR = "#D1D5DB"

    n = len(labels)
    fig_h = max(3.6, 0.48 * n + 1.2)
    fig_w = 11.2

    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_subplot(111)

    y = np.arange(n)

    # бары
    ax.barh(
        y,
        carry_vals,
        label="Переходящие заказы",
        color=COLOR_CARRY,
        edgecolor="white",
        linewidth=0.8,
    )
    ax.barh(
        y,
        new_vals,
        left=carry_vals,
        label="Новые заказы",
        color=COLOR_NEW,
        edgecolor="white",
        linewidth=0.8,
    )

    # заголовок
    title = "Отгрузка периода по типам заказов: Новые + Переходящие заказы"
    subtitle = f"Период: {period_start.strftime('%d.%m.%Y')} – {period_end.strftime('%d.%m.%Y')}"
    ax.set_title(f"{title}\n{subtitle}", loc="left", pad=12, fontsize=13, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()

    ax.set_xlabel("Чистая выручка за период", labelpad=8)
    ax.xaxis.set_major_formatter(_money_formatter(ax))

    ax.grid(axis="x", linestyle="-", linewidth=0.8, color=GRID_COLOR, alpha=0.7)
    ax.set_axisbelow(True)

    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_alpha(0.3)

    ax.legend(loc="lower right", frameon=False, fontsize=10)

    max_total = float(np.max(total_vals)) if len(total_vals) else 0.0
    right_pad = max(1.0, max_total * 0.10)
    ax.set_xlim(0, max_total + right_pad)

    # подписи Total + доли Carryover и New (1 знак после запятой)
    for i, (carry, new, total) in enumerate(zip(carry_vals, new_vals, total_vals)):
        # Total справа
        ax.text(
            total + right_pad * 0.02,
            i,
            _human_money(total),
            va="center",
            ha="left",
            fontsize=10,
            color=COLOR_TOTAL_TEXT,
            fontweight="bold",
        )

        if total > 0:
            carry_share = (carry / total) * 100.0
            new_share = (new / total) * 100.0

            # 1) подпись доли Carryover — в центре серого сегмента
            if carry > 0 and total >= max_total * 0.12 and carry_share >= 4.0:
                ax.text(
                    carry * 0.5,
                    i,
                    f"{carry_share:.1f}%",
                    va="center",
                    ha="center",
                    fontsize=9,
                    color="white",
                    fontweight="bold",
                )

            # 2) подпись доли New — в центре синего сегмента
            if new > 0 and total >= max_total * 0.12 and new_share >= 4.0:
                ax.text(
                    carry + new * 0.5,
                    i,
                    f"{new_share:.1f}%",
                    va="center",
                    ha="center",
                    fontsize=9,
                    color="white",
                    fontweight="bold",
                )

    ax.margins(y=0.06)

    fig.tight_layout()
    return _fig_to_svg(fig)

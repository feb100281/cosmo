# sales/reports/sales_report/commulative_chart.py
from __future__ import annotations

import io
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from sales.reports.sales_report.formatters import (
    fmt_money_chart,
    fmt_delta_short_chart,
    fmt_pct,
)



def _df_prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    # безопасно приводим к числам
    for c in ("amount", "dt", "cr", "orders", "quant"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def _to_svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def build_mtd_waterfall_svg(
    df_mtd_raw: "pd.DataFrame",
    title: str = "MTD: разбор изменения выручки (заказы / чек)",
) -> str:
    """
    ✅ ВЕРСИЯ, КОТОРАЯ СХОДИТСЯ С ТАБЛИЦЕЙ MTD "ВЫРУЧКА" (amount)

    Почему так:
      - В таблице "Выручка" = amount.
      - DT и CR показаны отдельно (как справочные метрики).
      - Поэтому waterfall строим по amount, чтобы контроль сходился 1-в-1.

    Методика (для amount):
      Revenue = Orders * AveRevenue
      AveRevenue = Revenue / Orders

      Эффект заказов       = (Orders_curr - Orders_prev) * Ave_prev
      Эффект среднего чека = (Ave_curr - Ave_prev) * Orders_curr

    Контроль:
      Revenue_prev + эффекты ≈ Revenue_curr

    Возвраты:
      показываем под графиком как справку (ΔCR), но НЕ включаем в мостик,
      чтобы не смешивать показатель amount с NET=DT-CR.
    """
    import io
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, MaxNLocator

    # ---------------- helpers ----------------
    def _to_svg(fig) -> str:
        buf = io.StringIO()
        fig.savefig(buf, format="svg", bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()

    def _prepare(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        for c in ("amount", "orders", "dt", "cr"):
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        return df

    def _fmt_int(v: float) -> str:
        return f"{int(round(float(v))):,}".replace(",", " ")

    def _fmt_money(v: float) -> str:
        return f"{float(v):,.0f}".replace(",", " ")

    def _fmt_delta(v: float) -> str:
        sign = "+" if v > 0 else ""
        return f"{sign}{_fmt_money(v)}"

    def _fmt_money_short(v: float) -> str:
        v = float(v)
        av = abs(v)
        if av >= 1_000_000:
            return f"{v/1_000_000:,.1f} млн".replace(",", " ")
        if av >= 1_000:
            return f"{v/1_000:,.0f} тыс".replace(",", " ")
        return f"{v:,.0f}".replace(",", " ")

    def _wrap_text(s: str, width: int = 128) -> str:
        words = s.split()
        lines, line, ln = [], [], 0
        for w in words:
            add = len(w) + (1 if line else 0)
            if ln + add > width:
                lines.append(" ".join(line))
                line = [w]
                ln = len(w)
            else:
                line.append(w)
                ln += add
        if line:
            lines.append(" ".join(line))
        return "\n".join(lines)

    # ---------------- data ----------------
    df = _prepare(df_mtd_raw)
    if df.empty:
        return ""

    df["year"] = df["date"].dt.year
    years = sorted(df["year"].unique())[-2:]
    if len(years) < 2:
        return ""
    y_prev, y_curr = years[0], years[1]

    def _totals(y: int) -> dict:
        d = df[df["year"] == y]
        revenue = float(d["amount"].sum())
        orders = float(d["orders"].sum())
        ave = (revenue / orders) if orders else 0.0

        # справочно (для подписи под графиком, не для водопада)
        dt = float(d["dt"].sum()) if "dt" in d.columns else 0.0
        cr = float(d["cr"].sum()) if "cr" in d.columns else 0.0

        return {"revenue": revenue, "orders": orders, "ave": ave, "dt": dt, "cr": cr}

    p = _totals(y_prev)
    c = _totals(y_curr)

    # ---------------- effects (по amount) ----------------
    eff_orders = (c["orders"] - p["orders"]) * p["ave"]
    eff_ave = (c["ave"] - p["ave"]) * c["orders"]

    base = p["revenue"]
    final = c["revenue"]
    deltas = [eff_orders, eff_ave]

    bridge_rev = base + sum(deltas)
    residual = final - bridge_rev  # должен быть ~0 (округления)

    # справочно: Δвозвратов (не часть водопада)
    d_cr = c["cr"] - p["cr"]  # отриц. => возвраты снизились
    # Влияние на "чистый поток" условно: -(ΔCR)
    cr_uplift = -(d_cr)

    # ---------------- labels ----------------
    labels = [
        f"База\nMTD {y_prev}",
        "Эффект\nзаказов",
        "Эффект\nсреднего чека",
        f"MTD {y_curr}",
    ]
    x = np.arange(len(labels))

    # ---------------- style (под твои токены) ----------------
    col_base = "#002FA7"      # --brand
    col_final = "#4B3FB5"     # аккуратный комплиментарный
    col_pos = "#0b6b2f"       # --pos
    col_neg = "#b00000"       # --neg
    col_conn = "#9AA4B2"
    grid_col = "#E6E8EE"
    text_muted = "#6b7280"

    fig = plt.figure(figsize=(11.2, 4.2), dpi=150)
    ax = fig.add_subplot(111)
    ax.set_title(title, pad=12, fontsize=15, fontweight="bold")

    # сетка/оси
    ax.grid(True, axis="y", color=grid_col, linewidth=0.9, alpha=0.9)
    ax.grid(False, axis="x")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_alpha(0.35)
    ax.spines["bottom"].set_alpha(0.35)

    # ---------------- draw waterfall ----------------
    width = 0.72

    ax.bar(x[0], base, width=width, color=col_base)

    running = base
    running_points = [running]
    bar_meta = []  # (ix, bottom, height, dlt, color)

    # эффекты: могут быть +/-
    for i, dlt in enumerate(deltas, start=1):
        bottom = running if dlt >= 0 else running + dlt
        height = abs(dlt)
        color = col_pos if dlt >= 0 else col_neg
        ax.bar(x[i], height, bottom=bottom, width=width, color=color)
        bar_meta.append((i, bottom, height, dlt, color))
        running += dlt
        running_points.append(running)

    ax.bar(x[3], final, width=width, color=col_final)

    # connectors
    for i in range(0, 3):
        y = running_points[i]  # уровень после шага i
        x0 = x[i] + width / 2
        x1 = x[i + 1] - width / 2
        ax.plot([x0, x1], [y, y], color=col_conn, linewidth=2)

    # ---------------- axis formatting ----------------
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)

    levels = [base, base + deltas[0], base + sum(deltas), final]
    y_min = min(0, min(levels)) * 1.12
    y_max = max(levels) * 1.18 if max(levels) != 0 else 1
    ax.set_ylim(y_min, y_max)

    # ✅ Ось Y в млн ₽ (без 1e7)
    def _yfmt(v, _pos):
        return f"{v/1_000_000:,.0f}".replace(",", " ")
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.yaxis.set_major_formatter(FuncFormatter(_yfmt))
    ax.set_ylabel("млн руб.", fontsize=11, color=text_muted)

    # ---------------- value labels ----------------
    def _top_label(ix: int, val: float, color: str):
        ax.text(
            x[ix],
            val,
            _fmt_money_short(val),
            ha="center",
            va="bottom",
            fontsize=11,
            color=color,
            fontweight="bold",
        )

    _top_label(0, base, col_base)
    _top_label(3, final, col_final)

    # подписи эффектов: если маленький — строго сверху
    yrange = y_max - y_min
    small_thr = 0.06 * yrange  # 6% высоты области

    for (ix, bottom, height, dlt, color) in bar_meta:
        txt = _fmt_delta(dlt)
        if height < small_thr:
            ax.text(
                x[ix],
                bottom + height + 0.012 * yrange,
                txt,
                ha="center",
                va="bottom",
                fontsize=10.5,
                color=color,
                fontweight="bold",
            )
        else:
            ax.text(
                x[ix],
                bottom + height / 2,
                txt,
                ha="center",
                va="center",
                fontsize=11,
                color="white",
                fontweight="bold",
            )

    
    fig.tight_layout()
    return _to_svg(fig)



def build_ytd_cumulative_svg(
    df_ytd_raw: pd.DataFrame,
    title: str = "YTD: накопленная выручка (текущий год vs прошлый)",
) -> str:
    import numpy as np
    from matplotlib.ticker import FuncFormatter, MaxNLocator

    RU_MONTHS_SHORT = {
        1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
        7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
    }

    df = _df_prepare(df_ytd_raw)
    if df.empty:
        return ""

    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    years = sorted(df["year"].unique())[-2:]
    if len(years) < 2:
        return ""

    y_prev, y_curr = years[0], years[1]

    def _build_monthly_cum(y: int) -> pd.DataFrame:
        d = df[df["year"] == y].copy()
        if d.empty:
            return pd.DataFrame(columns=["month", "cum"])
        g = (
            d.groupby("month", as_index=False)["amount"]
            .sum()
            .sort_values("month")
        )
        g["cum"] = g["amount"].cumsum()
        return g[["month", "cum"]]

    prev = _build_monthly_cum(y_prev)
    curr = _build_monthly_cum(y_curr)
    if curr.empty or prev.empty:
        return ""

    last_m = int(curr["month"].max())
    prev = prev[prev["month"] <= last_m].copy()

    months = np.arange(1, last_m + 1)
    prev_map = dict(zip(prev["month"], prev["cum"]))
    curr_map = dict(zip(curr["month"], curr["cum"]))
    y_prev_vals = np.array([float(prev_map.get(m, np.nan)) for m in months], dtype=float)
    y_curr_vals = np.array([float(curr_map.get(m, np.nan)) for m in months], dtype=float)

    def _ffill(a: np.ndarray) -> np.ndarray:
        out = a.copy()
        last = np.nan
        for i in range(len(out)):
            if np.isnan(out[i]):
                out[i] = last
            else:
                last = out[i]
        return out

    y_prev_vals = _ffill(y_prev_vals)
    y_curr_vals = _ffill(y_curr_vals)

    # стиль
    col_curr = "#002FA7"
    col_prev = "#94A3B8"
    col_pos = "#0b6b2f"
    col_neg = "#b00000"
    grid_col = "#E6E8EE"
    text_muted = "#6b7280"

    fig = plt.figure(figsize=(11.2, 4.2), dpi=150)
    ax = fig.add_subplot(111)
    ax.set_title(title, pad=12, fontsize=15, fontweight="bold")

    ax.grid(True, axis="y", color=grid_col, linewidth=0.9, alpha=0.9)
    ax.grid(False, axis="x")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_alpha(0.35)
    ax.spines["bottom"].set_alpha(0.35)

    ax.plot(
        months, y_prev_vals,
        linestyle="--", linewidth=2.2, color=col_prev,
        marker="o", markersize=4.5, markerfacecolor="white",
        label=str(y_prev),
        zorder=2
    )
    ax.plot(
        months, y_curr_vals,
        linestyle="-", linewidth=3.0, color=col_curr,
        marker="o", markersize=5.2,
        label=str(y_curr),
        zorder=3
    )

    diff = y_curr_vals - y_prev_vals
    
    
    # ---------- аналитика динамики YTD ----------

    # вклад месяцев в разрыв
    month_deltas = diff.copy()

    # где максимум ухудшения
    worst_idx = int(np.nanargmin(month_deltas))
    best_idx = int(np.nanargmax(month_deltas))

    worst_month = months[worst_idx]
    best_month = months[best_idx]

    # тренд разрыва: растёт или сокращается
    if len(month_deltas) >= 2:
        trend_delta = month_deltas[-1] - month_deltas[0]
    else:
        trend_delta = 0

    if trend_delta < 0:
        trend_label = "разрыв увеличивается"
    elif trend_delta > 0:
        trend_label = "разрыв сокращается"
    else:
        trend_label = "разрыв стабилен"

    main_drop_month = RU_MONTHS_SHORT[worst_month]

    ax.fill_between(months, y_prev_vals, y_curr_vals, where=(diff >= 0),
                    interpolate=True, alpha=0.12, color=col_pos, zorder=1)
    ax.fill_between(months, y_prev_vals, y_curr_vals, where=(diff < 0),
                    interpolate=True, alpha=0.12, color=col_neg, zorder=1)

    ax.set_xticks(months)
    ax.set_xticklabels([RU_MONTHS_SHORT[m] for m in months], fontsize=11)

    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _pos: f"{v/1_000_000:,.0f}".replace(",", " ")))
    ax.set_ylabel("млн руб.", fontsize=11, color=text_muted)

    ax.legend(loc="upper left", frameon=False)

    last_x = months[-1]
    last_curr = float(y_curr_vals[-1])
    ax.scatter([last_x], [last_curr], s=55, color=col_curr, zorder=4)


    ax.annotate(
        fmt_money_chart(last_curr),
        (last_x, last_curr),
        textcoords="offset points",
        xytext=(10, -10),
        ha="left",
        fontsize=11,
        color=col_curr,
        fontweight="bold",
    )

    # ---------- SUMMARY (нормальная рамка + без дублирования) ----------
    last_prev = float(y_prev_vals[-1])
    d_abs = last_curr - last_prev
    d_pct = (d_abs / last_prev * 100) if last_prev else 0.0
    sign = "+" if d_abs > 0 else ""
    d_col = col_pos if d_abs >= 0 else col_neg

    line1 = f"YTD {y_curr}:  {fmt_money_chart(last_curr)}"
    line2 = f"YTD {y_prev}:  {fmt_money_chart(last_prev)}"
    line3 = f"Δ: {fmt_delta_short_chart(d_abs)}"
    line4 = f"Δ%: {fmt_pct(d_pct)}"


    # 1) Основной текст в рамке:
    #    Δ-строки заменяем пробелами той же длины => рамка по ширине будет как надо,
    #    но чёрных дельт не будет видно.
    spacer3 = " " * len(line3)
    spacer4 = " " * len(line4)

    boxed_text = f"{line1}\n{line2}\n{spacer3}\n{spacer4}"

    x, y = 0.985, 0.06
    ax.text(
        x, y,
        boxed_text,
        transform=ax.transAxes,
        ha="right", va="bottom",
        fontsize=11,
        color="#111827",
        bbox=dict(
            boxstyle="round,pad=0.45,rounding_size=0.12",
            facecolor="white",
            edgecolor=grid_col,
            linewidth=1.0,
            alpha=0.95,
        ),
        zorder=10,
    )

    # 2) Цветные дельты — строго поверх зарезервированных строк
    #    (те же x,y, но через \n\n сработает стабильно, потому что 4 строки уже есть)
    ax.text(
        x, y,
        f"\n\n{line3}\n{line4}",
        transform=ax.transAxes,
        ha="right", va="bottom",
        fontsize=11,
        color=d_col,
        fontweight="bold",
        zorder=11,
    )
    
    ytd_comment = (
    f"Основной вклад в отклонение формируется в {main_drop_month}. "
    f"По мере накопления {trend_label}."
)
    
    ax.text(
    0.01, -0.28,
    "Динамика YTD: " + ytd_comment,
    transform=ax.transAxes,
    ha="left",
    va="top",
    fontsize=11,
    color="#111827",
)


    # -------------------------------------------------------------------

    fig.tight_layout()
    return _to_svg(fig)

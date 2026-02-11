# sales/reports/sales_report/commulative_chart.py
from __future__ import annotations

import io
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


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


def build_ytd_cumulative_svg(
    df_ytd_raw: pd.DataFrame,
    title: str = "YTD: накопленная выручка (текущий год vs прошлый)",
) -> str:
    """
    df_ytd_raw: результат get_ytd_data(d)
    В нём два года, агрегировано по LAST_DAY(date).
    Рисуем кумулятив по месяцам: net_amount = amount (или можно заменить на dt-cr).
    """
    df = _df_prepare(df_ytd_raw)

    if df.empty:
        return ""

    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    # берем последние 2 года из набора (на случай, если отчёт когда-то будет шире)
    years = sorted(df["year"].unique())[-2:]
    if len(years) < 2:
        return ""

    y_prev, y_curr = years[0], years[1]

    def _series(y: int) -> pd.DataFrame:
        d = df[df["year"] == y].copy()
        d = d.sort_values("date")
        d["cum"] = d["amount"].cumsum()  # ключевой показатель для траектории
        return d[["date", "cum"]]

    prev = _series(y_prev)
    curr = _series(y_curr)

    fig = plt.figure(figsize=(10.8, 3.6))
    ax = fig.add_subplot(111)

    ax.plot(prev["date"], prev["cum"], marker="o", linewidth=2, label=str(y_prev))
    ax.plot(curr["date"], curr["cum"], marker="o", linewidth=2, label=str(y_curr))

    ax.set_title(title, pad=12)
    ax.grid(True, alpha=0.25)

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    for label in ax.get_xticklabels():
        label.set_rotation(0)

    ax.legend(loc="upper left", frameon=False)

    # подпишем последнее значение на линии текущего года
    if not curr.empty:
        last_x = curr["date"].iloc[-1]
        last_y = curr["cum"].iloc[-1]
        ax.annotate(
            f"{last_y:,.0f}".replace(",", " "),
            (last_x, last_y),
            textcoords="offset points",
            xytext=(8, -10),
        )

    return _to_svg(fig)


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
    ax.set_ylabel("млн ₽", fontsize=11, color=text_muted)

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

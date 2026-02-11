# sales/reports/sales_report/categories_chart.py
from __future__ import annotations

import io
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator


# ---------- helpers ----------
def _to_svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _prep_raw(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for c in ("amount", "quant"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")

    if "cat_name" in df.columns:
        df["cat_name"] = df["cat_name"].fillna("Без категории")
    if "sc_name" in df.columns:
        df["sc_name"] = df["sc_name"].fillna("Нет подкатегории")

    return df


_RU_MONTHS = {
    1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
    7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек"
}


def _fmt_ru_date(dt: pd.Timestamp) -> str:
    if pd.isna(dt):
        return ""
    dt = pd.to_datetime(dt)
    return f"{dt.day:02d} {_RU_MONTHS.get(dt.month, dt.month)} {dt.year}"


def _year_date_range_label(df: pd.DataFrame, year: int) -> str:
    """
    Возвращает строку: "01 Фев 2026 - 11 Фев 2026"
    Берёт min/max по df['date'] для указанного года.
    Если date нет/пусто — fallback на str(year).
    """
    if "date" not in df.columns:
        return str(year)

    d = df.loc[df["year"] == year, "date"]
    d = d.dropna()
    if d.empty:
        return str(year)

    d_min = d.min()
    d_max = d.max()
    return f"{_fmt_ru_date(d_min)} - {_fmt_ru_date(d_max)}"


def _mln_formatter(decimals: int = 1):
    def _f(v, _pos):
        # 1_234_567 -> "1.2" (в млн), пробелы как разделители тысяч
        fmt = f"{v/1_000_000:,.{decimals}f}".replace(",", " ")
        return fmt
    return FuncFormatter(_f)


# ---------- charts ----------
def build_mtd_categories_bar_svg(
    raw: pd.DataFrame,
    top_n: int = 12,
    title: str = "MTD: ТОП категорий (текущий год vs прошлый)",
) -> str:
    """
    Горизонтальный bar chart: по каждой категории 2 значения (prev/curr).
    Легенда: диапазоны дат (из raw).
    """
    df = _prep_raw(raw)
    if df is None or df.empty:
        return ""

    years = sorted(df["year"].dropna().unique())[-2:]
    if len(years) < 2:
        return ""

    y_prev, y_curr = int(years[0]), int(years[1])
    lab_prev = _year_date_range_label(df, y_prev)
    lab_curr = _year_date_range_label(df, y_curr)

    g = df.groupby(["cat_id", "cat_name", "year"], as_index=False)["amount"].sum()

    prev = (
        g[g["year"] == y_prev]
        .rename(columns={"amount": "amount_prev"})
        .drop(columns=["year"])
    )
    curr = (
        g[g["year"] == y_curr]
        .rename(columns={"amount": "amount_curr"})
        .drop(columns=["year"])
    )

    t = curr.merge(prev, on=["cat_id", "cat_name"], how="left")
    t["amount_prev"] = t["amount_prev"].fillna(0.0)

    # топ по текущему году
    t = t.sort_values("amount_curr", ascending=False).head(top_n)
    if t.empty:
        return ""

    # порядок сверху вниз
    t = t.iloc[::-1]

    cats = t["cat_name"].astype(str).tolist()
    prev_vals = t["amount_prev"].to_numpy(dtype=float)
    curr_vals = t["amount_curr"].to_numpy(dtype=float)

    # style
    col_curr = "#002FA7"
    col_prev = "#94A3B8"
    grid_col = "#E6E8EE"
    text_muted = "#6b7280"

    fig_h = max(4.2, 0.34 * len(cats) + 1.6)
    fig = plt.figure(figsize=(11.2, fig_h), dpi=150)
    ax = fig.add_subplot(111)
    ax.set_title(title, pad=12, fontsize=15, fontweight="bold")

    ax.grid(True, axis="x", color=grid_col, linewidth=0.9, alpha=0.9)
    ax.grid(False, axis="y")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_alpha(0.25)
    ax.spines["bottom"].set_alpha(0.25)

    y = np.arange(len(cats))
    h = 0.36

    ax.barh(y - h / 2, prev_vals, height=h, color=col_prev, label=lab_prev)
    ax.barh(y + h / 2, curr_vals, height=h, color=col_curr, label=lab_curr)

    ax.set_yticks(y)
    ax.set_yticklabels(cats, fontsize=11)

    ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.xaxis.set_major_formatter(_mln_formatter(decimals=1))
    ax.set_xlabel("млн руб.", fontsize=11, color=text_muted)

    ax.legend(loc="lower right", frameon=False)

    xmax = float(max(curr_vals.max(initial=0), prev_vals.max(initial=0)))
    ax.set_xlim(0, xmax * 1.18 if xmax else 1)

    # Δ рядом с текущим баром
    for i, (pv, cv) in enumerate(zip(prev_vals, curr_vals)):
        d = cv - pv
        sign = "+" if d > 0 else ""
        d_txt = f"{sign}{d/1_000_000:,.1f} млн".replace(",", " ")
        ax.text(
            cv + (xmax * 0.02 if xmax else 0.02),
            y[i] + h / 2,
            d_txt,
            va="center",
            ha="left",
            fontsize=10.5,
            color="#111827",
        )

    fig.tight_layout()
    return _to_svg(fig)


def build_ytd_categories_bar_svg(
    raw: pd.DataFrame,
    top_n: int = 12,
    title: str = "YTD: ТОП категорий (текущий год vs прошлый)",
) -> str:
    """
    TOP-N категорий по amount текущего года и сравнение с прошлым годом.
    ВАЖНО: теперь рисует Δ (дельты) как в MTD.
    Легенда: диапазоны дат (из raw).
    """
    df = _prep_raw(raw)
    if df is None or df.empty:
        return ""

    if "year" not in df.columns:
        if "date" in df.columns:
            df["year"] = pd.to_datetime(df["date"], errors="coerce").dt.year
        else:
            return ""

    years = sorted([y for y in df["year"].dropna().unique()])[-2:]
    if len(years) < 2:
        return ""

    y_prev, y_curr = int(years[0]), int(years[1])
    lab_prev = _year_date_range_label(df, y_prev)
    lab_curr = _year_date_range_label(df, y_curr)

    g = df.groupby(["cat_name", "year"], as_index=False)["amount"].sum()

    curr = (
        g[g["year"] == y_curr]
        .rename(columns={"amount": "amount_curr"})[["cat_name", "amount_curr"]]
    )
    prev = (
        g[g["year"] == y_prev]
        .rename(columns={"amount": "amount_prev"})[["cat_name", "amount_prev"]]
    )

    m = curr.merge(prev, on="cat_name", how="left")
    m["amount_prev"] = m["amount_prev"].fillna(0.0)

    # TOP-N по текущему году
    m = m.sort_values("amount_curr", ascending=False).head(top_n)
    if m.empty:
        return ""

    # порядок сверху вниз
    cats = m["cat_name"].tolist()[::-1]
    curr_vals = m["amount_curr"].to_numpy(dtype=float)[::-1]
    prev_vals = m["amount_prev"].to_numpy(dtype=float)[::-1]

    # style
    col_curr = "#002FA7"
    col_prev = "#94A3B8"
    grid_col = "#E6E8EE"
    text_muted = "#6b7280"

    fig_h = max(4.2, 0.34 * len(cats) + 1.6)
    fig = plt.figure(figsize=(11.2, fig_h), dpi=150)
    ax = fig.add_subplot(111)
    ax.set_title(title, pad=12, fontsize=15, fontweight="bold")

    ax.grid(True, axis="x", color=grid_col, linewidth=0.9, alpha=0.9)
    ax.grid(False, axis="y")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_alpha(0.35)
    ax.spines["bottom"].set_alpha(0.35)

    y = np.arange(len(cats))
    h = 0.36

    ax.barh(y - h / 2, prev_vals, height=h, color=col_prev, label=lab_prev)
    ax.barh(y + h / 2, curr_vals, height=h, color=col_curr, label=lab_curr)

    ax.set_yticks(y)
    ax.set_yticklabels(cats, fontsize=11)

    ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.xaxis.set_major_formatter(_mln_formatter(decimals=1))
    ax.set_xlabel("млн руб.", fontsize=11, color=text_muted)

    ax.legend(loc="lower right", frameon=False)

    xmax = float(max(curr_vals.max(initial=0), prev_vals.max(initial=0)))
    ax.set_xlim(0, xmax * 1.18 if xmax else 1)

    # Δ (дельты) — теперь добавлены
    for i, (pv, cv) in enumerate(zip(prev_vals, curr_vals)):
        d = cv - pv
        sign = "+" if d > 0 else ""
        d_txt = f"{sign}{d/1_000_000:,.1f} млн".replace(",", " ")
        ax.text(
            cv + (xmax * 0.02 if xmax else 0.02),
            y[i] + h / 2,
            d_txt,
            va="center",
            ha="left",
            fontsize=10.5,
            color="#111827",
        )

    fig.tight_layout()
    return _to_svg(fig)

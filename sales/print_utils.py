# sales/print_utils.py
import io
import base64
from datetime import date

import numpy as np
import pandas as pd

# ✅ backend без GUI, чтобы не было NSWindow / main thread на macOS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


RENAMING_COLS = {
    "amount": "Выручка",
    "quant": "Кол-во",
    "orders": "Заказы",
    "dt": "Продажи",
    "cr": "Возвраты",
}

# обратное переименование (на случай если df уже приходит с русскими колонками)
REVERSE_RENAMING_COLS = {v: k for k, v in RENAMING_COLS.items()}

ORDER_METRICS = ["Выручка", "Кол-во", "Заказы", "Ср. чек", "Продажи", "Возвраты", "К возвратов"]

# Колонки, которые обязаны быть числовыми (иначе groupby.sum может их "выкинуть")
NUM_COLS = ["amount", "quant", "orders", "dt", "cr"]


def _format_money(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


def _format_int(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


def _format_pct(v: float) -> str:
    return f"{v:,.1f}%"


def _ensure_raw_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Нормализуем входной df:
    - должен содержать: date, amount, quant, orders, dt, cr
    - если вместо них уже русские колонки — переведем обратно.
    """
    out = df.copy()

    # если нет amount, но есть "Выручка" — считаем, что df уже с русскими колонками
    if "amount" not in out.columns and "Выручка" in out.columns:
        cols_to_rename = {
            c: REVERSE_RENAMING_COLS[c]
            for c in out.columns
            if c in REVERSE_RENAMING_COLS
        }
        out = out.rename(columns=cols_to_rename)

    return out


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Приводим ключевые метрики к числовому типу.
    Это критично, потому что если они object/Decimal, то после sum(numeric_only=True)
    могут исчезнуть (и будет KeyError: 'amount').
    """
    out = df.copy()
    for c in NUM_COLS:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def _to_print_table(df_pivot: pd.DataFrame, title_left: str, title_right: str) -> dict:
    """
    df_pivot: index = Метрика
              columns = [title_left, title_right, Δ абс., Δ отн.]
    Возвращает dict {"html": "<table ...>...</table>"}

    ✅ Правило: если в предыдущем периоде нет значения (NaN или 0) — Δ = "—"
    """
    out = df_pivot.copy()
    out = out.astype("object")

    base_cols = [c for c in [title_left, title_right] if c in out.columns]

    def fmt_value(metric: str, v) -> str:
        if pd.isna(v):
            return "—"
        v = float(v)

        if metric in ("Выручка", "Продажи", "Возвраты", "Ср. чек"):
            return _format_money(v)

        if metric in ("Кол-во", "Заказы"):
            return _format_int(v)

        if metric == "К возвратов":
            return _format_pct(v)

        return str(v)

    # ✅ форматируем только колонки периодов (не Δ)
    for metric in out.index:
        for c in base_cols:
            out.loc[metric, c] = fmt_value(metric, df_pivot.loc[metric, c])

    abs_cls: dict[str, str] = {}
    pct_cls: dict[str, str] = {}

    def _prev_missing(prev_val) -> bool:
        return pd.isna(prev_val) or float(prev_val) == 0.0

    def fmt_delta_abs(metric: str, v) -> str:
        if pd.isna(v):
            return "—"
        v = float(v)
        sign = "+" if v > 0 else "−" if v < 0 else ""
        vv = abs(v)

        if metric in ("Выручка", "Продажи", "Возвраты", "Ср. чек"):
            return f"{sign}{_format_money(vv)}"
        if metric in ("Кол-во", "Заказы"):
            return f"{sign}{_format_int(vv)}"
        if metric == "К возвратов":
            return f"{sign}{_format_pct(vv)}"
        return f"{sign}{vv}"

    def fmt_delta_pct(v) -> str:
        if pd.isna(v):
            return "—"
        v = float(v)
        sign = "+" if v > 0 else "−" if v < 0 else ""
        return f"{sign}{_format_pct(abs(v))}"

    # ✅ Δ отдельно + классы, с правилом "если нет прошлого периода -> —"
    if "Δ абс." in out.columns or "Δ отн." in out.columns:
        for metric in out.index:
            prev_val = df_pivot.loc[metric, title_left] if title_left in df_pivot.columns else np.nan

            # ❗ если прошлого нет — Δ не считаем
            if _prev_missing(prev_val):
                if "Δ абс." in out.columns:
                    out.loc[metric, "Δ абс."] = "—"
                    abs_cls[metric] = ""
                if "Δ отн." in out.columns:
                    out.loc[metric, "Δ отн."] = "—"
                    pct_cls[metric] = ""
                continue

            if "Δ абс." in out.columns:
                vabs = df_pivot.loc[metric, "Δ абс."]
                out.loc[metric, "Δ абс."] = fmt_delta_abs(metric, vabs)
                abs_cls[metric] = (
                    "pos" if (not pd.isna(vabs) and float(vabs) > 0) else
                    "neg" if (not pd.isna(vabs) and float(vabs) < 0) else
                    ""
                )

            if "Δ отн." in out.columns:
                vpct = df_pivot.loc[metric, "Δ отн."]
                out.loc[metric, "Δ отн."] = fmt_delta_pct(vpct)
                pct_cls[metric] = (
                    "pos" if (not pd.isna(vpct) and float(vpct) > 0) else
                    "neg" if (not pd.isna(vpct) and float(vpct) < 0) else
                    ""
                )

    # ✅ рендер HTML вручную
    cols = [c for c in [title_left, title_right, "Δ абс.", "Δ отн."] if c in out.columns]

    rows_html = []
    for metric in out.index:
        tds = [f"<td class='metric'>{metric}</td>"]
        for c in cols:
            if c == "Δ абс.":
                cls = abs_cls.get(metric, "")
                tds.append(f"<td class='num {cls}'>{out.loc[metric, c]}</td>")
            elif c == "Δ отн.":
                cls = pct_cls.get(metric, "")
                tds.append(f"<td class='num {cls}'>{out.loc[metric, c]}</td>")
            else:
                tds.append(f"<td class='num'>{out.loc[metric, c]}</td>")
        rows_html.append("<tr>" + "".join(tds) + "</tr>")

    thead = (
        "<thead><tr>"
        "<th>Метрика</th>"
        + "".join(f"<th>{c}</th>" for c in cols)
        + "</tr></thead>"
    )

    html = "<table class='tbl'>" + thead + "<tbody>" + "".join(rows_html) + "</tbody></table>"
    return {"html": html}


def build_mtd_table(df_raw: pd.DataFrame) -> dict:
    df = _ensure_raw_columns(df_raw)

    required = {"date", "amount", "quant", "orders", "dt", "cr"}
    if not required.issubset(set(df.columns)):
        missing = sorted(list(required - set(df.columns)))
        return {"html": f"<div class='note'>Нет колонок для отчёта: {', '.join(missing)}</div>"}

    df = df.copy()

    # ✅ приводим типы, иначе groupby.sum может потерять amount/dt/cr и будет KeyError
    df = _coerce_numeric(df)

    df["month"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("MTD %b %y").str.upper()

    # Оставляем только валидные строки с периодом
    df = df.dropna(subset=["month"])

    # ✅ суммируем без numeric_only (после coercion колонки уже числовые)
    df = df.drop(columns=["date"]).groupby("month", as_index=False)[NUM_COLS].sum()

    # Защита от пустого df
    if df.empty:
        return {"html": "<div class='note'>Нет данных за период MTD</div>"}

    df["Ср. чек"] = (df["amount"] / df["orders"].replace(0, pd.NA)).fillna(0)
    df["К возвратов"] = (df["cr"] / df["dt"].replace(0, pd.NA) * 100).fillna(0)

    df = df.rename(columns=RENAMING_COLS)

    df_long = df.melt(
        id_vars="month",
        value_vars=ORDER_METRICS,
        var_name="Метрика",
        value_name="value",
    )
    pivot = df_long.pivot_table(index="Метрика", columns="month", values="value", aggfunc="first")

    if pivot.shape[1] < 2:
        return {"html": "<div class='note'>Недостаточно данных для сравнения (нужно 2 периода)</div>"}

    c0, c1 = pivot.columns[:2]
    pivot["Δ абс."] = pivot[c1] - pivot[c0]
    pivot["Δ отн."] = pivot["Δ абс."] / pivot[c0].replace(0, pd.NA) * 100

    if "К возвратов" in pivot.index:
        pivot.loc["К возвратов", ["Δ абс.", "Δ отн."]] *= -1

    pivot = pivot.reindex(ORDER_METRICS)
    return _to_print_table(pivot, c0, c1)


def build_ytd_table(df_raw: pd.DataFrame) -> dict:
    df = _ensure_raw_columns(df_raw)

    required = {"date", "amount", "quant", "orders", "dt", "cr"}
    if not required.issubset(set(df.columns)):
        missing = sorted(list(required - set(df.columns)))
        return {"html": f"<div class='note'>Нет колонок для отчёта: {', '.join(missing)}</div>"}

    df = df.copy()

    # ✅ приводим типы, иначе groupby.sum может потерять amount/dt/cr и будет KeyError
    df = _coerce_numeric(df)

    df["period"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("YTD %Y").str.upper()
    df = df.dropna(subset=["period"])

    df = df.drop(columns=["date"]).groupby("period", as_index=False)[NUM_COLS].sum()

    if df.empty:
        return {"html": "<div class='note'>Нет данных за период YTD</div>"}

    df["Ср. чек"] = (df["amount"] / df["orders"].replace(0, pd.NA)).fillna(0)
    df["К возвратов"] = (df["cr"] / df["dt"].replace(0, pd.NA) * 100).fillna(0)

    df = df.rename(columns=RENAMING_COLS)

    df_long = df.melt(
        id_vars="period",
        value_vars=ORDER_METRICS,
        var_name="Метрика",
        value_name="value",
    )
    pivot = df_long.pivot_table(index="Метрика", columns="period", values="value", aggfunc="first")

    if pivot.shape[1] < 2:
        return {"html": "<div class='note'>Недостаточно данных для сравнения (нужно 2 периода)</div>"}

    c0, c1 = pivot.columns[:2]
    pivot["Δ абс."] = pivot[c1] - pivot[c0]
    pivot["Δ отн."] = pivot["Δ абс."] / pivot[c0].replace(0, pd.NA) * 100

    if "К возвратов" in pivot.index:
        pivot.loc["К возвратов", ["Δ абс.", "Δ отн."]] *= -1

    pivot = pivot.reindex(ORDER_METRICS)
    return _to_print_table(pivot, c0, c1)


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")







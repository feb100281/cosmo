# sales/reports/sales_report/ltm_insights.py
from __future__ import annotations

from datetime import date
import numpy as np
import pandas as pd

from .formatters import fmt_money, fmt_pct, fmt_delta_money, fmt_delta_pct


def _safe_pct(curr: float, base: float) -> float | None:
    if base in (None, 0) or np.isnan(base):
        return None
    return (curr - base) / base * 100


def build_ltm_insights(df_13m_raw: pd.DataFrame, report_date: date) -> dict:
    """
    Делает owner-инсайты для блока II.3:
    - текущий месяц (последний столбец), 3M MA, отклонение к MA
    - YoY (последний месяц vs -12)
    - min/max/avg за окно
    - статус (green/yellow/red)
    - простой прогноз на 2 месяца (линейный по 6 последним точкам)
    """
    if df_13m_raw is None or df_13m_raw.empty:
        return {}

    df = df_13m_raw.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    # месячная агрегация (MS)
    m = df.set_index("date")["amount"].resample("MS").sum().reset_index()
    if m.empty:
        return {}

    end_ms = pd.Timestamp(report_date).replace(day=1)
    start_ms = (end_ms - pd.DateOffset(months=12)).replace(day=1)
    m = m[(m["date"] >= start_ms) & (m["date"] <= end_ms)].sort_values("date").copy()

    vals = m["amount"].to_numpy(dtype=float)
    n = len(vals)
    if n < 2:
        return {}

    curr = float(vals[-1])
    ma3 = float(pd.Series(vals).rolling(3, min_periods=1).mean().iloc[-1])
    d_ma_abs = curr - ma3
    d_ma_pct = _safe_pct(curr, ma3)

    yoy_abs = None
    yoy_pct = None
    if n >= 13:
        base = float(vals[-13])
        yoy_abs = curr - base
        yoy_pct = _safe_pct(curr, base)

    avg = float(np.mean(vals))
    vmin = float(np.min(vals))
    vmax = float(np.max(vals))

    # статус: по отклонению от MA (управленчески понятно)
    # <= -10%: red, [-10%; +5%): yellow, >= +5%: green
    status = "na"
    if d_ma_pct is not None:
        if d_ma_pct <= -10:
            status = "red"
        elif d_ma_pct < 5:
            status = "yellow"
        else:
            status = "green"

    # простой прогноз на 2 месяца: линейный тренд по последним 6 точкам
    # (без фанатизма, но собственнику уже полезно)
    k = min(6, n)
    y = vals[-k:]
    x = np.arange(k, dtype=float)
    # y = a*x + b
    a, b = np.polyfit(x, y, 1)
    f1 = float(a * (k) + b)
    f2 = float(a * (k + 1) + b)
    # не даём уйти ниже 0
    f1 = max(0.0, f1)
    f2 = max(0.0, f2)

    return {
        "curr": {
            "value": fmt_money(curr),
            "ma3": fmt_money(ma3),
            "d_ma_abs": fmt_delta_money(d_ma_abs),
            "d_ma_pct": fmt_delta_pct(d_ma_pct),
        },
        "yoy": {
            "abs": fmt_delta_money(yoy_abs) if yoy_abs is not None else "—",
            "pct": fmt_delta_pct(yoy_pct) if yoy_pct is not None else "—",
            "has": yoy_abs is not None and yoy_pct is not None,
        },
        "stats": {
            "avg": fmt_money(avg),
            "min": fmt_money(vmin),
            "max": fmt_money(vmax),
        },
        "status": status,  # red/yellow/green/na
        "forecast": {
            "m1": fmt_money(f1),
            "m2": fmt_money(f2),
            "note": "Линейная экстраполяция тренда по 6 последним месяцам (ориентир).",
        },
    }

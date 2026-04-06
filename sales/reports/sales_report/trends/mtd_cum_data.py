# sales/reports/sales_report/trends/mtd_cum_data.py
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

import pandas as pd

from ..formatters import fmt_money


def build_mtd_cum_series(df_mtd_raw, report_date: date) -> Dict[str, Any]:
    """
    Строит MTD накопление по дням из df_mtd_raw (get_month_data),
    без вызовов build_kpi_for_range.

    df_mtd_raw ожидается с колонками:
      - date (дата)
      - amount (чистая выручка)
    + опционально dt/cr/orders (не нужны для графика)
    """
    if df_mtd_raw is None or len(df_mtd_raw) == 0:
        return {
            "series_cur": [],
            "series_ly": [],
            "cum_cur_raw": 0.0,
            "cum_ly_raw": 0.0,
            "cum_cur": fmt_money(0),
            "cum_ly": fmt_money(0),
        }

    df = df_mtd_raw.copy()
    # date -> date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.date

    # ограничиваем до даты отчёта (на всякий случай)
    df = df[df["date"] <= report_date]
    if df.empty:
        return {
            "series_cur": [],
            "series_ly": [],
            "cum_cur_raw": 0.0,
            "cum_ly_raw": 0.0,
            "cum_cur": fmt_money(0),
            "cum_ly": fmt_money(0),
        }

    # amount -> numeric
    df["amount"] = pd.to_numeric(df.get("amount"), errors="coerce").fillna(0.0)

    # год и день месяца
    dts = pd.to_datetime(df["date"])
    df["year"] = dts.dt.year
    df["dom"] = dts.dt.day  # day-of-month

    years = sorted(df["year"].unique())
    if len(years) < 2:
        # если вдруг в df нет прошлого года
        y_curr = years[-1]
        cur = df[df["year"] == y_curr].sort_values("date")
        cur["cum_raw"] = cur["amount"].cumsum()

        series_cur = [{
            "date": r.date,
            "label": f"{int(r.dom):02d}.{report_date.month:02d}",
            "amount_raw": float(r.amount),
            "cum_raw": float(r.cum_raw),
            "cum": fmt_money(float(r.cum_raw)),
        } for r in cur.itertuples()]

        return {
            "series_cur": series_cur,
            "series_ly": [],
            "cum_cur_raw": series_cur[-1]["cum_raw"] if series_cur else 0.0,
            "cum_ly_raw": 0.0,
            "cum_cur": series_cur[-1]["cum"] if series_cur else fmt_money(0),
            "cum_ly": fmt_money(0),
        }

    y_prev, y_curr = years[-2], years[-1]
    dom_max = report_date.day

    def _make(y: int) -> List[Dict[str, Any]]:
        d = df[df["year"] == y].copy()
        d = d[d["dom"] <= dom_max].sort_values("date")
        d["cum_raw"] = d["amount"].cumsum()

        return [{
            "date": r.date,
            "label": f"{int(r.dom):02d}.{report_date.month:02d}",
            "amount_raw": float(r.amount),
            "cum_raw": float(r.cum_raw),
            "cum": fmt_money(float(r.cum_raw)),
        } for r in d.itertuples()]

    series_cur = _make(y_curr)
    series_ly = _make(y_prev)

    return {
        "start_cur": report_date.replace(day=1),
        "end_cur": report_date,
        "start_ly": date(report_date.year - 1, report_date.month, 1),
        "end_ly": date(report_date.year - 1, report_date.month, dom_max),

        "series_cur": series_cur,
        "series_ly": series_ly,

        "cum_cur_raw": series_cur[-1]["cum_raw"] if series_cur else 0.0,
        "cum_ly_raw": series_ly[-1]["cum_raw"] if series_ly else 0.0,
        "cum_cur": series_cur[-1]["cum"] if series_cur else fmt_money(0),
        "cum_ly": series_ly[-1]["cum"] if series_ly else fmt_money(0),
    }
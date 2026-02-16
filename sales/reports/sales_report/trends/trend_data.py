from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from ..kpi.kpi_data import build_kpi_for_range
from ..formatters import fmt_money, fmt_int
from .trend_ranges import trend_ranges


def _calc_amount_bars(trend: List[dict]) -> None:
    vals = [t.get("amount_raw") or 0 for t in trend]
    vmax = max(vals) if vals else 0
    vmax = vmax or 1
    for t in trend:
        v = t.get("amount_raw") or 0
        t["amount_pct"] = round((v / vmax) * 100, 1)


def build_trend_series(
    report_type: str,
    report_date: date,
    points: int = 12,
) -> List[Dict[str, Any]]:
    trend: List[Dict[str, Any]] = []

    for s, e, label, is_current in trend_ranges(report_type, report_date, points=points):
        k = build_kpi_for_range(s, e)
        trend.append({
            "label": label,
            "start": s,
            "end": e,
            "is_current": is_current,

            "amount_raw": float(k.get("amount") or 0),
            "dt_raw": float(k.get("dt") or 0),
            "cr_raw": float(k.get("cr") or 0),

            "amount": fmt_money(k.get("amount")),
            "dt": fmt_money(k.get("dt")),
            "cr": fmt_money(k.get("cr")),
            "orders": fmt_int(k.get("orders")),
        })

    _calc_amount_bars(trend)
    return trend

from __future__ import annotations

from datetime import date
from typing import Any, Dict

from .trend_data import build_trend_series
from .trend_meta import trend_meta
from .trend_chart import build_trend_chart_svg


def build_trends_context(
    report_type: str,
    report_date: date,
    points: int = 12,
) -> Dict[str, Any]:
    trend = build_trend_series(report_type, report_date, points=points)

    return {
        "trend": trend,
        "trend_meta": trend_meta(report_type, report_date, points=points),
        "trend_chart_svg": build_trend_chart_svg(trend, metric="amount_raw"),
    }

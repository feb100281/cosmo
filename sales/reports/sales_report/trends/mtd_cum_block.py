# sales/reports/sales_report/trends/mtd_cum_block.py
from __future__ import annotations

from datetime import date
from typing import Any, Dict

from .mtd_cum_data import build_mtd_cum_series
from .mtd_cum_chart import build_mtd_cum_chart_svg


def build_mtd_cum_context(report_date: date) -> Dict[str, Any]:
    ctx = build_mtd_cum_series(report_date)
    ctx["mtd_cum_chart_svg"] = build_mtd_cum_chart_svg(ctx)
    return ctx
# sales/reports/sales_report/compare.py
from __future__ import annotations

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from .kpi import build_kpi_for_range
from .formatters import pct_change, fmt_pp, fmt_money, fmt_int, fmt_pct


def _prev_range(report_type: str, start: date, end: date) -> tuple[date, date, str]:
    if report_type == "daily":
        return start - timedelta(days=7), end - timedelta(days=7), "аналогичный день прошлой недели"
    if report_type == "weekly":
        return start - timedelta(days=7), end - timedelta(days=7), "предыдущая неделя"
    # monthly
    return start - relativedelta(months=1), end - relativedelta(months=1), "предыдущий месяц"


def _ly_range(start: date, end: date) -> tuple[date, date, str]:
    return start - relativedelta(years=1), end - relativedelta(years=1), "прошлый год"


def _fmt_value(metric: str, v):
    if metric in ("dt", "cr", "amount", "ave_check"):
        return fmt_money(v)
    if metric in ("orders", "quant"):
        return fmt_int(v)
    if metric in ("rtr_ratio",):
        return fmt_pct(v)
    return fmt_money(v)

def _fmt_delta_abs(metric: str, v):
    """
    Формат абсолютной дельты для графика:
    - money-метрики → fmt_money
    - count-метрики → fmt_int
    """
    if v is None:
        return "—"
    if metric in ("orders", "quant"):
        return fmt_int(v)
    # amount/dt/cr/ave_check
    return fmt_money(v)


def _block(metric: str, curr: dict, base: dict) -> dict:
    curr_v = curr.get(metric)
    base_v = base.get(metric)

    delta = None
    try:
        if curr_v is not None and base_v is not None:
            delta = float(curr_v) - float(base_v)
    except Exception:
        delta = None

    dpct = pct_change(curr_v, base_v)

    return {
        "base": _fmt_value(metric, base_v),
        "curr": _fmt_value(metric, curr_v),
        "delta": _fmt_value(metric, delta) if delta is not None else "—",
        "delta_pct": fmt_pp(dpct),
    }


def build_compare(report_type: str, period_start: date, period_end: date) -> dict:
    """
    compare.rows — список строк:
    row.prev / row.ly — блоки Было/Стало/Δ/Δ%
    """
    curr = build_kpi_for_range(period_start, period_end)

    prev_start, prev_end, prev_label = _prev_range(report_type, period_start, period_end)
    ly_start, ly_end, ly_label = _ly_range(period_start, period_end)

    prev = build_kpi_for_range(prev_start, prev_end)
    ly = build_kpi_for_range(ly_start, ly_end)

    def _has(k: dict) -> bool:
        return any((k.get("amount"), k.get("dt"), k.get("orders"), k.get("cr")))

    metrics = [
        ("amount", "Выручка"),
        ("dt", "Оборот"),
        ("orders", "Заказы"),
        ("cr", "Возвраты"),
    ]

    rows = []
    for key, title in metrics:
        rows.append({
            "key": key,
            "title": title,
            "prev": _block(key, curr, prev),
            "ly": _block(key, curr, ly),
        })
    
    chart = []
    for key, title in metrics:
        curr_v = curr.get(key)
        prev_v = prev.get(key)
        ly_v = ly.get(key)
        
        # абсолютные дельты
        prev_abs = None
        ly_abs = None
        try:
            if curr_v is not None and prev_v is not None:
                prev_abs = float(curr_v) - float(prev_v)
        except Exception:
            prev_abs = None

        try:
            if curr_v is not None and ly_v is not None:
                ly_abs = float(curr_v) - float(ly_v)
        except Exception:
            ly_abs = None

        chart.append({
            "key": key,
            "title": title,
            # проценты
            "prev_pct": pct_change(curr_v, prev_v),  # float or None
            "ly_pct": pct_change(curr_v, ly_v),      # float or None
            
            # абсолюты (RAW) — НУЖНО для abs-графика
            "prev_abs_raw": prev_abs,  # float|None
            "ly_abs_raw": ly_abs,      # float|None
            
            # абсолюты (строки) — НУЖНО для подписей
            "prev_abs": _fmt_delta_abs(key, prev_abs) if prev_abs is not None else "—",
            "ly_abs": _fmt_delta_abs(key, ly_abs) if ly_abs is not None else "—",
            
            # инверсия метрики (для возвратов меньше = лучше)
            "invert": (key == "cr"),
        })


    return {
        "curr": {"start": period_start, "end": period_end},
        "prev": {"start": prev_start, "end": prev_end, "label": prev_label, "has": _has(prev)},
        "ly": {"start": ly_start, "end": ly_end, "label": ly_label, "has": _has(ly)},
        "rows": rows,
        "chart": chart, 
    }

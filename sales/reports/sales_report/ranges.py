# sales/reports/sales_report/ranges.py
from datetime import date, timedelta
import calendar
from dateutil.relativedelta import relativedelta

def period_range(d: date, report_type: str) -> tuple[date, date]:
    """
    Возвращает (start, end) ВКЛЮЧИТЕЛЬНО.

    daily: d..d
    weekly: понедельник..воскресенье (d = воскресенье)
    monthly: 1-е число..последний день месяца (d = последний день)
    """
    if report_type == "daily":
        return d, d

    if report_type == "weekly":
        start = d - timedelta(days=6)
        end = d
        return start, end

    # monthly
    start = d.replace(day=1)
    last_day = calendar.monthrange(d.year, d.month)[1]
    end = d.replace(day=last_day)
    return start, end


def prev_period_range(period_start: date, period_end: date, report_type: str):

    # ✅ ДНЕВНОЙ ОТЧЁТ — аналогичный день прошлой недели
    if report_type == "daily":
        shift = timedelta(days=7)
        return period_start - shift, period_end - shift

    # ✅ НЕДЕЛЬНЫЙ — предыдущая неделя
    if report_type == "weekly":
        shift = timedelta(days=7)
        return period_start - shift, period_end - shift

    # ✅ МЕСЯЧНЫЙ — предыдущий календарный месяц
    prev_end = period_start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    return prev_start, prev_end



def last_13m_range(d: date) -> tuple[date, date]:
    start = d.replace(day=1) - relativedelta(months=12)
    end = d
    return start, end


from __future__ import annotations

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar

RU_MONTHS = {
    1: "ЯНВАРЬ", 2: "ФЕВРАЛЬ", 3: "МАРТ", 4: "АПРЕЛЬ",
    5: "МАЙ", 6: "ИЮНЬ", 7: "ИЮЛЬ", 8: "АВГУСТ",
    9: "СЕНТЯБРЬ", 10: "ОКТЯБРЬ", 11: "НОЯБРЬ", 12: "ДЕКАБРЬ",
}


def _last_day_of_month(d: date) -> int:
    return calendar.monthrange(d.year, d.month)[1]


def _month_label(d: date) -> str:
    return f"{RU_MONTHS[d.month]} {d.year}"


def trend_ranges(report_type: str, d: date, points: int = 12):
    """
    Возвращает список (start, end, label, is_current) от старых к новым.

    daily: последние N аналогичных дней недели (шаг 7 дней) + текущий день
    weekly: последние N недель + текущая неделя (d = конец недели)
    monthly: последние N месяцев + текущий месяц (d = конец месяца)
    """
    out = []

    if report_type == "daily":
        for i in range(points, 0, -1):
            x = d - timedelta(days=7 * i)
            out.append((x, x, x.strftime("%d.%m.%Y"), False))
        out.append((d, d, f"сегодня ({d:%d.%m.%Y})", True))
        return out

    if report_type == "weekly":
        for i in range(points, 0, -1):
            end = d - timedelta(days=7 * i)
            start = end - timedelta(days=6)
            label = f"{start:%d.%m.%Y} – {end:%d.%m.%Y}"
            out.append((start, end, label, False))

        start0 = d - timedelta(days=6)
        label0 = f"{start0:%d.%m.%Y} – {d:%d.%m.%Y}"
        out.append((start0, d, label0, True))
        return out

    # monthly
    for i in range(points, 0, -1):
        end = d - relativedelta(months=i)
        end = end.replace(day=_last_day_of_month(end))
        start = end.replace(day=1)
        out.append((start, end, _month_label(end), False))

    end0 = d.replace(day=_last_day_of_month(d))
    start0 = end0.replace(day=1)
    out.append((start0, end0, _month_label(end0), True))
    return out

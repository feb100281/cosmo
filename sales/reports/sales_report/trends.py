# sales/reports/sales_report/trends.py
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar

RU_MONTHS = {
    1: "ЯНВАРЬ", 2: "ФЕВРАЛЬ", 3: "МАРТ", 4: "АПРЕЛЬ",
    5: "МАЙ", 6: "ИЮНЬ", 7: "ИЮЛЬ", 8: "АВГУСТ",
    9: "СЕНТЯБРЬ", 10: "ОКТЯБРЬ", 11: "НОЯБРЬ", 12: "ДЕКАБРЬ",
}

RU_WEEKDAYS = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}


def _last_day_of_month(d: date) -> int:
    return calendar.monthrange(d.year, d.month)[1]


def _month_label(d: date) -> str:
    # "ЯНВАРЬ 2025"
    return f"{RU_MONTHS[d.month]} {d.year}"


def apply_bars(rows: list[dict], field_raw: str, out_field: str = "pct") -> list[dict]:
    """
    Добавляет в каждую строку rows[out_field] значение 0..100
    по min/max среди rows[field_raw].

    Ожидается, что rows — список dict, например:
    {"label": "...", "amount_raw": 123, "amount": "123 ₽", ...}
    """
    vals = [r.get(field_raw) for r in rows if r.get(field_raw) is not None]
    if not vals:
        for r in rows:
            r[out_field] = 0
        return rows

    vmin, vmax = min(vals), max(vals)
    span = (vmax - vmin) or 1

    for r in rows:
        v = r.get(field_raw)
        r[out_field] = round(((v - vmin) / span) * 100, 1) if v is not None else 0

    return rows



def trend_meta(report_type: str, d: date, points: int = 12) -> dict:
    """
    Метаданные для заголовка блока тренда (чтобы один раз показать день недели и т.п.)
    """
    if report_type == "daily":
        wd = RU_WEEKDAYS[d.weekday()]
        return {
            "title": f"Динамика за {points} аналогичных дней ({wd})",
            "subtitle": "Сравнение идёт по одинаковому дню недели (шаг 7 дней).",
        }

    if report_type == "weekly":
        return {
            "title": f"Динамика за {points} последних недель",
            "subtitle": "Каждая строка — неделя (Пн–Вс).",
        }

    return {
        "title": f"Динамика за {points} последних месяцев",
        "subtitle": "Каждая строка — календарный месяц.",
    }


def trend_ranges(report_type: str, d: date, points: int = 12):
    """
    Возвращает список (start, end, label, is_current) от старых к новым.

    daily: последние N аналогичных дней недели (шаг 7 дней) + текущий день
    weekly: последние N недель + текущая неделя (d = конец недели)
    monthly: последние N месяцев + текущий месяц (d = конец месяца)
    """
    out = []

    # -------- daily (аналогичный день недели) --------
    if report_type == "daily":
        for i in range(points, 0, -1):
            x = d - timedelta(days=7 * i)
            out.append((x, x, x.strftime("%d.%m.%Y"), False))

        out.append((d, d, f"сегодня ({d:%d.%m.%Y})", True))
        return out

    # -------- weekly (Пн–Вс) --------
    if report_type == "weekly":
        # d — конец недели (воскресенье), период = d-6..d
        for i in range(points, 0, -1):
            end = d - timedelta(days=7 * i)
            start = end - timedelta(days=6)
            label = f"{start:%d.%m.%Y} – {end:%d.%m.%Y}"
            out.append((start, end, label, False))

        start0 = d - timedelta(days=6)
        label0 = f"{start0:%d.%m.%Y} – {d:%d.%m.%Y}"
        out.append((start0, d, label0, True))
        return out

    # -------- monthly (календарный месяц) --------
    # d — конец месяца, период = 1..lastday
    for i in range(points, 0, -1):
        end = d - relativedelta(months=i)
        end = end.replace(day=_last_day_of_month(end))
        start = end.replace(day=1)
        out.append((start, end, _month_label(end), False))

    end0 = d.replace(day=_last_day_of_month(d))
    start0 = end0.replace(day=1)
    out.append((start0, end0, _month_label(end0), True))
    return out



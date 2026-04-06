from __future__ import annotations

from datetime import date

RU_WEEKDAYS = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}


def trend_meta(report_type: str, d: date, points: int = 12) -> dict:
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

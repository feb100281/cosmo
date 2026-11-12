# sales/reports/meeting_brief/periods.py
"""Отчётный период и периоды сравнения."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
              "августа", "сентября", "октября", "ноября", "декабря"]


MONTHS_NOM = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
              "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
MONTHS_PREP = ["январе", "феврале", "марте", "апреле", "мае", "июне", "июле",
               "августе", "сентябре", "октябре", "ноябре", "декабре"]


def fmt_day(d: date, year: bool = True) -> str:
    return f"{d.day} {MONTHS_GEN[d.month - 1]}" + (f" {d.year}" if year else "")


def fmt_range(d1: date, d2: date) -> str:
    if d1 == d2:
        return fmt_day(d1)
    if d1.year == d2.year and d1.month == d2.month:
        return f"{d1.day}–{d2.day} {MONTHS_GEN[d1.month - 1]} {d1.year}"
    if d1.year == d2.year:
        return f"{fmt_day(d1, False)} – {fmt_day(d2)}"
    return f"{fmt_day(d1)} – {fmt_day(d2)}"


@dataclass(frozen=True)
class Periods:
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def prev_end(self) -> date:
        return self.start - timedelta(days=1)

    @property
    def prev_start(self) -> date:
        # Целый месяц сравниваем с целым прошлым месяцем
        if self.is_full_month:
            return self.start - relativedelta(months=1)
        return self.start - timedelta(days=self.days)

    @property
    def ly_start(self) -> date:
        return self.start - relativedelta(years=1)

    @property
    def ly_end(self) -> date:
        return self.end - relativedelta(years=1)

    @property
    def month_start(self) -> date:
        return self.end.replace(day=1)

    @property
    def is_full_month(self) -> bool:
        return self.start.day == 1 and (self.end + timedelta(days=1)).day == 1 and \
            self.start.replace(day=1) == self.end.replace(day=1)

    @property
    def kind(self) -> str:
        if self.days == 7 and self.start.weekday() == 0:
            return "неделя"
        if self.is_full_month:
            return "месяц"
        return "период"

    @property
    def month_label(self) -> str:
        return f"{MONTHS_NOM[self.end.month - 1].capitalize()} {self.end.year}"

    @property
    def month_gen(self) -> str:
        return MONTHS_GEN[self.end.month - 1]

    @property
    def prev_label(self) -> str:
        return {"неделя": "к прошлой неделе", "месяц": "к прошлому месяцу"}.get(self.kind, "к прошлому периоду")

    @property
    def label(self) -> str:
        return fmt_range(self.start, self.end)

    @property
    def prev_range_label(self) -> str:
        return fmt_range(self.prev_start, self.prev_end)

    @property
    def ly_range_label(self) -> str:
        return fmt_range(self.ly_start, self.ly_end)


def last_full_week(today: date | None = None) -> Periods:
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    return Periods(monday - timedelta(days=7), monday - timedelta(days=1))


def presets(today: date | None = None) -> list[tuple[str, date, date]]:
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    month1 = today.replace(day=1)
    prev_month_end = month1 - timedelta(days=1)
    yesterday = today - timedelta(days=1)
    quarter1 = today.replace(month=(today.month - 1) // 3 * 3 + 1, day=1)
    year1 = today.replace(month=1, day=1)
    return [
        ("Прошлая неделя", monday - timedelta(days=7), monday - timedelta(days=1)),
        ("Эта неделя", monday, max(monday, yesterday)),
        ("Прошлый месяц", prev_month_end.replace(day=1), prev_month_end),
        ("Этот месяц", month1, max(month1, yesterday)),
        ("С начала квартала", quarter1, max(quarter1, yesterday)),
        ("С начала года", year1, max(year1, yesterday)),
    ]

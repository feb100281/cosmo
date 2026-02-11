# sales/reports/sales_report/period.py
from datetime import date, timedelta
import calendar

RU_MONTHS = {
    1: "ЯНВАРЬ", 2: "ФЕВРАЛЬ", 3: "МАРТ", 4: "АПРЕЛЬ",
    5: "МАЙ", 6: "ИЮНЬ", 7: "ИЮЛЬ", 8: "АВГУСТ",
    9: "СЕНТЯБРЬ", 10: "ОКТЯБРЬ", 11: "НОЯБРЬ", 12: "ДЕКАБРЬ",
}

def last_day_of_month(d: date) -> int:
    return calendar.monthrange(d.year, d.month)[1]

def classify_report(d: date) -> str:
    if d.day == last_day_of_month(d):
        return "monthly"
    if d.weekday() == 6:  # Sunday
        return "weekly"
    return "daily"

def format_period(d: date, report_type: str) -> dict:
    if report_type == "monthly":
        return {"label": "Отчётный период:", "value": f"{RU_MONTHS[d.month]} {d.year}"}
    if report_type == "weekly":
        week_start = d - timedelta(days=6)
        return {"label": "Отчётная неделя:", "value": f"{week_start:%d.%m.%Y} - {d:%d.%m.%Y}"}
    return {"label": "Отчётный день:", "value": d.strftime("%d.%m.%Y")}

def report_number(d: date, report_type: str) -> str:
    if report_type == "monthly":
        return f"MR-{d:%y%m}"
    if report_type == "weekly":
        return f"WR-{d:%G%V}"
    return f"DR-{d:%y%m%d}"

from datetime import date
from django.utils import timezone

from .formatters import fmt_money, fmt_int, fmt_pct
from .compare import build_compare
from .compare_chart import build_compare_delta_bar_svg


def build_summary(
    kpi: dict,
    period_value: str,
    report_type: str,
    report_date: date,
    period_start: date,
    period_end: date,
    generated_dt=None,
) -> dict:
    # timezone-aware datetime
    as_of = generated_dt or timezone.now()

    # Заголовок KPI (итоги за период)
    if report_type == "daily":
        title = f"I. KPI за {period_start:%d.%m.%Y}"
    elif report_type == "weekly":
        title = f"I. KPI за неделю ({period_start:%d.%m.%Y} – {period_end:%d.%m.%Y})"
    else:
        title = f"I. KPI за {period_value}"

    # Сравнение период-к-периоду (prev: вчера/пред.неделя/пред.месяц, ly: прошлый год)
    compare = build_compare(report_type, period_start, period_end)
    compare_chart_svg_pct = build_compare_delta_bar_svg(compare)


    # Короткий вывод
    note = "Сводка сформирована по данным периода."
    try:
        rr = float(kpi.get("rtr_ratio") or 0)
        if -1.0 <= rr <= 1.0:
            rr *= 100
        note = (
            "Зона внимания: повышенная доля возвратов — рекомендуется проверить причины (категории/магазины/логистика)."
            if rr >= 15
            else "Возвраты в контролируемом диапазоне. Фокус — удержание темпа продаж и контроль среднего чека."
        )
    except Exception:
        pass

    return {
        "title": title,
        "as_of": as_of,
        "report_date": report_date,     # дата среза (обычно конец периода)
        "period_start": period_start,   # начало периода KPI
        "period_end": period_end,       # конец периода KPI
        "values": {
            "dt": fmt_money(kpi.get("dt")),
            "cr": fmt_money(kpi.get("cr")),
            "amount": fmt_money(kpi.get("amount")),
            "orders": fmt_int(kpi.get("orders")),
            "ave_check": fmt_money(kpi.get("ave_check")),
            "rtr_ratio": fmt_pct(kpi.get("rtr_ratio")),
        },
        "compare": compare,  # compare.prev / compare.ly / compare.rows
        "compare_chart_svg_pct": compare_chart_svg_pct,

        "note": note,
    }

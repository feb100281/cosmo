# sales/reports/sales_plan_report/data.py

from calendar import monthrange, isleap
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta
from django.db import connection

from sales.models import StoreSalesPlan

from .calendar import build_cash_calendar
from .charts import build_cash_share_chart
from .forecast import build_forecast_vs_plan_chart
from .utils import to_decimal, fmt_money, fmt_pct, safe_div, normalize_store_name
from .returns_analytics import build_returns_analytics
from .calendar import build_calendars_for_all_stores






def get_month_bounds(report_date):
    start = report_date.replace(day=1)
    end = report_date.replace(
        day=monthrange(report_date.year, report_date.month)[1]
    )
    return start, end


def get_cash_fact_by_store(date_start, date_end):
    """
    ТОЛЬКО ПОСТУПЛЕНИЯ (без возвратов)
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                LOWER(TRIM(store)) AS store_name,
                COALESCE(SUM(amount), 0) AS fact
            FROM orders_orderscf
            WHERE date >= %s
              AND date <= %s
              AND (
                    oper_type = 'Поступление оплаты от клиента (продажа товаров, работ, услуг)'
                    OR register LIKE 'Отчет о розничных продажах%%'
              )
            GROUP BY LOWER(TRIM(store))
            """,
            [date_start, date_end],
        )
        return {
            row[0]: Decimal(str(row[1] or 0))
            for row in cursor.fetchall()
            if row[0] 
        }



def get_sales_plan_data(report_date):
    month_start, month_end = get_month_bounds(report_date)

    prev_month_report_date = report_date - relativedelta(months=1)
    prev_year_report_date = report_date - relativedelta(years=1)

    prev_month_start = prev_month_report_date.replace(day=1)
    prev_year_start = prev_year_report_date.replace(day=1)

    prev_month_fact_map = get_cash_fact_by_store(
        prev_month_start,
        prev_month_report_date,
    )

    prev_year_fact_map = get_cash_fact_by_store(
        prev_year_start,
        prev_year_report_date,
    )

    days_in_month = month_end.day
    days_passed = report_date.day
    days_left = max(days_in_month - days_passed, 0)

    # Получаем планы
    plans_qs = (
        StoreSalesPlan.objects
        .filter(
            plan_month__year=report_date.year,
            plan_month__month=report_date.month,
        )
        .select_related("store", "store__gr")
    )

    # Получаем факт по ВСЕМ магазинам (только поступления, без возвратов)
    facts_map = get_cash_fact_by_store(month_start, report_date)
    # ДОБАВИТЬ ЭТИ ДВЕ СТРОКИ:
    facts_map = {k: v for k, v in facts_map.items() if k and isinstance(k, str)}
    
    # Создаем словарь планов для быстрого доступа
    plans_map = {}
    stores_with_plan = {}
    
    for plan in plans_qs:
        store_key = normalize_store_name(str(plan.store).strip())
        plans_map[store_key] = to_decimal(plan.amount)
        stores_with_plan[store_key] = plan

    # Получаем ВСЕ уникальные магазины (и с планом, и без)
    all_stores = set(facts_map.keys()) | set(plans_map.keys())

    rows = []
    total_plan = Decimal("0")
    total_fact = Decimal("0")

    # Проходим по ВСЕМ магазинам
    for store_key in all_stores:
        # Получаем план (если есть)
        plan_amount = plans_map.get(store_key, Decimal("0"))
        
        # Получаем объект магазина (если есть план)
        plan_obj = stores_with_plan.get(store_key)
        
        # Получаем факт (только поступления)
        fact = facts_map.get(store_key, Decimal("0"))
        
        # Для магазинов без плана - пропускаем или добавляем с plan=0
        # Я добавляю с plan=0, чтобы видеть магазины с фактом но без плана
        
        # Получаем данные за прошлые периоды
        prev_month_fact = prev_month_fact_map.get(store_key, Decimal("0"))
        prev_year_fact = prev_year_fact_map.get(store_key, Decimal("0"))

        mom_diff = fact - prev_month_fact
        mom_pct = safe_div(mom_diff, prev_month_fact) * Decimal("100")

        yoy_diff = fact - prev_year_fact
        yoy_pct = safe_div(yoy_diff, prev_year_fact) * Decimal("100")

        # Выполнение плана (если плана нет - ставим 0 или None)
        if plan_amount > 0:
            exec_pct = safe_div(fact, plan_amount) * Decimal("100")
            diff = fact - plan_amount
            remaining = max(plan_amount - fact, Decimal("0"))
            is_done = exec_pct >= 100
        else:
            exec_pct = Decimal("0")
            diff = fact
            remaining = Decimal("0")
            is_done = False

        avg_daily_fact = safe_div(fact, days_passed) if days_passed > 0 else Decimal("0")
        
        if plan_amount > 0 and days_left > 0:
            required_daily = safe_div(remaining, days_left)
        else:
            required_daily = Decimal("0")

        projected_month_fact = avg_daily_fact * Decimal(days_in_month)
        
        if plan_amount > 0:
            projected_diff = projected_month_fact - plan_amount
            is_on_track = projected_month_fact >= plan_amount
        else:
            projected_diff = projected_month_fact
            is_on_track = False

        progress_width = Decimal("0")
        if plan_amount > 0:
            progress_width = min(exec_pct, Decimal("100")).quantize(
                Decimal("0.1"),
                rounding=ROUND_HALF_UP,
            )

        # Формируем название магазина
        if plan_obj:
            store_name = str(plan_obj.store).strip()
            group_name = str(plan_obj.store.gr) if getattr(plan_obj.store, "gr", None) else "—"
        else:
            store_name = store_key.title()  # или как-то иначе получаем имя
            group_name = "—"

        rows.append({
            "store": plan_obj.store if plan_obj else None,
            "store_name": store_name,
            "group_name": group_name,
            "has_plan": plan_amount > 0,

            "plan": plan_amount,
            "fact": fact,
            "diff": diff,
            "remaining": remaining,
            "exec_pct": exec_pct,

            "avg_daily_fact": avg_daily_fact,
            "required_daily": required_daily,
            "projected_month_fact": projected_month_fact,
            "projected_diff": projected_diff,

            "prev_month_fact": prev_month_fact,
            "prev_year_fact": prev_year_fact,
            "mom_diff": mom_diff,
            "mom_pct": mom_pct,
            "yoy_diff": yoy_diff,
            "yoy_pct": yoy_pct,

            "plan_fmt": fmt_money(plan_amount) if plan_amount > 0 else "—",
            "fact_fmt": fmt_money(fact),
            "diff_fmt": fmt_money(abs(diff)),
            "remaining_fmt": fmt_money(remaining) if plan_amount > 0 else "—",
            "avg_daily_fact_fmt": fmt_money(avg_daily_fact),
            "required_daily_fmt": fmt_money(required_daily),
            "projected_month_fact_fmt": fmt_money(projected_month_fact),
            "projected_diff_fmt": fmt_money(abs(projected_diff)),

            "prev_month_fact_fmt": fmt_money(prev_month_fact),
            "prev_year_fact_fmt": fmt_money(prev_year_fact),
            "mom_diff_fmt": fmt_money(abs(mom_diff)),
            "mom_pct_fmt": fmt_pct(abs(mom_pct)) if prev_month_fact > 0 else "—",
            "yoy_diff_fmt": fmt_money(abs(yoy_diff)),
            "yoy_pct_fmt": fmt_pct(abs(yoy_pct)) if prev_year_fact > 0 else "—",

            "exec_pct_fmt": fmt_pct(exec_pct) if plan_amount > 0 else "нет плана",
            "progress_width": progress_width,

            "is_done": is_done,
            "is_on_track": is_on_track if plan_amount > 0 else False,
            # Единый показатель для покраски и бейджа, и прогресс-бара —
            # чтобы они никогда не расходились по цвету на одной строке.
            "status_tier": (
                "good" if is_done
                else "watch" if (plan_amount > 0 and is_on_track)
                else "bad"
            ),
        })

        if plan_amount > 0:
            total_plan += plan_amount
        total_fact += fact

    # Сортируем: сначала с планом по выполнению, потом без плана
    rows = sorted(rows, key=lambda x: (not x["has_plan"], -x["exec_pct"] if x["has_plan"] else 0))

    # Считаем доли только для магазинов с фактом
    for row in rows:
        if total_fact > 0 and row["fact"] > 0:
            share_pct = safe_div(row["fact"], total_fact) * Decimal("100")
            row["share_pct"] = share_pct
            row["share_pct_fmt"] = fmt_pct(share_pct)
        else:
            row["share_pct"] = Decimal("0")
            row["share_pct_fmt"] = "0%"

    # Итоги
    total_exec_pct = safe_div(total_fact, total_plan) * Decimal("100") if total_plan > 0 else Decimal("0")
    total_diff = total_fact - total_plan
    total_remaining = max(total_plan - total_fact, Decimal("0"))

    total_avg_daily_fact = safe_div(total_fact, days_passed) if days_passed > 0 else Decimal("0")
    total_required_daily = safe_div(total_remaining, days_left) if days_left > 0 else total_remaining

    total_projected_month_fact = total_avg_daily_fact * Decimal(days_in_month)
    total_projected_diff = total_projected_month_fact - total_plan

    total_progress_width = Decimal("0")
    if total_plan > 0:
        total_progress_width = min(total_exec_pct, Decimal("100")).quantize(
            Decimal("0.1"),
            rounding=ROUND_HALF_UP,
        )

    calendar_daily_plan = safe_div(total_plan, days_in_month) if total_plan > 0 else Decimal("0")
    stores_calendars = build_calendars_for_all_stores(report_date, rows)

    cash_calendar = build_cash_calendar(
        report_date=report_date,
        daily_plan=calendar_daily_plan,
    )

    cash_share_chart = build_cash_share_chart(
        rows=[r for r in rows if r["fact"] > 0],
        total_fact=total_fact,
    )
    
    forecast_vs_plan_chart = build_forecast_vs_plan_chart(
        total_plan=total_plan,
        total_fact=total_fact,
        projected_month_fact=total_projected_month_fact,
    )
    returns_analytics = build_returns_analytics(report_date, rows)

    return {
        "report_date": report_date,
        "month_start": month_start,
        "month_end": month_end,
        "days_in_month": days_in_month,
        "days_passed": days_passed,
        "days_left": days_left,

        "cash_calendar": cash_calendar,
        "stores_calendars": stores_calendars,
        "cash_share_chart": cash_share_chart,
        "forecast_vs_plan_chart": forecast_vs_plan_chart,
        "returns_analytics": returns_analytics,

        "rows": rows,

        "totals": {
            "plan": total_plan,
            "fact": total_fact,
            "diff": total_diff,
            "remaining": total_remaining,
            "exec_pct": total_exec_pct,

            "avg_daily_fact": total_avg_daily_fact,
            "required_daily": total_required_daily,
            "projected_month_fact": total_projected_month_fact,
            "projected_diff": total_projected_diff,

            "plan_fmt": fmt_money(total_plan),
            "fact_fmt": fmt_money(total_fact),
            "diff_fmt": fmt_money(abs(total_diff)),
            "remaining_fmt": fmt_money(total_remaining),
            "avg_daily_fact_fmt": fmt_money(total_avg_daily_fact),
            "required_daily_fmt": fmt_money(total_required_daily),
            "projected_month_fact_fmt": fmt_money(total_projected_month_fact),
            "projected_diff_fmt": fmt_money(abs(total_projected_diff)),

            "exec_pct_fmt": fmt_pct(total_exec_pct),
            "progress_width": total_progress_width,

            "is_done": total_exec_pct >= 100,
            "is_on_track": total_projected_month_fact >= total_plan,
            "status_tier": (
                "good" if total_exec_pct >= 100
                else "watch" if total_projected_month_fact >= total_plan
                else "bad"
            ),
            "stores_count": len(rows),
            "stores_with_plan_count": len([r for r in rows if r["has_plan"]]),
        },
    }


# ---------------------------------------------------------------------------
# YTD (год к дате) — накопительный план/факт по кэшу с начала года.
#
# Переиспользует те же кирпичи, что и месячный расчёт выше
# (get_cash_fact_by_store, StoreSalesPlan, normalize_store_name/to_decimal/
# fmt_money/fmt_pct/safe_div) — никакой новой методологии подсчёта кэша,
# только другой горизонт агрегации: с 1 января по report_date включительно.
#
# "План с начала года" считается накопительно и с той же логикой, что и
# темп месяца в get_sales_plan_data: полностью прошедшие месяцы года берутся
# целиком, а текущий (ещё не закончившийся) месяц — пропорционально доле
# прошедших в нём дней. Это даёт корректное "план на сегодня" в любой день
# года, а не только на конец месяца. Отдельно считается "план на год" —
# сумма всех строк StoreSalesPlan за календарный год (включая ещё не
# наступившие месяцы, если они уже заведены) — для контекста "% от
# годового плана", который не является метрикой темпа.
# ---------------------------------------------------------------------------

_MONTHS_RU_SHORT = [
    "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
]


def _build_ytd_monthly_series(report_date, year_plans):
    """
    Помесячный ряд план/факт с начала года (месяцы 1..report_date.month
    включительно) — для тренд-графика на странице YTD. year_plans — уже
    материализованный список StoreSalesPlan за календарный год (чтобы не
    дёргать БД ещё раз поверх того, что уже выбрано в get_cash_ytd_data).
    """
    plan_by_month = {}
    for plan in year_plans:
        m = plan.plan_month.month
        plan_by_month[m] = plan_by_month.get(m, Decimal("0")) + to_decimal(plan.amount)

    months = []
    for m in range(1, report_date.month + 1):
        month_start = report_date.replace(month=m, day=1)
        if m == report_date.month:
            month_end = report_date
        else:
            month_end = report_date.replace(month=m, day=monthrange(report_date.year, m)[1])

        fact_map = get_cash_fact_by_store(month_start, month_end)
        fact = sum(fact_map.values(), Decimal("0"))

        prev_year_month_start = month_start - relativedelta(years=1)
        prev_year_month_end = month_end - relativedelta(years=1)
        prev_fact_map = get_cash_fact_by_store(prev_year_month_start, prev_year_month_end)
        prev_fact = sum(prev_fact_map.values(), Decimal("0"))

        plan = plan_by_month.get(m, Decimal("0"))

        months.append({
            "month": m,
            "month_name": _MONTHS_RU_SHORT[m - 1],
            "is_current": m == report_date.month,
            "plan": plan,
            "fact": fact,
            "fact_prev_year": prev_fact,
            "plan_fmt": fmt_money(plan) if plan > 0 else "—",
            "fact_fmt": fmt_money(fact),
            "fact_prev_year_fmt": fmt_money(prev_fact),
        })

    return months


def get_cash_ytd_data(report_date):
    """
    Накопительный план/факт по кэшу с начала года по report_date.year по
    report_date включительно, по компании и по магазинам, плюс сравнение с
    аналогичным периодом прошлого года (АППГ) и помесячный ряд для графика.
    """
    year_start = report_date.replace(month=1, day=1)
    days_in_year = 366 if isleap(report_date.year) else 365
    days_passed_year = (report_date - year_start).days + 1

    prev_year_report_date = report_date - relativedelta(years=1)
    prev_year_start = prev_year_report_date.replace(month=1, day=1)

    fact_map = get_cash_fact_by_store(year_start, report_date)
    fact_map = {k: v for k, v in fact_map.items() if k and isinstance(k, str)}

    prev_year_fact_map = get_cash_fact_by_store(prev_year_start, prev_year_report_date)
    prev_year_fact_map = {k: v for k, v in prev_year_fact_map.items() if k and isinstance(k, str)}

    days_in_month = monthrange(report_date.year, report_date.month)[1]
    month_fraction = to_decimal(report_date.day) / to_decimal(days_in_month)

    year_plans = list(
        StoreSalesPlan.objects
        .filter(plan_month__year=report_date.year)
        .select_related("store", "store__gr")
    )

    # "План на год" выше складывается из всех строк StoreSalesPlan за год,
    # включая ещё не наступившие месяцы, ЕСЛИ они уже заведены. Если план
    # заведён только по текущий месяц (декабрь ещё не внесён), эта сумма —
    # не полный годовой план, а лишь то, что успели ввести. Помечаем это
    # явно, чтобы потребители (например, Newspaper) не показывали "% от
    # годового плана" и прогноз-vs-план как надёжную метрику, пока план не
    # заведён на весь год.
    # Важно: считаем месяц "заведённым" только если по нему есть реальная
    # ненулевая сумма плана хотя бы по одному магазину, а не просто по
    # факту существования строки StoreSalesPlan. На практике строки на
    # будущие месяцы иногда создаются заранее пустыми (amount=0) как
    # заготовка — такая строка не должна считаться "план на декабрь уже
    # есть", иначе plan_year_complete station станет True раньше времени.
    plan_amount_by_month = {}
    for p in year_plans:
        plan_amount_by_month[p.plan_month.month] = (
            plan_amount_by_month.get(p.plan_month.month, Decimal("0")) + to_decimal(p.amount)
        )
    planned_months = {m for m, amt in plan_amount_by_month.items() if amt > 0}
    plan_year_complete = bool(planned_months) and max(planned_months) >= 12
    plan_year_last_month = max(planned_months) if planned_months else None

    plan_to_date_map = {}
    plan_year_full_map = {}
    store_obj_map = {}

    for plan in year_plans:
        store_key = normalize_store_name(str(plan.store).strip())
        store_obj_map.setdefault(store_key, plan.store)
        amt = to_decimal(plan.amount)

        plan_year_full_map[store_key] = plan_year_full_map.get(store_key, Decimal("0")) + amt

        if plan.plan_month.month < report_date.month:
            plan_to_date_map[store_key] = plan_to_date_map.get(store_key, Decimal("0")) + amt
        elif plan.plan_month.month == report_date.month:
            prorated = amt * month_fraction
            plan_to_date_map[store_key] = plan_to_date_map.get(store_key, Decimal("0")) + prorated
        # месяцы позже report_date.month в "план на сегодня" не входят —
        # только в "план на год"

    all_stores = set(fact_map) | set(plan_to_date_map) | set(plan_year_full_map)

    rows = []
    total_plan_to_date = Decimal("0")
    total_plan_year_full = Decimal("0")
    total_fact = Decimal("0")
    total_prev_year_fact = Decimal("0")

    for store_key in all_stores:
        fact = fact_map.get(store_key, Decimal("0"))
        prev_year_fact = prev_year_fact_map.get(store_key, Decimal("0"))
        plan_to_date = plan_to_date_map.get(store_key, Decimal("0"))
        plan_year_full = plan_year_full_map.get(store_key, Decimal("0"))
        store_obj = store_obj_map.get(store_key)

        has_plan = plan_to_date > 0 or plan_year_full > 0

        exec_pct = safe_div(fact, plan_to_date) * Decimal("100") if plan_to_date > 0 else Decimal("0")
        year_pct = safe_div(fact, plan_year_full) * Decimal("100") if plan_year_full > 0 else Decimal("0")

        yoy_diff = fact - prev_year_fact
        yoy_pct = safe_div(yoy_diff, prev_year_fact) * Decimal("100")

        # Прогноз на конец года по этому магазину — тот же принцип, что и
        # для компании целиком (среднедневной факт с начала года * дней в
        # году), чтобы "в темпе ли магазин" не путать с "уже выполнил план
        # на сегодня" (is_done) — ровно то же разделение, что и в месячном
        # расчёте выше (is_done vs is_on_track).
        avg_daily_fact = safe_div(fact, days_passed_year) if days_passed_year > 0 else Decimal("0")
        projected_year_fact = avg_daily_fact * Decimal(days_in_year)

        is_done = exec_pct >= 100 if plan_to_date > 0 else False
        is_on_track = projected_year_fact >= plan_year_full if plan_year_full > 0 else False

        if store_obj:
            store_name = str(store_obj).strip()
            group_name = str(store_obj.gr) if getattr(store_obj, "gr", None) else "—"
        else:
            store_name = store_key.title()
            group_name = "—"

        rows.append({
            "store_name": store_name,
            "group_name": group_name,
            "has_plan": has_plan,

            "plan_to_date": plan_to_date,
            "plan_year_full": plan_year_full,
            "fact": fact,
            "exec_pct": exec_pct,
            "year_pct": year_pct,
            "projected_year_fact": projected_year_fact,

            "prev_year_fact": prev_year_fact,
            "yoy_diff": yoy_diff,
            "yoy_pct": yoy_pct,

            "plan_to_date_fmt": fmt_money(plan_to_date) if plan_to_date > 0 else "—",
            "plan_year_full_fmt": fmt_money(plan_year_full) if plan_year_full > 0 else "—",
            "fact_fmt": fmt_money(fact),
            "exec_pct_fmt": fmt_pct(exec_pct) if plan_to_date > 0 else "нет плана",
            "year_pct_fmt": fmt_pct(year_pct) if plan_year_full > 0 else "—",
            "projected_year_fact_fmt": fmt_money(projected_year_fact),

            "prev_year_fact_fmt": fmt_money(prev_year_fact),
            "yoy_diff_fmt": fmt_money(abs(yoy_diff)),
            "yoy_pct_fmt": fmt_pct(abs(yoy_pct)) if prev_year_fact > 0 else "—",

            "is_done": is_done,
            "is_on_track": is_on_track,
            "status_tier": (
                "good" if is_done
                else "watch" if (plan_to_date > 0 and is_on_track)
                else "bad" if has_plan
                else "neutral"
            ),
        })

        if plan_to_date > 0:
            total_plan_to_date += plan_to_date
        if plan_year_full > 0:
            total_plan_year_full += plan_year_full
        total_fact += fact
        total_prev_year_fact += prev_year_fact

    rows = sorted(
        rows,
        key=lambda r: (not r["has_plan"], -float(r["exec_pct"]) if r["has_plan"] else 0),
    )

    total_exec_pct = safe_div(total_fact, total_plan_to_date) * Decimal("100") if total_plan_to_date > 0 else Decimal("0")
    total_year_pct = safe_div(total_fact, total_plan_year_full) * Decimal("100") if total_plan_year_full > 0 else Decimal("0")
    total_yoy_diff = total_fact - total_prev_year_fact
    total_yoy_pct = safe_div(total_yoy_diff, total_prev_year_fact) * Decimal("100")

    avg_daily_fact = safe_div(total_fact, days_passed_year) if days_passed_year > 0 else Decimal("0")
    projected_year_fact = avg_daily_fact * Decimal(days_in_year)
    projected_year_diff = projected_year_fact - total_plan_year_full

    monthly = _build_ytd_monthly_series(report_date, year_plans)

    return {
        "report_date": report_date,
        "year_start": year_start,
        "days_passed_year": days_passed_year,
        "days_in_year": days_in_year,
        "prev_year_start": prev_year_start,
        "prev_year_report_date": prev_year_report_date,

        "rows": rows,
        "monthly": monthly,

        "totals": {
            "plan_to_date": total_plan_to_date,
            "plan_year_full": total_plan_year_full,
            "plan_year_complete": plan_year_complete,
            "plan_year_last_month": plan_year_last_month,
            "fact": total_fact,
            "exec_pct": total_exec_pct,
            "year_pct": total_year_pct,

            "prev_year_fact": total_prev_year_fact,
            "yoy_diff": total_yoy_diff,
            "yoy_pct": total_yoy_pct,

            "projected_year_fact": projected_year_fact,
            "projected_year_diff": projected_year_diff,
            "is_done": total_exec_pct >= 100 if total_plan_to_date > 0 else False,
            "is_on_track": projected_year_fact >= total_plan_year_full if total_plan_year_full > 0 else False,
            "status_tier": (
                "good" if (total_plan_to_date > 0 and total_exec_pct >= 100)
                else "watch" if (total_plan_year_full > 0 and projected_year_fact >= total_plan_year_full)
                else "bad" if total_plan_to_date > 0
                else "neutral"
            ),

            "plan_to_date_fmt": fmt_money(total_plan_to_date),
            "plan_year_full_fmt": fmt_money(total_plan_year_full),
            "fact_fmt": fmt_money(total_fact),
            "exec_pct_fmt": fmt_pct(total_exec_pct),
            "year_pct_fmt": fmt_pct(total_year_pct),

            "prev_year_fact_fmt": fmt_money(total_prev_year_fact),
            "yoy_diff_fmt": fmt_money(abs(total_yoy_diff)),
            "yoy_pct_fmt": fmt_pct(abs(total_yoy_pct)) if total_prev_year_fact > 0 else "—",

            "projected_year_fact_fmt": fmt_money(projected_year_fact),
            "projected_year_diff_fmt": fmt_money(abs(projected_year_diff)),

            "stores_count": len(rows),
            "stores_with_plan_count": len([r for r in rows if r["has_plan"]]),
        },
    }

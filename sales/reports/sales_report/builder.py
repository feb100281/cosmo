# sales/reports/sales_report/builder.py
from datetime import date
import pandas as pd


from sales.models import MV_Daily_Sales
from sales.dash_apps.dailysales.data import get_month_data, get_ytd_data
from sales.print_utils import build_mtd_table, build_ytd_table

from .charts import build_charts
from .insights import build_insights
from .period import classify_report, format_period, report_number
from .summary import build_summary

from .ranges import period_range, prev_period_range, last_13m_range
from .trends import trend_ranges, trend_meta
from .kpi import build_kpi_for_range

from .stores import get_store_sales_for_range
from .store_chart import build_store_amount_bar_svg
from .store_logos import attach_store_logos
from .trend_chart import build_trend_chart_svg
from .commulative_chart import build_mtd_waterfall_svg, build_ytd_cumulative_svg
from .ltm_chart import build_revenue_13m_svg
from .categories_block import build_categories_context, build_categories_context_ytd
from .print_utils_categories import build_categories_table
from .categories_chart import build_mtd_categories_bar_svg, build_ytd_categories_bar_svg
from .ltm_insights import build_ltm_insights

from dateutil.relativedelta import relativedelta
from .ltm_forecast_prophet import build_prophet_eom_projection






from .formatters import (
    fmt_money,
    fmt_int,
    fmt_pct,
    fmt_delta_money,
    fmt_delta_pct,
    fmt_money_0, 
    fmt_delta_short
)


def build_mtd_method_context(df_mtd_raw):
    """
    Методика для MTD-waterfall, которая сходится с таблицей "Выручка" (amount).
    Готовит данные для красивого HTML-блока под графиком.
    """
    import pandas as pd

    
    
    df = df_mtd_raw.copy()
    if df.empty:
        return None

    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    for c in ("amount", "orders", "dt", "cr"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    years = sorted(df["year"].unique())[-2:]
    if len(years) < 2:
        return None
    y_prev, y_curr = years[0], years[1]

    def _totals(y: int):
        d = df[df["year"] == y]
        revenue = float(d["amount"].sum())
        orders = float(d["orders"].sum())
        ave = (revenue / orders) if orders else 0.0

        # справочно
        dt = float(d["dt"].sum()) if "dt" in d.columns else 0.0
        cr = float(d["cr"].sum()) if "cr" in d.columns else 0.0

        return {"revenue": revenue, "orders": orders, "ave": ave, "dt": dt, "cr": cr}

    p = _totals(y_prev)
    c = _totals(y_curr)

    eff_orders = (c["orders"] - p["orders"]) * p["ave"]
    eff_ave = (c["ave"] - p["ave"]) * c["orders"]

    bridge_rev = p["revenue"] + eff_orders + eff_ave
    residual = c["revenue"] - bridge_rev

    d_cr = c["cr"] - p["cr"]
    cr_uplift = -(d_cr)

    return {
        "y_prev": y_prev,
        "y_curr": y_curr,

        # значения
        "revenue_prev": fmt_money(p["revenue"]),
        "revenue_curr": fmt_money(c["revenue"]),
        "orders_prev": fmt_int(p["orders"]),
        "orders_curr": fmt_int(c["orders"]),
        "ave_prev": fmt_money_0(p["ave"]),
        "ave_curr": fmt_money_0(c["ave"]),

        # эффекты
        "eff_orders": fmt_delta_short(eff_orders),
        "eff_ave": fmt_delta_short(eff_ave),

        # контроль
        "bridge_rev": fmt_money(bridge_rev),
        "residual": fmt_delta_money(residual),

        # контрольная строка (чтобы красиво вывести в HTML)
        "control_left": fmt_money(p["revenue"]),
        "control_e1": fmt_delta_money(eff_orders),
        "control_e2": fmt_delta_money(eff_ave),
        "control_right": fmt_money(c["revenue"]),

        # возвраты (справочно)
        "cr_prev": fmt_money(p["cr"]),
        "cr_curr": fmt_money(c["cr"]),
        "d_cr": fmt_delta_money(d_cr),
        "cr_uplift": fmt_delta_money(cr_uplift),
    }


def build_ytd_driver_context(df_ytd_raw):
    """
    YTD: драйверы изменения выручки (Orders / Ave) + контроль сходимости.
    Revenue = Orders * Ave, Ave = Revenue / Orders
    Эффект заказов       = (Orders_curr - Orders_prev) * Ave_prev
    Эффект среднего чека = (Ave_curr - Ave_prev) * Orders_curr
    Контроль:
      Revenue_prev + эффекты ≈ Revenue_curr
      residual = Revenue_curr - bridge_rev
    """
    import pandas as pd

    if df_ytd_raw is None or df_ytd_raw.empty:
        return None

    df = df_ytd_raw.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    for c in ("amount", "orders"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    years = sorted(df["year"].unique())[-2:]
    if len(years) < 2:
        return None
    y_prev, y_curr = years[0], years[1]

    def _totals(y: int):
        d = df[df["year"] == y]
        revenue = float(d["amount"].sum())
        orders = float(d["orders"].sum()) if "orders" in d.columns else 0.0
        ave = (revenue / orders) if orders else 0.0
        return {"revenue": revenue, "orders": orders, "ave": ave}

    p = _totals(y_prev)
    c = _totals(y_curr)

    if p["orders"] == 0 and c["orders"] == 0:
        return None

    eff_orders = (c["orders"] - p["orders"]) * p["ave"]
    eff_ave = (c["ave"] - p["ave"]) * c["orders"]

    bridge_rev = p["revenue"] + eff_orders + eff_ave
    residual = c["revenue"] - bridge_rev  # то, что не “сошлось” из-за округлений/особенностей данных

    d_rev = c["revenue"] - p["revenue"]
    eff_sum = eff_orders + eff_ave

    main_driver = (
        "за счёт объёма (кол-ва заказов)"
        if abs(eff_orders) >= abs(eff_ave)
        else "за счёт среднего чека"
    )
    def _dir(v):
        if v > 0:
            return "pos"
        if v < 0:
            return "neg"
        return "flat"

    return {
        "has": True,
        "y_prev": y_prev,
        "y_curr": y_curr,

        # эффекты (коротко — для текста)
        "eff_orders": fmt_delta_short(eff_orders),
        "eff_ave": fmt_delta_short(eff_ave),
        "eff_orders_dir": _dir(eff_orders),
        "eff_ave_dir": _dir(eff_ave),


        # контроль (точнее)
        "d_rev": fmt_delta_money(d_rev),
        "eff_sum": fmt_delta_money(eff_sum),
        "residual": fmt_delta_money(residual),

        "main_driver": main_driver,
    }



def build_daily_sales_report_context(d: date, request=None) -> dict:
    # объект дня (может быть нужен для insights/секций, но KPI теперь не из него)
    obj = MV_Daily_Sales.objects.get(pk=d)

    # тип отчёта + период (строки для обложки)
    rtype = classify_report(d)
    period = format_period(d, rtype)

    # диапазон дат для KPI (итог за период)
    period_start, period_end = period_range(d, rtype)
    kpi = build_kpi_for_range(period_start, period_end)

    # ---------------------------------------------------------------------
    # ✅ TREND (пока без графика) — сразу форматируем для шаблона
    # ---------------------------------------------------------------------
    trend_points = 12

    trend = []
    for s, e, label, is_current in trend_ranges(rtype, d, points=trend_points):
        k = build_kpi_for_range(s, e)

        trend.append({
            "label": label,
            "start": s,
            "end": e,
            "is_current": is_current,

            # RAW для графика
            "amount_raw": k.get("amount") or 0,
            "dt_raw": k.get("dt") or 0,
            "orders_raw": k.get("orders") or 0,
            "cr_raw": k.get("cr") or 0,
            "ave_check_raw": k.get("ave_check") or 0,

            # formatted для таблицы
            "amount": fmt_money(k.get("amount")),
            "dt": fmt_money(k.get("dt")),
            "orders": fmt_int(k.get("orders")),
            "cr": fmt_money(k.get("cr")),
            "ave_check": fmt_money(k.get("ave_check")),
            "rtr_ratio": fmt_pct(k.get("rtr_ratio")),
        })

    trend_meta_ctx = trend_meta(rtype, d, points=trend_points)

    trend_chart_svg = build_trend_chart_svg(trend, metric="amount_raw")
    
    
    # --- data-bars для "Выручка" (amount_raw) ---
    amount_vals = [t["amount_raw"] for t in trend if (t.get("amount_raw") is not None)]
    if amount_vals:
        vmin, vmax = min(amount_vals), max(amount_vals)
        span = (vmax - vmin) or 1
        for t in trend:
            v = t.get("amount_raw") or 0
            t["amount_pct"] = round((v - vmin) / span * 100, 1)
    else:
        for t in trend:
            t["amount_pct"] = 0




    # продажи по магазинам за период (RAW)
    store_rows_raw = get_store_sales_for_range(period_start, period_end)

    # предыдущий период для сравнения (RAW)
    prev_start, prev_end = prev_period_range(period_start, period_end, rtype)
    store_prev_raw = get_store_sales_for_range(prev_start, prev_end)

    # индекс прошлого периода по store_id
    prev_map = {r["store_id"]: r for r in store_prev_raw}

    # ✅ данные для графика: current vs prev (amount)
    store_rows_chart = []
    for r in store_rows_raw:
        p = prev_map.get(r["store_id"])
        store_rows_chart.append({
            "store": r["store"],
            "amount": r.get("amount") or 0,
            "prev_amount": (p.get("amount") if p else 0) or 0,
        })
        
    
    

    # ✅ график (SVG) по магазинам (TOP-12 по чистой выручке)
    store_chart_svg = build_store_amount_bar_svg(
        store_rows_chart,
        title="Чистая выручка по магазинам (было / стало)",
    )
    


    def _delta(curr, prev):
        if prev is None:
            return None
        return (curr or 0) - (prev or 0)

    def _delta_pct(curr, prev):
        if prev in (None, 0):
            return None
        return ((curr or 0) - prev) / prev * 100

    def _dir(v):
        if v is None:
            return "na"
        if v > 0:
            return "up"
        if v < 0:
            return "down"
        return "flat"

    # ✅ ИТОГО (по текущему периоду)
    total_dt = 0
    total_cr = 0
    total_amount = 0
    total_quant = 0
    total_orders = 0

    for r in store_rows_raw:
        total_dt += r.get("dt") or 0
        total_cr += r.get("cr") or 0
        total_amount += r.get("amount") or 0
        total_quant += r.get("quant") or 0
        total_orders += r.get("orders") or 0

    total_ave_check = (total_amount / total_orders) if total_orders else None
    total_rtr_ratio = (total_cr / total_dt) if total_dt else None

    # форматируем строки магазинов + дельты к прошлому периоду
    store_rows = []
    for r in store_rows_raw:
        p = prev_map.get(r["store_id"])

        # дельты (RAW)
        d_amount = _delta(r.get("amount"), p.get("amount") if p else None)
        d_amount_pct = _delta_pct(r.get("amount"), p.get("amount") if p else None)

        d_dt = _delta(r.get("dt"), p.get("dt") if p else None)
        d_dt_pct = _delta_pct(r.get("dt"), p.get("dt") if p else None)

        d_orders = _delta(r.get("orders"), p.get("orders") if p else None)
        d_orders_pct = _delta_pct(r.get("orders"), p.get("orders") if p else None)

        d_ave = _delta(r.get("ave_check"), p.get("ave_check") if p else None)
        d_ave_pct = _delta_pct(r.get("ave_check"), p.get("ave_check") if p else None)

        # ⚠ возвраты: рост — плохо (для стрелок/цвета можно инвертировать)
        d_cr = _delta(r.get("cr"), p.get("cr") if p else None)
        d_cr_pct = _delta_pct(r.get("cr"), p.get("cr") if p else None)

        store_rows.append({
            "store": r["store"],

            "amount": fmt_money(r.get("amount")),
            "dt": fmt_money(r.get("dt")),
            "cr": fmt_money(r.get("cr")),
            "quant": fmt_int(r.get("quant")),
            "orders": fmt_int(r.get("orders")),
            "ave_check": fmt_money(r.get("ave_check")),
            "rtr_ratio": fmt_pct(r.get("rtr_ratio")),

            # дельты для отображения (вторая строка в ячейке)
            "delta": {
                "amount": {
                    "abs": fmt_delta_money(d_amount),
                    "pct": fmt_delta_pct(d_amount_pct),
                    "dir": _dir(d_amount),
                    "has": p is not None,
                },
                "dt": {
                    "abs": fmt_delta_money(d_dt),
                    "pct": fmt_delta_pct(d_dt_pct),
                    "dir": _dir(d_dt),
                    "has": p is not None,
                },
                "orders": {
                    "abs": fmt_int(d_orders) if d_orders is not None else "—",
                    "pct": fmt_delta_pct(d_orders_pct),
                    "dir": _dir(d_orders),
                    "has": p is not None,
                },
                "ave_check": {
                    "abs": fmt_delta_money(d_ave),
                    "pct": fmt_delta_pct(d_ave_pct),
                    "dir": _dir(d_ave),
                    "has": p is not None,
                },
                "cr": {
                    "abs": fmt_delta_money(d_cr),
                    "pct": fmt_delta_pct(d_cr_pct),
                    # рост возвратов визуально считаем "down" (т.е. плохо)
                    "dir": _dir(-d_cr) if d_cr is not None else "na",
                    "has": p is not None,
                },
            },
        })

    # добавляем строку ИТОГО последней (без дельт, чтобы не перегружать)
    store_rows.append({
        "store": "ИТОГО",
        "amount": fmt_money(total_amount),
        "dt": fmt_money(total_dt),
        "cr": fmt_money(total_cr),
        "quant": fmt_int(total_quant),
        "orders": fmt_int(total_orders),
        "ave_check": fmt_money(total_ave_check),
        "rtr_ratio": fmt_pct(total_rtr_ratio),
        "delta": None,
    })
    store_rows = attach_store_logos(store_rows)

    # данные MTD/YTD (как и раньше, на дату d)
    df_mtd_raw = get_month_data(d)
    df_ytd_raw = get_ytd_data(d)
    ytd_driver = build_ytd_driver_context(df_ytd_raw)
    
    categories = build_categories_context(d, top_n=12)
    
    categories_chart_svg = build_mtd_categories_bar_svg(
    categories.get("raw"),
    top_n=12,
    title="MTD: ТОП категорий (текущий год vs прошлый)",
)
    
    categories_ytd = build_categories_context_ytd(d, top_n=12)

    categories_ytd_chart_svg = build_ytd_categories_bar_svg(
    categories_ytd.get("raw"),
    top_n=12,
    title="YTD: ТОП категорий (текущий год vs прошлый)",
)


    categories_table_html = build_categories_table(
    categories.get("cats", []),
    title="ТОП категорий (MTD, к прошлому году)",
    mode="cat"
).get("html", "")

    subcategories_table_html = build_categories_table(
        categories.get("subcats", []),
        title="ТОП подкатегорий (MTD, к прошлому году)",
        mode="sub"
    ).get("html", "")
    
    
    categories_ytd = build_categories_context_ytd(d, top_n=12)

    categories_ytd_table_html = build_categories_table(
        categories_ytd.get("cats", []),
        title="ТОП категорий (YTD, к прошлому году)",
        mode="cat"
    ).get("html", "")

    subcategories_ytd_table_html = build_categories_table(
        categories_ytd.get("subcats", []),
        title="ТОП подкатегорий (YTD, к прошлому году)",
        mode="sub"
    ).get("html", "")



    
    # --- 13 месяцев (с 1-го числа) ---
    ltm_start, ltm_end = last_13m_range(d)

    qs_13m = (
        MV_Daily_Sales.objects
        .filter(date__gte=ltm_start, date__lte=ltm_end)
        .values("date", "amount")
        .order_by("date")
    )
    df_13m_raw = pd.DataFrame(list(qs_13m))

    revenue_13m_svg = build_revenue_13m_svg(df_13m_raw, report_date=d)
    ltm_insights = build_ltm_insights(df_13m_raw, d)
    
    
    # --- Prophet projection (EOM) ---
    fc_start = date(2023, 1, 1)

    qs_fc = (
        MV_Daily_Sales.objects
        .filter(date__gte=fc_start, date__lte=d)
        .values("date", "amount")
        .order_by("date")
    )

    df_fc_raw = pd.DataFrame(list(qs_fc))
    
    print("PROPHET df_fc_raw rows:", len(df_fc_raw))
    if not df_fc_raw.empty:
        print("PROPHET range:", df_fc_raw["date"].min(), "->", df_fc_raw["date"].max())

    ltm_prophet = build_prophet_eom_projection(
        df_fc_raw,
        report_date=d,
        historical_cut_off=None,   # можно поставить fc_start, если хочешь жестко
        yearly_seasonality=True,
        weekly_seasonality=True,
        seasonality_mode="additive",
        changepoint_prior_scale=0.05,
        changepoint_range=1.0,
        n_changepoints=25,
)







    table_mtd = build_mtd_table(df_mtd_raw)
    table_ytd = build_ytd_table(df_ytd_raw)
    
    mtd_waterfall_svg = build_mtd_waterfall_svg(df_mtd_raw)
    mtd_method = build_mtd_method_context(df_mtd_raw)
    ytd_cum_svg = build_ytd_cumulative_svg(df_ytd_raw)
    




    charts = build_charts(d, df_mtd_raw=df_mtd_raw, df_ytd_raw=df_ytd_raw)
    insights = build_insights(obj)

    # summary — строим из KPI за период
    summary = build_summary(
        kpi=kpi,
        period_value=period["value"],
        report_type=rtype,
        report_date=d,
        period_start=period_start,
        period_end=period_end,
        generated_dt=None,
    )

    return {
        "obj": obj,
        "report_date": d,  # дата среза (конец периода)
        "generated_date": date.today(),
        "report_type": rtype,
        "period_label": period["label"],
        "period_value": period["value"],
        "period_start": period_start,
        "period_end": period_end,

        "store_sales": store_rows,
        "store_prev_start": prev_start,
        "store_prev_end": prev_end,

        # ✅ SVG-график по магазинам
        "store_chart_svg": store_chart_svg,

        "report_number": report_number(d, rtype),
        "summary": summary,
        "kpi": kpi,

        # ✅ тренды
        "trend": trend,
        "trend_chart_svg": trend_chart_svg,
        "trend_meta": trend_meta_ctx,
        


        "table_mtd_html": table_mtd.get("html", ""),
        "table_ytd_html": table_ytd.get("html", ""),
        "mtd_waterfall_svg": mtd_waterfall_svg,
        "mtd_method": mtd_method,
        "ytd_cum_svg": ytd_cum_svg,
        "ytd_driver": ytd_driver,
        "revenue_13m_svg": revenue_13m_svg,
        "ltm_insights": ltm_insights,
        "ltm_prophet": ltm_prophet,
        
        "categories": categories,
        "categories_table_html": categories_table_html,
        "subcategories_table_html": subcategories_table_html,
        "categories_chart_svg": categories_chart_svg,
        
        "categories_ytd": categories_ytd,
        "categories_ytd_table_html": categories_ytd_table_html,
        "subcategories_ytd_table_html": subcategories_ytd_table_html,
        "categories_ytd": categories_ytd,
        "categories_ytd_chart_svg": categories_ytd_chart_svg,

        
        "charts": charts,
        "insights": insights,
        "src": (request.GET.get("src", "list") if request else "list"),
    }
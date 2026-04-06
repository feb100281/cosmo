# # sales/reports/sales_report/ltm_forecast_prophet.py
# from __future__ import annotations

# from datetime import date
# import numpy as np
# import pandas as pd
# from prophet import Prophet

# from .formatters import fmt_money, fmt_delta_money, fmt_delta_pct


# RU_MON_3 = {
#     1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр",
#     5: "Май", 6: "Июн", 7: "Июл", 8: "Авг",
#     9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
# }


# def month_label_ru3(dt: pd.Timestamp) -> str:
#     dt = pd.to_datetime(dt)
#     return f"{RU_MON_3[int(dt.month)]} {int(dt.year)}"


# def _monthly_mape(df: pd.DataFrame, cut_date: pd.Timestamp) -> float | None:
#     """
#     MAPE по МЕСЯЦАМ:
#     агрегируем факт (y) и прогноз (yhat) по месяцу и считаем среднюю % ошибку.
#     """
#     d = df[df["ds"] <= cut_date].copy()
#     if d.empty:
#         return None

#     d["month"] = pd.to_datetime(d["ds"]).dt.to_period("M").dt.to_timestamp("M")

#     monthly = (
#         d.groupby("month", as_index=False)[["y", "yhat"]]
#         .sum()
#         .sort_values("month")
#     )

#     monthly = monthly[monthly["y"] != 0]
#     if monthly.empty:
#         return None

#     ape = np.abs(monthly["y"] - monthly["yhat"]) / np.abs(monthly["y"])
#     v = float(np.nanmean(ape) * 100) if np.isfinite(np.nanmean(ape)) else None
#     return v


# def _month_sum(series: pd.Series, ms: pd.Timestamp, me: pd.Timestamp) -> float:
#     s = series[(series.index >= ms) & (series.index <= me)]
#     return float(s.sum()) if len(s) else 0.0




# def build_prophet_eom_projection(
#     df_daily: pd.DataFrame,
#     report_date: date,
#     historical_cut_off: date | None = None,
#     yearly_seasonality: bool = True,
#     weekly_seasonality: bool = True,
#     seasonality_mode: str = "additive",
#     changepoint_prior_scale: float = 0.05,
#     changepoint_range: float = 1.0,
#     n_changepoints: int = 25,
# ) -> dict:
#     if df_daily is None or df_daily.empty:
#         return {"has_data": False, "note": "Нет данных для прогноза."}

#     df = df_daily.copy()
#     df["ds"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
#     df["y"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

#     df = (
#         df[["ds", "y"]]
#         .dropna(subset=["ds"])
#         .groupby("ds", as_index=False)["y"]
#         .sum()
#         .sort_values("ds")
#     )

#     current_date = pd.to_datetime(report_date).normalize()

#     if historical_cut_off:
#         hco = pd.to_datetime(historical_cut_off).normalize()
#         df = df[df["ds"] >= hco].copy()

#     # ✅ защита: не обучаемся на датах позже report_date
#     df = df[df["ds"] <= current_date].copy()

#     if len(df) < 30:
#         return {"has_data": False, "note": "Недостаточно истории для Prophet (нужно хотя бы ~30 дней)."}

#     # горизонты месяца
#     this_eom = (current_date + pd.offsets.MonthEnd(0)).normalize()
#     ms = current_date.replace(day=1)
#     is_month_closed = current_date >= this_eom

#     # --- fit "today" (для стандартной части: EOM/M+1/M+2 + MAPE) ---
#     model = Prophet(
#         yearly_seasonality=yearly_seasonality,
#         weekly_seasonality=weekly_seasonality,
#         seasonality_mode=seasonality_mode,
#         growth="linear",
#         changepoint_prior_scale=changepoint_prior_scale,
#         changepoint_range=changepoint_range,
#         n_changepoints=n_changepoints,
#     )
#     model.fit(df)

#     # прогноз до конца года (как у тебя было) — чтобы и FY-график не ломался
#     year_end = pd.Timestamp(year=int(current_date.year), month=12, day=31).normalize()
#     num_days = int((year_end - current_date).days)
#     future = model.make_future_dataframe(periods=max(num_days, 0))
#     fc = model.predict(future)[["ds", "yhat"]].copy()
#     yhat = fc.set_index("ds")["yhat"]

#     # # факт MTD
#     # mtd_actual = float(df[(df["ds"] >= ms) & (df["ds"] <= current_date)]["y"].sum())

#     # # прогноз суммы месяца (на текущую дату)
#     # eom_forecast = _month_sum(yhat, ms, this_eom)
    
    
#     # факт MTD
#     mtd_actual = float(df[(df["ds"] >= ms) & (df["ds"] <= current_date)]["y"].sum())

#     # прогноз только на оставшиеся дни месяца
#     rest_start = (current_date + pd.Timedelta(days=1)).normalize()
#     rest_forecast = _month_sum(yhat, rest_start, this_eom)

#     # прогноз закрытия месяца = факт MTD + прогноз остатка
#     eom_forecast = mtd_actual + rest_forecast

#     # gap до закрытия
#     if is_month_closed:
#         # факт за месяц
#         eom_fact = float(df[(df["ds"] >= ms) & (df["ds"] <= this_eom)]["y"].sum())
#         eom_forecast_display = eom_fact  # показываем факт, а не прогноз
#         gap = 0.0
#         gap_pct = 0.0
#     else:
#         eom_fact = None
#         eom_forecast_display = eom_forecast
#         gap = eom_forecast - mtd_actual
#         gap_pct = (gap / eom_forecast * 100) if eom_forecast else None

#     # --- M+1 и M+2 ---
#     m1_eom = (this_eom + pd.offsets.MonthEnd(1)).normalize()
#     m2_eom = (this_eom + pd.offsets.MonthEnd(2)).normalize()
#     m1_ms = (this_eom + pd.offsets.Day(1)).normalize()
#     m2_ms = (m1_eom + pd.offsets.Day(1)).normalize()

#     m1_forecast = _month_sum(yhat, m1_ms, m1_eom)
#     m2_forecast = _month_sum(yhat, m2_ms, m2_eom)

#     # --- MAPE по месяцам ---
#     tmp = df.merge(fc, on="ds", how="left")
#     mape_total = _monthly_mape(tmp, current_date)

#     # подписи месяцев
#     m1_label = month_label_ru3(m1_ms)
#     m2_label = month_label_ru3(m2_ms)


# # ============================================================
# # ✅ EOM-оценка качества прогноза: только "на старт месяца"
# # ============================================================
#     eom_accuracy = None

#     if is_month_closed and eom_fact is not None:
#         # прогноз "на старт месяца" = модель знает данные до конца предыдущего дня
#         asof_start = (ms - pd.offsets.Day(1)).normalize()
#         df_start = df[df["ds"] <= asof_start].copy()

#         forecast_start = None
#         if len(df_start) >= 30:
#             m_start = Prophet(
#                 yearly_seasonality=yearly_seasonality,
#                 weekly_seasonality=weekly_seasonality,
#                 seasonality_mode=seasonality_mode,
#                 growth="linear",
#                 changepoint_prior_scale=changepoint_prior_scale,
#                 changepoint_range=changepoint_range,
#                 n_changepoints=n_changepoints,
#             )
#             m_start.fit(df_start)

#             periods_start = int((this_eom - asof_start).days)
#             fut_start = m_start.make_future_dataframe(periods=max(periods_start, 0))
#             fc_start = m_start.predict(fut_start)[["ds", "yhat"]].copy()
#             yhat_start = fc_start.set_index("ds")["yhat"]

#             # сумма прогноза именно за текущий месяц
#             forecast_start = _month_sum(yhat_start, ms, this_eom)

#         def _err(forecast_val: float | None, fact_val: float) -> dict | None:
#             if forecast_val is None:
#                 return None
#             err_abs = forecast_val - fact_val  # >0 завысили
#             err_pct = (err_abs / fact_val * 100) if fact_val else None
#             return {
#                 "forecast_raw": float(forecast_val),
#                 "forecast": fmt_money(float(forecast_val)),
#                 "err_abs_raw": float(err_abs),
#                 "err_abs": fmt_delta_money(float(err_abs)),
#                 "err_pct_raw": float(err_pct) if err_pct is not None else None,
#                 "err_pct": fmt_delta_pct(float(err_pct)) if err_pct is not None else "—",
#             }

#         eom_accuracy = {
#             "fact_raw": float(eom_fact),
#             "fact": fmt_money(float(eom_fact)),
#             "target_month": month_label_ru3(ms), 
#             "calc_date": asof_start.date(),     
#             "asof_start": ms.date(),             
#             "start": _err(forecast_start, eom_fact),
#         }

#     return {
#         "has_data": True,
#         "current_date": current_date.date(),

#         "eom": this_eom.date(),
#         "m1_eom": m1_eom.date(),
#         "m2_eom": m2_eom.date(),

#         "mtd_actual_raw": mtd_actual,
#         "eom_forecast_raw": float(eom_forecast_display),
#         "gap_raw": gap,
#         "gap_pct_raw": gap_pct,

#         "m1_forecast_raw": m1_forecast,
#         "m2_forecast_raw": m2_forecast,

#         "mtd_actual": fmt_money(mtd_actual),
#         "eom_forecast": fmt_money(float(eom_forecast_display)),
#         "gap": fmt_delta_money(gap),
#         "gap_pct": fmt_delta_pct(gap_pct),

#         "m1_label": m1_label,
#         "m2_label": m2_label,
#         "m1_forecast": fmt_money(m1_forecast),
#         "m2_forecast": fmt_money(m2_forecast),

#         "is_month_closed": bool(is_month_closed),
#         "gap_title": "Месяц закрыт" if is_month_closed else "Осталось добрать",

#         "mape_total": (
#             f"{mape_total:,.1f}%".replace(",", " ").replace(".", ",")
#             if mape_total is not None else "—"
#         ),

#         # ✅ новая секция
#         "eom_accuracy": eom_accuracy,

#         "note": (
#             "Прогноз: Prophet на дневной выручке. EOM — прогноз закрытия текущего месяца, "
#             "M+1/M+2 — суммы по следующим месяцам. MAPE рассчитан по месяцам."
#         ),
#         "_forecast_df": fc,
#     }




from __future__ import annotations

from datetime import date
import numpy as np
import pandas as pd
from prophet import Prophet

from .formatters import fmt_money, fmt_delta_money, fmt_delta_pct


RU_MON_3 = {
    1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр",
    5: "Май", 6: "Июн", 7: "Июл", 8: "Авг",
    9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
}


def month_label_ru3(dt: pd.Timestamp) -> str:
    dt = pd.to_datetime(dt)
    return f"{RU_MON_3[int(dt.month)]} {int(dt.year)}"


def _monthly_mape(df: pd.DataFrame, cut_date: pd.Timestamp) -> float | None:
    """
    MAPE по МЕСЯЦАМ:
    агрегируем факт (y) и прогноз (yhat) по месяцу и считаем среднюю % ошибку.
    """
    d = df[df["ds"] <= cut_date].copy()
    if d.empty:
        return None

    d["month"] = pd.to_datetime(d["ds"]).dt.to_period("M").dt.to_timestamp("M")

    monthly = (
        d.groupby("month", as_index=False)[["y", "yhat"]]
        .sum()
        .sort_values("month")
    )

    monthly = monthly[monthly["y"] != 0]
    if monthly.empty:
        return None

    ape = np.abs(monthly["y"] - monthly["yhat"]) / np.abs(monthly["y"])
    v = float(np.nanmean(ape) * 100) if np.isfinite(np.nanmean(ape)) else None
    return v


def _month_sum(series: pd.Series, ms: pd.Timestamp, me: pd.Timestamp) -> float:
    s = series[(series.index >= ms) & (series.index <= me)]
    return float(s.sum()) if len(s) else 0.0


def build_prophet_eom_projection(
    df_daily: pd.DataFrame,
    report_date: date,
    historical_cut_off: date | None = None,
    yearly_seasonality: bool = True,
    weekly_seasonality: bool = True,
    seasonality_mode: str = "additive",
    changepoint_prior_scale: float = 0.05,
    changepoint_range: float = 1.0,
    n_changepoints: int = 25,
) -> dict:
    if df_daily is None or df_daily.empty:
        return {"has_data": False, "note": "Нет данных для прогноза."}

    df = df_daily.copy()
    df["ds"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["y"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    df = (
        df[["ds", "y"]]
        .dropna(subset=["ds"])
        .groupby("ds", as_index=False)["y"]
        .sum()
        .sort_values("ds")
    )

    current_date = pd.to_datetime(report_date).normalize()

    if historical_cut_off:
        hco = pd.to_datetime(historical_cut_off).normalize()
        df = df[df["ds"] >= hco].copy()

    # не обучаемся на датах позже report_date
    df = df[df["ds"] <= current_date].copy()

    if len(df) < 30:
        return {"has_data": False, "note": "Недостаточно истории для Prophet (нужно хотя бы ~30 дней)."}

    # границы текущего месяца
    this_eom = (current_date + pd.offsets.MonthEnd(0)).normalize()
    ms = current_date.replace(day=1)
    is_month_closed = current_date >= this_eom

    # --- fit "today" (EOM / M+1 / M+2 / MAPE) ---
    model = Prophet(
        yearly_seasonality=yearly_seasonality,
        weekly_seasonality=weekly_seasonality,
        seasonality_mode=seasonality_mode,
        growth="linear",
        changepoint_prior_scale=changepoint_prior_scale,
        changepoint_range=changepoint_range,
        n_changepoints=n_changepoints,
    )
    model.fit(df)

    # Прогноз до конца года, чтобы хватило и на EOM, и на M+1/M+2, и на FY-графики
    year_end = pd.Timestamp(year=int(current_date.year), month=12, day=31).normalize()
    num_days = int((year_end - current_date).days)
    future = model.make_future_dataframe(periods=max(num_days, 0))
    fc = model.predict(future)[["ds", "yhat"]].copy()
    yhat = fc.set_index("ds")["yhat"]

    # факт MTD: с 1-го числа месяца по report_date
    mtd_actual = float(df[(df["ds"] >= ms) & (df["ds"] <= current_date)]["y"].sum())

    # прогноз только на оставшиеся дни месяца
    rest_start = (current_date + pd.Timedelta(days=1)).normalize()
    rest_forecast = _month_sum(yhat, rest_start, this_eom)

    # прогноз закрытия месяца = факт MTD + прогноз на остаток
    eom_forecast = mtd_actual + rest_forecast

    # Что показывать в EOM-блоке
    if is_month_closed:
        eom_fact = float(df[(df["ds"] >= ms) & (df["ds"] <= this_eom)]["y"].sum())
        eom_forecast_display = eom_fact
        rest_forecast = 0.0
        gap = 0.0
        gap_pct = 0.0
    else:
        eom_fact = None
        eom_forecast_display = eom_forecast
        gap = rest_forecast
        gap_pct = (gap / eom_forecast * 100) if eom_forecast else None

    # --- M+1 и M+2 ---
    m1_eom = (this_eom + pd.offsets.MonthEnd(1)).normalize()
    m2_eom = (this_eom + pd.offsets.MonthEnd(2)).normalize()
    m1_ms = (this_eom + pd.offsets.Day(1)).normalize()
    m2_ms = (m1_eom + pd.offsets.Day(1)).normalize()

    m1_forecast = _month_sum(yhat, m1_ms, m1_eom)
    m2_forecast = _month_sum(yhat, m2_ms, m2_eom)

    # --- MAPE по месяцам ---
    tmp = df.merge(fc, on="ds", how="left")
    mape_total = _monthly_mape(tmp, current_date)

    # подписи месяцев
    m1_label = month_label_ru3(m1_ms)
    m2_label = month_label_ru3(m2_ms)

    # ============================================================
    # EOM-оценка качества прогноза: прогноз "на старт месяца"
    # ============================================================
    eom_accuracy = None

    if is_month_closed and eom_fact is not None:
        # Модель знает данные только до конца предыдущего дня перед стартом месяца
        asof_start = (ms - pd.offsets.Day(1)).normalize()
        df_start = df[df["ds"] <= asof_start].copy()

        forecast_start = None
        if len(df_start) >= 30:
            m_start = Prophet(
                yearly_seasonality=yearly_seasonality,
                weekly_seasonality=weekly_seasonality,
                seasonality_mode=seasonality_mode,
                growth="linear",
                changepoint_prior_scale=changepoint_prior_scale,
                changepoint_range=changepoint_range,
                n_changepoints=n_changepoints,
            )
            m_start.fit(df_start)

            periods_start = int((this_eom - asof_start).days)
            fut_start = m_start.make_future_dataframe(periods=max(periods_start, 0))
            fc_start = m_start.predict(fut_start)[["ds", "yhat"]].copy()
            yhat_start = fc_start.set_index("ds")["yhat"]

            # Здесь логика правильная: нужен прогноз на ВЕСЬ месяц, потому что это прогноз на старт месяца
            forecast_start = _month_sum(yhat_start, ms, this_eom)

        def _err(forecast_val: float | None, fact_val: float) -> dict | None:
            if forecast_val is None:
                return None

            err_abs = forecast_val - fact_val  # > 0 = завысили
            err_pct = (err_abs / fact_val * 100) if fact_val else None

            return {
                "forecast_raw": float(forecast_val),
                "forecast": fmt_money(float(forecast_val)),
                "err_abs_raw": float(err_abs),
                "err_abs": fmt_delta_money(float(err_abs)),
                "err_pct_raw": float(err_pct) if err_pct is not None else None,
                "err_pct": fmt_delta_pct(float(err_pct)) if err_pct is not None else "—",
            }

        eom_accuracy = {
            "fact_raw": float(eom_fact),
            "fact": fmt_money(float(eom_fact)),
            "target_month": month_label_ru3(ms),
            "calc_date": asof_start.date(),
            "asof_start": ms.date(),
            "start": _err(forecast_start, eom_fact),
        }

    return {
        "has_data": True,
        "current_date": current_date.date(),

        "eom": this_eom.date(),
        "m1_eom": m1_eom.date(),
        "m2_eom": m2_eom.date(),

        "mtd_actual_raw": mtd_actual,
        "rest_forecast_raw": rest_forecast,
        "eom_forecast_raw": float(eom_forecast_display),
        "gap_raw": gap,
        "gap_pct_raw": gap_pct,

        "m1_forecast_raw": m1_forecast,
        "m2_forecast_raw": m2_forecast,

        "mtd_actual": fmt_money(mtd_actual),
        "rest_forecast": fmt_money(rest_forecast),
        "eom_forecast": fmt_money(float(eom_forecast_display)),
        "gap": fmt_delta_money(gap),
        "gap_pct": fmt_delta_pct(gap_pct),

        "m1_label": m1_label,
        "m2_label": m2_label,
        "m1_forecast": fmt_money(m1_forecast),
        "m2_forecast": fmt_money(m2_forecast),

        "is_month_closed": bool(is_month_closed),
        "gap_title": "Месяц закрыт" if is_month_closed else "Осталось добрать",

        "mape_total": (
            f"{mape_total:,.1f}%".replace(",", " ").replace(".", ",")
            if mape_total is not None else "—"
        ),

        "eom_accuracy": eom_accuracy,

        "note": (
            "Прогноз: Prophet на дневной выручке. "
            "EOM = факт MTD + прогноз на оставшиеся дни текущего месяца. "
            "M+1/M+2 — суммы по следующим месяцам. MAPE рассчитан по месяцам."
        ),
        "_forecast_df": fc,
    }
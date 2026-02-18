# sales/reports/sales_report/ltm_forecast_prophet.py
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
    """
    Возвращает:
      - MTD факт
      - прогноз закрытия текущего месяца (EOM)
      - gap до EOM
      - MAPE (по месяцам)
      - прогноз на 2 следующих месяца (сумма по месяцу)
    """
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

    if len(df) < 30:
        return {
            "has_data": False,
            "note": "Недостаточно истории для Prophet (нужно хотя бы ~30 дней).",
        }

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

    # # --- горизонты: EOM + 2 месяца вперёд ---
    # this_eom = (current_date + pd.offsets.MonthEnd(0)).normalize()
    # m1_eom = (this_eom + pd.offsets.MonthEnd(1)).normalize()
    # m2_eom = (this_eom + pd.offsets.MonthEnd(2)).normalize()

    # # сколько дней прогнозируем вперёд до конца M+2
    # num_days = int((m2_eom - current_date).days)
    # future = model.make_future_dataframe(periods=max(num_days, 0))
    # fc = model.predict(future)[["ds", "yhat"]].copy()
    
    
    # --- горизонты: EOM + 2 месяца вперёд (для карточек) ---
    this_eom = (current_date + pd.offsets.MonthEnd(0)).normalize()
    m1_eom = (this_eom + pd.offsets.MonthEnd(1)).normalize()
    m2_eom = (this_eom + pd.offsets.MonthEnd(2)).normalize()

    # ✅ ДО КОНЦА ГОДА (для графика FY)
    year_end = pd.Timestamp(year=int(current_date.year), month=12, day=31).normalize()

    # сколько дней прогнозируем вперёд: ДО КОНЦА ГОДА
    num_days = int((year_end - current_date).days)
    future = model.make_future_dataframe(periods=max(num_days, 0))
    fc = model.predict(future)[["ds", "yhat"]].copy()

    # серия прогнозов для удобных срезов
    yhat = fc.set_index("ds")["yhat"]

    # --- текущий месяц: факт MTD и прогноз EOM ---
    ms = current_date.replace(day=1)

    mtd_actual = float(df[(df["ds"] >= ms) & (df["ds"] <= current_date)]["y"].sum())
    eom_forecast = _month_sum(yhat, ms, this_eom)

    gap = eom_forecast - mtd_actual
    gap_pct = (gap / eom_forecast * 100) if eom_forecast else None

    # --- M+1 и M+2 месяцы (полные суммы по прогнозу) ---
    m1_ms = (this_eom + pd.offsets.Day(1)).normalize()
    m2_ms = (m1_eom + pd.offsets.Day(1)).normalize()

    m1_forecast = _month_sum(yhat, m1_ms, m1_eom)
    m2_forecast = _month_sum(yhat, m2_ms, m2_eom)

    # --- точность: MAPE по месяцам (на истории до current_date) ---
    tmp = df.merge(fc, on="ds", how="left")
    mape_total = _monthly_mape(tmp, current_date)

    # подписи месяцев (чтобы красиво вывести в табе)
    m1_label = month_label_ru3(m1_ms)
    m2_label = month_label_ru3(m2_ms)


    return {
        "has_data": True,
        "current_date": current_date.date(),

        "eom": this_eom.date(),
        "m1_eom": m1_eom.date(),
        "m2_eom": m2_eom.date(),

        "mtd_actual_raw": mtd_actual,
        "eom_forecast_raw": eom_forecast,
        "gap_raw": gap,
        "gap_pct_raw": gap_pct,

        "m1_forecast_raw": m1_forecast,
        "m2_forecast_raw": m2_forecast,

        "mtd_actual": fmt_money(mtd_actual),
        "eom_forecast": fmt_money(eom_forecast),
        "gap": fmt_delta_money(gap),
        "gap_pct": fmt_delta_pct(gap_pct),

        "m1_label": m1_label,
        "m2_label": m2_label,
        "m1_forecast": fmt_money(m1_forecast),
        "m2_forecast": fmt_money(m2_forecast),

        "mape_total": (
            f"{mape_total:,.1f}%".replace(",", " ").replace(".", ",")
            if mape_total is not None else "—"
        ),

        "note": "Прогноз: Prophet на дневной выручке. EOM — прогноз закрытия текущего месяца, M+1/M+2 — суммы по следующим месяцам. MAPE рассчитан по месяцам.",
         "_forecast_df": fc, 
    }

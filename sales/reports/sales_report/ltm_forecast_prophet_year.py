from __future__ import annotations

from datetime import date, timedelta
import numpy as np
import pandas as pd
from prophet import Prophet

from .formatters import fmt_money, fmt_delta_money, fmt_delta_pct


def _prepare_daily(df_daily: pd.DataFrame) -> pd.DataFrame:
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
    return df


def _month_mape(df_fact: pd.DataFrame, df_fc: pd.DataFrame, cut_date: pd.Timestamp) -> float | None:
    """
    MAPE по месяцам на истории (до cut_date). Это ровно твоя логика из _monthly_mape,
    но вынесена сюда чтобы не плодить импортов.
    """
    d = df_fact.merge(df_fc, on="ds", how="left")
    d = d[d["ds"] <= cut_date].copy()
    if d.empty:
        return None

    d["month"] = pd.to_datetime(d["ds"]).dt.to_period("M").dt.to_timestamp("M")
    monthly = d.groupby("month", as_index=False)[["y", "yhat"]].sum().sort_values("month")
    monthly = monthly[monthly["y"] != 0]
    if monthly.empty:
        return None

    ape = np.abs(monthly["y"] - monthly["yhat"]) / np.abs(monthly["y"])
    m = float(np.nanmean(ape) * 100) if np.isfinite(np.nanmean(ape)) else None
    return m


def _fit_and_predict(
    df: pd.DataFrame,
    report_dt: pd.Timestamp,
    yearly_seasonality: bool,
    weekly_seasonality: bool,
    seasonality_mode: str,
    changepoint_prior_scale: float,
    changepoint_range: float,
    n_changepoints: int,
) -> pd.DataFrame:
    """
    Fit Prophet on df (ds,y) and return daily forecast (ds,yhat) up to year-end.
    """
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

    year_end = pd.Timestamp(year=report_dt.year, month=12, day=31).normalize()
    periods = int((year_end - report_dt).days)
    future = model.make_future_dataframe(periods=max(periods, 0))
    fc = model.predict(future)[["ds", "yhat"]].copy()
    return fc


def _sum_between(series: pd.Series, d1: pd.Timestamp, d2: pd.Timestamp) -> float:
    s = series[(series.index >= d1) & (series.index <= d2)]
    return float(s.sum()) if len(s) else 0.0


def build_prophet_fy_vector(
    df_daily: pd.DataFrame,
    report_date: date,
    historical_cut_off: date | None = None,

    yearly_seasonality: bool = True,
    weekly_seasonality: bool = True,
    seasonality_mode: str = "additive",
    changepoint_prior_scale: float = 0.05,
    changepoint_range: float = 1.0,
    n_changepoints: int = 25,

    # сравнение с вчерашним
    compare_with_yesterday: bool = True,

    # “лента” вектора: сколько дней показать (просто данные для шаблона)
    last_n_days: int = 14,
) -> dict:
    """
    Ежедневный “вектор” годового прогноза:
      - FY forecast (сумма по году)
      - Remaining to go (до конца года)
      - Δ vs yesterday (изменение годового прогноза)
      - MAPE по месяцам (на истории до report_date)
      - mini series (последние N дней) — чтобы рисовать тренд (без хранения в БД, считаем “на лету”)

    Важно: mini series тут считается повторным обучением модели на каждую дату,
    это O(N) фиттов. N=14 обычно ок. Если захочешь идеальный перфоманс — лучше сохранять снапшоты в БД.
    """
    if df_daily is None or df_daily.empty:
        return {"has_data": False, "note": "Нет данных для годового прогноза."}

    df0 = _prepare_daily(df_daily)
    report_dt = pd.to_datetime(report_date).normalize()

    if historical_cut_off:
        hco = pd.to_datetime(historical_cut_off).normalize()
        df0 = df0[df0["ds"] >= hco].copy()

    # чтобы Prophet вообще имел смысл
    if len(df0) < 60:
        return {"has_data": False, "note": "Недостаточно истории для годового прогноза (желательно 60+ дней)."}

    # ограничиваем факт датой отчёта (важно для стабильной логики)
    df = df0[df0["ds"] <= report_dt].copy()
    if df.empty or len(df) < 60:
        return {"has_data": False, "note": "Недостаточно истории до даты отчёта."}

    # --- fit today ---
    fc = _fit_and_predict(
        df=df,
        report_dt=report_dt,
        yearly_seasonality=yearly_seasonality,
        weekly_seasonality=weekly_seasonality,
        seasonality_mode=seasonality_mode,
        changepoint_prior_scale=changepoint_prior_scale,
        changepoint_range=changepoint_range,
        n_changepoints=n_changepoints,
    )
    yhat = fc.set_index("ds")["yhat"]

    year_start = pd.Timestamp(year=report_dt.year, month=1, day=1).normalize()
    year_end = pd.Timestamp(year=report_dt.year, month=12, day=31).normalize()

    # факт YTD (только в пределах года)
    ytd_actual = float(df[(df["ds"] >= year_start) & (df["ds"] <= report_dt)]["y"].sum())

    # прогноз FY = факт до report_dt (внутри года) + прогноз после report_dt до 31.12
    # Чтобы было “честно”: берем прогноз на весь год (yhat) и не смешиваем двойной учет:
    # проще: FY = ytd_actual + sum(yhat[report_dt+1..year_end])
    remain_start = (report_dt + pd.Timedelta(days=1)).normalize()
    remaining_forecast = _sum_between(yhat, remain_start, year_end)
    fy_forecast = ytd_actual + remaining_forecast

    # MAPE по месяцам (на истории до report_dt) — не зависит от горизонта
    mape_total = _month_mape(df, fc, report_dt)

    # --- сравнение с вчерашним ---
    fy_yesterday = None
    d_fy = None
    d_fy_pct = None
    vector_dir = "flat"
    vector_text = "без изменения"

    if compare_with_yesterday:
        yday = (report_dt - pd.Timedelta(days=1)).normalize()
        df_y = df0[df0["ds"] <= yday].copy()
        if len(df_y) >= 60:
            fc_y = _fit_and_predict(
                df=df_y,
                report_dt=yday,
                yearly_seasonality=yearly_seasonality,
                weekly_seasonality=weekly_seasonality,
                seasonality_mode=seasonality_mode,
                changepoint_prior_scale=changepoint_prior_scale,
                changepoint_range=changepoint_range,
                n_changepoints=n_changepoints,
            )
            yhat_y = fc_y.set_index("ds")["yhat"]

            ytd_y = float(df_y[(df_y["ds"] >= year_start) & (df_y["ds"] <= yday)]["y"].sum())
            remain_start_y = (yday + pd.Timedelta(days=1)).normalize()
            remaining_y = _sum_between(yhat_y, remain_start_y, year_end)
            fy_yesterday = ytd_y + remaining_y

            d_fy = fy_forecast - fy_yesterday
            d_fy_pct = (d_fy / fy_yesterday * 100) if fy_yesterday else None

            if d_fy > 0:
                vector_dir = "up"
                vector_text = "улучшается (прогноз растёт)"
            elif d_fy < 0:
                vector_dir = "down"
                vector_text = "ухудшается (прогноз снижается)"
            else:
                vector_dir = "flat"
                vector_text = "стабилен"

    # --- mini series: последние N дней (вектор) ---
    # считаем FY forecast на каждую дату, чтобы показать “куда идем”
    # (если начнет тормозить — перенесем в БД снапшотами)
    series = []
    start_series = report_dt - pd.Timedelta(days=max(last_n_days - 1, 0))
    dates = pd.date_range(start_series, report_dt, freq="D")

    for dt in dates:
        dff = df0[df0["ds"] <= dt].copy()
        if len(dff) < 60:
            continue
        fcc = _fit_and_predict(
            df=dff,
            report_dt=dt,
            yearly_seasonality=yearly_seasonality,
            weekly_seasonality=weekly_seasonality,
            seasonality_mode=seasonality_mode,
            changepoint_prior_scale=changepoint_prior_scale,
            changepoint_range=changepoint_range,
            n_changepoints=n_changepoints,
        )
        yh = fcc.set_index("ds")["yhat"]

        ys = pd.Timestamp(year=dt.year, month=1, day=1).normalize()
        ye = pd.Timestamp(year=dt.year, month=12, day=31).normalize()

        ytd = float(dff[(dff["ds"] >= ys) & (dff["ds"] <= dt)]["y"].sum())
        rem = _sum_between(yh, (dt + pd.Timedelta(days=1)).normalize(), ye)
        fy = ytd + rem

        series.append({
            "date": dt.date(),
            "fy_raw": fy,
            "fy": fmt_money(fy),
        })

    return {
        "has_data": True,

        "report_date": report_dt.date(),
        "year": int(report_dt.year),
        "year_end": year_end.date(),

        "ytd_actual_raw": ytd_actual,
        "remaining_forecast_raw": remaining_forecast,
        "fy_forecast_raw": fy_forecast,

        "ytd_actual": fmt_money(ytd_actual),
        "remaining_forecast": fmt_money(remaining_forecast),
        "fy_forecast": fmt_money(fy_forecast),

        "fy_yesterday_raw": fy_yesterday,
        "d_fy_raw": d_fy,
        "d_fy_pct_raw": d_fy_pct,

        "fy_yesterday": fmt_money(fy_yesterday) if fy_yesterday is not None else "—",
        "d_fy": fmt_delta_money(d_fy) if d_fy is not None else "—",
        "d_fy_pct": fmt_delta_pct(d_fy_pct) if d_fy_pct is not None else "—",

        "vector_dir": vector_dir,   # up/down/flat
        "vector_text": vector_text,

        "mape_total": (
            f"{mape_total:,.1f}%".replace(",", " ").replace(".", ",")
            if mape_total is not None else "—"
        ),

        "series": series,  # последние N дней (для динамики)
        "note": "FY прогноз пересчитывается ежедневно. Сравнение — с прогнозом, построенным на данных до вчерашней даты.",
    }

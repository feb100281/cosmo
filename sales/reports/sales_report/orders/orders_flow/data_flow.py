import pandas as pd
import numpy as np


def build_orders_aging(df_orders, period_end):
    """
    Разбивка заказов по возрасту (дней в работе).
    """

    if df_orders.empty:
        return pd.DataFrame()

    df = df_orders.copy()

    df["age_days"] = df["current_order_duration"].astype(float)

    bins = [0, 7, 14, 30, 60, 90, 10_000]
    labels = ["0–7", "8–14", "15–30", "31–60", "61–90", "90+"]

    df["aging_bucket"] = pd.cut(
        df["age_days"],
        bins=bins,
        labels=labels,
        right=True
    )

    aging = (
        df.groupby("aging_bucket", dropna=False)
        .agg(
            orders=("client_order_number", "nunique"),
            amount=("amount_period", "sum")
        )
        .reset_index()
    )

    aging["share"] = aging["amount"] / aging["amount"].sum()

    return aging


def build_execution_speed_metrics(df_orders):
    """
    KPI по скорости исполнения заказов
    """

    if df_orders.empty:
        return {}

    durations = df_orders["current_order_duration"].astype(float)

    return {
        "median_days": int(durations.median()),
        "p75_days": int(durations.quantile(0.75)),
        "p90_days": int(durations.quantile(0.90)),
        "avg_days": int(durations.mean()),
    }

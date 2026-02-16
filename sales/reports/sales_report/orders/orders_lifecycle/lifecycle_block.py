import pandas as pd
from .data_lifecycle import get_orders_lifecycle
from .lifecycle_chart import build_lifecycle_svg


def build_orders_lifecycle_context(period_start, period_end, top_n=8):

    df = get_orders_lifecycle(period_start, period_end)

    if df is None or df.empty:
        return {"has": False}

    # ✅ порядок важен для cumsum
    df = df.sort_values(["orders_id", "ship_date"]).copy()

    # ✅ безопасность типов
    df["orders_id"] = df["orders_id"].fillna(0)
    df["net"] = pd.to_numeric(df["net"], errors="coerce").fillna(0)
    df["age_day"] = pd.to_numeric(df["age_day"], errors="coerce").fillna(0).astype(int)

    # накопленная выручка по каждому заказу
    df["cum_net"] = df.groupby("orders_id")["net"].cumsum()

    # средняя кривая (средняя накопленная выручка на день жизни заказа)
    avg_curve = (
        df.groupby("age_day", as_index=False)["cum_net"]
          .mean()
    )

    # топ заказов по итоговой накопленной выручке
    top_orders = (
        df.groupby("orders_id")["cum_net"]
          .max()
          .sort_values(ascending=False)
          .head(top_n)
          .index
    )

    df_top = df[df["orders_id"].isin(top_orders)]

    svg = build_lifecycle_svg(avg_curve, df_top)

    return {
        "has": True,
        "lifecycle_svg": svg,
    }

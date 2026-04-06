import pandas as pd
from .data_flow import build_orders_aging, build_execution_speed_metrics
from .flow_chart import build_aging_svg
from ...formatters import fmt_money, fmt_int, fmt_pct


def build_orders_flow_context(df_orders):
    if df_orders.empty:
        return {"has": False}

    aging = build_orders_aging(df_orders, None)
    speed = build_execution_speed_metrics(df_orders)

    aging_fmt = pd.DataFrame({
        "Возраст заказ (дней)": aging["aging_bucket"].astype(str),
        "Заказов": aging["orders"].map(fmt_int),
        "Выручка": aging["amount"].map(fmt_money),
        "Доля": aging["share"].map(lambda x: fmt_pct(x * 100)),
    })

    aging_html = aging_fmt.to_html(
        index=False,
        classes="compare-table",
        border=0,
        escape=False,
    )

    aging_svg = build_aging_svg(aging)

    return {
        "has": True,
        "aging_table_html": aging_html,
        "aging_svg": aging_svg,
        "speed": {
            "median": fmt_int(speed["median_days"]),
            "p75": fmt_int(speed["p75_days"]),
            "p90": fmt_int(speed["p90_days"]),
            "avg": fmt_int(speed["avg_days"]),
        }
    }

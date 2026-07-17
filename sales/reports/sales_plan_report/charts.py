# sales/reports/sales_plan_report/charts.py

from decimal import Decimal
import math


CHART_COLORS = [
    "#145c48",
    "#2f7d4f",
    "#4f9b52",
    "#9abd58",
    "#f4b63f",
    "#f28c28",
    "#f45b69",
    "#d71920",
]


def to_float(value):
    return float(value or 0)


def fmt_money_mln(value):
    value = Decimal(str(value or 0))

    if abs(value) >= Decimal("1000000"):
        return f"{float(value / Decimal('1000000')):.2f} млн ₽"

    if abs(value) >= Decimal("1000"):
        return f"{float(value / Decimal('1000')):.0f} тыс. ₽"

    return f"{float(value):.0f} ₽"


def polar_to_cartesian(cx, cy, r, angle_deg):
    angle_rad = math.radians(angle_deg)
    return cx + r * math.cos(angle_rad), cy + r * math.sin(angle_rad)


def donut_segment_path(cx, cy, r_outer, r_inner, start_angle, end_angle):
    large_arc = 1 if end_angle - start_angle > 180 else 0

    x1, y1 = polar_to_cartesian(cx, cy, r_outer, start_angle)
    x2, y2 = polar_to_cartesian(cx, cy, r_outer, end_angle)

    x3, y3 = polar_to_cartesian(cx, cy, r_inner, end_angle)
    x4, y4 = polar_to_cartesian(cx, cy, r_inner, start_angle)

    return (
        f"M {x1:.2f} {y1:.2f} "
        f"A {r_outer} {r_outer} 0 {large_arc} 1 {x2:.2f} {y2:.2f} "
        f"L {x3:.2f} {y3:.2f} "
        f"A {r_inner} {r_inner} 0 {large_arc} 0 {x4:.2f} {y4:.2f} "
        f"Z"
    )


def build_cash_share_chart(rows, total_fact):
    total_fact = Decimal(str(total_fact or 0))

    if total_fact <= 0:
        return {
            "items": [],
            "segments": [],
            "top3": [],
            "top3_share_fmt": "0.0",
            "top3_fact_fmt": "0 ₽",
            "total_fact_mln": "0.00 млн ₽",
        }

    chart_rows = sorted(rows, key=lambda x: x["fact"], reverse=True)

    max_share = max([row["share_pct"] for row in chart_rows] or [Decimal("0")])
    if max_share <= 0:
        max_share = Decimal("1")

    items = []
    segments = []

    start_angle = -90

    for index, row in enumerate(chart_rows):
        color = CHART_COLORS[index % len(CHART_COLORS)]
        share_pct = Decimal(str(row["share_pct"] or 0))

        end_angle = start_angle + to_float(share_pct) / 100 * 360
        mid_angle = (start_angle + end_angle) / 2

        label_x, label_y = polar_to_cartesian(
            cx=160,
            cy=160,
            r=118,
            angle_deg=mid_angle,
        )

        if share_pct > 0:
            segments.append({
                "path": donut_segment_path(
                    cx=160,
                    cy=160,
                    r_outer=145,
                    r_inner=78,
                    start_angle=start_angle,
                    end_angle=end_angle,
                ),
                "color": color,
                "share_pct_fmt": row["share_pct_fmt"],
                "label_x": f"{label_x:.1f}",
                "label_y": f"{label_y:.1f}",
                "show_label": share_pct >= Decimal("5"),
            })

        bar_width = (share_pct / max_share * Decimal("100")).quantize(
            Decimal("0.1")
        )

        items.append({
            "store_name": row["store_name"],
            "fact_fmt": row["fact_fmt"],
            "fact_short": fmt_money_mln(row["fact"]),
            "share_pct_fmt": row["share_pct_fmt"],
            "bar_width": bar_width,
            "color": color,
        })

        start_angle = end_angle

    top3 = items[:3]
    top3_fact = sum(
        [chart_rows[i]["fact"] for i in range(min(3, len(chart_rows)))],
        Decimal("0"),
    )
    top3_share = top3_fact / total_fact * Decimal("100")

    return {
        "items": items,
        "segments": segments,
        "top3": top3,
        "top3_share_fmt": f"{float(top3_share):.1f}",
        "top3_fact_fmt": fmt_money_mln(top3_fact),
        "total_fact_mln": fmt_money_mln(total_fact),
    }
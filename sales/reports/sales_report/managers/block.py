import pandas as pd
from datetime import timedelta

from .data import (
    get_mtd_managers_shipments_bundle,
    get_ytd_managers_shipments_bundle,
)

from ..formatters import (
    fmt_money, fmt_int, fmt_pct,
    fmt_rub, fmt_delta_rub,
)
from .chart import build_managers_bar_svg

NBSP = "\u00A0"


def _safe_div(a, b):
    try:
        a = float(a)
        b = float(b)
    except Exception:
        return None
    if b == 0:
        return None
    return a / b


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    for c in ("amount", "dt", "cr", "quant", "orders_with_shipments", "orders_100k"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def _index_by(df: pd.DataFrame):
    if df is None or df.empty:
        return {}
    return {(r["manager_id"], r["manager_name"]): r for _, r in df.iterrows()}


def _split_manager_name(full: str) -> dict:
    """
    В таблице:
      1 строка — Фамилия
      2 строка — Имя (+ Отчество если есть)
    """
    full = (full or "Без менеджера").strip()
    parts = [p for p in full.split() if p]
    if not parts:
        return {"l1": "Без", "l2": "менеджера"}
    if len(parts) == 1:
        return {"l1": parts[0], "l2": ""}
    return {"l1": parts[0], "l2": " ".join(parts[1:])}


def _fmt_money_mln2(v: float) -> str:
    """
    Для "Чистая выручка": 2 знака после запятой в млн.
    NBSP + неразрывный ₽.
    """
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"

    av = abs(v)
    if av >= 1_000_000:
        s = f"{v / 1_000_000:,.2f}".replace(",", NBSP).replace(".", ",")
        return f"{s}{NBSP}млн{NBSP}₽"

    return fmt_money(v)


def _rr_class(rr: float | None, warn: float, crit: float) -> str:
    """
    Для подсветки возвратного % (бейдж).
    """
    if rr is None:
        return "rr-na"
    if rr >= crit:
        return "rr-crit"
    if rr >= warn:
        return "rr-warn"
    return "rr-ok"


def _build_rows(
    cur: pd.DataFrame,
    ly: pd.DataFrame,
    pm: pd.DataFrame | None,
    return_warn_pct: float = 5.5,
    return_crit_pct: float = 8.0,
) -> dict:
    cur = _prep(cur)
    ly = _prep(ly)
    pm = _prep(pm) if pm is not None else pd.DataFrame()

    if cur.empty:
        return {"rows": [], "total": {}, "insights": []}

    # сортировка по чистой выручке
    cur = cur.sort_values("amount", ascending=False)

    pm_map = _index_by(pm)

    total_amount = float(cur["amount"].sum()) or 0.0
    total_dt = float(cur["dt"].sum()) or 0.0
    total_cr = float(cur["cr"].sum()) or 0.0
    total_orders = float(cur["orders_with_shipments"].sum()) or 0.0

    total_aov = _safe_div(total_dt, total_orders)
    total_rr = (_safe_div(total_cr, total_dt) * 100) if total_dt else None

    rows = []

    rr_list = []
    aov_list = []
    mom_list = []
    orders_list = []

    for _, r in cur.iterrows():
        key = (r["manager_id"], r["manager_name"])
        prev = pm_map.get(key)

        name = r["manager_name"]
        curr_amount = float(r["amount"])
        curr_dt = float(r["dt"])
        curr_cr = float(r["cr"])
        curr_orders = float(r["orders_with_shipments"]) or 0.0

        # средний чек (по обороту)
        aov = _safe_div(curr_dt, curr_orders)

        # прошлый месяц (по тем же дням)
        aov_prev = _safe_div(float(prev["dt"]), float(prev["orders_with_shipments"])) if prev is not None else None

        # MoM абсолют
        d_aov_abs = (aov - aov_prev) if (aov is not None and aov_prev is not None) else None

        # возвратный %
        rr = (_safe_div(curr_cr, curr_dt) * 100) if curr_dt else None
        rr_cls = _rr_class(rr, return_warn_pct, return_crit_pct)

        row_flag = ""
        if rr is not None:
            if rr >= return_crit_pct:
                row_flag = "crit"
            elif rr >= return_warn_pct:
                row_flag = "warn"

        nm = _split_manager_name(name)
        share = (curr_amount / total_amount * 100) if total_amount else 0.0

        rows.append({
            "manager_l1": nm["l1"],
            "manager_l2": nm["l2"],

            "amount": _fmt_money_mln2(curr_amount),
            "orders_with_shipments": fmt_int(curr_orders),

            "cr": fmt_money(curr_cr),
            "return_rate": fmt_pct(rr),
            "rr_class": rr_cls,
            "row_flag": row_flag,

            "aov": fmt_rub(aov) if aov is not None else "—",
            "aov_prev": fmt_rub(aov_prev) if aov_prev is not None else "—",
            "delta_aov_abs": fmt_delta_rub(d_aov_abs) if d_aov_abs is not None else "—",
            "mom_dir": (
                "pos" if (d_aov_abs or 0) > 0
                else "neg" if (d_aov_abs or 0) < 0
                else "flat"
            ) if d_aov_abs is not None else "na",

            "share": share,
        })

        if rr is not None:
            rr_list.append((name, rr, curr_dt, curr_cr))

        if aov is not None:
            aov_list.append((name, aov))
        if d_aov_abs is not None and aov_prev is not None and aov is not None:
            mom_list.append((name, d_aov_abs, aov_prev, aov))
        orders_list.append((name, curr_orders))

    insights = []
    n_mgr = len(cur.index)

    # 70% концентрация
    target = 70.0
    cum = 0.0
    k70 = 0
    for v in cur["amount"].tolist():
        if total_amount <= 0:
            break
        cum += float(v) / total_amount * 100
        k70 += 1
        if cum >= target:
            break

    leader = cur.iloc[0]
    leader_share = (float(leader["amount"]) / (total_amount or 1) * 100)

    insights.append({
        "title": "Краткое резюме",
        "items": [
            f"Менеджеров в отчётном периоде: <b>{n_mgr}</b>.",
            f"Чистая выручка (итого): <b>{_fmt_money_mln2(total_amount)}</b>.",
            f"Концентрация: <b>{target:.0f}%</b> чистой выручки формируют <b>{k70}</b> менеджер(ов).",
            f"Лидер по чистой выручке: <b>{leader['manager_name']}</b> — <b>{_fmt_money_mln2(float(leader['amount']))}</b> "
            f"(<b>{fmt_pct(leader_share, digits=1)}</b> от итога).",
        ]
    })

    if total_rr is not None:
        quality_items = [
            f"Средний возвратный процент: <b>{fmt_pct(total_rr)}</b> (возвраты / оборот).",
        ]

        if rr_list:
            top_rr = sorted(rr_list, key=lambda x: x[1], reverse=True)[:3]
            quality_items.append(
                "Максимальный возвратный %: " +
                "; ".join([f"<b>{n}</b> — <b>{fmt_pct(v)}</b>" for n, v, _, _ in top_rr]) + "."
            )

        insights.append({
            "title": "Качество продаж (возвраты)",
            "items": quality_items
        })

    return {
        "rows": rows,
        "total": {
            "amount": _fmt_money_mln2(total_amount),
            "cr": fmt_money(total_cr),
            "orders_with_shipments": fmt_int(total_orders),
            "aov": fmt_rub(total_aov) if total_aov is not None else "—",
            "return_rate": fmt_pct(total_rr),
        },
        "insights": insights,
    }


def build_managers_shipments_context(
    d,
    big_order_threshold: int = 100_000,
    return_warn_pct: float = 5.5,
    return_crit_pct: float = 8.0,
) -> dict:
    d = pd.to_datetime(d).date()

    mtd = get_mtd_managers_shipments_bundle(d, big_order_threshold=big_order_threshold)
    ytd = get_ytd_managers_shipments_bundle(d, big_order_threshold=big_order_threshold)

    mtd_block = _build_rows(
        mtd["cur"], mtd["ly"], mtd["pm"],
        return_warn_pct=return_warn_pct, return_crit_pct=return_crit_pct
    )
    ytd_block = _build_rows(
        ytd["cur"], ytd["ly"], None,
        return_warn_pct=return_warn_pct, return_crit_pct=return_crit_pct
    )

    mtd_block["chart_svg"] = build_managers_bar_svg(
    mtd_block["rows"],
    title="MTD: ТОП менеджеров по чистой выручке",
    top_n=10,
)

    ytd_block["chart_svg"] = build_managers_bar_svg(
        ytd_block["rows"],
        title="YTD: ТОП менеджеров по чистой выручке",
        top_n=10,
    )

    return {
        "mtd": mtd_block,
        "ytd": ytd_block,
        "meta": {
            "big_order_threshold": big_order_threshold,
            "return_warn_pct": return_warn_pct,
            "return_crit_pct": return_crit_pct,
        }
    }
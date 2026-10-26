# sales/reports/meeting_brief/metrics.py
"""Расчёт показателей отчёта из исходных таблиц (без обращения к БД)."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

import pandas as pd

from . import config as C
from .periods import Periods

TOL = C.MONEY_TOL


def pct_change(cur: float, prev: float):
    if not prev:
        return None
    return (cur - prev) / abs(prev) * 100


def share(part: float, total: float):
    return part / total * 100 if total else None


# ---------------------------------------------------------------- деньги

def _in_range(df: pd.DataFrame, d1: date, d2: date, col: str = "date") -> pd.DataFrame:
    if df.empty:
        return df
    return df[(df[col] >= d1) & (df[col] <= d2)]


def cash_section(src: dict, p: Periods) -> dict:
    cash, cash_ly = src["cash"], src["cash_ly"]
    cur = _in_range(cash, p.start, p.end)
    prev = _in_range(cash, p.prev_start, p.prev_end)

    def totals(df):
        cin = float(df["cash_in"].sum()) if not df.empty else 0.0
        cret = float(df["cash_ret"].sum()) if not df.empty else 0.0
        return {"cash_in": cin, "cash_ret": cret, "net": cin - cret}

    t_cur, t_prev, t_ly = totals(cur), totals(prev), totals(cash_ly)

    # По дням: текущий период и прошлый, выровненный по номеру дня
    days = [p.start + timedelta(days=i) for i in range(p.days)]
    by_day = cur.groupby("date")["cash_in"].sum() if not cur.empty else pd.Series(dtype=float)
    prev_days = [p.prev_start + timedelta(days=i) for i in range((p.prev_end - p.prev_start).days + 1)]
    by_day_prev = prev.groupby("date")["cash_in"].sum() if not prev.empty else pd.Series(dtype=float)
    daily = [{"date": d, "cash_in": float(by_day.get(d, 0.0))} for d in days]
    daily_prev = [float(by_day_prev.get(d, 0.0)) for d in prev_days]

    filled = [x for x in daily if x["cash_in"] > 0]
    best = max(filled, key=lambda x: x["cash_in"]) if filled else None
    worst = min(filled, key=lambda x: x["cash_in"]) if len(filled) > 1 else None
    avg_day = t_cur["cash_in"] / p.days if p.days else 0

    return {
        "cur": t_cur, "prev": t_prev, "ly": t_ly,
        "chg_prev": pct_change(t_cur["cash_in"], t_prev["cash_in"]),
        "chg_ly": pct_change(t_cur["cash_in"], t_ly["cash_in"]),
        "daily": daily, "daily_prev": daily_prev,
        "best_day": best, "worst_day": worst, "avg_day": avg_day,
    }


def plan_section(src: dict, p: Periods) -> dict:
    cash, plans = src["cash"], src["plans"]
    cur = _in_range(cash, p.start, p.end)
    fact = cur.groupby("store")["cash_in"].sum() if not cur.empty else pd.Series(dtype=float)
    prev = _in_range(cash, p.prev_start, p.prev_end)
    fact_prev = prev.groupby("store")["cash_in"].sum() if not prev.empty else pd.Series(dtype=float)

    # План на период: месячный план пропорционально дням периода в каждом месяце
    plan_period, names, groups = {}, {}, {}
    month_plan = {}
    for r in plans.itertuples():
        m = r.plan_month
        dim = monthrange(m.year, m.month)[1]
        m_end = m.replace(day=dim)
        overlap = (min(p.end, m_end) - max(p.start, m)).days + 1
        if overlap > 0:
            plan_period[r.store] = plan_period.get(r.store, 0.0) + r.amount * overlap / dim
        if m == p.month_start:
            month_plan[r.store] = month_plan.get(r.store, 0.0) + r.amount
        names[r.store] = r.store_name
        groups[r.store] = r.group

    mtd = _in_range(cash, p.month_start, p.end)
    fact_mtd = mtd.groupby("store")["cash_in"].sum() if not mtd.empty else pd.Series(dtype=float)
    dim = monthrange(p.end.year, p.end.month)[1]
    days_passed = p.end.day

    rows = []
    stores = (set(plan_period) | set(month_plan) | set(k for k, v in fact.items() if v > 0)
              | set(k for k, v in fact_mtd.items() if v > 0))
    for store in stores:
        if not store:
            continue
        f = float(fact.get(store, 0.0))
        pl = plan_period.get(store, 0.0)
        mp = month_plan.get(store, 0.0)
        fm = float(fact_mtd.get(store, 0.0))
        forecast = fm / days_passed * dim if days_passed else 0.0
        rows.append({
            "store": names.get(store, store.title()),
            "group": groups.get(store, ""),
            "plan": pl, "fact": f,
            "exec": share(f, pl),
            "prev": float(fact_prev.get(store, 0.0)),
            "chg_prev": pct_change(f, float(fact_prev.get(store, 0.0))),
            "month_plan": mp, "month_fact": fm,
            "month_exec": share(fm, mp),
            "month_forecast": forecast,
            "month_forecast_exec": share(forecast, mp),
            "month_expected": mp * days_passed / dim if dim else 0.0,
        })
    rows.sort(key=lambda r: (r["month_plan"] <= 0, -(r["month_exec"] or 0), -r["month_fact"]))

    tot_plan = sum(r["plan"] for r in rows)
    tot_fact = sum(r["fact"] for r in rows)
    tot_mp = sum(r["month_plan"] for r in rows)
    tot_mf = sum(r["month_fact"] for r in rows)
    tot_fc = tot_mf / days_passed * dim if days_passed else 0
    days_left = dim - days_passed
    expected = tot_mp * days_passed / dim if dim else 0.0
    example = next((r for r in rows if r["month_plan"] > 0), None)
    return {
        "rows": rows,
        "has_plan": tot_plan > 0,
        "total": {
            "plan": tot_plan, "fact": tot_fact, "exec": share(tot_fact, tot_plan),
            "month_plan": tot_mp, "month_fact": tot_mf, "month_exec": share(tot_mf, tot_mp),
            "month_forecast": tot_fc, "month_forecast_exec": share(tot_fc, tot_mp),
            "month_expected": expected, "month_vs_expected": tot_mf - expected,
            "month_left": max(tot_mp - tot_mf, 0.0),
            "need_daily": max(tot_mp - tot_mf, 0.0) / days_left if days_left > 0 else None,
            "avg_daily": tot_mf / days_passed if days_passed else 0.0,
        },
        "days_left": days_left,
        "example": example,
        "days_passed": days_passed, "days_in_month": dim,
        "behind": [r for r in rows if r["plan"] > 0 and (r["exec"] or 0) < 90],
        "done": [r for r in rows if r["plan"] > 0 and (r["exec"] or 0) >= 100],
    }


# ---------------------------------------------------------------- заказы

def _txt(v, default: str = "—") -> str:
    if v is None or (isinstance(v, float) and v != v):
        return default
    v = str(v).strip()
    return v or default


def _manager(src: dict, name) -> str:
    name = _txt(name, "")
    if not name:
        return "Без менеджера"
    return src["managers"].get(name, name)


def _orders_stats(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"count": 0, "amount": 0.0, "avg": 0.0, "paid": 0.0, "shipped": 0.0}
    amount = float(df["amount_active"].sum())
    return {
        "count": int(len(df)),
        "amount": amount,
        "avg": amount / len(df),
        "paid": float(df[["cash_pmts", "amount_active"]].min(axis=1).clip(lower=0).sum()),
        "shipped": float(df["total_shiped_amount"].sum()),
    }


def orders_section(src: dict, p: Periods) -> dict:
    orders = src["orders"]
    created_all = _in_range(orders, p.start, p.end, "date_from")
    created = created_all[~created_all["cancelled"] & (created_all["amount_active"] > 0)].copy()
    cancelled = created_all[created_all["cancelled"]]

    prev = _in_range(orders, p.prev_start, p.prev_end, "date_from")
    prev = prev[~prev["cancelled"] & (prev["amount_active"] > 0)]
    ly = _in_range(orders, p.ly_start, p.ly_end, "date_from")
    ly = ly[~ly["cancelled"] & (ly["amount_active"] > 0)]

    created["pay_state"] = "partial"
    created.loc[created["cash_pmts"] >= created["amount_active"] - TOL, "pay_state"] = "full"
    created.loc[created["cash_pmts"] <= TOL, "pay_state"] = "none"
    commission = (src.get("exclusions") or {}).get("commission", set())
    ext = created["client"].map(lambda c: " ".join(_txt(c, "").split()).casefold() in commission)
    created.loc[ext & (created["pay_state"] == "none"), "pay_state"] = "ext"
    created["manager_name"] = created["manager"].map(lambda m: _manager(src, m))

    def bucket(state):
        part = created[created["pay_state"] == state]
        return {"count": int(len(part)), "amount": float(part["amount_active"].sum())}

    st = _orders_stats(created)
    with_delivery = created[created["amount_delivery"] > 0]
    delivery_sum = float(created["amount_delivery"].sum())

    # Деньги, собранные в периоде, по менеджерам заказа
    cash = _in_range(src["cash"], p.start, p.end)
    mgr_by_order = dict(zip(orders["order_id"], orders["manager"]))
    cash_orders = cash[cash["order_guid"].notna() & (cash["order_guid"] != "")]
    cash_by_mgr = {}
    for r in cash_orders.itertuples():
        name = _manager(src, mgr_by_order.get(r.order_guid))
        cash_by_mgr[name] = cash_by_mgr.get(name, 0.0) + float(r.cash_in) - float(r.cash_ret)

    managers = []
    for name, g in created.groupby("manager_name"):
        s = _orders_stats(g)
        none = g[g["pay_state"] == "none"]
        managers.append({
            "name": name, **s,
            "paid_share": share(s["paid"], s["amount"]),
            "no_pay_count": int(len(none)), "no_pay_amount": float(none["amount_active"].sum()),
            "delivery_share": share(float(g["amount_delivery"].sum()), s["amount"]),
            "cash": cash_by_mgr.get(name, 0.0),
        })
    for name, v in cash_by_mgr.items():
        if v > 0 and name not in {m["name"] for m in managers}:
            managers.append({"name": name, "count": 0, "amount": 0.0, "avg": 0.0, "paid": 0.0,
                             "shipped": 0.0, "paid_share": None, "no_pay_count": 0,
                             "no_pay_amount": 0.0, "delivery_share": None, "cash": v})
    managers.sort(key=lambda m: -m["amount"])

    best = managers[0] if managers and managers[0]["amount"] > 0 else None
    best_cash = max(managers, key=lambda m: m["cash"]) if managers else None
    if best_cash and best_cash["cash"] <= 0:
        best_cash = None

    no_pay = created[created["pay_state"] == "none"].sort_values("amount_active", ascending=False)
    no_pay_list = [{
        "number": _txt(r.number), "date": r.date_from, "client": _txt(r.client),
        "manager": r.manager_name, "amount": float(r.amount_active), "status": _txt(r.status, ""),
        "store": _txt(r.store, ""),
    } for r in no_pay.head(C.TOP_ROWS).itertuples()]

    return {
        "cur": st, "prev": _orders_stats(prev), "ly": _orders_stats(ly),
        "chg_prev_count": pct_change(st["count"], len(prev)),
        "chg_prev_amount": pct_change(st["amount"], float(prev["amount_active"].sum())),
        "chg_ly_amount": pct_change(st["amount"], float(ly["amount_active"].sum())),
        "full": bucket("full"), "partial": bucket("partial"), "none": bucket("none"), "ext": bucket("ext"),
        "paid_share": share(st["paid"], st["amount"]),
        "shipped_share": share(st["shipped"], st["amount"]),
        "delivery": {
            "orders": int(len(with_delivery)),
            "orders_share": share(len(with_delivery), st["count"]),
            "amount": delivery_sum,
            "amount_share": share(delivery_sum, st["amount"]),
            "avg": delivery_sum / len(with_delivery) if len(with_delivery) else 0.0,
        },
        "cancelled": {"count": int(len(cancelled)),
                      "amount": float(cancelled["order_amount"].sum())},
        "managers": managers, "best": best, "best_cash": best_cash,
        "no_pay_list": no_pay_list,
    }


def exclusion_reason(df: pd.DataFrame, ex: dict | None) -> pd.Series:
    """Причина исключения заказа из долгов (пусто — долг считается)."""
    ex = ex or {"clients": {}, "orders": {}}

    def one(r):
        client = " ".join(_txt(r.client, "").split()).casefold()
        if client in ex["clients"]:
            return ex["clients"][client]
        for key in (_txt(r.order_id, "").casefold(), _txt(r.number, "").casefold()):
            if key and key in ex["orders"]:
                return ex["orders"][key]
        return ""
    return pd.Series([one(r) for r in df.itertuples()], index=df.index, dtype=object)


def control_section(src: dict, p: Periods) -> dict:
    """Состояние заказов на дату отчёта: что требует действий."""
    o = src["orders"]
    o = o[~o["cancelled"] & (o["amount_active"] > TOL)].copy()
    o["excluded"] = exclusion_reason(o, src.get("exclusions"))
    o["manager_name"] = o["manager"].map(lambda m: _manager(src, m))
    today = p.end

    def row(r, **extra):
        return {"number": _txt(r.number), "date": r.date_from, "client": _txt(r.client),
                "manager": r.manager_name, "amount": float(r.amount_active),
                "paid": float(r.cash_pmts), "shipped": float(r.total_shiped_amount),
                "days": (today - r.date_from).days if isinstance(r.date_from, date) else None, **extra}

    def by_manager(df, col="amount_active"):
        g = df.groupby("manager_name").agg(count=("order_id", "count"), amount=(col, "sum"))
        g = g.sort_values("count", ascending=False)
        return [{"name": n, "count": int(v["count"]), "amount": float(v["amount"])} for n, v in g.iterrows()]

    open_ = o[o["status"] != C.ST_CLOSED]
    ready = open_[((open_["total_shiped_amount"] - open_["amount_active"]).abs() <= TOL)
                  & (open_["cash_pmts"] >= open_["amount_active"] - TOL)]

    o["ship_debt"] = (o["total_shiped_amount"] - o["cash_pmts"]).clip(lower=0)
    recent = o[o["date_from"].notna() & (o["date_from"] >= today - timedelta(days=365))]
    debt_all = recent[recent["ship_debt"] > TOL].sort_values("ship_debt", ascending=False)
    debt = debt_all[debt_all["excluded"] == ""]
    debt_ex = debt_all[debt_all["excluded"] != ""]

    approval = open_[(open_["status"] == C.ST_APPROVAL) & open_["date_from"].notna()
                     & (open_["date_from"] <= today - timedelta(days=C.APPROVAL_STUCK_DAYS))]
    reserve = open_[(open_["status"] == C.ST_RESERVE) & open_["date_from"].notna()
                    & (open_["total_shiped_amount"] <= TOL)
                    & (open_["date_from"] <= today - timedelta(days=C.RESERVE_STUCK_DAYS))]

    return {
        "ready": {"count": int(len(ready)), "amount": float(ready["amount_active"].sum()),
                  "by_manager": by_manager(ready),
                  "list": [row(r) for r in ready.sort_values("date_from").head(C.TOP_ROWS).itertuples()]},
        "debt": {"count": int(len(debt)), "amount": float(debt["ship_debt"].sum()),
                 "by_manager": by_manager(debt, "ship_debt")[:C.TOP_ROWS],
                 "list": [row(r, debt=float(r.ship_debt)) for r in debt.head(C.TOP_ROWS).itertuples()]},
        "exclusions_ok": (src.get("exclusions") or {}).get("ok", True),
        "debt_excluded": {
            "count": int(len(debt_ex)), "amount": float(debt_ex["ship_debt"].sum()),
            "list": [row(r, debt=float(r.ship_debt), reason=r.excluded) for r in debt_ex.head(C.TOP_ROWS).itertuples()],
            "by_client": [
                {"client": _txt(g["client"].iloc[0]), "count": int(len(g)), "amount": float(g["ship_debt"].sum()),
                 "reason": g["excluded"].iloc[0]}
                for _, g in sorted(debt_ex.groupby(debt_ex["client"].map(lambda v: " ".join(_txt(v, "").split()).casefold())),
                                   key=lambda kv: -kv[1]["ship_debt"].sum())
            ],
        },
        "approval": {"count": int(len(approval)), "amount": float(approval["amount_active"].sum()),
                     "list": [row(r) for r in approval.sort_values("amount_active", ascending=False)
                              .head(5).itertuples()]},
        "reserve": {"count": int(len(reserve)), "amount": float(reserve["amount_active"].sum()),
                    "paid": float(reserve["cash_pmts"].clip(lower=0).sum()),
                    "list": [row(r) for r in reserve.sort_values("amount_active", ascending=False)
                             .head(5).itertuples()]},
    }


# ---------------------------------------------------------------- продажи

def _is_service(row) -> bool:
    names = " ".join(str(x).lower() for x in (row.get("root"), row.get("cat"), row.get("subcat")) if x)
    full = str(row.get("fullname") or "").lower()
    return any(k in names for k in C.SERVICE_KEYWORDS) or any(
        k in full for k in ("доставк", "логист", "услуг", "подъем", "подъём", "монтаж"))


def _goods(items: pd.DataFrame) -> pd.DataFrame:
    items = items.copy()
    items["is_service"] = [_is_service(r) for r in items.to_dict("records")]
    items["root"] = items["root"].fillna("Без категории")
    items["cat"] = items["cat"].fillna(items["root"])
    items["subcat"] = items["subcat"].fillna("")
    items["brand"] = items["brand"].fillna("")
    return items


def _sales_frame(goods: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    df = sales.merge(goods, on="item_id", how="left")
    df["is_service"] = df["is_service"].fillna(False).astype(bool)
    df = df[~df["is_service"]].copy()
    df["root"] = df["root"].fillna("Без категории")
    df["net"] = df["dt"] - df["cr"]
    return df


def sales_section(src: dict, p: Periods, goods: pd.DataFrame) -> dict:
    cur = _sales_frame(goods, src["sales"])
    prev = _sales_frame(goods, src["sales_prev"])
    ly = _sales_frame(goods, src["sales_ly"])

    def tot(df):
        dt, cr = float(df["dt"].sum()), float(df["cr"].sum())
        return {"dt": dt, "cr": cr, "net": dt - cr, "qty": float(df["qty"].sum() - df["qty_ret"].sum()),
                "ret_share": share(cr, dt)}

    t_cur, t_prev, t_ly = tot(cur), tot(prev), tot(ly)

    def by(keys):
        a = cur.groupby(keys).agg(net=("net", "sum"), dt=("dt", "sum"), cr=("cr", "sum"),
                                  qty=("qty", "sum"))
        b = prev.groupby(keys)["net"].sum().rename("prev")
        c = ly.groupby(keys)["net"].sum().rename("ly")
        out = a.join(b, how="outer").join(c, how="outer").fillna(0.0)
        out["chg"] = [pct_change(n, pv) for n, pv in zip(out["net"], out["prev"])]
        out["chg_ly"] = [pct_change(n, pv) for n, pv in zip(out["net"], out["ly"])]
        out["ret_share"] = [share(cr, dt) for cr, dt in zip(out["cr"], out["dt"])]
        out["share"] = [share(n, t_cur["net"]) for n in out["net"]]
        return out.reset_index()

    cats = by(["root"]).sort_values("net", ascending=False)
    cats = cats[(cats["net"] != 0) | (cats["prev"] != 0)]
    cat_rows = cats.head(C.CAT_ROWS).to_dict("records")
    rest = cats.iloc[C.CAT_ROWS:]
    if not rest.empty:
        cat_rows.append({"root": f"Прочие ({len(rest)})", "net": rest["net"].sum(),
                         "prev": rest["prev"].sum(), "ly": rest["ly"].sum(),
                         "chg": pct_change(rest["net"].sum(), rest["prev"].sum()),
                         "chg_ly": pct_change(rest["net"].sum(), rest["ly"].sum()),
                         "ret_share": share(rest["cr"].sum(), rest["dt"].sum()),
                         "share": share(rest["net"].sum(), t_cur["net"]), "is_rest": True})

    # Подкатегории с самым большим изменением в рублях
    cur["sub"] = [s or c for s, c in zip(cur["subcat"].fillna(""), cur["cat"].fillna(""))]
    prev["sub"] = [s or c for s, c in zip(prev["subcat"].fillna(""), prev["cat"].fillna(""))]
    ly["sub"] = [s or c for s, c in zip(ly["subcat"].fillna(""), ly["cat"].fillna(""))]
    subs = by(["root", "sub"])
    subs["delta"] = subs["net"] - subs["prev"]
    growth = subs[subs["delta"] > 0].sort_values("delta", ascending=False).head(5).to_dict("records")
    drops = subs[subs["delta"] < 0].sort_values("delta").head(5).to_dict("records")

    brands = by(["brand"])
    brands = brands[brands["brand"] != ""].sort_values("net", ascending=False).head(C.TOP_ROWS)

    ret_items = cur[cur["cr"] > 0].sort_values("cr", ascending=False).head(5)
    ret_list = [{"name": _txt(r.fullname), "root": r.root, "cr": float(r.cr), "qty": float(r.qty_ret),
                 "share": share(r.cr, r.dt)} for r in ret_items.itertuples()]

    top_items = cur.groupby(["item_id", "fullname", "root"], dropna=False)["net"].sum().reset_index()
    top_items = top_items.sort_values("net", ascending=False).head(5)

    return {
        "cur": t_cur, "prev": t_prev, "ly": t_ly,
        "chg_prev": pct_change(t_cur["net"], t_prev["net"]),
        "chg_ly": pct_change(t_cur["net"], t_ly["net"]),
        "ret_pp": (t_cur["ret_share"] or 0) - (t_prev["ret_share"] or 0) if t_prev["dt"] else None,
        "categories": cat_rows, "growth": growth, "drops": drops,
        "brands": brands.to_dict("records"), "returns": ret_list,
        "top_items": [{"name": _txt(r.fullname), "root": r.root, "net": float(r.net)}
                      for r in top_items.itertuples()],
    }


# ---------------------------------------------------------------- остатки

def _suggest(r) -> str:
    nsd = r["no_sale_days"]
    if not r["qty_all"]:
        return "Не продавался: проверить выкладку и карточку на сайте, показать дизайнерам"
    if nsd is not None and nsd == nsd and nsd > 365:
        return "Год без продаж: уценка или распродажа, возврат поставщику"
    if r["available"] >= 10:
        return "Большой запас: акция, комплект с ходовым товаром, перераспределить"
    return "Акция на 2–4 недели, вернуть в зал и на главную сайта"


def stock_section(src: dict, p: Periods, goods: pd.DataFrame) -> dict:
    st = src["stocks"]
    if st.empty:
        return {"has_data": False}
    df = (st.merge(goods, on="item_id", how="left")
            .merge(src["history"], on="item_id", how="left")
            .merge(src["receipts"], on="item_id", how="left"))
    df["is_service"] = df["is_service"].fillna(False).astype(bool)
    df = df[~df["is_service"]].copy()
    df["root"] = df["root"].fillna("Без категории")
    for c in ("qty_90", "dt_365", "qty_365", "dt_all", "qty_all"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    sold = src["sales"].set_index("item_id")
    df["sold_period"] = df["item_id"].map((sold["qty"] - sold["qty_ret"])).fillna(0.0)
    stock_date = pd.to_datetime(df["stock_date"], errors="coerce").max()
    stock_date = stock_date.date() if pd.notna(stock_date) else None
    ref = stock_date or p.end

    df["price"] = [
        (a / q) if q > 0 else ((b / w) if w > 0 else None)
        for a, q, b, w in zip(df["dt_365"], df["qty_365"], df["dt_all"], df["qty_all"])
    ]
    df["no_sale_days"] = [(ref - d).days if isinstance(d, date) else None for d in df["last_sale"]]
    # Сколько товар на складе: последний приход, если нет — дата появления карточки
    init = pd.to_datetime(df["init_date"], errors="coerce").dt.date if "init_date" in df.columns else None
    df["age_days"] = [
        (ref - d).days if isinstance(d, date) else ((ref - i).days if isinstance(i, date) else None)
        for d, i in zip(df["last_receipt"], init if init is not None else [None] * len(df))
    ]

    avail = df[df["available"] > 0].copy()
    stale_mask = ((avail["no_sale_days"].isna() | (avail["no_sale_days"] > C.STALE_NO_SALES_DAYS))
                  & avail["age_days"].notna() & (avail["age_days"] > C.STALE_MIN_AGE_DAYS))
    stale = avail[stale_mask].copy()
    stale["never"] = stale["qty_all"] <= 0
    stale = stale.sort_values(["available", "age_days"], ascending=False)
    stale_list = [{
        "name": _txt(r["fullname"]), "article": _txt(r.get("article"), ""), "root": r["root"],
        "available": float(r["available"]), "age_days": r["age_days"],
        "last_sale": r["last_sale"] if isinstance(r["last_sale"], date) else None,
        "no_sale_days": r["no_sale_days"], "last_receipt": r["last_receipt"] if isinstance(r["last_receipt"], date) else None,
        "advice": _suggest(r),
    } for r in stale.head(10).to_dict("records")]

    # Хиты периода без остатка
    hits = df[df["sold_period"] > 0].sort_values("sold_period", ascending=False).head(C.DEFICIT_TOP_N)
    deficit = hits[hits["available"] <= 0]
    deficit_list = [{"name": _txt(r.fullname), "root": r.root, "sold": float(r.sold_period),
                     "ordered": float(r.ordered)} for r in deficit.head(C.TOP_ROWS).itertuples()]

    cats = avail.groupby("root").agg(sku=("item_id", "count"), qty=("available", "sum"),
                                     sold=("sold_period", "sum"))
    stale_by = stale.groupby("root").agg(stale_sku=("item_id", "count"), stale_qty=("available", "sum"))
    cats = cats.join(stale_by, how="left").fillna(0).sort_values("qty", ascending=False)
    weeks = p.days / 7
    cat_rows = [{
        "root": n, "sku": int(v["sku"]), "qty": float(v["qty"]), "sold": float(v["sold"]),
        "cover_weeks": (v["qty"] / (v["sold"] / weeks)) if v["sold"] > 0 else None,
        "stale_sku": int(v["stale_sku"]), "stale_share": share(v["stale_sku"], v["sku"]),
    } for n, v in cats.head(C.CAT_ROWS).iterrows()]

    return {
        "has_data": True, "stock_date": stock_date,
        "sku": int(len(avail)), "qty": float(avail["available"].sum()),
        "stale": {"sku": int(len(stale)), "qty": float(stale["available"].sum()),
                  "never": int(stale["never"].sum()),
                  "share": share(len(stale), len(avail)), "list": stale_list},
        "deficit": {"count": int(len(deficit)), "of": int(len(hits)), "list": deficit_list},
        "categories": cat_rows,
    }


# ---------------------------------------------------------------- сборка

def build_metrics(src: dict, p: Periods) -> dict:
    goods = _goods(src["items"])
    return {
        "cash": cash_section(src, p),
        "plan": plan_section(src, p),
        "orders": orders_section(src, p),
        "control": control_section(src, p),
        "sales": sales_section(src, p, goods),
        "stock": stock_section(src, p, goods),
    }

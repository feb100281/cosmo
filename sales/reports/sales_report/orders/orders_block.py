from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional
import re

import numpy as np
import pandas as pd

from ..formatters import fmt_money, fmt_int, fmt_pct, fmt_money_0
from .data_orders import get_orders_by_period
from .orders_chart import build_orders_carryover_by_type_svg


def _safe_div(a: float, b: float) -> float:
    return (a / b) if b else 0.0


def _to_html_table(df: pd.DataFrame, table_class: str = "compare-table") -> str:
    if df is None or df.empty:
        return ""
    return df.to_html(
        index=False,
        border=0,
        classes=table_class,
        escape=False,  # важно: мы вставляем HTML для бейджей
    )


def _add_total_row_class(html: str, total_label: str = "Итого", row_class: str = "total-row") -> str:
    """
    Добавляет CSS-класс строке <tr>, где первая <td> содержит total_label.
    Работает устойчиво независимо от переносов строк/пробелов, и умеет:
      - добавить class="", если его нет
      - дописать класс, если class="" уже есть
    """
    if not html:
        return html

    # Вариант 1: у <tr> нет class=""
    pattern_no_class = re.compile(
        rf'(<tr)(\s*>\s*<td[^>]*>\s*{re.escape(total_label)}\s*</td>)',
        flags=re.IGNORECASE,
    )
    html, n1 = pattern_no_class.subn(rf'\1 class="{row_class}"\2', html, count=1)
    if n1:
        return html

    # Вариант 2: class="" уже есть — дописываем наш класс
    pattern_has_class = re.compile(
        rf'(<tr[^>]*\bclass=")([^"]*)("([^>]*)>\s*<td[^>]*>\s*{re.escape(total_label)}\s*</td>)',
        flags=re.IGNORECASE,
    )
    html = pattern_has_class.sub(rf'\1\2 {row_class}\3', html, count=1)

    return html


# ---------- UI helpers (HTML badges) ----------

def _badge(text: str, tone: str = "neutral") -> str:
    """
    tone: neutral / info / warn / danger / accent
    Требует CSS классы:
      .ords-badge, .ords-badge--neutral/info/warn/danger/accent
    """
    text = (text or "").strip()
    return f'<span class="ords-badge ords-badge--{tone}">{text}</span>'


def _age_badge(days: Any) -> str:
    """
    Бейдж для "Дней в работе":
      0–14 neutral, 15–30 info, 31–60 warn, 61+ danger
    """
    try:
        d = int(float(days))
    except Exception:
        d = 0

    if d >= 61:
        tone = "danger"
    elif d >= 31:
        tone = "warn"
    elif d >= 15:
        tone = "info"
    else:
        tone = "neutral"

    return _badge(f"{d} дн.", tone)


def build_orders_context(
    period_start: date,
    period_end: date,
    order_type: Optional[int] = None,  # None/1/2 как в примере
    top_n_orders: int = 15,
) -> Dict[str, Any]:
    """
    Возвращает готовый context для вставки в HTML.
    """
    df = get_orders_by_period(period_start, period_end, order_type=order_type)

    if df is None or df.empty:
        return {
            "has": False,
            "period_start": period_start,
            "period_end": period_end,
            "orders_table_html": "",
            "orders_by_type_html": "",
            "orders_chart_svg": None,
            "summary": None,
        }

    # --- флаги: new vs carryover ---
    df = df.copy()
    df["is_new"] = df["client_order_date"].dt.date.between(period_start, period_end)
    df["cohort"] = np.where(df["is_new"], "New", "Carryover")

    # --- основные totals периода ---
    dt = float(df["sales_period"].sum())
    cr = float(df["returns_period"].sum())
    amount = float(df["amount_period"].sum())

    orders_cnt = int(df["client_order_number"].nunique())
    rtr_ratio = _safe_div(cr, dt)  # доля возвратов (0..1)
    ave_check = _safe_div(amount, orders_cnt)

    carry_amount = float(df.loc[df["cohort"] == "Carryover", "amount_period"].sum())
    new_amount = float(df.loc[df["cohort"] == "New", "amount_period"].sum())

    carry_share = _safe_div(carry_amount, amount)  # 0..1
    new_share = _safe_div(new_amount, amount)      # 0..1

    # медиана "возраста активных заказов" на момент последней отгрузки в периоде
    # (current_order_duration считается в SQL как DATEDIFF(x.max_date, order_date)+1)
    med_duration = float(
        df["current_order_duration"]
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
        .clip(lower=0)
        .median()
        if "current_order_duration" in df.columns
        else 0.0
    )

    summary = {
        "orders": fmt_int(orders_cnt),
        "dt": fmt_money(dt),
        "cr": fmt_money(cr),
        "amount": fmt_money(amount),
        "rtr_ratio": fmt_pct(rtr_ratio * 100),
        "ave_check": fmt_money_0(ave_check),

        "new_share": fmt_pct(new_share * 100),
        "new_share_num": round(float(new_share * 100), 1),  # ✅ для progress bar (0..100)

        "carry_share": fmt_pct(carry_share * 100),
        "carry_share_num": round(float(carry_share * 100), 1),  # ✅ для progress bar (0..100)

        "med_duration": fmt_int(med_duration),
    }

    # --- таблица по типам: New vs Carryover + возвраты ---
    # NOTE: чтобы корректно посчитать new_amount/carry_amount внутри группировки,
    # не используем lambda с внешним df.loc[s.index,...] (часто путается), а считаем отдельными полями.
    df["_new_amount"] = np.where(df["cohort"] == "New", df["amount_period"], 0.0)
    df["_carry_amount"] = np.where(df["cohort"] == "Carryover", df["amount_period"], 0.0)

    by_type = (
        df.groupby("client_order_type", dropna=False)
        .agg(
            orders=("client_order_number", "nunique"),
            dt=("sales_period", "sum"),
            cr=("returns_period", "sum"),
            amount=("amount_period", "sum"),
            new_amount=("_new_amount", "sum"),
            carry_amount=("_carry_amount", "sum"),
        )
        .reset_index()
    )

    by_type["rtr_ratio"] = by_type.apply(lambda r: _safe_div(float(r["cr"]), float(r["dt"])) * 100, axis=1)
    by_type["carry_share"] = by_type.apply(lambda r: _safe_div(float(r["carry_amount"]), float(r["amount"])) * 100, axis=1)
    by_type["new_share"] = by_type.apply(lambda r: _safe_div(float(r["new_amount"]), float(r["amount"])) * 100, axis=1)

    by_type = by_type.sort_values("amount", ascending=False)

    # ===== ИТОГО (последней строкой) =====
    total_row = pd.Series({
        "client_order_type": "Итого",
        "orders": int(df["client_order_number"].nunique()),
        "dt": float(df["sales_period"].sum()),
        "cr": float(df["returns_period"].sum()),
        "amount": float(df["amount_period"].sum()),
        "new_amount": float(df["_new_amount"].sum()),
        "carry_amount": float(df["_carry_amount"].sum()),
    })
    total_row["rtr_ratio"] = _safe_div(float(total_row["cr"]), float(total_row["dt"])) * 100
    total_row["carry_share"] = _safe_div(float(total_row["carry_amount"]), float(total_row["amount"])) * 100
    total_row["new_share"] = _safe_div(float(total_row["new_amount"]), float(total_row["amount"])) * 100

    by_type = pd.concat([by_type, total_row.to_frame().T], ignore_index=True)

    by_type_fmt = pd.DataFrame({
        "Тип заказа": by_type["client_order_type"].astype(str),
        "Заказов (шт.)": by_type["orders"].map(fmt_int),
        "Оборот": by_type["dt"].map(fmt_money),
        "Возвраты": by_type["cr"].map(fmt_money),
        "Чистая выручка": by_type["amount"].map(fmt_money),
        "New (выручка)": by_type["new_amount"].map(fmt_money),
        "Carryover (выручка)": by_type["carry_amount"].map(fmt_money),
        "Доля New": by_type["new_share"].map(lambda x: fmt_pct(float(x))),
        "Доля Carryover": by_type["carry_share"].map(lambda x: fmt_pct(float(x))),
        "Доля возвратов": by_type["rtr_ratio"].map(lambda x: fmt_pct(float(x))),
    })

    orders_by_type_html = _to_html_table(by_type_fmt, table_class="compare-table")
    orders_by_type_html = _add_total_row_class(orders_by_type_html, total_label="Итого", row_class="total-row")

    # --- топ заказов периода по чистой выручке ---
    top = df.sort_values("amount_period", ascending=False).head(top_n_orders).copy()

    # Русский статус: Новый / Хвост (для собственника понятнее)
    top["status_ru"] = np.where(top["is_new"], "New", "Carryover")

    # HTML-бейджи
    top["status_badge"] = top["status_ru"].map(
        lambda s: _badge(s, "accent" if s == "Carryover" else "neutral")
    )
    top["age_badge"] = top["current_order_duration"].map(_age_badge)

    # ВАЖНО: порядок колонок — сначала смысл/риски, потом даты, потом деньги
    top_fmt = pd.DataFrame({
        "Заказ": top["client_order_number"].astype(str),
        "Тип": top["client_order_type"].astype(str),
        "Статус": top["status_badge"],                 # бейдж
        "Дней в работе": top["age_badge"],            # бейдж
        "Дата заказа": top["client_order_date"].dt.strftime("%d.%m.%Y").fillna("—"),
        "Последняя отгрузка": top["last_ship_date"].dt.strftime("%d.%m.%Y").fillna("—"),
        "Отгружено за период": top["amount_period"].map(fmt_money),
        "Всего отгружено по заказу": top.apply(
            lambda r: (
                f'{fmt_money(r["total_amount_upto_end"])}'
                f'<div class="ord-cell-subline">в т.ч. услуги: {fmt_money(r.get("services_upto_end", 0))}</div>'
                if float(r.get("services_upto_end", 0) or 0) > 0
                else f'{fmt_money(r["total_amount_upto_end"])}'
            ),
            axis=1
        ),

        # "Оборот": top["sales_period"].map(fmt_money),
        "Возвраты": top["returns_period"].map(fmt_money),
    })

    orders_table_html = _to_html_table(top_fmt, table_class="compare-table")

    # --- обязательный график ---
    orders_chart_svg = build_orders_carryover_by_type_svg(df, period_start, period_end, top_n=8)

    # уборка служебных колонок (не обязательно, но красиво)
    df.drop(columns=[c for c in ["_new_amount", "_carry_amount"] if c in df.columns], inplace=True, errors="ignore")

    return {
        "has": True,
        "period_start": period_start,
        "period_end": period_end,
        "summary": summary,
        "orders_by_type_html": orders_by_type_html,
        "orders_table_html": orders_table_html,
        "orders_chart_svg": orders_chart_svg,
        "order_type": order_type,

        # ✅ отдаём df наружу, чтобы дальше строить orders_flow без второго запроса
        "_df_orders": df,
    }

# sales/reports/newspaper/analytics/narrative.py
"""
Связный текст для разделов отчёта ("читается как газета", а не только
таблицы и цифры). Как и остальная аналитика — это детерминированные
Python-правила поверх уже посчитанных данных, без LLM. Каждое предложение
добавляется только если для него есть реальное основание в данных.
"""

from __future__ import annotations

from ..render.helpers import fmt_money_short, fmt_pct


def build_cash_lead(cash_data: dict, cash_analytics: dict) -> str:
    totals = cash_data["totals"]
    sentences = []

    sentences.append(
        f"На {cash_data['days_passed']}-й день месяца компания собрала "
        f"{fmt_money_short(totals['fact'])} из {fmt_money_short(totals['plan'])} "
        f"плана — это {fmt_pct(totals['exec_pct'])} выполнения."
    )

    if cash_analytics["is_behind_pace"]:
        sentences.append(
            f"Темп отстаёт от календарного графика месяца: при равномерном "
            f"поступлении к этому дню должно было накопиться "
            f"{cash_analytics['expected_pace_pct_fmt']} плана."
        )
    elif cash_analytics["is_ahead_pace"]:
        sentences.append(
            f"Темп опережает календарный график: при равномерном поступлении "
            f"к этому дню ожидалось бы {cash_analytics['expected_pace_pct_fmt']} плана."
        )
    else:
        sentences.append("Темп сбора примерно соответствует календарному графику месяца.")

    worst = cash_analytics["worst_store"]
    best = cash_analytics["best_store"]
    if worst is not None and best is not None and worst["store_name"] != best["store_name"]:
        sentences.append(
            f"Лучший результат по выполнению плана показывает «{best['store_name']}» "
            f"({fmt_pct(best['exec_pct'])}), слабее всех — «{worst['store_name']}» "
            f"({fmt_pct(worst['exec_pct'])})."
        )

    if totals["is_on_track"]:
        sentences.append(
            f"При сохранении текущей динамики к концу месяца компания выйдет "
            f"на {fmt_money_short(totals['projected_month_fact'])}, что покрывает план."
        )
    else:
        gap = totals["plan"] - totals["projected_month_fact"]
        sentences.append(
            f"При сохранении текущей динамики прогноз на конец месяца — "
            f"{fmt_money_short(totals['projected_month_fact'])}, "
            f"это ниже плана на {fmt_money_short(gap)}."
        )

    return " ".join(sentences)


def build_returns_lead(returns_data: dict) -> str:
    sentences = []

    sentences.append(
        f"С начала месяца возвраты составили {fmt_money_short(abs(returns_data['total_returns']))} "
        f"({fmt_pct(abs(returns_data['total_return_pct']))} от факта поступлений), "
        f"дизайнерское вознаграждение — {fmt_money_short(abs(returns_data['total_designer']))} "
        f"({fmt_pct(abs(returns_data['total_designer_pct']))} от факта)."
    )

    rows_with_returns = [r for r in returns_data["rows"] if r["returns_amount"] != 0]
    if rows_with_returns:
        top_return_store = max(rows_with_returns, key=lambda r: abs(r["returns_amount"]))
        sentences.append(
            f"Больше всего возвратов — у «{top_return_store['store_name']}»: "
            f"{fmt_money_short(abs(top_return_store['returns_amount']))} "
            f"({fmt_pct(abs(top_return_store['return_pct_of_income']))} от факта магазина)."
        )

    sentences.append(
        f"С учётом возвратов и дизайнерского вознаграждения чистый факт по сети — "
        f"{fmt_money_short(returns_data['net_after_all'])}."
    )

    return " ".join(sentences)


def build_stocks_lead(stocks_data: dict, stocks_analytics: dict) -> str:
    company = stocks_data["company"]
    sentences = []

    # Важно: "в магазинах и на складах" — это qty_available, а не qty_total
    # (qty_total = qty_available + qty_ordered, то есть остаток на месте
    # плюс то, что ещё в пути; складывать их снова в этой фразе нельзя,
    # иначе "в пути" считается дважды).
    qty_available_fmt = f"{company['qty_available']:,.0f}".replace(",", " ")
    qty_ordered_fmt = f"{company['qty_ordered']:,.0f}".replace(",", " ")
    sentences.append(
        f"На складах и в магазинах компании числится {qty_available_fmt} шт. товара, "
        f"ещё {qty_ordered_fmt} шт. в пути."
    )

    if stocks_analytics["is_concentrated"]:
        top3_names = ", ".join(c["cat_name"] for c in stocks_analytics["top3_categories"])
        sentences.append(
            f"Запасы сконцентрированы: категории {top3_names} формируют "
            f"{stocks_analytics['top3_share_pct_fmt']} остатков по количеству."
        )

    return " ".join(sentences)

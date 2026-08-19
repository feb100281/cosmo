# sales/reports/newspaper/render/helpers.py
"""
Форматирование чисел для отображения.

Базовые денежные форматтеры (fmt_money, fmt_pct, safe_div,
normalize_store_name) переиспользуются из sales_plan_report.utils — чтобы
числа кэша в Newspaper форматировались абсолютно так же, как в исходном
отчёте. Здесь — только то, чего там нет: короткая запись крупных сумм
(млн/тыс.) для заголовков и графиков, и вспомогательные CSS-классы для
отклонений.
"""

from __future__ import annotations

from decimal import Decimal

from sales.reports.sales_plan_report.utils import (  # noqa: F401
    fmt_money,
    fmt_pct,
    normalize_store_name,
    safe_div,
    to_decimal,
)


def fmt_money_short(value) -> str:
    """
    Компактная запись суммы: 12.4 млн ₽ / 850 тыс. ₽ / 320 ₽.
    Используется в заголовках, KPI-цифрах и графиках, где длинная запись
    с разрядами перегружала бы полосу.
    """
    value = to_decimal(value)

    if abs(value) >= Decimal("1000000"):
        return f"{float(value / Decimal('1000000')):.1f} млн ₽"
    if abs(value) >= Decimal("1000"):
        return f"{float(value / Decimal('1000')):.0f} тыс. ₽"
    return f"{float(value):,.0f} ₽".replace(",", " ")


def fmt_qty(value) -> str:
    """Целочисленное количество с разрядами: 128 430 шт."""
    try:
        return f"{float(value):,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def fmt_pp(value) -> str:
    """Разница в процентных пунктах со знаком: +4.2 п.п. / -11.0 п.п."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    sign = "+" if value >= 0 else "−"
    return f"{sign}{abs(value):.1f} п.п."


def nbsp(text) -> str:
    """
    Заменяет обычные пробелы в уже отформатированной строке на неразрывные
    (U+00A0) — чтобы разряды числа вроде "1 234 567" не переносились на
    новую строку в узкой ячейке (календарь, компактные колонки таблиц).
    Это чисто отображение: сама величина и её форматирование (разряды,
    десятичные) не меняются, меняется только символ пробела.
    """
    if not isinstance(text, str):
        return text
    return text.replace(" ", " ")


def deviation_class(value) -> str:
    """CSS-класс для положительного/отрицательного/нейтрального значения."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "neutral"
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"

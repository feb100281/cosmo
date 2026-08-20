# sales/reports/sales_digest/config.py
"""
Общие константы для нового отчёта "COSMORELAX Sales Digest" — большого
отчёта по продажам (день/неделя/месяц — в зависимости от даты, см. старую
sales.reports.sales_report.period.classify_report).

Это НЕ переделка бизнес-логики: весь расчёт данных по-прежнему выполняет
старый модуль sales.reports.sales_report (builder.py и всё, что под ним) —
sales_digest только рисует эти же данные в новой, газетной верстке
COSMORELAX (тот же язык, что в sales.reports.newspaper). Старый отчёт
(sales/reports/sales_report/templates/...) не меняется и продолжает
работать как раньше отдельной кнопкой в админке.
"""

from __future__ import annotations

# Переиспользуем бренд/палитру/шрифты/страницу — один в один с newspaper,
# чтобы оба отчёта выглядели как один визуальный язык COSMORELAX.
from ..newspaper.config import (  # noqa: F401
    COLOR_ACCENT,
    COLOR_ACCENT_SOFT,
    COLOR_BRAND_DEEP,
    COLOR_INK,
    COLOR_INK_SOFT,
    COLOR_NEGATIVE,
    COLOR_NEGATIVE_BG,
    COLOR_NEUTRAL,
    COLOR_PAPER,
    COLOR_POSITIVE,
    COLOR_POSITIVE_BG,
    COLOR_RULE,
    COMPANY_BRAND_NAME,
    COMPANY_LEGAL_NAME,
    COMPANY_WEBSITE,
    CHART_PALETTE,
    FONT_SANS,
    FONT_SERIF,
    PAGE_MARGIN,
    PAGE_SIZE,
)

REPORT_TITLE = "COSMORELAX Sales Digest"

# Имя PDF-файла — префикс зависит от типа периода (день/неделя/месяц),
# см. render/html.py (report_type уже приходит из старого builder'а).
PDF_FILENAME_PREFIX = {
    "daily": "Sales_Digest_Day",
    "weekly": "Sales_Digest_Week",
    "monthly": "Sales_Digest_Month",
}

# Сколько строк показываем в больших таблицах (магазины, менеджеры,
# категории) — старый отчёт местами не ограничивает вовсе; здесь одно
# универсальное разумное ограничение, чтобы верстка не расползалась на
# десятки страниц, если магазинов/менеджеров станет много.
MAX_TABLE_ROWS = 30

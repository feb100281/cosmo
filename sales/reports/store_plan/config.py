# sales/reports/store_plan/config.py
"""
Константы для печати плана продаж на месяц (StoreSalesPlan).

Модель StoreSalesPlan не трогаем — это только слой печати поверх неё.
Визуальный стиль (цвета, шрифты, разметка страницы) переиспользуется из
newspaper/config.py, чтобы документ выглядел как часть той же системы
отчётов COSMORELAX, а не как отдельный самодельный шаблон.
"""

from __future__ import annotations

from ..newspaper.config import (  # noqa: F401  переиспользуем стиль Newspaper
    COLOR_ACCENT,
    COLOR_BRAND_DEEP,
    COLOR_INK,
    COLOR_INK_SOFT,
    COLOR_NEGATIVE,
    COLOR_NEUTRAL,
    COLOR_POSITIVE,
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

REPORT_TITLE = "План продаж на месяц"

# Страница всегда двухколоночная: график слева, таблица справа (см.
# .plan-columns в report.css). Таблица при необходимости продолжается на
# следующей странице целиком — ограничение здесь только про читаемость
# самого графика: больше баров — подписи начинают налезать друг на друга,
# поэтому график показывает топ по плану, а таблица ниже/справа — всегда
# полностью, без ограничений.
CHART_MAX_ROWS = 20

# Имя файла на выходе (латиницей — чтобы не спотыкаться о кодировку
# заголовка Content-Disposition):
#   один магазин  -> Plan_Prodazh_2026-08_store12.pdf
#   все магазины  -> Plan_Prodazh_2026-08_vse_magaziny.pdf
PDF_FILENAME_TEMPLATE_SINGLE = "Plan_Prodazh_{month}_store{store_id}.pdf"
PDF_FILENAME_TEMPLATE_ALL = "Plan_Prodazh_{month}_vse_magaziny.pdf"

_MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

# sales/reports/newspaper/data/stocks.py
"""
Слой данных "Остатки" для Newspaper.

Источник истины для остатков — таблица ``stocks_data`` и связанные
справочники товаров (``corporate_items``, ``corporate_cattree``), как это
установлено по референсному файлу ``pages/matrix/data.py`` (Dash-приложение
матрицы ассортимента). Таблицы и поля ниже — те же самые, что использует
matrix/data.py:

    stocks_data:      item_id, init_date, tot_available, tot_ordered, total,
                       warehouse_stocks, warehouse_ordered
    corporate_items:   id, article, fullname, cat_id
    corporate_cattree: id, name, parent_id

Ключевое отличие от matrix/data.py: там данные тянутся через отдельный
SQLAlchemy ``ENGINE`` (аналитическая БД, к которой обращается Dash), здесь —
через штатное Django-соединение (``django.db.connection``), как это уже
делает ``sales_plan_report/data.py`` для ``orders_orderscf``. Это то же
самое единственное соединение, которым пользуется остальной Django-проект;
имя схемы (``djangodb.``) не указывается явно по той же причине, по которой
его не указывает sales_plan_report.

``warehouse_stocks`` — это JSON-массив строк вида
``["Европарк - 2 шт.", "ОСНОВНОЙ склад - 1364 шт."]``. Названия внутри —
это либо название магазина, либо название физического склада. Newspaper
пытается сопоставить эти названия со списком магазинов из cash-данных
(``data/cash.py``), чтобы название точки в отчёте по остаткам совпадало с
её названием в отчёте по кэшу. Но группировки "всё, что не магазин — в
одну кучу 'Склады'" здесь больше нет: каждое подразделение (магазин ИЛИ
физический склад) выводится отдельной строкой под своим собственным
названием, как оно записано в ``warehouse_stocks``. Единственное
исключение — остатки, для которых в ``warehouse_stocks`` вообще нет
разбивки по местам хранения (пусто/не заполнено); такие остатки помечены
как "не распределено по месту хранения", потому что для них правда нет
данных о том, где физически лежит товар.

Денежной оценки остатков здесь нет: реальной закупочной цены/себестоимости
в доступных данных нет, а ранняя версия отчёта считала оценку по средней
цене продажи за последние 90 дней — но эта оценка покрывала меньше
половины остатков (у товаров без продаж в окне взять цену неоткуда) и
только создавала вопросы к недостоверной цифре. Поэтому отчёт по остаткам
показывает только то, что в данных есть железно — количество.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

from django.db import connection

from sales.reports.sales_plan_report.utils import normalize_store_name

UNASSIGNED_LABEL = "Не распределено по месту хранения"


# ---------------------------------------------------------------------------
# Разбор warehouse_stocks / warehouse_ordered
# ---------------------------------------------------------------------------

_WAREHOUSE_ITEM_RE = re.compile(
    r"^\s*(.+?)\s*-\s*(-?\d+(?:[.,]\d+)?)\s*шт\.\s*$",
    flags=re.IGNORECASE,
)


def _parse_warehouse_breakdown(raw_value) -> dict:
    """
    Разбирает значение вида ["Европарк - 2 шт.", "ОСНОВНОЙ склад - 1364 шт."]
    в {"Европарк": 2.0, "ОСНОВНОЙ склад": 1364.0}.

    Логика идентична ``_parse_stock_qty`` из pages/matrix/data.py, но без
    зависимости от pandas/numpy — здесь работаем с обычными Python-типами,
    так как raw-курсор Django возвращает строки/None, а не DataFrame.
    """
    if raw_value is None:
        return {}

    text = str(raw_value).strip()
    if not text:
        return {}

    raw_items = None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            raw_items = parsed
    except (json.JSONDecodeError, TypeError, ValueError):
        raw_items = None

    result: dict = {}

    if raw_items is not None:
        for item in raw_items:
            match = _WAREHOUSE_ITEM_RE.match(str(item))
            if not match:
                continue
            name = match.group(1).strip().strip("'\"")
            if not name:
                continue
            try:
                qty = float(match.group(2).replace(",", "."))
            except (TypeError, ValueError):
                continue
            result[name] = result.get(name, 0.0) + qty
        return result

    # Фолбэк на случай, если значение хранится не как валидный JSON
    # (устаревший формат) — тот же приём, что и в matrix/data.py.
    matches = re.findall(
        r"[\"']?([^\"'\[\],]+?)[\"']?\s*-\s*(-?\d+(?:[.,]\d+)?)\s*шт\.",
        text,
        flags=re.IGNORECASE,
    )
    for name, qty in matches:
        name = str(name).strip().strip("'\"")
        if not name:
            continue
        try:
            qty_value = float(str(qty).replace(",", "."))
        except (TypeError, ValueError):
            continue
        result[name] = result.get(name, 0.0) + qty_value

    return result


def _dictfetchall(cursor) -> list:
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Запросы
# ---------------------------------------------------------------------------

def _fetch_latest_stock_rows() -> list:
    """
    Последний (по init_date) остаток по каждому item_id, с присоединённой
    категорией товара. Тот же принцип "последний остаток на item", что и в
    matrix/data.py (ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY
    init_date DESC)).
    """
    sql = """
        WITH ranked AS (
            SELECT
                s.item_id,
                s.init_date,
                s.tot_available,
                s.tot_ordered,
                s.total,
                s.warehouse_stocks,
                s.warehouse_ordered,
                ROW_NUMBER() OVER (
                    PARTITION BY s.item_id
                    ORDER BY s.init_date DESC
                ) AS rn
            FROM stocks_data s
        )
        SELECT
            r.item_id,
            r.init_date,
            r.tot_available,
            r.tot_ordered,
            r.total,
            r.warehouse_stocks,
            r.warehouse_ordered,
            i.fullname AS item_name,
            i.article AS item_article,
            COALESCE(cat.name, 'Без категории') AS cat_name
        FROM ranked r
        LEFT JOIN corporate_items i ON i.id = r.item_id
        LEFT JOIN corporate_cattree cat ON cat.id = i.cat_id
        WHERE r.rn = 1
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return _dictfetchall(cursor)


# ---------------------------------------------------------------------------
# Сопоставление складов/магазинов
# ---------------------------------------------------------------------------

def _build_store_matcher(store_names: list) -> dict:
    """
    normalize_store_name(warehouse_label) -> каноническое имя магазина
    (то же самое имя, что используется в cash-отчёте), если оно совпадает.
    """
    return {normalize_store_name(name): name for name in store_names if name}


def _resolve_bucket(warehouse_label: str, matcher: dict) -> str:
    """
    Возвращает название строки, под которой остаток попадёт в таблицу:
    каноническое имя магазина, если ярлык склада сопоставился с одним из
    магазинов кэш-отчёта, иначе — исходный ярлык места хранения как он
    есть (без группировки в общий "склад"), чтобы каждое подразделение
    было видно отдельно.
    """
    key = normalize_store_name(warehouse_label)
    if key in matcher:
        return matcher[key]

    # Точного совпадения нет — пробуем частичное совпадение по подстроке:
    # в warehouse_stocks название магазина иногда записано не 1-в-1 с тем,
    # как магазин называется в кэш-отчёте (доп. слово, номер точки,
    # порядок слов и т.п.). Если нормализованное имя магазина целиком
    # входит в ярлык склада (или наоборот) — считаем это тем же магазином.
    # Из нескольких кандидатов берём самое длинное совпадение — оно
    # надёжнее короткого.
    if key:
        candidates = [
            (name_norm, name)
            for name_norm, name in matcher.items()
            if name_norm and (name_norm in key or key in name_norm)
        ]
        if candidates:
            candidates.sort(key=lambda c: len(c[0]), reverse=True)
            return candidates[0][1]

    # Ни точного, ни частичного совпадения с магазином из кэш-отчёта нет —
    # это либо физический склад, либо подразделение, которого нет в
    # кэш-отчёте. Показываем его под тем именем, как оно записано в
    # warehouse_stocks, а не сваливаем в общий бакет.
    return str(warehouse_label).strip() or UNASSIGNED_LABEL


# ---------------------------------------------------------------------------
# Основной расчёт
# ---------------------------------------------------------------------------

def get_stocks_data(report_date, store_names: list) -> dict:
    """
    Строит "сырую" картину остатков компании на дату отчёта — только
    количество, без денежной оценки (см. пояснение в шапке модуля).

    :param report_date: дата отчёта (не используется в расчёте — остатки
        это последний известный срез, как и в matrix/data.py, где нет
        фильтра по дате остатка; параметр оставлен для единообразия
        сигнатуры и на случай, если понадобится в будущем).
    :param store_names: список имён магазинов из cash-отчёта — чтобы разбивка
        остатков по точкам была согласована с разбивкой по кэшу.
    """
    stock_rows = _fetch_latest_stock_rows()
    matcher = _build_store_matcher(store_names)

    company_qty_available = 0.0
    company_qty_ordered = 0.0
    company_qty_total = 0.0

    by_bucket = defaultdict(lambda: {
        "qty_available": 0.0,
        "qty_ordered": 0.0,
    })

    by_category = defaultdict(lambda: {
        "qty_available": 0.0,
    })

    sku_count_with_stock = 0

    for row in stock_rows:
        available = float(row["tot_available"] or 0)
        ordered = float(row["tot_ordered"] or 0)
        total_qty = float(row["total"] or 0)

        if available == 0 and ordered == 0 and total_qty == 0:
            continue

        sku_count_with_stock += 1

        company_qty_available += available
        company_qty_ordered += ordered
        company_qty_total += total_qty

        cat_name = row["cat_name"] or "Без категории"
        by_category[cat_name]["qty_available"] += available

        # Разбивка остатка товара по местам хранения (магазин/склад).
        breakdown = _parse_warehouse_breakdown(row["warehouse_stocks"])
        ordered_breakdown = _parse_warehouse_breakdown(row["warehouse_ordered"])

        if breakdown:
            for wh_label, qty in breakdown.items():
                bucket = _resolve_bucket(wh_label, matcher)
                by_bucket[bucket]["qty_available"] += qty
        elif available:
            # В warehouse_stocks для этой позиции вообще нет разбивки по
            # местам хранения — это единственный случай, когда мы не можем
            # показать остаток под конкретным подразделением, поэтому и
            # только поэтому он уходит в "не распределено".
            by_bucket[UNASSIGNED_LABEL]["qty_available"] += available

        if ordered_breakdown:
            for wh_label, qty in ordered_breakdown.items():
                bucket = _resolve_bucket(wh_label, matcher)
                by_bucket[bucket]["qty_ordered"] += qty
        elif ordered:
            by_bucket[UNASSIGNED_LABEL]["qty_ordered"] += ordered

    top_categories = sorted(
        (
            {"cat_name": name, **values}
            for name, values in by_category.items()
        ),
        key=lambda x: x["qty_available"],
        reverse=True,
    )

    # Все подразделения (магазины + физические склады), кроме псевдо-бакета
    # "не распределено" — он показывается в шаблоне отдельно, последней
    # строкой, а не смешивается со списком реальных подразделений.
    locations = {
        bucket: values
        for bucket, values in by_bucket.items()
        if bucket != UNASSIGNED_LABEL
    }
    unassigned_bucket = by_bucket.get(UNASSIGNED_LABEL, {
        "qty_available": 0.0,
        "qty_ordered": 0.0,
    })

    return {
        "report_date": report_date,
        "sku_count_with_stock": sku_count_with_stock,
        "company": {
            "qty_available": company_qty_available,
            "qty_ordered": company_qty_ordered,
            "qty_total": company_qty_total,
        },
        "by_store": locations,
        "unassigned_bucket": unassigned_bucket,
        "top_categories": top_categories,
    }

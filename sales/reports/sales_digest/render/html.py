# sales/reports/sales_digest/render/html.py
"""
Строит HTML нового отчёта "COSMORELAX Sales Digest".

Важно: этот файл НИЧЕГО не считает сам. Все цифры и графики берутся
напрямую из существующего sales.reports.sales_report.builder —
build_daily_sales_report_context(d) — той же функции, что использует
старый отчёт. sales_digest — это только новая верстка (шаблон + CSS)
поверх тех же самых данных, чтобы цифры двух отчётов никогда не
расходились.
"""

from __future__ import annotations

import math
import re
from datetime import date
from html import escape

import pandas as pd
from django.template.loader import render_to_string

from sales.dash_apps.dailysales.data import get_month_data, get_ytd_data
from sales.models import MV_Daily_Sales
from sales.reports.sales_report.builder import build_daily_sales_report_context
from sales.reports.sales_report.categories_data import get_mtd_categories_raw, get_ytd_categories_raw
from sales.reports.sales_report.kpi.categories_period_data import get_categories_for_period
from sales.reports.sales_report.kpi.manufacturers_period_data import get_manufacturers_for_period
from sales.reports.sales_report.managers.data import (
    get_mtd_managers_shipments_bundle,
    get_ytd_managers_shipments_bundle,
)
from sales.reports.sales_report.formatters import (
    fmt_delta_money,
    fmt_delta_pct,
    fmt_delta_short,
    fmt_int,
    fmt_money,
    fmt_pct,
)
from sales.reports.sales_report.stores.store_sales import get_store_sales_for_range
from sales.reports.sales_report.stores.performance.metrics import build_store_performance_block
from sales.reports.sales_report.stores.storegroup_categories_data import (
    get_mtd_storegroup_categories_raw,
    get_ytd_storegroup_categories_raw,
)
from sales.reports.sales_report.stores.storegroup_category_diagnostics import (
    build_delta_matrices_by_root,
    build_delta_qty_matrices_by_root,
    build_yoy_storegroup_category,
)
from sales.reports.sales_report.trends.mtd_cum_data import build_mtd_cum_series

from ..charts import (
    build_categories_compare_chart,
    build_categories_waterfall_chart,
    build_compare_delta_chart,
    build_manager_bar_chart,
    build_mtd_cum_chart,
    build_period_pareto_chart,
    build_prophet_fy_chart,
    build_store_monthly_bars_chart,
    build_stores_amount_chart,
    build_stores_share_pie,
    build_trend_chart,
    build_ytd_cum_chart,
)
from ..config import (
    COLOR_NEGATIVE,
    COLOR_POSITIVE,
    COMPANY_BRAND_NAME,
    COMPANY_LEGAL_NAME,
    COMPANY_WEBSITE,
    REPORT_TITLE,
)

TEMPLATE_NAME = "reports/sales_digest/report.html"

_WEEKDAYS_RU = [
    "Понедельник", "Вторник", "Среда", "Четверг",
    "Пятница", "Суббота", "Воскресенье",
]

_REPORT_TYPE_LABEL = {
    "daily": "Отчёт за день",
    "weekly": "Отчёт за неделю",
    "monthly": "Отчёт за месяц",
}


def _movers_str(movers: list) -> str:
    """
    'Категория А (+120 000 ₽), Категория Б (+80 000 ₽)' — собираем строку
    здесь, а не циклом в шаблоне (шаблон рендерится и Django, и нашим
    Jinja2-тестом при разработке, а forloop.last/loop.last в них разные).
    """
    if not movers:
        return ""
    return ", ".join(f"{m['cat']} ({m['d_amount']})" for m in movers)


def _fmt_pp(v: float | None) -> str:
    if v is None or not math.isfinite(v):
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}%".replace(".", ",")


def _tone_class(v: float | None) -> str:
    if v is None or not math.isfinite(v) or v == 0:
        return "dev-flat"
    return "dev-positive" if v > 0 else "dev-negative"


def _trend_badges(trend_rows: list) -> dict:
    """
    'К среднему' / 'К прошлому периоду' — та же логика, что была в старом
    trend_chart.py (build_trend_chart_svg), просто вынесена в чистый Python,
    т.к. сам график теперь ничего не считает — только рисует готовые числа.
    """
    values = [float(t["amount_raw"]) for t in trend_rows if t.get("amount_raw") is not None]
    if not values:
        return {"vs_avg": "—", "vs_avg_class": "dev-flat", "vs_prev": "—", "vs_prev_class": "dev-flat"}

    curr_idx = next((i for i, t in enumerate(trend_rows) if t.get("is_current")), len(trend_rows) - 1)
    avg = sum(values) / len(values)
    curr = values[curr_idx]
    prev = values[curr_idx - 1] if curr_idx - 1 >= 0 else None

    vs_avg = ((curr - avg) / avg * 100) if avg else None
    vs_prev = ((curr - prev) / prev * 100) if prev else None

    return {
        "vs_avg": _fmt_pp(vs_avg),
        "vs_avg_class": _tone_class(vs_avg),
        "vs_prev": _fmt_pp(vs_prev),
        "vs_prev_class": _tone_class(vs_prev),
    }
    
    

def _build_trend_insight(trend_rows: list, report_type: str) -> dict | None:
    if not trend_rows:
        return None

    rows = [
        r for r in trend_rows
        if r.get("amount_raw") is not None
    ]

    if not rows:
        return None

    curr_idx = next(
        (
            i for i, r in enumerate(rows)
            if r.get("is_current")
        ),
        len(rows) - 1,
    )

    curr = rows[curr_idx]
    prev = rows[curr_idx - 1] if curr_idx > 0 else None

    amounts = [
        float(r["amount_raw"])
        for r in rows
    ]

    curr_amount = float(curr["amount_raw"])
    avg_amount = sum(amounts) / len(amounts)

    max_row = max(
        rows,
        key=lambda r: float(r["amount_raw"]),
    )

    min_row = min(
        rows,
        key=lambda r: float(r["amount_raw"]),
    )

    max_amount = float(max_row["amount_raw"])
    min_amount = float(min_row["amount_raw"])

    # ---------------------------------------------------------
    # Ранг текущего результата
    # ---------------------------------------------------------
    sorted_amounts = sorted(
        amounts,
        reverse=True,
    )

    current_rank = (
        sorted_amounts.index(curr_amount) + 1
    )

    # ---------------------------------------------------------
    # Сколько периодов выше / ниже среднего
    # ---------------------------------------------------------
    above_avg_count = sum(
        1 for v in amounts
        if v > avg_amount
    )

    below_avg_count = sum(
        1 for v in amounts
        if v < avg_amount
    )

    # ---------------------------------------------------------
    # Насколько текущий результат ниже максимума
    # ---------------------------------------------------------
    gap_to_max = max_amount - curr_amount

    gap_to_max_pct = (
        gap_to_max / max_amount * 100
        if max_amount
        else None
    )

    # ---------------------------------------------------------
    # Возвраты: текущий vs предыдущий период
    # ---------------------------------------------------------
    curr_cr_raw = curr.get("cr_raw")
    prev_cr_raw = (
        prev.get("cr_raw")
        if prev
        else None
    )

    cr_delta = None
    cr_delta_pct = None

    try:
        if curr_cr_raw is not None and prev_cr_raw is not None:
            curr_cr_raw = float(curr_cr_raw)
            prev_cr_raw = float(prev_cr_raw)

            cr_delta = curr_cr_raw - prev_cr_raw

            if prev_cr_raw:
                cr_delta_pct = (
                    cr_delta / prev_cr_raw * 100
                )
    except Exception:
        curr_cr_raw = None
        prev_cr_raw = None
        cr_delta = None
        cr_delta_pct = None

    labels = {
        "daily": {
            "period": "Текущий день",
            "period_plural": "дней",
        },
        "weekly": {
            "period": "Текущая неделя",
            "period_plural": "недель",
        },
        "monthly": {
            "period": "Текущий месяц",
            "period_plural": "месяцев",
        },
    }

    wording = labels.get(
        report_type,
        labels["daily"],
    )

    return {
        "period_label": wording["period"],
        "period_plural": wording["period_plural"],

        "count": len(rows),

        "current_rank": current_rank,

        "max_amount": fmt_money(max_amount),
        "max_label": max_row.get("label") or "—",

        "min_amount": fmt_money(min_amount),
        "min_label": min_row.get("label") or "—",

        "gap_to_max": fmt_money(gap_to_max),
        "gap_to_max_pct": gap_to_max_pct,

        "above_avg_count": above_avg_count,
        "below_avg_count": below_avg_count,

        "curr_cr": (
            fmt_money(curr_cr_raw)
            if curr_cr_raw is not None
            else curr.get("cr")
        ),

        "prev_cr": (
            fmt_money(prev_cr_raw)
            if prev_cr_raw is not None
            else (
                prev.get("cr")
                if prev
                else None
            )
        ),

        "cr_delta": (
            fmt_delta_money(cr_delta)
            if cr_delta is not None
            else None
        ),

        "cr_delta_pct": cr_delta_pct,
        "cr_worse": (
            cr_delta is not None
            and cr_delta > 0
        ),
    }

def _enrich_period_text(period_text: dict | None) -> None:
    if not period_text:
        return
    for key in ("mtd_text", "ytd_text"):
        block = period_text.get(key)
        if not block:
            continue
        block["movers_up_str"] = _movers_str(block.get("movers_up") or [])
        block["movers_down_str"] = _movers_str(block.get("movers_down") or [])
        



def _parse_pct_text(value) -> float | None:
    """
    '−4,9%' / '+10,6%' / '-3.2%' -> float
    """
    if value in (None, "", "—"):
        return None

    try:
        s = str(value).strip()
        s = (
            s.replace("%", "")
            .replace("−", "-")
            .replace(",", ".")
            .replace(" ", "")
        )
        return float(s)
    except (TypeError, ValueError):
        return None


def _build_period_insight(block: dict | None) -> dict | None:
    """
    Аналитический вывод MTD/YTD только для sales_digest.
    Используем уже готовые данные period_text.
    """
    if not block:
        return None

    amount_pct = _parse_pct_text(block.get("yoy_amount_pct"))
    quant_pct = _parse_pct_text(block.get("yoy_quant_pct"))

    # Изменение выручки на единицу:
    # (1 + изменение выручки) / (1 + изменение количества) - 1
    revenue_per_unit_pct = None

    if (
        amount_pct is not None
        and quant_pct is not None
        and (100.0 + quant_pct) != 0
    ):
        revenue_per_unit_pct = (
            (1.0 + amount_pct / 100.0)
            / (1.0 + quant_pct / 100.0)
            - 1.0
        ) * 100.0

    return {
        "amount_pct": amount_pct,
        "quant_pct": quant_pct,

        "amount_is_positive": (
            amount_pct is not None
            and amount_pct >= 0
        ),

        "quant_is_positive": (
            quant_pct is not None
            and quant_pct >= 0
        ),

        "revenue_per_unit_pct": revenue_per_unit_pct,

        "movers_up": block.get("movers_up") or [],
        "movers_down": block.get("movers_down") or [],
    }

_STRIPPED_METRICS = ("Заказы", "Ср. чек")


def _strip_metric_rows(table_html: str, metrics: tuple[str, ...] = _STRIPPED_METRICS) -> str:
    """
    Таблицы MTD/YTD приходят готовым HTML из sales.print_utils
    (build_mtd_table/build_ytd_table) — тем же самым, что использует старый
    отчёт, поэтому саму функцию не трогаем (иначе поедет старый отчёт).
    Здесь просто вырезаем строки "Заказы"/"Ср. чек" из готовой разметки —
    в sales_digest эти метрики не нужны (дублируют оборот/выручку).
    """
    if not table_html:
        return table_html
    out = table_html
    for metric in metrics:
        out = re.sub(rf"<tr><td class='metric'>{re.escape(metric)}</td>.*?</tr>", "", out)
    return out


def _build_ytd_cum_series(df_ytd_raw, report_date: date) -> dict:
    """
    Аналог build_mtd_cum_series (sales_report/trends/mtd_cum_data.py), но
    накопление помесячно (get_ytd_data отдаёт по одной агрегированной
    строке на месяц, с датой = LAST_DAY месяца), а не по дням — тот модуль
    жёстко завязан на один месяц и для YTD не подходит. Считается заново
    из df_ytd_raw (get_ytd_data) — та же чистая функция без побочных
    эффектов, что и остальные повторные вычисления в этом файле.

    report_date оставлен в сигнатуре для совместимости с вызовом на
    строке ~1217, но здесь больше не используется для фильтрации: сама
    get_ytd_data(d) уже ограничивает выборку датой отчёта на уровне SQL
    (см. её WHERE date < d + 1 day), включая текущий незакрытый месяц.
    """
    empty = {"series_cur": [], "series_ly": []}
    if df_ytd_raw is None or len(df_ytd_raw) == 0:
        return empty

    df = df_ytd_raw.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return empty

    # ВАЖНО: get_ytd_data() агрегирует продажи по месяцам (GROUP BY
    # LAST_DAY(date)) — колонка "date" здесь это последний день месяца,
    # а НЕ дата последней реальной записи, и SQL там же уже ограничивает
    # выборку датой отчёта (report_date). Раньше здесь была повторная
    # фильтрация "date <= report_date" / "doy <= doy_max" — для текущего
    # (ещё не закрытого) месяца LAST_DAY всегда позже report_date, поэтому
    # весь текущий месяц вырезался целиком и график обрывался на конце
    # последнего ПОЛНОГО месяца (расходясь с таблицей, где такой фильтрации
    # нет). Данные уже корректно ограничены на уровне SQL — повторно
    # фильтровать по дате здесь не нужно и неверно.
    df["amount"] = pd.to_numeric(df.get("amount"), errors="coerce").fillna(0.0)
    df["year"] = df["date"].dt.year

    years = sorted(df["year"].unique())

    def _make(y: int) -> list[dict]:
        dd = df[df["year"] == y].sort_values("date").copy()
        dd["cum_raw"] = dd["amount"].cumsum()
        return [{"label": r.date.strftime("%d.%m"), "cum_raw": float(r.cum_raw)} for r in dd.itertuples()]

    if len(years) < 2:
        return {"series_cur": _make(years[-1]), "series_ly": []}

    y_prev, y_curr = years[-2], years[-1]
    return {"series_cur": _make(y_curr), "series_ly": _make(y_prev)}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


_MATRIX_POS_RGB = _hex_to_rgb(COLOR_POSITIVE)
_MATRIX_NEG_RGB = _hex_to_rgb(COLOR_NEGATIVE)


def _matrix_cell_style(v: float, vmax: float) -> str:
    """
    Деликатная heatmap-заливка ячейки матрицы (магазин × категория) —
    непрозрачность зависит от силы отклонения относительно максимума в
    матрице, цвет — знак (зелёный/терракотовый), те же токены, что и
    остальные "хорошо/плохо" сигналы отчёта (COLOR_POSITIVE/COLOR_NEGATIVE).
    Обычные <table> с background-color в ячейке — самый надёжный способ
    показать heatmap под WeasyPrint (без CSS grid/flex-хитростей).

    Диапазон непрозрачности сознательно светлее, чем в первой версии
    (было 0.08–0.40) — по фидбэку матрицы выглядели слишком "плотными" и
    тяжёлыми рядом со сдержанной палитрой остального отчёта; теперь
    заливка — лёгкий акцент, а не основной носитель информации (её несёт
    само число в ячейке).
    """
    if vmax <= 0 or abs(v) < 1e-9:
        return ""
    a = min(1.0, abs(v) / vmax)
    alpha = 0.05 + a * 0.18
    r, g, b = _MATRIX_POS_RGB if v > 0 else _MATRIX_NEG_RGB
    return f"background: rgba({r}, {g}, {b}, {alpha:.2f});"


def _fmt_qty_delta_short(v: float) -> str:
    """
    Δ количества, короткая запись (аналог fmt_delta_short, но для штук,
    без денежного форматтера) — используется в матрицах Δшт.
    """
    if v is None or not math.isfinite(v):
        return "—"
    sign = "+" if v > 0 else "−" if v < 0 else ""
    av = abs(float(v))
    if av >= 1000:
        return f"{sign}{av / 1000:.1f} тыс шт".replace(".", ",")
    return f"{sign}{av:,.0f} шт".replace(",", " ")


def _render_matrix_table(
    root: str, mat, fmt_fn, metric_label: str = "", max_cols: int = 10,
) -> tuple[str, int]:
    """
    Рендерит одну матрицу "магазин × категория" (root-категория) как обычную
    HTML-таблицу в теме sales_digest (.mini-table), с heatmap-заливкой ячеек
    по знаку/силе изменения. Данные приходят уже готовыми (pivot-таблица) из
    старого sales_report.stores.storegroup_category_diagnostics — здесь
    только своя разметка вместо старой compare-table--matrix.

    metric_label — короткая пометка метрики матрицы ("Δ, ₽" / "Δ, шт"),
    выводится рядом с названием root-категории в заголовке матрицы. Нужна
    с тех пор, как рублёвая и количественная матрицы одной категории
    выводятся парой подряд (см. _build_store_category_matrices) — раньше
    метрика была понятна из заголовка всей группы (.subblock-head), теперь
    группировка идёт по категории, а не по метрике, так что подпись метрики
    нужна у каждой отдельной матрицы.

    Возвращает (html, n_cols) — количество реальных колонок-категорий нужно
    вызывающему коду (_build_store_category_matrices/_pack_matrix_html), чтобы
    решить, узкая это матрица (тогда её можно поставить в пару с другой
    узкой матрицей в один ряд) или широкая (остаётся на всю ширину).
    """
    if mat is None or mat.empty:
        return "", 0

    cols = list(mat.columns)[:max_cols]
    sub = mat[cols]
    vmax = float(sub.abs().to_numpy().max()) if not sub.empty else 0.0

    thead_cells = "".join(
        f"<th class='num' title='{escape(str(c))}'>{escape(_short_label_ellipsis(str(c), 14))}</th>"
        for c in cols
    )

    body_rows = []
    for idx, row in sub.iterrows():
        cells = [f"<td class='store-cell'>{escape(str(idx))}</td>"]
        for c in cols:
            v = float(row[c])
            text = "" if abs(v) < 1e-9 else fmt_fn(v)
            style = _matrix_cell_style(v, vmax)
            cells.append(f"<td class='num matrix-cell' style='{style}'>{text}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    title_html = escape(str(root))
    if metric_label:
        title_html += f" <span class='matrix-metric-tag'>{escape(metric_label)}</span>"

    html = (
        "<div class='matrix-block'>"
        f"<div class='matrix-block-title'>{title_html}</div>"
        "<table class='mini-table matrix-table'>"
        f"<thead><tr><th>Магазин</th>{thead_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</div>"
    )
    return html, len(cols)


_MATRIX_NARROW_MAX_COLS = 3


def _pack_matrix_html(entries: list[tuple[str, int]]) -> str:
    """
    Узкие матрицы (мало колонок-категорий, ≤3 — например, магазин × 1-2
    категории) занимают целую строку на всю ширину полосы почти пустой
    (по фидбэку это выглядело неаккуратно) — группируем такие матрицы по
    две в ряд (двухколоночная раскладка, .matrix-row в CSS, тот же приём,
    что и .two-col в остальном отчёте). Широкие матрицы (обычный случай)
    остаются на всю ширину, как и раньше.
    """
    out: list[str] = []
    pending: str | None = None
    for html, n_cols in entries:
        if not html:
            continue
        if 0 < n_cols <= _MATRIX_NARROW_MAX_COLS:
            if pending is None:
                pending = html
            else:
                out.append(f"<div class='matrix-row'>{pending}{html}</div>")
                pending = None
        else:
            if pending is not None:
                out.append(pending)
                pending = None
            out.append(html)
    if pending is not None:
        out.append(pending)
    return "".join(out)


def _short_label_ellipsis(label: str, max_len: int) -> str:
    return label if len(label) <= max_len else label[: max_len - 1] + "…"


def _build_store_category_matrices(d: date) -> dict:
    """
    Раздел IX: матрицы изменений (магазин × категория) в рублях и в штуках,
    MTD и YTD — та же самая расчётная цепочка, что и в старом отчёте
    (Приложение A): get_*_storegroup_categories_raw -> build_yoy_storegroup_category
    -> build_delta_matrices_by_root / build_delta_qty_matrices_by_root. Здесь
    только своя разметка (см. _render_matrix_table) вместо старой
    compare-table--matrix.

    Группировка вывода — ПО КАТЕГОРИИ, затем по метрике (по фидбэку: для
    каждой root-категории рублёвая матрица должна идти сразу за ней —
    количественная, парой, а не все рублёвые матрицы отдельным блоком и все
    количественные отдельным блоком).

    ВАЖНО (фикс парности, второй заход): build_delta_matrices_by_root и
    build_delta_qty_matrices_by_root каждый САМ ранжирует top_roots по своей
    метрике (Δ₽ или Δшт) — при вызове обоих с одинаковым top_roots=4 это два
    НЕЗАВИСИМЫХ топа, которые пересекаются только случайно. Первый фикс решил
    это только для одной стороны: money-топ-4 брался как основной список, а
    qty запрашивался с top_roots=9999 (полный словарь), чтобы найти
    количественную пару для каждой money-категории. Но money по-прежнему
    запрашивался с top_roots=4 — поэтому для категорий, которые попадали в
    qty-топ-4, но НЕ входили в money-топ-4 (например, "Посуда"), поиск
    money_by_root.get(root) шёл по словарю всего из 4 записей и ожидаемо не
    находил пару, хотя в полном money-списке она могла быть.

    Исправлено симметрично: ОБЕ функции вызываются один раз каждая с
    заведомо большим top_roots (весь список root-категорий, отранжированный
    по своей метрике) — money_matrices_all и qty_matrices_all — это два
    полных словаря {root: матрица} по деньгам и по штукам для ВСЕХ
    root-категорий сразу. Итоговый список отображаемых категорий (roots_order)
    строится как объединение первых 4 записей money_matrices_all (money-топ-4)
    и первых 4 записей qty_matrices_all (qty-топ-4), без дублей, в порядке
    "сначала money-топ-4, затем оставшиеся qty-топ-4". Для КАЖДОЙ категории
    из этого объединённого списка пара берётся из ПОЛНЫХ словарей
    (money_by_root.get(root), qty_by_root.get(root)) — то есть с обеих сторон
    ищем во всём списке, а не только в чужом топ-4. Если для категории
    реально нет данных с одной из сторон (например, есть выручка, но 0
    зафиксированных проданных штук, или наоборот) — это единственный случай,
    когда матрица останется без пары (money-only или qty-only), и это
    поведение уже поддерживает _pack_matrix_html/report.html (см. условную
    разметку там же).

    _pack_matrix_html (двухколоночная раскладка для узких матриц, ≤3
    колонки-категории) применяется ВНУТРИ пары одной категории — это отдаёт
    ровно [money_entry, qty_entry] на категорию, поэтому узкие матрицы
    разных категорий никогда не попадают в один ряд.
    """
    out: dict = {}
    periods = (
        ("mtd", get_mtd_storegroup_categories_raw),
        ("ytd", get_ytd_storegroup_categories_raw),
    )
    for period_key, getter in periods:
        df_raw = getter(d)
        yoy = build_yoy_storegroup_category(df_raw)
        if yoy is None or yoy.empty:
            out[period_key] = {"has": False}
            continue

        y_prev = yoy.attrs.get("y_prev")
        y_curr = yoy.attrs.get("y_curr")

        # top_roots заведомо больше реального числа root-категорий — нужны
        # ПОЛНЫЕ ранжированные списки (и по Δ₽, и по Δшт), чтобы для любой
        # категории из объединённого топа найти пару с обеих сторон (см.
        # комментарий выше в докстринге про фикс парности).
        money_matrices_all = build_delta_matrices_by_root(
            yoy, top_roots=9999, top_cats_per_root=6, top_groups=14, min_abs_total=1.0,
        )
        qty_matrices_all = build_delta_qty_matrices_by_root(
            yoy, top_roots=9999, top_cats_per_root=6, top_groups=14, min_abs_total=1.0,
        )
        money_matrices_top = money_matrices_all[:4]
        qty_matrices_top = qty_matrices_all[:4]

        money_by_root = dict(money_matrices_all)
        qty_by_root = dict(qty_matrices_all)

        roots_order: list[str] = []
        for root, _ in money_matrices_top:
            if root not in roots_order:
                roots_order.append(root)
        for root, _ in qty_matrices_top:
            if root not in roots_order:
                roots_order.append(root)

        category_blocks: list[str] = []
        for root in roots_order:
            pair_entries = []
            money_df = money_by_root.get(root)
            if money_df is not None:
                pair_entries.append(_render_matrix_table(root, money_df, fmt_delta_short, "Δ, ₽"))
            qty_df = qty_by_root.get(root)
            if qty_df is not None:
                pair_entries.append(
                    _render_matrix_table(root, qty_df, _fmt_qty_delta_short, "Δ, шт")
                )
            block_html = _pack_matrix_html(pair_entries)
            if block_html:
                category_blocks.append(block_html)

        out[period_key] = {
            "has": bool(category_blocks),
            # str(), не сырой int — см. комментарий в _build_store_perf_context
            # (Django USE_THOUSAND_SEPARATOR ломает год как "2,026").
            "y_prev": str(y_prev) if y_prev is not None else "",
            "y_curr": str(y_curr) if y_curr is not None else "",
            "category_blocks_html": category_blocks,
        }
    return out


def _store_perf_rows(perf_df, top_n: int = 30) -> list[dict]:
    """
    Строки для мини-таблиц "KPI по магазинам" (MTD/YTD) — раздел II. Данные —
    те же самые DataFrame'ы (curr/prev/delta по магазину), что строила
    старая stores/performance/metrics.build_store_performance_block и
    рендерила таблицей render_store_kpi_table; здесь просто своё
    форматирование под sales_digest (fmt_money/fmt_pct из formatters.py,
    _tone_class — тот же хелпер, что и для остальных отклонений отчёта).
    """
    if perf_df is None or perf_df.empty:
        return []
    df = perf_df.sort_values("amount_curr", ascending=False).head(top_n)
    rows: list[dict] = []
    for _, r in df.iterrows():
        delta = float(r.get("delta_amount") or 0.0)
        delta_pct = r.get("delta_amount_pct")
        share = r.get("share_curr")
        rtr = r.get("rtr_ratio_curr")
        rows.append({
            "store": r.get("store") or "—",
            "amount_curr": fmt_money(r.get("amount_curr")),
            "delta": fmt_delta_money(delta),
            "delta_pct": fmt_delta_pct(delta_pct) if delta_pct is not None else "—",
            "delta_class": _tone_class(delta),
            "share": fmt_pct(share) if share is not None else "—",
            "rtr": fmt_pct(rtr) if rtr is not None else "—",
        })
    return rows


def _store_perf_long_df(perf_df, y_prev: int, y_curr: int):
    """
    Разворачивает "широкий" DataFrame (amount_curr/amount_prev по магазину)
    в "длинный" (year/cat_name/amount), чтобы переиспользовать уже готовый
    build_categories_compare_chart (парные горизонтальные бары curr vs prev)
    без нового кода графика — тот же приём, что и с остальными графиками
    sales_digest: не рисуем заново то, для чего уже есть чартбилдер в нужной
    палитре, только переставляем данные под его сигнатуру.
    """
    if perf_df is None or perf_df.empty:
        return pd.DataFrame(columns=["year", "cat_name", "amount"])
    rows = []
    for _, r in perf_df.iterrows():
        store = r.get("store") or "—"
        rows.append({"year": y_prev, "cat_name": store, "amount": float(r.get("amount_prev") or 0.0)})
        rows.append({"year": y_curr, "cat_name": store, "amount": float(r.get("amount_curr") or 0.0)})
    return pd.DataFrame(rows)



def _build_store_insight(perf_df) -> dict | None:
    if perf_df is None or perf_df.empty:
        return None

    df = perf_df.copy()

    total_curr = float(df["amount_curr"].sum())
    total_prev = float(df["amount_prev"].sum())
    total_delta = total_curr - total_prev

    total_delta_pct = (
        (total_delta / total_prev * 100)
        if total_prev
        else None
    )

    # ---------------------------------------------------------
    # Лидеры по доле в текущей выручке
    # ---------------------------------------------------------
    leaders = (
        df.sort_values("amount_curr", ascending=False)
        .head(2)
    )

    leaders_rows = []
    for _, r in leaders.iterrows():
        share = (
            float(r["amount_curr"]) / total_curr * 100
            if total_curr
            else 0
        )

        leaders_rows.append({
            "store": r["store"],
            "share": share,
        })

    top2_share = sum(x["share"] for x in leaders_rows)

    # ---------------------------------------------------------
    # Рост
    # ---------------------------------------------------------
    up = (
        df[df["delta_amount"] > 0]
        .sort_values("delta_amount", ascending=False)
        .head(3)
    )

    movers_up = [
        {
            "store": r["store"],
            "delta": fmt_delta_money(float(r["delta_amount"])),
        }
        for _, r in up.iterrows()
    ]

    # ---------------------------------------------------------
    # Снижение
    # ---------------------------------------------------------
    down = (
        df[df["delta_amount"] < 0]
        .sort_values("delta_amount", ascending=True)
        .head(3)
    )

    movers_down = [
        {
            "store": r["store"],
            "delta": fmt_delta_money(float(r["delta_amount"])),
        }
        for _, r in down.iterrows()
    ]

    # ---------------------------------------------------------
    # Возвраты — топ по сумме возвратов
    # ---------------------------------------------------------
    returns_df = (
        df[df["cr_curr"] > 0]
        .sort_values("cr_curr", ascending=False)
        .head(3)
    )

    returns = []

    for _, r in returns_df.iterrows():
        cr = float(r["cr_curr"] or 0)
        dt = float(r["dt_curr"] or 0)

        ratio = (cr / dt * 100) if dt else 0

        returns.append({
            "store": r["store"],
            "amount": fmt_money(cr),
            "ratio": ratio,
        })

    return {
        "total_curr": total_curr,
        "total_prev": total_prev,
        "total_delta": fmt_delta_money(total_delta),
        "total_delta_pct": total_delta_pct,
        "is_positive": total_delta >= 0,

        "leaders": leaders_rows,
        "top2_share": top2_share,

        "movers_up": movers_up,
        "movers_down": movers_down,

        "returns": returns,
    }


def _build_store_perf_context(d: date) -> dict:
    """
    Раздел "KPI по магазинам · MTD и YTD" (II) — расчёт полностью из старого
    sales_report.stores.performance.metrics.build_store_performance_block
    (та же функция, что использует старый отчёт для этих же самых цифр,
    см. stores/performance/block.py -> build_store_performance_html_block).
    Здесь берём НЕ готовый HTML, а сырые DataFrame'ы (ytd/mtd) и
    рисуем/форматируем их заново в теме COSMORELAX.

    Помесячная динамика по магазинам: раньше была спарклайн-сетка (много
    узких колонок, пунктир/сплошная линия) — убрана по фидбэку (плохо
    читалась, названия магазинов резались многоточием). По следующему
    фидбэку раздел вернули, но перерисовали заново: сгруппированные
    столбики (build_store_monthly_bars_chart, 2 колонки × 3 строки, топ-6
    магазинов YTD), данные — тот же самый "monthly" DataFrame из
    build_store_performance_block, который раньше здесь просто не
    использовался.
    """
    data = build_store_performance_block(d)
    if not data.get("has"):
        return {"has": False}

    y_curr, y_prev = data["y_curr"], data["y_prev"]
    ytd_df, mtd_df, monthly_df = data["ytd"], data["mtd"], data["monthly"]

    return {
        "has": True,
        # str(), а не сырой int: Django-шаблоны (см. TEMPLATES/USE_THOUSAND_SEPARATOR
        # в настройках проекта) форматируют числовые значения контекста
        # разделителем тысяч, из-за чего год в бейдже/подписи выводился как
        # "2,026" вместо "2026" — год не количественная величина, разделитель
        # тысяч ему не нужен. Сам build_store_performance_block (старый
        # sales_report) не трогаем, чтобы не сломать старый отчёт — просто
        # переформатируем значение здесь, перед выводом в шаблон sales_digest.
        "y_curr": str(y_curr),
        "y_prev": str(y_prev),
        "mtd_rows": _store_perf_rows(mtd_df),
        "ytd_rows": _store_perf_rows(ytd_df),
        "mtd_chart_svg": build_categories_compare_chart(
            _store_perf_long_df(mtd_df, y_prev, y_curr), top_n=12,
        ),
        "ytd_chart_svg": build_categories_compare_chart(
            _store_perf_long_df(ytd_df, y_prev, y_curr), top_n=12,
        ),
        "monthly_chart_svg": build_store_monthly_bars_chart(
            monthly_df, y_curr, y_prev, top_n=6,
        ),
        
        "insights": {
            "mtd": _build_store_insight(mtd_df),
            "ytd": _build_store_insight(ytd_df),
        },
    }


# Приоритетный порядок категорий (раздел X, "YTD по подкатегориям") — эти
# категории для бизнеса важнее прочих, поэтому должны идти первыми. Названия
# — как в corporate_cattree.name (то же поле, что отдаёт get_ytd_categories_raw
# -> cat_name -> subcats_ytd "cat"); если реальное написание в данных
# отличается (например, где-то используется составное имя вроде "Диваны и
# кресла" вместо "Диваны"), эта категория просто не попадёт в приоритетную
# группу и уйдёт в "остальные" по прежней сортировке — раздел всё равно не
# сломается, порядок внутри "остальных" сохраняется как раньше (по убыванию
# выручки YTD).
#
# По фидбэку раздел больше НЕ обрезается по числу категорий — показываем
# ВСЕ категории (раньше здесь был лимит топ-8 с подписью "ещё N категорий не
# показано"; убрано, раздел теперь просто занимает больше одной страницы —
# для этого у каждого .subcats-cat-block есть break-inside: avoid, см.
# static/sales_digest/report.css, чтобы таблица одной категории не рвалась
# посреди страницы).
_SUBCATS_YTD_PRIORITY = ["Столы", "Стулья", "Кресла", "Хранение", "Диваны", "Свет"]


def _reorder_subcats_ytd(subcats_ytd: dict | None) -> None:
    """
    subcats_ytd (раздел X) приходит уже готовым из старого builder'а
    (build_subcategories_ytd_context, категории уже отсортированы по
    текущей выручке YTD) — здесь только выносим вперёд приоритетные
    категории (_SUBCATS_YTD_PRIORITY) в заданном порядке, без усечения
    списка. Остальные категории идут следом в прежнем порядке (по убыванию
    выручки YTD, как отдаёт builder).
    """
    if not subcats_ytd or not subcats_ytd.get("has"):
        return
    cats = subcats_ytd.get("cats") or []
    if not cats:
        return

    by_name = {c.get("cat"): c for c in cats}
    used: set = set()
    ordered: list = []
    for name in _SUBCATS_YTD_PRIORITY:
        c = by_name.get(name)
        if c is not None:
            ordered.append(c)
            used.add(name)
    for c in cats:
        if c.get("cat") not in used:
            ordered.append(c)

    subcats_ytd["cats"] = ordered
    
    
def _build_forecast_insight(
    df_actual: pd.DataFrame,
    forecast_df: pd.DataFrame,
    report_date: date,
) -> dict | None:

    if (
        df_actual is None
        or df_actual.empty
        or forecast_df is None
        or forecast_df.empty
    ):
        return None

    # =========================================================
    # ФАКТ YTD
    # =========================================================
    actual = df_actual.copy()
    actual["date"] = pd.to_datetime(actual["date"], errors="coerce")
    actual["amount"] = pd.to_numeric(actual["amount"], errors="coerce").fillna(0.0)

    actual = actual[
        (actual["date"].dt.year == report_date.year)
        & (actual["date"].dt.date <= report_date)
    ]

    ytd_actual = float(actual["amount"].sum())

    # =========================================================
    # ПРОГНОЗ ДО КОНЦА ГОДА
    # =========================================================
    fc = forecast_df.copy()

    if "ds" not in fc.columns or "yhat" not in fc.columns:
        return None

    fc["ds"] = pd.to_datetime(fc["ds"], errors="coerce")
    fc["yhat"] = pd.to_numeric(fc["yhat"], errors="coerce").fillna(0.0)

    year_end = pd.Timestamp(date(report_date.year, 12, 31))

    future = fc[
        (fc["ds"].dt.date > report_date)
        & (fc["ds"] <= year_end)
    ].copy()

    if future.empty:
        return None

    remaining_forecast = float(future["yhat"].sum())
    fy_forecast = ytd_actual + remaining_forecast

    # =========================================================
    # СКОЛЬКО ПРОГНОЗА УЖЕ ВЫПОЛНЕНО
    # =========================================================
    done_pct = (
        ytd_actual / fy_forecast * 100
        if fy_forecast
        else None
    )

    remaining_pct = (
        remaining_forecast / fy_forecast * 100
        if fy_forecast
        else None
    )

    # =========================================================
    # ТЕМП ДО КОНЦА ГОДА
    # =========================================================
    days_elapsed = report_date.timetuple().tm_yday
    days_left = (date(report_date.year, 12, 31) - report_date).days

    actual_daily_pace = (
        ytd_actual / days_elapsed
        if days_elapsed
        else None
    )

    required_daily_pace = (
        remaining_forecast / days_left
        if days_left
        else None
    )

    pace_delta_pct = (
        (required_daily_pace - actual_daily_pace)
        / actual_daily_pace
        * 100
        if actual_daily_pace
        and required_daily_pace is not None
        else None
    )

    # =========================================================
    # ПРОГНОЗ ПО ОСТАВШИМСЯ МЕСЯЦАМ
    # =========================================================
    future["month_no"] = future["ds"].dt.month

    monthly = (
        future.groupby("month_no", as_index=False)["yhat"]
        .sum()
    )

    RU_MONTHS_FULL = {
        1: "январь",
        2: "февраль",
        3: "март",
        4: "апрель",
        5: "май",
        6: "июнь",
        7: "июль",
        8: "август",
        9: "сентябрь",
        10: "октябрь",
        11: "ноябрь",
        12: "декабрь",
    }

    strongest_month = None

    if not monthly.empty:
        strongest = monthly.loc[monthly["yhat"].idxmax()]

        strongest_month = {
            "name": RU_MONTHS_FULL.get(
                int(strongest["month_no"]),
                "—",
            ),
            "amount": fmt_money(float(strongest["yhat"])),
        }

    return {
        "done_pct": done_pct,
        "remaining_pct": remaining_pct,

        "ytd_actual": fmt_money(ytd_actual),
        "remaining_forecast": fmt_money(remaining_forecast),
        "fy_forecast": fmt_money(fy_forecast),

        "actual_daily_pace": (
            fmt_money(actual_daily_pace)
            if actual_daily_pace is not None
            else "—"
        ),

        "required_daily_pace": (
            fmt_money(required_daily_pace)
            if required_daily_pace is not None
            else "—"
        ),

        "pace_delta_pct": pace_delta_pct,
        "pace_needs_growth": (
            pace_delta_pct is not None
            and pace_delta_pct > 0
        ),

        "days_left": days_left,
        "strongest_month": strongest_month,
    }


def build_sales_digest_context(d: date, request=None) -> dict:
    ctx = build_daily_sales_report_context(d, request=request)

    ctx["meta"] = {
        "title": REPORT_TITLE,
        "report_type_label": _REPORT_TYPE_LABEL.get(ctx["report_type"], "Отчёт"),
        "report_date_fmt": d.strftime("%d.%m.%Y"),
        "weekday_ru": _WEEKDAYS_RU[d.weekday()],
        "generated_at_fmt": ctx["generated_date"].strftime("%d.%m.%Y"),
    }
    ctx["company"] = {
        "brand_name": COMPANY_BRAND_NAME,
        "legal_name": COMPANY_LEGAL_NAME,
        "website": COMPANY_WEBSITE,
    }

    # Готовые строки для шаблона (без date-фильтров и без циклов с
    # forloop.last в самом шаблоне — только простые переменные).
    if ctx.get("store_prev_start"):
        ctx["store_prev_start_fmt"] = ctx["store_prev_start"].strftime("%d.%m.%Y")
    if ctx.get("store_prev_end"):
        ctx["store_prev_end_fmt"] = ctx["store_prev_end"].strftime("%d.%m.%Y")

    _enrich_period_text(ctx.get("period_text"))
    
    period_text = ctx.get("period_text") or {}

    ctx["mtd_insight"] = _build_period_insight(
        period_text.get("mtd_text")
    )

    ctx["ytd_insight"] = _build_period_insight(
        period_text.get("ytd_text")
    )
    
    

    # Свои графики вместо старых (см. charts.py: разваливались под WeasyPrint
    # и/или были нарисованы в чужой палитре) — считаются по тем же самым
    # данным, что уже лежат в ctx / приходят из sales_report, просто рисуем
    # заново в теме COSMORELAX.
    if ctx.get("summary", {}).get("compare"):
        ctx["summary"]["compare_chart_svg_pct"] = build_compare_delta_chart(
            ctx["summary"]["compare"]
        )

    store_rows_raw = get_store_sales_for_range(ctx["period_start"], ctx["period_end"])
    ctx["store_chart_svg"] = build_stores_amount_chart(store_rows_raw)
    ctx["store_share_pie_svg"] = build_stores_share_pie(store_rows_raw)

    # Тренды и динамика (N аналогичных периодов) — данные уже посчитаны
    # старым build_kpi_context и лежат в kpi_ctx (trend/trend_meta), просто
    # раньше их никто не выводил в sales_digest. Свой график вместо старого
    # (тот был в чужой сине-розовой палитре).
    trend_rows = (ctx.get("kpi_ctx") or {}).get("trend") or []
    ctx["trend_rows"] = trend_rows
    ctx["trend_meta"] = (ctx.get("kpi_ctx") or {}).get("trend_meta") or {}
    ctx["trend_chart_svg"] = build_trend_chart(trend_rows)
    ctx["trend_badges"] = _trend_badges(trend_rows)
    ctx["trend_insight"] = _build_trend_insight(trend_rows,ctx["report_type"],)

    # MTD: свой накопительный график вместо старого (тоже был в чужой
    # сине-розовой палитре) — считаем те же самые исходные данные ещё раз
    # (get_month_data/build_mtd_cum_series — чистые функции без побочных
    # эффектов, дублирующий вызов безопасен).
    df_mtd_raw = get_month_data(d)
    mtd_cum_ctx = build_mtd_cum_series(df_mtd_raw, d)
    ctx["mtd_cum_svg"] = build_mtd_cum_chart(mtd_cum_ctx)

    # YTD: тот же накопительный график, но по дню года — считаем сами
    # (в старом builder'е накопительный YTD-график был в чужой палитре,
    # см. commulative_chart.build_ytd_cumulative_svg, здесь не используем).
    df_ytd_raw = get_ytd_data(d)
    ytd_cum_ctx = _build_ytd_cum_series(df_ytd_raw, d)
    ctx["ytd_cum_svg"] = build_ytd_cum_chart(ytd_cum_ctx)

    # Раздел IV/V: убираем "Заказы" и "Ср. чек" из таблиц MTD/YTD (готовый
    # HTML из sales.print_utils — сам builder не трогаем, чтобы не задеть
    # старый отчёт).
    ctx["table_mtd_html"] = _strip_metric_rows(ctx.get("table_mtd_html", ""))
    ctx["table_ytd_html"] = _strip_metric_rows(ctx.get("table_ytd_html", ""))

    # Раздел IV/V: "Вклад категорий в изменение выручки" (waterfall) — тот
    # же самый расчёт, что и в старом отчёте (categories_waterfall_mtd/ytd),
    # но перерисован в теме COSMORELAX (см. charts.py) и компактнее, чтобы
    # уместиться на одной странице вместе с таблицей.
    ctx["mtd_cat_waterfall_svg"] = build_categories_waterfall_chart(get_mtd_categories_raw(d), top_n=8)
    ctx["ytd_cat_waterfall_svg"] = build_categories_waterfall_chart(get_ytd_categories_raw(d), top_n=8)

    # Раздел VI: ТОП категорий MTD/YTD (текущий год vs прошлый) — свои
    # графики вместо старого categories_chart.py (обычный matplotlib без
    # темы отчёта — другие шрифты/цвета, не сочетался с остальными
    # графиками sales_digest).
    ctx["categories_chart_svg"] = build_categories_compare_chart(
        (ctx.get("categories") or {}).get("raw"), top_n=8,
    )
    ctx["categories_ytd_chart_svg"] = build_categories_compare_chart(
        (ctx.get("categories_ytd") or {}).get("raw"), top_n=8,
    )

    # Раздел VII: менеджеры — свои графики (замена старого серо-синего
    # matplotlib-графика со встроенным заголовком). Считаем из тех же самых
    # источников, что и managers_shipments_context (data.py), только сырые
    # (числовые) данные, не отформатированные строки из таблицы.
    mtd_mgr_bundle = get_mtd_managers_shipments_bundle(d, big_order_threshold=100_000)
    ytd_mgr_bundle = get_ytd_managers_shipments_bundle(d, big_order_threshold=100_000)
    if ctx.get("managers"):


        # Таблица менеджеров может быть очень длинной (десятки менеджеров) —
        # именно это раздувало раздел на несколько почти пустых страниц
        # (WeasyPrint плохо фрагментирует flex-блоки .two-col, если левая
        # колонка выше страницы). Показываем топ-20 (строки уже отсортированы
        # по выручке в managers/block.py), остальное — одной строкой ниже.
        _MGR_TABLE_LIMIT = 20
        for _period in ("mtd", "ytd"):
            _rows = ctx["managers"][_period].get("rows") or []
            if len(_rows) > _MGR_TABLE_LIMIT:
                ctx["managers"][_period]["rows_hidden_count"] = len(_rows) - _MGR_TABLE_LIMIT
                ctx["managers"][_period]["rows"] = _rows[:_MGR_TABLE_LIMIT]
            else:
                ctx["managers"][_period]["rows_hidden_count"] = 0

    # Раздел VI: "Категории за период" / "Производители за период" — данные
    # уже считались для KPI-контекста старого отчёта (build_kpi_context),
    # но нигде не выводились. Добавляем таблицу (с количеством, шт.) и
    # компактный график в тему COSMORELAX.
    period_start, period_end = ctx["period_start"], ctx["period_end"]
    cat_period_df = get_categories_for_period(period_start, period_end)
    mf_period_df = get_manufacturers_for_period(period_start, period_end)

    def _period_rows(df, name_col: str, top_n: int = 6) -> list[dict]:
        if df is None or df.empty:
            return []
        tmp = df.sort_values("amount", ascending=False).copy()
        total = float(tmp["amount"].sum()) or 0.0
        rows = []
        for _, r in tmp.head(top_n).iterrows():
            share = (float(r["amount"]) / total) if total else 0.0
            rows.append({
                "name": str(r[name_col]) or "—",
                "amount": fmt_money(r["amount"]),
                "quant": fmt_int(r.get("quant", 0)),
                "share": fmt_pct(share),
            })
        return rows

    ctx["period_categories"] = {
        "rows": _period_rows(cat_period_df, "cat_name", top_n=20),
        "chart_svg": build_period_pareto_chart(cat_period_df, "cat_name", top_n=20),
    }
    ctx["period_manufacturers"] = {
        "rows": _period_rows(mf_period_df, "manufacturer_name", top_n=20),
        "chart_svg": build_period_pareto_chart(mf_period_df, "manufacturer_name", top_n=20),
    }

    # Раздел IX: прогноз Prophet до конца года — тот же самый прогноз, что
    # уже считает старый builder (ltm_prophet_year / fy_bar_svg), просто
    # перерисовываем график в теме COSMORELAX (старый был сине-белый,
    # #002FA7, со встроенным заголовком). Дневные факт/прогноз пересчитываем
    # тем же способом, что и builder.py (тот же диапазон дат), чтобы не
    # трогать сам builder.
    forecast_df = (ctx.get("ltm_prophet") or {}).get("_forecast_df")
    if forecast_df is not None and not getattr(forecast_df, "empty", True):
        fc_start = date(2023, 1, 1)
        qs_fc = (
            MV_Daily_Sales.objects
            .filter(date__gte=fc_start, date__lte=d)
            .values("date", "amount")
            .order_by("date")
        )
        df_fc_raw = pd.DataFrame(list(qs_fc))
        ctx["fy_bar_svg"] = build_prophet_fy_chart(df_fc_raw, forecast_df, d)
        
        ctx["forecast_insight"] = _build_forecast_insight(
                df_fc_raw,
                forecast_df,
                d,
            )

    # Раздел II (доп.): KPI по магазинам MTD/YTD + помесячная динамика год к
    # году — расчёт из stores/performance/metrics.build_store_performance_block
    # (та же функция, что и в старом отчёте), своя разметка/графики в теме
    # COSMORELAX (см. _build_store_perf_context).
    ctx["store_perf"] = _build_store_perf_context(d)

    # Раздел IX: матрицы изменений (магазин × категория), Δ₽ и Δшт, MTD и
    # YTD — расчёт из старого stores/storegroup_category_diagnostics (то же,
    # что и Приложение A старого отчёта), своя разметка (heatmap-таблица)
    # вместо старой compare-table--matrix.
    ctx["store_category_matrices"] = _build_store_category_matrices(d)

    # Раздел X: YTD по подкатегориям (было/стало) — данные уже посчитаны
    # старым builder'ом (subcats_ytd, build_subcategories_ytd_context) и
    # лежат в ctx; здесь выносим вперёд приоритетные категории (без
    # усечения списка — показываем все категории, см. _reorder_subcats_ytd).
    _reorder_subcats_ytd(ctx.get("subcats_ytd"))

    # Год как строка, а не сырой int, там, где он выводится в шаблон рядом
    # с "к"/как подпись таблицы (не денежная/количественная величина, ей не
    # нужен разделитель тысяч из Django USE_THOUSAND_SEPARATOR — см. тот же
    # комментарий в _build_store_perf_context / _build_store_category_matrices
    # выше). ltm_prophet_year и subcats_ytd.years приходят из старого
    # sales_report builder'а (build_daily_sales_report_context) — сам он не
    # трогается, переформатируем значения здесь, только для sales_digest.
    if ctx.get("ltm_prophet_year", {}).get("has_data"):
        ctx["ltm_prophet_year"]["year"] = str(ctx["ltm_prophet_year"]["year"])
    subcats_years = (ctx.get("subcats_ytd") or {}).get("years")
    if subcats_years:
        ctx["subcats_ytd"]["years"] = {
            "prev": str(subcats_years["prev"]),
            "curr": str(subcats_years["curr"]),
        }

    return ctx


def render_sales_digest_html(d: date, request=None) -> str:
    context = build_sales_digest_context(d, request=request)
    return render_to_string(TEMPLATE_NAME, context, request=request)

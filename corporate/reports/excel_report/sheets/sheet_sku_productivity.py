# corporate/reports/excel_report/sheets/sheet_sku_productivity.py
from collections import defaultdict

from ..styles.theme import FORMATS, ALIGNMENTS, FILLS, FONTS
from ..styles.style_helpers import (
    draw_toc_button,
    draw_sheet_header,
    draw_table_header_with_gaps,
    hide_grid_and_freeze,
    set_column_widths,
    set_row_heights,
    style_data_row,
    style_total_row,
)


def _safe_float(v) -> float:
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def _get_status(delta_sku: float, delta_rev_per_sku: float) -> str:
    if delta_sku < 0 and delta_rev_per_sku > 0:
        return "Оптимизация"
    if delta_sku < 0 and delta_rev_per_sku < 0:
        return "Снижение эффективности"
    if delta_sku > 0 and delta_rev_per_sku > 0:
        return "Рост с улучшением"
    if delta_sku > 0 and delta_rev_per_sku < 0:
        return "Рост с размыванием"
    return "Стабильно"


def build_sku_productivity_sheet(wb, rows):
    ws = wb.create_sheet("SKU productivity")
    ws.sheet_properties.outlinePr.summaryBelow = False

    draw_toc_button(ws, cell="A1", target_sheet="TOC")

    headers = [
        "Категория",
        "Подкатегория",
        "SKU\nпред. год",
        "SKU\nтек. год",
        "Δ SKU",
        "Выручка\nпред. год",
        "Выручка\nтек. год",
        "Δ Выручка",
        "Выручка\nна 1 SKU\nпред. год",
        "Выручка\nна 1 SKU\nтек. год",
        "Δ Выручка\nна 1 SKU",
        "Статус",
    ]

    header_row = 8
    data_start_row = 9

    draw_table_header_with_gaps(
        ws,
        row=header_row,
        headers=headers,
        wrap=True,
    )

    # -----------------------------
    # Подготовка данных
    # -----------------------------
    grouped = defaultdict(dict)
    years = set()

    for r in rows:
        category = r.get("category") or "Без категории"
        subcategory = r.get("subcategory") or "Нет подкатегории"
        year = int(r.get("year"))
        years.add(year)

        grouped[(category, subcategory)][year] = {
            "full_sku_count": _safe_float(r.get("full_sku_count")),
            "ytd_sku_count": _safe_float(r.get("ytd_sku_count")),
            "full_amount": _safe_float(r.get("full_amount")),
            "ytd_amount": _safe_float(r.get("ytd_amount")),
            "cutoff_year": r.get("cutoff_year"),
            "cutoff_month": r.get("cutoff_month"),
            "cutoff_day": r.get("cutoff_day"),
        }

    years = sorted(years)
    prev_year = years[-2] if len(years) >= 2 else None
    last_year = years[-1] if len(years) >= 1 else None

    # -----------------------------
    # Определяем YTD или full
    # -----------------------------
    is_ytd_comparison = False
    cutoff_year = None
    cutoff_month = None
    cutoff_day = None

    if prev_year and last_year and grouped:
        sample_vals = next(iter(grouped.values()))
        sample_last = sample_vals.get(last_year, {})

        cutoff_year = sample_last.get("cutoff_year")
        cutoff_month = sample_last.get("cutoff_month")
        cutoff_day = sample_last.get("cutoff_day")

        if cutoff_year and cutoff_month and cutoff_day:
            is_ytd_comparison = bool(
                int(last_year) == int(cutoff_year)
                and (int(cutoff_month) < 12 or int(cutoff_day) < 31)
            )

    # -----------------------------
    # Header
    # -----------------------------
    if is_ytd_comparison:
        note = (
            f"Сравнение YTD: {prev_year} vs {last_year} "
            f"на {int(cutoff_day):02d}.{int(cutoff_month):02d}.{int(cutoff_year)}. "
            f"Показывает, компенсируется ли сокращение SKU ростом выручки на SKU."
        )
    else:
        note = "Сравнение по полным годам."

    draw_sheet_header(
        ws,
        title="Эффективность SKU по подкатегориям",
        subtitle="Ширина ассортимента vs выручка на SKU",
        note=note,
        line_to_col=12,
    )

    # -----------------------------
    # Основной расчет
    # -----------------------------
    cur_row = data_start_row

    total_prev_sku = 0
    total_last_sku = 0
    total_prev_rev = 0
    total_last_rev = 0

    prepared_rows = []

    for (category, subcategory), vals in grouped.items():
        prev_vals = vals.get(prev_year, {}) if prev_year else {}
        last_vals = vals.get(last_year, {}) if last_year else {}

        if is_ytd_comparison:
            sku_prev = _safe_float(prev_vals.get("ytd_sku_count"))
            sku_last = _safe_float(last_vals.get("ytd_sku_count"))
            rev_prev = _safe_float(prev_vals.get("ytd_amount"))
            rev_last = _safe_float(last_vals.get("ytd_amount"))
        else:
            sku_prev = _safe_float(prev_vals.get("full_sku_count"))
            sku_last = _safe_float(last_vals.get("full_sku_count"))
            rev_prev = _safe_float(prev_vals.get("full_amount"))
            rev_last = _safe_float(last_vals.get("full_amount"))

        delta_sku = sku_last - sku_prev
        delta_rev = rev_last - rev_prev

        rev_per_sku_prev = rev_prev / sku_prev if sku_prev else 0
        rev_per_sku_last = rev_last / sku_last if sku_last else 0
        delta_rev_per_sku = rev_per_sku_last - rev_per_sku_prev

        status = _get_status(delta_sku, delta_rev_per_sku)

        prepared_rows.append(
            [
                category,
                subcategory,
                sku_prev,
                sku_last,
                delta_sku,
                rev_prev,
                rev_last,
                delta_rev,
                rev_per_sku_prev,
                rev_per_sku_last,
                delta_rev_per_sku,
                status,
            ]
        )

    # сортировка
    prepared_rows.sort(key=lambda x: (x[4], x[10], x[6]))

    # -----------------------------
    # Запись строк
    # -----------------------------
    for row in prepared_rows:
        style_data_row(
            ws,
            row=cur_row,
            values=row,
            number_formats={
                3: "#,##0",
                4: "#,##0",
                5: "#,##0;[Red]-#,##0",
                6: FORMATS["money"],
                7: FORMATS["money"],
                8: FORMATS["money"],
                9: FORMATS["money"],
                10: FORMATS["money"],
                11: FORMATS["money"],
            },
        )

        for col_idx in range(3, 12):
            ws.cell(row=cur_row, column=col_idx).alignment = ALIGNMENTS["center"]

        ws.cell(row=cur_row, column=12).alignment = ALIGNMENTS["left_wrap"]

        total_prev_sku += row[2]
        total_last_sku += row[3]
        total_prev_rev += row[5]
        total_last_rev += row[6]

        cur_row += 1

    # -----------------------------
    # ИТОГО
    # -----------------------------
    total_delta_sku = total_last_sku - total_prev_sku
    total_delta_rev = total_last_rev - total_prev_rev

    total_prev_rev_per_sku = total_prev_rev / total_prev_sku if total_prev_sku else 0
    total_last_rev_per_sku = total_last_rev / total_last_sku if total_last_sku else 0
    total_delta_rev_per_sku = total_last_rev_per_sku - total_prev_rev_per_sku

    style_total_row(
        ws,
        row=cur_row,
        values=[
            "ИТОГО",
            "",
            total_prev_sku,
            total_last_sku,
            total_delta_sku,
            total_prev_rev,
            total_last_rev,
            total_delta_rev,
            total_prev_rev_per_sku,
            total_last_rev_per_sku,
            total_delta_rev_per_sku,
            "",
        ],
        number_formats={
            3: "#,##0",
            4: "#,##0",
            5: "#,##0;[Red]-#,##0",
            6: FORMATS["money"],
            7: FORMATS["money"],
            8: FORMATS["money"],
            9: FORMATS["money"],
            10: FORMATS["money"],
            11: FORMATS["money"],
        },
    )

    # -----------------------------
    # Форматирование
    # -----------------------------
    set_column_widths(
        ws,
        {
            "A": 22,
            "B": 28,
            "C": 12,
            "D": 12,
            "E": 10,
            "F": 16,
            "G": 16,
            "H": 14,
            "I": 16,
            "J": 16,
            "K": 16,
            "L": 22,
        },
    )

    set_row_heights(
        ws,
        {
            2: 24,
            3: 18,
            4: 34,
            8: 38,
        },
    )

    hide_grid_and_freeze(ws, "C9")
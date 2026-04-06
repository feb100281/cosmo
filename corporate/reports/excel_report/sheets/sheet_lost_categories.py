# corporate/reports/excel_report/sheets/sheet_lost_categories.py

from ..styles.theme import FILLS, FONTS, ALIGNMENTS, FORMATS
from ..styles.style_helpers import (
    draw_toc_button,
    draw_sheet_header,
    draw_table_header,
    hide_grid_and_freeze,
    set_column_widths,
    set_row_heights,
    style_data_row,
    style_total_row,
)


def build_lost_categories_sheet(wb, rows):
    ws = wb.create_sheet("Lost categories")

    draw_toc_button(ws, cell="A1", target_sheet="TOC")
    draw_sheet_header(
        ws,
        title="Lost categories",
        subtitle="Категории с падением выручки",
        note="Сравнение предыдущего и последнего года",
    )

    headers = [
        "Категория",
        "Предыдущий год",
        "Последний год",
        "Изменение",
        "Изменение, %",
    ]

    header_row = 8
    data_start_row = 9

    draw_table_header(ws, row=header_row, headers=headers, wrap=True)

    cur_row = data_start_row
    total_prev = 0
    total_last = 0
    total_diff = 0

    for r in rows:
        prev_val = float(r.get("prev_year_amount") or 0)
        last_val = float(r.get("last_year_amount") or 0)
        diff = float(r.get("diff_amount") or 0)
        diff_pct = 0 if prev_val == 0 else diff / prev_val

        style_data_row(
            ws,
            row=cur_row,
            values=[
                r.get("category"),
                prev_val,
                last_val,
                diff,
                diff_pct,
            ],
            number_formats={
                2: FORMATS["money"],
                3: FORMATS["money"],
                4: FORMATS["money"],
                5: FORMATS["pct"],
            },
        )

        diff_cell = ws.cell(row=cur_row, column=4)
        diff_pct_cell = ws.cell(row=cur_row, column=5)

        if diff < 0:
            diff_cell.fill = FILLS["section"]
            diff_pct_cell.fill = FILLS["section"]
            diff_cell.font = FONTS["bold"]
            diff_pct_cell.font = FONTS["bold"]
            diff_pct_cell.alignment = ALIGNMENTS["center"]

        total_prev += prev_val
        total_last += last_val
        total_diff += diff
        cur_row += 1

    total_diff_pct = 0 if total_prev == 0 else total_diff / total_prev

    style_total_row(
        ws,
        row=cur_row,
        values=[
            "ИТОГО",
            total_prev,
            total_last,
            total_diff,
            total_diff_pct,
        ],
        number_formats={
            2: FORMATS["money"],
            3: FORMATS["money"],
            4: FORMATS["money"],
            5: FORMATS["pct"],
        },
    )

    set_column_widths(
        ws,
        {
            "A": 34,
            "B": 16,
            "C": 16,
            "D": 16,
            "E": 14,
        },
    )

    set_row_heights(
        ws,
        {
            2: 24,
            3: 18,
            4: 18,
            8: 24,
        },
    )

    hide_grid_and_freeze(ws, "A9")
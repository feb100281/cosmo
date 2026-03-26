# corporate/reports/excel_report/sheets/sheet_new_vs_old.py

from ..styles.theme import FORMATS
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


def build_new_vs_old_sheet(wb, rows):
    ws = wb.create_sheet("New vs old manufacturers")

    draw_toc_button(ws, cell="A1", target_sheet="TOC")
    draw_sheet_header(
        ws,
        title="New vs old manufacturers",
        subtitle="Сравнение новых и старых производителей",
        note="Показаны количество производителей, суммарная и средняя выручка по группам",
    )

    headers = [
        "Группа",
        "Количество производителей",
        "Общая выручка",
        "Средняя выручка на производителя",
    ]

    header_row = 8
    data_start_row = 9

    draw_table_header(ws, row=header_row, headers=headers, wrap=True)

    cur_row = data_start_row
    total_count = 0
    total_revenue = 0

    for r in rows:
        cnt = int(r.get("manufacturers_count") or 0)
        revenue = float(r.get("total_revenue") or 0)
        avg_revenue = 0 if cnt == 0 else revenue / cnt

        style_data_row(
            ws,
            row=cur_row,
            values=[
                r.get("mf_group"),
                cnt,
                revenue,
                avg_revenue,
            ],
            number_formats={
                2: FORMATS["int"],
                3: FORMATS["money"],
                4: FORMATS["money"],
            },
        )

        total_count += cnt
        total_revenue += revenue
        cur_row += 1

    total_avg_revenue = 0 if total_count == 0 else total_revenue / total_count

    style_total_row(
        ws,
        row=cur_row,
        values=[
            "ИТОГО",
            total_count,
            total_revenue,
            total_avg_revenue,
        ],
        number_formats={
            2: FORMATS["int"],
            3: FORMATS["money"],
            4: FORMATS["money"],
        },
    )

    set_column_widths(
        ws,
        {
            "A": 24,
            "B": 18,
            "C": 18,
            "D": 24,
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
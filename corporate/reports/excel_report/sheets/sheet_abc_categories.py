# corporate/reports/excel_report/sheets/sheet_abc_categories.py

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


def _abc_label(cum_share: float):
    if cum_share <= 0.80:
        return "A"
    if cum_share <= 0.95:
        return "B"
    return "C"


def build_abc_categories_sheet(wb, rows):
    ws = wb.create_sheet("ABC categories")

    draw_toc_button(ws, cell="A1", target_sheet="TOC")
    draw_sheet_header(
        ws,
        title="ABC по категориям",
        subtitle="ABC-анализ категорий по выручке",
        note="Группы: A = до 80%, B = до 95%, C = хвост",
    )

    headers = [
        "Категория",
        "Выручка",
        "Доля",
        "Накопленная доля",
        "ABC",
    ]

    header_row = 8
    data_start_row = 9

    draw_table_header(ws, row=header_row, headers=headers)

    total = sum(float(r.get("net_amount") or 0) for r in rows)

    clean_rows = [
        {
            "name": r.get("category"),
            "revenue": float(r.get("net_amount") or 0),
        }
        for r in sorted(rows, key=lambda x: float(x.get("net_amount") or 0), reverse=True)
    ]

    cur_row = data_start_row
    cum = 0.0

    for item in clean_rows:
        share = 0 if total == 0 else item["revenue"] / total
        cum += share
        abc = _abc_label(cum)

        style_data_row(
            ws,
            row=cur_row,
            values=[
                item["name"],
                item["revenue"],
                share,
                cum,
                abc,
            ],
            number_formats={
                2: FORMATS["money"],
                3: FORMATS["pct"],
                4: FORMATS["pct"],
            },
        )

        abc_cell = ws.cell(row=cur_row, column=5)
        abc_cell.alignment = ALIGNMENTS["center"]

        if abc == "A":
            abc_cell.fill = FILLS["total"]
            abc_cell.font = FONTS["bold"]
        elif abc == "B":
            abc_cell.fill = FILLS["section"]
            abc_cell.font = FONTS["bold"]

        cur_row += 1

    style_total_row(
        ws,
        row=cur_row,
        values=[
            "ИТОГО",
            total,
            1 if total > 0 else 0,
            "",
            "",
        ],
        number_formats={
            2: FORMATS["money"],
            3: FORMATS["pct"],
        },
    )

    set_column_widths(
        ws,
        {
            "A": 34,
            "B": 16,
            "C": 14,
            "D": 18,
            "E": 10,
        },
    )

    set_row_heights(
        ws,
        {
            2: 24,
            3: 18,
            4: 18,
            8: 22,
        },
    )

    hide_grid_and_freeze(ws, "A9")
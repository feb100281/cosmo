# corporate/reports/excel_report/sheets/sheet_store_x_manufacturer.py

from collections import defaultdict

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


def build_store_x_manufacturer_sheet(wb, rows):
    ws = wb.create_sheet("Store x manufacturer")

    draw_toc_button(ws, cell="A1", target_sheet="TOC")
    draw_sheet_header(
        ws,
        title="Магазин × производитель",
        subtitle="Матрица выручки: магазин × производитель",
        note="По строкам — магазины, по колонкам — производители, в ячейках — выручка",
    )

    stores = sorted({(r.get("store_name") or "—") for r in rows})
    manufacturers = sorted({(r.get("manufacturer") or "—") for r in rows})

    data = defaultdict(dict)
    for r in rows:
        store = r.get("store_name") or "—"
        manufacturer = r.get("manufacturer") or "—"
        amount = float(r.get("net_amount") or 0)
        data[store][manufacturer] = amount

    headers = ["Магазин"] + manufacturers + ["Итого"]

    header_row = 8
    data_start_row = 9

    draw_table_header(ws, row=header_row, headers=headers, wrap=True)

    cur_row = data_start_row
    totals_by_manufacturer = {manufacturer: 0 for manufacturer in manufacturers}
    grand_total = 0

    for store in stores:
        values_by_manufacturer = [
            float(data[store].get(manufacturer, 0) or 0)
            for manufacturer in manufacturers
        ]
        row_total = sum(values_by_manufacturer)

        row_values = [store] + values_by_manufacturer + [row_total]

        number_formats = {
            col_idx: FORMATS["money"] for col_idx in range(2, len(headers) + 1)
        }

        style_data_row(
            ws,
            row=cur_row,
            values=row_values,
            number_formats=number_formats,
        )

        for manufacturer, value in zip(manufacturers, values_by_manufacturer):
            totals_by_manufacturer[manufacturer] += value
        grand_total += row_total

        cur_row += 1

    total_values = (
        ["ИТОГО"]
        + [totals_by_manufacturer[manufacturer] for manufacturer in manufacturers]
        + [grand_total]
    )

    total_number_formats = {
        col_idx: FORMATS["money"] for col_idx in range(2, len(headers) + 1)
    }

    style_total_row(
        ws,
        row=cur_row,
        values=total_values,
        number_formats=total_number_formats,
    )

    widths = {"A": 24}
    for idx in range(2, len(headers)):
        widths[ws.cell(1, idx).column_letter] = 14
    widths[ws.cell(1, len(headers)).column_letter] = 16

    set_column_widths(ws, widths)

    set_row_heights(
        ws,
        {
            2: 24,
            3: 18,
            4: 18,
            8: 26,
        },
    )

    hide_grid_and_freeze(ws, "B9")
# corporate/reports/excel_report/sheets/sheet_overview.py


from ..styles.theme import FORMATS, FILLS, ALIGNMENTS, FONTS
from ..styles.style_helpers import (
    draw_toc_button,
    draw_sheet_header,
    draw_table_header,
    draw_section_title,
    style_data_row,
    style_total_row,
    hide_grid_and_freeze,
    set_column_widths,
    set_row_heights,
    draw_blank_row,
    apply_3color_heatmap,
)


def build_overview_sheet(wb, overview_rows, overview_store_rows):
    ws = wb.create_sheet("Сводка")

    # -------------------------------------------------
    # Header
    # -------------------------------------------------
    draw_toc_button(ws, cell="A1", text="← Оглавление", target_sheet="TOC")

    draw_sheet_header(
        ws,
        title="Общая сводка по продажам",
        subtitle="Продажи по годам и каналам",
        note="Чистая выручка",
        line_to_col=7,
    )

    ws.auto_filter.ref = None

    # -------------------------------------------------
    # SUMMARY (верх)
    # -------------------------------------------------
    summary_headers = [
        "Год",
        "Чистая выручка, ₽",
        "Товаров, шт.",
        "Производителей,\nшт.",
        "Каналов продаж",
    ]

    header_row = 8
    cur_row = 9

    draw_table_header(ws, row=header_row, headers=summary_headers, wrap=True)

    total_revenue = 0
    total_items = 0
    max_manufacturers = 0
    max_stores = 0

    for item in overview_rows:
        year = int(item.get("year") or 0)
        net_amount = float(item.get("net_amount") or 0)
        items_cnt = int(item.get("items_cnt") or 0)
        manufacturers_cnt = int(item.get("manufacturers_cnt") or 0)
        stores_cnt = int(item.get("stores_cnt") or 0)

        style_data_row(
            ws,
            row=cur_row,
            values=[
                year,
                net_amount,
                items_cnt,
                manufacturers_cnt,
                stores_cnt,
            ],
            number_formats={
                2: FORMATS["money"],
                3: FORMATS["int"],
                4: FORMATS["int"],
                5: FORMATS["int"],
            },
        )

        ws.cell(row=cur_row, column=1).alignment = ALIGNMENTS["center"]

        total_revenue += net_amount
        total_items += items_cnt
        max_manufacturers = max(max_manufacturers, manufacturers_cnt)
        max_stores = max(max_stores, stores_cnt)

        cur_row += 1
        
    # -------------------------------------------------
    # Отступ перед ИТОГО
    # -------------------------------------------------
    
    draw_blank_row(ws, row=cur_row, col_start=1, col_end=5, height=8)
    cur_row += 1


    # --- ИТОГО (верхняя таблица)
    style_total_row(
        ws,
        row=cur_row,
        values=[
            "ИТОГО",
            total_revenue,
            total_items,
            max_manufacturers,
            max_stores,
        ],
        number_formats={
            2: FORMATS["money"],
            3: FORMATS["int"],
            4: FORMATS["int"],
            5: FORMATS["int"],
        },
    )

    total_row = cur_row

    # -------------------------------------------------
    # Отступ
    # -------------------------------------------------
    draw_blank_row(ws, row=total_row + 1, col_start=1, col_end=7, height=8)

    # -------------------------------------------------
    # MATRIX: Выручка по каналам
    # -------------------------------------------------
    section_row = total_row + 3

    draw_section_title(
        ws,
        row=section_row,
        col_start=1,
        col_end=7,
        title="Выручка по каналам продаж",
    )

    years = sorted(set(int(r["year"]) for r in overview_store_rows))
    stores = sorted(set((r.get("store_name") or "—") for r in overview_store_rows))

    revenue_map = {}
    for r in overview_store_rows:
        store = r.get("store_name") or "—"
        year = int(r.get("year") or 0)
        revenue_map[(store, year)] = float(r.get("net_amount") or 0)

    header_row = section_row + 1
    data_start = header_row + 1

    headers = ["Канал продаж"] + [str(y) for y in years] + ["Итого"]

    draw_table_header(ws, row=header_row, headers=headers, wrap=True)

    cur_row = data_start
    total_col = len(years) + 2

    # --- строки магазинов
    for store in stores:
        values = [store]
        total = 0

        for y in years:
            val = revenue_map.get((store, y), 0)
            values.append(val)
            total += val

        values.append(total)

        number_formats = {i + 2: FORMATS["money"] for i in range(len(years))}
        number_formats[total_col] = FORMATS["money"]

        style_data_row(
            ws,
            row=cur_row,
            values=values,
            number_formats=number_formats,
        )

        # выделяем колонку ИТОГО
        ws.cell(row=cur_row, column=total_col).fill = FILLS["summary"]
        ws.cell(row=cur_row, column=total_col).font = FONTS["bold"]

        cur_row += 1

    # -------------------------------------------------
    # Отступ перед ИТОГО
    # -------------------------------------------------
    draw_blank_row(ws, row=cur_row, col_start=1, col_end=total_col, height=8)
    cur_row += 1

    # -------------------------------------------------
    # ИТОГО по матрице
    # -------------------------------------------------
    total_values = ["ИТОГО"]
    grand_total = 0

    for y in years:
        y_total = sum(revenue_map.get((s, y), 0) for s in stores)
        total_values.append(y_total)
        grand_total += y_total

    total_values.append(grand_total)

    number_formats = {i + 2: FORMATS["money"] for i in range(len(years))}
    number_formats[total_col] = FORMATS["money"]

    style_total_row(
        ws,
        row=cur_row,
        values=total_values,
        number_formats=number_formats,
    )

    matrix_total_row = cur_row

    # -------------------------------------------------
    # HEATMAP
    # -------------------------------------------------
    apply_3color_heatmap(
        ws,
        start_row=data_start,
        end_row=matrix_total_row - 2,
        start_col=2,
        end_col=1 + len(years),
    )

    # -------------------------------------------------
    # Размеры
    # -------------------------------------------------
    set_column_widths(
        ws,
        {
            "A": 32,
            "B": 17,
            "C": 17,
            "D": 17,
            "E": 17,
            "F": 17,
            "G": 20,
        },
    )

    set_row_heights(
        ws,
        {
            1: 20,
            2: 24,
            3: 18,
            4: 18,
            8: 28,
            header_row: 24,
        },
    )

    # hide_grid_and_freeze(ws, "A9")
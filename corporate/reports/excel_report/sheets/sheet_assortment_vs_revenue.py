# corporate/reports/excel_report/sheets/sheet_assortment_vs_revenue.py

from collections import defaultdict

from ..styles.theme import FILLS, FONTS, ALIGNMENTS, FORMATS, BORDERS
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


def build_assortment_vs_revenue_sheet(wb, manufacturer_rows, category_rows):
    ws = wb.create_sheet("Assortment vs revenue")
    ws.sheet_properties.outlinePr.summaryBelow = False

    draw_toc_button(ws, cell="A1", target_sheet="TOC")
    draw_sheet_header(
        ws,
        title="Ассортимент vs выручка",
        subtitle="Сопоставление ассортимента и выручки по производителям",
        note=(
            "Показатель 'Выручка на 1 SKU' рассчитывается как выручка / количество SKU. "
            "Под каждым производителем доступна разбивка по категориям."
        ),
        line_to_col=4,
    )

    headers = [
        "Производитель / Категория",
        "Кол-во SKU",
        "Выручка",
        "Выручка на 1 SKU",
    ]

    header_row = 8
    data_start_row = 9

    draw_table_header(ws, row=header_row, headers=headers, wrap=True)

    # -------------------------------------------------
    # Категории внутри производителя
    # -------------------------------------------------
    categories_by_manufacturer = defaultdict(list)
    for r in category_rows:
        manufacturer = r.get("manufacturer") or "—"
        categories_by_manufacturer[manufacturer].append(
            {
                "category": r.get("category") or "—",
                "item_count": int(r.get("item_count") or 0),
                "net_amount": float(r.get("net_amount") or 0),
            }
        )

    for manufacturer in categories_by_manufacturer:
        categories_by_manufacturer[manufacturer].sort(
            key=lambda x: x["net_amount"],
            reverse=True,
        )

    # -------------------------------------------------
    # Стиль строк категорий
    # -------------------------------------------------
    def style_category_row(ws, row, values, number_formats=None):
        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.font = FONTS["normal"]
            cell.fill = FILLS["alt"]
            cell.border = BORDERS["thin"]

            if col_idx == 1:
                cell.alignment = ALIGNMENTS["left"]
            else:
                cell.alignment = ALIGNMENTS["right"]

            if number_formats and col_idx in number_formats:
                cell.number_format = number_formats[col_idx]

    # -------------------------------------------------
    # Основные строки
    # -------------------------------------------------
    cur_row = data_start_row
    total_sku = 0
    total_revenue = 0

    for r in manufacturer_rows:
        manufacturer = r.get("manufacturer") or "—"
        item_count = int(r.get("item_count") or 0)
        net_amount = float(r.get("net_amount") or 0)
        revenue_per_sku = 0 if item_count == 0 else net_amount / item_count

        manufacturer_row_idx = cur_row

        style_data_row(
            ws,
            row=cur_row,
            values=[
                manufacturer,
                item_count,
                net_amount,
                revenue_per_sku,
            ],
            number_formats={
                2: FORMATS["int"],
                3: FORMATS["money"],
                4: FORMATS["money"],
            },
        )

        total_sku += item_count
        total_revenue += net_amount
        cur_row += 1

        # -------------------------------------------------
        # Вложенные строки категорий
        # -------------------------------------------------
        mf_categories = categories_by_manufacturer.get(manufacturer, [])

        for cat in mf_categories:
            cat_item_count = int(cat["item_count"] or 0)
            cat_net_amount = float(cat["net_amount"] or 0)
            cat_revenue_per_sku = 0 if cat_item_count == 0 else cat_net_amount / cat_item_count

            style_category_row(
                ws,
                row=cur_row,
                values=[
                    f"    ↳ {cat['category']}",
                    cat_item_count,
                    cat_net_amount,
                    cat_revenue_per_sku,
                ],
                number_formats={
                    2: FORMATS["int"],
                    3: FORMATS["money"],
                    4: FORMATS["money"],
                },
            )

            ws.row_dimensions[cur_row].outlineLevel = 1
            ws.row_dimensions[cur_row].hidden = True
            cur_row += 1

        if mf_categories:
            ws.row_dimensions[manufacturer_row_idx].collapsed = True

    total_revenue_per_sku = 0 if total_sku == 0 else total_revenue / total_sku

    style_total_row(
        ws,
        row=cur_row,
        values=[
            "ИТОГО",
            total_sku,
            total_revenue,
            total_revenue_per_sku,
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
            "A": 38,
            "B": 14,
            "C": 16,
            "D": 18,
        },
    )

    set_row_heights(
        ws,
        {
            2: 24,
            3: 18,
            4: 30,
            8: 26,
        },
    )

    hide_grid_and_freeze(ws, "A9")
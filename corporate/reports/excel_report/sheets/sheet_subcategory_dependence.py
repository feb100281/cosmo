# # corporate/reports/excel_report/sheets/sheet_category_dependence.py

# from ..styles.theme import FILLS, FONTS, ALIGNMENTS, FORMATS
# from ..styles.style_helpers import (
#     draw_toc_button,
#     draw_sheet_header,
#     draw_table_header_with_gaps,
#     hide_grid_and_freeze,
#     set_column_widths,
#     set_row_heights,
#     style_data_row,
#     style_total_row,
#     clear_column,
# )


# def build_category_dependence_sheet(wb, rows):
#     ws = wb.create_sheet("Category dependence")
#     ws.sheet_properties.outlinePr.summaryBelow = False

#     draw_toc_button(ws, cell="A1", target_sheet="TOC")
#     draw_sheet_header(
#         ws,
#         title="Зависимость категорий",
#         subtitle="Зависимость категории от ключевого производителя",
#         note=(
#             "Показатель отражает долю крупнейшего производителя в общей выручке категории. "
#             "Строки отсортированы по убыванию зависимости."
#         ),
#         line_to_col=7,
#     )

#     layout = [
#         ("category", "Категория"),
#         ("manufacturer", "Ключевой\nпроизводитель"),
#         ("manufacturer_revenue", "Выручка\nпроизводителя"),
#         ("total_category_revenue", "Общая выручка\nкатегории"),
#         ("gap_before_share", ""),
#         ("dependence_share", "Зависимость от\nпроизводителя"),
#         ("risk_level", "Риск"),
#     ]

#     headers = [label for _, label in layout]

#     gap_cols = set()
#     col_map = {}
#     for idx, (key, _) in enumerate(layout, start=1):
#         col_map[key] = idx
#         if key.startswith("gap_"):
#             gap_cols.add(idx)

#     header_row = 8
#     data_start_row = 9

#     draw_table_header_with_gaps(
#         ws,
#         row=header_row,
#         headers=headers,
#         wrap=True,
#         gap_cols=gap_cols,
#     )

#     cur_row = data_start_row
#     total_leader_revenue = 0
#     total_category_revenue = 0
#     dependence_values = []

#     for r in rows:
#         category = r.get("category") or "—"
#         manufacturer = r.get("manufacturer") or "—"
#         manufacturer_revenue = float(r.get("manufacturer_revenue") or 0)
#         total_row_revenue = float(r.get("total_category_revenue") or 0)
#         dependence_share = float(r.get("dependence_share") or 0)

#         if dependence_share >= 0.7:
#             risk_label = "Высокий"
#         elif dependence_share >= 0.5:
#             risk_label = "Средний"
#         else:
#             risk_label = "Низкий"

#         style_data_row(
#             ws,
#             row=cur_row,
#             values=[
#                 category,
#                 manufacturer,
#                 manufacturer_revenue,
#                 total_row_revenue,
#                 None,
#                 dependence_share,
#                 risk_label,
#             ],
#             number_formats={
#                 col_map["manufacturer_revenue"]: FORMATS["money"],
#                 col_map["total_category_revenue"]: FORMATS["money"],
#                 col_map["dependence_share"]: FORMATS["pct"],
#             },
#         )

#         dep_cell = ws.cell(row=cur_row, column=col_map["dependence_share"])
#         dep_cell.alignment = ALIGNMENTS["center"]

#         risk_cell = ws.cell(row=cur_row, column=col_map["risk_level"])
#         risk_cell.alignment = ALIGNMENTS["center"]

#         if dependence_share >= 0.7:
#             dep_cell.fill = FILLS["section"]
#             dep_cell.font = FONTS["bold"]
#             risk_cell.fill = FILLS["section"]
#             risk_cell.font = FONTS["bold"]
#         elif dependence_share >= 0.5:
#             dep_cell.fill = FILLS["total"]
#             dep_cell.font = FONTS["bold"]
#             risk_cell.font = FONTS["bold"]

#         total_leader_revenue += manufacturer_revenue
#         total_category_revenue += total_row_revenue
#         dependence_values.append(dependence_share)

#         cur_row += 1

#     avg_dependence = sum(dependence_values) / len(dependence_values) if dependence_values else 0

#     style_total_row(
#         ws,
#         row=cur_row,
#         values=[
#             "ИТОГО / СРЕДНЕЕ",
#             "",
#             total_leader_revenue,
#             total_category_revenue,
#             None,
#             avg_dependence,
#             "",
#         ],
#         number_formats={
#             col_map["manufacturer_revenue"]: FORMATS["money"],
#             col_map["total_category_revenue"]: FORMATS["money"],
#             col_map["dependence_share"]: FORMATS["pct"],
#         },
#     )

#     total_row = cur_row

#     for gap_col in gap_cols:
#         clear_column(ws, col_idx=gap_col, row_start=header_row, row_end=total_row)

#     set_column_widths(
#         ws,
#         {
#             "A": 30,
#             "B": 28,
#             "C": 18,
#             "D": 20,
#             "E": 3.5,
#             "F": 18,
#             "G": 12,
#         },
#     )

#     set_row_heights(
#         ws,
#         {
#             2: 24,
#             3: 18,
#             4: 34,
#             8: 30,
#         },
#     )

#     hide_grid_and_freeze(ws, "A9")




from ..styles.theme import FILLS, FONTS, ALIGNMENTS, FORMATS
from ..styles.style_helpers import (
    draw_toc_button,
    draw_sheet_header,
    draw_table_header_with_gaps,
    hide_grid_and_freeze,
    set_column_widths,
    set_row_heights,
    style_data_row,
    style_total_row,
    clear_column,
)


def build_subcategory_dependence_sheet(wb, rows):
    ws = wb.create_sheet("Subcategory dependence")
    ws.sheet_properties.outlinePr.summaryBelow = False

    draw_toc_button(ws, cell="A1", target_sheet="TOC")
    draw_sheet_header(
        ws,
        title="Зависимость подкатегорий",
        subtitle="Зависимость подкатегории от ключевого производителя",
        note=(
            "Показатель отражает долю крупнейшего производителя в общей выручке подкатегории. "
            "Строки отсортированы по убыванию зависимости."
        ),
        line_to_col=8,
    )

    layout = [
        ("category", "Категория"),
        ("subcategory", "Подкатегория"),
        ("manufacturer", "Ключевой\nпроизводитель"),
        ("manufacturer_revenue", "Выручка\nпроизводителя"),
        ("total_subcategory_revenue", "Общая выручка\nподкатегории"),
        ("gap_before_share", ""),
        ("dependence_share", "Зависимость от\nпроизводителя"),
        ("risk_level", "Риск"),
    ]

    headers = [label for _, label in layout]

    gap_cols = set()
    col_map = {}
    for idx, (key, _) in enumerate(layout, start=1):
        col_map[key] = idx
        if key.startswith("gap_"):
            gap_cols.add(idx)

    header_row = 8
    data_start_row = 9

    draw_table_header_with_gaps(
        ws,
        row=header_row,
        headers=headers,
        wrap=True,
        gap_cols=gap_cols,
    )

    cur_row = data_start_row
    total_leader_revenue = 0
    total_subcategory_revenue = 0
    dependence_values = []

    for r in rows:
        category = r.get("category") or "—"
        subcategory = r.get("subcategory") or "—"
        manufacturer = r.get("manufacturer") or "—"
        manufacturer_revenue = float(r.get("manufacturer_revenue") or 0)
        total_row_revenue = float(r.get("total_subcategory_revenue") or 0)
        dependence_share = float(r.get("dependence_share") or 0)

        if dependence_share >= 0.7:
            risk_label = "Высокий"
        elif dependence_share >= 0.5:
            risk_label = "Средний"
        else:
            risk_label = "Низкий"

        style_data_row(
            ws,
            row=cur_row,
            values=[
                category,
                subcategory,
                manufacturer,
                manufacturer_revenue,
                total_row_revenue,
                None,
                dependence_share,
                risk_label,
            ],
            number_formats={
                col_map["manufacturer_revenue"]: FORMATS["money"],
                col_map["total_subcategory_revenue"]: FORMATS["money"],
                col_map["dependence_share"]: FORMATS["pct"],
            },
        )

        dep_cell = ws.cell(row=cur_row, column=col_map["dependence_share"])
        dep_cell.alignment = ALIGNMENTS["center"]

        risk_cell = ws.cell(row=cur_row, column=col_map["risk_level"])
        risk_cell.alignment = ALIGNMENTS["center"]

        if dependence_share >= 0.7:
            dep_cell.fill = FILLS["section"]
            dep_cell.font = FONTS["bold"]
            risk_cell.fill = FILLS["section"]
            risk_cell.font = FONTS["bold"]
        elif dependence_share >= 0.5:
            dep_cell.fill = FILLS["total"]
            dep_cell.font = FONTS["bold"]
            risk_cell.font = FONTS["bold"]

        total_leader_revenue += manufacturer_revenue
        total_subcategory_revenue += total_row_revenue
        dependence_values.append(dependence_share)

        cur_row += 1

    avg_dependence = sum(dependence_values) / len(dependence_values) if dependence_values else 0

    style_total_row(
        ws,
        row=cur_row,
        values=[
            "ИТОГО / СРЕДНЕЕ",
            "",
            "",
            total_leader_revenue,
            total_subcategory_revenue,
            None,
            avg_dependence,
            "",
        ],
        number_formats={
            col_map["manufacturer_revenue"]: FORMATS["money"],
            col_map["total_subcategory_revenue"]: FORMATS["money"],
            col_map["dependence_share"]: FORMATS["pct"],
        },
    )

    total_row = cur_row

    for gap_col in gap_cols:
        clear_column(ws, col_idx=gap_col, row_start=header_row, row_end=total_row)

    set_column_widths(
        ws,
        {
            "A": 24,
            "B": 28,
            "C": 28,
            "D": 18,
            "E": 20,
            "F": 3.5,
            "G": 18,
            "H": 12,
        },
    )

    set_row_heights(
        ws,
        {
            2: 24,
            3: 18,
            4: 34,
            8: 30,
        },
    )

    hide_grid_and_freeze(ws, "A9")
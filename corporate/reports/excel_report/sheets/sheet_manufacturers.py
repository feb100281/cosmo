# corporate/reports/excel_report/sheets/sheet_manufacturers.py

# from collections import defaultdict

# from ..styles.theme import FILLS, FONTS, ALIGNMENTS, FORMATS
# from ..styles.style_helpers import (
#     draw_toc_button,
#     draw_sheet_header,
#     draw_table_header,
#     hide_grid_and_freeze,
#     set_column_widths,
#     set_row_heights,
#     style_data_row,
#     style_total_row,
# )


# def build_manufacturers_sheet(wb, years, rows):
#     ws = wb.create_sheet("Производители")

#     draw_toc_button(ws, cell="A1", target_sheet="TOC")
#     draw_sheet_header(
#         ws,
#         title="Производители",
#         subtitle="Выручка по производителям в разрезе лет",
#         note="Показаны итоговая выручка, доля в общем объеме и тренд за период",
#     )

#     headers = ["Производитель"] + [str(y) for y in years] + ["Итого", "Доля", "Тренд"]

#     header_row = 8
#     data_start_row = 9

#     draw_table_header(ws, row=header_row, headers=headers, wrap=True)

#     data = defaultdict(dict)
#     for r in rows:
#         manufacturer = r.get("manufacturer")
#         year = int(r.get("year"))
#         amount = float(r.get("net_amount") or 0)
#         data[manufacturer][year] = amount

#     sorted_names = sorted(
#         data.keys(),
#         key=lambda name: sum(float(data[name].get(y, 0) or 0) for y in years),
#         reverse=True,
#     )

#     totals_by_year = {y: 0 for y in years}
#     prepared_rows = []

#     for name in sorted_names:
#         year_values = [float(data[name].get(y, 0) or 0) for y in years]
#         row_total = sum(year_values)

#         if len(years) >= 2:
#             first_val = year_values[0]
#             last_val = year_values[-1]
#             trend = 0 if first_val == 0 else (last_val - first_val) / first_val
#         else:
#             trend = 0

#         prepared_rows.append(
#             {
#                 "name": name,
#                 "year_values": year_values,
#                 "total": row_total,
#                 "trend": trend,
#             }
#         )

#         for y, val in zip(years, year_values):
#             totals_by_year[y] += val

#     grand_total = sum(item["total"] for item in prepared_rows)

#     cur_row = data_start_row
#     for item in prepared_rows:
#         share = 0 if grand_total == 0 else item["total"] / grand_total

#         values = [item["name"]] + item["year_values"] + [item["total"], share, item["trend"]]

#         number_formats = {
#             col_idx: FORMATS["money"] for col_idx in range(2, 2 + len(years) + 1)
#         }
#         number_formats[len(headers) - 1] = FORMATS["pct"]  # Доля
#         number_formats[len(headers)] = FORMATS["pct"]      # Тренд

#         style_data_row(
#             ws,
#             row=cur_row,
#             values=values,
#             number_formats=number_formats,
#         )

#         share_cell = ws.cell(row=cur_row, column=len(headers) - 1)
#         trend_cell = ws.cell(row=cur_row, column=len(headers))

#         share_cell.alignment = ALIGNMENTS["center"]
#         trend_cell.alignment = ALIGNMENTS["center"]

#         if item["trend"] < 0:
#             trend_cell.fill = FILLS["section"]
#             trend_cell.font = FONTS["bold"]

#         cur_row += 1

#     total_values = ["ИТОГО"] + [totals_by_year[y] for y in years] + [grand_total, 1 if grand_total > 0 else 0, ""]

#     total_number_formats = {
#         col_idx: FORMATS["money"] for col_idx in range(2, 2 + len(years) + 1)
#     }
#     total_number_formats[len(headers) - 1] = FORMATS["pct"]

#     style_total_row(
#         ws,
#         row=cur_row,
#         values=total_values,
#         number_formats=total_number_formats,
#     )

#     widths = {"A": 34}
#     for i in range(2, 2 + len(years)):
#         widths[ws.cell(1, i).column_letter] = 14
#     widths[ws.cell(1, 1 + len(years) + 1).column_letter] = 16  # Итого
#     widths[ws.cell(1, 1 + len(years) + 2).column_letter] = 12  # Доля
#     widths[ws.cell(1, 1 + len(years) + 3).column_letter] = 12  # Тренд

#     set_column_widths(ws, widths)

#     set_row_heights(
#         ws,
#         {
#             2: 24,
#             3: 18,
#             4: 18,
#             8: 24,
#         },
#     )

#     hide_grid_and_freeze(ws, "B9")




from collections import defaultdict
from datetime import date

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
    draw_blank_row,
    clear_column,
)


def build_manufacturers_sheet(wb, years, rows):
    ws = wb.create_sheet("Производители")

    current_year = date.today().year

    # -------------------------------------------------
    # Определяем, какие годы реально сравниваем в росте
    # -------------------------------------------------
    trend_years = years[:]

    # Если последний год = текущий и в выборке есть хотя бы 3 года,
    # считаем его незавершенным и исключаем из расчета роста
    if len(trend_years) >= 3 and trend_years[-1] == current_year:
        trend_years = trend_years[:-1]

    if len(trend_years) >= 2:
        trend_prev_year = trend_years[-2]
        trend_last_year = trend_years[-1]
        trend_header = f"Рост {trend_last_year}/{trend_prev_year}"
        trend_note = f"Рост рассчитан как изменение {trend_last_year} к {trend_prev_year}. Текущий незавершенный {current_year} год в расчете роста не участвует."
    else:
        trend_prev_year = None
        trend_last_year = None
        trend_header = "Рост г/г"
        trend_note = "Недостаточно данных для расчета роста г/г."

    draw_toc_button(ws, cell="A1", target_sheet="TOC")
    draw_sheet_header(
        ws,
        title="Производители",
        subtitle="Выручка по производителям в разрезе лет",
        note=trend_note,
        line_to_col=len(years) + 5,
    )

    # -------------------------------------------------
    # Header
    # -------------------------------------------------
    headers = ["Производитель"] + [str(y) for y in years] + ["", "Итого", "Доля", trend_header]

    header_row = 8
    data_start_row = 9

    blank_col = 2 + len(years)
    total_col = blank_col + 1
    share_col = blank_col + 2
    trend_col = blank_col + 3

    draw_table_header_with_gaps(
        ws,
        row=header_row,
        headers=headers,
        wrap=True,
        gap_cols={blank_col},
    )

    # -------------------------------------------------
    # Данные
    # -------------------------------------------------
    data = defaultdict(dict)
    for r in rows:
        manufacturer = r.get("manufacturer") or "—"
        year = int(r.get("year"))
        amount = float(r.get("net_amount") or 0)
        data[manufacturer][year] = amount

    sorted_names = sorted(
        data.keys(),
        key=lambda name: sum(float(data[name].get(y, 0) or 0) for y in years),
        reverse=True,
    )

    totals_by_year = {y: 0 for y in years}
    prepared_rows = []

    for name in sorted_names:
        year_values = [float(data[name].get(y, 0) or 0) for y in years]
        row_total = sum(year_values)

        trend = 0
        if trend_prev_year is not None and trend_last_year is not None:
            prev_val = float(data[name].get(trend_prev_year, 0) or 0)
            last_val = float(data[name].get(trend_last_year, 0) or 0)
            trend = 0 if prev_val == 0 else (last_val - prev_val) / prev_val

        prepared_rows.append(
            {
                "name": name,
                "year_values": year_values,
                "total": row_total,
                "trend": trend,
            }
        )

        for y, val in zip(years, year_values):
            totals_by_year[y] += val

    grand_total = sum(item["total"] for item in prepared_rows)

    # -------------------------------------------------
    # Строки данных
    # -------------------------------------------------
    cur_row = data_start_row
    for item in prepared_rows:
        share = 0 if grand_total == 0 else item["total"] / grand_total

        values = [item["name"]] + item["year_values"] + ["", item["total"], share, item["trend"]]

        number_formats = {
            col_idx: FORMATS["money"] for col_idx in range(2, 2 + len(years))
        }
        number_formats[total_col] = FORMATS["money"]
        number_formats[share_col] = FORMATS["pct"]
        number_formats[trend_col] = FORMATS["pct"]

        style_data_row(
            ws,
            row=cur_row,
            values=values,
            number_formats=number_formats,
        )

        share_cell = ws.cell(row=cur_row, column=share_col)
        trend_cell = ws.cell(row=cur_row, column=trend_col)

        share_cell.alignment = ALIGNMENTS["center"]
        trend_cell.alignment = ALIGNMENTS["center"]

        if item["trend"] < 0:
            trend_cell.fill = FILLS["section"]
            trend_cell.font = FONTS["bold"]

        cur_row += 1

    # -------------------------------------------------
    # Пустая строка перед итогом
    # -------------------------------------------------
    draw_blank_row(ws, row=cur_row, col_start=1, col_end=len(headers), height=8)
    cur_row += 1

    # -------------------------------------------------
    # ИТОГО
    # -------------------------------------------------
    total_values = (
        ["ИТОГО"]
        + [totals_by_year[y] for y in years]
        + ["", grand_total, 1 if grand_total > 0 else 0, ""]
    )

    total_number_formats = {
        col_idx: FORMATS["money"] for col_idx in range(2, 2 + len(years))
    }
    total_number_formats[total_col] = FORMATS["money"]
    total_number_formats[share_col] = FORMATS["pct"]

    style_total_row(
        ws,
        row=cur_row,
        values=total_values,
        number_formats=total_number_formats,
    )

    total_row = cur_row

    # -------------------------------------------------
    # Очищаем колонку-разделитель полностью
    # -------------------------------------------------
    clear_column(ws, col_idx=blank_col, row_start=header_row, row_end=total_row)

    # -------------------------------------------------
    # Widths
    # -------------------------------------------------
    widths = {"A": 34}

    for i in range(2, 2 + len(years)):
        widths[ws.cell(1, i).column_letter] = 14

    widths[ws.cell(1, blank_col).column_letter] = 5
    widths[ws.cell(1, total_col).column_letter] = 16
    widths[ws.cell(1, share_col).column_letter] = 12
    widths[ws.cell(1, trend_col).column_letter] = 14

    set_column_widths(ws, widths)

    # -------------------------------------------------
    # Heights
    # -------------------------------------------------
    set_row_heights(
        ws,
        {
            2: 24,
            3: 18,
            4: 34,
            8: 24,
        },
    )

    hide_grid_and_freeze(ws, "B9")
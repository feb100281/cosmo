# # corporate/reports/excel_report/sheets/sheet_categories.py

# from collections import defaultdict

# from ..styles.theme import FORMATS, ALIGNMENTS, FILLS, FONTS
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


# def build_categories_sheet(wb, years, rows):
#     ws = wb.create_sheet("Categories")
#     ws.sheet_properties.outlinePr.summaryBelow = False

#     draw_toc_button(ws, cell="A1", target_sheet="TOC")

#     # -------------------------------------------------
#     # Дата среза
#     # -------------------------------------------------
#     if rows:
#         cutoff_year = int(rows[0].get("cutoff_year") or 0)
#         cutoff_month = int(rows[0].get("cutoff_month") or 0)
#         cutoff_day = int(rows[0].get("cutoff_day") or 0)
#     else:
#         cutoff_year = 0
#         cutoff_month = 0
#         cutoff_day = 0

#     last_year = years[-1] if years else None
#     is_last_year_incomplete = bool(
#         last_year
#         and cutoff_year == last_year
#         and (cutoff_month < 12 or cutoff_day < 31)
#     )

#     if is_last_year_incomplete:
#         note = (
#             f"Для закрытых лет показана выручка и YOY. "
#             f"Для {last_year} год еще не закрыт, поэтому последний блок рассчитан как YTD "
#             f"на {cutoff_day:02d}.{cutoff_month:02d}.{cutoff_year}: "
#             f"сравнение {last_year} с {last_year - 1} за сопоставимый период. "
#             f"Справа дополнительно показан объем реализации в штуках за последний период и его изменение."
#         )
#     else:
#         note = (
#             "Показана выручка по категориям в разрезе лет, изменение к предыдущему году и итог за период. "
#             "Справа дополнительно показан объем реализации в штуках за последний год и его изменение."
#         )
#     # -------------------------------------------------
#     # Layout колонок
#     # -------------------------------------------------
#     layout = [("name", "Категория")]

#     for i, y in enumerate(years):
#         year_header = f"{y}\nYTD" if (is_last_year_incomplete and y == last_year) else str(y)
#         layout.append((f"year_{y}", year_header))

#         if i > 0:
#             prev_y = years[i - 1]
#             delta_header = (
#                 f"YTD\n{prev_y}→{y}"
#                 if (is_last_year_incomplete and y == last_year)
#                 else f"YOY\n{prev_y}→{y}"
#             )
#             layout.append((f"delta_{prev_y}_{y}", delta_header))

#         layout.append((f"gap_after_{y}", ""))

#     if years:
#         compare_prev_year = years[-2] if len(years) >= 2 else years[-1]
#         compare_last_year = years[-1]

#         qty_header = f"{compare_last_year}\nШт" if not is_last_year_incomplete else f"{compare_last_year}\nШт YTD"
#         qty_delta_header = (
#             f"Δ Шт\n{compare_prev_year}→{compare_last_year}"
#             if len(years) >= 2 else "Δ Шт"
#         )

#         layout.extend(
#             [
#                 ("gap_before_qty", ""),
#                 ("qty_last", qty_header),
#                 ("qty_delta", qty_delta_header),
#             ]
#         )

#     layout.append(("total", "Итого"))

#     headers = [label for _, label in layout]

#     gap_cols = set()
#     col_map = {}
#     for idx, (key, _) in enumerate(layout, start=1):
#         col_map[key] = idx
#         if key.startswith("gap_after_"):
#             gap_cols.add(idx)

#     last_used_col = len(layout)

#     draw_sheet_header(
#         ws,
#         title="Категории",
#         subtitle="Выручка по категориям в разрезе лет",
#         note=note,
#         line_to_col=last_used_col,
#     )

#     header_row = 8
#     data_start_row = 9

#     draw_table_header_with_gaps(
#         ws,
#         row=header_row,
#         headers=headers,
#         wrap=True,
#         gap_cols=gap_cols,
#     )

#     # -------------------------------------------------
#     # Подготовка данных
#     # -------------------------------------------------
#     data = defaultdict(dict)

#     for r in rows:
#         category = r.get("category") or r.get("root_category") or "—"
#         year = int(r.get("year"))
#         full_amount = float(r.get("full_amount") or 0)
#         ytd_amount = float(r.get("ytd_amount") or 0)
#         full_qty = float(r.get("full_qty") or 0)
#         ytd_qty = float(r.get("ytd_qty") or 0)
#         sku_count = float(r.get("sku_count") or 0)

#         data[category][year] = {
#             "full_amount": full_amount,
#             "ytd_amount": ytd_amount,
#             "full_qty": full_qty,
#             "ytd_qty": ytd_qty,
#             "sku_count": sku_count,
#         }

#     def get_display_value(category_name, year):
#         payload = data[category_name].get(year, {})
#         if is_last_year_incomplete and year == last_year:
#             return float(payload.get("ytd_amount", 0) or 0)
#         return float(payload.get("full_amount", 0) or 0)
    
    
#     def get_display_qty(category_name, year):
#         payload = data[category_name].get(year, {})
#         if is_last_year_incomplete and year == last_year:
#             return float(payload.get("ytd_qty", 0) or 0)
#         return float(payload.get("full_qty", 0) or 0)

#     sorted_names = sorted(
#         data.keys(),
#         key=lambda name: (
#             get_display_value(name, last_year) if last_year else 0,
#             sum(get_display_value(name, y) for y in years),
#             name,
#         ),
#         reverse=True,
#     )

#     cur_row = data_start_row
#     totals_full_by_year = {y: 0 for y in years}
#     totals_ytd_by_year = {y: 0 for y in years}
#     totals_full_qty_by_year = {y: 0 for y in years}
#     totals_ytd_qty_by_year = {y: 0 for y in years}
#     grand_total = 0
#     # -------------------------------------------------
#     # Строки данных
#     # -------------------------------------------------
#     for name in sorted_names:
#         row_values = []
#         number_formats = {}
#         display_values_by_year = {}

#         for y in years:
#             full_amount = float(data[name].get(y, {}).get("full_amount", 0) or 0)
#             ytd_amount = float(data[name].get(y, {}).get("ytd_amount", 0) or 0)
#             full_qty = float(data[name].get(y, {}).get("full_qty", 0) or 0)
#             ytd_qty = float(data[name].get(y, {}).get("ytd_qty", 0) or 0)

#             display_val = ytd_amount if (is_last_year_incomplete and y == last_year) else full_amount
#             display_values_by_year[y] = display_val

#             totals_full_by_year[y] += full_amount
#             totals_ytd_by_year[y] += ytd_amount
#             totals_full_qty_by_year[y] += full_qty
#             totals_ytd_qty_by_year[y] += ytd_qty
            
#         row_total = sum(display_values_by_year[y] for y in years)
#         grand_total += row_total

#         for key, _label in layout:
#             if key == "name":
#                 row_values.append(name)

#             elif key.startswith("year_"):
#                 y = int(key.replace("year_", ""))
#                 val = display_values_by_year[y]
#                 row_values.append(None if val == 0 else val)
#                 number_formats[len(row_values)] = FORMATS["money"]

#             elif key.startswith("delta_"):
#                 _, prev_y, curr_y = key.split("_")
#                 prev_y = int(prev_y)
#                 curr_y = int(curr_y)

#                 if is_last_year_incomplete and curr_y == last_year:
#                     prev_val = float(data[name].get(prev_y, {}).get("ytd_amount", 0) or 0)
#                     curr_val = float(data[name].get(curr_y, {}).get("ytd_amount", 0) or 0)
#                 else:
#                     prev_val = float(data[name].get(prev_y, {}).get("full_amount", 0) or 0)
#                     curr_val = float(data[name].get(curr_y, {}).get("full_amount", 0) or 0)

#                 delta = 0 if prev_val == 0 else (curr_val - prev_val) / prev_val
#                 row_values.append(None if prev_val == 0 and curr_val == 0 else delta)
#                 number_formats[len(row_values)] = FORMATS["pct"]

#             elif key.startswith("gap_after_"):
#                 row_values.append(None)

#             elif key == "gap_before_qty":
#                 row_values.append(None)

#             elif key == "qty_last":
#                 if years:
#                     qty_last_val = get_display_qty(name, years[-1])
#                 else:
#                     qty_last_val = 0
#                 row_values.append(None if qty_last_val == 0 else qty_last_val)
#                 number_formats[len(row_values)] = '#,##0'

#             elif key == "qty_delta":
#                 if len(years) >= 2:
#                     prev_qty = get_display_qty(name, years[-2])
#                     last_qty = get_display_qty(name, years[-1])
#                     qty_delta = 0 if prev_qty == 0 else (last_qty - prev_qty) / prev_qty
#                     row_values.append(None if prev_qty == 0 and last_qty == 0 else qty_delta)
#                 else:
#                     row_values.append(None)
#                 number_formats[len(row_values)] = FORMATS["pct"]

#             elif key == "total":
#                 row_values.append(None if row_total == 0 else row_total)
#                 number_formats[len(row_values)] = FORMATS["money"]

#         style_data_row(
#             ws,
#             row=cur_row,
#             values=row_values,
#             number_formats=number_formats,
#         )

#         # форматируем delta-колонки
#         for key, col_idx in col_map.items():
#             if key.startswith("delta_") or key == "qty_delta":
#                 cell = ws.cell(row=cur_row, column=col_idx)
#                 cell.alignment = ALIGNMENTS["center"]
#                 if isinstance(cell.value, (int, float)) and cell.value < 0:
#                     cell.fill = FILLS["section"]
#                     cell.font = FONTS["bold"]

#         ws.cell(row=cur_row, column=col_map["total"]).alignment = ALIGNMENTS["right"]

#         cur_row += 1

#     # -------------------------------------------------
#     # ИТОГО
#     # -------------------------------------------------
#     total_values = []
#     total_number_formats = {}

#     for key, _label in layout:
#         if key == "name":
#             total_values.append("ИТОГО")

#         elif key.startswith("year_"):
#             y = int(key.replace("year_", ""))
#             total_val = totals_ytd_by_year[y] if (is_last_year_incomplete and y == last_year) else totals_full_by_year[y]
#             total_values.append(total_val)
#             total_number_formats[len(total_values)] = FORMATS["money"]

#         elif key.startswith("delta_"):
#             _, prev_y, curr_y = key.split("_")
#             prev_y = int(prev_y)
#             curr_y = int(curr_y)

#             if is_last_year_incomplete and curr_y == last_year:
#                 prev_total = totals_ytd_by_year[prev_y]
#                 curr_total = totals_ytd_by_year[curr_y]
#             else:
#                 prev_total = totals_full_by_year[prev_y]
#                 curr_total = totals_full_by_year[curr_y]

#             delta_total = 0 if prev_total == 0 else (curr_total - prev_total) / prev_total
#             total_values.append(delta_total)
#             total_number_formats[len(total_values)] = FORMATS["pct"]

#         elif key.startswith("gap_after_"):
#             total_values.append(None)

#         elif key == "gap_before_qty":
#             total_values.append(None)

#         elif key == "qty_last":
#             if years:
#                 qty_total = totals_ytd_qty_by_year[years[-1]] if (is_last_year_incomplete and years[-1] == last_year) else totals_full_qty_by_year[years[-1]]
#             else:
#                 qty_total = 0
#             total_values.append(qty_total)
#             total_number_formats[len(total_values)] = '#,##0'

#         elif key == "qty_delta":
#             if len(years) >= 2:
#                 prev_qty_total = totals_ytd_qty_by_year[years[-2]] if (is_last_year_incomplete and years[-2] == last_year) else totals_full_qty_by_year[years[-2]]
#                 last_qty_total = totals_ytd_qty_by_year[years[-1]] if (is_last_year_incomplete and years[-1] == last_year) else totals_full_qty_by_year[years[-1]]
#                 total_qty_delta = 0 if prev_qty_total == 0 else (last_qty_total - prev_qty_total) / prev_qty_total
#                 total_values.append(total_qty_delta)
#             else:
#                 total_values.append(None)
#             total_number_formats[len(total_values)] = FORMATS["pct"]

#         elif key == "total":
#             total_values.append(grand_total)
#             total_number_formats[len(total_values)] = FORMATS["money"]

#     style_total_row(
#         ws,
#         row=cur_row,
#         values=total_values,
#         number_formats=total_number_formats,
#     )

#     total_row = cur_row

#     # -------------------------------------------------
#     # Очищаем gap-колонки
#     # -------------------------------------------------
#     for gap_col in gap_cols:
#         clear_column(ws, col_idx=gap_col, row_start=header_row, row_end=total_row)

#     # -------------------------------------------------
#     # Widths
#     # -------------------------------------------------
#     widths = {"A": 38}

#     for key, col_idx in col_map.items():
#         col_letter = ws.cell(1, col_idx).column_letter

#         if key.startswith("year_"):
#             widths[col_letter] = 14
#         elif key.startswith("delta_"):
#             widths[col_letter] = 13
#         elif key.startswith("gap_after_") or key == "gap_before_qty":
#             widths[col_letter] = 3.5
#         elif key == "qty_last":
#             widths[col_letter] = 12
#         elif key == "qty_delta":
#             widths[col_letter] = 13
#         elif key == "total":
#             widths[col_letter] = 16

#     set_column_widths(ws, widths)

#     # -------------------------------------------------
#     # Heights
#     # -------------------------------------------------
#     set_row_heights(
#         ws,
#         {
#             2: 24,
#             3: 18,
#             4: 34,
#             8: 30,
#         },
#     )

#     hide_grid_and_freeze(ws, "B9")














# from collections import defaultdict

# from ..styles.theme import FORMATS, ALIGNMENTS, FILLS, FONTS
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


# def build_categories_sheet(wb, years, rows):
#     ws = wb.create_sheet("Categories")
#     ws.sheet_properties.outlinePr.summaryBelow = False

#     draw_toc_button(ws, cell="A1", target_sheet="TOC")

#     # -------------------------------------------------
#     # Дата среза
#     # -------------------------------------------------
#     if rows:
#         cutoff_year = int(rows[0].get("cutoff_year") or 0)
#         cutoff_month = int(rows[0].get("cutoff_month") or 0)
#         cutoff_day = int(rows[0].get("cutoff_day") or 0)
#     else:
#         cutoff_year = 0
#         cutoff_month = 0
#         cutoff_day = 0

#     last_year = years[-1] if years else None
#     is_last_year_incomplete = bool(
#         last_year
#         and cutoff_year == last_year
#         and (cutoff_month < 12 or cutoff_day < 31)
#     )

#     compare_prev_year = years[-2] if len(years) >= 2 else None
#     compare_last_year = years[-1] if years else None

#     if is_last_year_incomplete and compare_prev_year is not None and compare_last_year is not None:
#         note = (
#             f"Для закрытых лет показана выручка и YOY. "
#             f"Для {last_year} год еще не закрыт, поэтому последний блок рассчитан как YTD "
#             f"на {cutoff_day:02d}.{cutoff_month:02d}.{cutoff_year}: "
#             f"сравнение {compare_last_year} с {compare_prev_year} за сопоставимый период. "
#             f"Справа дополнительно показан объем реализации в штуках: "
#             f"{compare_prev_year} YTD, {compare_last_year} YTD и абсолютное изменение в штуках."
#         )
#     else:
#         note = (
#             "Показана выручка по категориям в разрезе лет, изменение к предыдущему году и итог за период. "
#             "Справа дополнительно показан объем реализации в штуках за предыдущий и текущий год, "
#             "а также абсолютное изменение в штуках."
#         )

#     # -------------------------------------------------
#     # Layout колонок
#     # -------------------------------------------------
#     layout = [("name", "Категория")]

#     for i, y in enumerate(years):
#         year_header = f"{y}\nYTD" if (is_last_year_incomplete and y == last_year) else str(y)
#         layout.append((f"year_{y}", year_header))

#         if i > 0:
#             prev_y = years[i - 1]
#             delta_header = (
#                 f"YTD\n{prev_y}→{y}"
#                 if (is_last_year_incomplete and y == last_year)
#                 else f"YOY\n{prev_y}→{y}"
#             )
#             layout.append((f"delta_{prev_y}_{y}", delta_header))

#         layout.append((f"gap_after_{y}", ""))

#     if compare_last_year is not None:
#         if compare_prev_year is not None:
#             qty_prev_header = (
#                 f"{compare_prev_year}\nШт YTD"
#                 if is_last_year_incomplete
#                 else f"{compare_prev_year}\nШт"
#             )
#         else:
#             qty_prev_header = "Пред.\nШт"

#         qty_last_header = (
#             f"{compare_last_year}\nШт YTD"
#             if is_last_year_incomplete
#             else f"{compare_last_year}\nШт"
#         )

#         qty_delta_header = (
#             f"Δ Шт\n{compare_prev_year}→{compare_last_year}"
#             if compare_prev_year is not None
#             else "Δ Шт"
#         )

#         layout.extend(
#             [
#                 ("gap_before_qty", ""),
#                 ("qty_prev", qty_prev_header),
#                 ("qty_last", qty_last_header),
#                 ("qty_delta", qty_delta_header),
#             ]
#         )

#     layout.append(("total", "Итого"))

#     headers = [label for _, label in layout]

#     gap_cols = set()
#     col_map = {}
#     for idx, (key, _) in enumerate(layout, start=1):
#         col_map[key] = idx
#         if key.startswith("gap_after_") or key == "gap_before_qty":
#             gap_cols.add(idx)

#     last_used_col = len(layout)

#     draw_sheet_header(
#         ws,
#         title="Категории",
#         subtitle="Выручка по категориям в разрезе лет",
#         note=note,
#         line_to_col=last_used_col,
#     )

#     header_row = 8
#     data_start_row = 9

#     draw_table_header_with_gaps(
#         ws,
#         row=header_row,
#         headers=headers,
#         wrap=True,
#         gap_cols=gap_cols,
#     )

#     # -------------------------------------------------
#     # Подготовка данных
#     # -------------------------------------------------
#     data = defaultdict(dict)

#     for r in rows:
#         category = r.get("category") or r.get("root_category") or "—"
#         year = int(r.get("year"))
#         full_amount = float(r.get("full_amount") or 0)
#         ytd_amount = float(r.get("ytd_amount") or 0)
#         full_qty = float(r.get("full_qty") or 0)
#         ytd_qty = float(r.get("ytd_qty") or 0)
#         sku_count = float(r.get("sku_count") or 0)

#         data[category][year] = {
#             "full_amount": full_amount,
#             "ytd_amount": ytd_amount,
#             "full_qty": full_qty,
#             "ytd_qty": ytd_qty,
#             "sku_count": sku_count,
#         }

#     def get_display_value(category_name, year):
#         payload = data[category_name].get(year, {})
#         if is_last_year_incomplete and year == last_year:
#             return float(payload.get("ytd_amount", 0) or 0)
#         return float(payload.get("full_amount", 0) or 0)

#     def get_display_qty(category_name, year):
#         payload = data[category_name].get(year, {})
#         if is_last_year_incomplete and year in {compare_prev_year, compare_last_year}:
#             return float(payload.get("ytd_qty", 0) or 0)
#         return float(payload.get("full_qty", 0) or 0)

#     sorted_names = sorted(
#         data.keys(),
#         key=lambda name: (
#             get_display_value(name, last_year) if last_year else 0,
#             sum(get_display_value(name, y) for y in years),
#             name,
#         ),
#         reverse=True,
#     )

#     cur_row = data_start_row
#     totals_full_by_year = {y: 0 for y in years}
#     totals_ytd_by_year = {y: 0 for y in years}
#     totals_full_qty_by_year = {y: 0 for y in years}
#     totals_ytd_qty_by_year = {y: 0 for y in years}
#     grand_total = 0

#     # -------------------------------------------------
#     # Строки данных
#     # -------------------------------------------------
#     for name in sorted_names:
#         row_values = []
#         number_formats = {}
#         display_values_by_year = {}

#         for y in years:
#             full_amount = float(data[name].get(y, {}).get("full_amount", 0) or 0)
#             ytd_amount = float(data[name].get(y, {}).get("ytd_amount", 0) or 0)
#             full_qty = float(data[name].get(y, {}).get("full_qty", 0) or 0)
#             ytd_qty = float(data[name].get(y, {}).get("ytd_qty", 0) or 0)

#             display_val = ytd_amount if (is_last_year_incomplete and y == last_year) else full_amount
#             display_values_by_year[y] = display_val

#             totals_full_by_year[y] += full_amount
#             totals_ytd_by_year[y] += ytd_amount
#             totals_full_qty_by_year[y] += full_qty
#             totals_ytd_qty_by_year[y] += ytd_qty

#         row_total = sum(display_values_by_year[y] for y in years)
#         grand_total += row_total

#         for key, _label in layout:
#             if key == "name":
#                 row_values.append(name)

#             elif key.startswith("year_"):
#                 y = int(key.replace("year_", ""))
#                 val = display_values_by_year[y]
#                 row_values.append(None if val == 0 else val)
#                 number_formats[len(row_values)] = FORMATS["money"]

#             elif key.startswith("delta_"):
#                 _, prev_y, curr_y = key.split("_")
#                 prev_y = int(prev_y)
#                 curr_y = int(curr_y)

#                 if is_last_year_incomplete and curr_y == last_year:
#                     prev_val = float(data[name].get(prev_y, {}).get("ytd_amount", 0) or 0)
#                     curr_val = float(data[name].get(curr_y, {}).get("ytd_amount", 0) or 0)
#                 else:
#                     prev_val = float(data[name].get(prev_y, {}).get("full_amount", 0) or 0)
#                     curr_val = float(data[name].get(curr_y, {}).get("full_amount", 0) or 0)

#                 delta = 0 if prev_val == 0 else (curr_val - prev_val) / prev_val
#                 row_values.append(None if prev_val == 0 and curr_val == 0 else delta)
#                 number_formats[len(row_values)] = FORMATS["pct"]

#             elif key.startswith("gap_after_"):
#                 row_values.append(None)

#             elif key == "gap_before_qty":
#                 row_values.append(None)

#             elif key == "qty_prev":
#                 if compare_prev_year is not None:
#                     qty_prev_val = get_display_qty(name, compare_prev_year)
#                     row_values.append(None if qty_prev_val == 0 else qty_prev_val)
#                 else:
#                     row_values.append(None)
#                 number_formats[len(row_values)] = '#,##0'

#             elif key == "qty_last":
#                 if compare_last_year is not None:
#                     qty_last_val = get_display_qty(name, compare_last_year)
#                     row_values.append(None if qty_last_val == 0 else qty_last_val)
#                 else:
#                     row_values.append(None)
#                 number_formats[len(row_values)] = '#,##0'

#             elif key == "qty_delta":
#                 if compare_prev_year is not None and compare_last_year is not None:
#                     prev_qty = get_display_qty(name, compare_prev_year)
#                     last_qty = get_display_qty(name, compare_last_year)
#                     qty_delta = last_qty - prev_qty
#                     row_values.append(None if prev_qty == 0 and last_qty == 0 else qty_delta)
#                 else:
#                     row_values.append(None)
#                 number_formats[len(row_values)] = '#,##0'

#             elif key == "total":
#                 row_values.append(None if row_total == 0 else row_total)
#                 number_formats[len(row_values)] = FORMATS["money"]

#         style_data_row(
#             ws,
#             row=cur_row,
#             values=row_values,
#             number_formats=number_formats,
#         )

#         # форматируем процентные delta-колонки
#         for key, col_idx in col_map.items():
#             if key.startswith("delta_"):
#                 cell = ws.cell(row=cur_row, column=col_idx)
#                 cell.alignment = ALIGNMENTS["center"]
#                 if isinstance(cell.value, (int, float)) and cell.value < 0:
#                     cell.fill = FILLS["section"]
#                     cell.font = FONTS["bold"]

#         # форматируем delta по штукам
#         if "qty_delta" in col_map:
#             cell = ws.cell(row=cur_row, column=col_map["qty_delta"])
#             cell.alignment = ALIGNMENTS["center"]
#             if isinstance(cell.value, (int, float)) and cell.value < 0:
#                 cell.fill = FILLS["section"]
#                 cell.font = FONTS["bold"]

#         if "qty_prev" in col_map:
#             ws.cell(row=cur_row, column=col_map["qty_prev"]).alignment = ALIGNMENTS["center"]

#         if "qty_last" in col_map:
#             ws.cell(row=cur_row, column=col_map["qty_last"]).alignment = ALIGNMENTS["center"]

#         ws.cell(row=cur_row, column=col_map["total"]).alignment = ALIGNMENTS["right"]

#         cur_row += 1

#     # -------------------------------------------------
#     # ИТОГО
#     # -------------------------------------------------
#     total_values = []
#     total_number_formats = {}

#     for key, _label in layout:
#         if key == "name":
#             total_values.append("ИТОГО")

#         elif key.startswith("year_"):
#             y = int(key.replace("year_", ""))
#             total_val = totals_ytd_by_year[y] if (is_last_year_incomplete and y == last_year) else totals_full_by_year[y]
#             total_values.append(total_val)
#             total_number_formats[len(total_values)] = FORMATS["money"]

#         elif key.startswith("delta_"):
#             _, prev_y, curr_y = key.split("_")
#             prev_y = int(prev_y)
#             curr_y = int(curr_y)

#             if is_last_year_incomplete and curr_y == last_year:
#                 prev_total = totals_ytd_by_year[prev_y]
#                 curr_total = totals_ytd_by_year[curr_y]
#             else:
#                 prev_total = totals_full_by_year[prev_y]
#                 curr_total = totals_full_by_year[curr_y]

#             delta_total = 0 if prev_total == 0 else (curr_total - prev_total) / prev_total
#             total_values.append(delta_total)
#             total_number_formats[len(total_values)] = FORMATS["pct"]

#         elif key.startswith("gap_after_"):
#             total_values.append(None)

#         elif key == "gap_before_qty":
#             total_values.append(None)

#         elif key == "qty_prev":
#             if compare_prev_year is not None:
#                 qty_prev_total = (
#                     totals_ytd_qty_by_year[compare_prev_year]
#                     if is_last_year_incomplete
#                     else totals_full_qty_by_year[compare_prev_year]
#                 )
#                 total_values.append(qty_prev_total)
#             else:
#                 total_values.append(None)
#             total_number_formats[len(total_values)] = '#,##0'

#         elif key == "qty_last":
#             if compare_last_year is not None:
#                 qty_last_total = (
#                     totals_ytd_qty_by_year[compare_last_year]
#                     if is_last_year_incomplete
#                     else totals_full_qty_by_year[compare_last_year]
#                 )
#                 total_values.append(qty_last_total)
#             else:
#                 total_values.append(None)
#             total_number_formats[len(total_values)] = '#,##0'

#         elif key == "qty_delta":
#             if compare_prev_year is not None and compare_last_year is not None:
#                 prev_qty_total = (
#                     totals_ytd_qty_by_year[compare_prev_year]
#                     if is_last_year_incomplete
#                     else totals_full_qty_by_year[compare_prev_year]
#                 )
#                 last_qty_total = (
#                     totals_ytd_qty_by_year[compare_last_year]
#                     if is_last_year_incomplete
#                     else totals_full_qty_by_year[compare_last_year]
#                 )
#                 total_qty_delta = last_qty_total - prev_qty_total
#                 total_values.append(total_qty_delta)
#             else:
#                 total_values.append(None)
#             total_number_formats[len(total_values)] = '#,##0'

#         elif key == "total":
#             total_values.append(grand_total)
#             total_number_formats[len(total_values)] = FORMATS["money"]

#     style_total_row(
#         ws,
#         row=cur_row,
#         values=total_values,
#         number_formats=total_number_formats,
#     )

#     total_row = cur_row

#     if "qty_delta" in col_map:
#         cell = ws.cell(row=total_row, column=col_map["qty_delta"])
#         cell.alignment = ALIGNMENTS["center"]
#         if isinstance(cell.value, (int, float)) and cell.value < 0:
#             cell.fill = FILLS["section"]
#             cell.font = FONTS["bold"]

#     if "qty_prev" in col_map:
#         ws.cell(row=total_row, column=col_map["qty_prev"]).alignment = ALIGNMENTS["center"]

#     if "qty_last" in col_map:
#         ws.cell(row=total_row, column=col_map["qty_last"]).alignment = ALIGNMENTS["center"]

#     # -------------------------------------------------
#     # Очищаем gap-колонки
#     # -------------------------------------------------
#     for gap_col in gap_cols:
#         clear_column(ws, col_idx=gap_col, row_start=header_row, row_end=total_row)

#     # -------------------------------------------------
#     # Widths
#     # -------------------------------------------------
#     widths = {"A": 38}

#     for key, col_idx in col_map.items():
#         col_letter = ws.cell(1, col_idx).column_letter

#         if key.startswith("year_"):
#             widths[col_letter] = 14
#         elif key.startswith("delta_"):
#             widths[col_letter] = 13
#         elif key.startswith("gap_after_") or key == "gap_before_qty":
#             widths[col_letter] = 3.5
#         elif key == "qty_prev":
#             widths[col_letter] = 12
#         elif key == "qty_last":
#             widths[col_letter] = 12
#         elif key == "qty_delta":
#             widths[col_letter] = 12
#         elif key == "total":
#             widths[col_letter] = 16

#     set_column_widths(ws, widths)

#     # -------------------------------------------------
#     # Heights
#     # -------------------------------------------------
#     set_row_heights(
#         ws,
#         {
#             2: 24,
#             3: 18,
#             4: 36,
#             8: 30,
#         },
#     )

#     hide_grid_and_freeze(ws, "B9")






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
    clear_column,
)


def build_categories_sheet(wb, years, rows):
    ws = wb.create_sheet("Categories")
    ws.sheet_properties.outlinePr.summaryBelow = False

    draw_toc_button(ws, cell="A1", target_sheet="TOC")

    # -------------------------------------------------
    # Дата среза
    # -------------------------------------------------
    if rows:
        cutoff_year = int(rows[0].get("cutoff_year") or 0)
        cutoff_month = int(rows[0].get("cutoff_month") or 0)
        cutoff_day = int(rows[0].get("cutoff_day") or 0)
    else:
        cutoff_year = 0
        cutoff_month = 0
        cutoff_day = 0

    last_year = years[-1] if years else None
    is_last_year_incomplete = bool(
        last_year
        and cutoff_year == last_year
        and (cutoff_month < 12 or cutoff_day < 31)
    )

    compare_prev_year = years[-2] if len(years) >= 2 else None
    compare_last_year = years[-1] if years else None

    if is_last_year_incomplete and compare_prev_year is not None and compare_last_year is not None:
        note = (
            f"Для закрытых лет показана выручка и YOY. "
            f"Для {last_year} год еще не закрыт, поэтому последний блок рассчитан как YTD "
            f"на {cutoff_day:02d}.{cutoff_month:02d}.{cutoff_year}: "
            f"сравнение {compare_last_year} с {compare_prev_year} за сопоставимый период. "
            f"После денежного блока отдельно показан объем реализации в штуках: "
            f"{compare_prev_year} YTD, {compare_last_year} YTD и абсолютное изменение в штуках."
        )
    else:
        note = (
            "Показана выручка по категориям в разрезе лет, изменение к предыдущему году и итог за период. "
            "После денежного блока отдельно показан объем реализации в штуках за предыдущий и текущий год, "
            "а также абсолютное изменение в штуках."
        )

    # -------------------------------------------------
    # Layout колонок
    # Логика:
    # Категория | годы и YOY | Итого ₽ | узкий разделитель | штуки
    # -------------------------------------------------
    layout = [("name", "Категория")]

    for i, y in enumerate(years):
        year_header = f"{y}\nYTD" if (is_last_year_incomplete and y == last_year) else str(y)
        layout.append((f"year_{y}", year_header))

        if i > 0:
            prev_y = years[i - 1]
            delta_header = (
                f"YTD\n{prev_y}→{y}"
                if (is_last_year_incomplete and y == last_year)
                else f"YOY\n{prev_y}→{y}"
            )
            layout.append((f"delta_{prev_y}_{y}", delta_header))

        layout.append((f"gap_after_{y}", ""))

    # ИТОГО сразу после денежного блока
    layout.append(("total", "Итого"))

    # потом отдельный операционный блок по штукам
    if compare_last_year is not None:
        if compare_prev_year is not None:
            qty_prev_header = (
                f"{compare_prev_year}\nШт YTD"
                if is_last_year_incomplete
                else f"{compare_prev_year}\nШт"
            )
        else:
            qty_prev_header = "Пред.\nШт"

        qty_last_header = (
            f"{compare_last_year}\nШт YTD"
            if is_last_year_incomplete
            else f"{compare_last_year}\nШт"
        )

        qty_delta_header = (
            f"Δ Шт\n{compare_prev_year}→{compare_last_year}"
            if compare_prev_year is not None
            else "Δ Шт"
        )

        layout.extend(
            [
                ("gap_before_qty", ""),
                ("qty_prev", qty_prev_header),
                ("qty_last", qty_last_header),
                ("qty_delta", qty_delta_header),
            ]
        )

    headers = [label for _, label in layout]

    gap_cols = set()
    col_map = {}
    for idx, (key, _) in enumerate(layout, start=1):
        col_map[key] = idx
        if key.startswith("gap_after_") or key == "gap_before_qty":
            gap_cols.add(idx)

    last_used_col = len(layout)

    draw_sheet_header(
        ws,
        title="Категории",
        subtitle="Выручка по категориям в разрезе лет",
        note=note,
        line_to_col=last_used_col,
    )

    header_row = 8
    data_start_row = 9

    draw_table_header_with_gaps(
        ws,
        row=header_row,
        headers=headers,
        wrap=True,
        gap_cols=gap_cols,
    )

    # -------------------------------------------------
    # Подготовка данных
    # -------------------------------------------------
    data = defaultdict(dict)

    for r in rows:
        category = r.get("category") or r.get("root_category") or "—"
        year = int(r.get("year"))
        full_amount = float(r.get("full_amount") or 0)
        ytd_amount = float(r.get("ytd_amount") or 0)
        full_qty = float(r.get("full_qty") or 0)
        ytd_qty = float(r.get("ytd_qty") or 0)
        sku_count = float(r.get("sku_count") or 0)

        data[category][year] = {
            "full_amount": full_amount,
            "ytd_amount": ytd_amount,
            "full_qty": full_qty,
            "ytd_qty": ytd_qty,
            "sku_count": sku_count,
        }

    def get_display_amount(category_name, year):
        payload = data[category_name].get(year, {})
        if is_last_year_incomplete and year == last_year:
            return float(payload.get("ytd_amount", 0) or 0)
        return float(payload.get("full_amount", 0) or 0)

    def get_display_qty(category_name, year):
        payload = data[category_name].get(year, {})
        if is_last_year_incomplete and year in {compare_prev_year, compare_last_year}:
            return float(payload.get("ytd_qty", 0) or 0)
        return float(payload.get("full_qty", 0) or 0)

    sorted_names = sorted(
        data.keys(),
        key=lambda name: (
            get_display_amount(name, last_year) if last_year else 0,
            sum(get_display_amount(name, y) for y in years),
            name,
        ),
        reverse=True,
    )

    cur_row = data_start_row

    totals_full_by_year = {y: 0 for y in years}
    totals_ytd_by_year = {y: 0 for y in years}
    totals_full_qty_by_year = {y: 0 for y in years}
    totals_ytd_qty_by_year = {y: 0 for y in years}
    grand_total = 0

    # -------------------------------------------------
    # Строки данных
    # -------------------------------------------------
    for name in sorted_names:
        row_values = []
        number_formats = {}
        display_values_by_year = {}

        for y in years:
            full_amount = float(data[name].get(y, {}).get("full_amount", 0) or 0)
            ytd_amount = float(data[name].get(y, {}).get("ytd_amount", 0) or 0)
            full_qty = float(data[name].get(y, {}).get("full_qty", 0) or 0)
            ytd_qty = float(data[name].get(y, {}).get("ytd_qty", 0) or 0)

            display_val = ytd_amount if (is_last_year_incomplete and y == last_year) else full_amount
            display_values_by_year[y] = display_val

            totals_full_by_year[y] += full_amount
            totals_ytd_by_year[y] += ytd_amount
            totals_full_qty_by_year[y] += full_qty
            totals_ytd_qty_by_year[y] += ytd_qty

        row_total = sum(display_values_by_year[y] for y in years)
        grand_total += row_total

        for key, _label in layout:
            if key == "name":
                row_values.append(name)

            elif key.startswith("year_"):
                y = int(key.replace("year_", ""))
                val = display_values_by_year[y]
                row_values.append(None if val == 0 else val)
                number_formats[len(row_values)] = FORMATS["money"]

            elif key.startswith("delta_"):
                _, prev_y, curr_y = key.split("_")
                prev_y = int(prev_y)
                curr_y = int(curr_y)

                if is_last_year_incomplete and curr_y == last_year:
                    prev_val = float(data[name].get(prev_y, {}).get("ytd_amount", 0) or 0)
                    curr_val = float(data[name].get(curr_y, {}).get("ytd_amount", 0) or 0)
                else:
                    prev_val = float(data[name].get(prev_y, {}).get("full_amount", 0) or 0)
                    curr_val = float(data[name].get(curr_y, {}).get("full_amount", 0) or 0)

                delta = 0 if prev_val == 0 else (curr_val - prev_val) / prev_val
                row_values.append(None if prev_val == 0 and curr_val == 0 else delta)
                number_formats[len(row_values)] = FORMATS["pct"]

            elif key.startswith("gap_after_"):
                row_values.append(None)

            elif key == "total":
                row_total_display = None if row_total == 0 else row_total
                row_values.append(row_total_display)
                number_formats[len(row_values)] = FORMATS["money"]

            elif key == "gap_before_qty":
                row_values.append(None)

            elif key == "qty_prev":
                if compare_prev_year is not None:
                    qty_prev_val = get_display_qty(name, compare_prev_year)
                    row_values.append(None if qty_prev_val == 0 else qty_prev_val)
                else:
                    row_values.append(None)
                number_formats[len(row_values)] = '#,##0'

            elif key == "qty_last":
                if compare_last_year is not None:
                    qty_last_val = get_display_qty(name, compare_last_year)
                    row_values.append(None if qty_last_val == 0 else qty_last_val)
                else:
                    row_values.append(None)
                number_formats[len(row_values)] = '#,##0'

            elif key == "qty_delta":
                if compare_prev_year is not None and compare_last_year is not None:
                    prev_qty = get_display_qty(name, compare_prev_year)
                    last_qty = get_display_qty(name, compare_last_year)
                    qty_delta = last_qty - prev_qty
                    row_values.append(None if prev_qty == 0 and last_qty == 0 else qty_delta)
                else:
                    row_values.append(None)
                number_formats[len(row_values)] = '#,##0;[Red]-#,##0'

        style_data_row(
            ws,
            row=cur_row,
            values=row_values,
            number_formats=number_formats,
        )

        # Выручка YOY
        for key, col_idx in col_map.items():
            if key.startswith("delta_"):
                cell = ws.cell(row=cur_row, column=col_idx)
                cell.alignment = ALIGNMENTS["center"]
                if isinstance(cell.value, (int, float)) and cell.value < 0:
                    cell.fill = FILLS["section"]
                    cell.font = FONTS["bold"]

        # Qty блок
        if "qty_prev" in col_map:
            ws.cell(row=cur_row, column=col_map["qty_prev"]).alignment = ALIGNMENTS["center"]

        if "qty_last" in col_map:
            ws.cell(row=cur_row, column=col_map["qty_last"]).alignment = ALIGNMENTS["center"]

        if "qty_delta" in col_map:
            cell = ws.cell(row=cur_row, column=col_map["qty_delta"])
            cell.alignment = ALIGNMENTS["center"]
            if isinstance(cell.value, (int, float)) and cell.value < 0:
                cell.fill = FILLS["section"]
                cell.font = FONTS["bold"]

        if "total" in col_map:
            ws.cell(row=cur_row, column=col_map["total"]).alignment = ALIGNMENTS["right"]

        cur_row += 1

    # -------------------------------------------------
    # ИТОГО
    # -------------------------------------------------
    total_values = []
    total_number_formats = {}

    for key, _label in layout:
        if key == "name":
            total_values.append("ИТОГО")

        elif key.startswith("year_"):
            y = int(key.replace("year_", ""))
            total_val = totals_ytd_by_year[y] if (is_last_year_incomplete and y == last_year) else totals_full_by_year[y]
            total_values.append(total_val)
            total_number_formats[len(total_values)] = FORMATS["money"]

        elif key.startswith("delta_"):
            _, prev_y, curr_y = key.split("_")
            prev_y = int(prev_y)
            curr_y = int(curr_y)

            if is_last_year_incomplete and curr_y == last_year:
                prev_total = totals_ytd_by_year[prev_y]
                curr_total = totals_ytd_by_year[curr_y]
            else:
                prev_total = totals_full_by_year[prev_y]
                curr_total = totals_full_by_year[curr_y]

            delta_total = 0 if prev_total == 0 else (curr_total - prev_total) / prev_total
            total_values.append(delta_total)
            total_number_formats[len(total_values)] = FORMATS["pct"]

        elif key.startswith("gap_after_"):
            total_values.append(None)

        elif key == "total":
            total_values.append(grand_total)
            total_number_formats[len(total_values)] = FORMATS["money"]

        elif key == "gap_before_qty":
            total_values.append(None)

        elif key == "qty_prev":
            if compare_prev_year is not None:
                qty_prev_total = (
                    totals_ytd_qty_by_year[compare_prev_year]
                    if is_last_year_incomplete
                    else totals_full_qty_by_year[compare_prev_year]
                )
                total_values.append(qty_prev_total)
            else:
                total_values.append(None)
            total_number_formats[len(total_values)] = '#,##0'

        elif key == "qty_last":
            if compare_last_year is not None:
                qty_last_total = (
                    totals_ytd_qty_by_year[compare_last_year]
                    if is_last_year_incomplete
                    else totals_full_qty_by_year[compare_last_year]
                )
                total_values.append(qty_last_total)
            else:
                total_values.append(None)
            total_number_formats[len(total_values)] = '#,##0'

        elif key == "qty_delta":
            if compare_prev_year is not None and compare_last_year is not None:
                prev_qty_total = (
                    totals_ytd_qty_by_year[compare_prev_year]
                    if is_last_year_incomplete
                    else totals_full_qty_by_year[compare_prev_year]
                )
                last_qty_total = (
                    totals_ytd_qty_by_year[compare_last_year]
                    if is_last_year_incomplete
                    else totals_full_qty_by_year[compare_last_year]
                )
                total_qty_delta = last_qty_total - prev_qty_total
                total_values.append(total_qty_delta)
            else:
                total_values.append(None)
            total_number_formats[len(total_values)] = '#,##0;[Red]-#,##0'

    style_total_row(
        ws,
        row=cur_row,
        values=total_values,
        number_formats=total_number_formats,
    )

    total_row = cur_row

    # Доп. выравнивание итоговой строки
    if "qty_prev" in col_map:
        ws.cell(row=total_row, column=col_map["qty_prev"]).alignment = ALIGNMENTS["center"]

    if "qty_last" in col_map:
        ws.cell(row=total_row, column=col_map["qty_last"]).alignment = ALIGNMENTS["center"]

    if "qty_delta" in col_map:
        cell = ws.cell(row=total_row, column=col_map["qty_delta"])
        cell.alignment = ALIGNMENTS["center"]
        if isinstance(cell.value, (int, float)) and cell.value < 0:
            cell.fill = FILLS["section"]
            cell.font = FONTS["bold"]

    if "total" in col_map:
        ws.cell(row=total_row, column=col_map["total"]).alignment = ALIGNMENTS["right"]

    # -------------------------------------------------
    # Очищаем gap-колонки
    # -------------------------------------------------
    for gap_col in gap_cols:
        clear_column(ws, col_idx=gap_col, row_start=header_row, row_end=total_row)

    # -------------------------------------------------
    # Widths
    # Логика:
    # - обычные gap между денежными блоками = 3.0
    # - gap перед qty-блоком = 2.0, чтобы не казался слишком широким
    # -------------------------------------------------
    widths = {"A": 38}

    for key, col_idx in col_map.items():
        col_letter = ws.cell(1, col_idx).column_letter

        if key.startswith("year_"):
            widths[col_letter] = 14
        elif key.startswith("delta_"):
            widths[col_letter] = 13
        elif key.startswith("gap_after_"):
            widths[col_letter] = 3.0
        elif key == "total":
            widths[col_letter] = 16
        elif key == "gap_before_qty":
            widths[col_letter] = 3.0
        elif key == "qty_prev":
            widths[col_letter] = 11
        elif key == "qty_last":
            widths[col_letter] = 11
        elif key == "qty_delta":
            widths[col_letter] = 12

    set_column_widths(ws, widths)

    # -------------------------------------------------
    # Heights
    # -------------------------------------------------
    set_row_heights(
        ws,
        {
            2: 24,
            3: 18,
            4: 36,
            8: 30,
        },
    )

    hide_grid_and_freeze(ws, "B9")
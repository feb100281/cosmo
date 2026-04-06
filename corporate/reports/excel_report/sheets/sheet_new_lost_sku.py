# # corporate/reports/excel_report/sheets/sheet_new_lost_sku.py
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
# )


# def build_new_lost_sku_sheet(wb, summary_data, subcategory_data):
#     ws = wb.create_sheet("New vs Lost SKU")
#     ws.sheet_properties.outlinePr.summaryBelow = False

#     draw_toc_button(ws, cell="A1", target_sheet="TOC")

#     rows = summary_data.get("rows", [])
#     sub_rows = subcategory_data.get("rows", [])

#     compare_prev_year = summary_data.get("compare_prev_year")
#     compare_last_year = summary_data.get("compare_last_year")
#     is_ytd_comparison = summary_data.get("is_ytd_comparison", False)
#     cutoff_year = summary_data.get("cutoff_year")
#     cutoff_month = summary_data.get("cutoff_month")
#     cutoff_day = summary_data.get("cutoff_day")

#     total_prev = sum(float(r.get("sku_prev") or 0) for r in rows)
#     total_last = sum(float(r.get("sku_last") or 0) for r in rows)
#     total_new = sum(float(r.get("new_sku") or 0) for r in rows)
#     total_lost = sum(float(r.get("lost_sku") or 0) for r in rows)
#     total_net = total_new - total_lost
#     churn = 0 if total_last == 0 else (total_new + total_lost) / total_last

#     period_label = (
#         f"{compare_prev_year} YTD vs {compare_last_year} YTD на {cutoff_day:02d}.{cutoff_month:02d}.{cutoff_year}"
#         if is_ytd_comparison and compare_prev_year and compare_last_year
#         else f"{compare_prev_year} vs {compare_last_year}"
#     )

#     note = (
#         f"Лист показывает динамику ассортиментной матрицы по производителям: "
#         f"какие SKU появились, какие выбыли и как изменился активный ассортимент. "
#         f"Сравнение выполнено за период {period_label}. "
#         f"Итого: new SKU = {int(total_new):,}, lost SKU = {int(total_lost):,}, "
#         f"net = {int(total_net):+,}, churn = {churn:.1%}."
#     ).replace(",", " ")

#     draw_sheet_header(
#         ws,
#         title="Новые и потерянные SKU",
#         subtitle="Динамика ассортиментной матрицы по производителям",
#         note=note,
#         line_to_col=7,
#     )

#     prev_header = f"{compare_prev_year}\nSKU"
#     last_header = f"{compare_last_year}\nSKU"

#     if is_ytd_comparison:
#         prev_header = f"{compare_prev_year}\nSKU YTD"
#         last_header = f"{compare_last_year}\nSKU YTD"

#     headers = [
#         "Производитель / Подкатегория",
#         prev_header,
#         last_header,
#         "New SKU",
#         "Lost SKU",
#         "Net",
#         "Churn",
#     ]

#     header_row = 8
#     data_start_row = 9

#     draw_table_header_with_gaps(
#         ws,
#         row=header_row,
#         headers=headers,
#         wrap=True,
#     )

#     grouped_sub = defaultdict(list)
#     for r in sub_rows:
#         mf = r.get("manufacturer") or "—"
#         grouped_sub[mf].append(r)

#     cur_row = data_start_row

#     def write_row(values, number_formats=None, is_total=False):
#         nonlocal cur_row
#         number_formats = number_formats or {}

#         if is_total:
#             style_total_row(
#                 ws,
#                 row=cur_row,
#                 values=values,
#                 number_formats=number_formats,
#             )
#         else:
#             style_data_row(
#                 ws,
#                 row=cur_row,
#                 values=values,
#                 number_formats=number_formats,
#             )
#         cur_row += 1
#         return cur_row - 1

#     for r in rows:
#         manufacturer = r.get("manufacturer") or "—"
#         sku_prev = float(r.get("sku_prev") or 0)
#         sku_last = float(r.get("sku_last") or 0)
#         new_sku = float(r.get("new_sku") or 0)
#         lost_sku = float(r.get("lost_sku") or 0)
#         net = new_sku - lost_sku
#         churn_row = 0 if sku_last == 0 else (new_sku + lost_sku) / sku_last

#         parent_values = [
#             manufacturer,
#             None if sku_prev == 0 else sku_prev,
#             None if sku_last == 0 else sku_last,
#             None if new_sku == 0 else new_sku,
#             None if lost_sku == 0 else lost_sku,
#             None if net == 0 else net,
#             None if churn_row == 0 else churn_row,
#         ]
#         parent_formats = {
#             2: '#,##0',
#             3: '#,##0',
#             4: '#,##0',
#             5: '#,##0',
#             6: '#,##0;[Red]-#,##0',
#             7: FORMATS["pct"],
#         }

#         parent_row_idx = write_row(parent_values, parent_formats, is_total=False)

#         for col_idx in range(2, 8):
#             ws.cell(row=parent_row_idx, column=col_idx).alignment = ALIGNMENTS["center"]

#         if isinstance(ws.cell(parent_row_idx, 6).value, (int, float)) and ws.cell(parent_row_idx, 6).value < 0:
#             ws.cell(parent_row_idx, 6).fill = FILLS["section"]
#             ws.cell(parent_row_idx, 6).font = FONTS["bold"]

#         if isinstance(ws.cell(parent_row_idx, 7).value, (int, float)) and ws.cell(parent_row_idx, 7).value > 0.5:
#             ws.cell(parent_row_idx, 7).fill = FILLS["section"]
#             ws.cell(parent_row_idx, 7).font = FONTS["bold"]

#         ws.row_dimensions[parent_row_idx].outlineLevel = 0

#         sub_items = grouped_sub.get(manufacturer, [])
#         sub_items = sorted(
#             sub_items,
#             key=lambda x: (
#                 float(x.get("new_sku") or 0) + float(x.get("lost_sku") or 0),
#                 float(x.get("sku_last") or 0),
#                 x.get("subcategory") or "",
#             ),
#             reverse=True,
#         )

#         for sub in sub_items:
#             subcategory = sub.get("subcategory") or "Нет подкатегории"
#             sub_prev = float(sub.get("sku_prev") or 0)
#             sub_last = float(sub.get("sku_last") or 0)
#             sub_new = float(sub.get("new_sku") or 0)
#             sub_lost = float(sub.get("lost_sku") or 0)
#             sub_net = sub_new - sub_lost
#             sub_churn = 0 if sub_last == 0 else (sub_new + sub_lost) / sub_last

#             sub_values = [
#                 f"   {subcategory}",
#                 None if sub_prev == 0 else sub_prev,
#                 None if sub_last == 0 else sub_last,
#                 None if sub_new == 0 else sub_new,
#                 None if sub_lost == 0 else sub_lost,
#                 None if sub_net == 0 else sub_net,
#                 None if sub_churn == 0 else sub_churn,
#             ]
#             sub_formats = {
#                 2: '#,##0',
#                 3: '#,##0',
#                 4: '#,##0',
#                 5: '#,##0',
#                 6: '#,##0;[Red]-#,##0',
#                 7: FORMATS["pct"],
#             }

#             sub_row_idx = write_row(sub_values, sub_formats, is_total=False)

#             for col_idx in range(2, 8):
#                 ws.cell(row=sub_row_idx, column=col_idx).alignment = ALIGNMENTS["center"]

#             if isinstance(ws.cell(sub_row_idx, 6).value, (int, float)) and ws.cell(sub_row_idx, 6).value < 0:
#                 ws.cell(sub_row_idx, 6).fill = FILLS["section"]
#                 ws.cell(sub_row_idx, 6).font = FONTS["bold"]

#             ws.row_dimensions[sub_row_idx].outlineLevel = 1

#     total_values = [
#         "ИТОГО",
#         total_prev,
#         total_last,
#         total_new,
#         total_lost,
#         total_net,
#         churn,
#     ]
#     total_formats = {
#         2: '#,##0',
#         3: '#,##0',
#         4: '#,##0',
#         5: '#,##0',
#         6: '#,##0;[Red]-#,##0',
#         7: FORMATS["pct"],
#     }
#     total_row = write_row(total_values, total_formats, is_total=True)

#     for col_idx in range(2, 8):
#         ws.cell(row=total_row, column=col_idx).alignment = ALIGNMENTS["center"]

#     widths = {
#         "A": 42,
#         "B": 12,
#         "C": 12,
#         "D": 11,
#         "E": 11,
#         "F": 10,
#         "G": 10,
#     }
#     set_column_widths(ws, widths)

#     set_row_heights(
#         ws,
#         {
#             2: 24,
#             3: 18,
#             4: 40,
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
# )


# def _safe_float(v) -> float:
#     try:
#         return float(v or 0)
#     except Exception:
#         return 0.0


# def _get_total_comment(total_net: float, churn: float, total_new: float, total_lost: float) -> str:
#     if total_new == 0 and total_lost == 0:
#         return "Ассортиментная матрица в сравнении с прошлым периодом не изменилась."

#     if total_net > 0:
#         base = f"Матрица расширилась: чистый прирост составил {int(total_net)} SKU."
#     elif total_net < 0:
#         base = f"Матрица сократилась: чистое снижение составило {int(abs(total_net))} SKU."
#     else:
#         base = "Общий размер матрицы остался на уровне прошлого периода."

#     if churn >= 0.70:
#         rotation = "Ротация очень высокая — фактически идет пересборка ассортиментной матрицы."
#     elif churn >= 0.40:
#         rotation = "Ротация высокая — ассортимент заметно обновляется."
#     elif churn >= 0.20:
#         rotation = "Ротация умеренная — матрица обновляется без резких изменений."
#     else:
#         rotation = "Ротация низкая — ассортимент в целом стабилен."

#     return f"{base} {rotation}"


# def _get_row_status_and_comment(sku_prev: float, sku_last: float, new_sku: float, lost_sku: float):
#     net = new_sku - lost_sku
#     churn = 0 if sku_last == 0 else (new_sku + lost_sku) / sku_last

#     if sku_prev == 0 and sku_last > 0:
#         return "Новый производитель", "Поставщик появился в матрице в текущем периоде."
#     if sku_prev > 0 and sku_last == 0:
#         return "Полный выход", "Ассортимент производителя полностью выбыл из матрицы."
#     if new_sku == 0 and lost_sku == 0:
#         return "Стабильно", "Изменений в активной матрице не зафиксировано."

#     if churn >= 0.70:
#         if net > 0:
#             return "Пересборка с ростом", "Матрица сильно обновилась, при этом общий ассортимент вырос."
#         elif net < 0:
#             return "Пересборка со снижением", "Матрица сильно обновилась, при этом общий ассортимент сократился."
#         return "Полная ротация", "Произошла почти полная замена действующей линейки."

#     if net > 0 and lost_sku == 0:
#         return "Рост", "Матрица расширяется за счет новых SKU."
#     if net > 0:
#         return "Рост", "Новые SKU превышают выбытие, ассортимент растет."
#     if net < 0 and new_sku == 0:
#         return "Снижение", "Идет сокращение матрицы без компенсации новыми SKU."
#     if net < 0:
#         return "Снижение", "Выбытие превышает ввод новых SKU, ассортимент сжимается."

#     if churn >= 0.40:
#         return "Высокая ротация", "Размер матрицы сопоставим, но состав SKU заметно меняется."

#     return "Умеренная ротация", "Идут точечные изменения в матрице без существенного изменения объема."


# def build_new_lost_sku_sheet(wb, summary_data, subcategory_data):
#     ws = wb.create_sheet("New vs Lost SKU")
#     ws.sheet_properties.outlinePr.summaryBelow = False

#     draw_toc_button(ws, cell="A1", target_sheet="TOC")

#     rows = summary_data.get("rows", [])
#     sub_rows = subcategory_data.get("rows", [])

#     compare_prev_year = summary_data.get("compare_prev_year")
#     compare_last_year = summary_data.get("compare_last_year")
#     is_ytd_comparison = summary_data.get("is_ytd_comparison", False)
#     cutoff_year = summary_data.get("cutoff_year")
#     cutoff_month = summary_data.get("cutoff_month")
#     cutoff_day = summary_data.get("cutoff_day")

#     total_prev = sum(_safe_float(r.get("sku_prev")) for r in rows)
#     total_last = sum(_safe_float(r.get("sku_last")) for r in rows)
#     total_new = sum(_safe_float(r.get("new_sku")) for r in rows)
#     total_lost = sum(_safe_float(r.get("lost_sku")) for r in rows)
#     total_net = total_new - total_lost
#     churn = 0 if total_last == 0 else (total_new + total_lost) / total_last

#     period_label = (
#         f"{compare_prev_year} YTD vs {compare_last_year} YTD на {cutoff_day:02d}.{cutoff_month:02d}.{cutoff_year}"
#         if is_ytd_comparison and compare_prev_year and compare_last_year
#         else f"{compare_prev_year} vs {compare_last_year}"
#     )

#     total_comment = _get_total_comment(
#         total_net=total_net,
#         churn=churn,
#         total_new=total_new,
#         total_lost=total_lost,
#     )

#     note = (
#         f"Лист показывает изменение активной ассортиментной матрицы по производителям и подкатегориям. "
#         f"Сравнение выполнено за период {period_label}. "
#         f"На конец периода активно {int(total_last):,} SKU против {int(total_prev):,} SKU годом ранее. "
#         f"Добавлено {int(total_new):,} SKU, выбыло {int(total_lost):,} SKU, "
#         f"чистое изменение составило {int(total_net):+,}. "
#         f"Коэффициент обновления матрицы — {churn:.1%}. "
#         f"{total_comment}"
#     ).replace(",", " ")

#     draw_sheet_header(
#         ws,
#         title="Новые и выбывшие SKU",
#         subtitle="Изменение ассортиментной матрицы по производителям",
#         note=note,
#         line_to_col=9,
#     )

#     prev_header = f"{compare_prev_year}\nSKU"
#     last_header = f"{compare_last_year}\nSKU"

#     if is_ytd_comparison:
#         prev_header = f"{compare_prev_year}\nSKU YTD"
#         last_header = f"{compare_last_year}\nSKU YTD"

#     headers = [
#         "Производитель / Подкатегория",
#         "SKU прошлый\nпериод" if not is_ytd_comparison else f"{compare_prev_year}\nSKU YTD",
#         "SKU текущий\nпериод" if not is_ytd_comparison else f"{compare_last_year}\nSKU YTD",
#         "Новые\nSKU",
#         "Выбывшие\nSKU",
#         "Чистое\nизменение",
#         "Коэффициент\nобновления",
#         "Статус",
#         "Комментарий",
#     ]

#     header_row = 8
#     data_start_row = 9

#     draw_table_header_with_gaps(
#         ws,
#         row=header_row,
#         headers=headers,
#         wrap=True,
#     )

#     grouped_sub = defaultdict(list)
#     for r in sub_rows:
#         mf = r.get("manufacturer") or "—"
#         grouped_sub[mf].append(r)

#     cur_row = data_start_row

#     def write_row(values, number_formats=None, is_total=False):
#         nonlocal cur_row
#         number_formats = number_formats or {}

#         if is_total:
#             style_total_row(
#                 ws,
#                 row=cur_row,
#                 values=values,
#                 number_formats=number_formats,
#             )
#         else:
#             style_data_row(
#                 ws,
#                 row=cur_row,
#                 values=values,
#                 number_formats=number_formats,
#             )

#         cur_row += 1
#         return cur_row - 1

#     # Сортировка: сначала самые проблемные / самые интересные
#     rows_sorted = sorted(
#         rows,
#         key=lambda x: (
#             abs(_safe_float(x.get("new_sku")) - _safe_float(x.get("lost_sku"))),
#             _safe_float(x.get("new_sku")) + _safe_float(x.get("lost_sku")),
#             _safe_float(x.get("sku_last")),
#             str(x.get("manufacturer") or ""),
#         ),
#         reverse=True,
#     )

#     for r in rows_sorted:
#         manufacturer = r.get("manufacturer") or "—"
#         sku_prev = _safe_float(r.get("sku_prev"))
#         sku_last = _safe_float(r.get("sku_last"))
#         new_sku = _safe_float(r.get("new_sku"))
#         lost_sku = _safe_float(r.get("lost_sku"))
#         net = new_sku - lost_sku
#         churn_row = 0 if sku_last == 0 else (new_sku + lost_sku) / sku_last
#         status, comment = _get_row_status_and_comment(
#             sku_prev=sku_prev,
#             sku_last=sku_last,
#             new_sku=new_sku,
#             lost_sku=lost_sku,
#         )

#         parent_values = [
#             manufacturer,
#             None if sku_prev == 0 else sku_prev,
#             None if sku_last == 0 else sku_last,
#             None if new_sku == 0 else new_sku,
#             None if lost_sku == 0 else lost_sku,
#             None if net == 0 else net,
#             None if churn_row == 0 else churn_row,
#             status,
#             comment,
#         ]
#         parent_formats = {
#             2: '#,##0',
#             3: '#,##0',
#             4: '#,##0',
#             5: '#,##0',
#             6: '#,##0;[Red]-#,##0',
#             7: FORMATS["pct"],
#         }

#         parent_row_idx = write_row(parent_values, parent_formats, is_total=False)

#         for col_idx in range(2, 8):
#             ws.cell(row=parent_row_idx, column=col_idx).alignment = ALIGNMENTS["center"]
#             ws.cell(row=parent_row_idx, column=8).alignment = ALIGNMENTS["center_wrap"]
#             ws.cell(row=parent_row_idx, column=9).alignment = ALIGNMENTS["left_wrap"]

#         ws.cell(row=parent_row_idx, column=8).font = FONTS["bold"]

#         if isinstance(ws.cell(parent_row_idx, 6).value, (int, float)) and ws.cell(parent_row_idx, 6).value < 0:
#             ws.cell(parent_row_idx, 6).fill = FILLS["section"]
#             ws.cell(parent_row_idx, 6).font = FONTS["bold"]

#         if isinstance(ws.cell(parent_row_idx, 7).value, (int, float)) and ws.cell(parent_row_idx, 7).value >= 0.40:
#             ws.cell(parent_row_idx, 7).fill = FILLS["section"]
#             ws.cell(parent_row_idx, 7).font = FONTS["bold"]

#         if status in {"Полный выход", "Пересборка со снижением", "Снижение"}:
#             ws.cell(parent_row_idx, 8).fill = FILLS["section"]
#             ws.cell(parent_row_idx, 8).font = FONTS["bold"]

#         ws.row_dimensions[parent_row_idx].outlineLevel = 0

#         sub_items = grouped_sub.get(manufacturer, [])
#         sub_items = sorted(
#             sub_items,
#             key=lambda x: (
#                 _safe_float(x.get("new_sku")) + _safe_float(x.get("lost_sku")),
#                 abs(_safe_float(x.get("new_sku")) - _safe_float(x.get("lost_sku"))),
#                 _safe_float(x.get("sku_last")),
#                 x.get("subcategory") or "",
#             ),
#             reverse=True,
#         )

#         for sub in sub_items:
#             subcategory = sub.get("subcategory") or "Нет подкатегории"
#             sub_prev = _safe_float(sub.get("sku_prev"))
#             sub_last = _safe_float(sub.get("sku_last"))
#             sub_new = _safe_float(sub.get("new_sku"))
#             sub_lost = _safe_float(sub.get("lost_sku"))
#             sub_net = sub_new - sub_lost
#             sub_churn = 0 if sub_last == 0 else (sub_new + sub_lost) / sub_last
#             sub_status, sub_comment = _get_row_status_and_comment(
#                 sku_prev=sub_prev,
#                 sku_last=sub_last,
#                 new_sku=sub_new,
#                 lost_sku=sub_lost,
#             )

#             sub_values = [
#                 f"   {subcategory}",
#                 None if sub_prev == 0 else sub_prev,
#                 None if sub_last == 0 else sub_last,
#                 None if sub_new == 0 else sub_new,
#                 None if sub_lost == 0 else sub_lost,
#                 None if sub_net == 0 else sub_net,
#                 None if sub_churn == 0 else sub_churn,
#                 sub_status,
#                 sub_comment,
#             ]
#             sub_formats = {
#                 2: '#,##0',
#                 3: '#,##0',
#                 4: '#,##0',
#                 5: '#,##0',
#                 6: '#,##0;[Red]-#,##0',
#                 7: FORMATS["pct"],
#             }

#             sub_row_idx = write_row(sub_values, sub_formats, is_total=False)

#             for col_idx in range(2, 8):
#                 ws.cell(row=sub_row_idx, column=col_idx).alignment = ALIGNMENTS["center"]

#             if isinstance(ws.cell(sub_row_idx, 6).value, (int, float)) and ws.cell(sub_row_idx, 6).value < 0:
#                 ws.cell(sub_row_idx, 6).fill = FILLS["section"]
#                 ws.cell(sub_row_idx, 6).font = FONTS["bold"]

#             if isinstance(ws.cell(sub_row_idx, 7).value, (int, float)) and ws.cell(sub_row_idx, 7).value >= 0.40:
#                 ws.cell(sub_row_idx, 7).fill = FILLS["section"]
#                 ws.cell(sub_row_idx, 7).font = FONTS["bold"]

#             ws.row_dimensions[sub_row_idx].outlineLevel = 1

#     total_values = [
#         "ИТОГО",
#         total_prev,
#         total_last,
#         total_new,
#         total_lost,
#         total_net,
#         churn,
#         "Общий итог",
#         total_comment,
#     ]
#     total_formats = {
#         2: '#,##0',
#         3: '#,##0',
#         4: '#,##0',
#         5: '#,##0',
#         6: '#,##0;[Red]-#,##0',
#         7: FORMATS["pct"],
#     }

#     total_row = write_row(total_values, total_formats, is_total=True)

#     for col_idx in range(2, 8):
#         ws.cell(row=total_row, column=col_idx).alignment = ALIGNMENTS["center"]

#     ws.cell(row=total_row, column=8).font = FONTS["bold"]

#     widths = {
#         "A": 34,   # Производитель / Подкатегория
#         "B": 12,   # SKU прошлый период
#         "C": 12,   # SKU текущий период
#         "D": 11,   # Новые SKU
#         "E": 12,   # Выбывшие SKU
#         "F": 12,   # Чистое изменение
#         "G": 14,   # Коэффициент обновления
#         "H": 24,   # Статус
#         "I": 48,   # Комментарий
#     }
#     set_column_widths(ws, widths)

#     set_row_heights(
#         ws,
#         {
#             2: 24,
#             3: 18,
#             4: 60,
#             8: 34,
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
# )


# def _safe_float(v) -> float:
#     try:
#         return float(v or 0)
#     except Exception:
#         return 0.0


# # -------------------------------
# # Общий комментарий по листу
# # -------------------------------
# def _get_total_comment(total_net: float, churn: float, total_new: float, total_lost: float) -> str:
#     if total_new == 0 and total_lost == 0:
#         return "Ассортимент не изменился."

#     if total_net > 0:
#         base = f"Ассортимент расширился (+{int(total_net)} SKU)."
#     elif total_net < 0:
#         base = f"Ассортимент сократился (-{int(abs(total_net))} SKU)."
#     else:
#         base = "Размер ассортимента не изменился."

#     if churn >= 0.70:
#         rotation = "Идет фактическая пересборка матрицы."
#     elif churn >= 0.40:
#         rotation = "Высокая ротация ассортимента."
#     elif churn >= 0.20:
#         rotation = "Умеренное обновление ассортимента."
#     else:
#         rotation = "Ассортимент в целом стабилен."

#     return f"{base} {rotation}"


# # -------------------------------
# # Статус + комментарий по строке
# # -------------------------------
# def _get_row_status_and_comment(sku_prev, sku_last, new_sku, lost_sku):
#     net = new_sku - lost_sku
#     churn = 0 if sku_last == 0 else (new_sku + lost_sku) / sku_last

#     if sku_prev == 0 and sku_last > 0:
#         return "Новый производитель", "Поставщик появился в текущем периоде."

#     if sku_prev > 0 and sku_last == 0:
#         return "Полный выход", "Ассортимент полностью выбыл из матрицы."

#     if new_sku == 0 and lost_sku == 0:
#         return "Стабильно", "Изменений в ассортименте нет."

#     if churn >= 0.70:
#         if net > 0:
#             return "Пересборка с ростом", "Матрица сильно обновилась и расширилась."
#         elif net < 0:
#             return "Пересборка со снижением", "Матрица сильно обновилась и сократилась."
#         return "Полная ротация", "Произошла почти полная замена ассортимента."

#     if net > 0:
#         return "Рост", "Ассортимент расширяется."

#     if net < 0:
#         return "Снижение", "Ассортимент сокращается."

#     if churn >= 0.40:
#         return "Высокая ротация", "Состав SKU сильно меняется."

#     return "Умеренная ротация", "Изменения точечные."


# # -------------------------------
# # ОСНОВНАЯ ФУНКЦИЯ
# # -------------------------------
# def build_new_lost_sku_sheet(wb, summary_data, subcategory_data):
#     ws = wb.create_sheet("New vs Lost SKU")
#     ws.sheet_properties.outlinePr.summaryBelow = False

#     draw_toc_button(ws, cell="A1", target_sheet="TOC")

#     rows = summary_data.get("rows", [])
#     sub_rows = subcategory_data.get("rows", [])

#     compare_prev_year = summary_data.get("compare_prev_year")
#     compare_last_year = summary_data.get("compare_last_year")
#     is_ytd_comparison = summary_data.get("is_ytd_comparison", False)
#     cutoff_year = summary_data.get("cutoff_year")
#     cutoff_month = summary_data.get("cutoff_month")
#     cutoff_day = summary_data.get("cutoff_day")

#     total_prev = sum(_safe_float(r.get("sku_prev")) for r in rows)
#     total_last = sum(_safe_float(r.get("sku_last")) for r in rows)
#     total_new = sum(_safe_float(r.get("new_sku")) for r in rows)
#     total_lost = sum(_safe_float(r.get("lost_sku")) for r in rows)
#     total_net = total_new - total_lost
#     churn = 0 if total_last == 0 else (total_new + total_lost) / total_last

#     period_label = (
#         f"{compare_prev_year} YTD vs {compare_last_year} YTD на {cutoff_day:02d}.{cutoff_month:02d}.{cutoff_year}"
#         if is_ytd_comparison
#         else f"{compare_prev_year} vs {compare_last_year}"
#     )

#     total_comment = _get_total_comment(total_net, churn, total_new, total_lost)

#     note = (
#         f"Сравнение: {period_label}. "
#         f"Было {int(total_prev):,} SKU → стало {int(total_last):,}. "
#         f"+{int(total_new):,} новых, -{int(total_lost):,} выбывших. "
#         f"Итого {int(total_net):+,}. Обновление {churn:.1%}. "
#         f"{total_comment}"
#     ).replace(",", " ")

#     draw_sheet_header(
#         ws,
#         title="Новые и выбывшие SKU",
#         subtitle="Динамика ассортиментной матрицы",
#         note=note,
#         line_to_col=9,
#     )

#     headers = [
#         "Производитель / Подкатегория",
#         "SKU прошлый",
#         "SKU текущий",
#         "Новые",
#         "Выбывшие",
#         "Изменение",
#         "Обновление",
#         "Статус",
#         "Комментарий",
#     ]

#     draw_table_header_with_gaps(ws, row=8, headers=headers, wrap=True)

#     grouped_sub = defaultdict(list)
#     for r in sub_rows:
#         grouped_sub[r.get("manufacturer")].append(r)

#     cur_row = 9

#     def write_row(values, formats=None, is_total=False):
#         nonlocal cur_row
#         formats = formats or {}

#         if is_total:
#             style_total_row(ws, row=cur_row, values=values, number_formats=formats)
#         else:
#             style_data_row(ws, row=cur_row, values=values, number_formats=formats)

#         cur_row += 1
#         return cur_row - 1

#     # сортировка — сначала самые проблемные
#     rows_sorted = sorted(
#         rows,
#         key=lambda x: abs(_safe_float(x["new_sku"]) - _safe_float(x["lost_sku"])),
#         reverse=True,
#     )

#     for r in rows_sorted:
#         manufacturer = r["manufacturer"]
#         sku_prev = _safe_float(r["sku_prev"])
#         sku_last = _safe_float(r["sku_last"])
#         new_sku = _safe_float(r["new_sku"])
#         lost_sku = _safe_float(r["lost_sku"])
#         net = new_sku - lost_sku
#         churn_row = 0 if sku_last == 0 else (new_sku + lost_sku) / sku_last

#         status, comment = _get_row_status_and_comment(
#             sku_prev, sku_last, new_sku, lost_sku
#         )

#         row_idx = write_row(
#             [
#                 manufacturer,
#                 sku_prev or None,
#                 sku_last or None,
#                 new_sku or None,
#                 lost_sku or None,
#                 net or None,
#                 churn_row or None,
#                 status,
#                 comment,
#             ],
#             {
#                 2: "#,##0",
#                 3: "#,##0",
#                 4: "#,##0",
#                 5: "#,##0",
#                 6: "#,##0;[Red]-#,##0",
#                 7: FORMATS["pct"],
#             },
#         )

#         # 👉 ВЫДЕЛЕНИЕ ПРОИЗВОДИТЕЛЯ
#         ws.cell(row=row_idx, column=1).fill = FILLS["section"]
#         ws.cell(row=row_idx, column=1).font = FONTS["bold"]

#         for col in range(2, 10):
#             ws.cell(row=row_idx, column=col).font = FONTS["bold"]

#         # 👉 ВЫРАВНИВАНИЕ
#         for col in range(2, 8):
#             ws.cell(row=row_idx, column=col).alignment = ALIGNMENTS["center"]

#         ws.cell(row=row_idx, column=8).alignment = ALIGNMENTS["left_wrap"]
#         ws.cell(row=row_idx, column=9).alignment = ALIGNMENTS["left_wrap"]

#         # 👉 ПОДКАТЕГОРИИ
#         for sub in grouped_sub.get(manufacturer, []):
#             sub_prev = _safe_float(sub["sku_prev"])
#             sub_last = _safe_float(sub["sku_last"])
#             sub_new = _safe_float(sub["new_sku"])
#             sub_lost = _safe_float(sub["lost_sku"])

#             sub_net = sub_new - sub_lost
#             sub_churn = 0 if sub_last == 0 else (sub_new + sub_lost) / sub_last

#             sub_status, sub_comment = _get_row_status_and_comment(
#                 sub_prev, sub_last, sub_new, sub_lost
#             )

#             sub_idx = write_row(
#                 [
#                     f"   {sub['subcategory']}",
#                     sub_prev or None,
#                     sub_last or None,
#                     sub_new or None,
#                     sub_lost or None,
#                     sub_net or None,
#                     sub_churn or None,
#                     sub_status,
#                     sub_comment,
#                 ],
#                 {
#                     2: "#,##0",
#                     3: "#,##0",
#                     4: "#,##0",
#                     5: "#,##0",
#                     6: "#,##0;[Red]-#,##0",
#                     7: FORMATS["pct"],
#                 },
#             )

#             for col in range(2, 8):
#                 ws.cell(row=sub_idx, column=col).alignment = ALIGNMENTS["center"]

#             ws.cell(row=sub_idx, column=8).alignment = ALIGNMENTS["left_wrap"]
#             ws.cell(row=sub_idx, column=9).alignment = ALIGNMENTS["left_wrap"]

#     # ---------------- TOTAL ----------------
#     total_row = write_row(
#         [
#             "ИТОГО",
#             total_prev,
#             total_last,
#             total_new,
#             total_lost,
#             total_net,
#             churn,
#             "",
#             total_comment,
#         ],
#         {
#             2: "#,##0",
#             3: "#,##0",
#             4: "#,##0",
#             5: "#,##0",
#             6: "#,##0;[Red]-#,##0",
#             7: FORMATS["pct"],
#         },
#         is_total=True,
#     )

#     for col in range(2, 8):
#         ws.cell(row=total_row, column=col).alignment = ALIGNMENTS["center"]

#     ws.cell(row=total_row, column=8).alignment = ALIGNMENTS["left_wrap"]
#     ws.cell(row=total_row, column=9).alignment = ALIGNMENTS["left_wrap"]

#     # ---------------- ШИРИНЫ ----------------
#     set_column_widths(
#         ws,
#         {
#             "A": 36,
#             "B": 12,
#             "C": 12,
#             "D": 11,
#             "E": 11,
#             "F": 12,
#             "G": 13,
#             "H": 22,
#             "I": 48,
#         },
#     )

#     set_row_heights(
#         ws,
#         {
#             2: 24,
#             3: 18,
#             4: 70,
#             8: 36,
#         },
#     )

#     hide_grid_and_freeze(ws, "B9")



# corporate/reports/excel_report/sheets/sheet_new_lost_sku.py

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


def _get_total_comment(total_net: float, churn: float, total_new: float, total_lost: float) -> str:
    if total_new == 0 and total_lost == 0:
        return "Ассортимент не изменился."

    if total_net > 0:
        base = f"Ассортимент расширился (+{int(total_net)} SKU)."
    elif total_net < 0:
        base = f"Ассортимент сократился (-{int(abs(total_net))} SKU)."
    else:
        base = "Размер ассортимента не изменился."

    if churn >= 0.70:
        rotation = "Идет фактическая пересборка матрицы."
    elif churn >= 0.40:
        rotation = "Высокая ротация ассортимента."
    elif churn >= 0.20:
        rotation = "Умеренное обновление ассортимента."
    else:
        rotation = "Ассортимент в целом стабилен."

    return f"{base} {rotation}"


def _get_row_status_and_comment(sku_prev, sku_last, new_sku, lost_sku):
    net = new_sku - lost_sku
    churn = 0 if sku_last == 0 else (new_sku + lost_sku) / sku_last

    if sku_prev == 0 and sku_last > 0:
        return "Новый поставщик", "Поставщик появился в текущем периоде."

    if sku_prev > 0 and sku_last == 0:
        return "Полный выход", "Ассортимент полностью выбыл из матрицы."

    if new_sku == 0 and lost_sku == 0:
        return "Стабильно", "Изменений в ассортименте нет."

    if churn >= 0.70:
        if net > 0:
            return "Пересборка с ростом", "Матрица сильно обновилась и расширилась."
        elif net < 0:
            return "Пересборка со снижением", "Матрица сильно обновилась и сократилась."
        return "Полная ротация", "Произошла почти полная замена ассортимента."

    if net > 0:
        return "Рост", "Ассортимент расширяется."

    if net < 0:
        return "Снижение", "Ассортимент сокращается."

    if churn >= 0.40:
        return "Высокая ротация", "Состав SKU заметно меняется."

    return "Умеренная ротация", "Изменения носят точечный характер."


def build_new_lost_sku_sheet(wb, summary_data, subcategory_data):
    ws = wb.create_sheet("New vs Lost SKU")
    ws.sheet_properties.outlinePr.summaryBelow = False
    ws.sheet_properties.outlinePr.applyStyles = True

    draw_toc_button(ws, cell="A1", target_sheet="TOC")

    rows = summary_data.get("rows", [])
    sub_rows = subcategory_data.get("rows", [])

    compare_prev_year = summary_data.get("compare_prev_year")
    compare_last_year = summary_data.get("compare_last_year")
    is_ytd_comparison = summary_data.get("is_ytd_comparison", False)
    cutoff_year = summary_data.get("cutoff_year")
    cutoff_month = summary_data.get("cutoff_month")
    cutoff_day = summary_data.get("cutoff_day")

    total_prev = sum(_safe_float(r.get("sku_prev")) for r in rows)
    total_last = sum(_safe_float(r.get("sku_last")) for r in rows)
    total_new = sum(_safe_float(r.get("new_sku")) for r in rows)
    total_lost = sum(_safe_float(r.get("lost_sku")) for r in rows)
    total_net = total_new - total_lost
    churn = 0 if total_last == 0 else (total_new + total_lost) / total_last

    if is_ytd_comparison and compare_prev_year and compare_last_year:
        period_label = (
            f"{compare_prev_year} YTD vs {compare_last_year} YTD "
            f"на {cutoff_day:02d}.{cutoff_month:02d}.{cutoff_year}"
        )
        prev_header = f"{compare_prev_year}\nSKU YTD"
        last_header = f"{compare_last_year}\nSKU YTD"
    else:
        period_label = f"{compare_prev_year} vs {compare_last_year}"
        prev_header = f"{compare_prev_year}\nSKU"
        last_header = f"{compare_last_year}\nSKU"

    total_comment = _get_total_comment(total_net, churn, total_new, total_lost)

    note = (
        f"Сравнение: {period_label}. "
        f"Было {int(total_prev):,} SKU → стало {int(total_last):,}. "
        f"+{int(total_new):,} новых, -{int(total_lost):,} выбывших. "
        f"Итого {int(total_net):+,}. Коэффициент обновления {churn:.1%}. "
        f"{total_comment}"
    ).replace(",", " ")

    draw_sheet_header(
        ws,
        title="Новые и выбывшие SKU",
        subtitle="Динамика ассортиментной матрицы по производителям",
        note=note,
        line_to_col=9,
    )

    headers = [
        "Производитель / Подкатегория",
        prev_header,
        last_header,
        "Новые\nSKU",
        "Выбывшие\nSKU",
        "Чистое\nизменение",
        "Коэффициент\nобновления",
        "Статус",
        "Комментарий",
    ]

    header_row = 8
    data_start_row = 9

    draw_table_header_with_gaps(
        ws,
        row=header_row,
        headers=headers,
        wrap=True,
    )

    grouped_sub = defaultdict(list)
    for r in sub_rows:
        mf = r.get("manufacturer") or "—"
        grouped_sub[mf].append(r)

    cur_row = data_start_row

    def write_row(values, formats=None, is_total=False):
        nonlocal cur_row
        formats = formats or {}

        if is_total:
            style_total_row(ws, row=cur_row, values=values, number_formats=formats)
        else:
            style_data_row(ws, row=cur_row, values=values, number_formats=formats)

        cur_row += 1
        return cur_row - 1

    rows_sorted = sorted(
        rows,
        key=lambda x: (
            abs(_safe_float(x.get("new_sku")) - _safe_float(x.get("lost_sku"))),
            _safe_float(x.get("new_sku")) + _safe_float(x.get("lost_sku")),
            _safe_float(x.get("sku_last")),
            str(x.get("manufacturer") or ""),
        ),
        reverse=True,
    )

    for r in rows_sorted:
        manufacturer = r.get("manufacturer") or "—"
        sku_prev = _safe_float(r.get("sku_prev"))
        sku_last = _safe_float(r.get("sku_last"))
        new_sku = _safe_float(r.get("new_sku"))
        lost_sku = _safe_float(r.get("lost_sku"))
        net = new_sku - lost_sku
        churn_row = 0 if sku_last == 0 else (new_sku + lost_sku) / sku_last

        status, comment = _get_row_status_and_comment(
            sku_prev, sku_last, new_sku, lost_sku
        )

        parent_values = [
            manufacturer,
            None if sku_prev == 0 else sku_prev,
            None if sku_last == 0 else sku_last,
            None if new_sku == 0 else new_sku,
            None if lost_sku == 0 else lost_sku,
            None if net == 0 else net,
            None if churn_row == 0 else churn_row,
            status,
            comment,
        ]
        parent_formats = {
            2: "#,##0",
            3: "#,##0",
            4: "#,##0",
            5: "#,##0",
            6: "#,##0;[Red]-#,##0",
            7: FORMATS["pct"],
        }

        parent_row_idx = write_row(parent_values, parent_formats, is_total=False)

        # Первый уровень = производитель
        ws.row_dimensions[parent_row_idx].outlineLevel = 0

        # Выделяем строку производителя
        ws.cell(row=parent_row_idx, column=1).fill = FILLS["section"]
        ws.cell(row=parent_row_idx, column=1).font = FONTS["bold"]

        for col_idx in range(2, 10):
            ws.cell(row=parent_row_idx, column=col_idx).font = FONTS["bold"]

        for col_idx in range(2, 8):
            ws.cell(row=parent_row_idx, column=col_idx).alignment = ALIGNMENTS["center"]

        ws.cell(row=parent_row_idx, column=8).alignment = ALIGNMENTS["left_wrap"]
        ws.cell(row=parent_row_idx, column=9).alignment = ALIGNMENTS["left_wrap"]

        if isinstance(ws.cell(parent_row_idx, 6).value, (int, float)) and ws.cell(parent_row_idx, 6).value < 0:
            ws.cell(parent_row_idx, 6).fill = FILLS["section"]
            ws.cell(parent_row_idx, 6).font = FONTS["bold"]

        if isinstance(ws.cell(parent_row_idx, 7).value, (int, float)) and ws.cell(parent_row_idx, 7).value >= 0.40:
            ws.cell(parent_row_idx, 7).fill = FILLS["section"]
            ws.cell(parent_row_idx, 7).font = FONTS["bold"]

        if status in {"Полный выход", "Пересборка со снижением", "Снижение"}:
            ws.cell(parent_row_idx, 8).fill = FILLS["section"]
            ws.cell(parent_row_idx, 8).font = FONTS["bold"]

        sub_items = grouped_sub.get(manufacturer, [])
        sub_items = sorted(
            sub_items,
            key=lambda x: (
                _safe_float(x.get("new_sku")) + _safe_float(x.get("lost_sku")),
                abs(_safe_float(x.get("new_sku")) - _safe_float(x.get("lost_sku"))),
                _safe_float(x.get("sku_last")),
                x.get("subcategory") or "",
            ),
            reverse=True,
        )

        for sub in sub_items:
            subcategory = sub.get("subcategory") or "Нет подкатегории"
            sub_prev = _safe_float(sub.get("sku_prev"))
            sub_last = _safe_float(sub.get("sku_last"))
            sub_new = _safe_float(sub.get("new_sku"))
            sub_lost = _safe_float(sub.get("lost_sku"))
            sub_net = sub_new - sub_lost
            sub_churn = 0 if sub_last == 0 else (sub_new + sub_lost) / sub_last

            sub_status, sub_comment = _get_row_status_and_comment(
                sub_prev, sub_last, sub_new, sub_lost
            )

            sub_values = [
                f"   {subcategory}",
                None if sub_prev == 0 else sub_prev,
                None if sub_last == 0 else sub_last,
                None if sub_new == 0 else sub_new,
                None if sub_lost == 0 else sub_lost,
                None if sub_net == 0 else sub_net,
                None if sub_churn == 0 else sub_churn,
                sub_status,
                sub_comment,
            ]
            sub_formats = {
                2: "#,##0",
                3: "#,##0",
                4: "#,##0",
                5: "#,##0",
                6: "#,##0;[Red]-#,##0",
                7: FORMATS["pct"],
            }

            sub_row_idx = write_row(sub_values, sub_formats, is_total=False)

            # Второй уровень = подкатегория
            ws.row_dimensions[sub_row_idx].outlineLevel = 1

            for col_idx in range(2, 8):
                ws.cell(row=sub_row_idx, column=col_idx).alignment = ALIGNMENTS["center"]

            ws.cell(row=sub_row_idx, column=8).alignment = ALIGNMENTS["left_wrap"]
            ws.cell(row=sub_row_idx, column=9).alignment = ALIGNMENTS["left_wrap"]

            if isinstance(ws.cell(sub_row_idx, 6).value, (int, float)) and ws.cell(sub_row_idx, 6).value < 0:
                ws.cell(sub_row_idx, 6).fill = FILLS["section"]
                ws.cell(sub_row_idx, 6).font = FONTS["bold"]

            if isinstance(ws.cell(sub_row_idx, 7).value, (int, float)) and ws.cell(sub_row_idx, 7).value >= 0.40:
                ws.cell(sub_row_idx, 7).fill = FILLS["section"]
                ws.cell(sub_row_idx, 7).font = FONTS["bold"]

    total_values = [
        "ИТОГО",
        total_prev,
        total_last,
        total_new,
        total_lost,
        total_net,
        churn,
        "",
        total_comment,
    ]
    total_formats = {
        2: "#,##0",
        3: "#,##0",
        4: "#,##0",
        5: "#,##0",
        6: "#,##0;[Red]-#,##0",
        7: FORMATS["pct"],
    }

    total_row = write_row(total_values, total_formats, is_total=True)

    for col_idx in range(2, 8):
        ws.cell(row=total_row, column=col_idx).alignment = ALIGNMENTS["center"]

    ws.cell(row=total_row, column=8).alignment = ALIGNMENTS["left_wrap"]
    ws.cell(row=total_row, column=9).alignment = ALIGNMENTS["left_wrap"]

    set_column_widths(
        ws,
        {
            "A": 36,
            "B": 12,
            "C": 12,
            "D": 11,
            "E": 11,
            "F": 12,
            "G": 14,
            "H": 24,
            "I": 52,
        },
    )

    set_row_heights(
        ws,
        {
            2: 24,
            3: 18,
            4: 72,
            8: 38,
        },
    )

    hide_grid_and_freeze(ws, "B9")
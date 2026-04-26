# # orders/reports/sheets/stuck_orders_sheet.py
# from datetime import datetime
# from openpyxl.styles import Font, PatternFill, Alignment
# from ..styles.theme import COLORS, BORDERS


# class StuckOrdersSheet:
#     """Лист с зависшими заказами (aging)"""

#     def __init__(self, workbook, sheet_number):
#         self.wb = workbook
#         self.sheet_number = sheet_number
#         self.ws = workbook.create_sheet(f"{sheet_number}. Зависшие заказы")
        
#         # Цвета для возрастных категорий
#         self.COLORS_AGE = {
#             '0-7': '4CAF50',
#             '8-30': 'FFC107',
#             '31-90': 'FF9800',
#             '90+': 'F44336',
#         }

#     def _format_currency(self, value):
#         if not value:
#             return "0 ₽"
#         return f"{int(round(value)):,} ₽".replace(",", " ")

#     def _get_fill_by_age(self, age_days):
#         if age_days <= 7:
#             return PatternFill("solid", fgColor="C8E6C9")
#         elif age_days <= 30:
#             return PatternFill("solid", fgColor="FFF9C4")
#         elif age_days <= 90:
#             return PatternFill("solid", fgColor="FFE0B2")
#         else:
#             return PatternFill("solid", fgColor="FFCDD2")

#     def _draw_toc_button(self):
#         from ..styles.helpers import draw_toc_button
#         draw_toc_button(self.ws, cell="B1", text="← Оглавление", target_sheet="TOC")

#     def build(self, stuck_data):
#         """Построение листа"""
#         row = 1
        
#         self.ws.row_dimensions[1].height = 20
#         self.ws.row_dimensions[2].height = 8
        
#         self._draw_toc_button()
        
#         # Заголовок
#         row = self._draw_header(
#             row=3,
#             title="ЗАВИСШИЕ ЗАКАЗЫ (AGING)",
#             subtitle=f"Заказы без оплаты и без отгрузки, не отменены | Всего: {stuck_data['summary']['total_count']} заказов на {self._format_currency(stuck_data['summary']['total_amount'])}",
#             date_text=f"Сформировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
#         )
        
#         row += 2
        
#         # Сводная таблица
#         row = self._draw_summary_table(row, stuck_data['summary'])
#         row += 2
        
#         # Детальные таблицы по категориям
#         categories = [
#             ('0-7', 'до 7 дней', '🟢'),
#             ('8-30', '8-30 дней', '🟡'),
#             ('31-90', '31-90 дней', '🟠'),
#             ('90+', 'более 90 дней', '🔴')
#         ]
        
#         for cat_code, cat_name, emoji in categories:
#             orders = stuck_data.get(cat_code, [])
#             if orders:
#                 row = self._draw_category_section(row, f"{emoji} {cat_name}", orders, cat_code)
#                 row += 1
        
#         self._set_column_widths()
#         self.ws.freeze_panes = 'A15'
#         self.ws.sheet_view.showGridLines = False

#     def _draw_header(self, row, title, subtitle, date_text):
#         self.ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=9)
#         title_cell = self.ws.cell(row=row, column=2, value=title)
#         title_cell.font = Font(name="Roboto", size=14, bold=True, color="1F4E79")
#         title_cell.alignment = Alignment(horizontal="center")
        
#         row += 1
#         self.ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=9)
#         subtitle_cell = self.ws.cell(row=row, column=2, value=subtitle)
#         subtitle_cell.font = Font(name="Roboto", size=10, color="666666")
#         subtitle_cell.alignment = Alignment(horizontal="center")
        
#         row += 1
#         date_cell = self.ws.cell(row=row, column=9, value=date_text)
#         date_cell.font = Font(name="Roboto", size=8, color="999999")
#         date_cell.alignment = Alignment(horizontal="right")
        
#         return row

#     def _draw_summary_table(self, row, summary):
#         title_cell = self.ws.cell(row=row, column=2, value="📊 СВОДКА ПО ВОЗРАСТНЫМ ГРУППАМ")
#         title_cell.font = Font(name="Roboto", size=12, bold=True, color="1F4E79")
#         row += 1
        
#         headers = ["Возраст заказа", "Кол-во заказов", "Сумма", "% от общей суммы"]
        
#         for col_idx, header in enumerate(headers, start=2):
#             cell = self.ws.cell(row=row, column=col_idx, value=header)
#             cell.font = Font(name="Roboto", size=10, bold=True, color="FFFFFF")
#             cell.fill = PatternFill("solid", fgColor="1F4E79")
#             cell.alignment = Alignment(horizontal="center")
#             cell.border = BORDERS["thin"]
#         row += 1
        
#         categories = [('0-7', 'до 7 дней'), ('8-30', '8-30 дней'), ('31-90', '31-90 дней'), ('90+', 'более 90 дней')]
#         total_amount = summary['total_amount']
        
#         for cat_code, cat_label in categories:
#             count = summary[cat_code]['count']
#             amount = summary[cat_code]['amount']
#             percent = (amount / total_amount * 100) if total_amount > 0 else 0
            
#             values = [cat_label, count, self._format_currency(amount), f"{percent:.1f}%"]
            
#             for col_idx, value in enumerate(values, start=2):
#                 cell = self.ws.cell(row=row, column=col_idx, value=value)
#                 cell.border = BORDERS["thin"]
#                 cell.font = Font(name="Roboto", size=9)
#                 cell.alignment = Alignment(horizontal="right" if col_idx > 2 else "left")
                
#                 if col_idx == 2:
#                     cell.fill = PatternFill("solid", fgColor=self.COLORS_AGE.get(cat_code, "FFFFFF"))
#                     cell.font = Font(name="Roboto", size=9, bold=True)
            
#             row += 1
        
#         # Итоговая строка
#         total_cell = self.ws.cell(row=row, column=2, value="ИТОГО")
#         total_cell.font = Font(name="Roboto", size=10, bold=True)
#         total_cell.fill = PatternFill("solid", fgColor="E0E0E0")
        
#         count_cell = self.ws.cell(row=row, column=3, value=summary['total_count'])
#         count_cell.font = Font(name="Roboto", size=10, bold=True)
#         count_cell.fill = PatternFill("solid", fgColor="E0E0E0")
#         count_cell.alignment = Alignment(horizontal="center")
        
#         amount_cell = self.ws.cell(row=row, column=4, value=self._format_currency(summary['total_amount']))
#         amount_cell.font = Font(name="Roboto", size=10, bold=True)
#         amount_cell.fill = PatternFill("solid", fgColor="E0E0E0")
#         amount_cell.alignment = Alignment(horizontal="right")
        
#         percent_cell = self.ws.cell(row=row, column=5, value="100%")
#         percent_cell.font = Font(name="Roboto", size=10, bold=True)
#         percent_cell.fill = PatternFill("solid", fgColor="E0E0E0")
#         percent_cell.alignment = Alignment(horizontal="center")
        
#         return row

#     def _draw_category_section(self, row, title, orders, cat_code):
#         title_cell = self.ws.cell(row=row, column=2, value=title)
#         title_cell.font = Font(name="Roboto", size=12, bold=True, color="1F4E79")
#         row += 1
        
#         headers = ["ЗАКАЗ", "ДАТА СОЗДАНИЯ", "ДНЕЙ В СТАТУСЕ", "СТАТУС", "КЛИЕНТ", "МЕНЕДЖЕР", "МАГАЗИН", "СУММА"]
        
#         for col_idx, header in enumerate(headers, start=2):
#             cell = self.ws.cell(row=row, column=col_idx, value=header)
#             cell.font = Font(name="Roboto", size=9, bold=True, color="FFFFFF")
#             cell.fill = PatternFill("solid", fgColor="1F4E79")
#             cell.alignment = Alignment(horizontal="center", wrap_text=True)
#             cell.border = BORDERS["thin"]
#         self.ws.row_dimensions[row].height = 35
#         row += 1
        
#         for order in orders:
#             age_days = order.get('age_days', 0)
#             row_fill = self._get_fill_by_age(age_days)
            
#             values = [
#                 order.get('order_name', ''),
#                 order.get('date_from').strftime('%Y-%m-%d') if order.get('date_from') else '',
#                 f"{age_days} дн.",
#                 order.get('status', ''),
#                 (order.get('client') or '')[:40],
#                 order.get('manager', ''),
#                 (order.get('store') or '')[:30],
#                 self._format_currency(order.get('amount', 0)),
#             ]
            
#             for col_idx, value in enumerate(values, start=2):
#                 cell = self.ws.cell(row=row, column=col_idx, value=value)
#                 cell.fill = row_fill
#                 cell.border = BORDERS["thin"]
#                 cell.font = Font(name="Roboto", size=9)
                
#                 if col_idx == 2 or col_idx == 5 or col_idx == 6 or col_idx == 7:
#                     cell.alignment = Alignment(horizontal="left")
#                 elif col_idx == 3 or col_idx == 4:
#                     cell.alignment = Alignment(horizontal="center")
#                 elif col_idx == 8:
#                     cell.alignment = Alignment(horizontal="right")
#                     if age_days > 90:
#                         cell.font = Font(name="Roboto", size=9, bold=True, color="F44336")
            
#             row += 1
        
#         return row

#     def _set_column_widths(self):
#         col_widths = {
#             "B": 28, "C": 14, "D": 14, "E": 20, "F": 35, "G": 20, "H": 25, "I": 18
#         }
#         for col, width in col_widths.items():
#             self.ws.column_dimensions[col].width = width
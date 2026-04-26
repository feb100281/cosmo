# # orders/reports/sheets/order_fulfillment_sheet.py
# from datetime import datetime
# from openpyxl.styles import Font, PatternFill, Alignment
# from ..styles.theme import COLORS, BORDERS


# class OrderFulfillmentSheet:
#     """Лист с анализом процента выполнения заказов"""

#     def __init__(self, workbook, sheet_number):
#         self.wb = workbook
#         self.sheet_number = sheet_number
#         self.ws = workbook.create_sheet(f"{sheet_number}. % выполнения заказов")

#     def _format_currency(self, value):
#         if not value:
#             return "0 ₽"
#         return f"{int(round(value)):,} ₽".replace(",", " ")

#     def _format_percent(self, value):
#         return f"{value:.1f}%" if value else "0%"

#     def _get_fulfillment_color(self, pct):
#         if pct < 50:
#             return "F44336"
#         elif pct < 80:
#             return "FF9800"
#         elif pct < 100:
#             return "FFC107"
#         return "4CAF50"

#     def _draw_toc_button(self):
#         from ..styles.helpers import draw_toc_button
#         draw_toc_button(self.ws, cell="B1", text="← Оглавление", target_sheet="TOC")

#     def build(self, fulfillment_by_manager, top_low_orders, summary):
#         row = 1
        
#         self.ws.row_dimensions[1].height = 20
        
#         self._draw_toc_button()
        
#         row = self._draw_header(
#             row=3,
#             title="% ВЫПОЛНЕНИЯ ЗАКАЗОВ",
#             subtitle=f"Анализ: сколько отгружено от суммы заказа | Общая недогрузка: {self._format_currency(summary['total_lost'])} ({self._format_percent(100 - summary['avg_fulfillment'])})",
#             date_text=f"Сформировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
#         )
        
#         row += 2
        
#         # Сводная статистика
#         row = self._draw_summary(row, summary)
#         row += 2
        
#         # По менеджерам
#         row = self._draw_manager_fulfillment(row, fulfillment_by_manager)
#         row += 2
        
#         # ТОП худших заказов
#         row = self._draw_top_low_orders(row, top_low_orders[:20])
        
#         self._set_column_widths()
#         self.ws.freeze_panes = 'A15'
#         self.ws.sheet_view.showGridLines = False

#     def _draw_header(self, row, title, subtitle, date_text):
#         self.ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)
#         title_cell = self.ws.cell(row=row, column=2, value=title)
#         title_cell.font = Font(name="Roboto", size=14, bold=True, color="1F4E79")
#         title_cell.alignment = Alignment(horizontal="center")
        
#         row += 1
#         self.ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)
#         subtitle_cell = self.ws.cell(row=row, column=2, value=subtitle)
#         subtitle_cell.font = Font(name="Roboto", size=10, color="666666")
#         subtitle_cell.alignment = Alignment(horizontal="center")
        
#         row += 1
#         date_cell = self.ws.cell(row=row, column=8, value=date_text)
#         date_cell.font = Font(name="Roboto", size=8, color="999999")
#         date_cell.alignment = Alignment(horizontal="right")
        
#         return row

#     def _draw_summary(self, row, summary):
#         title_cell = self.ws.cell(row=row, column=2, value="📊 СВОДНАЯ СТАТИСТИКА")
#         title_cell.font = Font(name="Roboto", size=12, bold=True, color="1F4E79")
#         row += 1
        
#         metrics = [
#             ("Всего заказов с отгрузкой", f"{summary['total_orders']:,}".replace(",", " "), ""),
#             ("Общая сумма заказов", self._format_currency(summary['total_amount']), ""),
#             ("Отгружено всего", self._format_currency(summary['total_shipped']), ""),
#             ("НЕДОГРУЗКА", self._format_currency(summary['total_lost']), "F44336"),
#             ("Средний % выполнения", self._format_percent(summary['avg_fulfillment']), ""),
#         ]
        
#         col = 2
#         for idx, (label, value, color) in enumerate(metrics):
#             if idx > 0 and idx % 3 == 0:
#                 row += 3
#                 col = 2
            
#             card_cell = self.ws.cell(row=row, column=col, value=label)
#             card_cell.font = Font(name="Roboto", size=9, bold=True, color="666666")
#             card_cell.fill = PatternFill("solid", fgColor="F5F5F5")
#             card_cell.border = BORDERS["thin"]
            
#             value_cell = self.ws.cell(row=row + 1, column=col, value=value)
#             value_cell.font = Font(name="Roboto", size=14, bold=True, color=color or "1F4E79")
#             value_cell.fill = PatternFill("solid", fgColor="F5F5F5")
#             value_cell.border = BORDERS["thin"]
#             value_cell.alignment = Alignment(horizontal="left")
            
#             self.ws.column_dimensions[self._get_column_letter(col)].width = 22
#             col += 1
        
#         return row + 3

#     def _draw_manager_fulfillment(self, row, fulfillment_by_manager):
#         row += 1
#         title_cell = self.ws.cell(row=row, column=2, value="👥 % ВЫПОЛНЕНИЯ ПО МЕНЕДЖЕРАМ")
#         title_cell.font = Font(name="Roboto", size=12, bold=True, color="1F4E79")
#         row += 1
        
#         headers = ["МЕНЕДЖЕР", "ЗАКАЗОВ", "СУММА ЗАКАЗОВ", "ОТГРУЖЕНО", "НЕДОГРУЗКА", "% ВЫПОЛНЕНИЯ"]
        
#         for col_idx, header in enumerate(headers, start=2):
#             cell = self.ws.cell(row=row, column=col_idx, value=header)
#             cell.font = Font(name="Roboto", size=10, bold=True, color="FFFFFF")
#             cell.fill = PatternFill("solid", fgColor="1F4E79")
#             cell.alignment = Alignment(horizontal="center")
#             cell.border = BORDERS["thin"]
#         row += 1
        
#         for mgr in fulfillment_by_manager[:15]:
#             pct = mgr['avg_fulfillment']
#             pct_color = self._get_fulfillment_color(pct)
            
#             values = [
#                 mgr['manager'],
#                 f"{mgr['orders_count']:,}".replace(",", " "),
#                 self._format_currency(mgr['total_amount']),
#                 self._format_currency(mgr['total_shipped']),
#                 self._format_currency(mgr['lost_revenue']),
#                 self._format_percent(pct)
#             ]
            
#             for col_idx, value in enumerate(values, start=2):
#                 cell = self.ws.cell(row=row, column=col_idx, value=value)
#                 cell.border = BORDERS["thin"]
#                 cell.font = Font(name="Roboto", size=9)
#                 cell.alignment = Alignment(horizontal="left" if col_idx == 2 else "right")
                
#                 if col_idx == 6:
#                     cell.font = Font(name="Roboto", size=9, bold=True, color=pct_color)
            
#             row += 1
        
#         return row

#     def _draw_top_low_orders(self, row, top_low_orders):
#         row += 1
#         title_cell = self.ws.cell(row=row, column=2, value="⚠️ ТОП-20 ЗАКАЗОВ С НИЗКИМ % ВЫПОЛНЕНИЯ")
#         title_cell.font = Font(name="Roboto", size=12, bold=True, color="F44336")
#         row += 1
        
#         headers = ["ЗАКАЗ", "КЛИЕНТ", "МЕНЕДЖЕР", "СУММА", "ОТГРУЖЕНО", "НЕДОГРУЗКА", "% ВЫП."]
        
#         for col_idx, header in enumerate(headers, start=2):
#             cell = self.ws.cell(row=row, column=col_idx, value=header)
#             cell.font = Font(name="Roboto", size=10, bold=True, color="FFFFFF")
#             cell.fill = PatternFill("solid", fgColor="F44336")
#             cell.alignment = Alignment(horizontal="center")
#             cell.border = BORDERS["thin"]
#         row += 1
        
#         for order in top_low_orders[:20]:
#             pct = order['fulfillment_pct']
#             pct_color = self._get_fulfillment_color(pct)
            
#             values = [
#                 order.get('order_name', ''),
#                 (order.get('client') or '')[:40],
#                 order.get('manager', ''),
#                 self._format_currency(order.get('amount', 0)),
#                 self._format_currency(order.get('shipped', 0)),
#                 self._format_currency(order.get('lost', 0)),
#                 self._format_percent(pct)
#             ]
            
#             for col_idx, value in enumerate(values, start=2):
#                 cell = self.ws.cell(row=row, column=col_idx, value=value)
#                 cell.border = BORDERS["thin"]
#                 cell.font = Font(name="Roboto", size=9)
#                 cell.alignment = Alignment(horizontal="left" if col_idx in [2, 3, 4] else "right")
                
#                 if col_idx == 7:
#                     cell.font = Font(name="Roboto", size=9, bold=True, color=pct_color)
            
#             row += 1
        
#         return row

#     def _set_column_widths(self):
#         col_widths = {"B": 28, "C": 30, "D": 20, "E": 18, "F": 18, "G": 18, "H": 12}
#         for col, width in col_widths.items():
#             self.ws.column_dimensions[col].width = width

#     def _get_column_letter(self, col_num):
#         return chr(64 + col_num)
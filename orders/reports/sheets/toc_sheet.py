# # orders/reports/sheets/toc_sheet.py
# from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
# from datetime import datetime
# from .base_sheet import BaseSheet
# from styles.theme import FILLS, FONTS, BORDERS, ALIGNMENTS, COLORS
# from ..queries.toc_queries import TOCQueries


# class TOCSheet(BaseSheet):
#     def __init__(self, workbook):
#         super().__init__(workbook, "TOC")
#         # Удаляем дефолтный лист, если он есть
#         if "Sheet" in self.wb.sheetnames:
#             self.wb.remove(self.wb["Sheet"])
    
#     def build(self, sheets_info, request=None, filters=None):

        
#         # Получаем метрики по статусам
#         metrics_by_status = TOCQueries.get_metrics_by_status(request=request, filters=filters)
        
#         # Получаем несоответствия
#         inconsistencies = TOCQueries.get_inconsistencies(request=request, filters=filters)
        
#         # -------------------------------------------------
#         # ШАПКА - компактно (сдвинута на колонку B)
#         # -------------------------------------------------
#         row = 1
#         self.ws.cell(row=row, column=2, value="ОТЧЕТ ПО ЗАКАЗАМ")
#         self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=16, bold=True, color=COLORS["dark_green"])
#         self.ws.cell(row=row, column=2).alignment = ALIGNMENTS["left"]
        
#         row += 1
#         self.ws.cell(row=row, column=2, value="Аналитика и детализация заказов")
#         self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=10, color=COLORS["text_gray"])
#         self.ws.cell(row=row, column=2).alignment = ALIGNMENTS["left"]
        
#         row += 1
#         generated_text = f"Сформировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
#         self.ws.cell(row=row, column=2, value=generated_text)
#         self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])
        
#         row += 2
        
#         # -------------------------------------------------
#         # БЛОК 1: НА СОГЛАСОВАНИИ
#         # -------------------------------------------------
#         # Заголовок
#         self.ws.cell(row=row, column=2, value="НА СОГЛАСОВАНИИ")
#         self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=11, bold=True, color=COLORS["dark_green"])
#         row += 1
        
#         # Данные для таблицы
#         stats_agreement = [
#             ("Всего заказов", metrics_by_status['agreement']['count']),
#             ("Общая сумма", f"{metrics_by_status['agreement']['total_amount']:,.0f} ₽"),
#             ("Средний чек", f"{metrics_by_status['agreement']['avg_check']:,.0f} ₽"),
#         ]
        
#         start_col = 2
        
#         # Строка с названиями
#         for col_offset, (label, _) in enumerate(stats_agreement):
#             label_cell = self.ws.cell(row=row, column=start_col + col_offset, value=label)
#             label_cell.font = Font(name="Roboto", size=9, bold=True)
#             label_cell.alignment = ALIGNMENTS["center"]
#             label_cell.border = BORDERS["thin"]
#             label_cell.fill = PatternFill(start_color=COLORS["light_green"], end_color=COLORS["light_green"], fill_type="solid")
        
#         # Строка со значениями
#         for col_offset, (_, value) in enumerate(stats_agreement):
#             value_cell = self.ws.cell(row=row + 1, column=start_col + col_offset, value=value)
#             value_cell.font = Font(name="Roboto", size=12, bold=True, color=COLORS["dark_green"])
#             value_cell.alignment = ALIGNMENTS["center"]
#             value_cell.border = BORDERS["thin"]
#             value_cell.fill = FILLS["none"]
        
#         row += 3  # после таблицы
        
#         # -------------------------------------------------
#         # БЛОК 2: К ВЫПОЛНЕНИЮ / В РЕЗЕРВЕ
#         # -------------------------------------------------
#         # Заголовок
#         self.ws.cell(row=row, column=2, value="К ВЫПОЛНЕНИЮ / В РЕЗЕРВЕ")
#         self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=11, bold=True, color=COLORS["dark_green"])
#         row += 1
        
#         # Данные для таблицы
#         stats_execution = [
#             ("Всего заказов", metrics_by_status['execution']['count']),
#             ("Общая сумма", f"{metrics_by_status['execution']['total_amount']:,.0f} ₽"),
#             ("Средний чек", f"{metrics_by_status['execution']['avg_check']:,.0f} ₽"),
#         ]
        
#         # Строка с названиями
#         for col_offset, (label, _) in enumerate(stats_execution):
#             label_cell = self.ws.cell(row=row, column=start_col + col_offset, value=label)
#             label_cell.font = Font(name="Roboto", size=9, bold=True)
#             label_cell.alignment = ALIGNMENTS["center"]
#             label_cell.border = BORDERS["thin"]
#             label_cell.fill = PatternFill(start_color=COLORS["light_green"], end_color=COLORS["light_green"], fill_type="solid")
        
#         # Строка со значениями
#         for col_offset, (_, value) in enumerate(stats_execution):
#             value_cell = self.ws.cell(row=row + 1, column=start_col + col_offset, value=value)
#             value_cell.font = Font(name="Roboto", size=12, bold=True, color=COLORS["dark_green"])
#             value_cell.alignment = ALIGNMENTS["center"]
#             value_cell.border = BORDERS["thin"]
#             value_cell.fill = FILLS["none"]
        
#         row += 3  # после таблицы
        
#         # -------------------------------------------------
#         # БЛОК 3: НЕСООТВЕТСТВИЯ (если есть)
#         # -------------------------------------------------
#         total_inconsistencies = len(inconsistencies['agreement_cancelled']) + len(inconsistencies['execution_cancelled'])

#         if total_inconsistencies > 0:
#             # Заголовок с предупреждением (используем существующий стиль)
#             warning_cell = self.ws.cell(row=row, column=2, value="⚠️ НЕСООТВЕТСТВИЯ")
#             warning_cell.font = Font(name="Roboto", size=11, bold=True, color=COLORS["dark_green"])  # вместо красного
#             warning_cell.alignment = ALIGNMENTS["left"]
#             row += 1
            
#             # Подзаголовок
#             info_cell = self.ws.cell(row=row, column=2, value="Обнаружены отмененные заказы с активными статусами:")
#             info_cell.font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])
#             info_cell.alignment = ALIGNMENTS["left"]
#             row += 1
            
#             # Таблица несоответствий
#             headers = ["СТАТУС", "КОЛИЧЕСТВО", "ПРИМЕЧАНИЕ"]
#             for col_idx, header in enumerate(headers, start_col):
#                 cell = self.ws.cell(row=row, column=col_idx, value=header)
#                 cell.font = FONTS["header_white"]
#                 cell.alignment = ALIGNMENTS["center"]
#                 cell.fill = FILLS["header"]  # Используем стандартный зелёный, а не красный
#                 cell.border = BORDERS["thin"]
#             row += 1
            
#             # Данные по 'На согласовании'
#             if inconsistencies['agreement_cancelled']:
#                 count = len(inconsistencies['agreement_cancelled'])
                
#                 # Статус
#                 cell_status = self.ws.cell(row=row, column=start_col, value="На согласовании (отменен)")
#                 cell_status.font = Font(name="Roboto", size=9, bold=True, color=COLORS["dark_green"])  # тёмно-зелёный
#                 cell_status.alignment = ALIGNMENTS["left"]
#                 cell_status.border = BORDERS["thin"]
#                 cell_status.fill = FILLS["alt"]  # Используем alt (светло-серый) вместо красного
                
#                 # Количество
#                 cell_count = self.ws.cell(row=row, column=start_col + 1, value=count)
#                 cell_count.font = FONTS["normal"]
#                 cell_count.alignment = ALIGNMENTS["center"]
#                 cell_count.border = BORDERS["thin"]
#                 cell_count.fill = FILLS["alt"]
                
#                 # Примечание с гиперссылкой
#                 cell_note = self.ws.cell(row=row, column=start_col + 2, value=f"Смотреть {count} заказов →")
#                 cell_note.font = Font(name="Roboto", size=9, color=COLORS["blue"], underline="single")
#                 cell_note.alignment = ALIGNMENTS["left"]
#                 cell_note.border = BORDERS["thin"]
#                 cell_note.fill = FILLS["alt"]
#                 cell_note.hyperlink = f"#'НЕСООТВЕТСТВИЯ'!A1"
                
#                 row += 1
            
#             # Данные по 'К выполнению / В резерве'
#             if inconsistencies['execution_cancelled']:
#                 count = len(inconsistencies['execution_cancelled'])
                
#                 # Статус
#                 cell_status = self.ws.cell(row=row, column=start_col, value="К выполнению / В резерве (отменен)")
#                 cell_status.font = Font(name="Roboto", size=9, bold=True, color=COLORS["dark_green"])
#                 cell_status.alignment = ALIGNMENTS["left"]
#                 cell_status.border = BORDERS["thin"]
#                 cell_status.fill = FILLS["alt"]
                
#                 # Количество
#                 cell_count = self.ws.cell(row=row, column=start_col + 1, value=count)
#                 cell_count.font = FONTS["normal"]
#                 cell_count.alignment = ALIGNMENTS["center"]
#                 cell_count.border = BORDERS["thin"]
#                 cell_count.fill = FILLS["alt"]
                
#                 # Примечание с гиперссылкой
#                 cell_note = self.ws.cell(row=row, column=start_col + 2, value=f"Смотреть {count} заказов →")
#                 cell_note.font = Font(name="Roboto", size=9, color=COLORS["blue"], underline="single")
#                 cell_note.alignment = ALIGNMENTS["left"]
#                 cell_note.border = BORDERS["thin"]
#                 cell_note.fill = FILLS["alt"]
#                 cell_note.hyperlink = f"#'НЕСООТВЕТСТВИЯ'!A1"
                
#                 row += 1
            
#             row += 1  # отступ после таблицы несоответствий
        
#         # -------------------------------------------------
#         # НАВИГАЦИЯ ПО ОТЧЕТУ
#         # -------------------------------------------------
#         nav_cell = self.ws.cell(row=row, column=2, value="НАВИГАЦИЯ ПО ОТЧЕТУ")
#         nav_cell.font = Font(name="Roboto", size=11, bold=True, color=COLORS["dark_green"])
#         nav_cell.alignment = ALIGNMENTS["left"]
#         row += 1
        
#         # -------------------------------------------------
#         # ТАБЛИЦА ОГЛАВЛЕНИЯ
#         # -------------------------------------------------
#         headers = ["№", "РАЗДЕЛ", "ОПИСАНИЕ"]
#         start_col = 2
        
#         for col_idx, header in enumerate(headers, start_col):
#             cell = self.ws.cell(row=row, column=col_idx, value=header)
#             cell.font = FONTS["header_white"]
#             cell.alignment = ALIGNMENTS["center"]
#             cell.fill = FILLS["header"]
#             cell.border = BORDERS["thin"]
        
#         row += 1
        
#         # Данные таблицы
#         for idx, sheet in enumerate(sheets_info, 1):
#             # Номер
#             cell_num = self.ws.cell(row=row, column=start_col, value=idx)
#             cell_num.font = FONTS["normal"]
#             cell_num.alignment = ALIGNMENTS["center"]
#             cell_num.border = BORDERS["thin"]
#             cell_num.fill = FILLS["alt"] if idx % 2 == 0 else FILLS["none"]
            
#             # Название раздела (с гиперссылкой)
#             cell_name = self.ws.cell(row=row, column=start_col + 1, value=f"{idx}. {sheet['name']}")
#             cell_name.font = Font(name="Roboto", size=10, bold=True, color=COLORS["blue"], underline="single")
#             cell_name.alignment = ALIGNMENTS["left"]
#             cell_name.border = BORDERS["thin"]
#             cell_name.fill = FILLS["alt"] if idx % 2 == 0 else FILLS["none"]
#             cell_name.hyperlink = f"#'{sheet['name']}'!A1"
            
#             # Описание
#             cell_desc = self.ws.cell(row=row, column=start_col + 2, value=sheet.get('description', ''))
#             cell_desc.font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])
#             cell_desc.alignment = ALIGNMENTS["left"]
#             cell_desc.border = BORDERS["thin"]
#             cell_desc.fill = FILLS["alt"] if idx % 2 == 0 else FILLS["none"]
            
#             row += 1
        
#         # -------------------------------------------------
#         # ПОДЧЕРКИВАНИЕ
#         # -------------------------------------------------
#         line_row = row
#         for col in range(start_col, start_col + 3):
#             cell = self.ws.cell(row=line_row, column=col)
#             cell.border = Border(bottom=Side(style='thick', color=COLORS["dark_green"]))
        
#         row += 1
        
#         # -------------------------------------------------
#         # ИТОГОВАЯ СТРОКА
#         # -------------------------------------------------
#         total_cell = self.ws.cell(row=row, column=start_col, value=f"Всего разделов: {len(sheets_info)}")
#         total_cell.font = Font(name="Roboto", size=10, bold=True, color=COLORS["dark_green"])
#         total_cell.fill = PatternFill(start_color=COLORS["light_green"], end_color=COLORS["light_green"], fill_type="solid")
#         total_cell.border = BORDERS["thin"]
        
#         # Объединяем ячейки
#         self.ws.merge_cells(start_row=row, start_column=start_col, end_row=row, end_column=start_col + 2)
#         total_cell.alignment = ALIGNMENTS["center"]
        
#         # -------------------------------------------------
#         # ШИРИНА КОЛОНОК
#         # -------------------------------------------------
#         self.ws.column_dimensions['A'].width = 3
#         self.ws.column_dimensions['B'].width = 12
#         self.ws.column_dimensions['C'].width = 30
#         self.ws.column_dimensions['D'].width = 48
#         self.ws.column_dimensions['E'].width = 20  
        
#         # -------------------------------------------------
#         # ВЫСОТА СТРОК
#         # -------------------------------------------------
#         self.ws.row_dimensions[1].height = 28
#         self.ws.row_dimensions[2].height = 20
#         self.ws.row_dimensions[3].height = 18
        
#         # Высота для строк с показателями
#         row_num = 5
#         self.ws.row_dimensions[row_num].height = 24
#         self.ws.row_dimensions[row_num + 1].height = 24
#         self.ws.row_dimensions[row_num + 2].height = 28
        
#         row_num = 8
#         self.ws.row_dimensions[row_num].height = 24
#         self.ws.row_dimensions[row_num + 1].height = 24
#         self.ws.row_dimensions[row_num + 2].height = 28
        
#         # Стандартная высота для таблицы
#         for r in range(12, row + 1):
#             self.ws.row_dimensions[r].height = 22
        
#         # -------------------------------------------------
#         # СКРЫВАЕМ СЕТКУ
#         # -------------------------------------------------
#         self.ws.sheet_view.showGridLines = False





# orders/reports/sheets/toc_sheet.py
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from datetime import datetime
from .base_sheet import BaseSheet
from ..styles.theme import FILLS, FONTS, BORDERS, ALIGNMENTS, COLORS
from ..queries.toc_queries import TOCQueries


class TOCSheet(BaseSheet):
    def __init__(self, workbook):
        super().__init__(workbook, "TOC")  # Лист называется "TOC"
        # Удаляем дефолтный лист, если он есть
        if "Sheet" in self.wb.sheetnames:
            self.wb.remove(self.wb["Sheet"])
    
    def build(self, sheets_info, request=None, filters=None):
        # sheets_info = [
        #   {"number": 1, "name": "НЕСООТВЕТСТВИЯ", "description": "..."},
        #   {"number": 2, "name": "ОБЩАЯ_АНАЛИТИКА", "description": "..."},
        #   {"number": 3, "name": "ДЕБИТОРКА", "description": "..."}
        # ]
        
        # Получаем метрики по статусам
        metrics_by_status = TOCQueries.get_metrics_by_status(request=request, filters=filters)
        
        # Получаем несоответствия
        inconsistencies = TOCQueries.get_inconsistencies(request=request, filters=filters)
        
        # -------------------------------------------------
        # ШАПКА - компактно (сдвинута на колонку B)
        # -------------------------------------------------
        row = 1
        self.ws.cell(row=row, column=2, value="ОТЧЕТ ПО ЗАКАЗАМ")
        self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=16, bold=True, color=COLORS["dark_green"])
        self.ws.cell(row=row, column=2).alignment = ALIGNMENTS["left"]
        
        row += 1
        self.ws.cell(row=row, column=2, value="Аналитика и детализация заказов")
        self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=10, color=COLORS["text_gray"])
        self.ws.cell(row=row, column=2).alignment = ALIGNMENTS["left"]
        
        row += 1
        generated_text = f"Сформировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        self.ws.cell(row=row, column=2, value=generated_text)
        self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])
        
        row += 2
        
        # -------------------------------------------------
        # БЛОК 1: НА СОГЛАСОВАНИИ
        # -------------------------------------------------
        # Заголовок
        self.ws.cell(row=row, column=2, value="НА СОГЛАСОВАНИИ")
        self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=11, bold=True, color=COLORS["dark_green"])
        row += 1
        
        # Данные для таблицы
        stats_agreement = [
            ("Всего заказов", metrics_by_status['agreement']['count']),
            ("Общая сумма", f"{metrics_by_status['agreement']['total_amount']:,.0f} ₽"),
            ("Средний чек", f"{metrics_by_status['agreement']['avg_check']:,.0f} ₽"),
        ]
        
        start_col = 2
        
        # Строка с названиями
        for col_offset, (label, _) in enumerate(stats_agreement):
            label_cell = self.ws.cell(row=row, column=start_col + col_offset, value=label)
            label_cell.font = Font(name="Roboto", size=9, bold=True)
            label_cell.alignment = ALIGNMENTS["center"]
            label_cell.border = BORDERS["thin"]
            label_cell.fill = PatternFill(start_color=COLORS["light_green"], end_color=COLORS["light_green"], fill_type="solid")
        
        # Строка со значениями
        for col_offset, (_, value) in enumerate(stats_agreement):
            value_cell = self.ws.cell(row=row + 1, column=start_col + col_offset, value=value)
            value_cell.font = Font(name="Roboto", size=12, bold=True, color=COLORS["dark_green"])
            value_cell.alignment = ALIGNMENTS["center"]
            value_cell.border = BORDERS["thin"]
            value_cell.fill = FILLS["none"]
        
        row += 3  # после таблицы
        
        # -------------------------------------------------
        # БЛОК 2: К ВЫПОЛНЕНИЮ / В РЕЗЕРВЕ
        # -------------------------------------------------
        # Заголовок
        self.ws.cell(row=row, column=2, value="К ВЫПОЛНЕНИЮ / В РЕЗЕРВЕ")
        self.ws.cell(row=row, column=2).font = Font(name="Roboto", size=11, bold=True, color=COLORS["dark_green"])
        row += 1
        
        # Данные для таблицы
        stats_execution = [
            ("Всего заказов", metrics_by_status['execution']['count']),
            ("Общая сумма", f"{metrics_by_status['execution']['total_amount']:,.0f} ₽"),
            ("Средний чек", f"{metrics_by_status['execution']['avg_check']:,.0f} ₽"),
        ]
        
        # Строка с названиями
        for col_offset, (label, _) in enumerate(stats_execution):
            label_cell = self.ws.cell(row=row, column=start_col + col_offset, value=label)
            label_cell.font = Font(name="Roboto", size=9, bold=True)
            label_cell.alignment = ALIGNMENTS["center"]
            label_cell.border = BORDERS["thin"]
            label_cell.fill = PatternFill(start_color=COLORS["light_green"], end_color=COLORS["light_green"], fill_type="solid")
        
        # Строка со значениями
        for col_offset, (_, value) in enumerate(stats_execution):
            value_cell = self.ws.cell(row=row + 1, column=start_col + col_offset, value=value)
            value_cell.font = Font(name="Roboto", size=12, bold=True, color=COLORS["dark_green"])
            value_cell.alignment = ALIGNMENTS["center"]
            value_cell.border = BORDERS["thin"]
            value_cell.fill = FILLS["none"]
        
        row += 3  # после таблицы
        
        # -------------------------------------------------
        # БЛОК 3: НЕСООТВЕТСТВИЯ (если есть)
        # -------------------------------------------------
        total_inconsistencies = len(inconsistencies['agreement_cancelled']) + len(inconsistencies['execution_cancelled'])

        if total_inconsistencies > 0:
            # Заголовок с предупреждением
            warning_cell = self.ws.cell(row=row, column=2, value="⚠️ НЕСООТВЕТСТВИЯ")
            warning_cell.font = Font(name="Roboto", size=11, bold=True, color=COLORS["dark_green"])
            warning_cell.alignment = ALIGNMENTS["left"]
            row += 1
            
            # Подзаголовок
            info_cell = self.ws.cell(row=row, column=2, value="Обнаружены отмененные заказы с активными статусами:")
            info_cell.font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])
            info_cell.alignment = ALIGNMENTS["left"]
            row += 1
            
            # Таблица несоответствий
            headers = ["СТАТУС", "КОЛИЧЕСТВО", "ПРИМЕЧАНИЕ"]
            for col_idx, header in enumerate(headers, start_col):
                cell = self.ws.cell(row=row, column=col_idx, value=header)
                cell.font = FONTS["header_white"]
                cell.alignment = ALIGNMENTS["center"]
                cell.fill = FILLS["header"]
                cell.border = BORDERS["thin"]
            row += 1
            
            # Находим номер листа с несоответствиями
            inconsistencies_sheet_num = None
            for sheet in sheets_info:
                if sheet["name"] == "НЕСООТВЕТСТВИЯ":
                    inconsistencies_sheet_num = sheet["number"]
                    break
            
            # Данные по 'На согласовании'
            if inconsistencies['agreement_cancelled']:
                count = len(inconsistencies['agreement_cancelled'])
                
                # Статус
                cell_status = self.ws.cell(row=row, column=start_col, value="На согласовании (отменен)")
                cell_status.font = Font(name="Roboto", size=9, bold=True, color=COLORS["dark_green"])
                cell_status.alignment = ALIGNMENTS["left"]
                cell_status.border = BORDERS["thin"]
                cell_status.fill = FILLS["alt"]
                
                # Количество
                cell_count = self.ws.cell(row=row, column=start_col + 1, value=count)
                cell_count.font = FONTS["normal"]
                cell_count.alignment = ALIGNMENTS["center"]
                cell_count.border = BORDERS["thin"]
                cell_count.fill = FILLS["alt"]
                
                # Примечание с гиперссылкой на лист-цифру
                cell_note = self.ws.cell(row=row, column=start_col + 2, value=f"Смотреть {count} заказов →")
                cell_note.font = Font(name="Roboto", size=9, color=COLORS["blue"], underline="single")
                cell_note.alignment = ALIGNMENTS["left"]
                cell_note.border = BORDERS["thin"]
                cell_note.fill = FILLS["alt"]
                if inconsistencies_sheet_num:
                    cell_note.hyperlink = f"#'{inconsistencies_sheet_num}'!A1"
                
                row += 1
            
            # Данные по 'К выполнению / В резерве'
            if inconsistencies['execution_cancelled']:
                count = len(inconsistencies['execution_cancelled'])
                
                # Статус
                cell_status = self.ws.cell(row=row, column=start_col, value="К выполнению / В резерве (отменен)")
                cell_status.font = Font(name="Roboto", size=9, bold=True, color=COLORS["dark_green"])
                cell_status.alignment = ALIGNMENTS["left"]
                cell_status.border = BORDERS["thin"]
                cell_status.fill = FILLS["alt"]
                
                # Количество
                cell_count = self.ws.cell(row=row, column=start_col + 1, value=count)
                cell_count.font = FONTS["normal"]
                cell_count.alignment = ALIGNMENTS["center"]
                cell_count.border = BORDERS["thin"]
                cell_count.fill = FILLS["alt"]
                
                # Примечание с гиперссылкой на лист-цифру
                cell_note = self.ws.cell(row=row, column=start_col + 2, value=f"Смотреть {count} заказов →")
                cell_note.font = Font(name="Roboto", size=9, color=COLORS["blue"], underline="single")
                cell_note.alignment = ALIGNMENTS["left"]
                cell_note.border = BORDERS["thin"]
                cell_note.fill = FILLS["alt"]
                if inconsistencies_sheet_num:
                    cell_note.hyperlink = f"#'{inconsistencies_sheet_num}'!A1"
                
                row += 1
            
            row += 1  # отступ после таблицы несоответствий
        
        # -------------------------------------------------
        # НАВИГАЦИЯ ПО ОТЧЕТУ
        # -------------------------------------------------
        nav_cell = self.ws.cell(row=row, column=2, value="НАВИГАЦИЯ ПО ОТЧЕТУ")
        nav_cell.font = Font(name="Roboto", size=11, bold=True, color=COLORS["dark_green"])
        nav_cell.alignment = ALIGNMENTS["left"]
        row += 1
        
        # -------------------------------------------------
        # ТАБЛИЦА ОГЛАВЛЕНИЯ
        # -------------------------------------------------
        headers = ["№", "РАЗДЕЛ", "ОПИСАНИЕ"]
        start_col = 2
        
        for col_idx, header in enumerate(headers, start_col):
            cell = self.ws.cell(row=row, column=col_idx, value=header)
            cell.font = FONTS["header_white"]
            cell.alignment = ALIGNMENTS["center"]
            cell.fill = FILLS["header"]
            cell.border = BORDERS["thin"]
        
        row += 1
        
        # Данные таблицы
        for sheet in sheets_info:
            # Номер
            cell_num = self.ws.cell(row=row, column=start_col, value=sheet["number"])
            cell_num.font = FONTS["normal"]
            cell_num.alignment = ALIGNMENTS["center"]
            cell_num.border = BORDERS["thin"]
            cell_num.fill = FILLS["alt"] if sheet["number"] % 2 == 0 else FILLS["none"]
            
            # Название раздела с гиперссылкой на лист-цифру
            cell_name = self.ws.cell(row=row, column=start_col + 1, value=f"{sheet['number']}. {sheet['name']}")
            cell_name.font = Font(name="Roboto", size=10, bold=True, color=COLORS["blue"], underline="single")
            cell_name.alignment = ALIGNMENTS["left"]
            cell_name.border = BORDERS["thin"]
            cell_name.fill = FILLS["alt"] if sheet["number"] % 2 == 0 else FILLS["none"]
            # Ссылка на лист с номером (цифрой!)
            cell_name.hyperlink = f"#'{sheet['number']}'!A1"
            
            # Описание
            cell_desc = self.ws.cell(row=row, column=start_col + 2, value=sheet.get('description', ''))
            cell_desc.font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])
            cell_desc.alignment = ALIGNMENTS["left"]
            cell_desc.border = BORDERS["thin"]
            cell_desc.fill = FILLS["alt"] if sheet["number"] % 2 == 0 else FILLS["none"]
            
            row += 1
        
        # -------------------------------------------------
        # ПОДЧЕРКИВАНИЕ
        # -------------------------------------------------
        line_row = row
        for col in range(start_col, start_col + 3):
            cell = self.ws.cell(row=line_row, column=col)
            cell.border = Border(bottom=Side(style='thick', color=COLORS["dark_green"]))
        
        row += 1
        
        # -------------------------------------------------
        # ИТОГОВАЯ СТРОКА
        # -------------------------------------------------
        total_cell = self.ws.cell(row=row, column=start_col, value=f"Всего разделов: {len(sheets_info)}")
        total_cell.font = Font(name="Roboto", size=10, bold=True, color=COLORS["dark_green"])
        total_cell.fill = PatternFill(start_color=COLORS["light_green"], end_color=COLORS["light_green"], fill_type="solid")
        total_cell.border = BORDERS["thin"]
        
        # Объединяем ячейки
        self.ws.merge_cells(start_row=row, start_column=start_col, end_row=row, end_column=start_col + 2)
        total_cell.alignment = ALIGNMENTS["center"]
        
        # -------------------------------------------------
        # ШИРИНА КОЛОНОК
        # -------------------------------------------------
        self.ws.column_dimensions['A'].width = 3
        self.ws.column_dimensions['B'].width = 12
        self.ws.column_dimensions['C'].width = 30
        self.ws.column_dimensions['D'].width = 48
        self.ws.column_dimensions['E'].width = 20  
        
        # -------------------------------------------------
        # ВЫСОТА СТРОК
        # -------------------------------------------------
        self.ws.row_dimensions[1].height = 28
        self.ws.row_dimensions[2].height = 20
        self.ws.row_dimensions[3].height = 18
        
        # Высота для строк с показателями
        row_num = 5
        self.ws.row_dimensions[row_num].height = 24
        self.ws.row_dimensions[row_num + 1].height = 24
        self.ws.row_dimensions[row_num + 2].height = 28
        
        row_num = 8
        self.ws.row_dimensions[row_num].height = 24
        self.ws.row_dimensions[row_num + 1].height = 24
        self.ws.row_dimensions[row_num + 2].height = 28
        
        # Стандартная высота для таблицы
        for r in range(12, row + 1):
            self.ws.row_dimensions[r].height = 22
        
        # -------------------------------------------------
        # СКРЫВАЕМ СЕТКУ
        # -------------------------------------------------
        self.ws.sheet_view.showGridLines = False
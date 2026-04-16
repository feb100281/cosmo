# orders/reports/sheets/toc_sheet.py
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from datetime import datetime
from .base_sheet import BaseSheet
from ..styles.theme import FILLS, FONTS, BORDERS, ALIGNMENTS, COLORS



class TOCSheet(BaseSheet):
    def __init__(self, workbook):
        super().__init__(workbook, "TOC")  # Лист называется "TOC"
        # Удаляем дефолтный лист, если он есть
        if "Sheet" in self.wb.sheetnames:
            self.wb.remove(self.wb["Sheet"])
    
    def build(self, sheets_info, request=None, filters=None):


        
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
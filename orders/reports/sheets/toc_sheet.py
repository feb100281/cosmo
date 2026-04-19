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
    
    def _draw_separator(self, row, start_col, end_col, color=COLORS["border_gray"]):
        """Рисует разделительную линию"""
        for col in range(start_col, end_col + 1):
            cell = self.ws.cell(row=row, column=col)
            cell.border = Border(bottom=Side(style='thin', color=color))
    
    def build(self, sheets_info, request=None, filters=None):
        
        # -------------------------------------------------
        # ЗАГОЛОВОК - с иконкой и стилем
        # -------------------------------------------------
        row = 1
        
        # Декоративная полоса сверху
        self._draw_separator(row, 2, 4, COLORS["dark_green"])
        row += 1
        
        # Главный заголовок
        title_cell = self.ws.cell(row=row, column=2, value="ОТЧЕТ ПО ЗАКАЗАМ")
        title_cell.font = Font(name="Roboto", size=20, bold=True, color=COLORS["dark_green"])
        title_cell.alignment = Alignment(horizontal="left", vertical="center")
        
        row += 1
        
        # Подзаголовок
        subtitle_cell = self.ws.cell(row=row, column=2, value="Аналитика и детализация заказов")
        subtitle_cell.font = Font(name="Roboto", size=11, color=COLORS["text_gray"])
        subtitle_cell.alignment = Alignment(horizontal="left", vertical="center")
        
        row += 1
        
        # Дата и время генерации с иконкой
        generated_text = f"Сформировано: {datetime.now().strftime('%d.%m.%Y в %H:%M')}"
        date_cell = self.ws.cell(row=row, column=2, value=generated_text)
        date_cell.font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])
        date_cell.alignment = Alignment(horizontal="left", vertical="center")
        
        row += 2
        
        # Декоративная полоса
        self._draw_separator(row, 2, 4, COLORS["light_green"])
        row += 1
        
        # -------------------------------------------------
        # НАВИГАЦИЯ ПО ОТЧЕТУ
        # -------------------------------------------------
        nav_cell = self.ws.cell(row=row, column=2, value="НАВИГАЦИЯ ПО ОТЧЕТУ")
        nav_cell.font = Font(name="Roboto", size=13, bold=True, color=COLORS["dark_green"])
        nav_cell.alignment = Alignment(horizontal="left", vertical="center")
        
        row += 1
        
        # Описание навигации
        desc_cell = self.ws.cell(row=row, column=2, value="Кликните на название раздела, чтобы перейти к нему")
        desc_cell.font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])
        desc_cell.alignment = Alignment(horizontal="left", vertical="center")
        
        row += 2
        
        # -------------------------------------------------
        # ТАБЛИЦА ОГЛАВЛЕНИЯ
        # -------------------------------------------------
        headers = ["№", "РАЗДЕЛ", "ОПИСАНИЕ"]
        start_col = 2
        
        # Заголовки таблицы
        for col_idx, header in enumerate(headers, start_col):
            cell = self.ws.cell(row=row, column=col_idx, value=header)
            cell.font = Font(name="Roboto", size=10, bold=True, color=COLORS["white"])
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.fill = PatternFill(start_color=COLORS["dark_green"], end_color=COLORS["dark_green"], fill_type="solid")
            cell.border = BORDERS["thin"]
        
        row += 1
        
        # Данные таблицы
        for sheet in sheets_info:
            # Номер раздела - стилизованный
            cell_num = self.ws.cell(row=row, column=start_col, value=f"0{sheet['number']}" if sheet['number'] < 10 else sheet['number'])
            cell_num.font = Font(name="Roboto", size=10, bold=True, color=COLORS["dark_green"])
            cell_num.alignment = Alignment(horizontal="center", vertical="center")
            cell_num.border = BORDERS["thin"]
            cell_num.fill = PatternFill(start_color=COLORS["light_green"], end_color=COLORS["light_green"], fill_type="solid")
            
            # Название раздела с гиперссылкой
            cell_name = self.ws.cell(row=row, column=start_col + 1, value=f"{sheet['name']}")
            cell_name.font = Font(name="Roboto", size=10, bold=True, color=COLORS["blue"])
            cell_name.alignment = Alignment(horizontal="left", vertical="center")
            cell_name.border = BORDERS["thin"]
            
            # Альтернативная подсветка строк
            if sheet["number"] % 2 == 0:
                cell_name.fill = PatternFill(start_color=COLORS["light_gray"], end_color=COLORS["light_gray"], fill_type="solid")
            else:
                cell_name.fill = PatternFill(start_color=COLORS["white"], end_color=COLORS["white"], fill_type="solid")
            
            # Ссылка на лист
            cell_name.hyperlink = f"#'{sheet['number']}'!A1"
            
            # Описание раздела
            cell_desc = self.ws.cell(row=row, column=start_col + 2, value=sheet.get('description', ''))
            cell_desc.font = Font(name="Roboto", size=9, color=COLORS["text_gray"])
            cell_desc.alignment = Alignment(horizontal="left", vertical="center")
            cell_desc.border = BORDERS["thin"]
            
            if sheet["number"] % 2 == 0:
                cell_desc.fill = PatternFill(start_color=COLORS["light_gray"], end_color=COLORS["light_gray"], fill_type="solid")
            
            row += 1
        
        # Нижняя граница таблицы
        for col in range(start_col, start_col + 3):
            cell = self.ws.cell(row=row, column=col)
            cell.border = Border(bottom=Side(style='medium', color=COLORS["dark_green"]))
        
        row += 1
        
        # -------------------------------------------------
        # ИТОГОВАЯ СТАТИСТИКА
        # -------------------------------------------------
        total_row = row
        total_text = f"Всего разделов в отчете: {len(sheets_info)}"
        total_cell = self.ws.cell(row=total_row, column=start_col, value=total_text)
        total_cell.font = Font(name="Roboto", size=10, bold=True, color=COLORS["white"])
        total_cell.fill = PatternFill(start_color=COLORS["dark_green"], end_color=COLORS["dark_green"], fill_type="solid")
        total_cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # Объединяем ячейки для итоговой строки
        self.ws.merge_cells(
            start_row=total_row, 
            start_column=start_col, 
            end_row=total_row, 
            end_column=start_col + 2
        )
        
        row += 2
        
        # -------------------------------------------------
        # ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ
        # -------------------------------------------------
        # Блок с полезной информацией
        info_row = row
        info_cell = self.ws.cell(row=info_row, column=start_col, value="ИНФОРМАЦИЯ")
        info_cell.font = Font(name="Roboto", size=10, bold=True, color=COLORS["dark_green"])
        info_cell.alignment = Alignment(horizontal="left", vertical="center")
        
        row += 1
        
        info_items = [
            "• Данные актуальны на момент формирования отчета",
            "• Для перехода к разделу кликните на его название",
            "• Отчет включает анализ заказов, доставки, оплат и клиентов",
    
        ]
        
        for item in info_items:
            item_cell = self.ws.cell(row=row, column=start_col + 1, value=item)
            item_cell.font = Font(name="Roboto", size=8, color=COLORS["text_gray"])
            item_cell.alignment = Alignment(horizontal="left", vertical="center")
            row += 1
        
        row += 1
        
        # -------------------------------------------------
        # ДЕКОРАТИВНЫЙ БЛОК
        # -------------------------------------------------
        # Полоса внизу
        self._draw_separator(row, 2, 4, COLORS["light_green"])
        row += 1
        
        # Текст с благодарностью
        thanks_cell = self.ws.cell(row=row, column=2, value="✨ Спасибо за использование отчета ✨")
        thanks_cell.font = Font(name="Roboto", size=9, italic=True, color=COLORS["text_gray"])
        thanks_cell.alignment = Alignment(horizontal="left", vertical="center")
        
        # -------------------------------------------------
        # НАСТРОЙКА ШИРИНЫ КОЛОНОК
        # -------------------------------------------------
        self.ws.column_dimensions['A'].width = 3
        self.ws.column_dimensions['B'].width = 10   # №
        self.ws.column_dimensions['C'].width = 35   # РАЗДЕЛ
        self.ws.column_dimensions['D'].width = 55   # ОПИСАНИЕ
        self.ws.column_dimensions['E'].width = 20
        
        # -------------------------------------------------
        # НАСТРОЙКА ВЫСОТЫ СТРОК
        # -------------------------------------------------
        self.ws.row_dimensions[1].height = 10  # Полоса сверху
        self.ws.row_dimensions[2].height = 35  # Заголовок
        self.ws.row_dimensions[3].height = 20  # Подзаголовок
        self.ws.row_dimensions[4].height = 20  # Дата
        self.ws.row_dimensions[5].height = 10  # Полоса
        self.ws.row_dimensions[6].height = 25  # Навигация
        self.ws.row_dimensions[7].height = 18  # Описание
        self.ws.row_dimensions[8].height = 28  # Заголовки таблицы
        
        # Высота для строк таблицы
        for r in range(9, 9 + len(sheets_info)):
            self.ws.row_dimensions[r].height = 24
        
        # Высота для итоговой строки
        self.ws.row_dimensions[9 + len(sheets_info)].height = 28
        
        # -------------------------------------------------
        # СКРЫВАЕМ СЕТКУ
        # -------------------------------------------------
        self.ws.sheet_view.showGridLines = False
        

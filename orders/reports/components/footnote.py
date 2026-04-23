# components/footnote.py
from openpyxl.styles import Font, Alignment
from openpyxl.worksheet.worksheet import Worksheet


class Footnote:
    def __init__(self, worksheet: Worksheet):
        self.ws = worksheet
    
    def draw(self, row: int, text: str, col: int = 1, font_size: int = 9) -> int:
        """
        Рисует сноску под таблицей/метриками
        
        Args:
            row: номер строки для вставки
            text: текст сноски
            col: номер колонки (по умолчанию 1)
            font_size: размер шрифта
        
        Returns:
            следующая свободная строка
        """
        cell = self.ws.cell(row=row, column=col, value=text)
        
        # Стиль для сноски
        cell.font = Font(
            size=font_size,
            italic=True,
            color="666666"  # серый цвет
        )
        cell.alignment = Alignment(horizontal='left', vertical='center')
        
        return row + 1
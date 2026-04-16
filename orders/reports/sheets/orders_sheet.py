# orders/reports/sheets/orders_sheet.py
from .base_sheet import BaseSheet
from styles.theme import FORMATS

class OrdersSheet(BaseSheet):
    """Лист с заказами"""
    
    def __init__(self, workbook, orders_data, summary):
        super().__init__(workbook, "ЗАКАЗЫ")
        self.orders_data = orders_data
        self.summary = summary
        
    def build(self):
        """Построить лист заказов"""
        self.add_header(
            title="📦 ОТЧЕТ ПО ЗАКАЗАМ",
            subtitle="Детальная информация по всем заказам",
            note="Сводка по заказам за выбранный период"
        )
        
        self.add_toc_button()
        
        # Секция сводки
        self.add_section_title("📊 ОБЩАЯ СВОДКА", col_start=1, col_end=12)
        
        # Сводные данные
        self.ws.cell(row=self.current_row, column=1, value="Всего заказов:")
        self.ws.cell(row=self.current_row, column=2, value=self.summary['total_orders'])
        self.ws.cell(row=self.current_row, column=4, value="Общая сумма:")
        self.ws.cell(row=self.current_row, column=5, value=self.summary['total_amount'])
        
        self.current_row += 1
        
        self.ws.cell(row=self.current_row, column=1, value="Активные заказы:")
        self.ws.cell(row=self.current_row, column=2, value=self.summary['active'])
        self.ws.cell(row=self.current_row, column=4, value="Отмененные:")
        self.ws.cell(row=self.current_row, column=5, value=self.summary['cancelled'])
        
        self.current_row += 2
        
        # Таблица заказов
        self.add_section_title("📋 ДЕТАЛИЗАЦИЯ ЗАКАЗОВ", col_start=1, col_end=12)
        
        headers = [
            "№", "ID заказа", "Наименование", "Номер", "Дата создания",
            "Статус", "Менеджер", "Клиент", "Тип опер.", "Магазин",
            "Кол-во", "Сумма"
        ]
        
        self.add_table_header(headers, start_col=1, wrap=True)
        
        # Данные
        total_sum = 0
        for idx, order in enumerate(self.orders_data, 1):
            values = [
                idx,
                order['id'][:8] + "...",
                order['fullname'],
                order['number'],
                order['date_from'].strftime('%d.%m.%Y') if order['date_from'] else '',
                order['status'],
                order['manager'],
                order['client'][:20] if order['client'] else '',
                order['oper_type'],
                order['store'],
                order['items_count'],
                order['total_amount']
            ]
            self.add_data_row(values, start_col=1)
            total_sum += order['total_amount']
        
        # Итог
        self.add_blank_row()
        self.add_total_row(["", "", "", "", "", "", "", "", "", "", "ИТОГО:", total_sum], start_col=1)
        
        # Форматы
        self.apply_money_format(12, start_row=8)
        self.set_column_widths({
            'A': 5, 'B': 20, 'C': 30, 'D': 15, 'E': 12,
            'F': 12, 'G': 20, 'H': 25, 'I': 10, 'J': 15,
            'K': 8, 'L': 15
        })
        
        self.freeze_and_hide_grid("A8")
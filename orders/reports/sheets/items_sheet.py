# orders/reports/sheets/items_sheet.py
from .base_sheet import BaseSheet
from django.db.models import Sum
from collections import defaultdict

class ItemsSheet(BaseSheet):
    """Лист с товарами в заказах"""
    
    def __init__(self, workbook, items_data):
        super().__init__(workbook, "ТОВАРЫ")
        self.items_data = items_data
        
    def build(self):
        """Построить лист товаров"""
        self.add_header(
            title="📦 ТОВАРЫ В ЗАКАЗАХ",
            subtitle="Детализация по товарам и позициям",
            note="Полный список всех товаров во всех заказах"
        )
        
        self.add_toc_button()
        
        # Сводка по товарам
        self.add_section_title("📊 СВОДКА ПО ТОВАРАМ", col_start=1, col_end=12)
        
        # Агрегируем данные по товарам
        product_summary = defaultdict(lambda: {'qty': 0, 'amount': 0})
        for item in self.items_data:
            key = item['item_name']
            product_summary[key]['qty'] += item['qty']
            product_summary[key]['amount'] += item['amount']
        
        self.ws.cell(row=self.current_row, column=1, value="Всего уникальных товаров:")
        self.ws.cell(row=self.current_row, column=2, value=len(product_summary))
        self.ws.cell(row=self.current_row, column=4, value="Всего позиций в заказах:")
        self.ws.cell(row=self.current_row, column=5, value=len(self.items_data))
        
        self.current_row += 2
        
        # Таблица товаров
        self.add_section_title("📋 ДЕТАЛИЗАЦИЯ ТОВАРОВ", col_start=1, col_end=12)
        
        headers = ["№", "ID заказа", "Заказ", "Товар", "Штрихкод", "Кол-во", "Цена", "Сумма"]
        self.add_table_header(headers, start_col=1, wrap=True)
        
        total_sum = 0
        for idx, item in enumerate(self.items_data, 1):
            values = [
                idx,
                item['order_id'][:8] + "...",
                item['order_name'][:30],
                item['item_name'][:40],
                item['barcode'],
                item['qty'],
                item['price'],
                item['amount']
            ]
            self.add_data_row(values, start_col=1)
            total_sum += item['amount']
        
        # Итог
        self.add_blank_row()
        self.add_total_row(["", "", "", "", "", "", "ИТОГО:", total_sum], start_col=1)
        
        # Форматы
        self.apply_money_format(7, start_row=8)
        self.apply_money_format(8, start_row=8)
        
        self.set_column_widths({
            'A': 5, 'B': 20, 'C': 35, 'D': 40, 'E': 18, 'F': 10, 'G': 12, 'H': 15
        })
        
        self.freeze_and_hide_grid("A8")
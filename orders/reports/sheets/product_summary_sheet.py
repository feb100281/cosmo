# orders/reports/sheets/product_summary_sheet.py
from .base_sheet import BaseSheet

class ProductSummarySheet(BaseSheet):
    """Лист со сводкой по товарам"""
    
    def __init__(self, workbook, product_summary):
        super().__init__(workbook, "ТОВАРЫ_СВОДКА")
        self.product_summary = product_summary
        
    def build(self):
        """Построить лист сводки по товарам"""
        self.add_header(
            title="📊 СВОДКА ПО ТОВАРАМ",
            subtitle="Анализ продаж по товарным позициям",
            note="Товары отсортированы по сумме продаж"
        )
        
        self.add_toc_button()
        
        # Таблица сводки
        headers = ["№", "Товар", "Кол-во продано", "Сумма продаж", "Кол-во заказов"]
        self.add_table_header(headers, start_col=1, wrap=True)
        
        total_qty = 0
        total_amount = 0
        
        for idx, product in enumerate(self.product_summary, 1):
            values = [
                idx,
                product['item_name'],
                product['total_qty'],
                product['total_amount'],
                product['orders_count']
            ]
            self.add_data_row(values, start_col=1)
            total_qty += product['total_qty']
            total_amount += product['total_amount']
        
        # Итог
        self.add_blank_row()
        self.add_total_row(["", "ИТОГО:", total_qty, total_amount, ""], start_col=1)
        
        # Форматы
        self.apply_money_format(4, start_row=8)
        
        self.set_column_widths({
            'A': 6, 'B': 50, 'C': 15, 'D': 18, 'E': 15
        })
        
        self.freeze_and_hide_grid("A8")
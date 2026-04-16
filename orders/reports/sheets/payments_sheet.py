# orders/reports/sheets/payments_sheet.py
from .base_sheet import BaseSheet

class PaymentsSheet(BaseSheet):
    """Лист с оплатами"""
    
    def __init__(self, workbook, payments_data):
        super().__init__(workbook, "ОПЛАТЫ")
        self.payments_data = payments_data
        
    def build(self):
        """Построить лист оплат"""
        self.add_header(
            title="💰 ОПЛАТЫ ПО ЗАКАЗАМ",
            subtitle="Детальная информация по всем платежам",
            note="История всех оплат и транзакций"
        )
        
        self.add_toc_button()
        
        # Сводка по оплатам
        self.add_section_title("📊 СВОДКА ПО ОПЛАТАМ", col_start=1, col_end=12)
        
        total_payments = len(self.payments_data)
        total_amount = sum(p['amount'] for p in self.payments_data)
        
        self.ws.cell(row=self.current_row, column=1, value="Всего платежей:")
        self.ws.cell(row=self.current_row, column=2, value=total_payments)
        self.ws.cell(row=self.current_row, column=4, value="Общая сумма:")
        self.ws.cell(row=self.current_row, column=5, value=total_amount)
        
        self.current_row += 2
        
        # Таблица оплат
        self.add_section_title("📋 ДЕТАЛИЗАЦИЯ ПЛАТЕЖЕЙ", col_start=1, col_end=12)
        
        headers = [
            "№", "GUID заказа", "Дата", "Тип операции", "Название",
            "Касса", "Номер документа", "Сумма", "Подразделение"
        ]
        
        self.add_table_header(headers, start_col=1, wrap=True)
        
        total_sum = 0
        for idx, payment in enumerate(self.payments_data, 1):
            values = [
                idx,
                payment['order_guid'][:8] + "...",
                payment['date'].strftime('%d.%m.%Y') if payment['date'] else '',
                payment['oper_type'],
                payment['oper_name'][:30],
                payment['cash_deck'],
                payment['doc_number'],
                payment['amount'],
                payment['store']
            ]
            self.add_data_row(values, start_col=1)
            total_sum += payment['amount']
        
        # Итог
        self.add_blank_row()
        self.add_total_row(["", "", "", "", "", "", "", "ИТОГО:", total_sum], start_col=1)
        
        # Форматы
        self.apply_money_format(8, start_row=8)
        
        self.set_column_widths({
            'A': 5, 'B': 20, 'C': 12, 'D': 12, 'E': 30,
            'F': 15, 'G': 15, 'H': 15, 'I': 20
        })
        
        self.freeze_and_hide_grid("A8")
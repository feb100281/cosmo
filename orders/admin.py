# # orders/admin.py

# from django.contrib import admin
# from django.urls import path
# from django.shortcuts import render
# from django.http import HttpResponse
# from django.utils.html import format_html
# from django.utils import timezone
# from .models import Order, OrderItem, OrdersCF
# import openpyxl
# from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
# from openpyxl.utils import get_column_letter
# from io import BytesIO
# from datetime import datetime


# class OrderItemInline(admin.TabularInline):
#     """Inline для отображения товаров в заказе"""
#     model = OrderItem
#     extra = 0
#     fields = ['item', 'barcode', 'qty', 'price', 'amount']
#     readonly_fields = ['amount']
#     raw_id_fields = ['item', 'barcode']
#     show_change_link = True


# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     list_display = [ 'fullname', 'number', 'date_from', 'status', 'manager', 'store', 'is_cancelled']
#     list_filter = ['status', 'is_cancelled', 'manager', 'store', 'date_from', 'oper_type']
#     search_fields = ['fullname', 'number', 'client', 'id']
#     readonly_fields = ['id', 'date_from', 'update_at']
#     inlines = [OrderItemInline]
#     date_hierarchy = 'date_from'
#     list_per_page = 50
    
#     fieldsets = (
#         ('Основная информация', {
#             'fields': ('id', 'fullname', 'number', 'client', 'manager')
#         }),
#         ('Статус и даты', {
#             'fields': ('status', 'oper_type', 'store', 'date_from', 'update_at')
#         }),
#         ('Отмена заказа', {
#             'fields': ('is_cancelled', 'cancellation_reason'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     actions = ['export_selected_orders_to_excel']
    
#     def get_urls(self):
#         urls = super().get_urls()
#         custom_urls = [
#             path('export-orders-report/', self.export_orders_report, name='export_orders_report'),
#         ]
#         return custom_urls + urls
    
#     def changelist_view(self, request, extra_context=None):
#         extra_context = extra_context or {}
#         extra_context['export_url'] = 'admin:export_orders_report'
#         return super().changelist_view(request, extra_context=extra_context)
    
#     def export_orders_report(self, request):
#         """Экспорт отчета по заказам в Excel"""
#         from django.db.models import Sum, Q
        
#         # Получаем фильтры из GET параметров
#         status = request.GET.get('status', '')
#         date_from = request.GET.get('date_from', '')
#         date_to = request.GET.get('date_to', '')
#         manager = request.GET.get('manager', '')
        
#         # Базовый queryset
#         orders = Order.objects.all()
        
#         # Применяем фильтры
#         if status:
#             orders = orders.filter(status=status)
#         if manager:
#             orders = orders.filter(manager=manager)
#         if date_from:
#             orders = orders.filter(date_from__gte=date_from)
#         if date_to:
#             orders = orders.filter(date_to__lte=date_to)
        
#         # Создаем Excel файл
#         wb = openpyxl.Workbook()
        
#         # Стили
#         header_font = Font(bold=True, color="FFFFFF")
#         header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
#         header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
#         border = Border(
#             left=Side(style='thin'),
#             right=Side(style='thin'),
#             top=Side(style='thin'),
#             bottom=Side(style='thin')
#         )
        
#         # Лист с заказами
#         ws_orders = wb.active
#         ws_orders.title = "Заказы"
        
#         # Заголовки для заказов
#         order_headers = [
#             'ID заказа', 'Наименование', 'Номер', 'Дата создания', 
#             'Дата изменения', 'Отменен', 'Причина отмены', 'Статус',
#             'Менеджер', 'Клиент', 'Тип операции', 'Магазин',
#             'Кол-во позиций', 'Общая сумма'
#         ]
        
#         # Заполняем заголовки
#         for col, header in enumerate(order_headers, 1):
#             cell = ws_orders.cell(row=1, column=col, value=header)
#             cell.font = header_font
#             cell.fill = header_fill
#             cell.alignment = header_alignment
#             cell.border = border
        
#         # Заполняем данные по заказам
#         for row, order in enumerate(orders, 2):
#             # Получаем сумму и количество позиций
#             order_items = OrderItem.objects.filter(order=order)
#             total_amount = order_items.aggregate(Sum('amount'))['amount__sum'] or 0
#             items_count = order_items.count()
            
#             data = [
#                 order.id,
#                 order.fullname or '',
#                 order.number or '',
#                 order.date_from.strftime('%d.%m.%Y') if order.date_from else '',
#                 order.update_at.strftime('%d.%m.%Y') if order.update_at else '',
#                 'Да' if order.is_cancelled else 'Нет',
#                 order.cancellation_reason or '',
#                 order.status or '',
#                 order.manager or '',
#                 order.client or '',
#                 order.oper_type or '',
#                 order.store or '',
#                 items_count,
#                 float(total_amount)
#             ]
            
#             for col, value in enumerate(data, 1):
#                 cell = ws_orders.cell(row=row, column=col, value=value)
#                 cell.border = border
#                 if isinstance(value, (int, float)):
#                     cell.alignment = Alignment(horizontal="right")
        
#         # Настраиваем ширину колонок
#         for col in range(1, len(order_headers) + 1):
#             ws_orders.column_dimensions[get_column_letter(col)].width = 20
        
#         # Лист с товарами в заказах
#         ws_items = wb.create_sheet("Товары в заказах")
        
#         item_headers = [
#             'ID заказа', 'Наименование заказа', 'Номенклатура', 
#             'Штрихкод', 'Количество', 'Цена', 'Сумма'
#         ]
        
#         for col, header in enumerate(item_headers, 1):
#             cell = ws_items.cell(row=1, column=col, value=header)
#             cell.font = header_font
#             cell.fill = header_fill
#             cell.alignment = header_alignment
#             cell.border = border
        
#         row = 2
#         for order in orders:
#             items = OrderItem.objects.filter(order=order).select_related('item', 'barcode')
#             for item in items:
#                 data = [
#                     order.id,
#                     order.fullname or '',
#                     item.item.fullname if item.item else '',
#                     item.barcode.barcode if item.barcode else '',
#                     float(item.qty),
#                     float(item.price),
#                     float(item.amount)
#                 ]
                
#                 for col, value in enumerate(data, 1):
#                     cell = ws_items.cell(row=row, column=col, value=value)
#                     cell.border = border
#                     if isinstance(value, (int, float)):
#                         cell.alignment = Alignment(horizontal="right")
                
#                 row += 1
        
#         # Настраиваем ширину колонок для товаров
#         for col in range(1, len(item_headers) + 1):
#             ws_items.column_dimensions[get_column_letter(col)].width = 20
        
#         # Лист с оплатами
#         ws_payments = wb.create_sheet("Оплаты")
        
#         payment_headers = [
#             'GUID заказа', 'Дата', 'Тип операции', 'Название операции',
#             'Касса', 'Номер документа', 'Сумма', 'Подразделение', 'Регистратор'
#         ]
        
#         for col, header in enumerate(payment_headers, 1):
#             cell = ws_payments.cell(row=1, column=col, value=header)
#             cell.font = header_font
#             cell.fill = header_fill
#             cell.alignment = header_alignment
#             cell.border = border
        
#         payments = OrdersCF.objects.all()
#         for row, payment in enumerate(payments, 2):
#             data = [
#                 payment.order_guid or '',
#                 payment.date.strftime('%d.%m.%Y') if payment.date else '',
#                 payment.oper_type or '',
#                 payment.oper_name or '',
#                 payment.cash_deck or '',
#                 payment.doc_number or '',
#                 float(payment.amount),
#                 payment.store or '',
#                 payment.register or ''
#             ]
            
#             for col, value in enumerate(data, 1):
#                 cell = ws_payments.cell(row=row, column=col, value=value)
#                 cell.border = border
#                 if isinstance(value, (int, float)):
#                     cell.alignment = Alignment(horizontal="right")
        
#         for col in range(1, len(payment_headers) + 1):
#             ws_payments.column_dimensions[get_column_letter(col)].width = 20
        
#         # Сохраняем файл
#         response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#         response['Content-Disposition'] = f'attachment; filename=orders_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
#         wb.save(response)
#         return response
    
#     def export_selected_orders_to_excel(self, request, queryset):
#         """Экспорт выбранных заказов в Excel"""
#         from django.db.models import Sum
        
#         wb = openpyxl.Workbook()
#         ws = wb.active
#         ws.title = "Выбранные заказы"
        
#         # Заголовки
#         headers = ['ID', 'Наименование', 'Номер', 'Дата', 'Статус', 'Менеджер', 'Сумма']
#         header_font = Font(bold=True)
#         for col, header in enumerate(headers, 1):
#             ws.cell(row=1, column=col, value=header).font = header_font
        
#         # Данные
#         for row, order in enumerate(queryset, 2):
#             total = OrderItem.objects.filter(order=order).aggregate(Sum('amount'))['amount__sum'] or 0
#             ws.cell(row=row, column=1, value=order.id)
#             ws.cell(row=row, column=2, value=order.fullname)
#             ws.cell(row=row, column=3, value=order.number)
#             ws.cell(row=row, column=4, value=order.date_from.strftime('%d.%m.%Y') if order.date_from else '')
#             ws.cell(row=row, column=5, value=order.status)
#             ws.cell(row=row, column=6, value=order.manager)
#             ws.cell(row=row, column=7, value=float(total))
        
#         response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#         response['Content-Disposition'] = f'attachment; filename=selected_orders_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
#         wb.save(response)
#         return response
    
#     export_selected_orders_to_excel.short_description = "Экспортировать выбранные заказы в Excel"


# @admin.register(OrderItem)
# class OrderItemAdmin(admin.ModelAdmin):
#     list_display = ['order', 'item', 'barcode', 'qty', 'price', 'amount']
#     list_filter = ['order__status', 'order__date_from']
#     search_fields = ['order__fullname', 'item__fullname', 'barcode__barcode']
#     readonly_fields = ['amount']
#     raw_id_fields = ['order', 'item', 'barcode']
#     list_per_page = 50


# @admin.register(OrdersCF)
# class OrdersCFAdmin(admin.ModelAdmin):
#     list_display = ['order_guid', 'date', 'oper_type', 'oper_name', 'amount', 'store', 'doc_number']
#     list_filter = ['oper_type', 'date', 'store']
#     search_fields = ['order_guid', 'doc_number', 'cash_deck']
#     date_hierarchy = 'date'
#     list_per_page = 50
    
#     actions = ['export_payments_to_excel']
    
#     def export_payments_to_excel(self, request, queryset):
#         """Экспорт оплат в Excel"""
#         wb = openpyxl.Workbook()
#         ws = wb.active
#         ws.title = "Оплаты"
        
#         headers = ['GUID заказа', 'Дата', 'Тип операции', 'Название', 'Касса', 'Номер', 'Сумма', 'Подразделение']
#         header_font = Font(bold=True)
#         for col, header in enumerate(headers, 1):
#             ws.cell(row=1, column=col, value=header).font = header_font
        
#         for row, payment in enumerate(queryset, 2):
#             ws.cell(row=row, column=1, value=payment.order_guid)
#             ws.cell(row=row, column=2, value=payment.date.strftime('%d.%m.%Y') if payment.date else '')
#             ws.cell(row=row, column=3, value=payment.oper_type)
#             ws.cell(row=row, column=4, value=payment.oper_name)
#             ws.cell(row=row, column=5, value=payment.cash_deck)
#             ws.cell(row=row, column=6, value=payment.doc_number)
#             ws.cell(row=row, column=7, value=float(payment.amount))
#             ws.cell(row=row, column=8, value=payment.store)
        
#         response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#         response['Content-Disposition'] = f'attachment; filename=payments_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
#         wb.save(response)
#         return response
    
#     export_payments_to_excel.short_description = "Экспортировать выбранные оплаты в Excel"


# # orders/admin.py




# class OrderItemInline(admin.TabularInline):
    # model = OrderItem
    # extra = 0
    # fields = ['item', 'barcode', 'qty', 'price', 'amount']
    # readonly_fields = ['amount']
    # raw_id_fields = ['item', 'barcode']
    # show_change_link = True


# # @admin.register(Order)
# # class OrderAdmin(admin.ModelAdmin):
#     list_display = ['fullname', 'number', 'date_from', 'status', 'manager', 'store', 'is_cancelled']
#     list_filter = ['status', 'is_cancelled', 'manager', 'store', 'date_from', 'oper_type']
#     search_fields = ['fullname', 'number', 'client', 'id']
#     readonly_fields = ['id', 'date_from', 'update_at']
#     inlines = [OrderItemInline]
#     date_hierarchy = 'date_from'
#     list_per_page = 50
    
#     fieldsets = (
#         ('Основная информация', {
#             'fields': ('id', 'fullname', 'number', 'client', 'manager')
#         }),
#         ('Статус и даты', {
#             'fields': ('status', 'oper_type', 'store', 'date_from', 'update_at')
#         }),
#         ('Отмена заказа', {
#             'fields': ('is_cancelled', 'cancellation_reason'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     def get_urls(self):
#         urls = super().get_urls()
#         custom_urls = [
#             path('export-report/', self.export_report, name='export_orders_report'),
#         ]
#         return custom_urls + urls
    
#     def changelist_view(self, request, extra_context=None):
#         extra_context = extra_context or {}
#         extra_context['export_url'] = 'admin:export_orders_report'
#         extra_context['current_filters'] = request.GET.urlencode()
#         return super().changelist_view(request, extra_context=extra_context)
    
#     def export_report(self, request):
#         """Экспорт отчета"""
#         from .reports.order_report import generate_orders_report
#         return generate_orders_report(request)


# @admin.register(OrderItem)
# class OrderItemAdmin(admin.ModelAdmin):
#     list_display = ['order', 'item', 'barcode', 'qty', 'price', 'amount']
#     list_filter = ['order__status', 'order__date_from']
#     search_fields = ['order__fullname', 'item__fullname', 'barcode__barcode']
#     readonly_fields = ['amount']
#     raw_id_fields = ['order', 'item', 'barcode']
#     list_per_page = 50


# @admin.register(OrdersCF)
# class OrdersCFAdmin(admin.ModelAdmin):
#     list_display = ['order_guid', 'date', 'oper_type', 'oper_name', 'amount', 'store', 'doc_number']
#     list_filter = ['oper_type', 'date', 'store']
#     search_fields = ['order_guid', 'doc_number', 'cash_deck']
#     date_hierarchy = 'date'
#     list_per_page = 50


from django.contrib import admin
from .models import MV_Orders, OrdersCF, MV_OrdersItems


class OrderCFInline(admin.TabularInline):
    model = OrdersCF
    extra = 0
    fields = ['date', 'oper_type', 'cash_deck', 'doc_number', 'amount', 'store']
    readonly_fields = ['date', 'oper_type', 'cash_deck', 'doc_number', 'amount', 'store']
    show_change_link = True

class OrderItemInline(admin.TabularInline):
    model = MV_OrdersItems
    extra = 0
    fields = ['article', 'fullname', 'barcode', 'qty', 'price', 'amount','cancellation_reason']
    readonly_fields = ['article', 'fullname', 'barcode', 'qty', 'price', 'amount','cancellation_reason']
    show_change_link = True


@admin.register(MV_Orders)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_name', 'number',
        'date_from', 'status', 'change_status',
        'client', 'manager',
        'qty_ordered', 'qty_cancelled', 'order_qty',
        'order_amount', 'amount_delivery', 'amount_cancelled', 'amount_active',
        'cash_recieved', 'cash_returned', 'cash_pmts',
        'shiped', 'returned', 'shiped_qty', 'shiped_amount', 'returned_amount',
        'total_shiped_amount', 'shiped_delivery_amount',
    ]
    list_filter = ['status', 'change_status', 'manager', 'date_from', 'client']
    search_fields = ['order_name', 'number', 'client', 'order_id']
    inlines = [OrderCFInline, OrderItemInline]
    date_hierarchy = 'date_from'
    list_per_page = 50
    
    class Media:
        css = {"all": ("css/admin_overrides.css",)}
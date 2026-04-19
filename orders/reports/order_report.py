# orders/reports/order_report.py
from django.http import HttpResponse
from openpyxl import Workbook
from datetime import datetime
import io
from django.db.models import Sum, Count, Q, Avg
from django.db.models.functions import TruncMonth

from .queries.dashboard_queries import DashboardQueries
from .queries.executive_queries import ExecutiveQueries
from .queries.orders_detail_queries import OrdersDetailQueries
from .queries.delivery_analysis_query import DeliveryAnalysisQueries  
from .queries.manager_queries import ManagerQueries 
from .queries.client_analysis_query import ClientAnalysisQueries
from .queries.payments_analysis_query import PaymentsAnalysisQueries 
from .queries.remaining_to_ship_query import RemainingToShipQueries
from .queries.debt_analysis_query import DebtAnalysisQueries


from .sheets.toc_sheet import TOCSheet
from .sheets.executive_sheet import ExecutiveSheet
from .sheets.orders_detail_sheet import OrdersDetailSheet
from .sheets.manager_analysis_sheet import ManagerAnalysisSheet
from .sheets.client_analysis_sheet import ClientAnalysisSheet
from .sheets.payments_analysis_sheet import PaymentsAnalysisSheet
from .sheets.daily_payments_sheet import DailyPaymentsSheet
from .sheets.delivery_analysis_sheet import DeliveryAnalysisSheet
from .sheets.remaining_to_ship_sheet import RemainingToShipSheet
from .sheets.debt_analysis_sheet import DebtAnalysisSheet  



def generate_orders_report(request):
    """Главная функция генерации отчета"""
    
    # Создаем workbook
    wb = Workbook()
    
    # Удаляем дефолтный лист
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])
    
    sheets_info = []
    sheet_counter = 1
    
    # ============================================================
    # 1. Executive Summary - использует ExecutiveQueries
    # ============================================================
    exec_queries = ExecutiveQueries(request)
    
    exec_sheet = ExecutiveSheet(wb, str(sheet_counter), request=request)
    exec_sheet.build()
    
    sheets_info.append({
        "number": sheet_counter,
        "name": "Executive Summary",
        "description": "Ключевые показатели, тренды, топ-менеджеры"
    })
    sheet_counter += 1
    
    # ============================================================
    # 2. Детализация АКТИВНЫХ заказов
    # ============================================================
    orders_detail_queries = OrdersDetailQueries()
    active_orders_data = orders_detail_queries.get_active_orders_detail()
    
    orders_sheet = OrdersDetailSheet(wb, str(sheet_counter))
    orders_sheet.build(active_orders_data)
    sheets_info.append({
        "number": sheet_counter,
        "name": "Детализация заказов",
        "description": f"Активные заказы ({len(active_orders_data)} шт.)"
    })
    sheet_counter += 1
    
    # ============================================================
    # 3. АНАЛИЗ ДОСТАВКИ
    # ============================================================
    delivery_analysis_queries = DeliveryAnalysisQueries(request)
    
    delivery_analysis_sheet = DeliveryAnalysisSheet(wb, str(sheet_counter), request=request)
    delivery_analysis_sheet.build()
    
    sheets_info.append({
        "number": sheet_counter,
        "name": "Анализ доставки",
        "description": "Аналитика по услугам доставки: менеджеры, тренды, клиенты"
    })
    sheet_counter += 1
    
    # ============================================================
    # 4. Остальные листы - используют DashboardQueries
    # ============================================================
    queries = DashboardQueries(request)
    
    # Базовые данные для остальных листов
    all_orders = queries.get_all_orders()
    
    status_summary = queries.get_status_summary()
    manager_summary = queries.get_manager_summary()
    client_summary = queries.get_client_summary()
    financial_metrics = queries.get_financial_metrics()
    changes_analysis = queries.get_changes_analysis()
    payment_analysis = queries.get_payment_analysis()
    monthly_trends = queries.get_monthly_trends()
    top_debtors = queries.get_top_debtors(limit=10)
    
    # Дополнительные данные
    store_summary = queries.get_store_summary(limit=5)
    stuck_orders = queries.get_stuck_orders(days_threshold=30)
    top_clients = queries.get_top_clients(limit=10)
    
    # ============================================================
    # 5. Анализ по менеджерам - ОБЪЕДИНЯЕМ ДАННЫЕ
    # ============================================================
    manager_queries = ManagerQueries(request)
    
    # Получаем базовую сводку по всем менеджерам
    all_managers_data = manager_queries.get_all_managers_summary()
    
    # ДЛЯ КАЖДОГО МЕНЕДЖЕРА ДОБАВЛЯЕМ ДЕТАЛЬНУЮ ИНФОРМАЦИЮ
    enhanced_managers_data = []
    for manager in all_managers_data:
        manager_name = manager.get('manager')
        if manager_name:
            # Получаем детальную информацию
            details = manager_queries.get_manager_details(manager_name)
            
            # Объединяем данные
            enhanced_manager = {
                **manager,  # Базовые MTD/YTD показатели
                'remaining_to_ship': details.get('remaining_to_ship', 0),
                'top_clients': details.get('top_clients', []),
                'oldest_unpaid_invoice': details.get('oldest_unpaid_invoice'),
            }
            enhanced_managers_data.append(enhanced_manager)
        else:
            enhanced_managers_data.append(manager)
    
    # Строим лист с обогащенными данными
    manager_sheet = ManagerAnalysisSheet(wb, str(sheet_counter))
    manager_sheet.build(enhanced_managers_data)

    sheets_info.append({
        "number": sheet_counter,
        "name": "Анализ по менеджерам",
        "description": f"Портфолио менеджеров ({len(enhanced_managers_data)} чел.) - MTD, YTD, топ-клиенты, старые счета"
    })
    sheet_counter += 1
    
    # ============================================================
    # 6. Анализ клиентской базы 
    # ============================================================
    client_analysis_queries = ClientAnalysisQueries(request)
    client_analysis_sheet = ClientAnalysisSheet(wb, str(sheet_counter), request=request)
    client_analysis_sheet.build()
    
    sheets_info.append({
        "number": sheet_counter,
        "name": "Анализ клиентов",
        "description": "ABC-анализ, топ-клиенты, риски, распределение по менеджерам"
    })
    sheet_counter += 1
    
    
 
    
    
    
    # ============================================================
    # 7. АНАЛИЗ ОПЛАТ (НОВЫЙ ЛИСТ)
    # ============================================================
    payments_analysis_queries = PaymentsAnalysisQueries(request)
    
    payments_analysis_sheet = PaymentsAnalysisSheet(wb, str(sheet_counter), request=request)
    payments_analysis_sheet.build()
    
    sheets_info.append({
        "number": sheet_counter,
        "name": "Анализ оплат",
        "description": "Полная аналитика по всем платежам: тренды, магазины, типы операций"
    })
    sheet_counter += 1
    
    
    # ============================================================
    # 8. ПОДНЕВНАЯ ДИНАМИКА ОПЛАТ ПО МАГАЗИНАМ
    # ============================================================
    daily_payments_data = payments_analysis_queries.get_daily_payments_by_store()

    daily_payments_sheet = DailyPaymentsSheet(wb, str(sheet_counter), request=request)
    daily_payments_sheet.build(daily_payments_data)

    sheets_info.append({
        "number": sheet_counter,
        "name": "Подневная динамика оплат",
        "description": f"Детальная разбивка оплат по дням: {len(daily_payments_data['data'])} магазинов, {len(daily_payments_data['dates'])} дней"
    })
    sheet_counter += 1
    
    
    
    # # ============================================================
    # # 9. АНАЛИЗ ДЕБИТОРСКОЙ ЗАДОЛЖЕННОСТИ (ЗАКАЗЫ С ДОЛГАМИ)
    # # ============================================================
    # debt_queries = DebtAnalysisQueries()
    
    # # Получаем все заказы с долгами
    # debt_orders = debt_queries.get_orders_with_debt()
    
    # # Получаем сводную статистику
    # debt_summary = debt_queries.get_debt_summary()
    
    # # Строим лист
    # debt_sheet = DebtAnalysisSheet(wb, str(sheet_counter), request=request)
    # debt_sheet.build(debt_orders, debt_summary)
    
    # sheets_info.append({
    #     "number": sheet_counter,
    #     "name": "Дебиторская задолженность",
    #     "description": f"Заказы с долгами: {debt_summary['total_debt_orders']} заказов на {debt_summary['total_debt_amount']:,.0f} ₽"
    # })
    # sheet_counter += 1
    
    
    # # ============================================================
    # # 9. ОСТАТКИ К ОТГРУЗКЕ ПО КАТЕГОРИЯМ
    # # ============================================================
    # remaining_queries = RemainingToShipQueries(request)

    # remaining_data = remaining_queries.get_remaining_by_category()
    # parent_cat_summary = remaining_queries.get_remaining_by_parent_cat()
    # summary = remaining_queries.get_remaining_summary()

    # remaining_sheet = RemainingToShipSheet(wb, str(sheet_counter), request=request)
    # remaining_sheet.build(remaining_data, summary, parent_cat_summary)

    # sheets_info.append({
    #     "number": sheet_counter,
    #     "name": "Остатки к отгрузке",
    #     "description": f"Товары к отгрузке: {summary['total_qty'] or 0} шт на {summary['total_amount'] or 0:,.0f} ₽ в {summary['total_orders'] or 0} заказах"
    # })
    # sheet_counter += 1
    
    

    
    # ============================================================
    # СОЗДАЕМ ОГЛАВЛЕНИЕ
    # ============================================================
    toc_sheet = TOCSheet(wb)
    toc_sheet.build(sheets_info, request=request)
    
    # Переставляем TOC на первое место
    toc_index = wb.sheetnames.index("TOC")
    wb.move_sheet(wb["TOC"], offset=-toc_index)
    
    # Сохраняем отчет
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f'Orders_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    
    with io.BytesIO() as output:
        wb.save(output)
        response.write(output.getvalue())
    
    return response
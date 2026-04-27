# # orders/reports/queries/order_fulfillment_query.py
# from django.db.models import Q, Sum, F, Value, FloatField
# from django.db.models.functions import Coalesce
# from orders.models import MV_Orders


# class OrderFulfillmentQueries:
#     """Запросы для анализа процента выполнения заказов (отгрузка / сумма заказа)"""

#     def get_fulfillment_by_manager(self, min_amount=10000):
#         """
#         % выполнения заказов по менеджерам
        
#         Параметры:
#         - min_amount: минимальная сумма заказа для включения в анализ (排除 мелких)
#         """
#         # Получаем заказы с отгрузками (исключаем отмены и закрытые)
#         qs = MV_Orders.objects.filter(
#             total_shiped_amount__gt=0
#         ).exclude(
#             status__in=['Отменен', 'Закрыт']
#         ).filter(
#             amount_active__gte=min_amount
#         )
        
#         # Группировка по менеджерам
#         managers_data = {}
        
#         for order in qs.iterator():
#             manager = order.manager or 'Не указан'
#             amount = float(order.amount_active or 0)
#             shipped = float(order.total_shiped_amount or 0)
            
#             if amount > 0:
#                 fulfillment_pct = (shipped / amount * 100)
#             else:
#                 fulfillment_pct = 0
            
#             if manager not in managers_data:
#                 managers_data[manager] = {
#                     'total_amount': 0,
#                     'total_shipped': 0,
#                     'orders': [],
#                     'lost_revenue': 0,
#                     'avg_fulfillment': 0,
#                 }
            
#             managers_data[manager]['total_amount'] += amount
#             managers_data[manager]['total_shipped'] += shipped
#             managers_data[manager]['orders'].append({
#                 'order_id': order.order_id,
#                 'order_name': order.order_name or order.number or '',
#                 'client': order.client or '',
#                 'amount': amount,
#                 'shipped': shipped,
#                 'fulfillment_pct': fulfillment_pct,
#                 'lost': amount - shipped
#             })
        
#         # Рассчитываем средние показатели и потери
#         result = []
        
#         for manager, data in managers_data.items():
#             total_amount = data['total_amount']
#             total_shipped = data['total_shipped']
            
#             if total_amount > 0:
#                 avg_fulfillment = (total_shipped / total_amount * 100)
#                 lost_revenue = total_amount - total_shipped
#             else:
#                 avg_fulfillment = 0
#                 lost_revenue = 0
            
#             # Сортируем заказы внутри менеджера по % выполнения (худшие сверху)
#             data['orders'].sort(key=lambda x: x['fulfillment_pct'])
            
#             result.append({
#                 'manager': manager,
#                 'total_amount': total_amount,
#                 'total_shipped': total_shipped,
#                 'avg_fulfillment': round(avg_fulfillment, 1),
#                 'lost_revenue': lost_revenue,
#                 'orders_count': len(data['orders']),
#                 'orders': data['orders'][:10],  # ТОП-10 худших заказов
#             })
        
#         # Сортируем по потерянной выручке (от большего к меньшему)
#         result.sort(key=lambda x: x['lost_revenue'], reverse=True)
        
#         return result

#     def get_fulfillment_by_client(self, min_amount=10000, limit=20):
#         """
#         % выполнения заказов по клиентам (для выявления проблемных клиентов)
        
#         Возвращает ТОП клиентов с наибольшей недогрузкой
#         """
#         qs = MV_Orders.objects.filter(
#             total_shiped_amount__gt=0
#         ).exclude(
#             status__in=['Отменен', 'Закрыт']
#         ).filter(
#             amount_active__gte=min_amount
#         )
        
#         clients_data = {}
        
#         for order in qs.iterator():
#             client = order.client or 'Не указан'
#             amount = float(order.amount_active or 0)
#             shipped = float(order.total_shiped_amount or 0)
            
#             if client not in clients_data:
#                 clients_data[client] = {
#                     'total_amount': 0,
#                     'total_shipped': 0,
#                     'lost_revenue': 0,
#                     'orders_count': 0,
#                     'managers': set()
#                 }
            
#             clients_data[client]['total_amount'] += amount
#             clients_data[client]['total_shipped'] += shipped
#             clients_data[client]['orders_count'] += 1
#             if order.manager:
#                 clients_data[client]['managers'].add(order.manager)
        
#         result = []
        
#         for client, data in clients_data.items():
#             total_amount = data['total_amount']
#             total_shipped = data['total_shipped']
#             lost_revenue = total_amount - total_shipped
            
#             if total_amount > 0:
#                 avg_fulfillment = (total_shipped / total_amount * 100)
#             else:
#                 avg_fulfillment = 0
            
#             # Берем только клиентов с потерями > 0
#             if lost_revenue > 0:
#                 result.append({
#                     'client': client,
#                     'total_amount': total_amount,
#                     'total_shipped': total_shipped,
#                     'lost_revenue': lost_revenue,
#                     'avg_fulfillment': round(avg_fulfillment, 1),
#                     'orders_count': data['orders_count'],
#                     'managers': ', '.join(data['managers'])
#                 })
        
#         # Сортируем по потерям
#         result.sort(key=lambda x: x['lost_revenue'], reverse=True)
        
#         return result[:limit]

#     def get_top_low_fulfillment_orders(self, limit=50):
#         """
#         ТОП заказов с самым низким % выполнения
#         (для ручного контроля)
#         """
#         qs = MV_Orders.objects.filter(
#             total_shiped_amount__gt=0
#         ).exclude(
#             status__in=['Отменен', 'Закрыт']
#         ).filter(
#             amount_active__gt=0
#         )
        
#         orders = []
        
#         for order in qs.iterator():
#             amount = float(order.amount_active or 0)
#             shipped = float(order.total_shiped_amount or 0)
            
#             if amount > 0:
#                 fulfillment_pct = (shipped / amount * 100)
#             else:
#                 fulfillment_pct = 0
            
#             # Берем только заказы с выполнением < 80%
#             if fulfillment_pct < 80 and shipped > 0:
#                 orders.append({
#                     'order_id': order.order_id,
#                     'order_name': order.order_name or order.number or '',
#                     'date_from': order.date_from,
#                     'client': order.client or '',
#                     'manager': order.manager or '',
#                     'store': order.store or '',
#                     'amount': amount,
#                     'shipped': shipped,
#                     'fulfillment_pct': round(fulfillment_pct, 1),
#                     'lost': amount - shipped,
#                     'status': order.status or '',
#                 })
        
#         # Сортируем по % выполнения (от худшего)
#         orders.sort(key=lambda x: x['fulfillment_pct'])
        
#         return orders[:limit]

#     def get_fulfillment_summary(self, min_amount=10000):
#         """
#         Сводная статистика по всем заказам
#         """
#         qs = MV_Orders.objects.filter(
#             total_shiped_amount__gt=0
#         ).exclude(
#             status__in=['Отменен', 'Закрыт']
#         ).filter(
#             amount_active__gte=min_amount
#         )
        
#         total_amount = 0
#         total_shipped = 0
#         total_lost = 0
        
#         for order in qs.iterator():
#             amount = float(order.amount_active or 0)
#             shipped = float(order.total_shiped_amount or 0)
            
#             total_amount += amount
#             total_shipped += shipped
#             total_lost += (amount - shipped)
        
#         # Группировка по категориям выполнения
#         categories = {
#             '0-20%': {'count': 0, 'amount': 0},
#             '21-50%': {'count': 0, 'amount': 0},
#             '51-80%': {'count': 0, 'amount': 0},
#             '81-99%': {'count': 0, 'amount': 0},
#             '100%': {'count': 0, 'amount': 0},
#         }
        
#         for order in qs.iterator():
#             amount = float(order.amount_active or 0)
#             shipped = float(order.total_shiped_amount or 0)
            
#             if amount > 0:
#                 pct = (shipped / amount * 100)
#             else:
#                 pct = 0
            
#             if pct < 20:
#                 cat = '0-20%'
#             elif pct < 50:
#                 cat = '21-50%'
#             elif pct < 80:
#                 cat = '51-80%'
#             elif pct < 100:
#                 cat = '81-99%'
#             else:
#                 cat = '100%'
            
#             categories[cat]['count'] += 1
#             categories[cat]['amount'] += amount
        
#         return {
#             'total_orders': qs.count(),
#             'total_amount': total_amount,
#             'total_shipped': total_shipped,
#             'total_lost': total_lost,
#             'avg_fulfillment': round((total_shipped / total_amount * 100), 1) if total_amount > 0 else 0,
#             'categories': categories
#         }
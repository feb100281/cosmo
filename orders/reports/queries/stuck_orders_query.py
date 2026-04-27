# # orders/reports/queries/stuck_orders_query.py
# from django.db.models import Q
# from datetime import datetime, date, timedelta
# from orders.models import MV_Orders


# class StuckOrdersQueries:
#     """Запросы для поиска зависших заказов (нет оплаты, нет отгрузки, не отменены)"""

#     def get_stuck_orders_by_age(self, days_threshold=7):
#         """
#         Возвращает зависшие заказы с группировкой по возрастным категориям
        
#         Возраст считается от даты создания заказа (date_from)
#         """
#         # Используем date.today() вместо datetime.now()
#         today = date.today()
        
#         # Базовый фильтр: нет оплат, нет отгрузок, не закрыт, не отменен
#         base_filter = Q(
#             cash_pmts=0,
#             total_shiped_amount=0,
#             status__in=['К выполнению / В резерве', 'На согласовании']
#         )
        
#         # Получаем все подходящие заказы
#         all_stuck = MV_Orders.objects.filter(base_filter).exclude(
#             status__in=['Закрыт', 'Отменен']
#         ).order_by('date_from')
        
#         # Группируем по возрасту
#         result = {
#             '0-7': [],
#             '8-30': [],
#             '31-90': [],
#             '90+': [],
#             'summary': {
#                 '0-7': {'count': 0, 'amount': 0},
#                 '8-30': {'count': 0, 'amount': 0},
#                 '31-90': {'count': 0, 'amount': 0},
#                 '90+': {'count': 0, 'amount': 0},
#                 'total_count': 0,
#                 'total_amount': 0,
#             }
#         }
        
#         for order in all_stuck:
#             if not order.date_from:
#                 continue
            
#             # Преобразуем order.date_from в date, если это datetime
#             if hasattr(order.date_from, 'date'):
#                 order_date = order.date_from.date()
#             else:
#                 order_date = order.date_from
            
#             age_days = (today - order_date).days
            
#             # Определяем категорию
#             if age_days <= 7:
#                 category = '0-7'
#             elif age_days <= 30:
#                 category = '8-30'
#             elif age_days <= 90:
#                 category = '31-90'
#             else:
#                 category = '90+'
            
#             # Добавляем в список с нужными полями
#             order_data = {
#                 'order_id': order.order_id,
#                 'order_name': order.order_name or order.number or '',
#                 'date_from': order_date,
#                 'age_days': age_days,
#                 'status': order.status or '',
#                 'client': order.client or '',
#                 'manager': order.manager or '',
#                 'store': order.store or '',
#                 'amount': float(order.amount_active or 0),
#                 'update_at': order.update_at,
#             }
            
#             result[category].append(order_data)
            
#             # Обновляем сводку
#             amount = float(order.amount_active or 0)
#             result['summary'][category]['count'] += 1
#             result['summary'][category]['amount'] += amount
#             result['summary']['total_count'] += 1
#             result['summary']['total_amount'] += amount
        
#         return result

#     def get_top_stuck_orders_by_manager(self, limit=10):
#         """Возвращает ТОП менеджеров по сумме зависших заказов"""
#         stuck_orders = self.get_stuck_orders_by_age()
        
#         managers = {}
        
#         for category in ['0-7', '8-30', '31-90', '90+']:
#             for order in stuck_orders[category]:
#                 manager = order.get('manager') or 'Не указан'
#                 amount = order.get('amount', 0)
                
#                 if manager not in managers:
#                     managers[manager] = {
#                         'count': 0,
#                         'amount': 0,
#                         'orders': []
#                     }
                
#                 managers[manager]['count'] += 1
#                 managers[manager]['amount'] += amount
#                 managers[manager]['orders'].append(order)
        
#         sorted_managers = sorted(
#             managers.items(),
#             key=lambda x: x[1]['amount'],
#             reverse=True
#         )[:limit]
        
#         return {
#             manager: data for manager, data in sorted_managers
#         }

#     def get_stuck_summary_by_store(self):
#         """Сводка по магазинам"""
#         stuck_orders = self.get_stuck_orders_by_age()
        
#         stores = {}
        
#         for category in ['0-7', '8-30', '31-90', '90+']:
#             for order in stuck_orders[category]:
#                 store = order.get('store') or 'Не указан'
#                 amount = order.get('amount', 0)
                
#                 if store not in stores:
#                     stores[store] = {'count': 0, 'amount': 0}
                
#                 stores[store]['count'] += 1
#                 stores[store]['amount'] += amount
        
#         sorted_stores = sorted(
#             stores.items(),
#             key=lambda x: x[1]['amount'],
#             reverse=True
#         )
        
#         return dict(sorted_stores)
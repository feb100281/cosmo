# # orders/reports/queries/negative_payments_query.py
# from django.db.models import Q, Sum, F, FloatField, Case, When, Value, IntegerField
# from django.db.models.functions import Coalesce
# from orders.models import MV_Orders


# class NegativePaymentsQueries:
#     """Запросы для поиска заказов с отрицательными оплатами без положительных"""

#     def get_orders_with_negative_payments_only(self, start_date='2025-04-01'):
#         """
#         Получение заказов, у которых:
#         1. Есть оплаты со знаком минус (возвраты/корректировки)
#         2. Нет положительных оплат
#         3. Заказ создан с 01.04.2025
#         """
        
#         # Фильтруем заказы с датой создания от start_date
#         qs = MV_Orders.objects.filter(date_from__gte=start_date)
        
#         result = []
        
#         for order in qs:
#             # Получаем оплаты в виде строки
#             payment_dates = order.payment_dates
            
#             if not payment_dates:
#                 continue
            
#             # Парсим оплаты
#             positive_payments = []
#             negative_payments = []
            
#             # Если payment_dates - это строка с данными
#             if isinstance(payment_dates, str):
#                 import re
#                 # Ищем все вхождения "YYYY-MM-DD: сумма руб"
#                 pattern = r'(\d{4}-\d{2}-\d{2}):\s*([\-\d\.]+)\s*руб'
#                 matches = re.findall(pattern, payment_dates, re.IGNORECASE)
                
#                 for date, amount_str in matches:
#                     try:
#                         amount = float(amount_str)
#                         if amount > 0:
#                             positive_payments.append(amount)
#                         elif amount < 0:
#                             negative_payments.append(amount)
#                     except ValueError:
#                         pass
            
#             # Условие: есть отрицательные оплаты и НЕТ положительных
#             if negative_payments and not positive_payments:
#                 total_negative = sum(negative_payments)
                
#                 # Безопасное преобразование чисел
#                 order_qty = float(order.order_qty or 0)
#                 order_amount = float(order.order_amount or 0)
#                 amount_active = float(order.amount_active or 0)
#                 cash_pmts = float(order.cash_pmts or 0)
                
#                 result.append({
#                     # Основная информация
#                     'order_id': order.order_id,
#                     'order_name': order.order_name or '',
#                     'number': order.number or '',
#                     'date_from': order.date_from,
#                     'update_at': order.update_at,
#                     'status': order.status or '',
#                     'change_status': order.change_status or 'Без изменений',
#                     'client': order.client or '',
#                     'manager': order.manager or '',
#                     'store': order.store or '',
                    
#                     # Количественные показатели
#                     'order_qty': order_qty,
#                     'shiped': float(order.shiped or 0),
#                     'returned': float(order.returned or 0),
#                     'shiped_qty': float(order.shiped_qty or 0),
                    
#                     # Суммовые показатели
#                     'order_amount': order_amount,
#                     'amount_delivery': float(order.amount_delivery or 0),
#                     'amount_cancelled': float(order.amount_cancelled or 0),
#                     'amount_active': amount_active,
                    
#                     # Оплаты
#                     'cash_recieved': float(order.cash_recieved or 0),
#                     'cash_returned': float(order.cash_returned or 0),
#                     'cash_pmts': cash_pmts,
#                     'payment_dates': payment_dates,
                    
#                     # Специфичные для этого отчета
#                     'negative_payments_total': total_negative,
#                     'negative_payments_count': len(negative_payments),
#                     'negative_payments_list': negative_payments,
#                 })
        
#         # Сортируем по сумме отрицательных оплат (самые большие возвраты первыми)
#         result.sort(key=lambda x: x['negative_payments_total'], reverse=False)  # Наименьшие (самые отрицательные) первыми
        
#         return result

#     def get_negative_payments_summary(self, orders_data):
#         """Получение сводной статистики по найденным заказам"""
        
#         if not orders_data:
#             return {
#                 'total_orders': 0,
#                 'total_negative_amount': 0,
#                 'total_order_amount': 0,
#                 'unique_clients': 0,
#                 'unique_managers': 0,
#                 'avg_negative_per_order': 0,
#             }
        
#         total_orders = len(orders_data)
#         total_negative_amount = sum(o.get('negative_payments_total', 0) for o in orders_data)
#         total_order_amount = sum(o.get('amount_active', 0) for o in orders_data)
#         unique_clients = len(set(o.get('client', '') for o in orders_data if o.get('client')))
#         unique_managers = len(set(o.get('manager', '') for o in orders_data if o.get('manager')))
        
#         return {
#             'total_orders': total_orders,
#             'total_negative_amount': total_negative_amount,
#             'total_order_amount': total_order_amount,
#             'unique_clients': unique_clients,
#             'unique_managers': unique_managers,
#             'avg_negative_per_order': total_negative_amount / total_orders if total_orders > 0 else 0,
#         }




# orders/reports/queries/negative_payments_query.py
from django.db.models import Q, Sum, F, FloatField, Case, When, Value, IntegerField
from django.db.models.functions import Coalesce
from orders.models import MV_Orders


class NegativePaymentsQueries:
    """Запросы для поиска заказов с отрицательными оплатами без положительных"""

    def get_orders_with_negative_payments_only(self, start_date='2025-04-01'):
        """
        Получение заказов, у которых:
        1. Есть оплаты со знаком минус (возвраты/корректировки)
        2. Нет положительных оплат
        3. Заказ создан с 01.04.2025
        """
        
        # Фильтруем заказы с датой создания от start_date
        qs = MV_Orders.objects.filter(date_from__gte=start_date)
        
        result = []
        
        for order in qs:
            # Получаем оплаты в виде строки
            payment_dates = order.payment_dates
            
            if not payment_dates:
                continue
            
            # Парсим оплаты
            positive_payments = []
            negative_payments = []
            
            # Если payment_dates - это строка с данными
            if isinstance(payment_dates, str):
                import re
                # Ищем все вхождения "YYYY-MM-DD: сумма руб"
                pattern = r'(\d{4}-\d{2}-\d{2}):\s*([\-\d\.]+)\s*руб'
                matches = re.findall(pattern, payment_dates, re.IGNORECASE)
                
                for date, amount_str in matches:
                    try:
                        amount = float(amount_str)
                        if amount > 0:
                            positive_payments.append(amount)
                        elif amount < 0:
                            negative_payments.append(amount)
                    except ValueError:
                        pass
            
            # Условие: есть отрицательные оплаты и НЕТ положительных
            if negative_payments and not positive_payments:
                total_negative = sum(negative_payments)
                
                # Безопасное преобразование чисел
                order_qty = float(order.order_qty or 0)
                order_amount = float(order.order_amount or 0)
                amount_active = float(order.amount_active or 0)
                cash_pmts = float(order.cash_pmts or 0)
                
                # Данные по отгрузкам
                total_shiped_amount = float(order.total_shiped_amount or 0)
                shiped_delivery_amount = float(order.shiped_delivery_amount or 0)
                shiped_amount = float(order.shiped_amount or 0)  # Отгружено товара (без доставки)
                
                # Рассчитываем отклонения
                shipment_variance = total_shiped_amount - amount_active  # Отклонение отгрузки от суммы заказа
                shipment_percent = (total_shiped_amount / amount_active * 100) if amount_active > 0 else 0
                
                # Статус отгрузки
                if total_shiped_amount >= amount_active:
                    shipment_status = "Переотгрузка"
                elif total_shiped_amount > 0:
                    shipment_status = "Частичная"
                else:
                    shipment_status = "Нет"
                
                result.append({
                    # Основная информация
                    'order_id': order.order_id,
                    'order_name': order.order_name or '',
                    'number': order.number or '',
                    'date_from': order.date_from,
                    'update_at': order.update_at,
                    'status': order.status or '',
                    'change_status': order.change_status or 'Без изменений',
                    'client': order.client or '',
                    'manager': order.manager or '',
                    'store': order.store or '',
                    
                    # Количественные показатели
                    'order_qty': order_qty,
                    'shiped': float(order.shiped or 0),
                    'returned': float(order.returned or 0),
                    'shiped_qty': float(order.shiped_qty or 0),
                    
                    # Суммовые показатели
                    'order_amount': order_amount,
                    'amount_delivery': float(order.amount_delivery or 0),
                    'amount_cancelled': float(order.amount_cancelled or 0),
                    'amount_active': amount_active,
                    
                    # Отгрузки
                    'total_shiped_amount': total_shiped_amount,  # Итого отгружено (с доставкой)
                    'shiped_amount': shiped_amount,  # Отгружено товара
                    'shiped_delivery_amount': shiped_delivery_amount,  # Сумма доставки отгруженного
                    
                    # Отклонения
                    'shipment_variance': shipment_variance,
                    'shipment_percent': shipment_percent,
                    'shipment_status': shipment_status,
                    
                    # Оплаты
                    'cash_recieved': float(order.cash_recieved or 0),
                    'cash_returned': float(order.cash_returned or 0),
                    'cash_pmts': cash_pmts,
                    'payment_dates': payment_dates,
                    
                    # Специфичные для этого отчета
                    'negative_payments_total': total_negative,
                    'negative_payments_count': len(negative_payments),
                    'negative_payments_list': negative_payments,
                })
        
        # Сортируем по сумме отрицательных оплат (самые большие возвраты первыми)
        result.sort(key=lambda x: x['negative_payments_total'], reverse=False)
        
        return result

    def get_negative_payments_summary(self, orders_data):
        """Получение сводной статистики по найденным заказам"""
        
        if not orders_data:
            return {
                'total_orders': 0,
                'total_negative_amount': 0,
                'total_order_amount': 0,
                'total_shipped_amount': 0,
                'unique_clients': 0,
                'unique_managers': 0,
                'avg_negative_per_order': 0,
                'orders_with_shipment': 0,
            }
        
        total_orders = len(orders_data)
        total_negative_amount = sum(o.get('negative_payments_total', 0) for o in orders_data)
        total_order_amount = sum(o.get('amount_active', 0) for o in orders_data)
        total_shipped_amount = sum(o.get('total_shiped_amount', 0) for o in orders_data)
        unique_clients = len(set(o.get('client', '') for o in orders_data if o.get('client')))
        unique_managers = len(set(o.get('manager', '') for o in orders_data if o.get('manager')))
        orders_with_shipment = sum(1 for o in orders_data if o.get('total_shiped_amount', 0) > 0)
        
        return {
            'total_orders': total_orders,
            'total_negative_amount': total_negative_amount,
            'total_order_amount': total_order_amount,
            'total_shipped_amount': total_shipped_amount,
            'unique_clients': unique_clients,
            'unique_managers': unique_managers,
            'avg_negative_per_order': total_negative_amount / total_orders if total_orders > 0 else 0,
            'orders_with_shipment': orders_with_shipment,
        }
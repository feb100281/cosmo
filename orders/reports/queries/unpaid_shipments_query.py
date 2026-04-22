# # orders/reports/queries/unpaid_shipments_query.py
# from django.db.models import Q, Sum, F, FloatField
# from django.db.models.functions import Coalesce
# from orders.models import MV_Orders
# from datetime import datetime


# class UnpaidShipmentsQueries:
#     """Запросы для поиска заказов с отгрузкой, но без оплаты или с неполной оплатой"""

#     def get_orders_with_unpaid_shipments(self, days_without_payment=7):
#         """
#         Получение заказов, где:
#         1. Есть отгрузка (total_shiped_amount > 0)
#         2. Оплата меньше отгрузки (cash_pmts < total_shiped_amount)
#         3. Заказ не закрыт
#         """
        
#         # Фильтруем заказы с отгрузкой
#         qs = MV_Orders.objects.filter(
#             total_shiped_amount__gt=0,  # есть отгрузка
#             date_from__gte='2026-01-01' # с 01 января 2026
#         ).exclude(
#             status__in=['Закрыт', 'Отменен']  # исключаем закрытые
#         )
        
#         result = []
        
#         for order in qs:
#             # Безопасное преобразование
#             total_shiped_amount = float(order.total_shiped_amount or 0)
#             cash_pmts = float(order.cash_pmts or 0)
#             amount_active = float(order.amount_active or 0)
            
#             # Расчет недоплаты
#             underpayment = total_shiped_amount - cash_pmts
            
#             # Если есть недоплата (даже 1 рубль)
#             if underpayment > 0:
#                 # Процент оплаты
#                 payment_percent = (cash_pmts / total_shiped_amount * 100) if total_shiped_amount > 0 else 0
                
#                 # Категория риска
#                 if cash_pmts == 0:
#                     risk_category = "КРИТИЧНО - полная неоплата"
#                 elif underpayment > total_shiped_amount * 0.5:
#                     risk_category = "ВЫСОКИЙ РИСК - оплачено менее 50%"
#                 elif underpayment > total_shiped_amount * 0.2:
#                     risk_category = "СРЕДНИЙ РИСК - оплачено 50-80%"
#                 else:
#                     risk_category = "НЕЗНАЧИТЕЛЬНО - оплачено более 80%"
                
#                 # Парсим даты оплат для детализации
#                 payment_details = self._parse_payment_dates(order.payment_dates)
                
#                 result.append({
#                     # Основная информация
#                     'order_id': order.order_id,
#                     'order_name': order.order_name or '',
#                     'number': order.number or '',
#                     'date_from': order.date_from,
#                     'update_at': order.update_at,
#                     'status': order.status or '',
#                     'client': order.client or '',
#                     'manager': order.manager or '',
#                     'store': order.store or '',
                    
#                     # Суммовые показатели
#                     'amount_active': amount_active,  # Сумма заказа
#                     'total_shiped_amount': total_shiped_amount,  # Отгружено всего
#                     'shiped_amount': float(order.shiped_amount or 0),  # Отгружено товара
#                     'shiped_delivery_amount': float(order.shiped_delivery_amount or 0),  # Доставка
#                     'cash_pmts': cash_pmts,  # Оплачено
#                     'underpayment': underpayment,  # Недоплата
#                     'payment_percent': payment_percent,  # % оплаты
#                     'risk_category': risk_category,  # Категория риска
                    
#                     # Детали оплат
#                     'payment_dates': order.payment_dates,
#                     'payment_details': payment_details,
                    
#                     # Дни без оплаты (если есть отгрузка, но нет оплаты)
#                     'days_without_payment': self._calculate_days_without_payment(order),
#                 })
        
#         # Сортируем: сначала критичные (полная неоплата), потом по сумме недоплаты
#         result.sort(key=lambda x: (
#             0 if x['risk_category'] == "КРИТИЧНО - полная неоплата" else 1,
#             -x['underpayment']
#         ))
        
#         return result

#     def _parse_payment_dates(self, payment_dates):
#         """Парсит даты оплат для детального отображения"""
#         if not payment_dates:
#             return []
        
#         payments = []
#         if isinstance(payment_dates, str):
#             import re
#             pattern = r'(\d{4}-\d{2}-\d{2}):\s*([\-\d\.]+)\s*руб'
#             matches = re.findall(pattern, payment_dates, re.IGNORECASE)
            
#             for date, amount_str in matches:
#                 try:
#                     amount = float(amount_str)
#                     payments.append({
#                         'date': date,
#                         'amount': amount,
#                         'type': 'оплата' if amount > 0 else 'возврат'
#                     })
#                 except ValueError:
#                     pass
        
#         return payments

#     def _calculate_days_without_payment(self, order):
#         """Рассчитывает количество дней с момента отгрузки без оплаты"""
#         if order.cash_pmts and float(order.cash_pmts) > 0:
#             return 0
        
#         # Если есть дата отгрузки (update_at может быть датой последнего изменения)
#         if order.update_at and hasattr(order.update_at, 'strftime'):
#             delta = datetime.now().date() - order.update_at.date()
#             return delta.days
        
#         return 0

#     def get_unpaid_shipments_summary(self, orders_data):
#         """Получение сводной статистики по неоплаченным отгрузкам"""
        
#         if not orders_data:
#             return {
#                 'total_orders': 0,
#                 'total_shipped_amount': 0,
#                 'total_underpayment': 0,
#                 'critical_orders': 0,
#                 'high_risk_orders': 0,
#                 'medium_risk_orders': 0,
#                 'low_risk_orders': 0,
#                 'unique_clients': 0,
#                 'unique_managers': 0,
#             }
        
#         total_orders = len(orders_data)
#         total_shipped_amount = sum(o.get('total_shiped_amount', 0) for o in orders_data)
#         total_underpayment = sum(o.get('underpayment', 0) for o in orders_data)
        
#         critical_orders = sum(1 for o in orders_data if o.get('risk_category') == "КРИТИЧНО - полная неоплата")
#         high_risk_orders = sum(1 for o in orders_data if o.get('risk_category') == "ВЫСОКИЙ РИСК - оплачено менее 50%")
#         medium_risk_orders = sum(1 for o in orders_data if o.get('risk_category') == "СРЕДНИЙ РИСК - оплачено 50-80%")
#         low_risk_orders = sum(1 for o in orders_data if o.get('risk_category') == "НЕЗНАЧИТЕЛЬНО - оплачено более 80%")
        
#         unique_clients = len(set(o.get('client', '') for o in orders_data if o.get('client')))
#         unique_managers = len(set(o.get('manager', '') for o in orders_data if o.get('manager')))
        
#         return {
#             'total_orders': total_orders,
#             'total_shipped_amount': total_shipped_amount,
#             'total_underpayment': total_underpayment,
#             'critical_orders': critical_orders,
#             'high_risk_orders': high_risk_orders,
#             'medium_risk_orders': medium_risk_orders,
#             'low_risk_orders': low_risk_orders,
#             'unique_clients': unique_clients,
#             'unique_managers': unique_managers,
#         }




# # orders/reports/queries/unpaid_shipments_query.py
# from django.db.models import Q, Sum, F, FloatField
# from django.db.models.functions import Coalesce
# from orders.models import MV_Orders
# from datetime import datetime
# from decimal import Decimal, ROUND_HALF_UP


# class UnpaidShipmentsQueries:
#     """Запросы для поиска заказов с отгрузкой, но без оплаты или с неполной оплатой"""

#     def get_orders_with_unpaid_shipments(self, days_without_payment=7):
#         """
#         Получение заказов, где:
#         1. Есть отгрузка (total_shiped_amount > 0)
#         2. Оплата меньше отгрузки (cash_pmts < total_shiped_amount)
#         3. Заказ не закрыт
#         """
        
#         # Фильтруем заказы с отгрузкой
#         qs = MV_Orders.objects.filter(
#             total_shiped_amount__gt=0,  # есть отгрузка
#             date_from__gte='2026-01-01' # с 01 января 2026
#         ).exclude(
#             status__in=['Закрыт', 'Отменен']  # исключаем закрытые
#         )
        
#         result = []
        
#         for order in qs:
#             # Безопасное преобразование с использованием Decimal
#             try:
#                 total_shiped_amount = Decimal(str(order.total_shiped_amount or 0))
#                 cash_pmts = Decimal(str(order.cash_pmts or 0))
#                 amount_active = Decimal(str(order.amount_active or 0))
#             except (ValueError, TypeError):
#                 total_shiped_amount = Decimal('0')
#                 cash_pmts = Decimal('0')
#                 amount_active = Decimal('0')
            
#             # Приводим к 2 знакам (копейки)
#             total_shiped_amount = total_shiped_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
#             cash_pmts = cash_pmts.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
#             amount_active = amount_active.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
#             # Корректируем отрицательные оплаты
#             if cash_pmts < 0:
#                 cash_pmts = Decimal('0')
            
#             # Если оплата больше отгрузки, считаем что оплачено 100%
#             if cash_pmts > total_shiped_amount:
#                 cash_pmts = total_shiped_amount
            
#             # Расчет недоплаты
#             underpayment = float(total_shiped_amount - cash_pmts)
            
#             # Если есть недоплата (даже 1 копейка)
#             if underpayment > 0:
#                 # Процент оплаты
#                 if total_shiped_amount > 0:
#                     payment_percent = float((cash_pmts / total_shiped_amount * 100).quantize(Decimal('0.01')))
#                     # Ограничиваем процент 100%
#                     if payment_percent > 100:
#                         payment_percent = 100.0
#                 else:
#                     payment_percent = 0.0
                
#                 # Категория риска
#                 if cash_pmts == 0:
#                     risk_category = "КРИТИЧНО - полная неоплата"
#                 elif underpayment > float(total_shiped_amount * Decimal('0.5')):
#                     risk_category = "ВЫСОКИЙ РИСК - оплачено менее 50%"
#                 elif underpayment > float(total_shiped_amount * Decimal('0.2')):
#                     risk_category = "СРЕДНИЙ РИСК - оплачено 50-80%"
#                 else:
#                     risk_category = "НЕЗНАЧИТЕЛЬНО - оплачено более 80%"
                
#                 # Парсим даты оплат для детализации
#                 payment_details = self._parse_payment_dates(order.payment_dates)
                
#                 result.append({
#                     # Основная информация
#                     'order_id': order.order_id,
#                     'order_name': order.order_name or '',
#                     'number': order.number or '',
#                     'date_from': order.date_from,
#                     'update_at': order.update_at,
#                     'status': order.status or '',
#                     'client': order.client or '',
#                     'manager': order.manager or '',
#                     'store': order.store or '',
                    
#                     # Суммовые показатели
#                     'amount_active': float(amount_active),
#                     'total_shiped_amount': float(total_shiped_amount),
#                     'shiped_amount': float(order.shiped_amount or 0),
#                     'shiped_delivery_amount': float(order.shiped_delivery_amount or 0),
#                     'cash_pmts': float(cash_pmts),
#                     'underpayment': underpayment,
#                     'payment_percent': payment_percent,
#                     'risk_category': risk_category,
                    
#                     # Детали оплат
#                     'payment_dates': order.payment_dates,
#                     'payment_details': payment_details,
                    
#                     # Дни без оплаты
#                     'days_without_payment': self._calculate_days_without_payment(order),
#                 })
        
#         # Сортируем: сначала критичные, потом по сумме недоплаты
#         result.sort(key=lambda x: (
#             0 if x['risk_category'] == "КРИТИЧНО - полная неоплата" else 1,
#             -x['underpayment']
#         ))
        
#         return result

#     def _parse_payment_dates(self, payment_dates):
#         """Парсит даты оплат для детального отображения"""
#         if not payment_dates:
#             return []
        
#         payments = []
#         if isinstance(payment_dates, str):
#             import re
#             pattern = r'(\d{4}-\d{2}-\d{2}):\s*([\-\d\.]+)\s*руб'
#             matches = re.findall(pattern, payment_dates, re.IGNORECASE)
            
#             for date, amount_str in matches:
#                 try:
#                     amount = float(amount_str)
#                     payments.append({
#                         'date': date,
#                         'amount': amount,
#                         'type': 'оплата' if amount > 0 else 'возврат'
#                     })
#                 except ValueError:
#                     pass
        
#         return payments

#     def _calculate_days_without_payment(self, order):
#         """Рассчитывает количество дней с момента отгрузки без оплаты"""
#         if order.cash_pmts and float(order.cash_pmts) > 0:
#             return 0
        
#         if order.update_at and hasattr(order.update_at, 'strftime'):
#             delta = datetime.now().date() - order.update_at.date()
#             return delta.days
        
#         return 0

#     def get_unpaid_shipments_summary(self, orders_data):
#         """Получение сводной статистики по неоплаченным отгрузкам"""
        
#         if not orders_data:
#             return {
#                 'total_orders': 0,
#                 'total_shipped_amount': 0,
#                 'total_underpayment': 0,
#                 'critical_orders': 0,
#                 'high_risk_orders': 0,
#                 'medium_risk_orders': 0,
#                 'low_risk_orders': 0,
#                 'unique_clients': 0,
#                 'unique_managers': 0,
#             }
        
#         total_orders = len(orders_data)
#         total_shipped_amount = sum(o.get('total_shiped_amount', 0) for o in orders_data)
#         total_underpayment = sum(o.get('underpayment', 0) for o in orders_data)
        
#         critical_orders = sum(1 for o in orders_data if o.get('risk_category') == "КРИТИЧНО - полная неоплата")
#         high_risk_orders = sum(1 for o in orders_data if o.get('risk_category') == "ВЫСОКИЙ РИСК - оплачено менее 50%")
#         medium_risk_orders = sum(1 for o in orders_data if o.get('risk_category') == "СРЕДНИЙ РИСК - оплачено 50-80%")
#         low_risk_orders = sum(1 for o in orders_data if o.get('risk_category') == "НЕЗНАЧИТЕЛЬНО - оплачено более 80%")
        
#         unique_clients = len(set(o.get('client', '') for o in orders_data if o.get('client')))
#         unique_managers = len(set(o.get('manager', '') for o in orders_data if o.get('manager')))
        
#         return {
#             'total_orders': total_orders,
#             'total_shipped_amount': total_shipped_amount,
#             'total_underpayment': total_underpayment,
#             'critical_orders': critical_orders,
#             'high_risk_orders': high_risk_orders,
#             'medium_risk_orders': medium_risk_orders,
#             'low_risk_orders': low_risk_orders,
#             'unique_clients': unique_clients,
#             'unique_managers': unique_managers,
#         }




# orders/reports/queries/unpaid_shipments_query.py
from django.db.models import Q, Sum, F, FloatField
from django.db.models.functions import Coalesce
from orders.models import MV_Orders
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


class UnpaidShipmentsQueries:
    """Запросы для поиска заказов с отгрузкой, но без оплаты или с неполной оплатой"""

    def get_orders_with_unpaid_shipments(self, days_without_payment=7):
        """
        Получение заказов, где:
        1. Есть отгрузка (total_shiped_amount > 0)
        2. Оплата меньше отгрузки (cash_pmts < total_shiped_amount)
        3. Заказ не закрыт
        """
        
        # Фильтруем заказы с отгрузкой
        qs = MV_Orders.objects.filter(
            total_shiped_amount__gt=0,  # есть отгрузка
            date_from__gte='2026-01-01' # с 01 января 2026
        ).exclude(
            status__in=['Закрыт', 'Отменен']  # исключаем закрытые
        )
        
        result = []
        
        for order in qs:
            # Безопасное преобразование с использованием Decimal
            try:
                total_shiped_amount = Decimal(str(order.total_shiped_amount or 0))
                cash_pmts = Decimal(str(order.cash_pmts or 0))
                amount_active = Decimal(str(order.amount_active or 0))
            except (ValueError, TypeError):
                total_shiped_amount = Decimal('0')
                cash_pmts = Decimal('0')
                amount_active = Decimal('0')
            
            # Приводим к 2 знакам (копейки)
            total_shiped_amount = total_shiped_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cash_pmts = cash_pmts.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            amount_active = amount_active.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Корректируем отрицательные оплаты
            if cash_pmts < 0:
                cash_pmts = Decimal('0')
            
            # Если оплата больше отгрузки, считаем что оплачено 100%
            if cash_pmts > total_shiped_amount:
                cash_pmts = total_shiped_amount
            
            # Расчет недоплаты
            underpayment = float(total_shiped_amount - cash_pmts)
            
            # Если есть недоплата (даже 1 копейка)
            if underpayment > 0:
                # Процент оплаты
                if total_shiped_amount > 0:
                    payment_percent = float((cash_pmts / total_shiped_amount * 100).quantize(Decimal('0.01')))
                    # Ограничиваем процент 100%
                    if payment_percent > 100:
                        payment_percent = 100.0
                else:
                    payment_percent = 0.0
                
                # Категория риска
                if cash_pmts == 0:
                    risk_category = "КРИТИЧНО - полная неоплата"
                elif underpayment > float(total_shiped_amount * Decimal('0.5')):
                    risk_category = "ВЫСОКИЙ РИСК - оплачено менее 50%"
                elif underpayment > float(total_shiped_amount * Decimal('0.2')):
                    risk_category = "СРЕДНИЙ РИСК - оплачено 50-80%"
                else:
                    risk_category = "НЕЗНАЧИТЕЛЬНО - оплачено более 80%"
                
                # Парсим даты оплат для детализации
                payment_details = self._parse_payment_dates(order.payment_dates)
                
                result.append({
                    # Основная информация
                    'order_id': order.order_id,
                    'order_name': order.order_name or '',
                    'number': order.number or '',
                    'date_from': order.date_from,
                    'update_at': order.update_at,
                    'status': order.status or '',
                    'client': order.client or '',
                    'manager': order.manager or '',
                    'store': order.store or '',
                    
                    # Суммовые показатели
                    'amount_active': float(amount_active),
                    'total_shiped_amount': float(total_shiped_amount),
                    'shiped_amount': float(order.shiped_amount or 0),
                    'shiped_delivery_amount': float(order.shiped_delivery_amount or 0),
                    'cash_pmts': float(cash_pmts),
                    'underpayment': underpayment,
                    'payment_percent': payment_percent,
                    'risk_category': risk_category,
                    
                    # Детали оплат
                    'payment_dates': order.payment_dates,
                    'payment_details': payment_details,
                    
                    # Дни без оплаты
                    'days_without_payment': self._calculate_days_without_payment(order),
                })
        
        # Сортируем: сначала критичные, потом по сумме недоплаты
        result.sort(key=lambda x: (
            0 if x['risk_category'] == "КРИТИЧНО - полная неоплата" else 1,
            -x['underpayment']
        ))
        
        return result

    def _parse_payment_dates(self, payment_dates):
        """Парсит даты оплат для детального отображения"""
        if not payment_dates:
            return []
        
        payments = []
        if isinstance(payment_dates, str):
            import re
            pattern = r'(\d{4}-\d{2}-\d{2}):\s*([\-\d\.]+)\s*руб'
            matches = re.findall(pattern, payment_dates, re.IGNORECASE)
            
            for date, amount_str in matches:
                try:
                    amount = float(amount_str)
                    payments.append({
                        'date': date,
                        'amount': amount,
                        'type': 'оплата' if amount > 0 else 'возврат'
                    })
                except ValueError:
                    pass
        
        return payments

    def _calculate_days_without_payment(self, order):
        """Рассчитывает количество дней с момента отгрузки без оплаты"""
        if order.cash_pmts and float(order.cash_pmts) > 0:
            return 0
        
        if order.update_at and hasattr(order.update_at, 'strftime'):
            delta = datetime.now().date() - order.update_at.date()
            return delta.days
        
        return 0

    def get_unpaid_shipments_summary(self, orders_data):
        """Получение сводной статистики по неоплаченным отгрузкам"""
        
        if not orders_data:
            return {
                'total_orders': 0,
                'total_shipped_amount': 0,
                'total_underpayment': 0,
                'critical_orders': 0,
                'high_risk_orders': 0,
                'medium_risk_orders': 0,
                'low_risk_orders': 0,
                'unique_clients': 0,
                'unique_managers': 0,
            }
        
        total_orders = len(orders_data)
        total_shipped_amount = sum(o.get('total_shiped_amount', 0) for o in orders_data)
        total_underpayment = sum(o.get('underpayment', 0) for o in orders_data)
        
        critical_orders = sum(1 for o in orders_data if o.get('risk_category') == "КРИТИЧНО - полная неоплата")
        high_risk_orders = sum(1 for o in orders_data if o.get('risk_category') == "ВЫСОКИЙ РИСК - оплачено менее 50%")
        medium_risk_orders = sum(1 for o in orders_data if o.get('risk_category') == "СРЕДНИЙ РИСК - оплачено 50-80%")
        low_risk_orders = sum(1 for o in orders_data if o.get('risk_category') == "НЕЗНАЧИТЕЛЬНО - оплачено более 80%")
        
        unique_clients = len(set(o.get('client', '') for o in orders_data if o.get('client')))
        unique_managers = len(set(o.get('manager', '') for o in orders_data if o.get('manager')))
        
        return {
            'total_orders': total_orders,
            'total_shipped_amount': total_shipped_amount,
            'total_underpayment': total_underpayment,
            'critical_orders': critical_orders,
            'high_risk_orders': high_risk_orders,
            'medium_risk_orders': medium_risk_orders,
            'low_risk_orders': low_risk_orders,
            'unique_clients': unique_clients,
            'unique_managers': unique_managers,
        }
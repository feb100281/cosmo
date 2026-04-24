# orders/reports/queries/completed_orders_wrong_status_query.py
from orders.models import MV_Orders
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime


class CompletedOrdersWrongStatusQueries:
    """Запросы для поиска полностью выполненных заказов с некорректным статусом"""
    
    def get_orders_completed_wrong_status(self):
        """
        Получение заказов, где:
        1. Отгружено всё = total_shiped_amount == amount_active
        2. Оплачено всё, что отгружено = cash_pmts == total_shiped_amount
        3. Статус не 'Закрыт' и не 'Отменен'
        4. Сумма заказа > 0
        """
        
        result = []
        
        # Получаем все не закрытые и не отмененные заказы
        orders = MV_Orders.objects.exclude(
            status__in=['Закрыт', 'Отменен']
        ).filter(
            amount_active__gt=0
        )
        
        for order in orders:
            # Безопасное преобразование в Decimal
            try:
                amount_active = Decimal(str(order.amount_active or 0))
                total_shiped = Decimal(str(order.total_shiped_amount or 0))
                cash_pmts = Decimal(str(order.cash_pmts or 0))
            except (ValueError, TypeError):
                continue
            
            # Приводим к 2 знакам
            amount_active = amount_active.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_shiped = total_shiped.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cash_pmts = cash_pmts.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Корректируем отрицательные оплаты
            if cash_pmts < 0:
                cash_pmts = Decimal('0')
            
            # ГЛАВНОЕ УСЛОВИЕ: отгрузили всё, что в заказе И оплатили всё, что отгрузили
            if total_shiped == amount_active and cash_pmts == total_shiped and amount_active > 0:
                
                # Форматируем даты (убираем время)
                date_from = order.date_from.date() if order.date_from else None
                update_at = order.update_at.date() if order.update_at else None
                
                # Дней с момента последнего изменения
                days_since_update = 0
                if update_at:
                    days_since_update = (datetime.now().date() - update_at).days
                
                result.append({
                    'order_name': f"{order.number or ''} от {date_from.strftime('%d.%m.%Y') if date_from else ''}" if order.number else order.order_name or '',
                    'number': order.number or '',
                    'date_from': date_from.strftime('%Y-%m-%d') if date_from else '',
                    'update_at': update_at.strftime('%Y-%m-%d') if update_at else '',
                    'status': order.status or '',
                    'client': order.client or '',
                    'manager': order.manager or '',
                    'store': order.store or '',
                    'amount_active': float(amount_active),
                    'total_shiped_amount': float(total_shiped),
                    'cash_pmts': float(cash_pmts),
                    'days_since_update': days_since_update,
                })
        
        # Сортируем по сумме (крупные сверху)
        result.sort(key=lambda x: -x['amount_active'])
        
        return result
    
    def get_summary(self, orders_data):
        """Получение сводной статистики"""
        if not orders_data:
            return {
                'total_orders': 0,
                'total_amount': 0,
                'unique_clients': 0,
                'unique_managers': 0,
            }
        
        return {
            'total_orders': len(orders_data),
            'total_amount': sum(o.get('amount_active', 0) for o in orders_data),
            'unique_clients': len(set(o.get('client', '') for o in orders_data if o.get('client'))),
            'unique_managers': len(set(o.get('manager', '') for o in orders_data if o.get('manager'))),
        }
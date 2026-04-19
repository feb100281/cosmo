# orders/reports/queries/period_queries.py
from django.db.models import Sum, Count, Q
from orders.models import MV_Orders
from datetime import datetime, timedelta
from .base_queries import BaseQueries


class PeriodQueries(BaseQueries):
    """Запросы для работы с периодами (вчера, позавчера и т.д.)"""
    
    def get_orders_for_period(self, days_ago=1):
        """
        Получить заказы за указанный день
        
        days_ago=1 - вчера
        days_ago=2 - позавчера
        """
        target_date = self.today - timedelta(days=days_ago)
        target_start = datetime.combine(target_date, datetime.min.time())
        target_end = datetime.combine(target_date, datetime.max.time())
        
        # Новые заказы (не отменённые)
        new_orders = MV_Orders.objects.filter(
            date_from__gte=target_start,
            date_from__lte=target_end
        ).exclude(change_status='Отменен').exclude(status='Отменен')
        
        new_stats = new_orders.aggregate(
            count=Count('order_id'),
            amount=Sum('amount_active')
        )
        
        # Отмены за период
        cancelled = MV_Orders.objects.filter(
            Q(change_status='Отменен') | Q(status='Отменен'),
            date_from__gte=target_start,
            date_from__lte=target_end
        )
        
        cancelled_stats = cancelled.aggregate(
            count=Count('order_id'),
            amount=Sum('amount_cancelled')
        )
        
        cancelled_details = cancelled.values(
            'order_name', 'number', 'manager', 'amount_cancelled', 'client'
        ).order_by('-amount_cancelled')[:5]
        
        return {
            'new_orders': {
                'count': new_stats['count'] or 0,
                'amount': float(new_stats['amount'] or 0),
            },
            'cancelled': {
                'count': cancelled_stats['count'] or 0,
                'amount': float(cancelled_stats['amount'] or 0),
                'details': list(cancelled_details),
            }
        }
    
    def get_last_days_stats(self, days=2):
        """
        Получить статистику за последние N дней
        
        Пример: get_last_days_stats(days=2) вернёт данные за вчера и позавчера
        """
        result = {}
        
        for i in range(1, days + 1):
            period_data = self.get_orders_for_period(days_ago=i)
            result[f'last_{i}_days'] = period_data
        
        return result
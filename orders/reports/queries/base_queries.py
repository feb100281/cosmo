# orders/reports/queries/base_queries.py
from django.db.models import Sum, Count, Q, Avg, F
from orders.models import MV_Orders
from datetime import datetime, timedelta


class BaseQueries:
    """Базовый класс с общими методами для всех запросов"""
    
    def __init__(self, request=None):
        self.request = request
        self.today = datetime.now().date()
        self.first_day_month = self.today.replace(day=1)
        self.first_day_year = self.today.replace(month=1, day=1)
    
    def _safe_float(self, value, default=0.0):
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _safe_int(self, value, default=0):
        if value is None:
            return default
        try:
            return int(round(float(value)))
        except (ValueError, TypeError):
            return default
    
    def get_active_orders_stats(self):
        """Статистика по активным заказам (К выполнению / В резерве, На согласовании)"""
        # Заказы со статусом "К выполнению" или "В резерве"
        to_do_orders = MV_Orders.objects.filter(
            Q(status='К выполнению') | Q(status='К выполнению / В резерве')
        )
        
        # Заказы со статусом "На согласовании"
        pending_orders = MV_Orders.objects.filter(status='На согласовании')
        
        # Статистика по "К выполнению"
        to_do_stats = to_do_orders.aggregate(
            count=Count('order_id'),
            qty=Sum('order_qty'),
            paid=Sum('cash_pmts'),
            shipped=Sum('shiped_qty'),
            amount=Sum('amount_active'),
            debt=Sum(F('amount_active') - F('cash_pmts'))
        )
        
        # Статистика по "На согласовании"
        pending_stats = pending_orders.aggregate(
            count=Count('order_id'),
            qty=Sum('order_qty'),
            paid=Sum('cash_pmts'),
            shipped=Sum('shiped_qty'),
            amount=Sum('amount_active'),
            debt=Sum(F('amount_active') - F('cash_pmts'))
        )
        
        # Общая статистика
        all_active_orders = MV_Orders.objects.filter(
            Q(status='К выполнению / В резерве') | Q(status='На согласовании')
        )
        
        all_active_stats = all_active_orders.aggregate(
            count=Count('order_id'),
            qty=Sum('order_qty'),
            paid=Sum('cash_pmts'),
            shipped=Sum('shiped_qty'),
            amount=Sum('amount_active'),
            debt=Sum(F('amount_active') - F('cash_pmts'))
        )
        
        return {
            'total_active_count': all_active_stats.get('count', 0) or 0,
            'total_active_qty': float(all_active_stats.get('qty', 0) or 0),
            'total_active_paid': float(all_active_stats.get('paid', 0) or 0),
            'total_active_shipped': float(all_active_stats.get('shipped', 0) or 0),
            'total_active_amount': float(all_active_stats.get('amount', 0) or 0),
            'total_active_remaining_qty': float((all_active_stats.get('qty', 0) or 0) - (all_active_stats.get('shipped', 0) or 0)),
            'total_active_debt': float(all_active_stats.get('debt', 0) or 0),
            
            'to_do_count': to_do_stats.get('count', 0) or 0,
            'to_do_qty': float(to_do_stats.get('qty', 0) or 0),
            'to_do_paid': float(to_do_stats.get('paid', 0) or 0),
            'to_do_shipped': float(to_do_stats.get('shipped', 0) or 0),
            'to_do_amount': float(to_do_stats.get('amount', 0) or 0),
            'to_do_remaining_qty': float((to_do_stats.get('qty', 0) or 0) - (to_do_stats.get('shipped', 0) or 0)),
            'to_do_debt': float(to_do_stats.get('debt', 0) or 0),
            
            'pending_count': pending_stats.get('count', 0) or 0,
            'pending_qty': float(pending_stats.get('qty', 0) or 0),
            'pending_paid': float(pending_stats.get('paid', 0) or 0),
            'pending_shipped': float(pending_stats.get('shipped', 0) or 0),
            'pending_amount': float(pending_stats.get('amount', 0) or 0),
            'pending_remaining_qty': float((pending_stats.get('qty', 0) or 0) - (pending_stats.get('shipped', 0) or 0)),
            'pending_debt': float(pending_stats.get('debt', 0) or 0),
        }
    
    def get_monthly_trends(self):
        """Тренды по месяцам"""
        from django.db.models.functions import TruncMonth
        
        monthly = MV_Orders.objects.annotate(
            month=TruncMonth('date_from')
        ).values('month').annotate(
            orders_count=Count('order_id'),
            total_amount=Sum('amount_active'),
            total_paid=Sum('cash_pmts'),
            avg_check=Avg('amount_active')
        ).order_by('month')
        
        return list(monthly)
    
    def get_manager_summary(self):
        """Сводка по менеджерам"""
        return MV_Orders.objects.values('manager').annotate(
            orders_count=Count('order_id'),
            total_amount=Sum('amount_active'),
            avg_check=Avg('amount_active'),
            total_qty=Sum('order_qty'),
            debt_amount=Sum(F('amount_active') - F('cash_pmts'))
        ).filter(manager__isnull=False).exclude(manager='').order_by('-total_amount')
    
    def get_top_clients(self, limit=10):
        """Топ клиентов по сумме активных заказов"""
        return MV_Orders.objects.values('client').annotate(
            orders_count=Count('order_id'),
            total_amount=Sum('amount_active'),
            paid_amount=Sum('cash_pmts'),
            debt=Sum(F('amount_active') - F('cash_pmts')),
            avg_check=Avg('amount_active')
        ).filter(client__isnull=False).exclude(client='').order_by('-total_amount')[:limit]
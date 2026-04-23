# orders/reports/queries/delivery_analysis_query.py
from django.db.models import Q, Sum, F, FloatField, Count, Avg
from django.db.models.functions import Coalesce, TruncMonth
from orders.models import MV_Orders
from datetime import datetime, timedelta


class DeliveryAnalysisQueries:
    """Запросы для анализа доставки (исключая отмененные заказы)"""
    
    def __init__(self, request=None):
        self.today = datetime.now().date()
        self.request = request
    
    def _base_queryset(self):
        """
        Базовый queryset с исключением отмененных заказов
        """
        return MV_Orders.objects.exclude(change_status='Отменен')
    
    def get_delivery_metrics(self):
        """
        Основные метрики по доставке (исключая отмененные)
        """
        qs = self._base_queryset()
        
        # Общая статистика
        total_stats = qs.aggregate(
            total_delivery_sum=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
            total_orders_with_delivery=Count('order_id', filter=Q(amount_delivery__gt=0)),
            total_orders_all=Count('order_id'),
            total_amount_sum=Coalesce(Sum('order_amount', output_field=FloatField()), 0.0),
        )
        
        # MTD статистика (с начала месяца)
        first_day_of_month = self.today.replace(day=1)
        mtd_qs = qs.filter(date_from__gte=first_day_of_month)
        
        mtd_stats = mtd_qs.aggregate(
            mtd_delivery_sum=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
            mtd_orders_with_delivery=Count('order_id', filter=Q(amount_delivery__gt=0)),
            mtd_orders_all=Count('order_id'),
            mtd_amount_sum=Coalesce(Sum('order_amount', output_field=FloatField()), 0.0),
        )
        
        # YTD статистика (с начала года)
        first_day_of_year = self.today.replace(month=1, day=1)
        ytd_qs = qs.filter(date_from__gte=first_day_of_year)
        
        ytd_stats = ytd_qs.aggregate(
            ytd_delivery_sum=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
            ytd_orders_with_delivery=Count('order_id', filter=Q(amount_delivery__gt=0)),
            ytd_orders_all=Count('order_id'),
            ytd_amount_sum=Coalesce(Sum('order_amount', output_field=FloatField()), 0.0),
        )
        
        # Рассчитываем проценты и средние
        total_orders_all = total_stats['total_orders_all'] or 1
        mtd_orders_all = mtd_stats['mtd_orders_all'] or 1
        ytd_orders_all = ytd_stats['ytd_orders_all'] or 1
        
        result = {
            'total': {
                'delivery_sum': total_stats['total_delivery_sum'],
                'delivery_percent_of_amount': (
                    (total_stats['total_delivery_sum'] / total_stats['total_amount_sum']) * 100 
                    if total_stats['total_amount_sum'] > 0 else 0
                ),
                'orders_with_delivery_pct': (
                    (total_stats['total_orders_with_delivery'] / total_orders_all) * 100
                ),
                'avg_delivery_per_order': (
                    total_stats['total_delivery_sum'] / total_stats['total_orders_with_delivery']
                    if total_stats['total_orders_with_delivery'] > 0 else 0
                ),
            },
            'mtd': {
                'delivery_sum': mtd_stats['mtd_delivery_sum'],
                'delivery_percent_of_amount': (
                    (mtd_stats['mtd_delivery_sum'] / mtd_stats['mtd_amount_sum']) * 100 
                    if mtd_stats['mtd_amount_sum'] > 0 else 0
                ),
                'orders_with_delivery_pct': (
                    (mtd_stats['mtd_orders_with_delivery'] / mtd_orders_all) * 100
                ),
                'avg_delivery_per_order': (
                    mtd_stats['mtd_delivery_sum'] / mtd_stats['mtd_orders_with_delivery']
                    if mtd_stats['mtd_orders_with_delivery'] > 0 else 0
                ),
            },
            'ytd': {
                'delivery_sum': ytd_stats['ytd_delivery_sum'],
                'delivery_percent_of_amount': (
                    (ytd_stats['ytd_delivery_sum'] / ytd_stats['ytd_amount_sum']) * 100 
                    if ytd_stats['ytd_amount_sum'] > 0 else 0
                ),
                'orders_with_delivery_pct': (
                    (ytd_stats['ytd_orders_with_delivery'] / ytd_orders_all) * 100
                ),
                'avg_delivery_per_order': (
                    ytd_stats['ytd_delivery_sum'] / ytd_stats['ytd_orders_with_delivery']
                    if ytd_stats['ytd_orders_with_delivery'] > 0 else 0
                ),
            }
        }
        
        return result
    
    def get_delivery_by_manager(self, limit=10):
        """
        Анализ доставки по менеджерам (MTD, исключая отмененные)
        """
        first_day_of_month = self.today.replace(day=1)
        
        managers = (
            self._base_queryset()
            .filter(date_from__gte=first_day_of_month)
            .values('manager')
            .annotate(
                total_delivery=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
                total_amount=Coalesce(Sum('order_amount', output_field=FloatField()), 0.0),
                orders_count=Count('order_id'),
                orders_with_delivery=Count('order_id', filter=Q(amount_delivery__gt=0)),
            )
            .filter(manager__isnull=False, manager__gt='')
            .order_by('-total_delivery')[:limit]
        )
        
        result = []
        for m in managers:
            delivery_pct = (m['total_delivery'] / m['total_amount'] * 100) if m['total_amount'] > 0 else 0
            avg_delivery = (m['total_delivery'] / m['orders_with_delivery']) if m['orders_with_delivery'] > 0 else 0
            
            result.append({
                'manager': m['manager'],
                'total_delivery': m['total_delivery'],
                'delivery_percent': delivery_pct,
                'avg_delivery': avg_delivery,
                'orders_count': m['orders_count'],
                'orders_with_delivery': m['orders_with_delivery'],
                'coverage_pct': (m['orders_with_delivery'] / m['orders_count'] * 100) if m['orders_count'] > 0 else 0,
            })
        
        return result
    

    def get_delivery_by_manager_ytd(self, limit=10):
        """
        Анализ доставки по менеджерам (YTD, исключая отмененные)
        """
        first_day_of_year = self.today.replace(month=1, day=1)
        
        managers = (
            self._base_queryset()
            .filter(date_from__gte=first_day_of_year)
            .values('manager')
            .annotate(
                total_delivery=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
                total_amount=Coalesce(Sum('order_amount', output_field=FloatField()), 0.0),
                orders_count=Count('order_id'),
                orders_with_delivery=Count('order_id', filter=Q(amount_delivery__gt=0)),
            )
            .filter(manager__isnull=False, manager__gt='')
            .order_by('-total_delivery')[:limit]
        )
        
        result = []
        for m in managers:
            delivery_pct = (m['total_delivery'] / m['total_amount'] * 100) if m['total_amount'] > 0 else 0
            avg_delivery = (m['total_delivery'] / m['orders_with_delivery']) if m['orders_with_delivery'] > 0 else 0
            
            result.append({
                'manager': m['manager'],
                'total_delivery': m['total_delivery'],
                'delivery_percent': delivery_pct,
                'avg_delivery': avg_delivery,
                'orders_count': m['orders_count'],
                'orders_with_delivery': m['orders_with_delivery'],
                'coverage_pct': (m['orders_with_delivery'] / m['orders_count'] * 100) if m['orders_count'] > 0 else 0,
            })
        
        return result
    
    def get_delivery_trend(self, months=6):
        """
        Месячный тренд доставки (исключая отмененные)
        """
        start_date = self.today - timedelta(days=months*30)
        
        monthly_data = (
            self._base_queryset()
            .filter(date_from__gte=start_date)
            .annotate(month=TruncMonth('date_from'))
            .values('month')
            .annotate(
                delivery_sum=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
                orders_with_delivery=Count('order_id', filter=Q(amount_delivery__gt=0)),
                total_orders=Count('order_id'),
                total_amount=Coalesce(Sum('order_amount', output_field=FloatField()), 0.0),
            )
            .order_by('month')
        )
        
        result = []
        for item in monthly_data:
            if item['month']:
                result.append({
                    'month': item['month'],
                    'delivery_sum': item['delivery_sum'],
                    'delivery_percent': (item['delivery_sum'] / item['total_amount'] * 100) if item['total_amount'] > 0 else 0,
                    'orders_with_delivery': item['orders_with_delivery'],
                    'coverage_pct': (item['orders_with_delivery'] / item['total_orders'] * 100) if item['total_orders'] > 0 else 0,
                })
        
        return result
    
    def get_top_clients_by_delivery(self, limit=5):
        """
        Топ клиентов по сумме доставки (MTD, исключая отмененные)
        """
        first_day_of_month = self.today.replace(day=1)
        
        clients = (
            self._base_queryset()
            .filter(date_from__gte=first_day_of_month, amount_delivery__gt=0)
            .values('client')
            .annotate(
                total_delivery=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
                orders_count=Count('order_id'),
                total_amount=Coalesce(Sum('order_amount', output_field=FloatField()), 0.0),
            )
            .filter(client__isnull=False, client__gt='')
            .order_by('-total_delivery')[:limit]
        )
        
        result = []
        for c in clients:
            result.append({
                'client': c['client'],
                'total_delivery': c['total_delivery'],
                'orders_count': c['orders_count'],
                'avg_delivery': c['total_delivery'] / c['orders_count'] if c['orders_count'] > 0 else 0,
                'delivery_percent': (c['total_delivery'] / c['total_amount'] * 100) if c['total_amount'] > 0 else 0,
            })
        
        return result
    
    def get_delivery_by_status(self):
        """
        Анализ доставки по статусам заказов (исключая отмененные)
        """
        statuses = (
            self._base_queryset()
            .values('status')
            .annotate(
                total_delivery=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
                orders_count=Count('order_id'),
                total_amount=Coalesce(Sum('order_amount', output_field=FloatField()), 0.0),
            )
            .filter(status__isnull=False, status__gt='')
            .order_by('-total_delivery')
        )
        
        result = []
        for s in statuses:
            result.append({
                'status': s['status'],
                'total_delivery': s['total_delivery'],
                'orders_count': s['orders_count'],
                'avg_delivery': s['total_delivery'] / s['orders_count'] if s['orders_count'] > 0 else 0,
                'delivery_percent': (s['total_delivery'] / s['total_amount'] * 100) if s['total_amount'] > 0 else 0,
            })
        
        return result
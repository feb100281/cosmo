# orders/reports/queries/client_analysis_query.py
from django.db.models import Q, Sum, F, FloatField, Count, Avg
from django.db.models.functions import Coalesce
from orders.models import MV_Orders
from datetime import datetime


class ClientAnalysisQueries:
    """Запросы для анализа клиентской базы"""
    
    def __init__(self, request=None):
        self.today = datetime.now().date()
        self.request = request
    
    def _base_queryset(self):
        """Базовый queryset с исключением отмененных заказов"""
        return MV_Orders.objects.exclude(change_status='Отменен')
    
    def get_client_metrics(self):
        """
        Получение ключевых метрик по клиентам (MTD и YTD)
        """
        first_day_of_month = self.today.replace(day=1)
        first_day_of_year = self.today.replace(month=1, day=1)
        
        # MTD метрики
        mtd_qs = self._base_queryset().filter(date_from__gte=first_day_of_month)
        
        mtd_metrics = mtd_qs.aggregate(
            total_clients=Count('client', distinct=True),
            total_orders=Count('order_id'),
            total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
            avg_check=Coalesce(Avg('amount_active', output_field=FloatField()), 0.0),
        )
        
        # Клиенты с повторными заказами (MTD)
        mtd_repeat_clients = (
            mtd_qs.values('client')
            .annotate(orders_count=Count('order_id'))
            .filter(orders_count__gt=1)
            .count()
        )
        
        # YTD метрики
        ytd_qs = self._base_queryset().filter(date_from__gte=first_day_of_year)
        
        ytd_metrics = ytd_qs.aggregate(
            total_clients=Count('client', distinct=True),
            total_orders=Count('order_id'),
            total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
            avg_check=Coalesce(Avg('amount_active', output_field=FloatField()), 0.0),
        )
        
        # Клиенты с повторными заказами (YTD)
        ytd_repeat_clients = (
            ytd_qs.values('client')
            .annotate(orders_count=Count('order_id'))
            .filter(orders_count__gt=1)
            .count()
        )
        
        return {
            'mtd': {
                'total_clients': mtd_metrics['total_clients'],
                'total_orders': mtd_metrics['total_orders'],
                'total_amount': mtd_metrics['total_amount'],
                'avg_check': mtd_metrics['avg_check'],
                'repeat_clients': mtd_repeat_clients,
                'repeat_rate': (mtd_repeat_clients / mtd_metrics['total_clients'] * 100) if mtd_metrics['total_clients'] > 0 else 0,
            },
            'ytd': {
                'total_clients': ytd_metrics['total_clients'],
                'total_orders': ytd_metrics['total_orders'],
                'total_amount': ytd_metrics['total_amount'],
                'avg_check': ytd_metrics['avg_check'],
                'repeat_clients': ytd_repeat_clients,
                'repeat_rate': (ytd_repeat_clients / ytd_metrics['total_clients'] * 100) if ytd_metrics['total_clients'] > 0 else 0,
            },
        }
    
    def _debt_parts(self, start_date, keys=("client",)):
        """
        Деньги по клиентам с разбивкой по заказам:
        долг по отгрузке = отгружено − оплачено (по каждому заказу, не меньше 0);
        не оплачено по неотгруженным = сумма заказа − max(отгружено, оплачено).
        """
        rows = (
            self._base_queryset()
            .filter(date_from__gte=start_date)
            .values(*keys, "amount_active", "cash_pmts", "total_shiped_amount")
        )
        out = {}
        for r in rows:
            amount = float(r["amount_active"] or 0)
            paid = float(r["cash_pmts"] or 0)
            shipped = float(r["total_shiped_amount"] or 0)
            k = tuple(r[x] for x in keys)
            acc = out.setdefault(k, {"shipped": 0.0, "ship_debt": 0.0, "open_unpaid": 0.0})
            acc["shipped"] += shipped
            acc["ship_debt"] += max(0.0, shipped - paid)
            acc["open_unpaid"] += max(0.0, amount - max(shipped, paid))
        return out

    def get_top_clients_by_amount(self, limit=10, period='ytd'):
        """
        Топ клиентов по сумме заказов
        period: 'mtd' или 'ytd'
        """
        if period == 'mtd':
            start_date = self.today.replace(day=1)
        else:
            start_date = self.today.replace(month=1, day=1)
        
        clients = (
            self._base_queryset()
            .filter(date_from__gte=start_date)
            .values('client')
            .annotate(
                total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
                orders_count=Count('order_id'),
                paid_amount=Coalesce(Sum('cash_pmts', output_field=FloatField()), 0.0),
                shipped_amount=Coalesce(Sum('total_shiped_amount', output_field=FloatField()), 0.0),
            )
            .filter(client__isnull=False, client__gt='', total_amount__gt=0)
            .order_by('-total_amount')[:limit]
        )
        
        parts = self._debt_parts(start_date)
        result = []
        for c in clients:
            p = parts.get((c['client'],), {"shipped": 0.0, "ship_debt": 0.0, "open_unpaid": 0.0})
            result.append({
                'client': c['client'],
                'total_amount': c['total_amount'],
                'orders_count': c['orders_count'],
                'avg_check': c['total_amount'] / c['orders_count'] if c['orders_count'] > 0 else 0,
                'paid_amount': c['paid_amount'],
                'shipped_amount': p['shipped'],
                'debt': p['ship_debt'],
                'open_unpaid': p['open_unpaid'],
                'debt_percent': (p['ship_debt'] / p['shipped'] * 100) if p['shipped'] > 0 else 0,
            })
        
        return result
    
    def get_top_clients_by_orders(self, limit=10, period='ytd'):
        """
        Топ клиентов по количеству заказов
        """
        if period == 'mtd':
            start_date = self.today.replace(day=1)
        else:
            start_date = self.today.replace(month=1, day=1)
        
        clients = (
            self._base_queryset()
            .filter(date_from__gte=start_date)
            .values('client')
            .annotate(
                orders_count=Count('order_id'),
                total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
            )
            .filter(client__isnull=False, client__gt='', orders_count__gt=0)
            .order_by('-orders_count')[:limit]
        )
        
        result = []
        for c in clients:
            result.append({
                'client': c['client'],
                'orders_count': c['orders_count'],
                'total_amount': c['total_amount'],
                'avg_check': c['total_amount'] / c['orders_count'] if c['orders_count'] > 0 else 0,
            })
        
        return result
    

    def get_abc_analysis(self, period='ytd'):
        """
        ABC-анализ клиентов (правильное распределение)
        A: 20% клиентов дают 80% выручки (основные)
        B: 30% клиентов дают 15% выручки (средние)
        C: 50% клиентов дают 5% выручки (мелкие)
        """
        if period == 'mtd':
            start_date = self.today.replace(day=1)
        else:
            start_date = self.today.replace(month=1, day=1)
        
        # Получаем всех клиентов с суммами, сортируем по убыванию
        clients = list(
            self._base_queryset()
            .filter(date_from__gte=start_date)
            .values('client')
            .annotate(
                total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
                orders_count=Count('order_id'),
            )
            .filter(client__isnull=False, client__gt='', total_amount__gt=0)
            .order_by('-total_amount')
        )
        
        total_amount = sum(c['total_amount'] for c in clients)
        total_clients = len(clients)
        
        if total_amount == 0:
            return {'A': [], 'B': [], 'C': [], 'total_clients': 0, 'total_amount': 0}
        
        # Правильное распределение по клиентам (а не по сумме!)
        # A: топ-20% клиентов по сумме
        # B: следующие 30% клиентов
        # C: остальные 50% клиентов
        
        a_count = max(1, int(total_clients * 0.2))  # 20% клиентов
        b_count = int(total_clients * 0.3)  # 30% клиентов
        c_count = total_clients - a_count - b_count  # остальные 50%
        
        a_clients = clients[:a_count]
        b_clients = clients[a_count:a_count + b_count]
        c_clients = clients[a_count + b_count:]
        
        # Считаем сумму по каждой категории
        a_amount = sum(c['total_amount'] for c in a_clients)
        b_amount = sum(c['total_amount'] for c in b_clients)
        c_amount = sum(c['total_amount'] for c in c_clients)
        
        return {
            'A': a_clients,
            'B': b_clients,
            'C': c_clients,
            'total_clients': total_clients,
            'total_amount': total_amount,
            'a_count': len(a_clients),
            'b_count': len(b_clients),
            'c_count': len(c_clients),
            'a_percent_of_clients': (len(a_clients) / total_clients * 100) if total_clients > 0 else 0,
            'b_percent_of_clients': (len(b_clients) / total_clients * 100) if total_clients > 0 else 0,
            'c_percent_of_clients': (len(c_clients) / total_clients * 100) if total_clients > 0 else 0,
            'a_percent_of_amount': (a_amount / total_amount * 100) if total_amount > 0 else 0,
            'b_percent_of_amount': (b_amount / total_amount * 100) if total_amount > 0 else 0,
            'c_percent_of_amount': (c_amount / total_amount * 100) if total_amount > 0 else 0,
        }
    
    def get_high_risk_clients(self, limit=10, debt_threshold_percent=50):
        """
        Клиенты с высоким риском (большой долг)
        debt_threshold_percent: порог долга в процентах от суммы заказов
        """
        first_day_of_year = self.today.replace(month=1, day=1)
        
        clients = (
            self._base_queryset()
            .filter(date_from__gte=first_day_of_year)
            .values('client', 'manager')
            .annotate(
                total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
                paid_amount=Coalesce(Sum('cash_pmts', output_field=FloatField()), 0.0),
                orders_count=Count('order_id'),
            )
            .filter(client__isnull=False, client__gt='', total_amount__gt=0)
            .order_by('-total_amount')
        )
        
        # Риск считается по долгу за уже отгруженный товар
        parts = self._debt_parts(first_day_of_year, keys=("client", "manager"))
        result = []
        for c in clients:
            p = parts.get((c['client'], c['manager']), {"shipped": 0.0, "ship_debt": 0.0, "open_unpaid": 0.0})
            debt = p['ship_debt']
            debt_percent = (debt / p['shipped'] * 100) if p['shipped'] > 0 else 0
            
            if debt_percent >= debt_threshold_percent and debt > 0:
                result.append({
                    'client': c['client'],
                    'manager': c['manager'],
                    'total_amount': c['total_amount'],
                    'shipped_amount': p['shipped'],
                    'paid_amount': c['paid_amount'],
                    'debt': debt,
                    'debt_percent': debt_percent,
                    'orders_count': c['orders_count'],
                })
        
        # Сортируем по сумме долга
        result.sort(key=lambda x: x['debt'], reverse=True)
        
        return result[:limit]
    
    def get_clients_by_manager(self, limit=10):
        """
        Распределение клиентов по менеджерам
        """
        clients_by_manager = (
            self._base_queryset()
            .filter(date_from__gte=self.today.replace(month=1, day=1))
            .values('manager')
            .annotate(
                clients_count=Count('client', distinct=True),
                total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
                orders_count=Count('order_id'),
            )
            .filter(manager__isnull=False, manager__gt='')
            .order_by('-clients_count')[:limit]
        )
        
        result = []
        for m in clients_by_manager:
            result.append({
                'manager': m['manager'],
                'clients_count': m['clients_count'],
                'total_amount': m['total_amount'],
                'orders_count': m['orders_count'],
                'avg_per_client': m['total_amount'] / m['clients_count'] if m['clients_count'] > 0 else 0,
            })
        
        return result
    
    def get_new_clients_trend(self, months=6):
        """
        Динамика появления новых клиентов по месяцам
        """
        from django.db.models.functions import TruncMonth
        
        first_date = self.today.replace(day=1)
        # Отступаем на months месяцев назад
        from dateutil.relativedelta import relativedelta
        start_date = first_date - relativedelta(months=months-1)
        
        # Получаем первых заказы клиентов
        first_orders = (
            self._base_queryset()
            .values('client')
            .annotate(first_order_date=Coalesce(Min('date_from'), F('date_from')))
            .filter(first_order_date__gte=start_date)
        )
        
        # Группируем по месяцам
        from django.db.models import Min
        
        monthly_new = (
            self._base_queryset()
            .filter(date_from__gte=start_date)
            .values('client')
            .annotate(first_order=Min('date_from'))
            .values('first_order')
            .annotate(new_clients=Count('client', distinct=True))
            .order_by('first_order')
        )
        
        result = []
        current = start_date
        while current <= self.today:
            month_name = self._get_month_name(current)
            month_new = 0
            
            for m in monthly_new:
                if m['first_order'] and m['first_order'].year == current.year and m['first_order'].month == current.month:
                    month_new = m['new_clients']
                    break
            
            result.append({
                'month': current,
                'month_name': month_name,
                'new_clients': month_new,
            })
            
            current += relativedelta(months=1)
        
        return result
    
    def _get_month_name(self, date_obj):
        """Возвращает название месяца"""
        month_names = {
            1: "ЯНВ", 2: "ФЕВ", 3: "МАР", 4: "АПР",
            5: "МАЙ", 6: "ИЮН", 7: "ИЮЛ", 8: "АВГ",
            9: "СЕН", 10: "ОКТ", 11: "НОЯ", 12: "ДЕК"
        }
        return f"{month_names[date_obj.month]} {date_obj.year}"
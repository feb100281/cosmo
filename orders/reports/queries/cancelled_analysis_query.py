# orders/reports/queries/cancelled_analysis_query.py
from django.db.models import Sum, Count, Q, F, OuterRef, Subquery, CharField, Value, FloatField, DecimalField
from django.db.models.functions import Coalesce, TruncMonth, TruncDate, Cast
from orders.models import MV_Orders, MV_OrdersItems
from datetime import datetime, timedelta
from decimal import Decimal


class CancelledAnalysisQueries:
    """Запросы для анализа отменённых заказов"""
    
    def __init__(self, request=None):
        self.request = request
        self.today = datetime.now().date()
        self.first_day_month = self.today.replace(day=1)
        self.first_day_year = self.today.replace(month=1, day=1)
        
        # Получаем параметры периода из request.GET
        self.start_date = None
        self.end_date = None
        
        if request and hasattr(request, 'GET'):
            # Получаем даты из параметров запроса
            start_date_str = request.GET.get('start_date')
            end_date_str = request.GET.get('end_date')
            
            if start_date_str:
                try:
                    self.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            if end_date_str:
                try:
                    self.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Если даты не указаны, берём начало года
            if not self.start_date:
                self.start_date = self.first_day_year
            
            if not self.end_date:
                self.end_date = self.today
    
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
    
    def get_cancelled_orders_detail(self, start_date=None, end_date=None):
        """
        Получает детальную информацию по отменённым заказам
        
        Args:
            start_date: дата начала периода (YYYY-MM-DD) - переопределяет request
            end_date: дата окончания периода (YYYY-MM-DD) - переопределяет request
        """
        
        # Используем переданные параметры или из request
        if start_date:
            start = start_date
        else:
            start = self.start_date
        
        if end_date:
            end = end_date
        else:
            end = self.end_date
        
        # Базовый запрос для отменённых заказов
        queryset = MV_Orders.objects.filter(
            Q(change_status='Отменен') | Q(status='Отменен')
        )
        
        # Фильтр по дате (используем date_from - дату создания заказа)
        if start:
            queryset = queryset.filter(date_from__gte=start)
        if end:
            queryset = queryset.filter(date_from__lte=end)
        
        # Подзапрос для получения причины отмены из первого товара
        reason_subquery = MV_OrdersItems.objects.filter(
            order=OuterRef('pk')
        ).exclude(
            cancellation_reason__isnull=True
        ).exclude(
            cancellation_reason__exact=''
        ).values('cancellation_reason')[:1]
        
        # ВАЖНО: Приводим все числовые поля к одному типу (DecimalField)
        # Используем Coalesce с Cast для приведения типов
        cancelled_amount_expr = Coalesce(
            Cast(Sum('amount_cancelled'), output_field=DecimalField(max_digits=15, decimal_places=2)),
            Value(0, output_field=DecimalField(max_digits=15, decimal_places=2))
        )
        
        order_qty_expr = Coalesce(
            Cast(Sum('order_qty'), output_field=DecimalField(max_digits=15, decimal_places=0)),
            Value(0, output_field=DecimalField(max_digits=15, decimal_places=0))
        )
        
        paid_amount_expr = Coalesce(
            Cast(Sum('cash_pmts'), output_field=DecimalField(max_digits=15, decimal_places=2)),
            Value(0, output_field=DecimalField(max_digits=15, decimal_places=2))
        )
        
        # Получаем данные
        orders = queryset.values(
            'order_id', 'order_name', 'number', 'client', 'manager', 
            'store', 'date_from', 'update_at', 'status', 'change_status'
        ).annotate(
            cancelled_amount=cancelled_amount_expr,
            order_qty=order_qty_expr,
            paid_amount=paid_amount_expr,
            cancellation_reason=Coalesce(
                Subquery(reason_subquery, output_field=CharField()),
                Value('Не указана', output_field=CharField())
            )
        ).filter(
            cancelled_amount__gt=0  # Только заказы с суммой отмены > 0
        ).order_by('-cancelled_amount')
        
        # Конвертируем Decimal в float для JSON-сериализации
        result = []
        for order in orders:
            order_dict = dict(order)
            order_dict['cancelled_amount'] = float(order_dict.get('cancelled_amount', 0))
            order_dict['order_qty'] = float(order_dict.get('order_qty', 0))
            order_dict['paid_amount'] = float(order_dict.get('paid_amount', 0))
            result.append(order_dict)
        
        return result
    
    def get_cancelled_summary(self, orders_data):
        """
        Получает сводную статистику по отменам
        
        Args:
            orders_data: список отменённых заказов из get_cancelled_orders_detail
        """
        if not orders_data:
            return {
                'total_orders': 0,
                'total_cancelled_amount': 0,
                'total_paid_amount': 0,
                'total_qty': 0,
                'unique_clients': 0,
                'unique_managers': 0,
                'unique_stores': 0,
                'avg_cancelled_amount': 0,
                'period_start': self.start_date,
                'period_end': self.end_date,
            }
        
        total_orders = len(orders_data)
        total_cancelled = sum(self._safe_float(o.get('cancelled_amount', 0)) for o in orders_data)
        total_paid = sum(self._safe_float(o.get('paid_amount', 0)) for o in orders_data)
        total_qty = sum(self._safe_int(o.get('order_qty', 0)) for o in orders_data)
        
        unique_clients = len(set(o.get('client', '') for o in orders_data if o.get('client')))
        unique_managers = len(set(o.get('manager', '') for o in orders_data if o.get('manager')))
        unique_stores = len(set(o.get('store', '') for o in orders_data if o.get('store')))
        
        # Даты периода
        dates = [o.get('date_from') for o in orders_data if o.get('date_from')]
        period_start = min(dates) if dates else self.start_date
        period_end = max(dates) if dates else self.end_date
        
        return {
            'total_orders': total_orders,
            'total_cancelled_amount': total_cancelled,
            'total_paid_amount': total_paid,
            'total_qty': total_qty,
            'unique_clients': unique_clients,
            'unique_managers': unique_managers,
            'unique_stores': unique_stores,
            'avg_cancelled_amount': total_cancelled / total_orders if total_orders > 0 else 0,
            'period_start': period_start,
            'period_end': period_end,
        }
    
    def get_cancelled_by_reason(self, orders_data):
        """
        Группировка отмен по причинам
        
        Args:
            orders_data: список отменённых заказов
        """
        reasons = {}
        
        for order in orders_data:
            reason = order.get('cancellation_reason', 'Не указана')
            if not reason or reason == '':
                reason = 'Не указана'
            
            if reason not in reasons:
                reasons[reason] = {
                    'count': 0,
                    'amount': 0,
                    'orders': []
                }
            
            reasons[reason]['count'] += 1
            reasons[reason]['amount'] += self._safe_float(order.get('cancelled_amount', 0))
            reasons[reason]['orders'].append(order)
        
        # Преобразуем в список и сортируем по сумме
        result = []
        for reason, data in reasons.items():
            result.append({
                'reason': reason,
                'count': data['count'],
                'amount': data['amount'],
                'avg_amount': data['amount'] / data['count'] if data['count'] > 0 else 0,
            })
        
        return sorted(result, key=lambda x: x['amount'], reverse=True)
    
    def get_cancelled_by_manager(self, orders_data):
        """
        Группировка отмен по менеджерам
        """
        managers = {}
        
        for order in orders_data:
            manager = order.get('manager', 'Не указан')
            if not manager or manager == '':
                manager = 'Не указан'
            
            if manager not in managers:
                managers[manager] = {
                    'count': 0,
                    'amount': 0,
                    'orders_count': 0
                }
            
            managers[manager]['count'] += 1
            managers[manager]['amount'] += self._safe_float(order.get('cancelled_amount', 0))
        
        # Преобразуем в список и сортируем по сумме
        result = []
        for manager, data in managers.items():
            result.append({
                'manager': manager,
                'orders_count': data['count'],
                'total_amount': data['amount'],
                'avg_amount': data['amount'] / data['count'] if data['count'] > 0 else 0,
            })
        
        return sorted(result, key=lambda x: x['total_amount'], reverse=True)
    
    def get_cancelled_by_client(self, orders_data, limit=10):
        """
        Топ клиентов по сумме отмен
        """
        clients = {}
        
        for order in orders_data:
            client = order.get('client', 'Не указан')
            if not client or client == '':
                client = 'Не указан'
            
            if client not in clients:
                clients[client] = {
                    'count': 0,
                    'amount': 0,
                    'orders': []
                }
            
            clients[client]['count'] += 1
            clients[client]['amount'] += self._safe_float(order.get('cancelled_amount', 0))
        
        # Преобразуем в список и сортируем по сумме
        result = []
        for client, data in clients.items():
            result.append({
                'client': client,
                'orders_count': data['count'],
                'total_amount': data['amount'],
                'avg_amount': data['amount'] / data['count'] if data['count'] > 0 else 0,
            })
        
        return sorted(result, key=lambda x: x['total_amount'], reverse=True)[:limit]
    
    def get_cancelled_trends(self, months=6):
        """
        Тренды отмен по месяцам
        
        Args:
            months: количество месяцев для анализа
        """
        # Получаем отменённые заказы за последние N месяцев
        start_date = self.today - timedelta(days=months*30)
        
        queryset = MV_Orders.objects.filter(
            Q(change_status='Отменен') | Q(status='Отменен'),
            date_from__gte=start_date,
            date_from__lte=self.today
        ).annotate(
            month=TruncMonth('date_from')
        ).values('month').annotate(
            orders_count=Count('order_id'),
            total_amount=Cast(Coalesce(Sum('amount_cancelled'), Value(0)), output_field=DecimalField(max_digits=15, decimal_places=2)),
            total_qty=Cast(Coalesce(Sum('order_qty'), Value(0)), output_field=DecimalField(max_digits=15, decimal_places=0))
        ).order_by('month')
        
        # Конвертируем Decimal в float для сериализации
        result = []
        for item in queryset:
            item_dict = dict(item)
            if item_dict['month']:
                item_dict['month'] = item_dict['month'].strftime('%Y-%m-%d')
            item_dict['total_amount'] = float(item_dict.get('total_amount', 0))
            item_dict['total_qty'] = float(item_dict.get('total_qty', 0))
            result.append(item_dict)
        
        return result
    
    def get_top_cancelled_orders(self, orders_data, limit=50):
        """
        Топ отменённых заказов по сумме
        """
        # Сортируем и возвращаем топ
        sorted_orders = sorted(orders_data, key=lambda x: self._safe_float(x.get('cancelled_amount', 0)), reverse=True)
        return sorted_orders[:limit]
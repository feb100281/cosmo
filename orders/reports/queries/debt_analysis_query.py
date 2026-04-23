# orders/reports/queries/debt_analysis_query.py
from django.db.models import Q, Sum, F, FloatField, Value, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone
from orders.models import MV_Orders
from datetime import timedelta


class DebtAnalysisQueries:
    """Запросы для анализа дебиторской задолженности"""
    
    def get_orders_with_debt(self, days_overdue=None):
        """
        Получение всех заказов с задолженностью (остаток к оплате > 0)
        """
        # Базовый запрос: остаток к оплате > 0
        qs = MV_Orders.objects.filter(
            Q(amount_active__gt=F('cash_pmts') + 0.01) |
            Q(cash_pmts__isnull=True)
        )
        
        # Фильтр по дате создания (если нужна просрочка)
        if days_overdue:
            cutoff_date = timezone.now().date() - timedelta(days=days_overdue)
            qs = qs.filter(date_from__lte=cutoff_date)
        
        # Получаем данные
        orders = []
        for order in qs:
            amount_active = float(order.amount_active or 0)
            cash_pmts = float(order.cash_pmts or 0)
            remaining_debt = max(0, amount_active - cash_pmts)
            debt_percentage = (remaining_debt / amount_active * 100) if amount_active > 0 else 0
            
            orders.append({
                'order_id': order.order_id,
                'order_name': order.order_name or '',
                'number': order.number or '',
                'date_from': order.date_from,
                'update_at': order.update_at,
                'status': order.status or '',
                'change_status': order.change_status or '',
                'client': order.client or '',
                'manager': order.manager or '',
                'store': order.store or '',
                'order_qty': float(order.order_qty or 0),
                'order_amount': float(order.order_amount or 0),
                'amount_active': amount_active,
                'cash_pmts': cash_pmts,
                'cash_recieved': float(order.cash_recieved or 0),
                'cash_returned': float(order.cash_returned or 0),
                'payment_dates': order.payment_dates,
                'remaining_debt': remaining_debt,
                'debt_percentage': debt_percentage,
            })
        
        # Сортируем по сумме долга
        orders.sort(key=lambda x: x['remaining_debt'], reverse=True)
        return orders
    
    def get_debt_summary(self):
        """Получение сводной статистики по задолженности"""
        orders = self.get_orders_with_debt()
        
        if not orders:
            return {
                'total_debt_orders': 0,
                'total_debt_amount': 0.0,
                'avg_debt': 0.0,
                'max_debt': 0.0,
                'total_order_amount': 0.0,
                'total_paid': 0.0,
                'collection_rate': 0.0,
                'unique_clients': 0,
                'unique_managers': 0,
                'status_breakdown': [],
                'top_debtors': [],
                'top_managers_debt': [],
                'old_debts': {'count': 0, 'amount': 0.0},
                'aging_buckets': self._get_empty_aging_buckets(),
            }
        
        total_debt_amount = sum(o['remaining_debt'] for o in orders)
        total_order_amount = sum(o['amount_active'] for o in orders)
        total_paid = sum(o['cash_pmts'] for o in orders)
        
        # Статус брейкдаун
        status_breakdown = {}
        for order in orders:
            status = order['status']
            if status not in status_breakdown:
                status_breakdown[status] = {'count': 0, 'total_debt': 0.0}
            status_breakdown[status]['count'] += 1
            status_breakdown[status]['total_debt'] += order['remaining_debt']
        
        # Топ должников
        clients_debt = {}
        for order in orders:
            client = order['client']
            if client:
                if client not in clients_debt:
                    clients_debt[client] = {'total_debt': 0.0, 'orders_count': 0}
                clients_debt[client]['total_debt'] += order['remaining_debt']
                clients_debt[client]['orders_count'] += 1
        
        top_debtors = sorted(
            [{'client': k, 'total_debt': v['total_debt'], 'orders_count': v['orders_count']} 
             for k, v in clients_debt.items()],
            key=lambda x: x['total_debt'],
            reverse=True
        )[:10]
        
        # Топ менеджеров по долгам
        managers_debt = {}
        for order in orders:
            manager = order['manager']
            if manager:
                if manager not in managers_debt:
                    managers_debt[manager] = {'total_debt': 0.0, 'orders_count': 0}
                managers_debt[manager]['total_debt'] += order['remaining_debt']
                managers_debt[manager]['orders_count'] += 1
        
        top_managers = sorted(
            [{'manager': k, 'total_debt': v['total_debt'], 'orders_count': v['orders_count']} 
             for k, v in managers_debt.items()],
            key=lambda x: x['total_debt'],
            reverse=True
        )[:10]
        
        # Старые долги (>90 дней)
        today = timezone.now().date()
        old_debts_count = 0
        old_debts_amount = 0.0
        for order in orders:
            if order['date_from']:
                order_date = order['date_from'].date() if hasattr(order['date_from'], 'date') else order['date_from']
                age = (today - order_date).days
                if age > 90 and order['remaining_debt'] > 0:
                    old_debts_count += 1
                    old_debts_amount += order['remaining_debt']
        
        # Возрастная структура
        aging_buckets = self._get_aging_buckets(orders)
        
        return {
            'total_debt_orders': len(orders),
            'total_debt_amount': total_debt_amount,
            'avg_debt': total_debt_amount / len(orders) if orders else 0,
            'max_debt': max(o['remaining_debt'] for o in orders) if orders else 0,
            'total_order_amount': total_order_amount,
            'total_paid': total_paid,
            'collection_rate': (total_paid / total_order_amount * 100) if total_order_amount > 0 else 0,
            'unique_clients': len(clients_debt),
            'unique_managers': len(managers_debt),
            'status_breakdown': [{'status': k, 'count': v['count'], 'total_debt': v['total_debt']} 
                                for k, v in status_breakdown.items()],
            'top_debtors': top_debtors,
            'top_managers_debt': top_managers,
            'old_debts': {'count': old_debts_count, 'amount': old_debts_amount},
            'aging_buckets': aging_buckets,
        }
    
    def _get_empty_aging_buckets(self):
        """Пустые buckets для возрастной структуры"""
        return {
            '0-30 дней': {'count': 0, 'amount': 0.0},
            '31-60 дней': {'count': 0, 'amount': 0.0},
            '61-90 дней': {'count': 0, 'amount': 0.0},
            '91-180 дней': {'count': 0, 'amount': 0.0},
            'более 180 дней': {'count': 0, 'amount': 0.0},
        }
    
    def _get_aging_buckets(self, orders):
        """Разбивка долгов по возрастным категориям"""
        today = timezone.now().date()
        
        buckets = self._get_empty_aging_buckets()
        
        for order in orders:
            if order['date_from'] and order['remaining_debt'] > 0:
                # Приводим к date
                if hasattr(order['date_from'], 'date'):
                    order_date = order['date_from'].date()
                else:
                    order_date = order['date_from']
                
                age = (today - order_date).days
                debt = order['remaining_debt']
                
                if age <= 30:
                    buckets['0-30 дней']['count'] += 1
                    buckets['0-30 дней']['amount'] += debt
                elif age <= 60:
                    buckets['31-60 дней']['count'] += 1
                    buckets['31-60 дней']['amount'] += debt
                elif age <= 90:
                    buckets['61-90 дней']['count'] += 1
                    buckets['61-90 дней']['amount'] += debt
                elif age <= 180:
                    buckets['91-180 дней']['count'] += 1
                    buckets['91-180 дней']['amount'] += debt
                else:
                    buckets['более 180 дней']['count'] += 1
                    buckets['более 180 дней']['amount'] += debt
        
        return buckets
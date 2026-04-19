# orders/reports/queries/dashboard_queries.py
from django.db.models import Sum, Count, Q, Avg, F
from django.db.models.functions import TruncMonth, TruncDate, ExtractDay
from orders.models import MV_Orders, OrdersCF
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class DashboardQueries:
    def __init__(self, request=None):
        self.request = request
        self.today = datetime.now().date()
        self.first_day_month = self.today.replace(day=1)
        self.first_day_year = self.today.replace(month=1, day=1)
    
    def get_all_orders(self):
        """Получить все заказы"""
        return MV_Orders.objects.all().order_by('-date_from')
    
    def get_orders_with_metrics(self):
        """Получить заказы с метриками"""
        orders = MV_Orders.objects.all().values(
            'order_name', 'number', 'date_from', 'update_at',
            'status', 'client', 'manager', 'store', 'change_status',
            'qty_ordered', 'qty_cancelled', 'order_qty',
            'order_amount', 'amount_delivery', 'amount_cancelled',
            'amount_active', 'cash_recieved', 'cash_returned',
            'cash_pmts', 'shiped', 'returned', 'shiped_qty',
            'shiped_amount', 'returned_amount', 'total_shiped_amount',
            'shiped_delivery_amount'
        ).order_by('-date_from')
        
        # Преобразуем в список для удобства
        return list(orders)
    
    def get_status_summary(self):
        """Сводка по статусам (все заказы)"""
        return MV_Orders.objects.values('status').annotate(
            count=Count('order_id'),
            total_amount=Sum('amount_active'),
            total_qty=Sum('order_qty'),
            avg_amount=Avg('amount_active')
        ).order_by('-total_amount')
    
    def get_manager_summary(self):
        """Сводка по менеджерам"""
        return MV_Orders.objects.values('manager').annotate(
            orders_count=Count('order_id'),
            total_amount=Sum('amount_active'),
            avg_check=Avg('amount_active'),
            total_qty=Sum('order_qty'),
            debt_amount=Sum(F('amount_active') - F('cash_pmts'))
        ).filter(manager__isnull=False).exclude(manager='').order_by('-total_amount')
    
    def get_client_summary(self):
        """Сводка по клиентам"""
        return MV_Orders.objects.values('client').annotate(
            orders_count=Count('order_id'),
            total_amount=Sum('amount_active'),
            avg_check=Avg('amount_active')
        ).filter(client__isnull=False).exclude(client='').order_by('-total_amount')[:50]
    
    def get_active_orders_stats(self):
        """Статистика по ВСЕМ активным заказам (К выполнению / В резерве, На согласовании)"""
        from django.db.models import Q, Sum, F
        
        # Заказы со статусом "К выполнению" или "В резерве"
        to_do_orders = MV_Orders.objects.filter(
            Q(status='К выполнению') | Q(status='К выполнению / В резерве')
        )
        
        # Заказы со статусом "На согласовании"
        pending_orders = MV_Orders.objects.filter(status='На согласовании')
        
        # Статистика по "К выполнению" (ВСЕ заказы, не только за месяц)
        to_do_stats = to_do_orders.aggregate(
            count=Count('order_id'),
            qty=Sum('order_qty'),
            paid=Sum('cash_pmts'),
            shipped=Sum('shiped_qty'),
            amount=Sum('amount_active'),
            debt=Sum(F('amount_active') - F('cash_pmts'))
        )
        
        # Статистика по "На согласовании" (ВСЕ заказы)
        pending_stats = pending_orders.aggregate(
            count=Count('order_id'),
            qty=Sum('order_qty'),
            paid=Sum('cash_pmts'),
            shipped=Sum('shiped_qty'),
            amount=Sum('amount_active'),
            debt=Sum(F('amount_active') - F('cash_pmts'))
        )
        
        # Общая статистика по всем активным заказам
        all_active_orders = MV_Orders.objects.filter(
            Q(status='К выполнению / В резерве')| Q(status='На согласовании')
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
            # Все активные заказы (итого)
            'total_active_count': all_active_stats.get('count', 0) or 0,
            'total_active_qty': float(all_active_stats.get('qty', 0) or 0),
            'total_active_paid': float(all_active_stats.get('paid', 0) or 0),
            'total_active_shipped': float(all_active_stats.get('shipped', 0) or 0),
            'total_active_amount': float(all_active_stats.get('amount', 0) or 0),
            'total_active_remaining_qty': float((all_active_stats.get('qty', 0) or 0) - (all_active_stats.get('shipped', 0) or 0)),
            'total_active_debt': float(all_active_stats.get('debt', 0) or 0),
            
            # К выполнению / В резерве
            'to_do_count': to_do_stats.get('count', 0) or 0,
            'to_do_qty': float(to_do_stats.get('qty', 0) or 0),
            'to_do_paid': float(to_do_stats.get('paid', 0) or 0),
            'to_do_shipped': float(to_do_stats.get('shipped', 0) or 0),
            'to_do_amount': float(to_do_stats.get('amount', 0) or 0),
            'to_do_remaining_qty': float((to_do_stats.get('qty', 0) or 0) - (to_do_stats.get('shipped', 0) or 0)),
            'to_do_debt': float(to_do_stats.get('debt', 0) or 0),
            
            # На согласовании
            'pending_count': pending_stats.get('count', 0) or 0,
            'pending_qty': float(pending_stats.get('qty', 0) or 0),
            'pending_paid': float(pending_stats.get('paid', 0) or 0),
            'pending_shipped': float(pending_stats.get('shipped', 0) or 0),
            'pending_amount': float(pending_stats.get('amount', 0) or 0),
            'pending_remaining_qty': float((pending_stats.get('qty', 0) or 0) - (pending_stats.get('shipped', 0) or 0)),
            'pending_debt': float(pending_stats.get('debt', 0) or 0),
        }
    
    
    def get_delivery_metrics(self):
        """Метрики по доставке"""
        return MV_Orders.objects.aggregate(
            total_delivery_amount=Sum('amount_delivery'),
            total_shipped_delivery=Sum('shiped_delivery_amount'),
            delivery_orders_count=Count('order_id', filter=Q(amount_delivery__gt=0)),
            avg_delivery=Avg('amount_delivery', filter=Q(amount_delivery__gt=0))
        )
    
    def get_changes_analysis(self):
        """Анализ изменений в заказах"""
        return MV_Orders.objects.values('change_status').annotate(
            count=Count('order_id'),
            total_amount=Sum('amount_active'),
            total_cancelled_amount=Sum('amount_cancelled')
        ).order_by('-count')
    
    def get_payment_analysis(self):
        """Анализ оплат"""
        # Оплаты из OrdersCF
        payments = OrdersCF.objects.filter(
            oper_type__in=['Оплата', 'Возврат']
        ).aggregate(
            total_payments=Sum('amount', filter=Q(oper_type='Оплата')),
            total_returns=Sum('amount', filter=Q(oper_type='Возврат'))
        )
        
        # Структура оплат по типам
        payment_structure = OrdersCF.objects.values('oper_type').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        return {
            'totals': payments,
            'structure': list(payment_structure)
        }
    
    def get_monthly_trends(self):
        """Тренды по месяцам"""
        monthly = MV_Orders.objects.annotate(
            month=TruncMonth('date_from')
        ).values('month').annotate(
            orders_count=Count('order_id'),
            total_amount=Sum('amount_active'),
            total_paid=Sum('cash_pmts'),
            avg_check=Avg('amount_active')
        ).order_by('month')
        
        return list(monthly)
    
    def get_top_debtors(self, limit=10):
        """Топ должников (активные заказы с долгом) - ВСЕ активные заказы"""
        return MV_Orders.objects.filter(
            amount_active__gt=F('cash_pmts')
        ).annotate(
            debt=F('amount_active') - F('cash_pmts')
        ).values(
            'client', 'order_name', 'number', 'amount_active',
            'cash_pmts', 'debt', 'status', 'manager'
        ).filter(debt__gt=0).order_by('-debt')[:limit]
        
    
    
    def get_completed_orders_stats(self):
        """Статистика по УСПЕШНО ЗАКРЫТЫМ заказам (status='Закрыт', не отменён)"""
        from django.db.models import Q
        
        # Успешно закрытые заказы
        completed = MV_Orders.objects.filter(
            status='Закрыт'
        ).exclude(
            Q(change_status='Отменен') | Q(status='Отменен')
        )
        
        # MTD (с начала месяца)
        mtd_completed = completed.filter(
            date_from__gte=self.first_day_month,
            date_from__lte=self.today
        ).aggregate(
            count=Count('order_id'),
            amount=Sum('amount_active')
        )
        
        # YTD (с начала года)
        ytd_completed = completed.filter(
            date_from__gte=self.first_day_year,
            date_from__lte=self.today
        ).aggregate(
            count=Count('order_id'),
            amount=Sum('amount_active')
        )
        
        return {
            'total_count': completed.count(),
            'total_amount': float(completed.aggregate(total=Sum('amount_active'))['total'] or 0),
            'mtd_count': mtd_completed['count'] or 0,
            'mtd_amount': float(mtd_completed['amount'] or 0),
            'ytd_count': ytd_completed['count'] or 0,
            'ytd_amount': float(ytd_completed['amount'] or 0),
        }


    def get_cancelled_orders_stats(self):
        """Статистика по ОТМЕНЁННЫМ заказам"""
        from django.db.models import Q
        
        # Отменённые заказы
        cancelled = MV_Orders.objects.filter(
            Q(change_status='Отменен') 
        )
        
        # YTD (с начала года)
        ytd_cancelled = cancelled.filter(
            date_from__gte=self.first_day_year,
            date_from__lte=self.today
        ).aggregate(
            count=Count('order_id'),
            amount=Sum('amount_cancelled')
        )
        
        return {
            'total_count': cancelled.count(),
            'total_amount': float(cancelled.aggregate(total=Sum('amount_cancelled'))['total'] or 0),
            'ytd_count': ytd_cancelled['count'] or 0,
            'ytd_amount': float(ytd_cancelled['amount'] or 0),
        }
    
    def get_store_summary(self, limit=10):
        """Сводка по магазинам (топ по сумме активных заказов)"""
        return MV_Orders.objects.values('store').annotate(
            orders_count=Count('order_id'),
            total_amount=Sum('amount_active'),
            paid_amount=Sum('cash_pmts'),
            debt=Sum(F('amount_active') - F('cash_pmts')),
            avg_check=Avg('amount_active')
        ).filter(store__isnull=False).exclude(store='').order_by('-total_amount')[:limit]
    

    def get_stuck_orders(self, days_threshold=30):
        """
        Заказы, которые зависли (долго в работе, не отгружены, не оплачены)
        days_threshold - сколько дней заказ считается "зависшим"
        """
        threshold_date = self.today - timedelta(days=days_threshold)
        
        # Получаем заказы, которые подходят под критерии
        stuck_orders_qs = MV_Orders.objects.filter(
            Q(status='К выполнению') | Q(status='К выполнению / В резерве') | Q(status='На согласовании'),
            date_from__lte=threshold_date,
            shiped_qty__lt=F('order_qty')
        )
        
        result = []
        for order in stuck_orders_qs[:20]:
            if not order.date_from:
                continue
            
            # Безопасное преобразование даты
            order_date = order.date_from
            if hasattr(order_date, 'date'):  # Если это datetime
                order_date = order_date.date()
            
            days_stuck = (self.today - order_date).days
            
            order_qty = float(order.order_qty or 0)
            shiped_qty = float(order.shiped_qty or 0)
            amount_active = float(order.amount_active or 0)
            cash_pmts = float(order.cash_pmts or 0)
            
            remaining_amount = amount_active - cash_pmts
            
            if remaining_amount <= 0:
                continue
            
            result.append({
                'order_name': order.order_name or '',
                'number': order.number or '',
                'client': order.client or '',
                'manager': order.manager or '',
                'store': order.store or '',
                'date_from': order.date_from,
                'days_stuck': days_stuck,
                'order_qty': order_qty,
                'shiped_qty': shiped_qty,
                'remaining_qty': order_qty - shiped_qty,
                'amount_active': amount_active,
                'cash_pmts': cash_pmts,
                'remaining_amount': remaining_amount,
                'status': order.status or '',
            })
        
        result.sort(key=lambda x: (-x['days_stuck'], -x['remaining_amount']))
        
        return result
    
    
    def get_top_clients(self, limit=10):
        """Топ клиентов по сумме активных заказов"""
        return MV_Orders.objects.values('client').annotate(
            orders_count=Count('order_id'),
            total_amount=Sum('amount_active'),
            paid_amount=Sum('cash_pmts'),
            debt=Sum(F('amount_active') - F('cash_pmts')),
            avg_check=Avg('amount_active')
        ).filter(client__isnull=False).exclude(client='').order_by('-total_amount')[:limit]
    
    def get_financial_metrics(self):
        """Финансовые метрики (обновлённая версия с исключением отменённых из среднего чека)"""
        metrics = MV_Orders.objects.aggregate(
            total_order_amount=Sum('order_amount'),
            total_delivery=Sum('amount_delivery'),
            total_cancelled=Sum('amount_cancelled'),
            total_active=Sum('amount_active'),
            total_cash_received=Sum('cash_recieved'),
            total_cash_returned=Sum('cash_returned'),
            total_cash_pmts=Sum('cash_pmts'),
            total_shipped=Sum('shiped_amount'),
            total_shipped_delivery=Sum('shiped_delivery_amount'),
            total_returned_amount=Sum('returned_amount'),
            total_debt=Sum(F('amount_active') - F('cash_pmts'))
        )
        completed_stats = self.get_completed_orders_stats()
        cancelled_stats = self.get_cancelled_orders_stats()
        
        # MTD (Month to Date) — только НЕ отменённые заказы
        mtd = MV_Orders.objects.filter(
            date_from__gte=self.first_day_month,
            date_from__lte=self.today
        ).exclude(change_status='Отменен').exclude(status='Отменен').aggregate(
            amount=Sum('amount_active'),
            paid=Sum('cash_pmts'),
            orders=Count('order_id')
        )
        
        # YTD (Year to Date) — только НЕ отменённые
        ytd = MV_Orders.objects.filter(
            date_from__gte=self.first_day_year,
            date_from__lte=self.today
        ).exclude(change_status='Отменен').exclude(status='Отменен').aggregate(
            amount=Sum('amount_active'),
            paid=Sum('cash_pmts'),
            orders=Count('order_id')
        )
        
        # Средний чек (только по не отменённым)
        avg_check_data = MV_Orders.objects.exclude(
            change_status='Отменен'
        ).exclude(status='Отменен').aggregate(
            avg_check=Avg('amount_active')
        )
        
        # Дебиторская задолженность по ВСЕМ заказам
        debt_orders = MV_Orders.objects.filter(
            amount_active__gt=F('cash_pmts')
        ).aggregate(
            debt_count=Count('order_id'),
            debt_amount=Sum(F('amount_active') - F('cash_pmts'))
        )
        
        active_stats = self.get_active_orders_stats()
  
        
        return {
            'total': metrics,
            'mtd': mtd,
            'ytd': ytd,
            'debt': debt_orders,
            'active_stats': active_stats,
            'completed_stats': completed_stats,
            'cancelled_stats': cancelled_stats,
            'overall_avg_check': avg_check_data['avg_check'] or 0,
        }
        
    
    def get_yesterday_cancelled_details(self):
        """Детализация отмен за вчера с номерами заказов и менеджерами"""
        from django.db.models import Q
        from datetime import datetime, timedelta
        
        yesterday = self.today - timedelta(days=1)
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        yesterday_end = datetime.combine(yesterday, datetime.max.time())
        
        cancelled_yesterday = MV_Orders.objects.filter(
            Q(change_status='Отменен') | Q(status='Отменен'),
            date_from__gte=yesterday_start,
            date_from__lte=yesterday_end
        ).values('order_name', 'number', 'manager', 'amount_active', 'client')
        
        return list(cancelled_yesterday)


    def get_cancelled_stats_ytd(self):
        """
        Статистика по отменённым заказам с начала года
        Отмена: change_status = 'Отменен' 
        """
        from django.db.models import Q
        
        # Отменённые заказы в текущем году
        cancelled_ytd = MV_Orders.objects.filter(
            Q(change_status='Отменен') | Q(status='Отменен'),
            date_from__gte=self.first_day_year,
            date_from__lte=self.today
        )
        
        # Общая статистика
        total_stats = cancelled_ytd.aggregate(
            count=Count('order_id'),
            total_amount=Sum('amount_cancelled'),
            total_qty=Sum('order_qty')
        )
        
        # Топ-5 самых крупных отмен (по сумме)
        top_cancelled = cancelled_ytd.values(
            'order_name', 'number', 'client', 'manager', 'store', 'date_from'
        ).annotate(
            cancelled_amount=Sum('amount_cancelled'),
            cancelled_qty=Sum('order_qty')
        ).order_by('-cancelled_amount')[:5]
        
        # Отмены за вчера
        yesterday = self.today - timedelta(days=1)
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        yesterday_end = datetime.combine(yesterday, datetime.max.time())
        
        cancelled_yesterday = cancelled_ytd.filter(
            date_from__gte=yesterday_start,
            date_from__lte=yesterday_end
        )
        
        # Статистика по вчерашним отменам
        yesterday_stats = cancelled_yesterday.aggregate(
            count=Count('order_id'),
            amount=Sum('amount_cancelled')
        )
        
        # Детализация по вчерашним отменам (заказы и менеджеры)
        yesterday_details = cancelled_yesterday.values(
            'order_name', 'number', 'manager', 'amount_cancelled', 'client', 'store'
        ).order_by('-amount_cancelled')[:10]  # топ-10 по сумме
        
        return {
            'total_count': total_stats['count'] or 0,
            'total_amount': float(total_stats['total_amount'] or 0),
            'total_qty': total_stats['total_qty'] or 0,
            'top_cancelled': list(top_cancelled),
            'yesterday_count': yesterday_stats['count'] or 0,
            'yesterday_amount': float(yesterday_stats['amount'] or 0),
            'yesterday_details': list(yesterday_details),  # <-- ДОБАВЛЕНО
        }

    def get_large_debt_orders(self, limit=5):
        """
        Крупные долги (активные заказы с суммой к оплате > 1 млн ₽)
        """
        from django.db.models import F
        
        large_debts = MV_Orders.objects.filter(
            Q(status='К выполнению') | Q(status='К выполнению / В резерве') | Q(status='На согласовании'),
            amount_active__gt=F('cash_pmts')
        ).annotate(
            debt=F('amount_active') - F('cash_pmts')
        ).filter(
            debt__gt=1000000  # больше 1 млн ₽
        ).values(
            'order_name', 'number', 'client', 'manager', 'store', 'date_from',
            'amount_active', 'cash_pmts', 'debt', 'status'
        ).order_by('-debt')[:limit]
        
        return list(large_debts)
    
    
    


    def get_orders_for_period(self, days_ago=1):
        """
        Получить заказы за указанный день (days_ago=1 - вчера, 2 - позавчера)
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
            'order_name', 'number', 'manager', 'amount_cancelled'
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

    def get_last_days_stats(self, days=1):
        """
        Универсальный метод для получения статистики за последние N дней
        days=1 - вчера, days=2 - позавчера
        """
        result = {}
        
        for i in range(1, days + 1):
            period_data = self.get_orders_for_period(days_ago=i)
            result[f'day_{i}'] = period_data
        
        return result
# orders/reports/queries/executive_queries.py
from django.db.models import Sum, Count, Q, Avg, F, OuterRef, Subquery, CharField, Value
from django.db.models.functions import Coalesce, TruncMonth
from orders.models import MV_Orders, MV_OrdersItems
from datetime import datetime, timedelta


class ExecutiveQueries:
    """Все запросы для Executive Summary - без дублирования"""
    
    def __init__(self, request=None):
        self.request = request
        self.today = datetime.now().date()
        self.first_day_month = self.today.replace(day=1)
        self.first_day_year = self.today.replace(month=1, day=1)
    
    # ============================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================================
    
    def _exclude_cancelled(self, queryset):
        """Исключить отмененные заказы"""
        return queryset.exclude(
            change_status='Отменен'
        ).exclude(
            status='Отменен'
        )
    
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
    
    # ============================================================
    # ОСНОВНЫЕ МЕТОДЫ ДЛЯ EXECUTIVE SHEET
    # ============================================================
    
    def get_financial_metrics(self):
        """Финансовые метрики для Executive Summary"""
        
        # MTD (Month to Date) — только НЕ отменённые
        mtd = self._exclude_cancelled(
            MV_Orders.objects.filter(
                date_from__gte=self.first_day_month,
                date_from__lte=self.today
            )
        ).aggregate(
            amount=Sum('amount_active'),
            paid=Sum('cash_pmts'),
            orders=Count('order_id')
        )
        
        # YTD (Year to Date) — только НЕ отменённые
        ytd = self._exclude_cancelled(
            MV_Orders.objects.filter(
                date_from__gte=self.first_day_year,
                date_from__lte=self.today
            )
        ).aggregate(
            amount=Sum('amount_active'),
            paid=Sum('cash_pmts'),
            orders=Count('order_id')
        )
        
        # Активные заказы
        active_stats = self.get_active_orders_stats()
        
        # Завершенные заказы
        completed_stats = self.get_completed_orders_stats()
        
        # Отмененные заказы
        cancelled_stats = self.get_cancelled_orders_stats()
        
        
        # Статистика за последние дни
        last_days_stats = self.get_last_days_stats(days=2)
        
        # Крупные долги
        large_debts = self.get_large_debt_orders(limit=6)
        
        return {
            'mtd': {
                'amount': float(mtd.get('amount') or 0),
                'paid': float(mtd.get('paid') or 0),
                'orders': mtd.get('orders') or 0,
            },
            'ytd': {
                'amount': float(ytd.get('amount') or 0),
                'paid': float(ytd.get('paid') or 0),
                'orders': ytd.get('orders') or 0,
            },
            'active_stats': active_stats,
            'completed_stats': completed_stats,
            'cancelled_stats': cancelled_stats,
            'last_days_stats': last_days_stats,
            'large_debts': large_debts,
        }
    
    def get_active_orders_stats(self):
        """Статистика по активным заказам (К выполнению, На согласовании)"""
        
        # К выполнению / В резерве
        to_do_orders = MV_Orders.objects.filter(
            Q(status='К выполнению') | Q(status='К выполнению / В резерве')
        )
        
        # На согласовании
        pending_orders = MV_Orders.objects.filter(status='На согласовании')
        
        # Все активные
        all_active = MV_Orders.objects.filter(
            Q(status='К выполнению / В резерве') | 
            Q(status='На согласовании')
        )
        
        def get_stats(queryset):
            stats = queryset.aggregate(
                count=Count('order_id'),
                qty=Sum('order_qty'),
                paid=Sum('cash_pmts'),
                shipped=Sum('shiped_qty'),
                amount=Sum('amount_active'),
            )
            debt = queryset.aggregate(
                debt=Sum(F('amount_active') - F('cash_pmts'))
            )['debt'] or 0
            
            return {
                'count': stats.get('count', 0) or 0,
                'qty': float(stats.get('qty', 0) or 0),
                'paid': float(stats.get('paid', 0) or 0),
                'shipped': float(stats.get('shipped', 0) or 0),
                'amount': float(stats.get('amount', 0) or 0),
                'debt': float(debt),
                'remaining_qty': float(
                    (stats.get('qty', 0) or 0) - (stats.get('shipped', 0) or 0)
                ),
            }
        
        to_do = get_stats(to_do_orders)
        pending = get_stats(pending_orders)
        total = get_stats(all_active)
        
        return {
            # Итого
            'total_active_count': total['count'],
            'total_active_qty': total['qty'],
            'total_active_paid': total['paid'],
            'total_active_shipped': total['shipped'],
            'total_active_amount': total['amount'],
            'total_active_remaining_qty': total['remaining_qty'],
            'total_active_debt': total['debt'],
            
            # К выполнению
            'to_do_count': to_do['count'],
            'to_do_qty': to_do['qty'],
            'to_do_paid': to_do['paid'],
            'to_do_shipped': to_do['shipped'],
            'to_do_amount': to_do['amount'],
            'to_do_remaining_qty': to_do['remaining_qty'],
            'to_do_debt': to_do['debt'],
            
            # На согласовании
            'pending_count': pending['count'],
            'pending_qty': pending['qty'],
            'pending_paid': pending['paid'],
            'pending_shipped': pending['shipped'],
            'pending_amount': pending['amount'],
            'pending_remaining_qty': pending['remaining_qty'],
            'pending_debt': pending['debt'],
        }
    
    def get_completed_orders_stats(self):
        """Статистика по успешно закрытым заказам"""
        
        completed = MV_Orders.objects.filter(
            status='Закрыт'
        ).exclude(
            Q(change_status='Отменен') | Q(status='Отменен')
        )
        
        # YTD
        ytd = completed.filter(
            date_from__gte=self.first_day_year,
            date_from__lte=self.today
        ).aggregate(
            count=Count('order_id'),
            amount=Sum('amount_active')
        )
        
        return {
            'ytd_count': ytd.get('count') or 0,
            'ytd_amount': float(ytd.get('amount') or 0),
        }
    
    def get_cancelled_orders_stats(self):
        """Статистика по отменённым заказам"""
        
        cancelled = MV_Orders.objects.filter(
            Q(change_status='Отменен') | Q(status='Отменен')
        )
        
        # YTD
        ytd = cancelled.filter(
            date_from__gte=self.first_day_year,
            date_from__lte=self.today
        ).aggregate(
            count=Count('order_id'),
            amount=Sum('amount_cancelled')
        )
        
        # Топ отмен (с причиной)
        reason_subquery = MV_OrdersItems.objects.filter(
            order=OuterRef('pk')
        ).exclude(
            cancellation_reason__isnull=True
        ).exclude(
            cancellation_reason__exact=''
        ).values('cancellation_reason')[:1]
        
        top_cancelled = cancelled.filter(
            date_from__gte=self.first_day_year
        ).values(
            'order_id', 'order_name', 'number', 'client', 
            'manager', 'store', 'date_from'
        ).annotate(
            cancelled_amount=Sum('amount_cancelled'),
            cancellation_reason=Coalesce(
                Subquery(reason_subquery, output_field=CharField()),
                Value('')
            )
        ).order_by('-cancelled_amount')[:5]
        
        return {
            'total_count': cancelled.count(),
            'total_amount': float(
                cancelled.aggregate(total=Sum('amount_cancelled'))['total'] or 0
            ),
            'ytd_count': ytd.get('count') or 0,
            'ytd_amount': float(ytd.get('amount') or 0),
            'top_cancelled': list(top_cancelled),
        }
    
    
    def get_monthly_trends(self):
        """Тренды по месяцам (только НЕ отмененные заказы)"""
        
        monthly = self._exclude_cancelled(
            MV_Orders.objects.all()
        ).annotate(
            month=TruncMonth('date_from')
        ).values('month').annotate(
            orders_count=Count('order_id'),
            total_amount=Sum('amount_active'),
            total_paid=Sum('cash_pmts'),
            avg_check=Avg('amount_active')
        ).order_by('month')
        
        return list(monthly)
    
    def get_manager_summary(self):
        """Сводка по менеджерам с разбивкой по периодам и отгрузкам"""
        
        # Базовый queryset (не отмененные заказы)
        base_qs = self._exclude_cancelled(MV_Orders.objects.all())
        
        # Сводка за весь период (YTD)
        ytd_summary = base_qs.filter(
            date_from__gte=self.first_day_year,
            date_from__lte=self.today
        ).values('manager').annotate(
            ytd_orders=Count('order_id'),
            ytd_amount=Sum('amount_active'),
            ytd_avg=Avg('amount_active'),
            ytd_qty=Sum('order_qty'),
            ytd_shipped_qty=Sum('shiped_qty'),  # отгружено товаров
            ytd_shipped_amount=Sum('shiped_amount'),  # отгружено на сумму
            ytd_paid=Sum('cash_pmts'),  # оплачено
        )
        
        # Сводка за месяц (MTD)
        mtd_summary = base_qs.filter(
            date_from__gte=self.first_day_month,
            date_from__lte=self.today
        ).values('manager').annotate(
            mtd_orders=Count('order_id'),
            mtd_amount=Sum('amount_active'),
            mtd_avg=Avg('amount_active'),
            mtd_qty=Sum('order_qty'),
            mtd_shipped_qty=Sum('shiped_qty'),
            mtd_shipped_amount=Sum('shiped_amount'),
            mtd_paid=Sum('cash_pmts'),
        )
        
        # Объединяем данные
        managers_data = {}
        
        # Заполняем YTD данные
        for item in ytd_summary:
            manager = item['manager']
            if not manager:
                continue
            managers_data[manager] = {
                'manager': manager,
                'ytd_orders': item['ytd_orders'] or 0,
                'ytd_amount': float(item['ytd_amount'] or 0),
                'ytd_avg': float(item['ytd_avg'] or 0),
                'ytd_qty': float(item['ytd_qty'] or 0),
                'ytd_shipped_qty': float(item['ytd_shipped_qty'] or 0),
                'ytd_shipped_amount': float(item['ytd_shipped_amount'] or 0),
                'ytd_paid': float(item['ytd_paid'] or 0),
                'mtd_orders': 0,
                'mtd_amount': 0,
                'mtd_avg': 0,
                'mtd_qty': 0,
                'mtd_shipped_qty': 0,
                'mtd_shipped_amount': 0,
                'mtd_paid': 0,
            }
        
        # Заполняем MTD данные
        for item in mtd_summary:
            manager = item['manager']
            if not manager or manager not in managers_data:
                continue
            managers_data[manager].update({
                'mtd_orders': item['mtd_orders'] or 0,
                'mtd_amount': float(item['mtd_amount'] or 0),
                'mtd_avg': float(item['mtd_avg'] or 0),
                'mtd_qty': float(item['mtd_qty'] or 0),
                'mtd_shipped_qty': float(item['mtd_shipped_qty'] or 0),
                'mtd_shipped_amount': float(item['mtd_shipped_amount'] or 0),
                'mtd_paid': float(item['mtd_paid'] or 0),
            })
        
        # Сортируем по YTD сумме
        result = sorted(
            managers_data.values(),
            key=lambda x: x['ytd_amount'],
            reverse=True
        )
        
        return result
    
    def get_top_clients(self, limit=5):
        """Топ клиентов по сумме долга"""
        
        return list(
            self._exclude_cancelled(
                MV_Orders.objects.all()
            ).values('client').annotate(
                orders_count=Count('order_id'),
                total_amount=Sum('amount_active'),
                paid_amount=Sum('cash_pmts'),
                debt=Sum(F('amount_active') - F('cash_pmts')),
                avg_check=Avg('amount_active')
            ).filter(
                client__isnull=False
            ).exclude(
                client=''
            ).order_by('-debt')[:limit]  # Сортируем по долгу
        )
    
    def get_large_debt_orders(self, limit=6):
        """Крупные долги (более 1 млн ₽) по конкретным заказам"""
        
        large_debts = MV_Orders.objects.filter(
            Q(status='К выполнению') |
            Q(status='К выполнению / В резерве') |
            Q(status='На согласовании'),
            amount_active__gt=F('cash_pmts')
        ).annotate(
            debt=F('amount_active') - F('cash_pmts')
        ).filter(
            debt__gt=1000000  # больше 1 млн
        ).values(
            'order_name', 'number', 'client', 'manager', 
            'store', 'date_from', 'amount_active', 'cash_pmts', 'debt', 'status'
        ).order_by('-debt')[:limit]
        
        return list(large_debts)
    
    def get_orders_for_period(self, days_ago=1):
        """Статистика за конкретный день (вчера, позавчера и т.д.)"""
        
        target_date = self.today - timedelta(days=days_ago)
        target_start = datetime.combine(target_date, datetime.min.time())
        target_end = datetime.combine(target_date, datetime.max.time())
        
        # Новые заказы (не отмененные)
        new_orders = self._exclude_cancelled(
            MV_Orders.objects.filter(
                date_from__gte=target_start,
                date_from__lte=target_end
            )
        )
        
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
                'count': new_stats.get('count') or 0,
                'amount': float(new_stats.get('amount') or 0),
            },
            'cancelled': {
                'count': cancelled_stats.get('count') or 0,
                'amount': float(cancelled_stats.get('amount') or 0),
                'details': list(cancelled_details),
            }
        }
    
    def get_last_days_stats(self, days=2):
        """Статистика за последние N дней"""
        
        result = {}
        for i in range(1, days + 1):
            period_data = self.get_orders_for_period(days_ago=i)
            result[f'last_{i}_days'] = period_data
        
        return result
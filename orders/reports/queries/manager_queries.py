# orders/reports/queries/manager_queries.py
from django.db.models import Q, Sum, F, FloatField, Count
from django.db.models.functions import Coalesce
from orders.models import MV_Orders
from datetime import datetime


class ManagerQueries:
    """Запросы для листа анализа менеджеров (портфолио)"""

    def __init__(self, request=None):
        self.today = datetime.now().date()
        self.request = request

    def _base_queryset(self):
        """Базовый queryset с исключением отмененных заказов"""
        return MV_Orders.objects.exclude(change_status='Отменен')

    def get_all_managers_summary(self):
        """
        Получение сводки по ВСЕМ менеджерам (MTD и YTD)
        Возвращает список менеджеров с показателями:
        - manager: имя менеджера
        - mtd_orders, mtd_amount, mtd_paid, mtd_shipped, mtd_delivery
        - ytd_orders, ytd_amount, ytd_paid, ytd_shipped, ytd_delivery
        """
        first_day_of_month = self.today.replace(day=1)
        first_day_of_year = self.today.replace(month=1, day=1)

        # Получаем всех менеджеров, у которых есть заказы (исключая отмененные)
        managers_list = (
            self._base_queryset()
            .values('manager')
            .filter(manager__isnull=False, manager__gt='')
            .distinct()
            .order_by('manager')
        )

        result = []

        for manager_item in managers_list:
            manager_name = manager_item['manager']

            # ============================================================
            # MTD статистика (с начала месяца)
            # ============================================================
            mtd_qs = self._base_queryset().filter(
                manager=manager_name,
                date_from__gte=first_day_of_month
            )

            mtd_stats = mtd_qs.aggregate(
                orders_count=Count('order_id'),
                total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
                paid_amount=Coalesce(Sum('cash_pmts', output_field=FloatField()), 0.0),
                shipped_amount=Coalesce(Sum('total_shiped_amount', output_field=FloatField()), 0.0),
                delivery_amount=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
            )

            # ============================================================
            # YTD статистика (с начала года)
            # ============================================================
            ytd_qs = self._base_queryset().filter(
                manager=manager_name,
                date_from__gte=first_day_of_year
            )

            ytd_stats = ytd_qs.aggregate(
                orders_count=Count('order_id'),
                total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
                paid_amount=Coalesce(Sum('cash_pmts', output_field=FloatField()), 0.0),
                shipped_amount=Coalesce(Sum('total_shiped_amount', output_field=FloatField()), 0.0),
                delivery_amount=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
            )

            # Добавляем только если есть хоть какие-то заказы
            if mtd_stats['orders_count'] > 0 or ytd_stats['orders_count'] > 0:
                result.append({
                    'manager': manager_name,
                    # MTD показатели
                    'mtd_orders': mtd_stats['orders_count'],
                    'mtd_amount': mtd_stats['total_amount'],
                    'mtd_paid': mtd_stats['paid_amount'],
                    'mtd_shipped': mtd_stats['shipped_amount'],
                    'mtd_delivery': mtd_stats['delivery_amount'],
                    # YTD показатели
                    'ytd_orders': ytd_stats['orders_count'],
                    'ytd_amount': ytd_stats['total_amount'],
                    'ytd_paid': ytd_stats['paid_amount'],
                    'ytd_shipped': ytd_stats['shipped_amount'],
                    'ytd_delivery': ytd_stats['delivery_amount'],
                })

        # Сортируем по сумме MTD (от большего к меньшему)
        result.sort(key=lambda x: x['mtd_amount'], reverse=True)

        return result

    def get_top_managers_mtd(self, limit=10):
        """
        Получение топ-N менеджеров за месяц (MTD)
        Используется для Executive Summary
        """
        first_day_of_month = self.today.replace(day=1)

        managers = (
            self._base_queryset()
            .filter(date_from__gte=first_day_of_month)
            .values('manager')
            .annotate(
                orders_count=Count('order_id'),
                total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
                paid_amount=Coalesce(Sum('cash_pmts', output_field=FloatField()), 0.0),
                shipped_amount=Coalesce(Sum('total_shiped_amount', output_field=FloatField()), 0.0),
                delivery_amount=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
            )
            .filter(manager__isnull=False, manager__gt='')
            .order_by('-total_amount')[:limit]
        )

        result = []
        for m in managers:
            avg_check = m['total_amount'] / m['orders_count'] if m['orders_count'] > 0 else 0

            result.append({
                'manager': m['manager'],
                'orders_count': m['orders_count'],
                'total_amount': m['total_amount'],
                'avg_check': avg_check,
                'paid_amount': m['paid_amount'],
                'shipped_amount': m['shipped_amount'],
                'delivery_amount': m['delivery_amount'],
            })

        return result

    def get_top_managers_ytd(self, limit=10):
        """
        Получение топ-N менеджеров с начала года (YTD)
        Используется для Executive Summary
        """
        first_day_of_year = self.today.replace(month=1, day=1)

        managers = (
            self._base_queryset()
            .filter(date_from__gte=first_day_of_year)
            .values('manager')
            .annotate(
                orders_count=Count('order_id'),
                total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
                paid_amount=Coalesce(Sum('cash_pmts', output_field=FloatField()), 0.0),
                shipped_amount=Coalesce(Sum('total_shiped_amount', output_field=FloatField()), 0.0),
                delivery_amount=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
            )
            .filter(manager__isnull=False, manager__gt='')
            .order_by('-total_amount')[:limit]
        )

        result = []
        for m in managers:
            avg_check = m['total_amount'] / m['orders_count'] if m['orders_count'] > 0 else 0

            result.append({
                'manager': m['manager'],
                'orders_count': m['orders_count'],
                'total_amount': m['total_amount'],
                'avg_check': avg_check,
                'paid_amount': m['paid_amount'],
                'shipped_amount': m['shipped_amount'],
                'delivery_amount': m['delivery_amount'],
            })

        return result

    # def get_manager_details(self, manager_name):
    #     """
    #     Получение детальной информации по конкретному менеджеру
    #     """
    #     first_day_of_month = self.today.replace(day=1)
    #     first_day_of_year = self.today.replace(month=1, day=1)

    #     # MTD статистика
    #     mtd_qs = self._base_queryset().filter(
    #         manager=manager_name,
    #         date_from__gte=first_day_of_month
    #     )

    #     mtd_stats = mtd_qs.aggregate(
    #         orders_count=Count('order_id'),
    #         total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
    #         paid_amount=Coalesce(Sum('cash_pmts', output_field=FloatField()), 0.0),
    #         shipped_amount=Coalesce(Sum('total_shiped_amount', output_field=FloatField()), 0.0),
    #         delivery_amount=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
    #     )

    #     # YTD статистика
    #     ytd_qs = self._base_queryset().filter(
    #         manager=manager_name,
    #         date_from__gte=first_day_of_year
    #     )

    #     ytd_stats = ytd_qs.aggregate(
    #         orders_count=Count('order_id'),
    #         total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
    #         paid_amount=Coalesce(Sum('cash_pmts', output_field=FloatField()), 0.0),
    #         shipped_amount=Coalesce(Sum('total_shiped_amount', output_field=FloatField()), 0.0),
    #         delivery_amount=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
    #     )

    #     # Список клиентов менеджера
    #     clients = (
    #         self._base_queryset()
    #         .filter(manager=manager_name)
    #         .values('client')
    #         .annotate(
    #             total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
    #             orders_count=Count('order_id'),
    #         )
    #         .filter(client__isnull=False, client__gt='')
    #         .order_by('-total_amount')[:5]
    #     )

    #     return {
    #         'manager': manager_name,
    #         'mtd': {
    #             'orders_count': mtd_stats['orders_count'],
    #             'total_amount': mtd_stats['total_amount'],
    #             'paid_amount': mtd_stats['paid_amount'],
    #             'shipped_amount': mtd_stats['shipped_amount'],
    #             'delivery_amount': mtd_stats['delivery_amount'],
    #         },
    #         'ytd': {
    #             'orders_count': ytd_stats['orders_count'],
    #             'total_amount': ytd_stats['total_amount'],
    #             'paid_amount': ytd_stats['paid_amount'],
    #             'shipped_amount': ytd_stats['shipped_amount'],
    #             'delivery_amount': ytd_stats['delivery_amount'],
    #         },
    #         'top_clients': list(clients),
    #     }
    
    
    

    def get_manager_details(self, manager_name):
        """
        Получение детальной информации по конкретному менеджеру
        """
        first_day_of_month = self.today.replace(day=1)
        first_day_of_year = self.today.replace(month=1, day=1)

        # MTD статистика
        mtd_qs = self._base_queryset().filter(
            manager=manager_name,
            date_from__gte=first_day_of_month
        )

        mtd_stats = mtd_qs.aggregate(
            orders_count=Count('order_id'),
            total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
            paid_amount=Coalesce(Sum('cash_pmts', output_field=FloatField()), 0.0),
            shipped_amount=Coalesce(Sum('total_shiped_amount', output_field=FloatField()), 0.0),
            delivery_amount=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
        )

        # YTD статистика
        ytd_qs = self._base_queryset().filter(
            manager=manager_name,
            date_from__gte=first_day_of_year
        )

        ytd_stats = ytd_qs.aggregate(
            orders_count=Count('order_id'),
            total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
            paid_amount=Coalesce(Sum('cash_pmts', output_field=FloatField()), 0.0),
            shipped_amount=Coalesce(Sum('total_shiped_amount', output_field=FloatField()), 0.0),
            delivery_amount=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
        )

        # Список клиентов менеджера
        clients = (
            self._base_queryset()
            .filter(manager=manager_name)
            .values('client')
            .annotate(
                total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
                orders_count=Count('order_id'),
            )
            .filter(client__isnull=False, client__gt='')
            .order_by('-total_amount')[:5]
        )
        
        # НОВОЕ: Самый старый неоплаченный счет
        oldest_invoice = self.get_manager_oldest_unpaid_invoice(manager_name)
        
        # НОВОЕ: Сумма к отгрузке
        remaining_to_ship = self.get_manager_remaining_to_ship(manager_name)

        return {
            'manager': manager_name,
            'mtd': {
                'orders_count': mtd_stats['orders_count'],
                'total_amount': mtd_stats['total_amount'],
                'paid_amount': mtd_stats['paid_amount'],
                'shipped_amount': mtd_stats['shipped_amount'],
                'delivery_amount': mtd_stats['delivery_amount'],
            },
            'ytd': {
                'orders_count': ytd_stats['orders_count'],
                'total_amount': ytd_stats['total_amount'],
                'paid_amount': ytd_stats['paid_amount'],
                'shipped_amount': ytd_stats['shipped_amount'],
                'delivery_amount': ytd_stats['delivery_amount'],
            },
            'top_clients': list(clients),
            'oldest_unpaid_invoice': oldest_invoice,  # НОВОЕ
            'remaining_to_ship': remaining_to_ship,   # НОВОЕ
        }

    def get_managers_count(self):
        """
        Получение количества активных менеджеров
        """
        count = (
            self._base_queryset()
            .values('manager')
            .filter(manager__isnull=False, manager__gt='')
            .distinct()
            .count()
        )
        return count
    


    def get_manager_oldest_unpaid_invoice(self, manager_name):
        """
        Получение самого старого неоплаченного счета для менеджера
        Возвращает словарь с информацией о счете:
        - number: номер счета
        - date_from: дата счета
        - client: клиент
        - amount: сумма к оплате (остаток)
        - days_overdue: количество дней просрочки (если есть)
        """
        from datetime import date
        
        # Активные статусы заказов (не отмененные и не полностью оплаченные)
        active_statuses = [
            'К выполнению / В резерве',
            'На согласовании',
        ]
        
        # Ищем активные заказы с остатком долга > 0
        oldest_order = (
            self._base_queryset()
            .filter(
                manager=manager_name,
                status__in=active_statuses,
                cash_pmts__lt=F('amount_active')  # Оплачено меньше суммы заказа
            )
            .exclude(change_status='Отменен')
            .order_by('date_from')  # Самый старый по дате
            .values(
                'number',
                'date_from',
                'client',
                'amount_active',
                'cash_pmts'
            )
            .first()
        )
        
        if oldest_order:
            remaining_amount = float(oldest_order['amount_active'] or 0) - float(oldest_order['cash_pmts'] or 0)
            
            # Расчет просрочки - ПРИВОДИМ К ОДНОМУ ТИПУ
            days_overdue = 0
            if oldest_order['date_from']:
                # Если date_from - datetime, преобразуем в date
                if hasattr(oldest_order['date_from'], 'date'):
                    order_date = oldest_order['date_from'].date()
                else:
                    order_date = oldest_order['date_from']
                
                days_overdue = (date.today() - order_date).days
            
            return {
                'number': oldest_order['number'],
                'date_from': oldest_order['date_from'],
                'client': oldest_order['client'],
                'remaining_amount': max(0, remaining_amount),
                'days_overdue': days_overdue,
            }
        
        return None


    def get_manager_remaining_to_ship(self, manager_name):
        """
        Получение суммы, которую еще нужно отгрузить менеджеру
        (Активные заказы - уже отгруженное)
        """
        active_statuses = [
            'К выполнению / В резерве',
            'На согласовании',
        ]
        
        stats = (
            self._base_queryset()
            .filter(
                manager=manager_name,
                status__in=active_statuses,
            )
            .aggregate(
                total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
                total_shipped=Coalesce(Sum('total_shiped_amount', output_field=FloatField()), 0.0),
            )
        )
        
        remaining_to_ship = max(0, stats['total_amount'] - stats['total_shipped'])
        return remaining_to_ship
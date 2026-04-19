# orders/reports/queries/payments_analysis_query.py
from datetime import datetime, timedelta

from django.db.models import Avg, Case, CharField, Count, Q, Sum, Value, When
from django.db.models.functions import Abs, TruncMonth
from django.utils import timezone

from ...models import OrdersCF


class PaymentsAnalysisQueries:
    """Запросы для анализа оплат - все суммы берутся как есть в БД, со знаком"""

    def __init__(self, request=None):
        self.request = request
        self.today = timezone.now().date()

        self.current_month_start = self.today.replace(day=1)
        self.current_year_start = self.today.replace(month=1, day=1)

        if self.current_month_start.month == 1:
            self.last_month_start = self.current_month_start.replace(
                year=self.current_month_start.year - 1,
                month=12,
                day=1,
            )
        else:
            self.last_month_start = self.current_month_start.replace(
                month=self.current_month_start.month - 1,
                day=1,
            )

        self.last_month_end = self.current_month_start - timedelta(days=1)

    def _get_base_queryset(self):
        """
        Все операции, участвующие в анализе.
        НИКАКОЙ фильтрации по знаку amount здесь нет.
        """
        return OrdersCF.objects.filter(
            Q(oper_type='Поступление оплаты от клиента') |
            Q(oper_type='Возврат или иная оплата клиенту') |
            Q(register__startswith='Отчет о розничных продажах') |
            Q(register__startswith='Отчет о розничных возвратах')
        )

    def _filter_by_date_range(self, queryset, start_date, end_date):
        return queryset.filter(date__gte=start_date, date__lte=end_date)

    def _get_classified_queryset(self):
        """
        Взаимоисключающая классификация строк.
        Одна строка попадает только в одну категорию.

        Приоритет:
        1. Выручка магазинов (включая возвраты)
        2. Поступления от клиентов
        3. Возвраты клиентам
        """
        return self._get_base_queryset().annotate(
            operation_group=Case(
                When(
                    Q(register__startswith='Отчет о розничных продажах') |
                    Q(register__startswith='Отчет о розничных возвратах'),
                    then=Value('store_revenue')
                ),
                When(
                    oper_type='Поступление оплаты от клиента',
                    then=Value('incoming')
                ),
                When(
                    oper_type='Возврат или иная оплата клиенту',
                    then=Value('outgoing')
                ),
                default=Value('other'),
                output_field=CharField(),
            )
        )

    def get_payments_metrics(self):
        """Метрики - amount суммируется как есть, со знаком"""
        base_qs = self._get_base_queryset()

        mtd_qs = self._filter_by_date_range(base_qs, self.current_month_start, self.today)
        ytd_qs = self._filter_by_date_range(base_qs, self.current_year_start, self.today)
        last_month_qs = self._filter_by_date_range(base_qs, self.last_month_start, self.last_month_end)

        mtd_metrics = {
            'total_amount': mtd_qs.aggregate(total=Sum('amount'))['total'] or 0,
            'total_payments': mtd_qs.count(),
            'avg_payment': mtd_qs.aggregate(avg=Avg('amount'))['avg'] or 0,
            'unique_stores': mtd_qs.values('store').distinct().count(),
            'unique_registers': mtd_qs.values('register').distinct().count(),
        }

        ytd_metrics = {
            'total_amount': ytd_qs.aggregate(total=Sum('amount'))['total'] or 0,
            'total_payments': ytd_qs.count(),
            'avg_payment': ytd_qs.aggregate(avg=Avg('amount'))['avg'] or 0,
            'unique_stores': ytd_qs.values('store').distinct().count(),
            'unique_registers': ytd_qs.values('register').distinct().count(),
        }

        last_month_metrics = {
            'total_amount': last_month_qs.aggregate(total=Sum('amount'))['total'] or 0,
            'total_payments': last_month_qs.count(),
        }

        mtd_dynamics = {
            'amount_vs_last_month': self._calculate_dynamics(
                mtd_metrics['total_amount'],
                last_month_metrics['total_amount']
            ),
            'payments_vs_last_month': self._calculate_dynamics(
                mtd_metrics['total_payments'],
                last_month_metrics['total_payments']
            ),
        }

        return {
            'mtd': mtd_metrics,
            'ytd': ytd_metrics,
            'mtd_dynamics': mtd_dynamics,
        }

    def get_payments_by_store(self, limit=None):
        """Магазины по сумме - amount как есть, со знаком"""
        qs = self._filter_by_date_range(
            self._get_base_queryset(),
            self.current_year_start,
            self.today
        )

        stores = qs.values('store').annotate(
            total_amount=Sum('amount'),
            payments_count=Count('id'),
            avg_payment=Avg('amount'),
            unique_registers=Count('register', distinct=True),
        ).order_by('-total_amount')

        if limit:
            stores = stores[:limit]

        return list(stores)

    def get_payments_trend(self, months=6):
        """Месячный тренд"""
        start_date = self.today.replace(day=1)

        for _ in range(months - 1):
            if start_date.month == 1:
                start_date = start_date.replace(
                    year=start_date.year - 1,
                    month=12,
                    day=1
                )
            else:
                start_date = start_date.replace(
                    month=start_date.month - 1,
                    day=1
                )

        qs = self._filter_by_date_range(self._get_base_queryset(), start_date, self.today)

        trends = qs.annotate(month=TruncMonth('date')).values('month').annotate(
            total_amount=Sum('amount'),
            payments_count=Count('id'),
            avg_payment=Avg('amount'),
        ).order_by('month')

        return list(trends)

    def get_large_payments(self, threshold=300000, limit=20):
        """
        Крупные платежи отбираем по модулю,
        но саму сумму показываем как есть, со знаком.
        """
        qs = self._filter_by_date_range(
            self._get_base_queryset(),
            self.current_year_start,
            self.today
        )

        large_payments = qs.annotate(
            abs_amount=Abs('amount')
        ).filter(
            abs_amount__gte=threshold
        ).values(
            'date', 'store', 'register', 'amount'
        ).order_by('-abs_amount')[:limit]

        return list(large_payments)

    def get_payments_by_store_monthly(self, year=None):
        """Помесячная разбивка по магазинам"""
        if year is None:
            year = self.today.year

        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year, 12, 31).date()

        qs = self._filter_by_date_range(self._get_base_queryset(), start_date, end_date)

        monthly = qs.annotate(month=TruncMonth('date')).values('store', 'month').annotate(
            total_amount=Sum('amount'),
            payments_count=Count('id'),
        ).order_by('store', 'month')

        result = {}
        months_order = []

        for item in monthly:
            store = item['store'] or 'БЕЗ МАГАЗИНА'
            month = item['month'].strftime('%Y-%m') if item['month'] else None
            amount = item['total_amount'] or 0

            if month and month not in months_order:
                months_order.append(month)

            if store not in result:
                result[store] = {}

            if month:
                result[store][month] = amount

        months_order.sort()

        return {
            'data': result,
            'months': months_order,
            'year': year,
        }

    def get_payments_summary_by_type(self):
        """
        Сводка по типам.
        ВАЖНО:
        - amount берется как есть, со знаком
        - строка не дублируется между категориями
        """
        qs = self._filter_by_date_range(
            self._get_classified_queryset(),
            self.current_year_start,
            self.today
        )

        grouped = qs.values('operation_group').annotate(
            total=Sum('amount'),
            count=Count('id')
        )

        result = {
            'incoming': {
                'total': 0,
                'count': 0,
                'name': 'Поступления от клиентов',
            },
            'outgoing': {
                'total': 0,
                'count': 0,
                'name': 'Возвраты клиентам',
            },
            'store_revenue': {
                'total': 0,
                'count': 0,
                'name': 'Выручка магазинов',
            },
        }

        for row in grouped:
            group = row['operation_group']
            if group in result:
                result[group]['total'] = row['total'] or 0
                result[group]['count'] = row['count'] or 0

        total_all = (
            result['incoming']['total'] +
            result['outgoing']['total'] +
            result['store_revenue']['total']
        )

        return {
            'incoming': result['incoming'],
            'outgoing': result['outgoing'],
            'store_revenue': result['store_revenue'],
            'total_all': total_all,
            'net': {
                'total': total_all,
                'name': 'ИТОГО ВСЕ ОПЕРАЦИИ',
            }
        }

    def _calculate_dynamics(self, current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)
    


    def get_daily_payments_by_store(self, start_date=None, end_date=None):
        """
        Подневная разбивка оплат по магазинам с начала года
        Возвращает словарь: {store: {date: {'amount': сумма, 'count': кол-во}}}
        """
        if start_date is None:
            start_date = self.current_year_start
        if end_date is None:
            end_date = self.today
        
        # Используем _get_classified_queryset() вместо _get_base_queryset()
        # чтобы получить operation_group
        qs = self._filter_by_date_range(
            self._get_classified_queryset(),  # ← ИСПРАВЛЕНО: используем классифицированный queryset
            start_date,
            end_date
        )
        
        # Группируем по магазину, дате и типу операции
        daily_data = qs.values('store', 'date', 'operation_group').annotate(
            daily_amount=Sum('amount'),
            daily_count=Count('id')
        ).order_by('store', 'date')
        
        # Структурируем результат
        result = {}
        all_dates = set()
        
        for item in daily_data:
            store = item['store'] or 'БЕЗ МАГАЗИНА'
            date = item['date']
            amount = item['daily_amount'] or 0
            count = item['daily_count'] or 0
            operation_type = item['operation_group']
            
            if store not in result:
                result[store] = {}
            
            if date not in result[store]:
                result[store][date] = {
                    'total_amount': 0,
                    'total_count': 0,
                    'incoming': 0,
                    'outgoing': 0,
                    'store_revenue': 0
                }
            
            # Суммируем по типам
            result[store][date]['total_amount'] += amount
            result[store][date]['total_count'] += count
            
            if operation_type == 'incoming':
                result[store][date]['incoming'] += amount
            elif operation_type == 'outgoing':
                result[store][date]['outgoing'] += amount
            elif operation_type == 'store_revenue':
                result[store][date]['store_revenue'] += amount
            
            all_dates.add(date)
        
        # Сортируем даты
        all_dates = sorted(list(all_dates))
        
        return {
            'data': result,
            'dates': all_dates,
            'start_date': start_date,
            'end_date': end_date,
        }

    def get_store_daily_summary(self, store_name, start_date=None, end_date=None):
        """
        Детальная информация по конкретному магазину
        """
        if start_date is None:
            start_date = self.current_year_start
        if end_date is None:
            end_date = self.today
        
        qs = self._filter_by_date_range(
            self._get_base_queryset().filter(store=store_name),
            start_date,
            end_date
        )
        
        # Получаем все операции магазина
        operations = qs.values(
            'date', 'register', 'oper_type', 'amount', 'document_number'
        ).order_by('-date', '-amount')
        
        # Агрегируем по дням
        daily = qs.values('date').annotate(
            daily_total=Sum('amount'),
            daily_count=Count('id'),
            avg_amount=Avg('amount')
        ).order_by('-date')
        
        return {
            'store_name': store_name,
            'operations': list(operations),
            'daily_summary': list(daily),
            'total_amount': qs.aggregate(total=Sum('amount'))['total'] or 0,
            'total_operations': qs.count(),
            'start_date': start_date,
            'end_date': end_date,
        }
        
    def get_last_data_date(self):
        """Возвращает последнюю дату, за которую есть данные по оплатам"""
        last_record = self._get_base_queryset().order_by('-date').first()
        if last_record and last_record.date:
            return last_record.date
        return self.today  # fallback на сегодня, если данных нет
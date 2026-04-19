# orders/reports/queries/orders_detail_query.py
from django.db.models import Q, Sum, F, FloatField
from django.db.models.functions import Coalesce
from orders.models import MV_Orders


class OrdersDetailQueries:
    """Запросы для листа детализации активных заказов"""

    ACTIVE_STATUSES = [
        'К выполнению / В резерве',
        'На согласовании',
    ]

    def get_active_orders_detail(self):
        """
        Детализация только по активным заказам
        """

        qs = (
            MV_Orders.objects
            .filter(status__in=self.ACTIVE_STATUSES)
            .values(
                'order_id',
                'order_name',
                'number',
                'date_from',
                'update_at',
                'status',
                'change_status',
                'client',
                'manager',
                'store',
                'order_qty',
                'order_amount',
                'amount_delivery',
                'amount_cancelled',
                'amount_active',
                'cash_recieved',
                'cash_returned',
                'cash_pmts',
                'shiped',
                'returned',
                'shiped_qty',
                'shiped_amount',
                'returned_amount',
                'total_shiped_amount',
                'shiped_delivery_amount',
                'payment_dates',
            )
            .order_by('-date_from', '-order_id')
        )

        result = []
        for order in qs:
            # Безопасное преобразование в числа
            order_qty = float(order.get('order_qty') or 0)
            order_amount = float(order.get('order_amount') or 0)
            amount_delivery = float(order.get('amount_delivery') or 0)
            amount_cancelled = float(order.get('amount_cancelled') or 0)
            amount_active = float(order.get('amount_active') or 0)
            cash_recieved = float(order.get('cash_recieved') or 0)
            cash_returned = float(order.get('cash_returned') or 0)
            cash_pmts = float(order.get('cash_pmts') or 0)
            shiped = float(order.get('shiped') or 0)
            returned = float(order.get('returned') or 0)
            shiped_qty = float(order.get('shiped_qty') or 0)
            shiped_amount = float(order.get('shiped_amount') or 0)
            returned_amount = float(order.get('returned_amount') or 0)
            total_shiped_amount = float(order.get('total_shiped_amount') or 0)
            shiped_delivery_amount = float(order.get('shiped_delivery_amount') or 0)
            
            # Рассчитываем остатки
            remaining_qty = max(0, order_qty - shiped_qty)
            remaining_amount = max(0, amount_active - cash_pmts)

            result.append({
                # Основная информация
                'order_id': order.get('order_id'),
                'order_name': order.get('order_name') or '',
                'number': order.get('number') or '',
                'date_from': order.get('date_from'),
                'update_at': order.get('update_at'),
                'status': order.get('status') or '',
                'change_status': order.get('change_status') or 'Без изменений',
                'client': order.get('client') or '',
                'manager': order.get('manager') or '',
                'store': order.get('store') or '',
                
                # Количественные показатели
                'order_qty': order_qty,  # Кол-во заказано
                'shiped': shiped,  # Отгружено
                'returned': returned,  # Возвращено
                'shiped_qty': shiped_qty,  # Итого отгружено с учетом возвратов
                'remaining_qty': remaining_qty,  # Остаток в шт
                
                # Суммовые показатели
                'order_amount': order_amount,  # Сумма заказа с доставкой
                'amount_delivery': amount_delivery,  # В том числе услуги (доставка)
                'amount_cancelled': amount_cancelled,  # Сумма отмены
                'amount_active': amount_active,  # Итого сумма заказа
                
                # Оплаты
                'cash_recieved': cash_recieved,  # Оплата полученная
                'cash_returned': cash_returned,  # Деньги возвращенные
                'cash_pmts': cash_pmts,  # Итого оплачено
                'remaining_amount': remaining_amount,  # К оплате
                'payment_dates': order.get('payment_dates'),  # Даты оплат
                
                # Отгрузки
                'shiped_amount': shiped_amount,  # Отгружено на сумму
                'returned_amount': returned_amount,  # Возврат в рублях
                'total_shiped_amount': total_shiped_amount,  # Итого отгружено в рублях
                'shiped_delivery_amount': shiped_delivery_amount,  # Сумма доставки отгруженного
            })

        return result

    def get_active_orders_summary(self):
        """
        Получение сводной статистики по активным заказам
        Используется для KPI карточек
        """
        qs = MV_Orders.objects.filter(status__in=self.ACTIVE_STATUSES)
        
        # Агрегации
        from django.db.models import Count, Sum
        
        stats = qs.aggregate(
            total_orders=Count('order_id'),
            total_amount=Coalesce(Sum('amount_active', output_field=FloatField()), 0.0),
            total_paid=Coalesce(Sum('cash_pmts', output_field=FloatField()), 0.0),
            total_shipped=Coalesce(Sum('total_shiped_amount', output_field=FloatField()), 0.0),
            total_delivery=Coalesce(Sum('amount_delivery', output_field=FloatField()), 0.0),
        )
        
        # Уникальные клиенты
        unique_clients = qs.values('client').distinct().count()
        
        return {
            'total_orders': stats['total_orders'],
            'total_amount': stats['total_amount'],
            'total_paid': stats['total_paid'],
            'total_shipped': stats['total_shipped'],
            'total_delivery': stats['total_delivery'],
            'total_remaining': max(0, stats['total_amount'] - stats['total_paid']),
            'unique_clients': unique_clients,
            'avg_check': stats['total_amount'] / stats['total_orders'] if stats['total_orders'] > 0 else 0,
        }
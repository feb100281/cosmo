# # orders/reports/queries/remaining_to_ship_query.py
# from django.db.models import Sum, Count, Q
# from django.utils import timezone
# from orders.models import MV_OrdersItems


# class RemainingToShipQueries:
#     """Запросы для анализа остатков к отгрузке"""

#     def __init__(self, request=None):
#         self.request = request
#         self.today = timezone.now().date()

#     def get_remaining_by_category(self):
#         """
#         Остатки к отгрузке по категориям (parent_cat, cat, subcat)
#         Исключаем закрытые заказы
#         """
#         # Фильтруем: статус НЕ "Закрыт"
#         # Нужно джойнить с MV_Orders, чтобы проверить статус заказа
#         qs = MV_OrdersItems.objects.filter(
#             ~Q(order__status='Закрыт'),  # Статус заказа НЕ "Закрыт"
#         )
        
#         # Группировка по категориям
#         result = qs.values('parent_cat', 'cat', 'subcat').annotate(
#             total_qty=Sum('qty'),
#             total_amount=Sum('amount'),
#             order_count=Count('order_id', distinct=True),
#             item_count=Count('id')
#         ).order_by('parent_cat', 'cat', 'subcat')
        
#         return list(result)

#     def get_remaining_by_parent_cat(self):
#         """
#         Сводка по родительским категориям
#         """
#         qs = MV_OrdersItems.objects.filter(
#             ~Q(order__status='Закрыт')
#         )
        
#         result = qs.values('parent_cat').annotate(
#             total_qty=Sum('qty'),
#             total_amount=Sum('amount'),
#             order_count=Count('order_id', distinct=True)
#         ).order_by('-total_amount')
        
#         return list(result)

#     def get_remaining_summary(self):
#         """
#         Общая сводка: всего к отгрузке в штуках и рублях
#         """
#         qs = MV_OrdersItems.objects.filter(
#             ~Q(order__status='Закрыт')
#         )
        
#         summary = qs.aggregate(
#             total_qty=Sum('qty'),
#             total_amount=Sum('amount'),
#             total_orders=Count('order_id', distinct=True),
#             total_items=Count('id')
#         )
        
#         # Обрабатываем None значения
#         return {
#             'total_qty': summary['total_qty'] or 0,
#             'total_amount': summary['total_amount'] or 0,
#             'total_orders': summary['total_orders'] or 0,
#             'total_items': summary['total_items'] or 0,
#         }

#     def get_remaining_by_order(self, limit=50):
#         """
#         Детализация по заказам (топ самых больших остатков)
#         """
#         qs = MV_OrdersItems.objects.filter(
#             ~Q(order__status='Закрыт')
#         )
        
#         orders = qs.values('order_id', 'order__number', 'order__client', 'order__manager').annotate(
#             total_qty=Sum('qty'),
#             total_amount=Sum('amount'),
#             items_count=Count('id')
#         ).filter(total_qty__gt=0).order_by('-total_amount')[:limit]
        
#         return list(orders)




# orders/reports/queries/remaining_to_ship_query.py
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from orders.models import MV_OrdersItems, MV_Orders


class RemainingToShipQueries:
    """Запросы для анализа остатков к отгрузке"""

    def __init__(self, request=None):
        self.request = request
        self.today = timezone.now().date()

    def get_remaining_by_category(self):
        """
        Остатки к отгрузке по категориям (parent_cat, cat, subcat)
        Учитываем только НЕ закрытые заказы и вычитаем уже отгруженное
        """
        # Джойним с MV_Orders, чтобы получить статус и отгруженное количество
        qs = MV_OrdersItems.objects.select_related('order').filter(
            ~Q(order__status='Закрыт'),  # Заказ не закрыт
        )
        
        # Группировка по категориям
        # ВАЖНО: остаток = qty - (shiped_qty) но shiped_qty нет на уровне позиции
        # Поэтому используем qty как есть, предполагая что в таблице только неотгруженные позиции
        result = qs.values('parent_cat', 'cat', 'subcat').annotate(
            total_qty=Sum('qty'),  # Суммируем количество
            total_amount=Sum('amount'),  # Суммируем сумму
            order_count=Count('order_id', distinct=True),
            item_count=Count('id')
        ).order_by('parent_cat', 'cat', 'subcat')
        
        return list(result)

    def get_remaining_by_parent_cat(self):
        """
        Сводка по родительским категориям
        """
        qs = MV_OrdersItems.objects.select_related('order').filter(
            ~Q(order__status='Закрыт')
        )
        
        result = qs.values('parent_cat').annotate(
            total_qty=Sum('qty'),
            total_amount=Sum('amount'),
            order_count=Count('order_id', distinct=True)
        ).order_by('-total_amount')
        
        return list(result)

    def get_remaining_summary(self):
        """
        Общая сводка: всего к отгрузке в штуках и рублях
        """
        qs = MV_OrdersItems.objects.select_related('order').filter(
            ~Q(order__status='Закрыт')
        )
        
        summary = qs.aggregate(
            total_qty=Sum('qty'),
            total_amount=Sum('amount'),
            total_orders=Count('order_id', distinct=True),
            total_items=Count('id')
        )
        
        # Обрабатываем None значения
        return {
            'total_qty': float(summary['total_qty'] or 0),
            'total_amount': float(summary['total_amount'] or 0),
            'total_orders': summary['total_orders'] or 0,
            'total_items': summary['total_items'] or 0,
        }

    def get_remaining_by_order(self, limit=50):
        """
        Детализация по заказам (топ самых больших остатков)
        """
        qs = MV_OrdersItems.objects.select_related('order').filter(
            ~Q(order__status='Закрыт')
        )
        
        orders = qs.values(
            'order_id', 
            'order__number', 
            'order__client', 
            'order__manager',
            'order__status'
        ).annotate(
            total_qty=Sum('qty'),
            total_amount=Sum('amount'),
            items_count=Count('id')
        ).filter(total_qty__gt=0).order_by('-total_amount')[:limit]
        
        return list(orders)

    def get_remaining_with_shipped_deduction(self):
        """
        Более точный расчет с вычетом уже отгруженного
        Используем данные из MV_Orders (shiped_qty)
        """
        # Получаем все активные заказы с их отгрузками
        active_orders = MV_Orders.objects.filter(
            ~Q(status='Закрыт')
        ).values('order_id', 'shiped_qty', 'order_qty')
        
        result = []
        
        for order in active_orders:
            order_id = order['order_id']
            shiped_qty = float(order['shiped_qty'] or 0)
            order_qty = float(order['order_qty'] or 0)
            
            # Получаем позиции заказа
            items = MV_OrdersItems.objects.filter(order_id=order_id)
            
            for item in items:
                # Остаток по позиции = количество в заказе минус доля отгруженного
                # Это приблизительный расчет, так как неизвестно, что именно отгружено
                remaining_qty = max(0, float(item.qty) - (float(item.qty) / order_qty * shiped_qty if order_qty > 0 else 0))
                remaining_amount = remaining_qty * float(item.price)
                
                result.append({
                    'parent_cat': item.parent_cat,
                    'cat': item.cat,
                    'subcat': item.subcat,
                    'remaining_qty': remaining_qty,
                    'remaining_amount': remaining_amount,
                    'order_id': order_id,
                })
        
        # Группируем по категориям
        from collections import defaultdict
        grouped = defaultdict(lambda: {'qty': 0, 'amount': 0, 'orders': set()})
        
        for item in result:
            key = (item['parent_cat'], item['cat'], item['subcat'])
            grouped[key]['qty'] += item['remaining_qty']
            grouped[key]['amount'] += item['remaining_amount']
            grouped[key]['orders'].add(item['order_id'])
        
        final_result = []
        for (parent_cat, cat, subcat), data in grouped.items():
            final_result.append({
                'parent_cat': parent_cat or '—',
                'cat': cat or '—',
                'subcat': subcat or '—',
                'total_qty': round(data['qty'], 2),
                'total_amount': round(data['amount'], 2),
                'order_count': len(data['orders']),
            })
        
        return final_result





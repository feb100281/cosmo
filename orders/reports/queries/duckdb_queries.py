# # orders/reports/queries/duckdb_queries.py
# import pandas as pd
# import duckdb
# from duckdb import DuckDBPyConnection
# from django.conf import settings

# # Импортируем только существующие модели
# from orders.models import Order, OrderItem, OrdersCF
# from corporate.models import Items, Barcode


# class DuckDBReportQueries:
#     """Запросы через DuckDB для быстрой аналитики"""
    
#     _conn = None
    
#     @classmethod
#     def get_connection(cls):
#         """Получить соединение с DuckDB (синглтон)"""
#         if cls._conn is None:
#             cls._conn = duckdb.connect(':memory:')
#             cls._register_tables(cls._conn)
#         return cls._conn
    
#     @classmethod
#     def _register_tables(cls, conn: DuckDBPyConnection):
#         """Зарегистрировать все таблицы из MySQL в DuckDB"""
        
#         # Конвертируем Decimal в float для избежания проблем с типами
#         def convert_decimal_to_float(df):
#             for col in df.columns:
#                 if df[col].dtype.name == 'object':
#                     try:
#                         # Пробуем конвертировать в float если это число
#                         if 'decimal' in str(df[col].dtype):
#                             df[col] = df[col].astype(float)
#                     except:
#                         pass
#             return df
        
#         # Основные таблицы (обязательные)
#         orders = pd.DataFrame(list(Order.objects.all().values()))
#         items = pd.DataFrame(list(Items.objects.all().values()))
#         order_items = pd.DataFrame(list(OrderItem.objects.all().values()))
#         orders_cf = pd.DataFrame(list(OrdersCF.objects.all().values()))
#         barcodes = pd.DataFrame(list(Barcode.objects.all().values()))
        
#         # Конвертируем Decimal в float для числовых колонок
#         for df in [orders, items, order_items, orders_cf, barcodes]:
#             for col in df.columns:
#                 if 'amount' in col.lower() or 'price' in col.lower() or 'qty' in col.lower():
#                     try:
#                         df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
#                     except:
#                         pass
        
#         # Регистрируем основные таблицы
#         conn.register("orders", orders)
#         conn.register("items", items)
#         conn.register("order_items", order_items)
#         conn.register("orders_cf", orders_cf)
#         conn.register("barcodes", barcodes)
        
#         # Создаем расширенную таблицу items_joined
#         cls._create_items_joined(conn)
        
#     @classmethod
#     def _create_items_joined(cls, conn: DuckDBPyConnection):
#         """Создать расширенную таблицу с товарами"""
#         conn.execute("""
#             CREATE OR REPLACE VIEW items_joined AS
#             SELECT
#                 oi.order_id,
#                 o.fullname as order_name,
#                 o.number,
#                 o.date_from,
#                 o.update_at,
#                 o.is_cancelled,
#                 o.status,
#                 o.manager,
#                 o.client,
#                 o.oper_type,
#                 o.store,
#                 oi.item_id,
#                 COALESCE(i.fullname, '') as item_name,
#                 COALESCE(bc.barcode, '') as barcode,
#                 CAST(oi.qty AS DOUBLE) as qty,
#                 CAST(oi.price AS DOUBLE) as price,
#                 CAST(oi.amount AS DOUBLE) as amount
#             FROM order_items oi
#             LEFT JOIN orders o ON o.id = oi.order_id
#             LEFT JOIN items i ON i.id = oi.item_id
#             LEFT JOIN barcodes bc ON bc.id = oi.barcode_id
#         """)
    
#     @classmethod
#     def get_filtered_orders(cls, request):
#         """Получить заказы с учетом фильтров из админки"""
#         conn = cls.get_connection()
        
#         filters = request.GET.get('changelist_filters', '')
#         from django.http import QueryDict
#         query_dict = QueryDict(filters) if filters else request.GET
        
#         # Базовый запрос
#         query = "SELECT * FROM orders WHERE 1=1"
#         params = []
        
#         if query_dict.get('status__exact'):
#             query += " AND status = ?"
#             params.append(query_dict['status__exact'])
#         if query_dict.get('manager__exact'):
#             query += " AND manager = ?"
#             params.append(query_dict['manager__exact'])
#         if query_dict.get('date_from__gte'):
#             query += " AND date_from >= ?"
#             params.append(query_dict['date_from__gte'])
#         if query_dict.get('date_from__lte'):
#             query += " AND date_from <= ?"
#             params.append(query_dict['date_from__lte'])
#         if query_dict.get('oper_type__exact'):
#             query += " AND oper_type = ?"
#             params.append(query_dict['oper_type__exact'])
#         if query_dict.get('is_cancelled__exact'):
#             is_cancelled = query_dict['is_cancelled__exact'] == '1'
#             query += " AND is_cancelled = ?"
#             params.append(is_cancelled)
        
#         if params:
#             df = conn.execute(query, params).df()
#         else:
#             df = conn.execute(query).df()
        
#         return df
    
#     @classmethod
#     def get_orders_summary(cls, request):
#         """Получить сводку по заказам с фильтрацией"""
#         conn = cls.get_connection()
        
#         # Получаем отфильтрованные заказы
#         orders_df = cls.get_filtered_orders(request)
        
#         # Если нет заказов, возвращаем пустой словарь
#         if orders_df.empty:
#             return {
#                 'total_orders': 0,
#                 'total_amount': 0,
#                 'cancelled': 0,
#                 'active': 0
#             }
        
#         # Регистрируем отфильтрованные заказы как временную таблицу
#         conn.register("filtered_orders", orders_df)
        
#         # Делаем сводный запрос
#         result = conn.execute("""
#             SELECT
#                 COUNT(DISTINCT fo.id) as total_orders,
#                 COALESCE(SUM(oi.total_amount), 0) as total_amount,
#                 SUM(CASE WHEN fo.is_cancelled = TRUE THEN 1 ELSE 0 END) as cancelled,
#                 SUM(CASE WHEN fo.is_cancelled = FALSE THEN 1 ELSE 0 END) as active
#             FROM filtered_orders fo
#             LEFT JOIN (
#                 SELECT order_id, SUM(amount) as total_amount
#                 FROM order_items
#                 GROUP BY order_id
#             ) oi ON oi.order_id = fo.id
#         """).fetchone()
        
#         return {
#             'total_orders': result[0] or 0,
#             'total_amount': float(result[1] or 0),
#             'cancelled': result[2] or 0,
#             'active': result[3] or 0
#         }
    
#     @classmethod
#     def get_orders_data(cls, request):
#         """Получить детальные данные по заказам"""
#         conn = cls.get_connection()
        
#         orders_df = cls.get_filtered_orders(request)
        
#         if orders_df.empty:
#             return []
        
#         conn.register("filtered_orders", orders_df)
        
#         try:
#             data_df = conn.execute("""
#                 SELECT
#                     fo.id,
#                     fo.fullname,
#                     fo.number,
#                     fo.date_from,
#                     fo.update_at,
#                     fo.is_cancelled,
#                     COALESCE(fo.cancellation_reason, '') as cancellation_reason,
#                     COALESCE(fo.status, '') as status,
#                     COALESCE(fo.manager, '') as manager,
#                     COALESCE(fo.client, '') as client,
#                     COALESCE(fo.oper_type, '') as oper_type,
#                     COALESCE(fo.store, '') as store,
#                     COALESCE(oi.items_count, 0) as items_count,
#                     COALESCE(oi.total_amount, 0) as total_amount
#                 FROM filtered_orders fo
#                 LEFT JOIN (
#                     SELECT 
#                         order_id,
#                         COUNT(*) as items_count,
#                         SUM(amount) as total_amount
#                     FROM order_items
#                     GROUP BY order_id
#                 ) oi ON oi.order_id = fo.id
#                 ORDER BY fo.date_from DESC
#             """).df()
#         except Exception as e:
#             # Если ошибка с типами, пробуем упрощенный запрос
#             data_df = conn.execute("""
#                 SELECT
#                     fo.id,
#                     fo.fullname,
#                     fo.number,
#                     fo.date_from,
#                     fo.update_at,
#                     fo.is_cancelled,
#                     COALESCE(fo.cancellation_reason, '') as cancellation_reason,
#                     COALESCE(fo.status, '') as status,
#                     COALESCE(fo.manager, '') as manager,
#                     COALESCE(fo.client, '') as client,
#                     COALESCE(fo.oper_type, '') as oper_type,
#                     COALESCE(fo.store, '') as store,
#                     0 as items_count,
#                     0.0 as total_amount
#                 FROM filtered_orders fo
#                 ORDER BY fo.date_from DESC
#             """).df()
        
#         # Конвертируем даты
#         if 'date_from' in data_df.columns:
#             data_df['date_from'] = pd.to_datetime(data_df['date_from']).dt.date
#         if 'update_at' in data_df.columns:
#             data_df['update_at'] = pd.to_datetime(data_df['update_at']).dt.date
        
#         return data_df.to_dict('records')
    
#     @classmethod
#     def get_items_data(cls, request):
#         """Получить данные по товарам с учетом фильтров заказов"""
#         conn = cls.get_connection()
        
#         orders_df = cls.get_filtered_orders(request)
        
#         if orders_df.empty:
#             return []
        
#         conn.register("filtered_orders", orders_df)
        
#         try:
#             data_df = conn.execute("""
#                 SELECT
#                     ij.order_id,
#                     ij.order_name,
#                     ij.item_name,
#                     ij.barcode,
#                     ij.qty,
#                     ij.price,
#                     ij.amount
#                 FROM items_joined ij
#                 INNER JOIN filtered_orders fo ON fo.id = ij.order_id
#                 ORDER BY ij.order_id, ij.item_name
#             """).df()
#         except Exception as e:
#             # Если ошибка, возвращаем пустой список
#             return []
        
#         return data_df.to_dict('records')
    
#     @classmethod
#     def get_payments_data(cls, request=None):
#         """Получить данные по оплатам"""
#         conn = cls.get_connection()
        
#         # Если есть фильтры по заказам, применяем их
#         if request:
#             orders_df = cls.get_filtered_orders(request)
#             if not orders_df.empty:
#                 conn.register("filtered_orders", orders_df)
                
#                 try:
#                     data_df = conn.execute("""
#                         SELECT
#                             oc.order_guid,
#                             oc.date,
#                             oc.oper_type,
#                             COALESCE(oc.oper_name, '') as oper_name,
#                             COALESCE(oc.cash_deck, '') as cash_deck,
#                             COALESCE(oc.doc_number, '') as doc_number,
#                             oc.amount,
#                             COALESCE(oc.store, '') as store,
#                             COALESCE(oc.register, '') as register
#                         FROM orders_cf oc
#                         INNER JOIN filtered_orders fo ON fo.id = oc.order_guid
#                         ORDER BY oc.date DESC
#                     """).df()
#                 except:
#                     return []
#             else:
#                 return []
#         else:
#             # Все оплаты
#             try:
#                 data_df = conn.execute("""
#                     SELECT
#                         order_guid,
#                         date,
#                         oper_type,
#                         COALESCE(oper_name, '') as oper_name,
#                         COALESCE(cash_deck, '') as cash_deck,
#                         COALESCE(doc_number, '') as doc_number,
#                         amount,
#                         COALESCE(store, '') as store,
#                         COALESCE(register, '') as register
#                     FROM orders_cf
#                     ORDER BY date DESC
#                 """).df()
#             except:
#                 return []
        
#         # Конвертируем даты
#         if 'date' in data_df.columns and not data_df.empty:
#             data_df['date'] = pd.to_datetime(data_df['date']).dt.date
        
#         return data_df.to_dict('records')
    
#     @classmethod
#     def get_product_summary(cls, request):
#         """Получить сводку по товарам"""
#         conn = cls.get_connection()
        
#         orders_df = cls.get_filtered_orders(request)
        
#         if orders_df.empty:
#             return []
        
#         conn.register("filtered_orders", orders_df)
        
#         try:
#             summary_df = conn.execute("""
#                 SELECT
#                     ij.item_name,
#                     SUM(ij.qty) as total_qty,
#                     SUM(ij.amount) as total_amount,
#                     COUNT(DISTINCT ij.order_id) as orders_count
#                 FROM items_joined ij
#                 INNER JOIN filtered_orders fo ON fo.id = ij.order_id
#                 GROUP BY ij.item_name
#                 ORDER BY total_amount DESC
#             """).df()
#         except:
#             return []
        
#         return summary_df.to_dict('records')





# orders/reports/queries/duckdb_queries.py
import pandas as pd
import duckdb
from django.db import connection
from datetime import date


class DuckDBReportQueries:
    """Базовые запросы к DuckDB для отчетов"""
    
    _conn = None
    
    @classmethod
    def get_connection(cls):
        """Получить соединение с DuckDB"""
        if cls._conn is None:
            cls._conn = duckdb.connect(':memory:')
        return cls._conn
    
    @classmethod
    def close_connection(cls):
        """Закрыть соединение с DuckDB"""
        if cls._conn is not None:
            cls._conn.close()
            cls._conn = None
    
    @classmethod
    def get_orders_data(cls, request=None, filters=None):
        """Получить DataFrame с заказами (алиас для get_filtered_orders)"""
        return cls.get_filtered_orders(request=request, filters=filters)
    
    @classmethod
    def get_filtered_orders(cls, request=None, filters=None):
        """Получить DataFrame с заказами с учетом фильтров"""
        from orders.models import Order
        
        # Получаем queryset заказов
        queryset = Order.objects.all()
        
        # Применяем фильтры из request
        if request and request.GET:
            if request.GET.get('status'):
                queryset = queryset.filter(status=request.GET.get('status'))
            if request.GET.get('date_from'):
                queryset = queryset.filter(date_from__gte=request.GET.get('date_from'))
            if request.GET.get('manager'):
                queryset = queryset.filter(manager=request.GET.get('manager'))
            if request.GET.get('client'):
                queryset = queryset.filter(client__icontains=request.GET.get('client'))
        
        if filters:
            if filters.get('status'):
                queryset = queryset.filter(status__in=filters['status'])
            if filters.get('date_from'):
                queryset = queryset.filter(date_from__gte=filters['date_from'])
            if filters.get('date_to'):
                queryset = queryset.filter(date_from__lte=filters['date_to'])
            if filters.get('manager'):
                queryset = queryset.filter(manager=filters['manager'])
            if filters.get('client'):
                queryset = queryset.filter(client__icontains=filters['client'])
        
        # Загружаем заказы
        orders_data = list(queryset.values(
            'id', 'number', 'client', 'manager', 'status', 
            'is_cancelled', 'date_from'
        ))
        
        if not orders_data:
            return pd.DataFrame()
        
        orders_df = pd.DataFrame(orders_data)
        
        # Загружаем позиции заказов и конвертируем amount в float
        order_ids = orders_df['id'].tolist()
        
        if order_ids:
            placeholders = ','.join(['%s'] * len(order_ids))
            
            with connection.cursor() as cursor:
                query = f"""
                    SELECT order_id, amount
                    FROM orders_orderitem
                    WHERE order_id IN ({placeholders})
                """
                cursor.execute(query, order_ids)
                items_data = cursor.fetchall()
            
            if items_data:
                items_df = pd.DataFrame(items_data, columns=['order_id', 'amount'])
                # Конвертируем amount в float
                items_df['amount'] = pd.to_numeric(items_df['amount'], errors='coerce').fillna(0).astype(float)
                conn = cls.get_connection()
                conn.register('order_items', items_df)
            else:
                conn = cls.get_connection()
                empty_items = pd.DataFrame(columns=['order_id', 'amount'])
                conn.register('order_items', empty_items)
        
        # Загружаем платежи и конвертируем amount в float
        if order_ids:
            placeholders = ','.join(['%s'] * len(order_ids))
            
            with connection.cursor() as cursor:
                query = f"""
                    SELECT order_guid, amount
                    FROM orders_orderscf
                    WHERE order_guid IN ({placeholders})
                """
                cursor.execute(query, order_ids)
                payments_data = cursor.fetchall()
            
            if payments_data:
                payments_df = pd.DataFrame(payments_data, columns=['order_guid', 'amount'])
                # Конвертируем amount в float
                payments_df['amount'] = pd.to_numeric(payments_df['amount'], errors='coerce').fillna(0).astype(float)
                conn = cls.get_connection()
                conn.register('orders_cf', payments_df)
            else:
                conn = cls.get_connection()
                empty_payments = pd.DataFrame(columns=['order_guid', 'amount'])
                conn.register('orders_cf', empty_payments)
        
        return orders_df
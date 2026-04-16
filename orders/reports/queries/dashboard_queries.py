# # orders/reports/queries/dashboard_queries.py
# from django.db import connection
# from datetime import date


# class DashboardQueries:
#     """Запросы для дашборда - через прямой SQL"""
    
#     ACTIVE_STATUSES = ("На согласовании", "К выполнению / В резерве")
    
#     @classmethod
#     def _format_statuses(cls):
#         """Форматирует статусы для SQL IN"""
#         return "', '".join(cls.ACTIVE_STATUSES)
    
#     @classmethod
#     def get_dashboard_data(cls, request=None, filters=None):
#         """Получить все данные для дашборда через прямой SQL"""
        
#         statuses_str = cls._format_statuses()
#         today = date.today()
#         year_start = date(today.year, 1, 1)
#         month_start = date(today.year, today.month, 1)
        
#         with connection.cursor() as cursor:
#             # 1. KPI по активным заказам (неотмененным)
#             cursor.execute(f"""
#                 SELECT 
#                     COUNT(DISTINCT o.id) as active_orders,
#                     COALESCE(SUM(oi.amount), 0) as active_amount,
#                     COALESCE(SUM(ocf.paid), 0) as active_paid,
#                     COALESCE(AVG(oi.amount), 0) as active_avg_check,
#                     COALESCE(SUM(oi.amount), 0) - COALESCE(SUM(ocf.paid), 0) as active_debt
#                 FROM orders_order o
#                 LEFT JOIN (
#                     SELECT order_id, SUM(amount) as amount
#                     FROM orders_orderitem
#                     GROUP BY order_id
#                 ) oi ON oi.order_id = o.id
#                 LEFT JOIN (
#                     SELECT ocf.order_guid, SUM(ocf.amount) as paid
#                     FROM orders_orderscf ocf
#                     INNER JOIN orders_order o2 ON ocf.order_guid = o2.id
#                     WHERE o2.status IN ('{statuses_str}') AND o2.is_cancelled = 0
#                     GROUP BY ocf.order_guid
#                 ) ocf ON ocf.order_guid = o.id
#                 WHERE o.status IN ('{statuses_str}') AND o.is_cancelled = 0
#             """)
#             kpi = cursor.fetchone()
            
#             # 2. Отмененные заказы
#             cursor.execute(f"""
#                 SELECT 
#                     COUNT(DISTINCT o.id) as cancelled_orders,
#                     COALESCE(SUM(oi.amount), 0) as cancelled_amount
#                 FROM orders_order o
#                 LEFT JOIN (
#                     SELECT order_id, SUM(amount) as amount
#                     FROM orders_orderitem
#                     GROUP BY order_id
#                 ) oi ON oi.order_id = o.id
#                 WHERE o.status IN ('{statuses_str}') AND o.is_cancelled = 1
#             """)
#             cancelled = cursor.fetchone()
            
#             # 3. YTD (с начала года)
#             cursor.execute(f"""
#                 SELECT 
#                     COUNT(DISTINCT o.id) as orders,
#                     COALESCE(SUM(oi.amount), 0) as amount,
#                     COALESCE(SUM(ocf.paid), 0) as paid,
#                     COALESCE(SUM(oi.amount), 0) - COALESCE(SUM(ocf.paid), 0) as debt
#                 FROM orders_order o
#                 LEFT JOIN (
#                     SELECT order_id, SUM(amount) as amount
#                     FROM orders_orderitem
#                     GROUP BY order_id
#                 ) oi ON oi.order_id = o.id
#                 LEFT JOIN (
#                     SELECT ocf.order_guid, SUM(ocf.amount) as paid
#                     FROM orders_orderscf ocf
#                     INNER JOIN orders_order o2 ON ocf.order_guid = o2.id
#                     WHERE o2.status IN ('{statuses_str}') 
#                         AND o2.is_cancelled = 0
#                         AND o2.date_from >= '{year_start}'
#                     GROUP BY ocf.order_guid
#                 ) ocf ON ocf.order_guid = o.id
#                 WHERE o.status IN ('{statuses_str}') 
#                     AND o.is_cancelled = 0
#                     AND o.date_from >= '{year_start}'
#             """)
#             ytd = cursor.fetchone()
            
#             # 4. MTD (с начала месяца)
#             cursor.execute(f"""
#                 SELECT 
#                     COUNT(DISTINCT o.id) as orders,
#                     COALESCE(SUM(oi.amount), 0) as amount,
#                     COALESCE(SUM(ocf.paid), 0) as paid,
#                     COALESCE(SUM(oi.amount), 0) - COALESCE(SUM(ocf.paid), 0) as debt
#                 FROM orders_order o
#                 LEFT JOIN (
#                     SELECT order_id, SUM(amount) as amount
#                     FROM orders_orderitem
#                     GROUP BY order_id
#                 ) oi ON oi.order_id = o.id
#                 LEFT JOIN (
#                     SELECT ocf.order_guid, SUM(ocf.amount) as paid
#                     FROM orders_orderscf ocf
#                     INNER JOIN orders_order o2 ON ocf.order_guid = o2.id
#                     WHERE o2.status IN ('{statuses_str}') 
#                         AND o2.is_cancelled = 0
#                         AND o2.date_from >= '{month_start}'
#                     GROUP BY ocf.order_guid
#                 ) ocf ON ocf.order_guid = o.id
#                 WHERE o.status IN ('{statuses_str}') 
#                     AND o.is_cancelled = 0
#                     AND o.date_from >= '{month_start}'
#             """)
#             mtd = cursor.fetchone()
            
#             # 5. Дебиторы (все с долгом > 0)
#             cursor.execute(f"""
#                 SELECT 
#                     COALESCE(o.client, 'НЕ УКАЗАН') as client,
#                     o.id as order_id,
#                     o.fullname as order_number,
#                     o.date_from as order_date,
#                     COALESCE(oi.amount, 0) as order_amount,
#                     COALESCE(ocf.paid, 0) as paid_amount,
#                     COALESCE(oi.amount, 0) - COALESCE(ocf.paid, 0) as debt
#                 FROM orders_order o
#                 LEFT JOIN (
#                     SELECT order_id, SUM(amount) as amount
#                     FROM orders_orderitem
#                     GROUP BY order_id
#                 ) oi ON oi.order_id = o.id
#                 LEFT JOIN (
#                     SELECT ocf.order_guid, SUM(ocf.amount) as paid
#                     FROM orders_orderscf ocf
#                     INNER JOIN orders_order o2 ON ocf.order_guid = o2.id
#                     WHERE o2.status IN ('{statuses_str}') AND o2.is_cancelled = 0
#                     GROUP BY ocf.order_guid
#                 ) ocf ON ocf.order_guid = o.id
#                 WHERE o.status IN ('{statuses_str}') AND o.is_cancelled = 0
#                 HAVING debt > 0
#                 ORDER BY debt DESC
#             """)
#             debtors = []
#             for row in cursor.fetchall():
#                 debtors.append({
#                     'client': row[0],
#                     'order_id': row[1],
#                     'order_number': row[2],
#                     'order_date': row[3],
#                     'order_amount': float(row[4]),
#                     'paid_amount': float(row[5]),
#                     'debt': float(row[6])
#                 })
            
#             # 6. Топ менеджеров
#             cursor.execute(f"""
#                 SELECT 
#                     COALESCE(o.manager, 'Не назначен') as manager,
#                     COUNT(DISTINCT o.id) as orders_count,
#                     COALESCE(SUM(oi.amount), 0) as total_amount,
#                     COALESCE(AVG(oi.amount), 0) as avg_check
#                 FROM orders_order o
#                 LEFT JOIN (
#                     SELECT order_id, SUM(amount) as amount
#                     FROM orders_orderitem
#                     GROUP BY order_id
#                 ) oi ON oi.order_id = o.id
#                 WHERE o.status IN ('{statuses_str}') AND o.is_cancelled = 0
#                 GROUP BY o.manager
#                 ORDER BY total_amount DESC
#                 LIMIT 100
#             """)
#             managers_top = []
#             for row in cursor.fetchall():
#                 managers_top.append({
#                     'manager': row[0],
#                     'orders_count': row[1],
#                     'total_amount': float(row[2]),
#                     'avg_check': float(row[3])
#                 })
            
#             # 7. Топ клиентов
#             cursor.execute(f"""
#                 SELECT 
#                     COALESCE(UPPER(o.client), 'НЕ УКАЗАН') as client,
#                     COUNT(DISTINCT o.id) as orders_count,
#                     COALESCE(SUM(oi.amount), 0) as total_amount,
#                     COALESCE(AVG(oi.amount), 0) as avg_check
#                 FROM orders_order o
#                 LEFT JOIN (
#                     SELECT order_id, SUM(amount) as amount
#                     FROM orders_orderitem
#                     GROUP BY order_id
#                 ) oi ON oi.order_id = o.id
#                 WHERE o.status IN ('{statuses_str}') AND o.is_cancelled = 0
#                 GROUP BY o.client
#                 ORDER BY total_amount DESC
#                 LIMIT 15
#             """)
#             clients_top = []
#             for row in cursor.fetchall():
#                 clients_top.append({
#                     'client': row[0],
#                     'orders_count': row[1],
#                     'total_amount': float(row[2]),
#                     'avg_check': float(row[3])
#                 })
            
#             return {
#                 'kpi': {
#                     'active_orders': int(kpi[0] or 0),
#                     'active_amount': float(kpi[1] or 0),
#                     'active_paid': float(kpi[2] or 0),
#                     'active_avg_check': float(kpi[3] or 0),
#                     'active_debt': float(kpi[4] or 0),
#                     'cancelled_orders': int(cancelled[0] or 0),
#                     'cancelled_amount': float(cancelled[1] or 0)
#                 },
#                 'ytd': {
#                     'orders': int(ytd[0] or 0),
#                     'amount': float(ytd[1] or 0),
#                     'paid': float(ytd[2] or 0),
#                     'debt': float(ytd[3] or 0)
#                 },
#                 'mtd': {
#                     'orders': int(mtd[0] or 0),
#                     'amount': float(mtd[1] or 0),
#                     'paid': float(mtd[2] or 0),
#                     'debt': float(mtd[3] or 0)
#                 },
#                 'debtors': debtors,
#                 'managers_top': managers_top,
#                 'clients_top': clients_top
#             }
            
#     @classmethod
#     def get_active_debtors(cls, request=None, filters=None):
#         """Активная дебиторка - активные заказы с долгом > 0"""
#         statuses_str = cls._format_statuses()
        
#         with connection.cursor() as cursor:
#             cursor.execute(f"""
#                 SELECT 
#                     COALESCE(o.client, 'НЕ УКАЗАН') as client,
#                     o.id as order_id,
#                     o.fullname as order_number,
#                     o.date_from as order_date,
#                     o.status,
#                     COALESCE(oi.amount, 0) as order_amount,
#                     COALESCE(ocf.paid, 0) as paid_amount,
#                     COALESCE(oi.amount, 0) - COALESCE(ocf.paid, 0) as debt
#                 FROM orders_order o
#                 LEFT JOIN (
#                     SELECT order_id, SUM(amount) as amount
#                     FROM orders_orderitem
#                     GROUP BY order_id
#                 ) oi ON oi.order_id = o.id
#                 LEFT JOIN (
#                     SELECT ocf.order_guid, SUM(ocf.amount) as paid
#                     FROM orders_orderscf ocf
#                     INNER JOIN orders_order o2 ON ocf.order_guid = o2.id
#                     WHERE o2.status IN ('{statuses_str}') AND o2.is_cancelled = 0
#                     GROUP BY ocf.order_guid
#                 ) ocf ON ocf.order_guid = o.id
#                 WHERE o.status IN ('{statuses_str}') 
#                     AND o.is_cancelled = 0
#                 HAVING debt > 0
#                 ORDER BY debt DESC
#             """)
            
#             debtors = []
#             for row in cursor.fetchall():
#                 debtors.append({
#                     'client': row[0],
#                     'order_id': row[1],
#                     'order_number': row[2],
#                     'order_date': row[3],
#                     'status': row[4],
#                     'order_amount': float(row[5]),
#                     'paid_amount': float(row[6]),
#                     'debt': float(row[7])
#                 })
#             return debtors
    
#     @classmethod
#     def get_closed_debtors(cls, request=None, filters=None):
#         """Закрытая дебиторка - закрытые/выполненные заказы с долгом > 0"""
#         closed_statuses = ("Закрыт", "Выполнен", "Доставлен")
#         closed_str = "', '".join(closed_statuses)
        
#         with connection.cursor() as cursor:
#             cursor.execute(f"""
#                 SELECT 
#                     COALESCE(o.client, 'НЕ УКАЗАН') as client,
#                     o.id as order_id,
#                     o.fullname as order_number,
#                     o.date_from as order_date,
#                     o.status,
#                     COALESCE(oi.amount, 0) as order_amount,
#                     COALESCE(ocf.paid, 0) as paid_amount,
#                     COALESCE(oi.amount, 0) - COALESCE(ocf.paid, 0) as debt
#                 FROM orders_order o
#                 LEFT JOIN (
#                     SELECT order_id, SUM(amount) as amount
#                     FROM orders_orderitem
#                     GROUP BY order_id
#                 ) oi ON oi.order_id = o.id
#                 LEFT JOIN (
#                     SELECT order_guid, SUM(amount) as paid
#                     FROM orders_orderscf
#                     GROUP BY order_guid
#                 ) ocf ON ocf.order_guid = o.id
#                 WHERE o.status IN ('{closed_str}') 
#                     AND o.is_cancelled = 0
#                 HAVING debt > 0
#                 ORDER BY debt DESC
#             """)
            
#             debtors = []
#             for row in cursor.fetchall():
#                 debtors.append({
#                     'client': row[0],
#                     'order_id': row[1],
#                     'order_number': row[2],
#                     'order_date': row[3],
#                     'status': row[4],
#                     'order_amount': float(row[5]),
#                     'paid_amount': float(row[6]),
#                     'debt': float(row[7])
#                 })
#             return debtors
        
        


#         @classmethod
#         def get_status_summary(cls, request=None, filters=None):
#             """Получить сводку по статусам заказов (из DuckDB через orders_summary)"""
#             # Если у вас уже есть orders_summary в DuckDB, используйте его
#             # Или прямой SQL запрос
            
#             statuses_str = cls._format_statuses()
            
#             with connection.cursor() as cursor:
#                 cursor.execute(f"""
#                     SELECT 
#                         o.status as "Статус заказа",
#                         COUNT(DISTINCT o.id) as "Всего заказов",
#                         SUM(CASE WHEN o.is_cancelled = 1 THEN 1 ELSE 0 END) as "в т.ч отменено",
#                         SUM(CASE WHEN o.is_cancelled = 0 THEN 1 ELSE 0 END) as "в т.ч выполнено / выполняется",
#                         COALESCE(SUM(oi.qty), 0) as "Ед заказано",
#                         COALESCE(SUM(CASE WHEN o.is_cancelled = 1 THEN oi.qty ELSE 0 END), 0) as "в т.ч отменено_ед",
#                         COALESCE(SUM(CASE WHEN o.is_cancelled = 0 THEN oi.qty ELSE 0 END), 0) as "в т.ч выполнено / выполняется_ед",
#                         COALESCE(SUM(oi.amount), 0) as "Сумма заказов",
#                         COALESCE(SUM(CASE WHEN o.is_cancelled = 1 THEN oi.amount ELSE 0 END), 0) as "в т.ч отменено_сумма",
#                         COALESCE(SUM(CASE WHEN o.is_cancelled = 0 THEN oi.amount ELSE 0 END), 0) as "в т.ч выполнено / выполняется_сумма",
#                         COALESCE(SUM(ocf.paid), 0) as "Оплачено на дату",
#                         COALESCE(SUM(s.shiped), 0) as "Отгружено ед на дату",
#                         COALESCE(SUM(s.returned), 0) as "Возвраты ед на дату",
#                         COALESCE(SUM(s.shiped_amount), 0) as "Реализация на дату (руб)",
#                         COALESCE(SUM(s.returned_amount), 0) as "Возвращено на дату (руб)",
#                         COALESCE(SUM(s.shiped_amount - s.returned_amount), 0) as "Всего реализация"
#                     FROM orders_order o
#                     LEFT JOIN (
#                         SELECT order_id, SUM(qty) as qty, SUM(amount) as amount
#                         FROM orders_orderitem
#                         GROUP BY order_id
#                     ) oi ON oi.order_id = o.id
#                     LEFT JOIN (
#                         SELECT ocf.order_guid, SUM(ocf.amount) as paid
#                         FROM orders_orderscf ocf
#                         GROUP BY ocf.order_guid
#                     ) ocf ON ocf.order_guid = o.id
#                     LEFT JOIN (
#                         SELECT order_guid, SUM(quant_dt) as shiped, SUM(quant_cr) as returned,
#                             SUM(dt) as shiped_amount, SUM(cr) as returned_amount
#                         FROM sales_salesdata
#                         GROUP BY order_guid
#                     ) s ON s.order_guid = o.id
#                     GROUP BY o.status
#                     ORDER BY "Всего заказов" DESC
#                 """)
                
#                 columns = [col[0] for col in cursor.description]
#                 status_summary = []
#                 for row in cursor.fetchall():
#                     status_summary.append(dict(zip(columns, row)))
                
#                 return status_summary
            


#     @classmethod
#     def get_status_summary(cls, request=None, filters=None):
#         """Получить сводку по статусам заказов"""
        
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT 
#                     o.status as "Статус заказа",
#                     COUNT(DISTINCT o.id) as "Всего заказов",
#                     SUM(CASE WHEN o.is_cancelled = 1 THEN 1 ELSE 0 END) as "в т.ч отменено",
#                     SUM(CASE WHEN o.is_cancelled = 0 THEN 1 ELSE 0 END) as "в т.ч выполнено / выполняется",
#                     COALESCE(SUM(oi.qty), 0) as "Ед заказано",
#                     COALESCE(SUM(CASE WHEN o.is_cancelled = 1 THEN oi.qty ELSE 0 END), 0) as "в т.ч отменено_ед",
#                     COALESCE(SUM(CASE WHEN o.is_cancelled = 0 THEN oi.qty ELSE 0 END), 0) as "в т.ч выполнено / выполняется_ед",
#                     COALESCE(SUM(oi.amount), 0) as "Сумма заказов",
#                     COALESCE(SUM(CASE WHEN o.is_cancelled = 1 THEN oi.amount ELSE 0 END), 0) as "в т.ч отменено_сумма",
#                     COALESCE(SUM(CASE WHEN o.is_cancelled = 0 THEN oi.amount ELSE 0 END), 0) as "в т.ч выполнено / выполняется_сумма",
#                     COALESCE(SUM(ocf.paid), 0) as "Оплачено на дату",
#                     COALESCE(SUM(s.shiped), 0) as "Отгружено ед на дату",
#                     COALESCE(SUM(s.returned), 0) as "Возвраты ед на дату",
#                     COALESCE(SUM(s.shiped_amount), 0) as "Реализация на дату (руб)",
#                     COALESCE(SUM(s.returned_amount), 0) as "Возвращено на дату (руб)",
#                     COALESCE(SUM(s.shiped_amount - s.returned_amount), 0) as "Всего реализация"
#                 FROM orders_order o
#                 LEFT JOIN (
#                     SELECT order_id, SUM(qty) as qty, SUM(amount) as amount
#                     FROM orders_orderitem
#                     GROUP BY order_id
#                 ) oi ON oi.order_id = o.id
#                 LEFT JOIN (
#                     SELECT ocf.order_guid, SUM(ocf.amount) as paid
#                     FROM orders_orderscf ocf
#                     GROUP BY ocf.order_guid
#                 ) ocf ON ocf.order_guid = o.id
#                 LEFT JOIN (
#                     SELECT order_guid, 
#                            SUM(quant_dt) as shiped, 
#                            SUM(quant_cr) as returned,
#                            SUM(dt) as shiped_amount, 
#                            SUM(cr) as returned_amount
#                     FROM sales_salesdata
#                     GROUP BY order_guid
#                 ) s ON s.order_guid = o.id
#                 GROUP BY o.status
#                 ORDER BY "Всего заказов" DESC
#             """)
            
#             columns = [col[0] for col in cursor.description]
#             status_summary = []
#             for row in cursor.fetchall():
#                 status_summary.append(dict(zip(columns, row)))
            
#             return status_summary




# orders/reports/queries/dashboard_queries.py
from django.db import connection
from datetime import date


class DashboardQueries:
    """Запросы для дашборда - через прямой SQL"""
    
    ACTIVE_STATUSES = ("На согласовании", "К выполнению / В резерве")
    CLOSED_STATUSES = ("Закрыт", "Выполнен", "Доставлен")
    
    @classmethod
    def _format_statuses(cls, statuses=None):
        """Форматирует статусы для SQL IN"""
        if statuses is None:
            statuses = cls.ACTIVE_STATUSES
        return "', '".join(statuses)
    
    @classmethod
    def get_dashboard_data(cls, request=None, filters=None):
        """Получить все данные для дашборда через прямой SQL"""
        
        statuses_str = cls._format_statuses()
        today = date.today()
        year_start = date(today.year, 1, 1)
        month_start = date(today.year, today.month, 1)
        
        with connection.cursor() as cursor:
            # 1. KPI по активным заказам (неотмененным)
            cursor.execute(f"""
                SELECT
                    COUNT(*) as active_orders,
                    COALESCE(SUM(t.order_amount), 0) as active_amount,
                    COALESCE(SUM(t.paid_amount), 0) as active_paid,
                    COALESCE(AVG(t.order_amount), 0) as active_avg_check,
                    COALESCE(SUM(CASE WHEN t.debt > 0 THEN t.debt ELSE 0 END), 0) as active_debt
                FROM (
                    SELECT
                        o.id,
                        COALESCE(oi.amount, 0) as order_amount,
                        COALESCE(ocf.paid, 0) as paid_amount,
                        COALESCE(oi.amount, 0) - COALESCE(ocf.paid, 0) as debt
                    FROM orders_order o
                    LEFT JOIN (
                        SELECT order_id, SUM(amount) as amount
                        FROM orders_orderitem
                        GROUP BY order_id
                    ) oi ON oi.order_id = o.id
                    LEFT JOIN (
                        SELECT ocf.order_guid, SUM(ocf.amount) as paid
                        FROM orders_orderscf ocf
                        GROUP BY ocf.order_guid
                    ) ocf ON ocf.order_guid = o.id
                    WHERE o.status IN ('{statuses_str}')
                    AND o.is_cancelled = 0
                ) t
            """)
            kpi = cursor.fetchone()
            
            # 2. Отмененные заказы
            cursor.execute(f"""
                SELECT 
                    COUNT(DISTINCT o.id) as cancelled_orders,
                    COALESCE(SUM(oi.amount), 0) as cancelled_amount
                FROM orders_order o
                LEFT JOIN (
                    SELECT order_id, SUM(amount) as amount
                    FROM orders_orderitem
                    GROUP BY order_id
                ) oi ON oi.order_id = o.id
                WHERE o.status IN ('{statuses_str}') AND o.is_cancelled = 0
            """)
            cancelled = cursor.fetchone()
            
            # 3. YTD (с начала года)
            cursor.execute(f"""
                SELECT 
                    COUNT(DISTINCT o.id) as orders,
                    COALESCE(SUM(oi.amount), 0) as amount,
                    COALESCE(SUM(ocf.paid), 0) as paid,
                    COALESCE(SUM(oi.amount), 0) - COALESCE(SUM(ocf.paid), 0) as debt
                FROM orders_order o
                LEFT JOIN (
                    SELECT order_id, SUM(amount) as amount
                    FROM orders_orderitem
                    GROUP BY order_id
                ) oi ON oi.order_id = o.id
                LEFT JOIN (
                    SELECT ocf.order_guid, SUM(ocf.amount) as paid
                    FROM orders_orderscf ocf
                    INNER JOIN orders_order o2 ON ocf.order_guid = o2.id
                    WHERE o2.status IN ('{statuses_str}') 
                        AND o2.is_cancelled = 0
                        AND o2.date_from >= '{year_start}'
                    GROUP BY ocf.order_guid
                ) ocf ON ocf.order_guid = o.id
                WHERE o.status IN ('{statuses_str}') 
                    AND o.is_cancelled = 0
                    AND o.date_from >= '{year_start}'
            """)
            ytd = cursor.fetchone()
            
            # 4. MTD (с начала месяца)
            cursor.execute(f"""
                SELECT 
                    COUNT(DISTINCT o.id) as orders,
                    COALESCE(SUM(oi.amount), 0) as amount,
                    COALESCE(SUM(ocf.paid), 0) as paid,
                    COALESCE(SUM(oi.amount), 0) - COALESCE(SUM(ocf.paid), 0) as debt
                FROM orders_order o
                LEFT JOIN (
                    SELECT order_id, SUM(amount) as amount
                    FROM orders_orderitem
                    GROUP BY order_id
                ) oi ON oi.order_id = o.id
                LEFT JOIN (
                    SELECT ocf.order_guid, SUM(ocf.amount) as paid
                    FROM orders_orderscf ocf
                    INNER JOIN orders_order o2 ON ocf.order_guid = o2.id
                    WHERE o2.status IN ('{statuses_str}') 
                        AND o2.is_cancelled = 0
                        AND o2.date_from >= '{month_start}'
                    GROUP BY ocf.order_guid
                ) ocf ON ocf.order_guid = o.id
                WHERE o.status IN ('{statuses_str}') 
                    AND o.is_cancelled = 0
                    AND o.date_from >= '{month_start}'
            """)
            mtd = cursor.fetchone()
            
            # 5. Дебиторы (все с долгом > 0) - ЕДИНЫЙ ЗАПРОС
            debtors = cls._get_debtors_query(statuses_str, include_status=False)
            
            # 6. Топ менеджеров
            cursor.execute(f"""
                SELECT 
                    COALESCE(o.manager, 'Не назначен') as manager,
                    COUNT(DISTINCT o.id) as orders_count,
                    COALESCE(SUM(oi.amount), 0) as total_amount,
                    COALESCE(AVG(oi.amount), 0) as avg_check
                FROM orders_order o
                LEFT JOIN (
                    SELECT order_id, SUM(amount) as amount
                    FROM orders_orderitem
                    GROUP BY order_id
                ) oi ON oi.order_id = o.id
                WHERE o.status IN ('{statuses_str}') AND o.is_cancelled = 0
                GROUP BY o.manager
                ORDER BY total_amount DESC
                LIMIT 100
            """)
            managers_top = []
            for row in cursor.fetchall():
                managers_top.append({
                    'manager': row[0],
                    'orders_count': row[1],
                    'total_amount': float(row[2]),
                    'avg_check': float(row[3])
                })
            
            # 7. Топ клиентов
            cursor.execute(f"""
                SELECT 
                    COALESCE(UPPER(o.client), 'НЕ УКАЗАН') as client,
                    COUNT(DISTINCT o.id) as orders_count,
                    COALESCE(SUM(oi.amount), 0) as total_amount,
                    COALESCE(AVG(oi.amount), 0) as avg_check
                FROM orders_order o
                LEFT JOIN (
                    SELECT order_id, SUM(amount) as amount
                    FROM orders_orderitem
                    GROUP BY order_id
                ) oi ON oi.order_id = o.id
                WHERE o.status IN ('{statuses_str}') AND o.is_cancelled = 0
                GROUP BY o.client
                ORDER BY total_amount DESC
                LIMIT 15
            """)
            clients_top = []
            for row in cursor.fetchall():
                clients_top.append({
                    'client': row[0],
                    'orders_count': row[1],
                    'total_amount': float(row[2]),
                    'avg_check': float(row[3])
                })
            
            return {
                'kpi': {
                    'active_orders': int(kpi[0] or 0),
                    'active_amount': float(kpi[1] or 0),
                    'active_paid': float(kpi[2] or 0),
                    'active_avg_check': float(kpi[3] or 0),
                    'active_debt': float(kpi[4] or 0),
                    'cancelled_orders': int(cancelled[0] or 0),
                    'cancelled_amount': float(cancelled[1] or 0)
                },
                'ytd': {
                    'orders': int(ytd[0] or 0),
                    'amount': float(ytd[1] or 0),
                    'paid': float(ytd[2] or 0),
                    'debt': float(ytd[3] or 0)
                },
                'mtd': {
                    'orders': int(mtd[0] or 0),
                    'amount': float(mtd[1] or 0),
                    'paid': float(mtd[2] or 0),
                    'debt': float(mtd[3] or 0)
                },
                'debtors': debtors,
                'managers_top': managers_top,
                'clients_top': clients_top
            }
    
    @classmethod
    def _get_debtors_query(cls, statuses_str, include_status=False):
        """Внутренний метод для получения дебиторов (единая логика)"""
        with connection.cursor() as cursor:
            status_field = ", o.status" if include_status else ""
            
            cursor.execute(f"""
                SELECT 
                    COALESCE(o.client, 'НЕ УКАЗАН') as client,
                    o.id as order_id,
                    o.fullname as order_number,
                    o.date_from as order_date
                    {status_field},
                    COALESCE(oi.amount, 0) as order_amount,
                    COALESCE(ocf.paid, 0) as paid_amount,
                    COALESCE(oi.amount, 0) - COALESCE(ocf.paid, 0) as debt
                FROM orders_order o
                LEFT JOIN (
                    SELECT order_id, SUM(amount) as amount
                    FROM orders_orderitem
                    GROUP BY order_id
                ) oi ON oi.order_id = o.id
                LEFT JOIN (
                    SELECT ocf.order_guid, SUM(ocf.amount) as paid
                    FROM orders_orderscf ocf
                    INNER JOIN orders_order o2 ON ocf.order_guid = o2.id
                    WHERE o2.status IN ('{statuses_str}') AND o2.is_cancelled = 0
                    GROUP BY ocf.order_guid
                ) ocf ON ocf.order_guid = o.id
                WHERE o.status IN ('{statuses_str}') 
                    AND o.is_cancelled = 0
                HAVING debt > 0
                ORDER BY debt DESC
            """)
            
            debtors = []
            for row in cursor.fetchall():
                if include_status:
                    # С полем status
                    debtors.append({
                        'client': row[0],
                        'order_id': row[1],
                        'order_number': row[2],
                        'order_date': row[3],
                        'status': row[4],
                        'order_amount': float(row[5]),
                        'paid_amount': float(row[6]),
                        'debt': float(row[7])
                    })
                else:
                    # Без поля status
                    debtors.append({
                        'client': row[0],
                        'order_id': row[1],
                        'order_number': row[2],
                        'order_date': row[3],
                        'order_amount': float(row[4]),
                        'paid_amount': float(row[5]),
                        'debt': float(row[6])
                    })
            return debtors
    
    @classmethod
    def get_active_debtors(cls, request=None, filters=None):
        """Активная дебиторка - активные заказы с долгом > 0"""
        statuses_str = cls._format_statuses()
        return cls._get_debtors_query(statuses_str, include_status=True)
    
    @classmethod
    def get_closed_debtors(cls, request=None, filters=None):
        """Закрытая дебиторка - закрытые/выполненные заказы с долгом > 0"""
        closed_str = cls._format_statuses(cls.CLOSED_STATUSES)
        
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    COALESCE(o.client, 'НЕ УКАЗАН') as client,
                    o.id as order_id,
                    o.fullname as order_number,
                    o.date_from as order_date,
                    o.status,
                    COALESCE(oi.amount, 0) as order_amount,
                    COALESCE(ocf.paid, 0) as paid_amount,
                    COALESCE(oi.amount, 0) - COALESCE(ocf.paid, 0) as debt
                FROM orders_order o
                LEFT JOIN (
                    SELECT order_id, SUM(amount) as amount
                    FROM orders_orderitem
                    GROUP BY order_id
                ) oi ON oi.order_id = o.id
                LEFT JOIN (
                    SELECT order_guid, SUM(amount) as paid
                    FROM orders_orderscf
                    GROUP BY order_guid
                ) ocf ON ocf.order_guid = o.id
                WHERE o.status IN ('{closed_str}') 
                    AND o.is_cancelled = 0
                HAVING debt > 0
                ORDER BY debt DESC
            """)
            
            debtors = []
            for row in cursor.fetchall():
                debtors.append({
                    'client': row[0],
                    'order_id': row[1],
                    'order_number': row[2],
                    'order_date': row[3],
                    'status': row[4],
                    'order_amount': float(row[5]),
                    'paid_amount': float(row[6]),
                    'debt': float(row[7])
                })
            return debtors
    
    @classmethod
    def get_status_summary(cls, request=None, filters=None):
        """Получить сводку по статусам заказов"""
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    o.status as "Статус заказа",
                    COUNT(DISTINCT o.id) as "Всего заказов",
                    SUM(CASE WHEN o.is_cancelled = 0 THEN 1 ELSE 0 END) as "в т.ч отменено",
                    SUM(CASE WHEN o.is_cancelled = 0 THEN 1 ELSE 0 END) as "в т.ч выполнено / выполняется",
                    COALESCE(SUM(oi.qty), 0) as "Ед заказано",
                    COALESCE(SUM(CASE WHEN o.is_cancelled = 1 THEN oi.qty ELSE 0 END), 0) as "в т.ч отменено_ед",
                    COALESCE(SUM(CASE WHEN o.is_cancelled = 0 THEN oi.qty ELSE 0 END), 0) as "в т.ч выполнено / выполняется_ед",
                    COALESCE(SUM(oi.amount), 0) as "Сумма заказов",
                    COALESCE(SUM(CASE WHEN o.is_cancelled = 1 THEN oi.amount ELSE 0 END), 0) as "в т.ч отменено_сумма",
                    COALESCE(SUM(CASE WHEN o.is_cancelled = 0 THEN oi.amount ELSE 0 END), 0) as "в т.ч выполнено / выполняется_сумма",
                    COALESCE(SUM(ocf.paid), 0) as "Оплачено на дату",
                    COALESCE(SUM(s.shiped), 0) as "Отгружено ед на дату",
                    COALESCE(SUM(s.returned), 0) as "Возвраты ед на дату",
                    COALESCE(SUM(s.shiped_amount), 0) as "Реализация на дату (руб)",
                    COALESCE(SUM(s.returned_amount), 0) as "Возвращено на дату (руб)",
                    COALESCE(SUM(s.shiped_amount - s.returned_amount), 0) as "Всего реализация"
                FROM orders_order o
                LEFT JOIN (
                    SELECT order_id, SUM(qty) as qty, SUM(amount) as amount
                    FROM orders_orderitem
                    GROUP BY order_id
                ) oi ON oi.order_id = o.id
                LEFT JOIN (
                    SELECT ocf.order_guid, SUM(ocf.amount) as paid
                    FROM orders_orderscf ocf
                    GROUP BY ocf.order_guid
                ) ocf ON ocf.order_guid = o.id
                LEFT JOIN (
                    SELECT order_guid, 
                           SUM(quant_dt) as shiped, 
                           SUM(quant_cr) as returned,
                           SUM(dt) as shiped_amount, 
                           SUM(cr) as returned_amount
                    FROM sales_salesdata
                    GROUP BY order_guid
                ) s ON s.order_guid = o.id
                GROUP BY o.status
                ORDER BY "Всего заказов" DESC
            """)
            
            columns = [col[0] for col in cursor.description]
            status_summary = []
            for row in cursor.fetchall():
                status_summary.append(dict(zip(columns, row)))
            
            return status_summary
    
    @classmethod
    def verify_debtors_match(cls):
        """Проверяет, совпадают ли суммы в разных запросах (для отладки)"""
        data = cls.get_dashboard_data()
        debtors_from_dashboard = data.get('debtors', [])
        debtors_from_method = cls.get_active_debtors()
        
        sum1 = sum(d.get('debt', 0) for d in debtors_from_dashboard)
        sum2 = sum(d.get('debt', 0) for d in debtors_from_method)
        
        print("=" * 50)
        print("ПРОВЕРКА СОВПАДЕНИЯ ДЕБИТОРОВ")
        print("=" * 50)
        print(f"Сумма долга из get_dashboard_data: {sum1:,.0f} ₽".replace(",", " "))
        print(f"Сумма долга из get_active_debtors:   {sum2:,.0f} ₽".replace(",", " "))
        print(f"Разница: {abs(sum1 - sum2):,.0f} ₽".replace(",", " "))
        print(f"Количество записей: {len(debtors_from_dashboard)} vs {len(debtors_from_method)}")
        
        if sum1 == sum2:
            print("✅ ДАННЫЕ СОВПАДАЮТ!")
        else:
            print("❌ ДАННЫЕ НЕ СОВПАДАЮТ! Проверьте фильтры.")
            
            # Найдем различия
            debt_dict1 = {d['order_id']: d['debt'] for d in debtors_from_dashboard}
            debt_dict2 = {d['order_id']: d['debt'] for d in debtors_from_method}
            
            all_ids = set(debt_dict1.keys()) | set(debt_dict2.keys())
            diff_count = 0
            for order_id in all_ids:
                debt1 = debt_dict1.get(order_id, 0)
                debt2 = debt_dict2.get(order_id, 0)
                if abs(debt1 - debt2) > 1:  # ignore float rounding
                    diff_count += 1
                    if diff_count <= 5:  # покажем первые 5 отличий
                        print(f"  Заказ {order_id}: {debt1:,.0f} ₽ vs {debt2:,.0f} ₽".replace(",", " "))
            
            if diff_count > 5:
                print(f"  ... и еще {diff_count - 5} отличий")
        
        return sum1 == sum2
# orders/reports/queries/dashboard_queries.py
import pandas as pd
from datetime import datetime, date
from .duckdb_queries import DuckDBReportQueries


class DashboardQueries:
    """Запросы для дашборда - общей аналитики"""
    
    @classmethod
    def get_dashboard_data(cls, request=None, filters=None):
        """Получить все данные для дашборда"""
        conn = DuckDBReportQueries.get_connection()
        
        orders_df = DuckDBReportQueries.get_filtered_orders(request=request, filters=filters)
        
        if orders_df.empty:
            return {
                'kpi': {},
                'ytd': {},
                'mtd': {},
                'debtors': [],
                'managers_top': [],
                'clients_top': [],
                'daily_dynamics': []
            }
        
        conn.register("source_orders", orders_df)
        
        today = date.today()
        year_start = date(today.year, 1, 1)
        month_start = date(today.year, today.month, 1)
        
        active_statuses = "('На согласовании', 'К выполнению / В резерве')"
        
        # 1. KPI
        kpi = conn.execute(f"""
            WITH order_items_sum AS (
                SELECT order_id, SUM(amount) as total_amount
                FROM order_items
                GROUP BY order_id
            ),
            order_payments AS (
                SELECT order_guid, SUM(amount) as paid_amount
                FROM orders_cf
                GROUP BY order_guid
            )
            SELECT
                COUNT(DISTINCT so.id) as active_orders,
                COALESCE(SUM(oit.total_amount), 0) as active_amount,
                COALESCE(SUM(op.paid_amount), 0) as active_paid,
                COALESCE(AVG(oit.total_amount), 0) as active_avg_check,
                COALESCE(SUM(oit.total_amount), 0) - COALESCE(SUM(op.paid_amount), 0) as active_debt,
                SUM(CASE WHEN so.is_cancelled = TRUE THEN 1 ELSE 0 END) as cancelled_orders,
                COALESCE(SUM(CASE WHEN so.is_cancelled = TRUE THEN oit.total_amount ELSE 0 END), 0) as cancelled_amount
            FROM source_orders so
            LEFT JOIN order_items_sum oit ON oit.order_id = so.id
            LEFT JOIN order_payments op ON op.order_guid = so.id
            WHERE so.status IN {active_statuses} AND so.is_cancelled = FALSE
        """).fetchone()
        
        # 2. YTD
        ytd = conn.execute(f"""
            WITH order_items_sum AS (
                SELECT order_id, SUM(amount) as total_amount
                FROM order_items
                GROUP BY order_id
            ),
            order_payments AS (
                SELECT order_guid, SUM(amount) as paid_amount
                FROM orders_cf
                GROUP BY order_guid
            )
            SELECT
                COUNT(DISTINCT so.id) as orders_count,
                COALESCE(SUM(oit.total_amount), 0) as total_amount,
                COALESCE(SUM(op.paid_amount), 0) as paid_amount,
                COALESCE(SUM(oit.total_amount), 0) - COALESCE(SUM(op.paid_amount), 0) as debt
            FROM source_orders so
            LEFT JOIN order_items_sum oit ON oit.order_id = so.id
            LEFT JOIN order_payments op ON op.order_guid = so.id
            WHERE so.status IN {active_statuses} 
              AND so.is_cancelled = FALSE
              AND so.date_from >= '{year_start}'
        """).fetchone()
        
        # 3. MTD
        mtd = conn.execute(f"""
            WITH order_items_sum AS (
                SELECT order_id, SUM(amount) as total_amount
                FROM order_items
                GROUP BY order_id
            ),
            order_payments AS (
                SELECT order_guid, SUM(amount) as paid_amount
                FROM orders_cf
                GROUP BY order_guid
            )
            SELECT
                COUNT(DISTINCT so.id) as orders_count,
                COALESCE(SUM(oit.total_amount), 0) as total_amount,
                COALESCE(SUM(op.paid_amount), 0) as paid_amount,
                COALESCE(SUM(oit.total_amount), 0) - COALESCE(SUM(op.paid_amount), 0) as debt
            FROM source_orders so
            LEFT JOIN order_items_sum oit ON oit.order_id = so.id
            LEFT JOIN order_payments op ON op.order_guid = so.id
            WHERE so.status IN {active_statuses} 
              AND so.is_cancelled = FALSE
              AND so.date_from >= '{month_start}'
        """).fetchone()
        
        # 4. Должники
        debtors = conn.execute(f"""
            WITH order_items_sum AS (
                SELECT order_id, SUM(amount) as total_amount
                FROM order_items
                GROUP BY order_id
            ),
            order_payments AS (
                SELECT order_guid, SUM(amount) as paid_amount
                FROM orders_cf
                GROUP BY order_guid
            )
            SELECT
                so.client,
                so.id as order_id,
                so.number as order_number,
                so.date_from as order_date,
                COALESCE(oit.total_amount, 0) as order_amount,
                COALESCE(op.paid_amount, 0) as paid_amount,
                COALESCE(oit.total_amount, 0) - COALESCE(op.paid_amount, 0) as debt
            FROM source_orders so
            LEFT JOIN order_items_sum oit ON oit.order_id = so.id
            LEFT JOIN order_payments op ON op.order_guid = so.id
            WHERE so.status IN {active_statuses} 
              AND so.is_cancelled = FALSE
              AND (COALESCE(oit.total_amount, 0) - COALESCE(op.paid_amount, 0)) > 0
            ORDER BY debt DESC
        """).df()
        
        # 5. Топ менеджеров
        managers_top = conn.execute(f"""
            WITH order_items_sum AS (
                SELECT order_id, SUM(amount) as total_amount
                FROM order_items
                GROUP BY order_id
            )
            SELECT
                COALESCE(so.manager, 'Не назначен') as manager,
                COUNT(DISTINCT so.id) as orders_count,
                COALESCE(SUM(oit.total_amount), 0) as total_amount,
                COALESCE(AVG(oit.total_amount), 0) as avg_check
            FROM source_orders so
            LEFT JOIN order_items_sum oit ON oit.order_id = so.id
            WHERE so.status IN {active_statuses} AND so.is_cancelled = FALSE
            GROUP BY so.manager
            ORDER BY total_amount DESC
            LIMIT 10
        """).df()
        
        # 6. Топ клиентов
        clients_top = conn.execute(f"""
            WITH order_items_sum AS (
                SELECT order_id, SUM(amount) as total_amount
                FROM order_items
                GROUP BY order_id
            )
            SELECT
                UPPER(COALESCE(so.client, 'НЕ УКАЗАН')) as client,
                COUNT(DISTINCT so.id) as orders_count,
                COALESCE(SUM(oit.total_amount), 0) as total_amount,
                COALESCE(AVG(oit.total_amount), 0) as avg_check
            FROM source_orders so
            LEFT JOIN order_items_sum oit ON oit.order_id = so.id
            WHERE so.status IN {active_statuses} AND so.is_cancelled = FALSE
            GROUP BY so.client
            ORDER BY total_amount DESC
            LIMIT 10
        """).df()
        
        return {
            'kpi': {
                'active_orders': int(kpi[0] or 0),
                'active_amount': float(kpi[1] or 0),
                'active_paid': float(kpi[2] or 0),
                'active_avg_check': float(kpi[3] or 0),
                'active_debt': float(kpi[4] or 0),
                'cancelled_orders': int(kpi[5] or 0),
                'cancelled_amount': float(kpi[6] or 0)
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
            'debtors': debtors.to_dict('records'),
            'managers_top': managers_top.to_dict('records'),
            'clients_top': clients_top.to_dict('records')
        }
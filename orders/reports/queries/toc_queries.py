# orders/reports/queries/toc_queries.py
import pandas as pd
from .duckdb_queries import DuckDBReportQueries


class TOCQueries:
    """Запросы для оглавления и несоответствий"""
    
    ACTIVE_STATUSES = ("На согласовании", "К выполнению / В резерве")
    
    @classmethod
    def _statuses_sql(cls):
        return "(" + ", ".join(f"'{s}'" for s in cls.ACTIVE_STATUSES) + ")"
    
    @classmethod
    def get_metrics_by_status(cls, request=None, filters=None):
        """Получить метрики по активным статусам"""
        conn = DuckDBReportQueries.get_connection()
        orders_df = DuckDBReportQueries.get_filtered_orders(request=request, filters=filters)
        
        if orders_df.empty:
            return {
                'agreement': {'count': 0, 'total_amount': 0, 'avg_check': 0},
                'execution': {'count': 0, 'total_amount': 0, 'avg_check': 0}
            }
        
        conn.register("source_orders", orders_df)
        
        # Метрики для статуса "На согласовании"
        agreement = conn.execute("""
            WITH order_items_sum AS (
                SELECT 
                    order_id,
                    SUM(COALESCE(CAST(amount AS DOUBLE), 0)) as total_amount
                FROM order_items
                GROUP BY order_id
            )
            SELECT
                COUNT(DISTINCT so.id) as cnt,
                COALESCE(SUM(oit.total_amount), 0) as total_amount,
                COALESCE(AVG(oit.total_amount), 0) as avg_check
            FROM source_orders so
            LEFT JOIN order_items_sum oit ON oit.order_id = so.id
            WHERE so.status = 'На согласовании' AND so.is_cancelled = FALSE
        """).fetchone()
        
        # Метрики для статуса "К выполнению / В резерве"
        execution = conn.execute("""
            WITH order_items_sum AS (
                SELECT 
                    order_id,
                    SUM(COALESCE(CAST(amount AS DOUBLE), 0)) as total_amount
                FROM order_items
                GROUP BY order_id
            )
            SELECT
                COUNT(DISTINCT so.id) as cnt,
                COALESCE(SUM(oit.total_amount), 0) as total_amount,
                COALESCE(AVG(oit.total_amount), 0) as avg_check
            FROM source_orders so
            LEFT JOIN order_items_sum oit ON oit.order_id = so.id
            WHERE so.status = 'К выполнению / В резерве' AND so.is_cancelled = FALSE
        """).fetchone()
        
        return {
            'agreement': {
                'count': int(agreement[0] or 0),
                'total_amount': float(agreement[1] or 0),
                'avg_check': float(agreement[2] or 0)
            },
            'execution': {
                'count': int(execution[0] or 0),
                'total_amount': float(execution[1] or 0),
                'avg_check': float(execution[2] or 0)
            }
        }
    
    @classmethod
    def get_inconsistencies(cls, request=None, filters=None):
        """Получить несоответствия - отмененные заказы с активными статусами"""
        conn = DuckDBReportQueries.get_connection()
        orders_df = DuckDBReportQueries.get_filtered_orders(request=request, filters=filters)
        
        if orders_df.empty:
            return {
                'agreement_cancelled': [],
                'execution_cancelled': []
            }
        
        conn.register("source_orders", orders_df)
        
        # Отмененные заказы со статусом "На согласовании"
        agreement_cancelled = conn.execute("""
            SELECT
                id,
                number,
                client,
                manager,
                date_from,
                status
            FROM source_orders
            WHERE status = 'На согласовании' 
              AND is_cancelled = TRUE
            ORDER BY date_from DESC
        """).df()
        
        # Отмененные заказы со статусом "К выполнению / В резерве"
        execution_cancelled = conn.execute("""
            SELECT
                id,
                number,
                client,
                manager,
                date_from,
                status
            FROM source_orders
            WHERE status = 'К выполнению / В резерве' 
              AND is_cancelled = TRUE
            ORDER BY date_from DESC
        """).df()
        
        return {
            'agreement_cancelled': agreement_cancelled.to_dict('records'),
            'execution_cancelled': execution_cancelled.to_dict('records')
        }
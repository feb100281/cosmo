# orders/reports/queries/__init__.py
from .executive_queries import ExecutiveQueries
from .base_queries import BaseQueries
from .period_queries import PeriodQueries
from .orders_detail_queries import OrdersDetailQueries 
from .delivery_analysis_query import DeliveryAnalysisQueries
from .manager_queries import ManagerQueries
from .client_analysis_query import ClientAnalysisQueries
from .payments_analysis_query import PaymentsAnalysisQueries 
# Старый dashboard_queries оставляем для обратной совместимости
from .dashboard_queries import DashboardQueries
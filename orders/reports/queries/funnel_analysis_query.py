# # orders/reports/queries/funnel_analysis_query.py
# from datetime import date
# from django.db.models import Q, Count, Sum, F, Case, When, Value, DecimalField
# from django.db.models.functions import Coalesce
# from orders.models import MV_Orders


# class FunnelAnalysisQueries:
#     CANCEL_STATUSES = ["Отменен", "Отменён"]
#     CLOSED_STATUSES = ["Закрыт", "Закрыто"]

#     def _get_date_filters(self, period="YTD"):
#         today = date.today()

#         if period == "YTD":
#             return {"date_from__gte": date(today.year, 1, 1)}

#         if period == "MTD":
#             return {"date_from__gte": date(today.year, today.month, 1)}

#         return {}

#     def _has_field(self, field_name):
#         try:
#             MV_Orders._meta.get_field(field_name)
#             return True
#         except Exception:
#             return False

#     def _period_name(self, period):
#         today = date.today()

#         if period == "YTD":
#             # Исправление: убираем повторение YTD YTD
#             return f"YTD с 01.01.{today.year}"

#         if period == "MTD":
#             return f"MTD с 01.{today.month:02d}.{today.year}"

#         return "За все время"

#     def _base_qs_all(self, period="YTD"):
#         qs = MV_Orders.objects.all()
#         date_filter = self._get_date_filters(period)

#         if date_filter:
#             qs = qs.filter(**date_filter)

#         return qs

#     def _canceled_filter(self):
#         q = Q(status__in=self.CANCEL_STATUSES)

#         if self._has_field("change_status"):
#             q |= Q(change_status__in=self.CANCEL_STATUSES)

#         return q

#     def _base_qs_active(self, period="YTD"):
#         return self._base_qs_all(period).exclude(self._canceled_filter())

#     def _pct(self, numerator, denominator):
#         return round(numerator / denominator * 100, 1) if denominator else 0

#     def _aggregate_funnel(self, qs):
#         return qs.aggregate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),
#             paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(cash_pmts__gt=0, then="cash_pmts"),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),
#             shipped_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             then="total_shiped_amount",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                 ),
#                 distinct=True,
#             ),
#             fully_paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             amount_active__gt=0,
#                             cash_pmts__gte=F("amount_active"),
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#             closed_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             amount_active__gt=0,
#                             cash_pmts__gte=F("amount_active"),
#                             status__in=self.CLOSED_STATUSES,
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),
#         )

#     def _get_canceled_summary(self, period="YTD"):
#         qs = self._base_qs_all(period).filter(self._canceled_filter())

#         agg = qs.aggregate(
#             canceled_orders=Count("order_id", distinct=True),
#             # Исправление: сумма отмен берется по колонке amount_cancelled
#             canceled_amount=Coalesce(Sum("amount_cancelled"), Value(0), output_field=DecimalField()),
#         )

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "canceled_orders": agg["canceled_orders"] or 0,
#             "canceled_amount": float(agg["canceled_amount"] or 0),
#         }

#     def _build_stages(self, agg):
#         total_orders = agg["total_orders"] or 0
#         paid_orders = agg["paid_orders"] or 0
#         shipped_orders = agg["shipped_orders"] or 0
#         fully_paid_orders = agg["fully_paid_orders"] or 0
#         closed_orders = agg["closed_orders"] or 0

#         return [
#             {
#                 "name": "1. Создано заказов",
#                 "orders": total_orders,
#                 "amount": float(agg["total_amount"] or 0),
#                 "conversion_from_prev": 100.0,
#                 "conversion_from_start": 100.0,
#             },
#             {
#                 "name": "2. Есть оплата",
#                 "orders": paid_orders,
#                 "amount": float(agg["paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(paid_orders, total_orders),
#                 "conversion_from_start": self._pct(paid_orders, total_orders),
#             },
#             {
#                 "name": "3. Есть отгрузка",
#                 "orders": shipped_orders,
#                 "amount": float(agg["shipped_amount"] or 0),
#                 "conversion_from_prev": self._pct(shipped_orders, paid_orders),
#                 "conversion_from_start": self._pct(shipped_orders, total_orders),
#             },
#             {
#                 "name": "4. Полностью оплачено",
#                 "orders": fully_paid_orders,
#                 "amount": float(agg["fully_paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(fully_paid_orders, shipped_orders),
#                 "conversion_from_start": self._pct(fully_paid_orders, total_orders),
#             },
#             {
#                 "name": "5. Закрыто в системе",
#                 "orders": closed_orders,
#                 "amount": float(agg["closed_amount"] or 0),
#                 "conversion_from_prev": self._pct(closed_orders, fully_paid_orders),
#                 "conversion_from_start": self._pct(closed_orders, total_orders),
#             },
#         ]

#     def _get_funnel_for_period(self, period="YTD"):
#         qs = self._base_qs_active(period)
#         agg = self._aggregate_funnel(qs)
#         stages = self._build_stages(agg)
#         canceled = self._get_canceled_summary(period)

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "total_orders": agg["total_orders"] or 0,
#             "total_amount": float(agg["total_amount"] or 0),
#             "canceled_orders": canceled["canceled_orders"],
#             "canceled_amount": canceled["canceled_amount"],
#             "stages": stages,
#         }

#     def get_funnel_overall(self):
#         return {
#             "ytd": self._get_funnel_for_period("YTD"),
#             "mtd": self._get_funnel_for_period("MTD"),
#         }

#     # НОВЫЙ МЕТОД: получение детальных заказов для конкретного менеджера
#     def get_manager_orders_detail(self, manager_name, status_filter=None):
#         """
#         Получить все заказы менеджера с детализацией по статусам
#         """
#         from orders.models import MV_Orders
        
#         qs = MV_Orders.objects.filter(manager=manager_name)
        
#         if status_filter == "active":
#             qs = qs.exclude(self._canceled_filter())
#         elif status_filter == "canceled":
#             qs = qs.filter(self._canceled_filter())
#         elif status_filter == "no_payment":
#             qs = qs.filter(cash_pmts=0).exclude(self._canceled_filter())
#         elif status_filter == "no_shipment":
#             qs = qs.filter(cash_pmts__gt=0, total_shiped_amount=0).exclude(self._canceled_filter())
#         elif status_filter == "partial_payment":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount__gt=0,
#                 amount_active__gt=0,
#                 cash_pmts__lt=F("amount_active")
#             ).exclude(self._canceled_filter())
#         elif status_filter == "not_closed":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount__gt=0,
#                 amount_active__gt=0,
#                 cash_pmts__gte=F("amount_active"),
#                 status__in=self.CLOSED_STATUSES
#             ).exclude(self._canceled_filter())
        
#         return qs.order_by('-date_from')

#     def get_funnel_by_manager(self, limit=15):
#         qs = self._base_qs_active("YTD").exclude(
#             manager__isnull=True
#         ).exclude(
#             manager=""
#         )

#         managers = qs.values("manager").annotate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),

#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                 ),
#                 distinct=True,
#             ),

#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#         ).filter(
#             total_amount__gt=0
#         ).order_by("-total_amount")[:limit]

#         result = []

#         for mgr in managers:
#             total = mgr["total_orders"] or 0
#             paid = mgr["paid_orders"] or 0
#             shipped = mgr["shipped_orders"] or 0
#             fully_paid = mgr["fully_paid_orders"] or 0
#             closed = mgr["closed_orders"] or 0

#             result.append({
#                 "manager": mgr["manager"],
#                 "ytd": {
#                     "total_orders": total,
#                     "total_amount": float(mgr["total_amount"] or 0),
#                     "paid_orders": paid,
#                     "shipped_orders": shipped,
#                     "fully_paid_orders": fully_paid,
#                     "closed_orders": closed,
#                     "stuck_without_payment": total - paid,
#                     "stuck_without_shipment": paid - shipped,
#                     "stuck_not_fully_paid": shipped - fully_paid,
#                     "stuck_not_closed": fully_paid - closed,
#                     "conv_paid": self._pct(paid, total),
#                     "conv_shipped": self._pct(shipped, paid),
#                     "conv_fully_paid": self._pct(fully_paid, shipped),
#                     "conv_closed": self._pct(closed, fully_paid),
#                 },
#             })

#         return result

#     def get_loss_analysis(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": self._analyze_bottlenecks(ytd),
#             "mtd": self._analyze_bottlenecks(mtd),
#         }

#     def _analyze_bottlenecks(self, funnel_data):
#         stages = funnel_data["stages"]
#         result = []

#         for i in range(1, len(stages)):
#             prev = stages[i - 1]
#             curr = stages[i]

#             lost_orders = prev["orders"] - curr["orders"]
#             lost_amount = prev["amount"] - curr["amount"]

#             result.append({
#                 "from_stage": prev["name"],
#                 "to_stage": curr["name"],
#                 "lost_orders": lost_orders,
#                 "loss_amount": lost_amount,
#                 "loss_percent": self._pct(lost_orders, prev["orders"]),
#                 "reason": self._get_loss_reason(prev["name"], curr["name"]),
#             })

#         return result

#     def get_canceled_summary(self):
#         return {
#             "ytd": self._get_canceled_summary("YTD"),
#             "mtd": self._get_canceled_summary("MTD"),
#         }

#     def get_comparison_summary(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": {
#                 "total_orders": ytd["total_orders"],
#                 "total_amount": ytd["total_amount"],
#                 "closed_orders": ytd["stages"][-1]["orders"],
#                 "closed_amount": ytd["stages"][-1]["amount"],
#                 "canceled_orders": ytd["canceled_orders"],
#                 "canceled_amount": ytd["canceled_amount"],
#                 "final_conversion": ytd["stages"][-1]["conversion_from_start"],
#             },
#             "mtd": {
#                 "total_orders": mtd["total_orders"],
#                 "total_amount": mtd["total_amount"],
#                 "closed_orders": mtd["stages"][-1]["orders"],
#                 "closed_amount": mtd["stages"][-1]["amount"],
#                 "canceled_orders": mtd["canceled_orders"],
#                 "canceled_amount": mtd["canceled_amount"],
#                 "final_conversion": mtd["stages"][-1]["conversion_from_start"],
#             },
#         }

#     def _get_loss_reason(self, from_stage, to_stage):
#         reasons = {
#             ("1. Создано заказов", "2. Есть оплата"): "Зависло без оплаты",
#             ("2. Есть оплата", "3. Есть отгрузка"): "Оплачено, но не отгружено",
#             ("3. Есть отгрузка", "4. Полностью оплачено"): "Есть отгрузка, но оплата частичная",
#             ("4. Полностью оплачено", "5. Закрыто в системе"): "Полностью оплачено, но не закрыто в системе",
#         }

#         return reasons.get((from_stage, to_stage), "Требуется анализ")




# # orders/reports/queries/funnel_analysis_query.py

# from datetime import date
# from django.db.models import Q, Count, Sum, F, Case, When, Value, DecimalField
# from django.db.models.functions import Coalesce
# from orders.models import MV_Orders


# class FunnelAnalysisQueries:
#     CANCEL_STATUSES = ["Отменен", "Отменён"]
#     CLOSED_STATUSES = ["Закрыт", "Закрыто"]

#     def _get_date_filters(self, period="YTD"):
#         today = date.today()

#         if period == "YTD":
#             return {"date_from__gte": date(today.year, 1, 1)}

#         if period == "MTD":
#             return {"date_from__gte": date(today.year, today.month, 1)}

#         return {}

#     def _has_field(self, field_name):
#         try:
#             MV_Orders._meta.get_field(field_name)
#             return True
#         except Exception:
#             return False

#     def _period_name(self, period):
#         today = date.today()

#         if period == "YTD":
#             return f"YTD с 01.01.{today.year}"

#         if period == "MTD":
#             return f"MTD с 01.{today.month:02d}.{today.year}"

#         return "За все время"

#     def _base_qs_all(self, period="YTD"):
#         qs = MV_Orders.objects.all()
#         date_filter = self._get_date_filters(period)

#         if date_filter:
#             qs = qs.filter(**date_filter)

#         return qs

#     def _canceled_filter(self):
#         q = Q(status__in=self.CANCEL_STATUSES)

#         if self._has_field("change_status"):
#             q |= Q(change_status__in=self.CANCEL_STATUSES)

#         return q

#     def _base_qs_active(self, period="YTD"):
#         return self._base_qs_all(period).exclude(self._canceled_filter())

#     def _pct(self, numerator, denominator):
#         return round(numerator / denominator * 100, 1) if denominator else 0

#     def _aggregate_funnel(self, qs):
#         return qs.aggregate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),
#             paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(cash_pmts__gt=0, then="cash_pmts"),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),
#             shipped_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             then="total_shiped_amount",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                 ),
#                 distinct=True,
#             ),
#             fully_paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             amount_active__gt=0,
#                             cash_pmts__gte=F("amount_active"),
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#             closed_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             amount_active__gt=0,
#                             cash_pmts__gte=F("amount_active"),
#                             status__in=self.CLOSED_STATUSES,
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),
#         )

#     def _get_canceled_summary(self, period="YTD"):
#         qs = self._base_qs_all(period).filter(self._canceled_filter())

#         agg = qs.aggregate(
#             canceled_orders=Count("order_id", distinct=True),
#             canceled_amount=Coalesce(
#                 Sum("amount_cancelled"),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),
#         )

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "canceled_orders": agg["canceled_orders"] or 0,
#             "canceled_amount": float(agg["canceled_amount"] or 0),
#         }

#     def _build_stages(self, agg):
#         total_orders = agg["total_orders"] or 0
#         paid_orders = agg["paid_orders"] or 0
#         shipped_orders = agg["shipped_orders"] or 0
#         fully_paid_orders = agg["fully_paid_orders"] or 0
#         closed_orders = agg["closed_orders"] or 0

#         return [
#             {
#                 "name": "1. Создано заказов",
#                 "orders": total_orders,
#                 "amount": float(agg["total_amount"] or 0),
#                 "conversion_from_prev": 100.0,
#                 "conversion_from_start": 100.0,
#             },
#             {
#                 "name": "2. Есть оплата",
#                 "orders": paid_orders,
#                 "amount": float(agg["paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(paid_orders, total_orders),
#                 "conversion_from_start": self._pct(paid_orders, total_orders),
#             },
#             {
#                 "name": "3. Есть отгрузка",
#                 "orders": shipped_orders,
#                 "amount": float(agg["shipped_amount"] or 0),
#                 "conversion_from_prev": self._pct(shipped_orders, paid_orders),
#                 "conversion_from_start": self._pct(shipped_orders, total_orders),
#             },
#             {
#                 "name": "4. Полностью оплачено",
#                 "orders": fully_paid_orders,
#                 "amount": float(agg["fully_paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(fully_paid_orders, shipped_orders),
#                 "conversion_from_start": self._pct(fully_paid_orders, total_orders),
#             },
#             {
#                 "name": "5. Закрыто в системе",
#                 "orders": closed_orders,
#                 "amount": float(agg["closed_amount"] or 0),
#                 "conversion_from_prev": self._pct(closed_orders, fully_paid_orders),
#                 "conversion_from_start": self._pct(closed_orders, total_orders),
#             },
#         ]

#     def _get_funnel_for_period(self, period="YTD"):
#         qs = self._base_qs_active(period)
#         agg = self._aggregate_funnel(qs)
#         stages = self._build_stages(agg)
#         canceled = self._get_canceled_summary(period)

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "total_orders": agg["total_orders"] or 0,
#             "total_amount": float(agg["total_amount"] or 0),
#             "canceled_orders": canceled["canceled_orders"],
#             "canceled_amount": canceled["canceled_amount"],
#             "stages": stages,
#         }

#     def get_funnel_overall(self):
#         return {
#             "ytd": self._get_funnel_for_period("YTD"),
#             "mtd": self._get_funnel_for_period("MTD"),
#         }

#     def get_manager_orders_detail(self, manager_name, status_filter=None):
#         qs = MV_Orders.objects.filter(manager=manager_name)

#         if status_filter == "active":
#             qs = qs.exclude(self._canceled_filter())

#         elif status_filter == "canceled":
#             qs = qs.filter(self._canceled_filter())

#         elif status_filter == "no_payment":
#             qs = qs.filter(
#                 cash_pmts=0,
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "no_shipment":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount=0,
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "partial_payment":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount__gt=0,
#                 amount_active__gt=0,
#                 cash_pmts__lt=F("amount_active"),
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "not_closed":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount__gt=0,
#                 amount_active__gt=0,
#                 cash_pmts__gte=F("amount_active"),
#             ).exclude(
#                 status__in=self.CLOSED_STATUSES
#             ).exclude(
#                 self._canceled_filter()
#             )

#         return qs.order_by("-date_from")

#     def get_funnel_by_manager(self, limit=15):
#         qs = self._base_qs_active("YTD").exclude(
#             manager__isnull=True
#         ).exclude(
#             manager=""
#         )

#         managers = qs.values("manager").annotate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),

#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                 ),
#                 distinct=True,
#             ),

#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#         ).filter(
#             total_amount__gt=0
#         ).order_by("-total_amount")[:limit]

#         result = []

#         for mgr in managers:
#             total = mgr["total_orders"] or 0
#             paid = mgr["paid_orders"] or 0
#             shipped = mgr["shipped_orders"] or 0
#             fully_paid = mgr["fully_paid_orders"] or 0
#             closed = mgr["closed_orders"] or 0

#             result.append({
#                 "manager": mgr["manager"],
#                 "ytd": {
#                     "total_orders": total,
#                     "total_amount": float(mgr["total_amount"] or 0),
#                     "paid_orders": paid,
#                     "shipped_orders": shipped,
#                     "fully_paid_orders": fully_paid,
#                     "closed_orders": closed,
#                     "stuck_without_payment": total - paid,
#                     "stuck_without_shipment": paid - shipped,
#                     "stuck_not_fully_paid": shipped - fully_paid,
#                     "stuck_not_closed": fully_paid - closed,
#                     "conv_paid": self._pct(paid, total),
#                     "conv_shipped": self._pct(shipped, paid),
#                     "conv_fully_paid": self._pct(fully_paid, shipped),
#                     "conv_closed": self._pct(closed, fully_paid),
#                 },
#             })

#         return result

#     def _get_order_problem_status(self, obj):
#         is_canceled = (
#             obj.status in self.CANCEL_STATUSES
#             or getattr(obj, "change_status", None) in self.CANCEL_STATUSES
#         )

#         if is_canceled:
#             return "Отменен", "Исключен из основной воронки"

#         cash_pmts = obj.cash_pmts or 0
#         total_shiped_amount = obj.total_shiped_amount or 0
#         amount_active = obj.amount_active or 0

#         if cash_pmts <= 0:
#             return "Нет оплаты", "Заказ создан, но нет оплаты"

#         if total_shiped_amount <= 0:
#             return "Нет отгрузки", "Оплата есть, но нет отгрузки"

#         if amount_active > 0 and cash_pmts < amount_active:
#             return "Частичная оплата", "Есть отгрузка, но заказ оплачен не полностью"

#         if obj.status not in self.CLOSED_STATUSES:
#             return "Не закрыт в системе", "Полностью оплачен и отгружен, но статус не закрыт"

#         return "ОК", "Закрыт"

#     def get_orders_detail_table(self, period="YTD"):
#         qs = self._base_qs_all(period).order_by("-date_from", "manager", "number")

#         rows = []

#         for obj in qs:
#             problem_status, problem_comment = self._get_order_problem_status(obj)

#             rows.append({
#                 "period": period,
#                 "order_name": obj.order_name,
#                 "number": obj.number,
#                 "date_from": obj.date_from.date() if obj.date_from else None,
#                 "update_at": obj.update_at.date() if obj.update_at else None,
#                 "status": obj.status,
#                 "client": obj.client,
#                 "manager": obj.manager,
#                 "store": obj.store,
#                 "change_status": obj.change_status,
#                 "qty_ordered": obj.qty_ordered or 0,
#                 "qty_cancelled": obj.qty_cancelled or 0,
#                 "order_qty": obj.order_qty or 0,
#                 "order_amount": float(obj.order_amount or 0),
#                 "amount_delivery": float(obj.amount_delivery or 0),
#                 "amount_cancelled": float(obj.amount_cancelled or 0),
#                 "amount_active": float(obj.amount_active or 0),
#                 "cash_recieved": float(obj.cash_recieved or 0),
#                 "cash_returned": float(obj.cash_returned or 0),
#                 "cash_pmts": float(obj.cash_pmts or 0),
#                 "shiped": obj.shiped or 0,
#                 "returned": obj.returned or 0,
#                 "shiped_qty": obj.shiped_qty or 0,
#                 "shiped_amount": float(obj.shiped_amount or 0),
#                 "returned_amount": float(obj.returned_amount or 0),
#                 "total_shiped_amount": float(obj.total_shiped_amount or 0),
#                 "shiped_delivery_amount": float(obj.shiped_delivery_amount or 0),
#                 "payment_dates": obj.payment_dates,
#                 "problem_status": problem_status,
#                 "problem_comment": problem_comment,
#             })

#         return rows

#     def get_loss_analysis(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": self._analyze_bottlenecks(ytd),
#             "mtd": self._analyze_bottlenecks(mtd),
#         }

#     def _analyze_bottlenecks(self, funnel_data):
#         stages = funnel_data["stages"]
#         result = []

#         for i in range(1, len(stages)):
#             prev = stages[i - 1]
#             curr = stages[i]

#             lost_orders = prev["orders"] - curr["orders"]
#             lost_amount = prev["amount"] - curr["amount"]

#             result.append({
#                 "from_stage": prev["name"],
#                 "to_stage": curr["name"],
#                 "lost_orders": lost_orders,
#                 "loss_amount": lost_amount,
#                 "loss_percent": self._pct(lost_orders, prev["orders"]),
#                 "reason": self._get_loss_reason(prev["name"], curr["name"]),
#             })

#         return result

#     def get_canceled_summary(self):
#         return {
#             "ytd": self._get_canceled_summary("YTD"),
#             "mtd": self._get_canceled_summary("MTD"),
#         }

#     def get_comparison_summary(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": {
#                 "total_orders": ytd["total_orders"],
#                 "total_amount": ytd["total_amount"],
#                 "closed_orders": ytd["stages"][-1]["orders"],
#                 "closed_amount": ytd["stages"][-1]["amount"],
#                 "canceled_orders": ytd["canceled_orders"],
#                 "canceled_amount": ytd["canceled_amount"],
#                 "final_conversion": ytd["stages"][-1]["conversion_from_start"],
#             },
#             "mtd": {
#                 "total_orders": mtd["total_orders"],
#                 "total_amount": mtd["total_amount"],
#                 "closed_orders": mtd["stages"][-1]["orders"],
#                 "closed_amount": mtd["stages"][-1]["amount"],
#                 "canceled_orders": mtd["canceled_orders"],
#                 "canceled_amount": mtd["canceled_amount"],
#                 "final_conversion": mtd["stages"][-1]["conversion_from_start"],
#             },
#         }

#     def _get_loss_reason(self, from_stage, to_stage):
#         reasons = {
#             ("1. Создано заказов", "2. Есть оплата"): "Зависло без оплаты",
#             ("2. Есть оплата", "3. Есть отгрузка"): "Оплачено, но не отгружено",
#             ("3. Есть отгрузка", "4. Полностью оплачено"): "Есть отгрузка, но оплата частичная",
#             ("4. Полностью оплачено", "5. Закрыто в системе"): "Полностью оплачено, но не закрыто в системе",
#         }

#         return reasons.get((from_stage, to_stage), "Требуется анализ")




# # orders/reports/queries/funnel_analysis_query.py

# from datetime import date
# from django.db.models import Q, Count, Sum, F, Case, When, Value, DecimalField
# from django.db.models.functions import Coalesce
# from orders.models import MV_Orders


# class FunnelAnalysisQueries:
#     CANCEL_STATUSES = ["Отменен", "Отменён"]
#     CLOSED_STATUSES = ["Закрыт", "Закрыто"]

#     def _get_date_filters(self, period="YTD"):
#         today = date.today()

#         if period == "YTD":
#             return {"date_from__gte": date(today.year, 1, 1)}

#         if period == "MTD":
#             return {"date_from__gte": date(today.year, today.month, 1)}

#         return {}

#     def _has_field(self, field_name):
#         try:
#             MV_Orders._meta.get_field(field_name)
#             return True
#         except Exception:
#             return False

#     def _period_name(self, period):
#         today = date.today()

#         if period == "YTD":
#             return f"YTD с 01.01.{today.year}"

#         if period == "MTD":
#             return f"MTD с 01.{today.month:02d}.{today.year}"

#         return "За все время"

#     def _base_qs_all(self, period="YTD"):
#         qs = MV_Orders.objects.all()
#         date_filter = self._get_date_filters(period)

#         if date_filter:
#             qs = qs.filter(**date_filter)

#         return qs

#     def _canceled_filter(self):
#         q = Q(status__in=self.CANCEL_STATUSES)

#         if self._has_field("change_status"):
#             q |= Q(change_status__in=self.CANCEL_STATUSES)

#         return q

#     def _base_qs_active(self, period="YTD"):
#         return self._base_qs_all(period).exclude(self._canceled_filter())

#     def _pct(self, numerator, denominator):
#         return round(numerator / denominator * 100, 1) if denominator else 0

#     def _aggregate_funnel(self, qs):
#         return qs.aggregate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),
#             paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(cash_pmts__gt=0, then="cash_pmts"),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),
#             shipped_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             then="total_shiped_amount",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                 ),
#                 distinct=True,
#             ),
#             fully_paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             amount_active__gt=0,
#                             cash_pmts__gte=F("amount_active"),
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#             closed_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             amount_active__gt=0,
#                             cash_pmts__gte=F("amount_active"),
#                             status__in=self.CLOSED_STATUSES,
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),
#         )

#     def _get_canceled_summary(self, period="YTD"):
#         qs = self._base_qs_all(period).filter(self._canceled_filter())

#         agg = qs.aggregate(
#             canceled_orders=Count("order_id", distinct=True),
#             canceled_amount=Coalesce(
#                 Sum("amount_cancelled"),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),
#         )

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "canceled_orders": agg["canceled_orders"] or 0,
#             "canceled_amount": float(agg["canceled_amount"] or 0),
#         }

#     def _build_stages(self, agg):
#         total_orders = agg["total_orders"] or 0
#         paid_orders = agg["paid_orders"] or 0
#         shipped_orders = agg["shipped_orders"] or 0
#         fully_paid_orders = agg["fully_paid_orders"] or 0
#         closed_orders = agg["closed_orders"] or 0

#         return [
#             {
#                 "name": "1. Создано заказов",
#                 "orders": total_orders,
#                 "amount": float(agg["total_amount"] or 0),
#                 "conversion_from_prev": 100.0,
#                 "conversion_from_start": 100.0,
#             },
#             {
#                 "name": "2. Есть оплата",
#                 "orders": paid_orders,
#                 "amount": float(agg["paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(paid_orders, total_orders),
#                 "conversion_from_start": self._pct(paid_orders, total_orders),
#             },
#             {
#                 "name": "3. Есть отгрузка",
#                 "orders": shipped_orders,
#                 "amount": float(agg["shipped_amount"] or 0),
#                 "conversion_from_prev": self._pct(shipped_orders, paid_orders),
#                 "conversion_from_start": self._pct(shipped_orders, total_orders),
#             },
#             {
#                 "name": "4. Полностью оплачено",
#                 "orders": fully_paid_orders,
#                 "amount": float(agg["fully_paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(fully_paid_orders, shipped_orders),
#                 "conversion_from_start": self._pct(fully_paid_orders, total_orders),
#             },
#             {
#                 "name": "5. Закрыто в системе",
#                 "orders": closed_orders,
#                 "amount": float(agg["closed_amount"] or 0),
#                 "conversion_from_prev": self._pct(closed_orders, fully_paid_orders),
#                 "conversion_from_start": self._pct(closed_orders, total_orders),
#             },
#         ]

#     def _get_funnel_for_period(self, period="YTD"):
#         qs = self._base_qs_active(period)
#         agg = self._aggregate_funnel(qs)
#         stages = self._build_stages(agg)
#         canceled = self._get_canceled_summary(period)

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "total_orders": agg["total_orders"] or 0,
#             "total_amount": float(agg["total_amount"] or 0),
#             "canceled_orders": canceled["canceled_orders"],
#             "canceled_amount": canceled["canceled_amount"],
#             "stages": stages,
#         }

#     def get_funnel_overall(self):
#         return {
#             "ytd": self._get_funnel_for_period("YTD"),
#             "mtd": self._get_funnel_for_period("MTD"),
#         }

#     def get_manager_orders_detail(self, manager_name, status_filter=None):
#         qs = MV_Orders.objects.filter(manager=manager_name)

#         if status_filter == "active":
#             qs = qs.exclude(self._canceled_filter())

#         elif status_filter == "canceled":
#             qs = qs.filter(self._canceled_filter())

#         elif status_filter == "no_payment":
#             qs = qs.filter(
#                 cash_pmts=0,
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "no_shipment":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount=0,
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "partial_payment":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount__gt=0,
#                 amount_active__gt=0,
#                 cash_pmts__lt=F("amount_active"),
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "not_closed":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount__gt=0,
#                 amount_active__gt=0,
#                 cash_pmts__gte=F("amount_active"),
#             ).exclude(
#                 status__in=self.CLOSED_STATUSES
#             ).exclude(
#                 self._canceled_filter()
#             )

#         return qs.order_by("-date_from")

#     def get_funnel_by_manager(self, limit=15):
#         qs = self._base_qs_active("YTD").exclude(
#             manager__isnull=True
#         ).exclude(
#             manager=""
#         )

#         managers = qs.values("manager").annotate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),

#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                 ),
#                 distinct=True,
#             ),

#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#         ).filter(
#             total_amount__gt=0
#         ).order_by("-total_amount")[:limit]

#         result = []

#         for mgr in managers:
#             total = mgr["total_orders"] or 0
#             paid = mgr["paid_orders"] or 0
#             shipped = mgr["shipped_orders"] or 0
#             fully_paid = mgr["fully_paid_orders"] or 0
#             closed = mgr["closed_orders"] or 0

#             result.append({
#                 "manager": mgr["manager"],
#                 "ytd": {
#                     "total_orders": total,
#                     "total_amount": float(mgr["total_amount"] or 0),
#                     "paid_orders": paid,
#                     "shipped_orders": shipped,
#                     "fully_paid_orders": fully_paid,
#                     "closed_orders": closed,

#                     "stuck_without_payment": total - paid,
#                     "stuck_without_shipment": paid - shipped,
#                     "stuck_not_fully_paid": shipped - fully_paid,
#                     "stuck_not_closed": fully_paid - closed,

#                     "conv_paid": self._pct(paid, total),
#                     "conv_shipped": self._pct(shipped, paid),
#                     "conv_fully_paid": self._pct(fully_paid, shipped),
#                     "conv_closed": self._pct(closed, fully_paid),
#                 },
#             })

#         return result

#     def _get_order_problem_status(self, obj):
#         status = obj.status or ""
#         change_status = getattr(obj, "change_status", None) or ""

#         is_canceled = (
#             status in self.CANCEL_STATUSES
#             or change_status in self.CANCEL_STATUSES
#         )

#         if is_canceled:
#             return "Отменен", "Исключен из основной воронки"

#         cash_pmts = obj.cash_pmts or 0
#         total_shiped_amount = obj.total_shiped_amount or 0
#         amount_active = obj.amount_active or 0

#         if cash_pmts <= 0:
#             return "Нет оплаты", "Заказ создан, но нет оплаты"

#         if total_shiped_amount <= 0:
#             return "Нет отгрузки", "Оплата есть, но нет отгрузки"

#         if amount_active > 0 and cash_pmts < amount_active:
#             return "Частичная оплата", "Есть отгрузка, но заказ оплачен не полностью"

#         if status not in self.CLOSED_STATUSES:
#             return "Не закрыт в системе", "Полностью оплачен и отгружен, но статус не закрыт"

#         return "ОК", "Закрыт"

#     def _safe_date(self, value):
#         if not value:
#             return None
#         if hasattr(value, "date"):
#             return value.date()
#         return value

#     def _safe_float(self, value):
#         return float(value or 0)

#     def _safe_int(self, value):
#         return int(value or 0)

#     def get_orders_detail_table(self, period="YTD"):
#         qs = self._base_qs_all(period).order_by("-date_from", "manager", "number")

#         rows = []

#         for obj in qs:
#             problem_status, problem_comment = self._get_order_problem_status(obj)

#             rows.append({
#                 "period": period,

#                 "order_name": obj.order_name or "",
#                 "number": obj.number or "",
#                 "date_from": self._safe_date(obj.date_from),
#                 "update_at": self._safe_date(obj.update_at),

#                 "status": obj.status or "",
#                 "client": obj.client or "",
#                 "manager": obj.manager or "",
#                 "store": obj.store or "",
#                 "change_status": obj.change_status or "",

#                 "qty_ordered": self._safe_int(obj.qty_ordered),
#                 "qty_cancelled": self._safe_int(obj.qty_cancelled),
#                 "order_qty": self._safe_int(obj.order_qty),

#                 "order_amount": self._safe_float(obj.order_amount),
#                 "amount_delivery": self._safe_float(obj.amount_delivery),
#                 "amount_cancelled": self._safe_float(obj.amount_cancelled),
#                 "amount_active": self._safe_float(obj.amount_active),

#                 "cash_recieved": self._safe_float(obj.cash_recieved),
#                 "cash_returned": self._safe_float(obj.cash_returned),
#                 "cash_pmts": self._safe_float(obj.cash_pmts),

#                 "shiped": self._safe_int(obj.shiped),
#                 "returned": self._safe_int(obj.returned),
#                 "shiped_qty": self._safe_int(obj.shiped_qty),

#                 "shiped_amount": self._safe_float(obj.shiped_amount),
#                 "returned_amount": self._safe_float(obj.returned_amount),
#                 "total_shiped_amount": self._safe_float(obj.total_shiped_amount),
#                 "shiped_delivery_amount": self._safe_float(obj.shiped_delivery_amount),

#                 "payment_dates": obj.payment_dates or "",

#                 "problem_status": problem_status,
#                 "problem_comment": problem_comment,
#             })

#         return rows

#     def get_loss_analysis(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": self._analyze_bottlenecks(ytd),
#             "mtd": self._analyze_bottlenecks(mtd),
#         }

#     def _analyze_bottlenecks(self, funnel_data):
#         stages = funnel_data["stages"]
#         result = []

#         for i in range(1, len(stages)):
#             prev = stages[i - 1]
#             curr = stages[i]

#             lost_orders = prev["orders"] - curr["orders"]
#             lost_amount = prev["amount"] - curr["amount"]

#             result.append({
#                 "from_stage": prev["name"],
#                 "to_stage": curr["name"],
#                 "lost_orders": lost_orders,
#                 "loss_amount": lost_amount,
#                 "loss_percent": self._pct(lost_orders, prev["orders"]),
#                 "reason": self._get_loss_reason(prev["name"], curr["name"]),
#             })

#         return result

#     def get_canceled_summary(self):
#         return {
#             "ytd": self._get_canceled_summary("YTD"),
#             "mtd": self._get_canceled_summary("MTD"),
#         }

#     def get_comparison_summary(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": {
#                 "total_orders": ytd["total_orders"],
#                 "total_amount": ytd["total_amount"],
#                 "closed_orders": ytd["stages"][-1]["orders"],
#                 "closed_amount": ytd["stages"][-1]["amount"],
#                 "canceled_orders": ytd["canceled_orders"],
#                 "canceled_amount": ytd["canceled_amount"],
#                 "final_conversion": ytd["stages"][-1]["conversion_from_start"],
#             },
#             "mtd": {
#                 "total_orders": mtd["total_orders"],
#                 "total_amount": mtd["total_amount"],
#                 "closed_orders": mtd["stages"][-1]["orders"],
#                 "closed_amount": mtd["stages"][-1]["amount"],
#                 "canceled_orders": mtd["canceled_orders"],
#                 "canceled_amount": mtd["canceled_amount"],
#                 "final_conversion": mtd["stages"][-1]["conversion_from_start"],
#             },
#         }

#     def _get_loss_reason(self, from_stage, to_stage):
#         reasons = {
#             ("1. Создано заказов", "2. Есть оплата"): "Зависло без оплаты",
#             ("2. Есть оплата", "3. Есть отгрузка"): "Оплачено, но не отгружено",
#             ("3. Есть отгрузка", "4. Полностью оплачено"): "Есть отгрузка, но оплата частичная",
#             ("4. Полностью оплачено", "5. Закрыто в системе"): "Полностью оплачено, но не закрыто в системе",
#         }

#         return reasons.get((from_stage, to_stage), "Требуется анализ")





# # orders/reports/queries/funnel_analysis_query.py

# from datetime import date
# from django.db.models import Q, Count, Sum, F, Case, When, Value, DecimalField
# from django.db.models.functions import Coalesce
# from orders.models import MV_Orders


# class FunnelAnalysisQueries:
#     CANCEL_STATUSES = ["Отменен", "Отменён"]
#     CLOSED_STATUSES = ["Закрыт", "Закрыто"]

#     def _get_date_filters(self, period="YTD"):
#         today = date.today()

#         if period == "YTD":
#             return {"date_from__gte": date(today.year, 1, 1)}

#         if period == "MTD":
#             return {"date_from__gte": date(today.year, today.month, 1)}

#         return {}

#     def _has_field(self, field_name):
#         try:
#             MV_Orders._meta.get_field(field_name)
#             return True
#         except Exception:
#             return False

#     def _period_name(self, period):
#         today = date.today()

#         if period == "YTD":
#             return f"YTD с 01.01.{today.year}"

#         if period == "MTD":
#             return f"MTD с 01.{today.month:02d}.{today.year}"

#         return "За все время"

#     def _base_qs_all(self, period="YTD"):
#         qs = MV_Orders.objects.all()
#         date_filter = self._get_date_filters(period)

#         if date_filter:
#             qs = qs.filter(**date_filter)

#         return qs

#     def _canceled_filter(self):
#         q = Q(status__in=self.CANCEL_STATUSES)

#         if self._has_field("change_status"):
#             q |= Q(change_status__in=self.CANCEL_STATUSES)

#         return q

#     def _base_qs_active(self, period="YTD"):
#         return self._base_qs_all(period).exclude(self._canceled_filter())

#     def _pct(self, numerator, denominator):
#         return round(numerator / denominator * 100, 1) if denominator else 0

#     def _aggregate_funnel(self, qs):
#         return qs.aggregate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),
#             paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(cash_pmts__gt=0, then="cash_pmts"),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),
#             shipped_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             then="total_shiped_amount",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                 ),
#                 distinct=True,
#             ),
#             fully_paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             amount_active__gt=0,
#                             cash_pmts__gte=F("amount_active"),
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#             closed_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             amount_active__gt=0,
#                             cash_pmts__gte=F("amount_active"),
#                             status__in=self.CLOSED_STATUSES,
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),
#         )

#     def _get_canceled_summary(self, period="YTD"):
#         qs = self._base_qs_all(period).filter(self._canceled_filter())

#         agg = qs.aggregate(
#             canceled_orders=Count("order_id", distinct=True),
#             canceled_amount=Coalesce(
#                 Sum("amount_cancelled"),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),
#         )

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "canceled_orders": agg["canceled_orders"] or 0,
#             "canceled_amount": float(agg["canceled_amount"] or 0),
#         }

#     def _build_stages(self, agg):
#         total_orders = agg["total_orders"] or 0
#         paid_orders = agg["paid_orders"] or 0
#         shipped_orders = agg["shipped_orders"] or 0
#         fully_paid_orders = agg["fully_paid_orders"] or 0
#         closed_orders = agg["closed_orders"] or 0

#         return [
#             {
#                 "name": "1. Создано заказов",
#                 "orders": total_orders,
#                 "amount": float(agg["total_amount"] or 0),
#                 "conversion_from_prev": 100.0,
#                 "conversion_from_start": 100.0,
#             },
#             {
#                 "name": "2. Есть оплата",
#                 "orders": paid_orders,
#                 "amount": float(agg["paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(paid_orders, total_orders),
#                 "conversion_from_start": self._pct(paid_orders, total_orders),
#             },
#             {
#                 "name": "3. Есть отгрузка",
#                 "orders": shipped_orders,
#                 "amount": float(agg["shipped_amount"] or 0),
#                 "conversion_from_prev": self._pct(shipped_orders, paid_orders),
#                 "conversion_from_start": self._pct(shipped_orders, total_orders),
#             },
#             {
#                 "name": "4. Полностью оплачено",
#                 "orders": fully_paid_orders,
#                 "amount": float(agg["fully_paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(fully_paid_orders, shipped_orders),
#                 "conversion_from_start": self._pct(fully_paid_orders, total_orders),
#             },
#             {
#                 "name": "5. Закрыто в системе",
#                 "orders": closed_orders,
#                 "amount": float(agg["closed_amount"] or 0),
#                 "conversion_from_prev": self._pct(closed_orders, fully_paid_orders),
#                 "conversion_from_start": self._pct(closed_orders, total_orders),
#             },
#         ]

#     def _get_funnel_for_period(self, period="YTD"):
#         qs = self._base_qs_active(period)
#         agg = self._aggregate_funnel(qs)
#         stages = self._build_stages(agg)
#         canceled = self._get_canceled_summary(period)

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "total_orders": agg["total_orders"] or 0,
#             "total_amount": float(agg["total_amount"] or 0),
#             "canceled_orders": canceled["canceled_orders"],
#             "canceled_amount": canceled["canceled_amount"],
#             "stages": stages,
#         }

#     def get_funnel_overall(self):
#         return {
#             "ytd": self._get_funnel_for_period("YTD"),
#             "mtd": self._get_funnel_for_period("MTD"),
#         }

#     def get_manager_orders_detail(self, manager_name, status_filter=None):
#         qs = MV_Orders.objects.filter(manager=manager_name)

#         if status_filter == "active":
#             qs = qs.exclude(self._canceled_filter())

#         elif status_filter == "canceled":
#             qs = qs.filter(self._canceled_filter())

#         elif status_filter == "no_payment":
#             qs = qs.filter(
#                 cash_pmts=0,
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "no_shipment":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount=0,
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "partial_payment":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount__gt=0,
#                 amount_active__gt=0,
#                 cash_pmts__lt=F("amount_active"),
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "not_closed":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount__gt=0,
#                 amount_active__gt=0,
#                 cash_pmts__gte=F("amount_active"),
#             ).exclude(
#                 status__in=self.CLOSED_STATUSES
#             ).exclude(
#                 self._canceled_filter()
#             )

#         return qs.order_by("-date_from")

#     def get_funnel_by_manager(self, limit=15):
#         qs = self._base_qs_active("YTD").exclude(
#             manager__isnull=True
#         ).exclude(
#             manager=""
#         )

#         managers = qs.values("manager").annotate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),

#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                 ),
#                 distinct=True,
#             ),

#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     cash_pmts__gt=0,
#                     total_shiped_amount__gt=0,
#                     amount_active__gt=0,
#                     cash_pmts__gte=F("amount_active"),
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#         ).filter(
#             total_amount__gt=0
#         ).order_by("-total_amount")[:limit]

#         result = []

#         for mgr in managers:
#             total = mgr["total_orders"] or 0
#             paid = mgr["paid_orders"] or 0
#             shipped = mgr["shipped_orders"] or 0
#             fully_paid = mgr["fully_paid_orders"] or 0
#             closed = mgr["closed_orders"] or 0

#             result.append({
#                 "manager": mgr["manager"],
#                 "ytd": {
#                     "total_orders": total,
#                     "total_amount": float(mgr["total_amount"] or 0),
#                     "paid_orders": paid,
#                     "shipped_orders": shipped,
#                     "fully_paid_orders": fully_paid,
#                     "closed_orders": closed,

#                     "stuck_without_payment": total - paid,
#                     "stuck_without_shipment": paid - shipped,
#                     "stuck_not_fully_paid": shipped - fully_paid,
#                     "stuck_not_closed": fully_paid - closed,

#                     "conv_paid": self._pct(paid, total),
#                     "conv_shipped": self._pct(shipped, paid),
#                     "conv_fully_paid": self._pct(fully_paid, shipped),
#                     "conv_closed": self._pct(closed, fully_paid),
#                 },
#             })

#         return result

#     def _get_order_problem_status(self, obj):
#         status = obj.status or ""
#         change_status = getattr(obj, "change_status", None) or ""

#         is_canceled = (
#             status in self.CANCEL_STATUSES
#             or change_status in self.CANCEL_STATUSES
#         )

#         if is_canceled:
#             return "Отменен", "Исключен из основной воронки"

#         cash_pmts = obj.cash_pmts or 0
#         total_shiped_amount = obj.total_shiped_amount or 0
#         amount_active = obj.amount_active or 0

#         if cash_pmts <= 0:
#             return "Нет оплаты", "Заказ создан, но нет оплаты"

#         if total_shiped_amount <= 0:
#             return "Нет отгрузки", "Оплата есть, но нет отгрузки"

#         if amount_active > 0 and cash_pmts < amount_active:
#             return "Частичная оплата", "Есть отгрузка, но заказ оплачен не полностью"

#         if status not in self.CLOSED_STATUSES:
#             return "Не закрыт в системе", "Полностью оплачен и отгружен, но статус не закрыт"

#         return "ОК", "Закрыт"

#     def _safe_date(self, value):
#         if not value:
#             return None
#         if hasattr(value, "date"):
#             return value.date()
#         return value

#     def _safe_float(self, value):
#         return float(value or 0)

#     def _safe_int(self, value):
#         return int(value or 0)

#     def get_orders_detail_table(self, period="YTD"):
#         qs = self._base_qs_all(period).order_by("-date_from", "manager", "number")

#         rows = []

#         for obj in qs:
#             problem_status, problem_comment = self._get_order_problem_status(obj)
            
#             # Пропускаем заказы со статусом OK и Отменен
#             if problem_status in ["ОК", "Отменен"]:
#                 continue

#             # Преобразуем клиента в ЗАГЛАВНЫЕ БУКВЫ
#             client_upper = (obj.client or "").upper()
            
#             # Преобразуем менеджера: первая фамилия + первая буква имени
#             manager_formatted = self._format_manager_name(obj.manager or "")
            
#             # Преобразуем магазин в ЗАГЛАВНЫЕ БУКВЫ
#             store_upper = (obj.store or "").upper()

#             rows.append({
#                 "period": period,
#                 "problem_status": problem_status,
#                 "problem_comment": problem_comment,
#                 "number": obj.number or "",
#                 "date_from": self._safe_date(obj.date_from),
#                 "status": obj.status or "",
#                 "client": client_upper,
#                 "manager": manager_formatted,
#                 "store": store_upper,
#                 "amount_active": self._safe_float(obj.amount_active),
#                 "cash_pmts": self._safe_float(obj.cash_pmts),
#                 "total_shiped_amount": self._safe_float(obj.total_shiped_amount),
#             })

#         return rows
    
#     def _format_manager_name(self, manager_name):
#         """
#         Иванов Иван Иванович -> ИВАНОВ И.
#         Иванов Иван -> ИВАНОВ И.
#         Иванов -> ИВАНОВ
#         """
#         if not manager_name:
#             return ""

#         words = str(manager_name).strip().split()
#         if not words:
#             return ""

#         first = words[0].upper()

#         if len(words) >= 2 and words[1]:
#             return f"{first} {words[1][0].upper()}."

#         return first

#     def get_loss_analysis(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": self._analyze_bottlenecks(ytd),
#             "mtd": self._analyze_bottlenecks(mtd),
#         }

#     def _analyze_bottlenecks(self, funnel_data):
#         stages = funnel_data["stages"]
#         result = []

#         for i in range(1, len(stages)):
#             prev = stages[i - 1]
#             curr = stages[i]

#             lost_orders = prev["orders"] - curr["orders"]
#             lost_amount = prev["amount"] - curr["amount"]

#             result.append({
#                 "from_stage": prev["name"],
#                 "to_stage": curr["name"],
#                 "lost_orders": lost_orders,
#                 "loss_amount": lost_amount,
#                 "loss_percent": self._pct(lost_orders, prev["orders"]),
#                 "reason": self._get_loss_reason(prev["name"], curr["name"]),
#             })

#         return result

#     def get_canceled_summary(self):
#         return {
#             "ytd": self._get_canceled_summary("YTD"),
#             "mtd": self._get_canceled_summary("MTD"),
#         }

#     def get_comparison_summary(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": {
#                 "total_orders": ytd["total_orders"],
#                 "total_amount": ytd["total_amount"],
#                 "closed_orders": ytd["stages"][-1]["orders"],
#                 "closed_amount": ytd["stages"][-1]["amount"],
#                 "canceled_orders": ytd["canceled_orders"],
#                 "canceled_amount": ytd["canceled_amount"],
#                 "final_conversion": ytd["stages"][-1]["conversion_from_start"],
#             },
#             "mtd": {
#                 "total_orders": mtd["total_orders"],
#                 "total_amount": mtd["total_amount"],
#                 "closed_orders": mtd["stages"][-1]["orders"],
#                 "closed_amount": mtd["stages"][-1]["amount"],
#                 "canceled_orders": mtd["canceled_orders"],
#                 "canceled_amount": mtd["canceled_amount"],
#                 "final_conversion": mtd["stages"][-1]["conversion_from_start"],
#             },
#         }

#     def _get_loss_reason(self, from_stage, to_stage):
#         reasons = {
#             ("1. Создано заказов", "2. Есть оплата"): "Зависло без оплаты",
#             ("2. Есть оплата", "3. Есть отгрузка"): "Оплачено, но не отгружено",
#             ("3. Есть отгрузка", "4. Полностью оплачено"): "Есть отгрузка, но оплата частичная",
#             ("4. Полностью оплачено", "5. Закрыто в системе"): "Полностью оплачено, но не закрыто в системе",
#         }

#         return reasons.get((from_stage, to_stage), "Требуется анализ")



# # orders/reports/queries/funnel_analysis_query.py

# from datetime import date
# from django.db.models import Q, Count, Sum, F, Case, When, Value, DecimalField
# from django.db.models.functions import Coalesce
# from orders.models import MV_Orders


# class FunnelAnalysisQueries:
#     CANCEL_STATUSES = ["Отменен", "Отменён"]
#     CLOSED_STATUSES = ["Закрыт", "Закрыто"]

#     def _get_date_filters(self, period="YTD"):
#         today = date.today()

#         if period == "YTD":
#             return {"date_from__gte": date(today.year, 1, 1)}

#         if period == "MTD":
#             return {"date_from__gte": date(today.year, today.month, 1)}

#         return {}

#     def _has_field(self, field_name):
#         try:
#             MV_Orders._meta.get_field(field_name)
#             return True
#         except Exception:
#             return False

#     def _period_name(self, period):
#         today = date.today()

#         if period == "YTD":
#             return f"YTD с 01.01.{today.year}"

#         if period == "MTD":
#             return f"MTD с 01.{today.month:02d}.{today.year}"

#         return "За все время"

#     def _base_qs_all(self, period="YTD"):
#         qs = MV_Orders.objects.all()
#         date_filter = self._get_date_filters(period)

#         if date_filter:
#             qs = qs.filter(**date_filter)

#         return qs

#     def _canceled_filter(self):
#         q = Q(status__in=self.CANCEL_STATUSES)

#         if self._has_field("change_status"):
#             q |= Q(change_status__in=self.CANCEL_STATUSES)

#         return q

#     def _base_qs_active(self, period="YTD"):
#         return self._base_qs_all(period).exclude(self._canceled_filter())

#     def _pct(self, numerator, denominator):
#         return round(numerator / denominator * 100, 1) if denominator else 0

#     def _aggregate_funnel(self, qs):
#         return qs.aggregate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),
#             paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(cash_pmts__gt=0, then="cash_pmts"),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),
#             shipped_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             then="total_shiped_amount",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             # Полностью оплачено И полностью отгружено
#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     amount_active__gt=0,
#                     total_shiped_amount=F("amount_active"),
#                     cash_pmts=F("total_shiped_amount"),
#                     cash_pmts__gt=0,
#                 ),
#                 distinct=True,
#             ),
#             fully_paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             amount_active__gt=0,
#                             total_shiped_amount=F("amount_active"),
#                             cash_pmts=F("total_shiped_amount"),
#                             cash_pmts__gt=0,
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             # Закрыто в системе (статус закрыт + полная отгрузка + полная оплата)
#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     amount_active__gt=0,
#                     total_shiped_amount=F("amount_active"),
#                     cash_pmts=F("total_shiped_amount"),
#                     cash_pmts__gt=0,
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#             closed_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             amount_active__gt=0,
#                             total_shiped_amount=F("amount_active"),
#                             cash_pmts=F("total_shiped_amount"),
#                             cash_pmts__gt=0,
#                             status__in=self.CLOSED_STATUSES,
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),
#         )

#     def _get_canceled_summary(self, period="YTD"):
#         qs = self._base_qs_all(period).filter(self._canceled_filter())

#         agg = qs.aggregate(
#             canceled_orders=Count("order_id", distinct=True),
#             canceled_amount=Coalesce(
#                 Sum("amount_cancelled"),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),
#         )

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "canceled_orders": agg["canceled_orders"] or 0,
#             "canceled_amount": float(agg["canceled_amount"] or 0),
#         }

#     def _build_stages(self, agg):
#         total_orders = agg["total_orders"] or 0
#         paid_orders = agg["paid_orders"] or 0
#         shipped_orders = agg["shipped_orders"] or 0
#         fully_paid_orders = agg["fully_paid_orders"] or 0
#         closed_orders = agg["closed_orders"] or 0

#         return [
#             {
#                 "name": "1. Создано заказов",
#                 "orders": total_orders,
#                 "amount": float(agg["total_amount"] or 0),
#                 "conversion_from_prev": 100.0,
#                 "conversion_from_start": 100.0,
#             },
#             {
#                 "name": "2. Есть оплата",
#                 "orders": paid_orders,
#                 "amount": float(agg["paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(paid_orders, total_orders),
#                 "conversion_from_start": self._pct(paid_orders, total_orders),
#             },
#             {
#                 "name": "3. Есть отгрузка",
#                 "orders": shipped_orders,
#                 "amount": float(agg["shipped_amount"] or 0),
#                 "conversion_from_prev": self._pct(shipped_orders, paid_orders),
#                 "conversion_from_start": self._pct(shipped_orders, total_orders),
#             },
#             {
#                 "name": "4. Полностью оплачено",
#                 "orders": fully_paid_orders,
#                 "amount": float(agg["fully_paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(fully_paid_orders, shipped_orders),
#                 "conversion_from_start": self._pct(fully_paid_orders, total_orders),
#             },
#             {
#                 "name": "5. Закрыто в системе",
#                 "orders": closed_orders,
#                 "amount": float(agg["closed_amount"] or 0),
#                 "conversion_from_prev": self._pct(closed_orders, fully_paid_orders),
#                 "conversion_from_start": self._pct(closed_orders, total_orders),
#             },
#         ]

#     def _get_funnel_for_period(self, period="YTD"):
#         qs = self._base_qs_active(period)
#         agg = self._aggregate_funnel(qs)
#         stages = self._build_stages(agg)
#         canceled = self._get_canceled_summary(period)

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "total_orders": agg["total_orders"] or 0,
#             "total_amount": float(agg["total_amount"] or 0),
#             "canceled_orders": canceled["canceled_orders"],
#             "canceled_amount": canceled["canceled_amount"],
#             "stages": stages,
#         }

#     def get_funnel_overall(self):
#         return {
#             "ytd": self._get_funnel_for_period("YTD"),
#             "mtd": self._get_funnel_for_period("MTD"),
#         }

#     def get_manager_orders_detail(self, manager_name, status_filter=None):
#         qs = MV_Orders.objects.filter(manager=manager_name)

#         if status_filter == "active":
#             qs = qs.exclude(self._canceled_filter())

#         elif status_filter == "canceled":
#             qs = qs.filter(self._canceled_filter())

#         elif status_filter == "no_payment":
#             qs = qs.filter(
#                 cash_pmts=0,
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "no_shipment":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount=0,
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "partial_payment":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount__gt=0,
#                 amount_active__gt=0,
#                 cash_pmts__lt=F("amount_active"),
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "not_closed":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount__gt=0,
#                 amount_active__gt=0,
#                 cash_pmts__gte=F("amount_active"),
#             ).exclude(
#                 status__in=self.CLOSED_STATUSES
#             ).exclude(
#                 self._canceled_filter()
#             )

#         return qs.order_by("-date_from")

#     def get_funnel_by_manager(self, limit=15):
#         qs = self._base_qs_active("YTD").exclude(
#             manager__isnull=True
#         ).exclude(
#             manager=""
#         )

#         managers = qs.values("manager").annotate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),

#             # Полностью оплачено И полностью отгружено
#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     amount_active__gt=0,
#                     total_shiped_amount=F("amount_active"),
#                     cash_pmts=F("total_shiped_amount"),
#                     cash_pmts__gt=0,
#                 ),
#                 distinct=True,
#             ),

#             # Закрыто в системе
#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     amount_active__gt=0,
#                     total_shiped_amount=F("amount_active"),
#                     cash_pmts=F("total_shiped_amount"),
#                     cash_pmts__gt=0,
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#         ).filter(
#             total_amount__gt=0
#         ).order_by("-total_amount")[:limit]

#         result = []

#         for mgr in managers:
#             total = mgr["total_orders"] or 0
#             paid = mgr["paid_orders"] or 0
#             shipped = mgr["shipped_orders"] or 0
#             fully_paid = mgr["fully_paid_orders"] or 0
#             closed = mgr["closed_orders"] or 0

#             result.append({
#                 "manager": mgr["manager"],
#                 "ytd": {
#                     "total_orders": total,
#                     "total_amount": float(mgr["total_amount"] or 0),
#                     "paid_orders": paid,
#                     "shipped_orders": shipped,
#                     "fully_paid_orders": fully_paid,
#                     "closed_orders": closed,

#                     "stuck_without_payment": total - paid,
#                     "stuck_without_shipment": paid - shipped,
#                     "stuck_not_fully_paid": shipped - fully_paid,
#                     "stuck_not_closed": fully_paid - closed,

#                     "conv_paid": self._pct(paid, total),
#                     "conv_shipped": self._pct(shipped, paid),
#                     "conv_fully_paid": self._pct(fully_paid, shipped),
#                     "conv_closed": self._pct(closed, fully_paid),
#                 },
#             })

#         return result

#     def _get_order_problem_status(self, obj):
#         status = obj.status or ""
#         change_status = getattr(obj, "change_status", None) or ""

#         is_canceled = (
#             status in self.CANCEL_STATUSES
#             or change_status in self.CANCEL_STATUSES
#         )

#         if is_canceled:
#             return "Отменен", "Исключен из основной воронки"

#         cash_pmts = obj.cash_pmts or 0
#         total_shiped_amount = obj.total_shiped_amount or 0
#         amount_active = obj.amount_active or 0

#         if cash_pmts <= 0:
#             return "Нет оплаты", "Заказ создан, но нет оплаты"

#         if total_shiped_amount <= 0:
#             return "Нет отгрузки", "Оплата есть, но нет отгрузки"

#         # ИСПРАВЛЕНО: проверка на частичную оплату с учетом полной отгрузки
#         if total_shiped_amount < amount_active:
#             return "Частичная отгрузка", "Отгружено не полностью"

#         if cash_pmts < total_shiped_amount:
#             return "Частичная оплата", "Отгружено полностью, но оплачено не полностью"

#         if status not in self.CLOSED_STATUSES:
#             return "Не закрыт в системе", "Полностью оплачен и отгружен, но статус не закрыт"

#         return "ОК", "Закрыт"

#     def _safe_date(self, value):
#         if not value:
#             return None
#         if hasattr(value, "date"):
#             return value.date()
#         return value

#     def _safe_float(self, value):
#         return float(value or 0)

#     def _safe_int(self, value):
#         return int(value or 0)

#     def _format_manager_name(self, manager_name):
#         """
#         Иванов Иван Иванович -> ИВАНОВ И.
#         Иванов Иван -> ИВАНОВ И.
#         Иванов -> ИВАНОВ
#         """
#         if not manager_name:
#             return ""

#         words = str(manager_name).strip().split()
#         if not words:
#             return ""

#         first = words[0].upper()

#         if len(words) >= 2 and words[1]:
#             return f"{first} {words[1][0].upper()}."

#         return first

#     def get_orders_detail_table(self, period="YTD"):
#         """Показывает только проблемные заказы (исключая ОК и Отменен)"""
#         qs = self._base_qs_all(period).order_by("-date_from", "manager", "number")

#         rows = []

#         for obj in qs:
#             problem_status, problem_comment = self._get_order_problem_status(obj)
            
#             # Пропускаем заказы со статусом ОК и Отменен
#             if problem_status in ["ОК", "Отменен"]:
#                 continue

#             # Преобразуем клиента в ЗАГЛАВНЫЕ БУКВЫ
#             client_upper = (obj.client or "").upper()
            
#             # Преобразуем менеджера: первая фамилия + первая буква имени
#             manager_formatted = self._format_manager_name(obj.manager or "")
            
#             # Преобразуем магазин в ЗАГЛАВНЫЕ БУКВЫ
#             store_upper = (obj.store or "").upper()

#             rows.append({
#                 "period": period,
#                 "problem_status": problem_status,
#                 "problem_comment": problem_comment,
#                 "number": obj.number or "",
#                 "date_from": self._safe_date(obj.date_from),
#                 "status": obj.status or "",
#                 "client": client_upper,
#                 "manager": manager_formatted,
#                 "store": store_upper,
#                 "amount_active": self._safe_float(obj.amount_active),
#                 "cash_pmts": self._safe_float(obj.cash_pmts),
#                 "total_shiped_amount": self._safe_float(obj.total_shiped_amount),
#             })

#         return rows

#     def get_loss_analysis(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": self._analyze_bottlenecks(ytd),
#             "mtd": self._analyze_bottlenecks(mtd),
#         }

#     def _analyze_bottlenecks(self, funnel_data):
#         stages = funnel_data["stages"]
#         result = []

#         for i in range(1, len(stages)):
#             prev = stages[i - 1]
#             curr = stages[i]

#             lost_orders = prev["orders"] - curr["orders"]
#             lost_amount = prev["amount"] - curr["amount"]

#             result.append({
#                 "from_stage": prev["name"],
#                 "to_stage": curr["name"],
#                 "lost_orders": lost_orders,
#                 "loss_amount": lost_amount,
#                 "loss_percent": self._pct(lost_orders, prev["orders"]),
#                 "reason": self._get_loss_reason(prev["name"], curr["name"]),
#             })

#         return result

#     def get_canceled_summary(self):
#         return {
#             "ytd": self._get_canceled_summary("YTD"),
#             "mtd": self._get_canceled_summary("MTD"),
#         }

#     def get_comparison_summary(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": {
#                 "total_orders": ytd["total_orders"],
#                 "total_amount": ytd["total_amount"],
#                 "closed_orders": ytd["stages"][-1]["orders"],
#                 "closed_amount": ytd["stages"][-1]["amount"],
#                 "canceled_orders": ytd["canceled_orders"],
#                 "canceled_amount": ytd["canceled_amount"],
#                 "final_conversion": ytd["stages"][-1]["conversion_from_start"],
#             },
#             "mtd": {
#                 "total_orders": mtd["total_orders"],
#                 "total_amount": mtd["total_amount"],
#                 "closed_orders": mtd["stages"][-1]["orders"],
#                 "closed_amount": mtd["stages"][-1]["amount"],
#                 "canceled_orders": mtd["canceled_orders"],
#                 "canceled_amount": mtd["canceled_amount"],
#                 "final_conversion": mtd["stages"][-1]["conversion_from_start"],
#             },
#         }

#     def _get_loss_reason(self, from_stage, to_stage):
#         reasons = {
#             ("1. Создано заказов", "2. Есть оплата"): "Зависло без оплаты",
#             ("2. Есть оплата", "3. Есть отгрузка"): "Оплачено, но не отгружено",
#             ("3. Есть отгрузка", "4. Полностью оплачено"): "Отгружено не полностью или оплачено не полностью",
#             ("4. Полностью оплачено", "5. Закрыто в системе"): "Полностью оплачено и отгружено, но не закрыто в системе",
#         }

#         return reasons.get((from_stage, to_stage), "Требуется анализ")




# # orders/reports/queries/funnel_analysis_query.py

# from datetime import date
# from django.db.models import Q, Count, Sum, F, Case, When, Value, DecimalField
# from django.db.models.functions import Coalesce
# from orders.models import MV_Orders


# class FunnelAnalysisQueries:
#     CANCEL_STATUSES = ["Отменен", "Отменён"]
#     CLOSED_STATUSES = ["Закрыт", "Закрыто"]

#     def _get_date_filters(self, period="YTD"):
#         today = date.today()

#         if period == "YTD":
#             return {"date_from__gte": date(today.year, 1, 1)}

#         if period == "MTD":
#             return {"date_from__gte": date(today.year, today.month, 1)}

#         return {}

#     def _has_field(self, field_name):
#         try:
#             MV_Orders._meta.get_field(field_name)
#             return True
#         except Exception:
#             return False

#     def _period_name(self, period):
#         today = date.today()

#         if period == "YTD":
#             return f"YTD с 01.01.{today.year}"

#         if period == "MTD":
#             return f"MTD с 01.{today.month:02d}.{today.year}"

#         return "За все время"

#     def _base_qs_all(self, period="YTD"):
#         qs = MV_Orders.objects.all()
#         date_filter = self._get_date_filters(period)

#         if date_filter:
#             qs = qs.filter(**date_filter)

#         return qs

#     def _canceled_filter(self):
#         q = Q(status__in=self.CANCEL_STATUSES)

#         if self._has_field("change_status"):
#             q |= Q(change_status__in=self.CANCEL_STATUSES)

#         return q

#     def _base_qs_active(self, period="YTD"):
#         return self._base_qs_all(period).exclude(self._canceled_filter())

#     def _pct(self, numerator, denominator):
#         return round(numerator / denominator * 100, 1) if denominator else 0

#     def _aggregate_funnel(self, qs):
#         return qs.aggregate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),
#             paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(cash_pmts__gt=0, then="cash_pmts"),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),
#             shipped_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             cash_pmts__gt=0,
#                             total_shiped_amount__gt=0,
#                             then="total_shiped_amount",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             # Полностью оплачено И полностью отгружено
#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     amount_active__gt=0,
#                     total_shiped_amount=F("amount_active"),
#                     cash_pmts=F("total_shiped_amount"),
#                     cash_pmts__gt=0,
#                 ),
#                 distinct=True,
#             ),
#             fully_paid_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             amount_active__gt=0,
#                             total_shiped_amount=F("amount_active"),
#                             cash_pmts=F("total_shiped_amount"),
#                             cash_pmts__gt=0,
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),

#             # Закрыто в системе (статус закрыт + полная отгрузка + полная оплата)
#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     amount_active__gt=0,
#                     total_shiped_amount=F("amount_active"),
#                     cash_pmts=F("total_shiped_amount"),
#                     cash_pmts__gt=0,
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#             closed_amount=Coalesce(
#                 Sum(
#                     Case(
#                         When(
#                             amount_active__gt=0,
#                             total_shiped_amount=F("amount_active"),
#                             cash_pmts=F("total_shiped_amount"),
#                             cash_pmts__gt=0,
#                             status__in=self.CLOSED_STATUSES,
#                             then="amount_active",
#                         ),
#                         default=Value(0),
#                         output_field=DecimalField(),
#                     )
#                 ),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),
#         )

#     def _get_canceled_summary(self, period="YTD"):
#         qs = self._base_qs_all(period).filter(self._canceled_filter())

#         agg = qs.aggregate(
#             canceled_orders=Count("order_id", distinct=True),
#             canceled_amount=Coalesce(
#                 Sum("amount_cancelled"),
#                 Value(0),
#                 output_field=DecimalField(),
#             ),
#         )

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "canceled_orders": agg["canceled_orders"] or 0,
#             "canceled_amount": float(agg["canceled_amount"] or 0),
#         }

#     def _build_stages(self, agg):
#         total_orders = agg["total_orders"] or 0
#         paid_orders = agg["paid_orders"] or 0
#         shipped_orders = agg["shipped_orders"] or 0
#         fully_paid_orders = agg["fully_paid_orders"] or 0
#         closed_orders = agg["closed_orders"] or 0

#         return [
#             {
#                 "name": "1. Создано заказов",
#                 "orders": total_orders,
#                 "amount": float(agg["total_amount"] or 0),
#                 "conversion_from_prev": 100.0,
#                 "conversion_from_start": 100.0,
#             },
#             {
#                 "name": "2. Есть оплата",
#                 "orders": paid_orders,
#                 "amount": float(agg["paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(paid_orders, total_orders),
#                 "conversion_from_start": self._pct(paid_orders, total_orders),
#             },
#             {
#                 "name": "3. Есть отгрузка",
#                 "orders": shipped_orders,
#                 "amount": float(agg["shipped_amount"] or 0),
#                 "conversion_from_prev": self._pct(shipped_orders, paid_orders),
#                 "conversion_from_start": self._pct(shipped_orders, total_orders),
#             },
#             {
#                 "name": "4. Полностью оплачено",
#                 "orders": fully_paid_orders,
#                 "amount": float(agg["fully_paid_amount"] or 0),
#                 "conversion_from_prev": self._pct(fully_paid_orders, shipped_orders),
#                 "conversion_from_start": self._pct(fully_paid_orders, total_orders),
#             },
#             {
#                 "name": "5. Закрыто в системе",
#                 "orders": closed_orders,
#                 "amount": float(agg["closed_amount"] or 0),
#                 "conversion_from_prev": self._pct(closed_orders, fully_paid_orders),
#                 "conversion_from_start": self._pct(closed_orders, total_orders),
#             },
#         ]

#     def _get_funnel_for_period(self, period="YTD"):
#         qs = self._base_qs_active(period)
#         agg = self._aggregate_funnel(qs)
#         stages = self._build_stages(agg)
#         canceled = self._get_canceled_summary(period)

#         return {
#             "period_key": period,
#             "period_name": self._period_name(period),
#             "total_orders": agg["total_orders"] or 0,
#             "total_amount": float(agg["total_amount"] or 0),
#             "canceled_orders": canceled["canceled_orders"],
#             "canceled_amount": canceled["canceled_amount"],
#             "stages": stages,
#         }

#     def get_funnel_overall(self):
#         return {
#             "ytd": self._get_funnel_for_period("YTD"),
#             "mtd": self._get_funnel_for_period("MTD"),
#         }

#     def get_manager_orders_detail(self, manager_name, status_filter=None):
#         qs = MV_Orders.objects.filter(manager=manager_name)

#         if status_filter == "active":
#             qs = qs.exclude(self._canceled_filter())

#         elif status_filter == "canceled":
#             qs = qs.filter(self._canceled_filter())

#         elif status_filter == "no_payment":
#             qs = qs.filter(
#                 cash_pmts=0,
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "no_shipment":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount=0,
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "partial_payment":
#             qs = qs.filter(
#                 cash_pmts__gt=0,
#                 total_shiped_amount__gt=0,
#                 amount_active__gt=0,
#                 cash_pmts__lt=F("amount_active"),
#             ).exclude(
#                 self._canceled_filter()
#             )

#         elif status_filter == "not_closed":
#             # Полностью оплачено и отгружено, но статус не закрыт
#             qs = qs.filter(
#                 amount_active__gt=0,
#                 total_shiped_amount=F("amount_active"),
#                 cash_pmts=F("total_shiped_amount"),
#                 cash_pmts__gt=0,
#             ).exclude(
#                 status__in=self.CLOSED_STATUSES
#             ).exclude(
#                 self._canceled_filter()
#             )

#         return qs.order_by("-date_from")

#     def get_funnel_by_manager(self, limit=15):
#         qs = self._base_qs_active("YTD").exclude(
#             manager__isnull=True
#         ).exclude(
#             manager=""
#         )

#         managers = qs.values("manager").annotate(
#             total_orders=Count("order_id", distinct=True),
#             total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

#             paid_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0),
#                 distinct=True,
#             ),

#             shipped_orders=Count(
#                 "order_id",
#                 filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
#                 distinct=True,
#             ),

#             # Полностью оплачено И полностью отгружено
#             fully_paid_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     amount_active__gt=0,
#                     total_shiped_amount=F("amount_active"),
#                     cash_pmts=F("total_shiped_amount"),
#                     cash_pmts__gt=0,
#                 ),
#                 distinct=True,
#             ),

#             # Закрыто в системе
#             closed_orders=Count(
#                 "order_id",
#                 filter=Q(
#                     amount_active__gt=0,
#                     total_shiped_amount=F("amount_active"),
#                     cash_pmts=F("total_shiped_amount"),
#                     cash_pmts__gt=0,
#                     status__in=self.CLOSED_STATUSES,
#                 ),
#                 distinct=True,
#             ),
#         ).filter(
#             total_amount__gt=0
#         ).order_by("-total_amount")[:limit]

#         result = []

#         for mgr in managers:
#             total = mgr["total_orders"] or 0
#             paid = mgr["paid_orders"] or 0
#             shipped = mgr["shipped_orders"] or 0
#             fully_paid = mgr["fully_paid_orders"] or 0
#             closed = mgr["closed_orders"] or 0

#             result.append({
#                 "manager": mgr["manager"],
#                 "ytd": {
#                     "total_orders": total,
#                     "total_amount": float(mgr["total_amount"] or 0),
#                     "paid_orders": paid,
#                     "shipped_orders": shipped,
#                     "fully_paid_orders": fully_paid,
#                     "closed_orders": closed,

#                     "stuck_without_payment": total - paid,
#                     "stuck_without_shipment": paid - shipped,
#                     "stuck_not_fully_paid": shipped - fully_paid,
#                     "stuck_not_closed": fully_paid - closed,

#                     "conv_paid": self._pct(paid, total),
#                     "conv_shipped": self._pct(shipped, paid),
#                     "conv_fully_paid": self._pct(fully_paid, shipped),
#                     "conv_closed": self._pct(closed, fully_paid),
#                 },
#             })

#         return result


    
    
#     def _get_order_problem_status(self, obj):
#         status = obj.status or ""
#         change_status = getattr(obj, "change_status", None) or ""

#         is_canceled = (
#             status in self.CANCEL_STATUSES
#             or change_status in self.CANCEL_STATUSES
#         )

#         if is_canceled:
#             return "Отменен", "Исключен из основной воронки"

#         cash_pmts = obj.cash_pmts or 0
#         total_shiped_amount = obj.total_shiped_amount or 0
#         amount_active = obj.amount_active or 0

#         if cash_pmts <= 0:
#             return "Нет оплаты", "Заказ создан, но нет оплаты"

#         if total_shiped_amount <= 0:
#             return "Нет отгрузки", "Оплата есть, но нет отгрузки"

#         if total_shiped_amount < amount_active:
#             return "Частичная отгрузка", "Отгружено не полностью"

#         if cash_pmts < total_shiped_amount:
#             return "Частичная оплата", "Отгружено полностью, но оплачено не полностью"

#         # ========== ИСПРАВЛЕНИЕ ТУТ ==========
#         # Полностью оплачено И полностью отгружено (те же условия, что в саммари)
#         if amount_active > 0 and total_shiped_amount == amount_active and cash_pmts == total_shiped_amount:
#             if status not in self.CLOSED_STATUSES:
#                 return "Не закрыт в системе", "Полностью оплачен и отгружен, но статус не закрыт"
#             return "ОК", "Закрыт"
        
#         # Если дошли сюда, значит оплата и отгрузка есть, но не полные
#         # Возвращаем какой-то статус по умолчанию
#         return "Проблема", "Требуется анализ"

#     def _safe_date(self, value):
#         if not value:
#             return None
#         if hasattr(value, "date"):
#             return value.date()
#         return value

#     def _safe_float(self, value):
#         return float(value or 0)

#     def _safe_int(self, value):
#         return int(value or 0)

#     def _format_manager_name(self, manager_name):
#         """
#         Иванов Иван Иванович -> ИВАНОВ И.
#         Иванов Иван -> ИВАНОВ И.
#         Иванов -> ИВАНОВ
#         """
#         if not manager_name:
#             return ""

#         words = str(manager_name).strip().split()
#         if not words:
#             return ""

#         first = words[0].upper()

#         if len(words) >= 2 and words[1]:
#             return f"{first} {words[1][0].upper()}."

#         return first

#     def get_orders_detail_table(self, period="YTD"):
#         """Показывает только проблемные заказы (исключая ОК и Отменен)"""
#         qs = self._base_qs_all(period).order_by("-date_from", "manager", "number")

#         rows = []

#         for obj in qs:
#             problem_status, problem_comment = self._get_order_problem_status(obj)
            
#             # Пропускаем заказы со статусом ОК и Отменен
#             if problem_status in ["ОК", "Отменен"]:
#                 continue

#             # Преобразуем клиента в ЗАГЛАВНЫЕ БУКВЫ
#             client_upper = (obj.client or "").upper()
            
#             # Преобразуем менеджера: первая фамилия + первая буква имени
#             manager_formatted = self._format_manager_name(obj.manager or "")
            
#             # Преобразуем магазин в ЗАГЛАВНЫЕ БУКВЫ
#             store_upper = (obj.store or "").upper()

#             rows.append({
#                 "period": period,
#                 "problem_status": problem_status,
#                 "problem_comment": problem_comment,
#                 "number": obj.number or "",
#                 "date_from": self._safe_date(obj.date_from),
#                 "status": obj.status or "",
#                 "client": client_upper,
#                 "manager": manager_formatted,
#                 "store": store_upper,
#                 "amount_active": self._safe_float(obj.amount_active),
#                 "cash_pmts": self._safe_float(obj.cash_pmts),
#                 "total_shiped_amount": self._safe_float(obj.total_shiped_amount),
#             })

#         return rows

#     def get_not_closed_orders(self):
#         """
#         Получение заказов, которые полностью оплачены и отгружены,
#         но статус не закрыт (аналог completed_orders_wrong_status_query)
#         """
#         result = []

#         # Получаем все не закрытые и не отмененные заказы
#         orders = MV_Orders.objects.exclude(
#             status__in=['Закрыт', 'Отменен']
#         ).filter(
#             amount_active__gt=0
#         )

#         for order in orders:
#             # Безопасное преобразование в Decimal
#             try:
#                 amount_active = Decimal(str(order.amount_active or 0))
#                 total_shiped = Decimal(str(order.total_shiped_amount or 0))
#                 cash_pmts = Decimal(str(order.cash_pmts or 0))
#             except (ValueError, TypeError):
#                 continue

#             # Приводим к 2 знакам
#             from decimal import Decimal, ROUND_HALF_UP
#             amount_active = amount_active.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
#             total_shiped = total_shiped.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
#             cash_pmts = cash_pmts.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

#             # Корректируем отрицательные оплаты
#             if cash_pmts < 0:
#                 cash_pmts = Decimal('0')

#             # Условие: отгрузили всё, что в заказе И оплатили всё, что отгрузили
#             if total_shiped == amount_active and cash_pmts == total_shiped and amount_active > 0:

#                 # Форматируем даты
#                 date_from = order.date_from.date() if order.date_from else None
#                 update_at = order.update_at.date() if order.update_at else None

#                 # Дней с момента последнего изменения
#                 days_since_update = 0
#                 if update_at:
#                     days_since_update = (date.today() - update_at).days

#                 result.append({
#                     'order_name': f"{order.number or ''} от {date_from.strftime('%d.%m.%Y') if date_from else ''}" if order.number else order.order_name or '',
#                     'number': order.number or '',
#                     'date_from': date_from.strftime('%Y-%m-%d') if date_from else '',
#                     'update_at': update_at.strftime('%Y-%m-%d') if update_at else '',
#                     'status': order.status or '',
#                     'client': (order.client or '').upper(),
#                     'manager': self._format_manager_name(order.manager or ''),
#                     'store': (order.store or '').upper(),
#                     'amount_active': float(amount_active),
#                     'total_shiped_amount': float(total_shiped),
#                     'cash_pmts': float(cash_pmts),
#                     'days_since_update': days_since_update,
#                 })

#         # Сортируем по сумме (крупные сверху)
#         result.sort(key=lambda x: -x['amount_active'])

#         return result

#     def get_not_closed_summary(self, orders_data):
#         """Получение сводной статистики по незакрытым заказам"""
#         if not orders_data:
#             return {
#                 'total_orders': 0,
#                 'total_amount': 0,
#                 'unique_clients': 0,
#                 'unique_managers': 0,
#             }

#         return {
#             'total_orders': len(orders_data),
#             'total_amount': sum(o.get('amount_active', 0) for o in orders_data),
#             'unique_clients': len(set(o.get('client', '') for o in orders_data if o.get('client'))),
#             'unique_managers': len(set(o.get('manager', '') for o in orders_data if o.get('manager'))),
#         }

#     def get_loss_analysis(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": self._analyze_bottlenecks(ytd),
#             "mtd": self._analyze_bottlenecks(mtd),
#         }

#     def _analyze_bottlenecks(self, funnel_data):
#         stages = funnel_data["stages"]
#         result = []

#         for i in range(1, len(stages)):
#             prev = stages[i - 1]
#             curr = stages[i]

#             lost_orders = prev["orders"] - curr["orders"]
#             lost_amount = prev["amount"] - curr["amount"]

#             result.append({
#                 "from_stage": prev["name"],
#                 "to_stage": curr["name"],
#                 "lost_orders": lost_orders,
#                 "loss_amount": lost_amount,
#                 "loss_percent": self._pct(lost_orders, prev["orders"]),
#                 "reason": self._get_loss_reason(prev["name"], curr["name"]),
#             })

#         return result

#     def get_canceled_summary(self):
#         return {
#             "ytd": self._get_canceled_summary("YTD"),
#             "mtd": self._get_canceled_summary("MTD"),
#         }

#     def get_comparison_summary(self):
#         ytd = self._get_funnel_for_period("YTD")
#         mtd = self._get_funnel_for_period("MTD")

#         return {
#             "ytd": {
#                 "total_orders": ytd["total_orders"],
#                 "total_amount": ytd["total_amount"],
#                 "closed_orders": ytd["stages"][-1]["orders"],
#                 "closed_amount": ytd["stages"][-1]["amount"],
#                 "canceled_orders": ytd["canceled_orders"],
#                 "canceled_amount": ytd["canceled_amount"],
#                 "final_conversion": ytd["stages"][-1]["conversion_from_start"],
#             },
#             "mtd": {
#                 "total_orders": mtd["total_orders"],
#                 "total_amount": mtd["total_amount"],
#                 "closed_orders": mtd["stages"][-1]["orders"],
#                 "closed_amount": mtd["stages"][-1]["amount"],
#                 "canceled_orders": mtd["canceled_orders"],
#                 "canceled_amount": mtd["canceled_amount"],
#                 "final_conversion": mtd["stages"][-1]["conversion_from_start"],
#             },
#         }

#     def _get_loss_reason(self, from_stage, to_stage):
#         reasons = {
#             ("1. Создано заказов", "2. Есть оплата"): "Зависло без оплаты",
#             ("2. Есть оплата", "3. Есть отгрузка"): "Оплачено, но не отгружено",
#             ("3. Есть отгрузка", "4. Полностью оплачено"): "Отгружено не полностью или оплачено не полностью",
#             ("4. Полностью оплачено", "5. Закрыто в системе"): "Полностью оплачено и отгружено, но не закрыто в системе",
#         }

#         return reasons.get((from_stage, to_stage), "Требуется анализ")





from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Q, Count, Sum, F, Case, When, Value, DecimalField
from django.db.models.functions import Coalesce
from orders.models import MV_Orders


class FunnelAnalysisQueries:
    CANCEL_STATUSES = ["Отменен", "Отменён"]
    CLOSED_STATUSES = ["Закрыт", "Закрыто"]

    def _get_date_filters(self, period="YTD"):
        today = date.today()

        if period == "YTD":
            return {"date_from__gte": date(today.year, 1, 1)}

        if period == "MTD":
            return {"date_from__gte": date(today.year, today.month, 1)}

        return {}

    def _has_field(self, field_name):
        try:
            MV_Orders._meta.get_field(field_name)
            return True
        except Exception:
            return False

    def _period_name(self, period):
        today = date.today()

        if period == "YTD":
            return f"YTD с 01.01.{today.year}"

        if period == "MTD":
            return f"MTD с 01.{today.month:02d}.{today.year}"

        return "За все время"

    def _base_qs_all(self, period="YTD"):
        qs = MV_Orders.objects.all()
        date_filter = self._get_date_filters(period)

        if date_filter:
            qs = qs.filter(**date_filter)

        return qs

    def _canceled_filter(self):
        q = Q(status__in=self.CANCEL_STATUSES)

        if self._has_field("change_status"):
            q |= Q(change_status__in=self.CANCEL_STATUSES)

        return q

    def _returned_filter(self):
        """Фильтр для заказов, которые полностью возвращены (отказ после оплаты/отгрузки)"""
        q = Q()
        
        if self._has_field("cash_returned"):
            q |= Q(cash_returned__gte=F("amount_active"), amount_active__gt=0)
        
        if self._has_field("returned_amount"):
            q |= Q(returned_amount__gte=F("amount_active"), amount_active__gt=0)
        
        return q

    def _base_qs_active(self, period="YTD"):
        """Активные заказы: исключаем отмененные и полностью возвращенные"""
        qs = self._base_qs_all(period)
        qs = qs.exclude(self._canceled_filter())
        qs = qs.exclude(self._returned_filter())
        return qs

    def _pct(self, numerator, denominator):
        return round(numerator / denominator * 100, 1) if denominator else 0

    def _aggregate_funnel(self, qs):
        return qs.aggregate(
            total_orders=Count("order_id", distinct=True),
            total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

            paid_orders=Count(
                "order_id",
                filter=Q(cash_pmts__gt=0),
                distinct=True,
            ),
            paid_amount=Coalesce(
                Sum(
                    Case(
                        When(cash_pmts__gt=0, then="cash_pmts"),
                        default=Value(0),
                        output_field=DecimalField(),
                    )
                ),
                Value(0),
                output_field=DecimalField(),
            ),

            shipped_orders=Count(
                "order_id",
                filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
                distinct=True,
            ),
            shipped_amount=Coalesce(
                Sum(
                    Case(
                        When(
                            cash_pmts__gt=0,
                            total_shiped_amount__gt=0,
                            then="total_shiped_amount",
                        ),
                        default=Value(0),
                        output_field=DecimalField(),
                    )
                ),
                Value(0),
                output_field=DecimalField(),
            ),

            # Полностью оплачено И полностью отгружено
            fully_paid_orders=Count(
                "order_id",
                filter=Q(
                    amount_active__gt=0,
                    total_shiped_amount=F("amount_active"),
                    cash_pmts=F("total_shiped_amount"),
                    cash_pmts__gt=0,
                ),
                distinct=True,
            ),
            fully_paid_amount=Coalesce(
                Sum(
                    Case(
                        When(
                            amount_active__gt=0,
                            total_shiped_amount=F("amount_active"),
                            cash_pmts=F("total_shiped_amount"),
                            cash_pmts__gt=0,
                            then="amount_active",
                        ),
                        default=Value(0),
                        output_field=DecimalField(),
                    )
                ),
                Value(0),
                output_field=DecimalField(),
            ),

            # Закрыто в системе (статус закрыт + полная отгрузка + полная оплата)
            closed_orders=Count(
                "order_id",
                filter=Q(
                    amount_active__gt=0,
                    total_shiped_amount=F("amount_active"),
                    cash_pmts=F("total_shiped_amount"),
                    cash_pmts__gt=0,
                    status__in=self.CLOSED_STATUSES,
                ),
                distinct=True,
            ),
            closed_amount=Coalesce(
                Sum(
                    Case(
                        When(
                            amount_active__gt=0,
                            total_shiped_amount=F("amount_active"),
                            cash_pmts=F("total_shiped_amount"),
                            cash_pmts__gt=0,
                            status__in=self.CLOSED_STATUSES,
                            then="amount_active",
                        ),
                        default=Value(0),
                        output_field=DecimalField(),
                    )
                ),
                Value(0),
                output_field=DecimalField(),
            ),
        )

    def _get_canceled_summary(self, period="YTD"):
        qs = self._base_qs_all(period).filter(self._canceled_filter())

        agg = qs.aggregate(
            canceled_orders=Count("order_id", distinct=True),
            canceled_amount=Coalesce(
                Sum("amount_cancelled"),
                Value(0),
                output_field=DecimalField(),
            ),
        )

        return {
            "period_key": period,
            "period_name": self._period_name(period),
            "canceled_orders": agg["canceled_orders"] or 0,
            "canceled_amount": float(agg["canceled_amount"] or 0),
        }

    def _get_returned_summary(self, period="YTD"):
        """Сводка по полностью возвращенным заказам"""
        qs = self._base_qs_all(period).filter(self._returned_filter())

        agg = qs.aggregate(
            returned_orders=Count("order_id", distinct=True),
            returned_amount=Coalesce(
                Sum("amount_active"),
                Value(0),
                output_field=DecimalField(),
            ),
        )

        return {
            "period_key": period,
            "period_name": self._period_name(period),
            "returned_orders": agg["returned_orders"] or 0,
            "returned_amount": float(agg["returned_amount"] or 0),
        }

    def _build_stages(self, agg):
        total_orders = agg["total_orders"] or 0
        paid_orders = agg["paid_orders"] or 0
        shipped_orders = agg["shipped_orders"] or 0
        fully_paid_orders = agg["fully_paid_orders"] or 0
        closed_orders = agg["closed_orders"] or 0

        return [
            {
                "name": "1. Создано заказов",
                "orders": total_orders,
                "amount": float(agg["total_amount"] or 0),
                "conversion_from_prev": 100.0,
                "conversion_from_start": 100.0,
            },
            {
                "name": "2. Есть оплата",
                "orders": paid_orders,
                "amount": float(agg["paid_amount"] or 0),
                "conversion_from_prev": self._pct(paid_orders, total_orders),
                "conversion_from_start": self._pct(paid_orders, total_orders),
            },
            {
                "name": "3. Есть отгрузка",
                "orders": shipped_orders,
                "amount": float(agg["shipped_amount"] or 0),
                "conversion_from_prev": self._pct(shipped_orders, paid_orders),
                "conversion_from_start": self._pct(shipped_orders, total_orders),
            },
            {
                "name": "4. Полностью оплачено",
                "orders": fully_paid_orders,
                "amount": float(agg["fully_paid_amount"] or 0),
                "conversion_from_prev": self._pct(fully_paid_orders, shipped_orders),
                "conversion_from_start": self._pct(fully_paid_orders, total_orders),
            },
            {
                "name": "5. Закрыто в системе",
                "orders": closed_orders,
                "amount": float(agg["closed_amount"] or 0),
                "conversion_from_prev": self._pct(closed_orders, fully_paid_orders),
                "conversion_from_start": self._pct(closed_orders, total_orders),
            },
        ]

    def _get_funnel_for_period(self, period="YTD"):
        qs = self._base_qs_active(period)
        agg = self._aggregate_funnel(qs)
        stages = self._build_stages(agg)
        canceled = self._get_canceled_summary(period)
        returned = self._get_returned_summary(period)

        return {
            "period_key": period,
            "period_name": self._period_name(period),
            "total_orders": agg["total_orders"] or 0,
            "total_amount": float(agg["total_amount"] or 0),
            "canceled_orders": canceled["canceled_orders"],
            "canceled_amount": canceled["canceled_amount"],
            "returned_orders": returned["returned_orders"],
            "returned_amount": returned["returned_amount"],
            "stages": stages,
        }

    def get_funnel_overall(self):
        return {
            "ytd": self._get_funnel_for_period("YTD"),
            "mtd": self._get_funnel_for_period("MTD"),
        }

    def get_manager_orders_detail(self, manager_name, status_filter=None):
        qs = MV_Orders.objects.filter(manager=manager_name)

        if status_filter == "active":
            qs = qs.exclude(self._canceled_filter()).exclude(self._returned_filter())

        elif status_filter == "canceled":
            qs = qs.filter(self._canceled_filter())

        elif status_filter == "returned":
            qs = qs.filter(self._returned_filter())

        elif status_filter == "no_payment":
            qs = qs.filter(
                cash_pmts=0,
            ).exclude(
                self._canceled_filter()
            ).exclude(
                self._returned_filter()
            )

        elif status_filter == "no_shipment":
            qs = qs.filter(
                cash_pmts__gt=0,
                total_shiped_amount=0,
            ).exclude(
                self._canceled_filter()
            ).exclude(
                self._returned_filter()
            )

        elif status_filter == "partial_payment":
            qs = qs.filter(
                cash_pmts__gt=0,
                total_shiped_amount__gt=0,
                amount_active__gt=0,
                cash_pmts__lt=F("amount_active"),
            ).exclude(
                self._canceled_filter()
            ).exclude(
                self._returned_filter()
            )

        elif status_filter == "not_closed":
            # Полностью оплачено и отгружено, но статус не закрыт
            qs = qs.filter(
                amount_active__gt=0,
                total_shiped_amount=F("amount_active"),
                cash_pmts=F("total_shiped_amount"),
                cash_pmts__gt=0,
            ).exclude(
                status__in=self.CLOSED_STATUSES
            ).exclude(
                self._canceled_filter()
            ).exclude(
                self._returned_filter()
            )

        return qs.order_by("-date_from")

    def get_funnel_by_manager(self, limit=15):
        qs = self._base_qs_active("YTD").exclude(
            manager__isnull=True
        ).exclude(
            manager=""
        )

        managers = qs.values("manager").annotate(
            total_orders=Count("order_id", distinct=True),
            total_amount=Coalesce(Sum("amount_active"), Value(0), output_field=DecimalField()),

            paid_orders=Count(
                "order_id",
                filter=Q(cash_pmts__gt=0),
                distinct=True,
            ),

            shipped_orders=Count(
                "order_id",
                filter=Q(cash_pmts__gt=0, total_shiped_amount__gt=0),
                distinct=True,
            ),

            # Полностью оплачено И полностью отгружено
            fully_paid_orders=Count(
                "order_id",
                filter=Q(
                    amount_active__gt=0,
                    total_shiped_amount=F("amount_active"),
                    cash_pmts=F("total_shiped_amount"),
                    cash_pmts__gt=0,
                ),
                distinct=True,
            ),

            # Закрыто в системе
            closed_orders=Count(
                "order_id",
                filter=Q(
                    amount_active__gt=0,
                    total_shiped_amount=F("amount_active"),
                    cash_pmts=F("total_shiped_amount"),
                    cash_pmts__gt=0,
                    status__in=self.CLOSED_STATUSES,
                ),
                distinct=True,
            ),
        ).filter(
            total_amount__gt=0
        ).order_by("-total_amount")[:limit]

        result = []

        for mgr in managers:
            total = mgr["total_orders"] or 0
            paid = mgr["paid_orders"] or 0
            shipped = mgr["shipped_orders"] or 0
            fully_paid = mgr["fully_paid_orders"] or 0
            closed = mgr["closed_orders"] or 0

            result.append({
                "manager": mgr["manager"],
                "ytd": {
                    "total_orders": total,
                    "total_amount": float(mgr["total_amount"] or 0),
                    "paid_orders": paid,
                    "shipped_orders": shipped,
                    "fully_paid_orders": fully_paid,
                    "closed_orders": closed,

                    "stuck_without_payment": total - paid,
                    "stuck_without_shipment": paid - shipped,
                    "stuck_not_fully_paid": shipped - fully_paid,
                    "stuck_not_closed": fully_paid - closed,

                    "conv_paid": self._pct(paid, total),
                    "conv_shipped": self._pct(shipped, paid),
                    "conv_fully_paid": self._pct(fully_paid, shipped),
                    "conv_closed": self._pct(closed, fully_paid),
                },
            })

        return result

    def _get_order_problem_status(self, obj):
        status = obj.status or ""
        change_status = getattr(obj, "change_status", None) or ""

        is_canceled = (
            status in self.CANCEL_STATUSES
            or change_status in self.CANCEL_STATUSES
        )

        if is_canceled:
            return "Отменен", "Исключен из основной воронки"

        cash_pmts = obj.cash_pmts or 0
        total_shiped_amount = obj.total_shiped_amount or 0
        amount_active = obj.amount_active or 0

        # Проверка на полный возврат
        cash_returned = getattr(obj, "cash_returned", 0) or 0
        returned_amount = getattr(obj, "returned_amount", 0) or 0

        if amount_active > 0 and (cash_returned >= amount_active or returned_amount >= amount_active):
            return "Полностью возвращен", "Была оплата/отгрузка, но клиент отказался (полный возврат)"

        if cash_pmts <= 0:
            return "Нет оплаты", "Заказ создан, но нет оплаты"

        if total_shiped_amount <= 0:
            return "Нет отгрузки", "Оплата есть, но нет отгрузки"

        if total_shiped_amount < amount_active:
            return "Частичная отгрузка", "Отгружено не полностью"

        if cash_pmts < total_shiped_amount:
            return "Частичная оплата", "Отгружено полностью, но оплачено не полностью"

        # Полностью оплачено И полностью отгружено (те же условия, что в саммари)
        if amount_active > 0 and total_shiped_amount == amount_active and cash_pmts == total_shiped_amount:
            if status not in self.CLOSED_STATUSES:
                return "Не закрыт в системе", "Полностью оплачен и отгружен, но статус не закрыт"
            return "ОК", "Закрыт"

        return "Проблема", "Требуется анализ"

    def _safe_date(self, value):
        if not value:
            return None
        if hasattr(value, "date"):
            return value.date()
        return value

    def _safe_float(self, value):
        return float(value or 0)

    def _safe_int(self, value):
        return int(value or 0)

    def _format_manager_name(self, manager_name):
        """
        Иванов Иван Иванович -> ИВАНОВ И.
        Иванов Иван -> ИВАНОВ И.
        Иванов -> ИВАНОВ
        """
        if not manager_name:
            return ""

        words = str(manager_name).strip().split()
        if not words:
            return ""

        first = words[0].upper()

        if len(words) >= 2 and words[1]:
            return f"{first} {words[1][0].upper()}."

        return first

    def get_orders_detail_table(self, period="YTD"):
        """Показывает только проблемные заказы (исключая ОК, Отменен и Полностью возвращен)"""
        # Используем _base_qs_active - ту же логику, что и в get_funnel_by_manager
        # Это исключает отмененные и полностью возвращенные заказы на уровне QuerySet
        qs = self._base_qs_active(period).order_by("-date_from", "manager", "number")

        rows = []

        for obj in qs:
            problem_status, problem_comment = self._get_order_problem_status(obj)

            # Пропускаем заказы со статусом ОК (полностью закрытые)
            # Отмененных и возвращенных здесь уже нет, потому что _base_qs_active их исключает
            if problem_status == "ОК":
                continue

            client_upper = (obj.client or "").upper()
            manager_formatted = self._format_manager_name(obj.manager or "")
            store_upper = (obj.store or "").upper()

            rows.append({
                "period": period,
                "problem_status": problem_status,
                "problem_comment": problem_comment,
                "number": obj.number or "",
                "date_from": self._safe_date(obj.date_from),
                "status": obj.status or "",
                "client": client_upper,
                "manager": manager_formatted,
                "store": store_upper,
                "amount_active": self._safe_float(obj.amount_active),
                "cash_pmts": self._safe_float(obj.cash_pmts),
                "total_shiped_amount": self._safe_float(obj.total_shiped_amount),
            })

        return rows

    def get_returned_orders_detail(self, period="YTD"):
        """Детализация полностью возвращенных заказов"""
        qs = self._base_qs_all(period).filter(self._returned_filter()).order_by("-date_from", "manager", "number")

        rows = []

        for obj in qs:
            client_upper = (obj.client or "").upper()
            manager_formatted = self._format_manager_name(obj.manager or "")
            store_upper = (obj.store or "").upper()
            
            cash_returned = getattr(obj, "cash_returned", 0) or 0
            returned_amount = getattr(obj, "returned_amount", 0) or 0

            rows.append({
                "period": period,
                "number": obj.number or "",
                "date_from": self._safe_date(obj.date_from),
                "status": obj.status or "",
                "client": client_upper,
                "manager": manager_formatted,
                "store": store_upper,
                "amount_active": self._safe_float(obj.amount_active),
                "cash_pmts": self._safe_float(obj.cash_pmts),
                "total_shiped_amount": self._safe_float(obj.total_shiped_amount),
                "cash_returned": self._safe_float(cash_returned),
                "returned_amount": self._safe_float(returned_amount),
            })

        return rows

    def get_not_closed_orders(self):
        """
        Получение заказов, которые полностью оплачены и отгружены,
        но статус не закрыт (аналог completed_orders_wrong_status_query)
        """
        result = []

        # Получаем все не закрытые и не отмененные заказы
        orders = MV_Orders.objects.exclude(
            status__in=['Закрыт', 'Отменен']
        ).filter(
            amount_active__gt=0
        )

        for order in orders:
            # Безопасное преобразование в Decimal
            try:
                amount_active = Decimal(str(order.amount_active or 0))
                total_shiped = Decimal(str(order.total_shiped_amount or 0))
                cash_pmts = Decimal(str(order.cash_pmts or 0))
            except (ValueError, TypeError):
                continue

            # Приводим к 2 знакам
            amount_active = amount_active.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_shiped = total_shiped.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cash_pmts = cash_pmts.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Корректируем отрицательные оплаты
            if cash_pmts < 0:
                cash_pmts = Decimal('0')

            # Условие: отгрузили всё, что в заказе И оплатили всё, что отгрузили
            if total_shiped == amount_active and cash_pmts == total_shiped and amount_active > 0:

                # Форматируем даты
                date_from = order.date_from.date() if order.date_from else None
                update_at = order.update_at.date() if order.update_at else None

                # Дней с момента последнего изменения
                days_since_update = 0
                if update_at:
                    days_since_update = (date.today() - update_at).days

                result.append({
                    'order_name': f"{order.number or ''} от {date_from.strftime('%d.%m.%Y') if date_from else ''}" if order.number else order.order_name or '',
                    'number': order.number or '',
                    'date_from': date_from.strftime('%Y-%m-%d') if date_from else '',
                    'update_at': update_at.strftime('%Y-%m-%d') if update_at else '',
                    'status': order.status or '',
                    'client': (order.client or '').upper(),
                    'manager': self._format_manager_name(order.manager or ''),
                    'store': (order.store or '').upper(),
                    'amount_active': float(amount_active),
                    'total_shiped_amount': float(total_shiped),
                    'cash_pmts': float(cash_pmts),
                    'days_since_update': days_since_update,
                })

        # Сортируем по сумме (крупные сверху)
        result.sort(key=lambda x: -x['amount_active'])

        return result

    def get_not_closed_summary(self, orders_data):
        """Получение сводной статистики по незакрытым заказам"""
        if not orders_data:
            return {
                'total_orders': 0,
                'total_amount': 0,
                'unique_clients': 0,
                'unique_managers': 0,
            }

        return {
            'total_orders': len(orders_data),
            'total_amount': sum(o.get('amount_active', 0) for o in orders_data),
            'unique_clients': len(set(o.get('client', '') for o in orders_data if o.get('client'))),
            'unique_managers': len(set(o.get('manager', '') for o in orders_data if o.get('manager'))),
        }

    def get_loss_analysis(self):
        ytd = self._get_funnel_for_period("YTD")
        mtd = self._get_funnel_for_period("MTD")

        return {
            "ytd": self._analyze_bottlenecks(ytd),
            "mtd": self._analyze_bottlenecks(mtd),
        }

    def _analyze_bottlenecks(self, funnel_data):
        stages = funnel_data["stages"]
        result = []

        for i in range(1, len(stages)):
            prev = stages[i - 1]
            curr = stages[i]

            lost_orders = prev["orders"] - curr["orders"]
            lost_amount = prev["amount"] - curr["amount"]

            result.append({
                "from_stage": prev["name"],
                "to_stage": curr["name"],
                "lost_orders": lost_orders,
                "loss_amount": lost_amount,
                "loss_percent": self._pct(lost_orders, prev["orders"]),
                "reason": self._get_loss_reason(prev["name"], curr["name"]),
            })

        return result

    def get_canceled_summary(self):
        return {
            "ytd": self._get_canceled_summary("YTD"),
            "mtd": self._get_canceled_summary("MTD"),
        }

    def get_returned_summary(self):
        return {
            "ytd": self._get_returned_summary("YTD"),
            "mtd": self._get_returned_summary("MTD"),
        }

    def get_comparison_summary(self):
        ytd = self._get_funnel_for_period("YTD")
        mtd = self._get_funnel_for_period("MTD")

        return {
            "ytd": {
                "total_orders": ytd["total_orders"],
                "total_amount": ytd["total_amount"],
                "closed_orders": ytd["stages"][-1]["orders"],
                "closed_amount": ytd["stages"][-1]["amount"],
                "canceled_orders": ytd["canceled_orders"],
                "canceled_amount": ytd["canceled_amount"],
                "returned_orders": ytd["returned_orders"],
                "returned_amount": ytd["returned_amount"],
                "final_conversion": ytd["stages"][-1]["conversion_from_start"],
            },
            "mtd": {
                "total_orders": mtd["total_orders"],
                "total_amount": mtd["total_amount"],
                "closed_orders": mtd["stages"][-1]["orders"],
                "closed_amount": mtd["stages"][-1]["amount"],
                "canceled_orders": mtd["canceled_orders"],
                "canceled_amount": mtd["canceled_amount"],
                "returned_orders": mtd["returned_orders"],
                "returned_amount": mtd["returned_amount"],
                "final_conversion": mtd["stages"][-1]["conversion_from_start"],
            },
        }

    def _get_loss_reason(self, from_stage, to_stage):
        reasons = {
            ("1. Создано заказов", "2. Есть оплата"): "Зависло без оплаты",
            ("2. Есть оплата", "3. Есть отгрузка"): "Оплачено, но не отгружено",
            ("3. Есть отгрузка", "4. Полностью оплачено"): "Отгружено не полностью или оплачено не полностью",
            ("4. Полностью оплачено", "5. Закрыто в системе"): "Полностью оплачено и отгружено, но не закрыто в системе",
        }

        return reasons.get((from_stage, to_stage), "Требуется анализ")
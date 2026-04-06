# corporate/reports/agents/agents_revenue.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Sum, Count
from django.db.models.functions import Coalesce

from corporate.models import Agents
from sales.models import SalesData

from .utils import _d


@dataclass
class AgentRow:
    agent_id: int
    name: str
    report_name: str
    tel: str
    email: str
    dt: Decimal
    cr: Decimal
    net: Decimal
    orders: int
    lines: int


@dataclass
class Totals:
    agents: int
    dt: Decimal
    cr: Decimal
    net: Decimal
    orders: int
    lines: int


def get_agents_metrics(
    *,
    date_from: date,
    date_to: date,
    ids: list[int] | None = None,
) -> tuple[list[AgentRow], Totals]:
    """
    Метрики по агентам за период [date_from, date_to].

    dt  = продажи
    cr  = возвраты
    net = dt - cr
    orders = distinct orders
    lines  = кол-во строк SalesData
    """
    ids = ids or []

    sales = SalesData.objects.filter(
        date__gte=date_from,
        date__lte=date_to,
        agent__isnull=False,
    )

    if ids:
        sales = sales.filter(agent_id__in=ids)

    agg = (
        sales.values("agent_id")
        .annotate(
            dt=Coalesce(Sum("dt"), Decimal("0")),
            cr=Coalesce(Sum("cr"), Decimal("0")),
            orders=Count("orders", distinct=True),
            lines=Count("id"),
        )
    )

    agg_map = {int(r["agent_id"]): r for r in agg}

    # Если ids не передали — берем всех агентов, у которых есть продажи в период
    # Если ids передали — показываем только выбранных (даже если в периоде нет продаж, они просто не попадут в agg_map)
    agents_qs = Agents.objects.filter(id__in=(ids or list(agg_map.keys()))).order_by("name")
    agents_map = {a.id: a for a in agents_qs}

    rows: list[AgentRow] = []
    for agent_id, a in agents_map.items():
        r = agg_map.get(agent_id)

        dt = _d(r.get("dt")) if r else Decimal("0")
        cr = _d(r.get("cr")) if r else Decimal("0")
        net = dt - cr
        orders = int(r.get("orders") or 0) if r else 0
        lines = int(r.get("lines") or 0) if r else 0

        rows.append(
            AgentRow(
                agent_id=agent_id,
                name=(a.name or "").strip(),
                report_name=(a.report_name or "").strip(),
                tel=(a.tel or "").strip(),
                email=(a.email or "").strip(),
                dt=dt,
                cr=cr,
                net=net,
                orders=orders,
                lines=lines,
            )
        )

    # сортировка: сначала по net, потом по dt
    rows.sort(key=lambda x: (x.net, x.dt), reverse=True)

    totals = Totals(
        agents=len(rows),
        dt=sum((x.dt for x in rows), Decimal("0")),
        cr=sum((x.cr for x in rows), Decimal("0")),
        net=sum((x.net for x in rows), Decimal("0")),
        orders=sum((x.orders for x in rows), 0),
        lines=sum((x.lines for x in rows), 0),
    )
    return rows, totals
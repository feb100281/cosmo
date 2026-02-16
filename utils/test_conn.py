import os
import pandas as pd
from dotenv import load_dotenv

from sqlalchemy import create_engine, text

# грузим .env из текущей директории (или выше, если у тебя так настроено)  
load_dotenv()

def get_engine():
    """
    Ожидает в .env одну из переменных:
      - DATABASE_URL (рекомендуется), пример:
        mysql+pymysql://user:pass@host:3306/dbname?charset=utf8mb4
      - или собрать вручную через отдельные поля (ниже)
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        # fallback на раздельные переменные
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "3306")
        db_name = os.getenv("DB_NAME")
        db_driver = os.getenv("DB_DRIVER", "mysql+pymysql")  # или mysql+mysqlconnector
        if not all([db_user, db_pass, db_name]):
            raise RuntimeError("Нет DATABASE_URL и не заданы DB_USER/DB_PASSWORD/DB_NAME в .env")
        db_url = f"{db_driver}://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"

    return create_engine(db_url, pool_pre_ping=True, future=True)


ENGINE = get_engine()


def get_orders_by_period_sa(sd=None, ed=None, order_type=None, engine=ENGINE):
    """
    :param sd: дата начала периода
    :param ed: дата конца периода
    :param order_type: None - все, 1 - только не розница, 2 - только розница
    """
    if not sd or not ed:
        return None

    start_date = pd.to_datetime(sd).strftime("%Y-%m-%d")
    end_date = pd.to_datetime(ed).strftime("%Y-%m-%d")

    # ВАЖНО: кусок SQL (WHERE ...) нельзя параметризовать как значение.
    # Поэтому собираем условие из фиксированных безопасных вариантов.
    where_sql = ""
    if order_type == 1:
        where_sql = "WHERE ord.client_order_type != 'Розничные продажи'"
    elif order_type == 2:
        where_sql = "WHERE ord.client_order_type = 'Розничные продажи'"

    sql = text(f"""
        SELECT
            ord.client_order_type,
            ord.client_order,
            ord.client_order_date,
            ord.sales as total_sales,
            x.dt as sales_period,
            ord.returns,
            x.cr as returns_period,
            ord.amount,
            x.dt - x.cr as amount_period,
            ord.items_amount,
            ord.service_amount,
            ord.items_quant,
            ord.unique_items,
            ord.order_duration,
            DATEDIFF(x.max_date, ord.client_order_date) + 1 AS current_order_duration
        FROM (
            SELECT
                orders_id,
                SUM(dt) as dt,
                SUM(cr) as cr,
                MAX(`date`) as max_date
            FROM sales_salesdata
            WHERE `date` BETWEEN :start_date AND :end_date
            GROUP BY orders_id
        ) x
        JOIN mv_orders as ord on ord.orders_id = x.orders_id
        {where_sql}
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"start_date": start_date, "end_date": end_date})
        rows = result.fetchall()
        cols = list(result.keys())

    return pd.DataFrame(rows, columns=cols)

## ПРИМЕР

start = '2026-02-02'
finish = '2026-02-08'
oreders_type = 1 # или 2 если розница не передаем по умолчанию None стоит

#ЗАПУСКАЕМ БЕЗ ДЖАНГО. ВАЖНО ПУТЬ УКАЗЫВАЕМ ЧЕРЕЗ . а не через /. Не ставим .py в конце. 
# Например у нас Сopy Relative Path дает  utils/test_conn.py следовательно запускаем так:
# python -m utils.test_conn 


# Исходная df из запроса
df = get_orders_by_period_sa(start,finish)

#Колонки
print(df.columns.to_list())

#Например агрегация по типу заказа

df_orders_type = df.pivot_table(
    index='client_order_type',
    values=['amount','amount_period'],
    aggfunc='sum'
    
)
print(df_orders_type)

# И ТАК ДАЛЕЕ



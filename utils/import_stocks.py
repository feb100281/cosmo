import duckdb
from conns import get_engine
import pandas as pd
import os

from dotenv import load_dotenv
from sqlalchemy import text
load_dotenv()

db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "3306")
db_name = os.getenv("DB_NAME")
db_driver = os.getenv("DB_DRIVER", "mysql+pymysql")

def duck_connection():
    con = duckdb.connect(":memory:")
    con.execute("INSTALL mysql")
    con.execute("LOAD mysql")
    con.execute(f"""
        ATTACH '
            host={os.getenv("DB_HOST", "localhost")}
            port={os.getenv("DB_PORT", "3306")}
            user={os.getenv("DB_USER")}
            password={os.getenv("DB_PASSWORD")}
            database={os.getenv("DB_NAME")}
        '
        AS mysql
        (TYPE mysql);
    """)

    return con    
    

def get_items():
    eng =  get_engine() 
    df = pd.read_sql("SELECT * FROM corporate_items",eng)
    return df

def get_file_data(file):
    with duck_connection() as con:
        con.register("items",get_items())
        df = con.execute(
            """ 
            select
            i.id as item_id,
            x.fullname,
            x.name,
            CURRENT_DATE as init_date,
            sum(available) as tot_available,
            sum(ordered) as tot_ordered,
            sum(available) + sum(ordered) as total,
            list(DISTINCT barcode || ' - ' || available::text || ' шт.') as barcode_stocks,
            list(DISTINCT barcode || ' - ' || ordered::text || ' шт.(дата поступления: '|| date_arrival ||')') as barcode_ordered,
            list(DISTINCT warehouse || ' - ' || available::text || ' шт.') as warehouse_stocks,
            list(DISTINCT warehouse || ' - ' || ordered::text || ' шт.') as warehouse_ordered
            from(
            SELECT 
            "H" as fullname,
            "N" as name,
            "L" as warehouse,
            "P" as barcode,
            COALESCE("R",'0')::bigint as available,
            COALESCE("T",'0')::bigint as ordered,
            try_strptime("V", '%d.%m.%Y')::DATE as date_arrival
            from(
            SELECT *
            FROM read_xlsx(
                ?,
                range='B3:V',
                header=false,
                all_varchar=true
            )
            where "B" is not null
            )
            ) x
            left join items i on i.fullname = x.fullname
            group by x.fullname, i.id, x.name,
            CURRENT_DATE
            ;            
            """,parameters=[file,]
        ).df()
        con.register("stocks",df)     
        
        mysql_con = get_engine()         
             
        df.to_sql('stocks_data',mysql_con,index=False,if_exists='replace')
        
        with mysql_con.begin() as conn:
            conn.execute(text("""
            INSERT IGNORE INTO corporate_items (
                fullname,
                name,
                init_date
            )
            SELECT
                fullname,
                name,
                init_date
            FROM stocks_data
            WHERE item_id IS NULL
        """))

file = '/Users/pavelustenko/Downloads/test.xlsx'  
get_file_data(file)


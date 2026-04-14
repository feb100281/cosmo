import duckdb
from duckdb import DuckDBPyConnection
import sqlite3
import pandas as pd
from pprint import pprint
import shutil

src = '/Users/pavelustenko/Desktop/Manu.db'
dst = '/Users/pavelustenko/Desktop/Manu_no_views.db'
mer_dist = '/Users/pavelustenko/Desktop/mer.db'



shutil.copy(src, dst)

#Убираем вью Comparisons из базы данных - кладет скрипт
conn = sqlite3.connect(dst)
cur = conn.cursor()
cur.execute('DROP VIEW IF EXISTS "Comparisons"')
conn.commit()
conn.close()

# подключаем утку
def get_conn():
    conn = duckdb.connect()
    conn.execute("INSTALL sqlite;")
    conn.execute("LOAD sqlite;")
    conn.execute(f"ATTACH '{dst}' AS sqlite_db (TYPE SQLITE)")
    return conn

# находим nameusage

def get_name_usage(mer_path):
    q = """ 
    select 
    t.id_agreement,
    t.project_type,
    p.name_usage
    from usage_agreements t
    left join usage_types as p on p.id = t.project_type
    """
    conn = sqlite3.connect(mer_path)
    df = pd.read_sql(q,con=conn)
    conn.close()
    return df


# находим количество и площади по каждому договору и возвращаем вьюху
def get_la_qty(conn:DuckDBPyConnection):
    
    return conn.sql(
        """ 
        select 
        t.id_agreement,
        p.id_premisType,
        count(t.id_premises) as qty,
        SUM(COALESCE(p.premis_area, 0.0)) AS r_area,
        COALESCE(la.calculated_area,0.0) as c_area
        from PremisConntact t
        left join RentPremises as p on p.id_premises = t.id_premises
        left join LeaseAgreements as la on la.id_agreement = t.id_agreement
        group by t.id_agreement, p.id_premisType,calculated_area
        """
    )

# находим даты и ставки по договорам
def get_terms(conn:DuckDBPyConnection):
    return conn.sql(
        """ 
        SELECT 
            id_agreement,
            date_start,
            date_finish,
            COALESCE(
                SUM(
                    CASE
                        WHEN incude_VAT = 0 THEN value
                        ELSE value / (100 + VAT) * 100
                    END
                ) FILTER (WHERE id_type = 5),
                0
            ) AS bap,
            COALESCE(
                SUM(
                    CASE
                        WHEN incude_VAT = 0 THEN value
                        ELSE value / (100 + VAT) * 100
                    END
                ) FILTER (WHERE id_type = 4),
                0
            ) AS ep,
            COALESCE(
                SUM(
                    CASE
                        WHEN incude_VAT = 0 THEN value
                        ELSE value / (100 + VAT) * 100
                    END
                ) FILTER (WHERE id_type = 2),
                0
            ) AS fixed_monthly,
            COALESCE(
                SUM(
                    CASE
                        WHEN incude_VAT = 0 THEN value
                        ELSE value / (100 + VAT) * 100
                    END
                ) FILTER (WHERE id_type = 6),
                0
            ) AS percent,
        LIST(DISTINCT date_accured ORDER BY date_accured) as payment_profile
        FROM sqlite_db.LeaseTerms
        WHERE id_type NOT IN (1, 3)
        GROUP BY id_agreement, date_start, date_finish
        
        """
    )
    
# находим пиды и джой финальной необработаной таблицы
def get_la(conn:DuckDBPyConnection):
    return conn.sql(
        """ 
        SELECT 
        CASE WHEN la.pid is null then la.id_agreement::bigint else la.pid::bigint end as pid,
        lt.id_agreement::bigint     as id_agreement,
        lp.id_premisType::bigint    as id_premisType,
        lp.qty::bigint              as qty,
        lp.r_area::double           as r_area,
        lp.c_area::double           as c_area,
        la.K_useful_area::double    as K_useful_area,
        la.id_contr::bigint         as id_contr,
        lt.date_start::date         as date_start,
        lt.date_finish::date        as date_finish,
        lt.payment_profile          as payment_profile,
        lt.bap::double              as bap,
        lt.ep::double               as ep,
        lt.fixed_monthly::double    as fixed_monthly,
        lt.percent::double          as percent        
        from la_terms lt
        join la_premis as lp on lp.id_agreement::bigint = lt.id_agreement::bigint
        left join LeaseAgreements as la on la.id_agreement::bigint = lt.id_agreement::bigint   
        """
    )

def finishing(conn:DuckDBPyConnection):
    return conn.sql(
        """ 
        SELECT 
            t.*,
            MIN(t.date_start) OVER (PARTITION BY t.pid) AS min_start,
            MAX(t.date_finish) OVER (PARTITION BY t.pid) AS max_finish,
            COALESCE(la.number_la ILIKE 'индек%', false) AS is_indexation,
            (COALESCE(t.bap, 0) + COALESCE(t.ep, 0)) / 12 * COALESCE(t.c_area, 0) + COALESCE(t.fixed_monthly, 0) AS map,
            CONCAT(
                COALESCE(pid.number_la, 'б/н'),
                ' от ',
                COALESCE(pid.date_la,'б/н')
               
            ) AS pid_name,
             -- COALESCE(strftime(pid.date_la::date, '%d.%m.%Y'), 'н/д') не работает 2023-11-?
            CONCAT(
                COALESCE(la.number_la, 'б/н'),
                ' от ',
                COALESCE(la.date_la,'н/д')
                
            ) AS la_name,
            -- COALESCE(strftime(la.date_la::date, '%d.%m.%Y'), 'н/д')
            cont.name_contr AS name_contr,
            pt.name_premisType,
            ut.name_usage,
            la.Comment
            
        FROM prefin t
        LEFT JOIN LeaseAgreements AS la
            ON la.id_agreement::BIGINT = t.id_agreement::BIGINT  
        LEFT JOIN LeaseAgreements AS pid
            ON pid.id_agreement::BIGINT = t.pid::BIGINT
        LEFT JOIN ContrAgents AS cont
            ON cont.id_contr::BIGINT = t.id_contr::BIGINT
        LEFT JOIN PremisType as pt on pt.id_premisType = t.id_premisType
        LEFT JOIN name_usage as ut on ut.id_agreement = t.id_agreement
        
        """
    )
    

final_colls = ['pid', 'id_agreement', 'id_premisType', 'qty', 'r_area', 'c_area',
       'K_useful_area', 'id_contr', 'date_start', 'date_finish',
       'payment_profile', 'bap', 'ep', 'fixed_monthly', 'percent', 'min_start',
       'max_finish', 'is_indexation', 'map', 'pid_name', 'la_name',
       'name_contr', 'name_premisType', 'name_usage', 'Comment']    


def agg_final(conn:DuckDBPyConnection):
    return conn.sql(
        """ 
        SELECT
        x.pid,
        x.id_agreement,
        x.pid_name,
        x.la_name,
        LIST(DISTINCT x.is_indexation) as is_indexation,
        x.name_contr,
        x.name_usage,
        LIST(DISTINCT x.Comment) as Comment,
        x.qty,
        x.r_area,
        x.c_area,
        x.id_contr,
        min(x.date_start) as date_start,
        max(x.date_finish) as date_finish,
        min(x.min_start) as min_start,
        max(x.max_finish) as max_finish,
        x.bap,
        x.ep,
        x.fixed_monthly,
        x.percent,
        x.map        
        FROM (    
        SELECT
        pid::bigint as pid,
        id_agreement::bigint as id_agreement,
        pid_name::text as pid_name,
        la_name::text as la_name,
        is_indexation,
        name_contr::text as name_contr,
        name_usage::text as name_usage,
        Comment::text as Comment,
        qty::bigint as qty,
        round(r_area,2)::double as r_area,
        round(c_area,2)::double as c_area,
        id_contr::text as id_contr,
        date_start::date as date_start,
        date_finish::date as date_finish,
        min_start::date as min_start,
        max_finish::date as max_finish,
        round(bap,2)::double as bap,
        round(ep,2)::double as ep,
        round(fixed_monthly,2)::double as fixed_monthly,
        round(percent,2)::double as percent,
        round(map,2)::double as map     
        FROM final
        ) x
        group by
        x.pid,
        x.id_agreement,
        x.pid_name,
        x.la_name,
        x.name_contr,
        x.name_usage,
        x.qty,
        x.r_area,
        x.c_area,
        x.id_contr,
        x.bap,
        x.ep,
        x.fixed_monthly,
        x.percent,
        x.map                
        """
    )
    
    
    

def main():
    conn = get_conn()
    conn = conn.execute("USE sqlite_db.main")
    # print(conn.sql("select * from LeaseTerms").df().columns)
    
    # строим базу в коннекшн из запросов
    conn.register("la_premis",get_la_qty(conn))
    conn.register("la_terms",get_terms(conn))
    conn.register("name_usage",get_name_usage(mer_dist))
    conn.register("prefin",get_la(conn))
    conn.register("final",finishing(conn))
    conn.register("agg_final",agg_final(conn))
        
    START = "2026-03-06"
    FINISH = "2026-04-11"
    
    # Пробуем сделать то что пулучится
    
    conn.sql(
    """
    select
        *,
        
        case 
            when min_start between ? and ? then 'Новый' 
            when max_finish between ? and ? then 'Завершенный'
            else 'В действии' 
        end as pid_status,
        
        case
            when date_start between ? and ? then 'Новые условия' 
            when date_finish between ? and ? then 'Завершенные условия'
            else 'В действии' 
        end as la_status
        
    from agg_final
        
    where
        date_start <= ?
        and date_finish >= ?
    """,
    params=[
        START, FINISH,
        START, FINISH,
        START, FINISH,
        START, FINISH,
        FINISH, START
    ]
).df().to_excel('try.xlsx',index=False)
    
    
    
    
    
    
    

main()
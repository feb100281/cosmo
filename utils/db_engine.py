import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pymysql
import duckdb

load_dotenv()

_ENGINE = None
_DUCK_CONN = None


def get_mysql_conn():
    """
    Всегда новый MySQL connection.
    ОБЯЗАТЕЛЬНО закрывать через mysql_conn.close()
    """
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.Cursor,
    )


def get_duckdb_conn():
    global _DUCK_CONN
    if _DUCK_CONN is not None:
        return _DUCK_CONN

    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME")

    if not all([db_user, db_pass, db_name]):
        raise RuntimeError("Не заданы DB_USER/DB_PASSWORD/DB_NAME")

    conn = duckdb.connect(database=":memory:")

    conn.execute("INSTALL mysql;")
    conn.execute("LOAD mysql;")

    conn.execute(f"""
        ATTACH 'host={db_host} user={db_user} password={db_pass} port={db_port} database={db_name}'
        AS mysql_db (TYPE MYSQL);
    """)

    _DUCK_CONN = conn
    return _DUCK_CONN


def get_engine():
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "3306")
        db_name = os.getenv("DB_NAME")
        db_driver = os.getenv("DB_DRIVER", "mysql+pymysql")

        if not all([db_user, db_pass, db_name]):
            raise RuntimeError(
                "Нет DATABASE_URL и не заданы DB_USER/DB_PASSWORD/DB_NAME"
            )

        db_url = f"{db_driver}://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"

    _ENGINE = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        future=True,
    )

    return _ENGINE
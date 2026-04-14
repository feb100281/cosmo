import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# грузим .env один раз (можно указать путь, если .env не в корне)
load_dotenv()

_ENGINE = None

def get_engine():
    """
    Возвращает singleton Engine.
    Источник:
      - DATABASE_URL (рекомендуется), пример:
        mysql+pymysql://user:pass@host:3306/dbname?charset=utf8mb4
      - или DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME (+ DB_DRIVER)
    """
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
                "Нет DATABASE_URL и не заданы DB_USER/DB_PASSWORD/DB_NAME в .env"
            )

        db_url = f"{db_driver}://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"

    _ENGINE = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        future=True,
    )
    return _ENGINE
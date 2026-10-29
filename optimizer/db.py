import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv

load_dotenv()

def connection():
    return psycopg.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "sql_optimizer"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )

@contextmanager
def get_connection():
    conn = connection()
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def execute_sql(sql: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall() if cur.description else None

import sqlite3
import pandas as pd

conn = sqlite3.connect("dataset/zomato.db")
with open("sql/queries.sql", encoding="utf-8") as f:
    queries = [q.strip() for q in f.read().split(";") if q.strip()]

for q in queries:
    print("\n" + q.splitlines()[0])
    print(pd.read_sql_query(q, conn).to_string(index=False))
conn.close()
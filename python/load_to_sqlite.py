import sqlite3
import pandas as pd

df = pd.read_csv("dataset/zomato_clean.csv")
conn = sqlite3.connect("dataset/zomato.db")
df.to_sql("restaurants", conn, if_exists="replace", index=False)
conn.close()
print("Done:", len(df), "rows loaded")
import pandas as pd

df = pd.read_csv("dataset/archive/zomato.csv", encoding="utf-8")

df = df.rename(columns={"approx_cost(for two people)": "cost_for_two"})

# "4.1/5" -> 4.1 ("NEW", "-" maathiri values NaN aagum)
df["rate"] = pd.to_numeric(df["rate"].astype(str).str.split("/").str[0], errors="coerce")
df["cost_for_two"] = pd.to_numeric(df["cost_for_two"].astype(str).str.replace(",", ""), errors="coerce")
df = df.dropna(subset=["rate", "cost_for_two"])

# Oru restaurant = oru row (adhigam votes ulla row-ah vachukkum)
df = df.sort_values("votes", ascending=False)
df = df.drop_duplicates(subset=["name", "address"], keep="first")

# Thevai illatha columns remove
df = df.drop(columns=["url", "phone", "reviews_list", "menu_item", "address",
                      "dish_liked", "listed_in(type)", "listed_in(city)"], errors="ignore")

df.to_csv("dataset/zomato_clean.csv", index=False)
print("Unique restaurants:", df.shape[0])
print(df.head())
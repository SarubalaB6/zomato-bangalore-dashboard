import os
import time
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = ["#E23744"]
px.defaults.color_continuous_scale = "Reds"

st.set_page_config(page_title="Bangalore Restaurants Dashboard", page_icon="🍽️", layout="wide")


@st.cache_data
def load_data():
    conn = sqlite3.connect("dataset/zomato.db")
    df = pd.read_sql_query("SELECT * FROM restaurants", conn)
    conn.close()
    return df


df = load_data()

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
areas = st.sidebar.multiselect("Area", sorted(df["location"].unique()))
min_rating = st.sidebar.slider("Minimum rating", 1.0, 5.0, 1.0, 0.1)
online = st.sidebar.selectbox("Online order", ["All", "Yes", "No"])
booking = st.sidebar.selectbox("Table booking", ["All", "Yes", "No"])

f = df[df["rate"] >= min_rating]
if areas:
    f = f[f["location"].isin(areas)]
if online != "All":
    f = f[f["online_order"] == online]
if booking != "All":
    f = f[f["book_table"] == booking]

# ---------- Header and KPIs ----------
st.title("🍽️ Bangalore Restaurants Dashboard")
st.caption("Zomato data, 9,478 unique restaurants")

if f.empty:
    st.warning("No restaurants match these filters.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Restaurants", f"{len(f):,}")
c2.metric("Avg rating", f"{f['rate'].mean():.2f}")
c3.metric("Avg cost for two", f"₹{f['cost_for_two'].mean():,.0f}")
c4.metric("Total votes", f"{f['votes'].sum():,}")

# ---------- Charts ----------
left, right = st.columns(2)

top_areas = f["location"].value_counts().head(10).reset_index()
top_areas.columns = ["location", "restaurants"]
fig1 = px.bar(top_areas, x="restaurants", y="location", orientation="h",
              title="Top 10 areas by number of restaurants")
fig1.update_yaxes(autorange="reversed")
left.plotly_chart(fig1)

types = (f.groupby("rest_type")
          .agg(restaurants=("name", "count"), avg_cost=("cost_for_two", "mean"))
          .reset_index()
          .sort_values("restaurants", ascending=False)
          .head(10))
fig2 = px.bar(types, x="rest_type", y="restaurants", color="avg_cost",
              title="Restaurant types (colour = average cost)")
right.plotly_chart(fig2)

left2, right2 = st.columns(2)

fig3 = px.scatter(f, x="cost_for_two", y="rate", size="votes", hover_name="name",
                  title="Cost vs rating (bubble size = votes)")
left2.plotly_chart(fig3)

right2.subheader("Top rated restaurants (500+ votes)")
top = (f[f["votes"] >= 500]
       .sort_values(["rate", "votes"], ascending=False)
       .head(10)[["name", "location", "rate", "votes"]])
right2.dataframe(top, hide_index=True)

# ---------- Cuisines and Hidden gems ----------
st.divider()
a, b = st.columns(2)

cuisine_df = f.assign(cuisine=f["cuisines"].str.split(", ")).explode("cuisine")
cuisine_stats = (cuisine_df.groupby("cuisine")
                 .agg(restaurants=("name", "count"), avg_rating=("rate", "mean"), avg_cost=("cost_for_two", "mean"))
                 .query("restaurants >= 30").round(2)
                 .sort_values("avg_rating", ascending=False).head(15))

fig4 = px.bar(cuisine_stats.head(10).reset_index(), x="avg_rating", y="cuisine", orientation="h",
              title="Top cuisines by average rating (30+ restaurants)")
fig4.update_yaxes(autorange="reversed")
a.plotly_chart(fig4)

b.subheader("💎 Hidden gems (4.0+ rating, under 500 votes)")
gems = (f[(f["rate"] >= 4.0) & (f["votes"] < 500)]
        .sort_values("rate", ascending=False)
        .head(10)[["name", "location", "rate", "votes", "cost_for_two"]])
b.dataframe(gems, hide_index=True)

# ---------- Ask your data (Gemini) ----------
st.divider()
st.subheader("🤖 Ask your data")

question = st.text_input("Ask a question about these restaurants",
                         placeholder="Which cuisine has the best ratings?")

if st.button("Ask") and question:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY not found. Check your .env file.")
    else:
        area_stats = (f.groupby("location")
                      .agg(restaurants=("name", "count"), avg_rating=("rate", "mean"), avg_cost=("cost_for_two", "mean"))
                      .query("restaurants >= 20").round(2)
                      .sort_values("avg_rating", ascending=False).head(15))
        type_stats = (f.groupby("rest_type")
                      .agg(restaurants=("name", "count"), avg_rating=("rate", "mean"), avg_cost=("cost_for_two", "mean"))
                      .query("restaurants >= 20").round(2)
                      .sort_values("restaurants", ascending=False).head(10))
        booking_stats = f.groupby("book_table").agg(avg_rating=("rate", "mean"), avg_cost=("cost_for_two", "mean")).round(2)
        online_stats = f.groupby("online_order").agg(avg_rating=("rate", "mean"), avg_cost=("cost_for_two", "mean")).round(2)
        top_names = f.sort_values(["rate", "votes"], ascending=False).head(10)[["name", "location", "rate", "votes"]]

        prompt = f"""You are a data analyst for Bangalore restaurant data.
Answer the question using ONLY the summary below. If the summary can't answer it, say so.
Keep the answer short and clear.

Total restaurants: {len(f)}
Average rating: {f['rate'].mean():.2f}
Average cost for two: {f['cost_for_two'].mean():.0f}

Best rated areas (min 20 restaurants):
{area_stats.to_string()}

Restaurant types:
{type_stats.to_string()}

Table booking:
{booking_stats.to_string()}

Online order:
{online_stats.to_string()}

Cuisines (min 30 restaurants):
{cuisine_stats.to_string()}

Top rated restaurants:
{top_names.to_string(index=False)}

Question: {question}"""

        client = genai.Client(api_key=api_key)
        answer = None
        with st.spinner("Thinking..."):
            for attempt in range(3):
                try:
                    resp = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
                    answer = resp.text
                    break
                except Exception as e:
                    if "503" in str(e) and attempt < 2:
                        time.sleep(3)
                    else:
                        st.error(f"Gemini error: {e}")
                        break
        if answer:
            st.write(answer)
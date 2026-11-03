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
cuisine_df = cuisine_df.dropna(subset=["cuisine"])
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

# ---------- Best areas to open a new restaurant ----------
st.divider()
st.subheader("🏆 Best areas to open a new restaurant")
st.caption("Areas with above-average ratings but fewer restaurants, so less competition (20+ restaurants).")

overall_rating = f["rate"].mean()
opportunity = (f.groupby("location")
               .agg(restaurants=("name", "count"), avg_rating=("rate", "mean"), avg_cost=("cost_for_two", "mean"))
               .round(2)
               .query("restaurants >= 20"))
opportunity = (opportunity[opportunity["avg_rating"] >= overall_rating]
               .sort_values("restaurants")
               .head(10)
               .reset_index())

if opportunity.empty:
    st.info("Not enough areas for this view with the current filters. Try clearing the Area filter.")
else:
    o1, o2 = st.columns(2)
    fig5 = px.bar(opportunity, x="restaurants", y="location", orientation="h",
                  color="avg_rating", title="Fewest restaurants among well-rated areas")
    fig5.update_yaxes(autorange="reversed")
    o1.plotly_chart(fig5)
    o2.dataframe(opportunity, hide_index=True)

# ---------- Restaurant recommender ----------
st.divider()
st.subheader("🎯 Restaurant recommender")

r1, r2 = st.columns(2)
cuisine_options = sorted(cuisine_df["cuisine"].unique())
chosen_cuisine = r1.selectbox("Cuisine", cuisine_options)
budget = r2.slider("Maximum cost for two (₹)", 100, 3000, 800, 50)

picks = (cuisine_df[(cuisine_df["cuisine"] == chosen_cuisine) & (cuisine_df["cost_for_two"] <= budget)]
         .sort_values(["rate", "votes"], ascending=False)
         .head(10)[["name", "location", "rate", "votes", "cost_for_two"]])

if picks.empty:
    st.info("No restaurants found. Try a higher budget or a different cuisine.")
else:
    st.dataframe(picks, hide_index=True)

    # ---------- Ask your data (Gemini) ----------
st.divider()
st.subheader("🤖 Ask your data")

question = st.text_input(
    "Ask a question about these restaurants",
    placeholder="Which cuisine has the best ratings?",
)


def summarize(data, column, min_count, top_n, sort_by):
    stats = data.groupby(column).agg(
        restaurants=("name", "count"),
        avg_rating=("rate", "mean"),
        avg_cost=("cost_for_two", "mean"),
    )
    stats = stats[stats["restaurants"] >= min_count].round(2)
    return stats.sort_values(sort_by, ascending=False).head(top_n)


if st.button("Ask") and question:
    wait_left = 15 - (time.time() - st.session_state.get("last_ask", 0))
    if wait_left > 0:
        st.info(f"Please wait {wait_left:.0f} more seconds.")
        st.stop()
    st.session_state["last_ask"] = time.time()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY not found. Check .env or Streamlit secrets.")
        st.stop()

    area_stats = summarize(f, "location", 20, 15, "avg_rating")
    type_stats = summarize(f, "rest_type", 20, 10, "restaurants")
    booking_stats = summarize(f, "book_table", 0, 5, "restaurants")
    online_stats = summarize(f, "online_order", 0, 5, "restaurants")
    top_names = f.sort_values(["rate", "votes"], ascending=False)
    top_names = top_names.head(10)[["name", "location", "rate", "votes"]]

    prompt = f"""You are a data analyst for Bangalore restaurant data.
Answer the question using ONLY the summary below.
If the summary can't answer it, say so.
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
                resp = client.models.generate_content(
                    model="gemini-3.8-flash", contents=prompt
                )
                answer = resp.text
                break
            except Exception as e:
                msg = str(e)
                if "503" in msg:
                    if attempt < 2:
                        time.sleep(3 * (attempt + 1))
                    else:
                        st.warning("The AI service is very busy. Please try again in a minute.")
                elif "429" in msg:
                    st.warning("Too many questions right now. Please wait a minute and try again.")
                    st.caption(msg[300:900])
                    break
                else:
                    st.error(f"Gemini error: {e}")
                    break
    if answer:
        st.write(answer)

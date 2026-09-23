import streamlit as st
import pandas as pd
import psycopg2
import altair as alt
import os
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

# ---------------- DASHBOARD CONFIG ----------------
st.set_page_config(
    page_title="Fraud Detection Dashboard",
    layout="wide",
    page_icon="💳"
)

# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
    color: #ffffff;
}
h1, h2, h3, .css-1d391kg { color: #ffd700; }
div[data-testid="metric-container"] {
    background-color: #1e2a38;
    border-radius: 10px;
    padding: 10px;
    color: #ffd700;
}
[data-testid="stDataFrame"] { background-color: #152836; }
thead tr th { background-color: #1e2a38 !important; color: #ffd700 !important; }
</style>
""", unsafe_allow_html=True)

st.title("💳 Real-Time Fraud Detection Dashboard (ML)")

# ---------------- AUTO REFRESH ----------------
st_autorefresh(interval=2000, key="datarefresh")  # refresh every 2 seconds

# ---------------- DATABASE FUNCTION ----------------
@st.cache_data(ttl=2)
def get_data():
    load_dotenv()

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    query = "SELECT * FROM transactions ORDER BY transaction_id DESC"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

df = get_data()

# ---------------- KPIs ----------------
total_tx = len(df)
fraud_tx = df['is_fraud'].sum()
avg_amount = df['amount'].mean()

col1, col2, col3 = st.columns(3)
col1.metric("💰 Total Transactions", total_tx)
col2.metric("🚨 Fraud Transactions", int(fraud_tx))
col3.metric("📊 Avg Amount", f"${avg_amount:.2f}")

# ---------------- CHART: Transaction Amount ----------------
st.subheader("📈 Transaction Amount Distribution")

# Create colored chart using Altair
df_chart = df.copy()
df_chart['Fraud Status'] = df_chart['is_fraud'].apply(lambda x: 'Fraud' if x else 'Normal')

amount_chart = alt.Chart(df_chart).mark_bar().encode(
    x=alt.X('amount', bin=True, title='Transaction Amount'),
    y='count()',
    color=alt.Color('Fraud Status', scale=alt.Scale(domain=['Normal', 'Fraud'], range=['#00ffcc', '#ff0033']))
).properties(height=300, width=700)



# ---------------- CHART: Transactions by Type ----------------
st.subheader("📍 Transactions by Type")

type_chart = alt.Chart(df_chart).mark_bar().encode(
    x='transaction_type',
    y='count()',
    color=alt.Color('Fraud Status', scale=alt.Scale(domain=['Normal', 'Fraud'], range=['#00ffcc', '#ff0033']))
).properties(height=300, width=700)

st.altair_chart(type_chart, use_container_width=True)
fraud_rate = (fraud_tx / total_tx) * 100 if total_tx > 0 else 0
col4 = st.columns(4)[-1]
col4.metric("⚠️ Fraud Rate", f"{fraud_rate:.2f}%")

# ---------------- TABLE ----------------
st.subheader("📋 Latest Transactions (ML Fraud Highlighted)")

def highlight_fraud(row):
    return ['background-color: #ff0033; color: white;' if row.is_fraud else 'background-color: #1b2b3b; color: #00ffcc;' for _ in row]

st.dataframe(df.style.apply(highlight_fraud, axis=1))


time_chart = df.groupby(df['created_at'].dt.floor('s')).size().reset_index(name='count')

st.subheader("⏱️ Transactions Over Time")
st.line_chart(time_chart.set_index('created_at'))
import altair as alt

pie_data = pd.DataFrame({
    'Category': ['Fraud', 'Normal'],
    'Count': [fraud_tx, total_tx - fraud_tx]
})

pie_chart = alt.Chart(pie_data).mark_arc().encode(
    theta='Count',
    color=alt.Color('Category', scale=alt.Scale(range=['#ff0033', '#00ffcc']))
)

st.subheader("🎯 Fraud vs Normal Distribution")
st.altair_chart(pie_chart)
st.caption("🔄 Refreshing every 2 seconds automatically")
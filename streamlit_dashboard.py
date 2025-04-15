import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Nico's Portfolio Dashboard", layout="wide")
st.title("📊 Nico's Live Portfolio Dashboard")

# Define your portfolio
portfolio = pd.DataFrame({
    "Type": ["Stock", "ETF", "ETF"],
    "Name": ["Palantir Technologies", "iShares Automation & Robotics", "iShares Core MSCI World"],
    "Ticker": ["PLTR", "RBOT.SW", "IWRD.SW"],
    "Currency": ["USD", "USD", "USD"],
    "Units": [2, 10, 3],
    "Buy Price": [79.72, 12.26, 120.00],
    "Target Horizon": ["1-2 years", "3-5 years", "3-5 years"]
})

# Fetch current prices and fundamental KPIs
@st.cache_data(ttl=3600)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = stock.history(period="1d")["Close"].iloc[-1]
        return pd.Series({
            "Current Price": price,
            "EPS": info.get("trailingEps", None),
            "PE Ratio": info.get("trailingPE", None),
            "Market Cap": info.get("marketCap", None),
            "PEG Ratio": info.get("pegRatio", None),
            "Beta": info.get("beta", None),
            "Free Cash Flow": info.get("freeCashflow", None),
            "Revenue Growth YoY (%)": info.get("revenueGrowth", None) * 100 if info.get("revenueGrowth") else None
        })
    except:
        return pd.Series({
            "Current Price": None,
            "EPS": None,
            "PE Ratio": None,
            "Market Cap": None,
            "PEG Ratio": None,
            "Beta": None,
            "Free Cash Flow": None,
            "Revenue Growth YoY (%)": None
        })

kpis = portfolio["Ticker"].apply(fetch_data)
portfolio = pd.concat([portfolio, kpis], axis=1)

# Calculations
portfolio["Value"] = portfolio["Units"] * portfolio["Current Price"]
portfolio["Cost Basis"] = portfolio["Units"] * portfolio["Buy Price"]
portfolio["Profit/Loss (CHF)"] = portfolio["Value"] - portfolio["Cost Basis"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

# Recommendation logic
STOP_LOSS = -15
TAKE_PROFIT = 25

def recommendation(row):
    if row["Profit/Loss (%)"] <= STOP_LOSS:
        return "❌ SELL (Stop-Loss)"
    elif row["Profit/Loss (%)"] >= TAKE_PROFIT:
        return "✅ SELL (Take-Profit)"
    elif row["PEG Ratio"] and row["PEG Ratio"] > 3:
        return "⚠️ Review – High PEG"
    elif row["Beta"] and row["Beta"] > 2:
        return "⚠️ Risky – High Volatility"
    elif row["EPS"] and row["EPS"] > 0 and row["Revenue Growth YoY (%)"] and row["Revenue Growth YoY (%)"] > 10:
        return "🟢 BUY (Growth)"
    else:
        return "HOLD"

portfolio["Recommendation"] = portfolio.apply(recommendation, axis=1)

# Styling for recommendation column
def highlight_recommendation(val):
    if "BUY" in str(val):
        return "background-color: #d1f7c4"  # green
    elif "SELL" in str(val):
        return "background-color: #f8d7da"  # red
    elif "Review" in str(val) or "Risky" in str(val):
        return "background-color: #fff3cd"  # yellow
    else:
        return ""

# Rounding for display
numeric_cols = ["Buy Price", "Current Price", "Value", "Cost Basis", "Profit/Loss (CHF)",
                "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[numeric_cols] = portfolio[numeric_cols].round(2)

# Display styled dataframe
styled_df = portfolio[[
    "Type", "Name", "Ticker", "Units", "Buy Price", "Current Price", "Value",
    "Profit/Loss (CHF)", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta",
    "Free Cash Flow", "Revenue Growth YoY (%)", "Target Horizon", "Recommendation"
]].style.applymap(highlight_recommendation, subset=["Recommendation"])

st.dataframe(styled_df, use_container_width=True)

# Portfolio summary
total_cost = portfolio["Cost Basis"].sum()
total_value = portfolio["Value"].sum()
total_pl = total_value - total_cost
total_pl_pct = (total_pl / total_cost) * 100

st.markdown("### 💰 Portfolio Summary")
st.metric(label="Total Invested", value=f"{total_cost:.2f} CHF")
st.metric(label="Current Value", value=f"{total_value:.2f} CHF")
st.metric(label="Total P/L", value=f"{total_pl:.2f} CHF ({total_pl_pct:.2f}%)")

import plotly.graph_objs as go
from datetime import datetime, timedelta

st.markdown("---")
st.markdown("### 📈 Kursentwicklung anzeigen")

# Dropdown für Ticker-Auswahl
selected_ticker = st.selectbox("Wähle eine Position aus dem Portfolio:", portfolio["Ticker"].unique())

# Kursdaten abrufen
@st.cache_data(ttl=3600)
def get_history(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="5y", interval="1d")

hist = get_history(selected_ticker)

# Plot erstellen
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=hist.index,
    y=hist["Close"],
    mode="lines",
    name="Kurs",
    line=dict(color="royalblue")
))

fig.update_layout(
    title=f"Kursentwicklung von {selected_ticker} (5 Jahre, täglich)",
    xaxis_title="Datum",
    yaxis_title="Kurs (in lokaler Währung)",
    height=500
)

st.plotly_chart(fig, use_container_width=True)
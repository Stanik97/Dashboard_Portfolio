import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
from datetime import datetime, timedelta

# Page settings
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("📊 Live Portfolio Dashboard")

# Total deposit (manuell definierbar)
total_deposit = 500.00  # CHF, manuell eingezahlt
cash = 162.07  # CHF noch auf Saxo Konto
invested = total_deposit - cash

# Define your portfolio
portfolio = pd.DataFrame({
    "Type": ["Stock", "ETF", "ETF"],
    "Name": ["Palantir Technologies", "iShares Automation & Robotics", "iShares Core MSCI World"],
    "Ticker": ["PLTR", "RBOT.SW", "IWRD.SW"],
    "Currency": ["EUR", "USD", "USD"],
    "Units": [2, 10, 1],
    "Buy Price": [79.72, 12.26, 101.30],
    "Target Horizon": ["1-2 years", "3-5 years", "3-5 years"]
})

# Get current exchange rate
@st.cache_data(ttl=300)
def get_fx_rate():
    try:
        rate = yf.Ticker("EURUSD=X").history(period="1d")["Close"].iloc[-1]
        return rate
    except:
        return 1.0

eur_usd_rate = get_fx_rate()

# Fetch current prices and KPIs
@st.cache_data(ttl=300)
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

# Umrechnung bei EUR -> USD -> CHF
portfolio["Current Price"] = portfolio.apply(
    lambda row: row["Current Price"] * eur_usd_rate if row["Currency"] == "EUR" else row["Current Price"],
    axis=1
)

portfolio["Value"] = portfolio["Units"] * portfolio["Current Price"]
portfolio["Cost Basis"] = portfolio["Units"] * portfolio["Buy Price"]
portfolio["Profit/Loss (CHF)"] = portfolio["Value"] - portfolio["Cost Basis"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

# Empfehlungen
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

# Formatierungen
portfolio = portfolio.round(2)

# Portfolio-Werte
total_value = portfolio["Value"].sum() + cash
portfolio_growth = ((total_value - total_deposit) / total_deposit) * 100

# 💰 Portfolio Summary Anzeige
st.markdown("### 💰 Portfolio Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric(label="Total Deposit", value=f"{total_deposit:.2f} CHF")
col1.caption(f"- Invested: {invested:.2f} CHF\n- Cash: {cash:.2f} CHF")
col2.metric(label="Total Value Portfolio", value=f"{total_value:.2f} CHF")
col3.metric(label="Cash (Saxo)", value=f"{cash:.2f} CHF")
col4.metric(label="Growth vs Deposit", value=f"{portfolio_growth:.2f} %")

# Tabelle
styled_df = portfolio[[
    "Type", "Name", "Ticker", "Units", "Buy Price", "Current Price", "Value",
    "Profit/Loss (CHF)", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta",
    "Free Cash Flow", "Revenue Growth YoY (%)", "Target Horizon", "Recommendation"
]].style.applymap(lambda val: "background-color: #d1f7c4" if "BUY" in str(val)
                  else "background-color: #f8d7da" if "SELL" in str(val)
                  else "background-color: #fff3cd" if "Review" in str(val) or "Risky" in str(val)
                  else "", subset=["Recommendation"])

st.dataframe(styled_df, use_container_width=True)

# 📈 Kursentwicklung
st.markdown("---")
st.markdown("### 📈 Kursentwicklung anzeigen")
selected_ticker = st.selectbox("Wähle eine Position aus dem Portfolio:", portfolio["Ticker"].unique())

@st.cache_data(ttl=3600)
def get_history(ticker):
    return yf.Ticker(ticker).history(period="5y", interval="1d")

hist = get_history(selected_ticker)
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
fig.update_layout(title=f"Kursentwicklung von {selected_ticker} (5 Jahre, täglich)",
                  xaxis_title="Datum", yaxis_title="Kurs (lokal)", height=500)
st.plotly_chart(fig, use_container_width=True)

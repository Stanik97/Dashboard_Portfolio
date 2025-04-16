import streamlit as st
import pandas as pd
import yfinance as yf

# === Exchange Rates ===
@st.cache_data(ttl=300)
def get_fx_rates():
    eur_chf = yf.Ticker("EURCHF=X").history(period="1d")["Close"].iloc[-1]
    return eur_chf

eur_chf = get_fx_rates()

# === Portfolio Definition ===
portfolio = pd.DataFrame({
    "Type": ["Stock", "ETF", "ETF"],
    "Name": ["Palantir Technologies", "iShares Automation & Robotics", "iShares Core MSCI World"],
    "Ticker": ["PLTR", "RBOT.SW", "IWRD.SW"],
    "Currency": ["EUR", "USD", "USD"],
    "Units": [2, 10, 1],
    "Buy Price": [79.72, 12.26, 101.30],
    "Target Horizon": ["1-2 years", "3-5 years", "3-5 years"]
})

cash = 162.07
total_deposit = 500.00

# === Data Fetching ===
@st.cache_data(ttl=300)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = stock.history(period="1d")["Close"].iloc[-1]
        return pd.Series({
            "Current Price Raw": price,
            "EPS": info.get("trailingEps"),
            "PE Ratio": info.get("trailingPE"),
            "PEG Ratio": info.get("pegRatio"),
            "Beta": info.get("beta"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Revenue Growth YoY (%)": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None
        })
    except:
        return pd.Series({"Current Price Raw": None, "EPS": None, "PE Ratio": None, "PEG Ratio": None, "Beta": None,
                          "Free Cash Flow": None, "Revenue Growth YoY (%)": None})

# Fetch KPIs
df_data = portfolio["Ticker"].apply(fetch_data)
portfolio = pd.concat([portfolio, df_data], axis=1)

# Convert Current Price to correct currency
def convert_price(row):
    if row["Currency"] == "EUR":
        return row["Current Price Raw"] * eur_chf
    else:
        return row["Current Price Raw"]

portfolio["Current Price"] = portfolio.apply(convert_price, axis=1)
portfolio["Value (CHF)"] = portfolio["Units"] * portfolio["Current Price"]
portfolio["Cost Basis"] = portfolio["Units"] * portfolio["Buy Price"]
portfolio["Profit/Loss"] = portfolio["Value (CHF)"] - portfolio["Cost Basis"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

# Recommendation
def recommendation(row):
    if row["Profit/Loss (%)"] <= -15:
        return "❌ SELL (Stop-Loss)"
    elif row["Profit/Loss (%)"] >= 25:
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

# === ROUNDING ===
portfolio = portfolio.round(3)

# === Portfolio Summary ===
total_value = portfolio["Value (CHF)"].sum() + cash
total_invested = total_deposit - cash
growth_pct = ((total_value - total_deposit) / total_deposit) * 100

st.markdown("### 💰 Portfolio Summary")
col1, col2, col3 = st.columns([1.5, 1.5, 1.2])
with col1:
    st.metric(label="Total Deposit", value=f"{total_deposit:.3f} CHF")
    st.markdown("<span style='font-size:14px'>• Invested: {:.2f} CHF<br>• Cash: {:.2f} CHF</span>".format(total_invested, cash), unsafe_allow_html=True)
with col2:
    st.metric(label="Total Value Portfolio", value=f"{total_value:.3f} CHF")
with col3:
    st.metric(label="Value Development", value=f"{growth_pct:.2f} %")

# === SPLIT STOCKS & ETFS ===
stocks_df = portfolio[portfolio["Type"] == "Stock"]
etfs_df = portfolio[portfolio["Type"] == "ETF"]

# === Display Tables ===
stock_columns = list(portfolio.columns)
st.markdown("### 📌 Current Positions – Stocks")
st.dataframe(stocks_df[stock_columns], use_container_width=True)

etf_columns = ["Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)",
               "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Target Horizon", "Recommendation"]
st.markdown("### 📌 Current Positions – ETFs")
st.dataframe(etfs_df[etf_columns], use_container_width=True)

# === Watchlist ===
watchlist = pd.DataFrame({
    "Name": ["Nvidia Corp", "ASML Holding", "Tesla Inc"],
    "Ticker": ["NVDA", "ASML", "TSLA"],
    "Currency": ["USD", "EUR", "USD"],
    "Type": ["Stock", "Stock", "Stock"],
    "Comment": ["High growth", "Strong EU Tech", "Volatile but strategic"]
})

watchlist_stocks = watchlist[watchlist["Type"] == "Stock"]
watchlist_etfs = watchlist[watchlist["Type"] == "ETF"]

st.markdown("### 👀 Watchlist – Stocks")
st.dataframe(watchlist_stocks.drop(columns=["Type"]), use_container_width=True)

st.markdown("### 👀 Watchlist – ETFs")
st.dataframe(watchlist_etfs.drop(columns=["Type"]), use_container_width=True)

# === Kursentwicklung ===
st.markdown("---")
st.markdown("### 📈 Kursentwicklung anzeigen")
selected_ticker = st.selectbox("Wähle eine Position aus dem Portfolio:", portfolio["Ticker"].unique())

@st.cache_data(ttl=3600)
def get_history(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="5y", interval="1d")

import plotly.graph_objs as go
hist = get_history(selected_ticker)
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
fig.update_layout(
    title=f"Kursentwicklung von {selected_ticker} (5 Jahre, täglich)",
    xaxis_title="Datum", yaxis_title="Kurs (lokale Währung)", height=500
)
st.plotly_chart(fig, use_container_width=True)

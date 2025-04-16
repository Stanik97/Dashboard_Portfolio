import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# --- Page Config ---
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("\U0001F4CA Live Portfolio Dashboard")

# --- Portfolio Data ---
portfolio = pd.DataFrame({
    "Type": ["Stock", "ETF", "ETF"],
    "Name": ["Palantir Technologies", "iShares Automation & Robotics", "iShares Core MSCI World"],
    "Ticker": ["PLTR", "RBOT.SW", "IWRD.SW"],
    "Currency": ["EUR", "USD", "USD"],
    "Units": [2, 10, 1],
    "Buy Price": [79.72, 12.26, 101.30],
    "Target Horizon": ["1-2 years", "3-5 years", "3-5 years"]
})

# --- Manual Inputs ---
cash = 162.07
fx_eur_chf = 0.93
fx_usd_chf = 0.91
total_deposit = 500.00
total_invested = total_deposit - cash

# --- Fetch Market Data ---
@st.cache_data(ttl=300)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = stock.history(period="1d")["Close"].iloc[-1]
        return pd.Series({
            "Current Price": price,
            "EPS": info.get("trailingEps"),
            "PE Ratio": info.get("trailingPE"),
            "Market Cap": info.get("marketCap"),
            "PEG Ratio": info.get("pegRatio"),
            "Beta": info.get("beta"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Revenue Growth YoY (%)": info.get("revenueGrowth") * 100 if info.get("revenueGrowth") else None
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

# --- Currency Conversion ---
def convert_to_chf(row):
    if row["Currency"] == "EUR":
        return row["Current Price"] * fx_eur_chf
    elif row["Currency"] == "USD":
        return row["Current Price"] * fx_usd_chf
    else:
        return row["Current Price"]

portfolio["Current Price (Local)"] = portfolio["Current Price"]
portfolio["Current Price"] = portfolio.apply(lambda row: row["Current Price"] if pd.notna(row["Current Price"]) else None, axis=1)
portfolio["Value (CHF)"] = portfolio["Units"] * portfolio.apply(convert_to_chf, axis=1)
portfolio["Cost Basis"] = portfolio["Units"] * portfolio["Buy Price"]
portfolio["Profit/Loss"] = portfolio["Value (CHF)"] - portfolio["Cost Basis"]
portfolio["Profit/Loss (%)"] = (portfolio["Profit/Loss"] / portfolio["Cost Basis"]) * 100

# --- Recommendation Logic ---
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

# --- Rounding ---
round_cols = ["Buy Price", "Current Price", "Current Price (Local)", "Value (CHF)", "Cost Basis", "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[round_cols] = portfolio[round_cols].round(3)

# --- Portfolio Summary ---
total_value = portfolio["Value (CHF)"].sum() + cash
growth_pct = ((total_value - total_deposit) / total_deposit) * 100

st.markdown("### 💰 Portfolio Summary")
col1, col2, col3 = st.columns([1.5, 1.5, 1.2])
with col1:
    st.metric(label="Total Deposit", value=f"{total_deposit:.3f} CHF")
    st.markdown("<p style='font-size: 0.85em;'>• Invested: {:.2f} CHF<br>• Cash: {:.2f} CHF</p>".format(total_invested, cash), unsafe_allow_html=True)
with col2:
    st.metric(label="Total Value Portfolio", value=f"{total_value:.3f} CHF")
with col3:
    st.metric(label="Value Development", value=f"{growth_pct:.2f} %")

# --- Stock Table ---
stocks = portfolio[portfolio["Type"] == "Stock"]
st.markdown("### 📌 Current Positions – Stocks")
st.dataframe(stocks, use_container_width=True)

# --- ETF Table ---
etfs = portfolio[portfolio["Type"] == "ETF"]
st.markdown("### 📌 Current Positions – ETFs")
st.dataframe(etfs[[
    "Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)", "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Target Horizon", "Recommendation"
]], use_container_width=True)

# --- Watchlist ---
st.markdown("### 👀 Watchlist")
watchlist = pd.DataFrame({
    "Name": ["Nvidia Corp", "ASML Holding", "Tesla Inc"],
    "Ticker": ["NVDA", "ASML", "TSLA"],
    "Currency": ["USD", "EUR", "USD"],
    "Comment": ["High growth", "Strong EU Tech", "Volatile but strategic"]
})
st.dataframe(watchlist, use_container_width=True)

# --- Chart ---
st.markdown("---")
st.markdown("### 📈 Kursentwicklung anzeigen")
all_tickers = pd.concat([portfolio["Ticker"], watchlist["Ticker"]]).unique()
selected_ticker = st.selectbox("Wähle eine Position aus dem Portfolio oder der Watchlist:", all_tickers)

@st.cache_data(ttl=3600)
def get_history(ticker):
    return yf.Ticker(ticker).history(period="5y", interval="1d")

hist = get_history(selected_ticker)
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
fig.update_layout(
    title=f"Kursentwicklung von {selected_ticker} (5 Jahre, täglich)",
    xaxis_title="Datum", yaxis_title="Kurs (lokal)", height=500
)
st.plotly_chart(fig, use_container_width=True)

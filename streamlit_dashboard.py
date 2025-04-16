import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# --- Konfiguration ---
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("📊 Live Portfolio Dashboard")

# --- Portfolio Daten ---
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
exchange_rate = 0.93  # EUR to CHF
usd_to_chf = 0.91

def convert_to_chf(row):
    if row["Currency"] == "EUR":
        return row["Current Price"] * row["Units"] * exchange_rate
    elif row["Currency"] == "USD":
        return row["Current Price"] * row["Units"] * usd_to_chf
    else:
        return row["Current Price"] * row["Units"]

@st.cache_data(ttl=3600)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = stock.history(period="1d")["Close"].iloc[-1]
        return pd.Series({
            "Current Price": price,
            "EPS": info.get("trailingEps"),
            "PE Ratio": info.get("trailingPE"),
            "PEG Ratio": info.get("pegRatio"),
            "Beta": info.get("beta"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Revenue Growth YoY (%)": info.get("revenueGrowth", 0) * 100
        })
    except:
        return pd.Series({
            "Current Price": None,
            "EPS": None,
            "PE Ratio": None,
            "PEG Ratio": None,
            "Beta": None,
            "Free Cash Flow": None,
            "Revenue Growth YoY (%)": None
        })

kpis = portfolio["Ticker"].apply(fetch_data)
portfolio = pd.concat([portfolio, kpis], axis=1)

portfolio["Value (CHF)"] = portfolio.apply(convert_to_chf, axis=1)
portfolio["Profit/Loss"] = portfolio["Current Price"] * portfolio["Units"] - portfolio["Buy Price"] * portfolio["Units"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

portfolio = portfolio.round(3)

# --- Empfehlungen ---
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
    elif row["EPS"] and row["EPS"] > 0 and row["Revenue Growth YoY (%)"] > 10:
        return "🟢 BUY (Growth)"
    else:
        return "HOLD"

portfolio["Recommendation"] = portfolio.apply(recommendation, axis=1)

# --- Portfolio Summary ---
total_value = portfolio["Value (CHF)"].sum() + cash
total_deposit = 500.00
total_invested = total_deposit - cash
growth_pct = ((total_value - total_deposit) / total_deposit) * 100

st.markdown("### 💰 Portfolio Summary")
col1, col2, col3 = st.columns([2, 2, 2])
with col1:
    st.metric(label="Total Deposit", value=f"{total_deposit:.3f} CHF")
    st.markdown("* Invested: {:.2f} CHF  \\n                 * Cash: {:.2f} CHF".format(total_invested, cash))
with col2:
    st.metric(label="Total Value Portfolio", value=f"{total_value:.3f} CHF")
with col3:
    st.metric(label="Value Development", value=f"{growth_pct:.2f} %")

# --- Current Positions ---
stocks_df = portfolio[portfolio["Type"] == "Stock"]
etfs_df = portfolio[portfolio["Type"] == "ETF"]

st.markdown("### 📌 Current Positions – Stocks")
st.dataframe(stocks_df.style.highlight_null(axis=None), use_container_width=True)

st.markdown("### 📌 Current Positions – ETFs")
st.dataframe(etfs_df[[
    "Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price",
    "Value (CHF)", "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Target Horizon", "Recommendation"
]], use_container_width=True)

# --- Watchlist ---
watchlist = pd.DataFrame({
    "Name": ["Nvidia Corp", "ASML Holding", "Tesla Inc", "iShares Clean Energy", "iShares Digitalisation"],
    "Ticker": ["NVDA", "ASML", "TSLA", "INRG.L", "DGTL.SW"],
    "Currency": ["USD", "EUR", "USD", "USD", "CHF"],
    "Type": ["Stock", "Stock", "Stock", "ETF", "ETF"],
    "Comment": ["High growth", "Strong EU Tech", "Volatile but strategic", "Clean energy theme", "Digital transformation"]
})

st.markdown("### 👀 Watchlist – Stocks")
watchlist_stocks = watchlist[watchlist["Type"] == "Stock"]
st.dataframe(watchlist_stocks.drop(columns="Type"), use_container_width=True)

st.markdown("### 👀 Watchlist – ETFs")
watchlist_etfs = watchlist[watchlist["Type"] == "ETF"]
st.dataframe(watchlist_etfs.drop(columns="Type"), use_container_width=True)

# --- Kursentwicklung ---
st.markdown("---")
st.markdown("### 📈 Kursentwicklung anzeigen")
all_tickers = pd.concat([portfolio["Ticker"], watchlist["Ticker"]]).unique()
selected_ticker = st.selectbox("Wähle eine Position aus Portfolio oder Watchlist:", all_tickers)

@st.cache_data(ttl=3600)
def get_history(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="5y", interval="1d")

hist = get_history(selected_ticker)
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
fig.update_layout(title=f"Kursentwicklung von {selected_ticker} (5 Jahre)", xaxis_title="Datum", yaxis_title="Kurs", height=500)
st.plotly_chart(fig, use_container_width=True)

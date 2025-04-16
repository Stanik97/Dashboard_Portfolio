import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# --- Konfiguration der Seite ---
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("\U0001F4C8 Live Portfolio Dashboard")

# --- Manuelle Werte ---
cash = 162.07
total_deposit = 500.00
total_invested = total_deposit - cash

# --- Portfolio definieren ---
data = [
    ["Stock", "Palantir Technologies", "PLTR", "EUR", 2, 79.72, "1-2 years"],
    ["ETF", "iShares Automation & Robotics", "RBOT.SW", "USD", 10, 12.26, "3-5 years"],
    ["ETF", "iShares Core MSCI World", "IWRD.SW", "USD", 1, 101.30, "3-5 years"]
]
columns = ["Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Target Horizon"]
portfolio = pd.DataFrame(data, columns=columns)

# --- Wechselkurs EUR zu USD (für PLTR) ---
@st.cache_data(ttl=300)
def get_fx_rate():
    try:
        return yf.Ticker("EURUSD=X").history(period="1d")["Close"].iloc[-1]
    except:
        return 1.0

fx_eur_usd = get_fx_rate()

# --- Daten abrufen ---
@st.cache_data(ttl=300)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = stock.history(period="1d")["Close"].iloc[-1]
        return pd.Series({
            "Raw Price": price,
            "EPS": info.get("trailingEps"),
            "PE Ratio": info.get("trailingPE"),
            "Market Cap": info.get("marketCap"),
            "PEG Ratio": info.get("pegRatio"),
            "Beta": info.get("beta"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Revenue Growth YoY (%)": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None
        })
    except:
        return pd.Series({
            "Raw Price": None,
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

# --- Preis anpassen (PLTR ist in USD, Anzeige aber in EUR) ---
def convert_price(row):
    if row["Currency"] == "EUR":
        return row["Raw Price"] * fx_eur_usd
    return row["Raw Price"]

portfolio["Current Price"] = portfolio.apply(convert_price, axis=1)
portfolio["Value"] = portfolio["Units"] * portfolio["Current Price"]
portfolio["Cost Basis"] = portfolio["Units"] * portfolio["Buy Price"]
portfolio["Profit/Loss"] = portfolio["Value"] - portfolio["Cost Basis"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

# --- Empfehlung ---
STOP_LOSS = -15
TAKE_PROFIT = 25

def recommend(row):
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

portfolio["Recommendation"] = portfolio.apply(recommend, axis=1)

# --- Runden ---
round_cols = ["Buy Price", "Current Price", "Value", "Cost Basis", "Profit/Loss", "Profit/Loss (%)",
              "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[round_cols] = portfolio[round_cols].round(3)

# --- Portfolio Summary ---
total_value = portfolio["Value"].sum() + cash
growth_pct = ((total_value - total_deposit) / total_deposit) * 100

st.markdown("### 💰 Portfolio Summary")
col1, col2, col3 = st.columns([2, 2, 2])
with col1:
    st.metric("Total Deposit", f"{total_deposit:.3f} CHF")
    st.markdown(f"- Invested: {total_invested:.2f} CHF  \n- Cash: {cash:.2f} CHF")
with col2:
    st.metric("Total Value Portfolio", f"{total_value:.3f} CHF")
with col3:
    st.metric("Value Development", f"{growth_pct:.2f} %")

# --- Aktien anzeigen ---
st.markdown("### 🖌️ Current Positions – Stocks")
stocks = portfolio[portfolio["Type"] == "Stock"]
st.dataframe(stocks[["Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value",
                    "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta",
                    "Free Cash Flow", "Revenue Growth YoY (%)", "Target Horizon", "Recommendation"]],
             use_container_width=True)

# --- ETFs anzeigen ---
st.markdown("### 🌿 Current Positions – ETFs")
etfs = portfolio[portfolio["Type"] == "ETF"]
st.dataframe(etfs[["Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value",
                   "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Beta", "Target Horizon", "Recommendation"]],
             use_container_width=True)

# --- Watchlist ---
st.markdown("### 👀 Watchlist")
watchlist = pd.DataFrame({
    "Name": ["Nvidia Corp", "ASML Holding", "Tesla Inc"],
    "Ticker": ["NVDA", "ASML", "TSLA"],
    "Currency": ["USD", "EUR", "USD"],
    "Comment": ["High growth", "Strong EU Tech", "Volatile but strategic"]
})
st.dataframe(watchlist, use_container_width=True)

# --- Kursentwicklung ---
st.markdown("### 📊 Kursentwicklung anzeigen")
ticker_options = pd.concat([portfolio["Ticker"], watchlist["Ticker"]]).unique()
selected_ticker = st.selectbox("Wähle eine Position aus:", ticker_options)

@st.cache_data(ttl=3600)
def get_history(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="5y", interval="1d")

hist = get_history(selected_ticker)
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
fig.update_layout(title=f"Kursentwicklung von {selected_ticker} (5 Jahre, täglich)",
                  xaxis_title="Datum", yaxis_title="Kurs (lokale Währung)", height=500)
st.plotly_chart(fig, use_container_width=True)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# Page config
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("📊 Live Portfolio Dashboard")

# --- Portfolio Definition ---
portfolio = pd.DataFrame({
    "Type": ["Stock", "ETF", "ETF"],
    "Name": ["Palantir Technologies", "iShares Automation & Robotics", "iShares Core MSCI World"],
    "Ticker": ["PLTR", "RBOT.SW", "IWRD.SW"],
    "Currency": ["EUR", "USD", "USD"],
    "Units": [2, 10, 1],
    "Buy Price": [79.72, 12.26, 101.30],
    "Target Horizon": ["1-2 years", "3-5 years", "3-5 years"]
})

# --- Manuelle Eingaben ---
cash = 162.07
fx_rates = {"EUR": 0.93, "USD": 0.91}  # Wechselkurse nach CHF (manuell oder via API aktualisieren)
total_deposit = 500.00
total_invested = total_deposit - cash

# --- Kursdaten abrufen ---
@st.cache_data(ttl=600)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = stock.history(period="1d")['Close'].iloc[-1]
        return pd.Series({
            "Current Price": price,
            "EPS": info.get("trailingEps"),
            "PE Ratio": info.get("trailingPE"),
            "PEG Ratio": info.get("pegRatio"),
            "Beta": info.get("beta"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Revenue Growth YoY (%)": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None
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

portfolio = pd.concat([portfolio, portfolio["Ticker"].apply(fetch_data)], axis=1)

# --- Berechnungen ---
portfolio["Value (CHF)"] = portfolio.apply(lambda x: x["Units"] * x["Current Price"] / fx_rates.get(x["Currency"], 1), axis=1)
portfolio["Cost Basis"] = portfolio["Units"] * portfolio["Buy Price"]
portfolio["Profit/Loss"] = portfolio["Value (CHF)"] - portfolio["Cost Basis"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

# --- Empfehlung ---
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

# --- Runden ---
round_cols = ["Buy Price", "Current Price", "Value (CHF)", "Cost Basis", "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[round_cols] = portfolio[round_cols].round(3)

# --- Portfolio Summary ---
total_value = portfolio["Value (CHF)"].sum() + cash
growth_pct = ((total_value - total_deposit) / total_deposit) * 100

st.markdown("### 💰 Portfolio Summary")
st.markdown("<style>div[data-testid=\"column\"]{align-items:start !important;}</style>", unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Deposit", f"{total_deposit:.3f} CHF")
    st.markdown(f"- Invested: {total_invested:.2f} CHF  ")
    st.markdown(f"- Cash: {cash:.2f} CHF")
with col2:
    st.metric("Total Value Portfolio", f"{total_value:.3f} CHF")
with col3:
    st.metric("Value Development", f"{growth_pct:.2f} %")

# --- Tabellen getrennt anzeigen ---
st.markdown("### 📌 Current Positions – Stocks")
stocks = portfolio[portfolio["Type"] == "Stock"]
st.dataframe(stocks.style.highlight_null(axis=None), use_container_width=True)

st.markdown("### 📌 Current Positions – ETFs")
etfs = portfolio[portfolio["Type"] == "ETF"]
st.dataframe(etfs[[
    "Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)",
    "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Target Horizon", "Recommendation"
]].style.highlight_null(axis=None), use_container_width=True)

# --- Watchlist ---
st.markdown("### 👀 Watchlist")
watchlist = pd.DataFrame({
    "Name": ["Nvidia Corp", "ASML Holding", "Tesla Inc"],
    "Ticker": ["NVDA", "ASML", "TSLA"],
    "Currency": ["USD", "EUR", "USD"],
    "Comment": ["High growth", "Strong EU Tech", "Volatile but strategic"]
})
st.dataframe(watchlist, use_container_width=True)

# --- Historische Kursentwicklung ---
st.markdown("### 📈 Kursentwicklung anzeigen")
selected_ticker = st.selectbox("Wähle eine Position aus dem Portfolio:", portfolio["Ticker"].tolist() + watchlist["Ticker"].tolist())

@st.cache_data(ttl=3600)
def get_history(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="5y", interval="1d")

hist = get_history(selected_ticker)
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
fig.update_layout(title=f"Kursentwicklung von {selected_ticker} (5 Jahre, täglich)", xaxis_title="Datum", yaxis_title="Kurs (lokal)", height=500)
st.plotly_chart(fig, use_container_width=True)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# Page config
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("\U0001F4C8 Live Portfolio Dashboard")

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

# Cash und Deposit
cash = 162.07
total_deposit = 500.00
total_invested = total_deposit - cash

# --- Wechselkurse ---
@st.cache_data(ttl=300)
def get_fx_rates():
    eur_chf = yf.Ticker("EURCHF=X").history(period="1d")["Close"].iloc[-1]
    usd_chf = yf.Ticker("USDCHF=X").history(period="1d")["Close"].iloc[-1]
    return eur_chf, usd_chf

eur_chf, usd_chf = get_fx_rates()

# --- Datenabruf ---
@st.cache_data(ttl=300)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = stock.history(period="1d")["Close"].iloc[-1]
        return pd.Series({
            "Current Price Raw": price,
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
            "Current Price Raw": None,
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

# --- Währungslogik ---
def convert_price(row):
    if row["Currency"] == "EUR":
        return row["Current Price Raw"] * eur_chf
    elif row["Currency"] == "USD":
        return row["Current Price Raw"] * usd_chf
    return row["Current Price Raw"]

portfolio["Current Price"] = portfolio.apply(lambda row: row["Current Price Raw"], axis=1)
portfolio["Value (CHF)"] = portfolio.apply(lambda row: row["Units"] * convert_price(row), axis=1)
portfolio["Cost Basis"] = portfolio["Units"] * portfolio["Buy Price"]
portfolio["Profit/Loss"] = portfolio["Value (CHF)"] - portfolio["Cost Basis"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

# Empfehlung
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
        return "\U0001F7E2 BUY (Growth)"
    else:
        return "HOLD"

portfolio["Recommendation"] = portfolio.apply(recommendation, axis=1)

# Runden aller Werte auf 3 Kommastellen
round_cols = ["Buy Price", "Current Price", "Value (CHF)", "Cost Basis", "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[round_cols] = portfolio[round_cols].round(3)

# --- Portfolio Summary ---
total_value = portfolio["Value (CHF)"].sum() + cash
growth_pct = ((total_value - total_deposit) / total_deposit) * 100

st.markdown("### 💰 Portfolio Summary")
col1, col2, col3 = st.columns([1.2, 1, 1])
with col1:
    st.metric(label="Total Deposit", value=f"{total_deposit:.3f} CHF")
    st.markdown("<div style='font-size: 14px;'>• Invested: {:.2f} CHF<br>• Cash: {:.2f} CHF</div>".format(total_invested, cash), unsafe_allow_html=True)
with col2:
    st.metric(label="Total Value Portfolio", value=f"{total_value:.3f} CHF")
with col3:
    st.metric(label="Value Development", value=f"{growth_pct:.2f} %")

# --- Tabellen nach Typ trennen ---
stocks_df = portfolio[portfolio["Type"] == "Stock"]
etfs_df = portfolio[portfolio["Type"] == "ETF"]

st.markdown("### 📌 Current Positions – Stocks")
st.dataframe(stocks_df.style.highlight_null(axis=None), use_container_width=True)

st.markdown("### 📌 Current Positions – ETFs")
st.dataframe(etfs_df[["Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)", "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Target Horizon", "Recommendation"]].style.highlight_null(axis=None), use_container_width=True)

# --- Watchlist ---
st.markdown("### 👀 Watchlist – Stocks")
watchlist_stocks = pd.DataFrame({
    "Name": ["Nvidia Corp", "Tesla Inc"],
    "Ticker": ["NVDA", "TSLA"],
    "Currency": ["USD", "USD"],
    "Comment": ["High growth", "Volatile but strategic"]
})
st.dataframe(watchlist_stocks, use_container_width=True)

st.markdown("### 👀 Watchlist – ETFs")
watchlist_etfs = pd.DataFrame({
    "Name": ["iShares S&P 500 UCITS ETF", "Xtrackers MSCI EM"],
    "Ticker": ["IUSA.L", "XMME.DE"],
    "Currency": ["USD", "EUR"],
    "Comment": ["US Market Exposure", "Emerging Markets"]
})
st.dataframe(watchlist_etfs, use_container_width=True)

# --- Kursentwicklung ---
st.markdown("---")
st.markdown("### 📈 Kursentwicklung anzeigen")
all_tickers = pd.concat([portfolio["Ticker"], watchlist_stocks["Ticker"], watchlist_etfs["Ticker"]])
selected_ticker = st.selectbox("Wähle eine Position aus dem Portfolio oder der Watchlist:", all_tickers.unique())

@st.cache_data(ttl=3600)
def get_history(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="5y", interval="1d")

hist = get_history(selected_ticker)
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
fig.update_layout(
    title=f"Kursentwicklung von {selected_ticker} (5 Jahre, täglich)",
    xaxis_title="Datum", yaxis_title="Kurs (in lokaler Währung)", height=500
)
st.plotly_chart(fig, use_container_width=True)
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from tradingview_ta import TA_Handler, Interval, Exchange

# Page config
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("📊 Live Portfolio Dashboard (mit TradingView Kurs)")

# --- Input Data ---
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
total_invested = total_deposit - cash

# --- Currency Conversion ---
@st.cache_data(ttl=300)
def get_fx_rates():
    eur_chf = yf.Ticker("EURCHF=X").history(period="1d")["Close"].iloc[-1]
    usd_chf = yf.Ticker("USDCHF=X").history(period="1d")["Close"].iloc[-1]
    usd_eur = yf.Ticker("USDEUR=X").history(period="1d")["Close"].iloc[-1]
    return eur_chf, usd_chf, usd_eur

eur_chf, usd_chf, usd_eur = get_fx_rates()

# --- TradingView Price Fetch ---
def get_tradingview_price(symbol):
    try:
        handler = TA_Handler(
            symbol=symbol,
            exchange="NASDAQ",
            screener="america",
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = handler.get_analysis()
        return analysis.indicators["close"]
    except:
        return None

# --- KPI Fetch ---
@st.cache_data(ttl=300)
def fetch_kpis(ticker, currency):
    try:
        if ticker == "PLTR":
            price_usd = get_tradingview_price("PLTR")
            if currency == "EUR":
                price = price_usd * usd_eur
            else:
                price = price_usd
        else:
            stock = yf.Ticker(ticker)
            price = stock.history(period="1d")["Close"].iloc[-1]
            info = stock.info
            return pd.Series({
                "Raw Price": price,
                "EPS": info.get("trailingEps"),
                "PE Ratio": info.get("trailingPE"),
                "Market Cap": info.get("marketCap"),
                "PEG Ratio": info.get("pegRatio"),
                "Beta": info.get("beta"),
                "Free Cash Flow": info.get("freeCashflow"),
                "Revenue Growth YoY (%)": info.get("revenueGrowth") * 100 if info.get("revenueGrowth") else None
            })

        stock = yf.Ticker("PLTR")  # nur für KPIs
        info = stock.info
        return pd.Series({
            "Raw Price": price,
            "EPS": info.get("trailingEps"),
            "PE Ratio": info.get("trailingPE"),
            "Market Cap": info.get("marketCap"),
            "PEG Ratio": info.get("pegRatio"),
            "Beta": info.get("beta"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Revenue Growth YoY (%)": info.get("revenueGrowth") * 100 if info.get("revenueGrowth") else None
        })

    except:
        return pd.Series({col: None for col in [
            "Raw Price", "EPS", "PE Ratio", "Market Cap", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"
        ]})

# --- Daten abrufen ---
kpis = portfolio.apply(lambda row: fetch_kpis(row["Ticker"], row["Currency"]), axis=1)
portfolio = pd.concat([portfolio, kpis], axis=1)

# --- Preis-Umrechnung und Kennzahlen ---
portfolio["Current Price"] = portfolio["Raw Price"]

def convert_to_chf(row):
    if row["Currency"] == "USD":
        return row["Current Price"] * usd_chf
    elif row["Currency"] == "EUR":
        return row["Current Price"] * eur_chf
    return row["Current Price"]

portfolio["Value (CHF)"] = portfolio.apply(lambda row: convert_to_chf(row) * row["Units"], axis=1)
portfolio["Cost Basis"] = portfolio["Buy Price"] * portfolio["Units"]
portfolio["Profit/Loss"] = (portfolio["Current Price"] - portfolio["Buy Price"]) * portfolio["Units"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

# Empfehlung
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

# Rundung
round_cols = ["Buy Price", "Current Price", "Value (CHF)", "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio",
              "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[round_cols] = portfolio[round_cols].round(3)

# Summary
total_value_chf = portfolio["Value (CHF)"].sum() + cash
growth_pct = ((total_value_chf - total_deposit) / total_deposit) * 100

st.markdown("### 💰 Portfolio Summary")
col1, col2, col3, col4 = st.columns([1.2, 1, 0.5, 1])
with col1:
    st.metric("Total Deposit", f"{total_deposit:.3f} CHF")
    st.markdown(f"<div style='margin-top: -15px; font-size: 0.9em;'>• Invested: {total_invested:.2f} CHF<br>• Cash: {cash:.2f} CHF</div>", unsafe_allow_html=True)
with col2:
    st.metric("Total Value Portfolio", f"{total_value_chf:.3f} CHF")
with col4:
    st.metric("Value Development", f"{growth_pct:.2f} %")

# Tabellen
stocks_df = portfolio[portfolio["Type"] == "Stock"]
etfs_df = portfolio[portfolio["Type"] == "ETF"]

st.markdown("### 📌 Current Positions – Stocks")
st.dataframe(stocks_df[[col for col in portfolio.columns if col != "Raw Price"]], use_container_width=True)

st.markdown("### 📌 Current Positions – ETFs")
etf_cols = ["Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)",
            "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Target Horizon", "Recommendation"]
st.dataframe(etfs_df[etf_cols], use_container_width=True)

# Watchlist
watchlist = pd.DataFrame({
    "Name": ["Nvidia Corp", "ASML Holding", "Tesla Inc"],
    "Ticker": ["NVDA", "ASML", "TSLA"],
    "Currency": ["USD", "EUR", "USD"],
    "Comment": ["High growth", "Strong EU Tech", "Volatile but strategic"],
    "Type": ["Stock", "Stock", "Stock"]
})
st.markdown("### 👀 Watchlist – Stocks")
st.dataframe(watchlist[watchlist["Type"] == "Stock"], use_container_width=True)
st.markdown("### 👀 Watchlist – ETFs")
st.dataframe(watchlist[watchlist["Type"] == "ETF"], use_container_width=True)

# Kursentwicklung
st.markdown("---")
st.markdown("### 📈 Kursentwicklung anzeigen")
all_tickers = pd.concat([portfolio[["Name", "Ticker"]], watchlist[["Name", "Ticker"]]])
selected_name = st.selectbox("Wähle eine Position aus dem Portfolio oder Watchlist:", all_tickers["Name"])
selected_ticker = all_tickers[all_tickers["Name"] == selected_name]["Ticker"].values[0]

@st.cache_data(ttl=3600)
def get_history(ticker):
    return yf.Ticker(ticker).history(period="5y", interval="1d")

hist = get_history(selected_ticker)
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
fig.update_layout(title=f"Kursentwicklung von {selected_ticker} (5 Jahre, täglich)",
                  xaxis_title="Datum", yaxis_title="Kurs", height=500)
st.plotly_chart(fig, use_container_width=True)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# Page config
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("\U0001F4CA Live Portfolio Dashboard")

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

# --- Cash und Total Deposit ---
cash = 162.07
total_deposit = 500.00
total_invested = total_deposit - cash

# --- Wechselkurse ---
@st.cache_data(ttl=300)
def get_fx():
    fx = {}
    fx["EUR"] = yf.Ticker("EURCHF=X").history(period="1d")["Close"].iloc[-1]
    fx["USD"] = yf.Ticker("USDCHF=X").history(period="1d")["Close"].iloc[-1]
    return fx

fx_rates = get_fx()

# --- Kurs- & KPI-Abruf ---
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
            "Revenue Growth YoY (%)": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None
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

# --- Berechnung ---
portfolio["Cost Basis"] = portfolio["Units"] * portfolio["Buy Price"]
portfolio["Profit/Loss"] = (portfolio["Current Price"] - portfolio["Buy Price"]) * portfolio["Units"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

# --- CHF-Wertberechnung ---
def calc_chf(row):
    if pd.isna(row["Current Price"]):
        return None
    return row["Current Price"] * row["Units"] * fx_rates.get(row["Currency"], 1)

portfolio["Value (CHF)"] = portfolio.apply(calc_chf, axis=1)

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
round_cols = ["Buy Price", "Current Price", "Value (CHF)", "Cost Basis", "Profit/Loss", "Profit/Loss (%)",
              "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[round_cols] = portfolio[round_cols].round(3)

# --- Portfolio Summary ---
total_value = portfolio["Value (CHF)"].sum() + cash
growth_pct = ((total_value - total_deposit) / total_deposit) * 100

st.markdown("### \U0001F4B0 Portfolio Summary")
col1, col2, col3 = st.columns([1.5, 1.5, 1])
with col1:
    st.metric(label="Total Deposit", value=f"{total_deposit:.3f} CHF")
    st.markdown(f"- Invested: {total_invested:.2f} CHF  \n- Cash: {cash:.2f} CHF")
with col2:
    st.metric(label="Total Value Portfolio", value=f"{total_value:.3f} CHF")
with col3:
    st.metric(label="Value Development", value=f"{growth_pct:.2f} %")

# --- Auftrennung in Stocks / ETFs ---
stocks = portfolio[portfolio["Type"] == "Stock"]
etfs = portfolio[portfolio["Type"] == "ETF"]

# --- Tabellenanzeige ---
st.markdown("### \U0001F4CC Current Positions – Stocks")
stocks_df = stocks[[
    "Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)",
    "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow",
    "Revenue Growth YoY (%)", "Target Horizon", "Recommendation"]]
st.dataframe(stocks_df, use_container_width=True)

st.markdown("### \U0001F4CC Current Positions – ETFs")
etfs_df = etfs[[
    "Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)",
    "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Target Horizon", "Recommendation"]]
st.dataframe(etfs_df, use_container_width=True)

# --- Watchlist ---
watchlist = pd.DataFrame({
    "Name": ["Nvidia Corp", "ASML Holding", "Tesla Inc"],
    "Ticker": ["NVDA", "ASML", "TSLA"],
    "Currency": ["USD", "EUR", "USD"],
    "Type": ["Stock", "Stock", "Stock"],
    "Comment": ["High growth", "Strong EU Tech", "Volatile but strategic"]
})

watch_stocks = watchlist[watchlist["Type"] == "Stock"]
watch_etfs = watchlist[watchlist["Type"] == "ETF"]

st.markdown("### \U0001F440 Watchlist – Stocks")
st.dataframe(watch_stocks.drop(columns=["Type"]), use_container_width=True)

st.markdown("### \U0001F440 Watchlist – ETFs")
st.dataframe(watch_etfs.drop(columns=["Type"]), use_container_width=True)

# --- Kursentwicklung ---
st.markdown("---")
st.markdown("### \U0001F4C8 Kursentwicklung anzeigen")
all_tickers = pd.concat([portfolio["Ticker"], watchlist["Ticker"]]).unique()
selected_ticker = st.selectbox("Wähle eine Position aus dem Portfolio oder Watchlist:", all_tickers)

@st.cache_data(ttl=3600)
def get_history(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="5y", interval="1d")

hist = get_history(selected_ticker)
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
fig.update_layout(title=f"Kursentwicklung von {selected_ticker} (5 Jahre, täglich)",
                  xaxis_title="Datum", yaxis_title="Kurs (in lokaler Währung)", height=500)
st.plotly_chart(fig, use_container_width=True)

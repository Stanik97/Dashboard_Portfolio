import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# Page config
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("📊 Live Portfolio Dashboard (PLTR in USD – held in EUR)")

# --- Input Data ---
portfolio = pd.DataFrame({
    "Type": ["Stock", "ETF", "ETF"],
    "Name": ["Palantir Technologies", "iShares Automation & Robotics", "iShares Core MSCI World"],
    "Ticker": ["PLTR", "RBOT.SW", "IWRD.SW"],
    "Currency": ["USD", "USD", "USD"],  # Alles auf USD – auch PLTR
    "Held In": ["EUR", "USD", "USD"],  # Nur Info
    "Units": [2, 10, 1],
    "Buy Price": [79.72, 12.26, 101.30],  # in USD
    "Target Horizon": ["1-2 years", "3-5 years", "3-5 years"]
})

cash = 162.07
total_deposit = 500.00
total_invested = total_deposit - cash

# --- Currency Conversion ---
@st.cache_data(ttl=300)
def get_fx_rates():
    usd_chf = yf.Ticker("USDCHF=X").history(period="1d")["Close"].iloc[-1]
    return usd_chf

usd_chf = get_fx_rates()

# --- KPI Fetch ---
@st.cache_data(ttl=300)
def fetch_kpis(ticker):
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
            "Revenue Growth YoY (%)": info.get("revenueGrowth") * 100 if info.get("revenueGrowth") else None
        })
    except:
        return pd.Series({col: None for col in ["Raw Price", "EPS", "PE Ratio", "Market Cap", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]})

kpis = portfolio["Ticker"].apply(fetch_kpis)
portfolio = pd.concat([portfolio, kpis], axis=1)

# --- Preis und CHF-Berechnung ---
portfolio["Current Price"] = portfolio["Raw Price"]
portfolio["Value (CHF)"] = portfolio["Current Price"] * portfolio["Units"] * usd_chf
portfolio["Cost Basis"] = portfolio["Buy Price"] * portfolio["Units"]
portfolio["Profit/Loss"] = (portfolio["Current Price"] - portfolio["Buy Price"]) * portfolio["Units"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

# --- Empfehlung ---
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

# --- Rundung ---
round_cols = ["Buy Price", "Current Price", "Value (CHF)", "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio",
              "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[round_cols] = portfolio[round_cols].round(3)

# --- Portfolio Summary ---
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

# --- Hinweis bei PLTR
if "PLTR" in portfolio["Ticker"].values:
    st.info("📌 Hinweis: Die Position Palantir wird in USD abgebildet, obwohl sie bei Saxo in EUR gehalten wird. Die CHF-Bewertung ist dennoch korrekt.")

# --- Positionen aufteilen ---
stocks_df = portfolio[portfolio["Type"] == "Stock"]
etfs_df = portfolio[portfolio["Type"] == "ETF"]

st.markdown("### 📌 Current Positions – Stocks")
st.dataframe(stocks_df[[col for col in portfolio.columns if col != "Raw Price"]], use_container_width=True)

st.markdown("### 📌 Current Positions – ETFs")
etf_cols = ["Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)",
            "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Target Horizon", "Recommendation"]
st.dataframe(etfs_df[etf_cols], use_container_width=True)

# --- Watchlist
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

# --- Kursentwicklung
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

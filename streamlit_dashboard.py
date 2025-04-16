import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# --- Konfiguration ---
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("📊 Live Portfolio Dashboard")

# --- Eingabedaten ---
portfolio_data = pd.DataFrame({
    "Type": ["Stock", "ETF", "ETF"],
    "Name": ["Palantir Technologies", "iShares Automation & Robotics", "iShares Core MSCI World"],
    "Ticker": ["PLTR", "RBOT.SW", "IWRD.SW"],
    "Currency": ["EUR", "USD", "USD"],
    "Units": [2, 10, 1],
    "Buy Price": [79.72, 12.26, 101.30],
    "Target Horizon": ["1-2 years", "3-5 years", "3-5 years"]
})

# --- Konstante Werte ---
cash = 162.07
chf_to_usd = yf.Ticker("CHFUSD=X").history(period="1d")["Close"].iloc[-1]
usd_to_chf = 1 / chf_to_usd
chf_to_eur = yf.Ticker("CHFEUR=X").history(period="1d")["Close"].iloc[-1]
eur_to_chf = 1 / chf_to_eur
total_deposit = 500.00
total_invested = total_deposit - cash

# --- Kurs- & Fundamentaldatenabruf ---
def fetch_data(ticker, currency):
    stock = yf.Ticker(ticker)
    info = stock.info
    price = stock.history(period="1d")["Close"].iloc[-1]
    if currency == "EUR":
        price_chf = price * eur_to_chf
    elif currency == "USD":
        price_chf = price * usd_to_chf
    else:
        price_chf = price
    return pd.Series({
        "Current Price": price,
        "Price (CHF)": price_chf,
        "EPS": info.get("trailingEps"),
        "PE Ratio": info.get("trailingPE"),
        "Market Cap": info.get("marketCap"),
        "PEG Ratio": info.get("pegRatio"),
        "Beta": info.get("beta"),
        "Free Cash Flow": info.get("freeCashflow"),
        "Revenue Growth YoY (%)": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None
    })

# --- Daten verarbeiten ---
portfolio = portfolio_data.copy()
all_kpis = portfolio.apply(lambda row: fetch_data(row["Ticker"], row["Currency"]), axis=1)
portfolio = pd.concat([portfolio, all_kpis], axis=1)

portfolio["Value (CHF)"] = portfolio["Units"] * portfolio["Price (CHF)"]
portfolio["Profit/Loss"] = portfolio["Value (CHF)"] - (portfolio["Units"] * portfolio["Buy Price"])
portfolio["Profit/Loss (%)"] = ((portfolio["Price (CHF)"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

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
    elif row["EPS"] and row["EPS"] > 0 and row["Revenue Growth YoY (%)"] and row["Revenue Growth YoY (%)"] > 10:
        return "🟢 BUY (Growth)"
    else:
        return "HOLD"

portfolio["Recommendation"] = portfolio.apply(recommendation, axis=1)

# --- Runden ---
round_cols = ["Buy Price", "Current Price", "Price (CHF)", "Value (CHF)", "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[round_cols] = portfolio[round_cols].round(3)

# --- Portfolio Summary ---
total_value = portfolio["Value (CHF)"].sum() + cash
growth_pct = ((total_value - total_deposit) / total_deposit) * 100

st.markdown("### 💰 Portfolio Summary")
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    st.metric(label="Total Deposit", value=f"{total_deposit:.3f} CHF")
    st.markdown(f"- Invested: {total_invested:.2f} CHF  \n- Cash: {cash:.2f} CHF")
with col2:
    st.metric(label="Total Value Portfolio", value=f"{total_value:.3f} CHF")
with col3:
    st.metric(label="Value Development", value=f"{growth_pct:.2f} %")

# --- Aufteilung in Stocks & ETFs ---
stocks_df = portfolio[portfolio["Type"] == "Stock"]
etfs_df = portfolio[portfolio["Type"] == "ETF"]

# --- Current Positions: Stocks ---
st.markdown("### 📌 Current Positions – Stocks")
st.dataframe(
    stocks_df[["Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)", "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)", "Target Horizon", "Recommendation"]],
    use_container_width=True
)

# --- Current Positions: ETFs ---
st.markdown("### 📌 Current Positions – ETFs")
st.dataframe(
    etfs_df[["Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)", "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Target Horizon", "Recommendation"]],
    use_container_width=True
)

# --- Watchlist (getrennt) ---
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
    "Name": ["iShares Global Clean Energy"],
    "Ticker": ["INRG.L"],
    "Currency": ["USD"],
    "Comment": ["Clean energy thematic"]
})
st.dataframe(watchlist_etfs, use_container_width=True)

# --- Kursentwicklung ---
st.markdown("---")
st.markdown("### 📈 Kursentwicklung anzeigen")
selected_ticker = st.selectbox("Wähle eine Position (Ticker):", portfolio["Ticker"].tolist() + watchlist_stocks["Ticker"].tolist() + watchlist_etfs["Ticker"].tolist())

@st.cache_data(ttl=3600)
def get_history(ticker):
    return yf.Ticker(ticker).history(period="5y", interval="1d")

hist = get_history(selected_ticker)
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
fig.update_layout(title=f"Kursentwicklung von {selected_ticker} (5 Jahre)", xaxis_title="Datum", yaxis_title="Kurs (lokale Währung)", height=500)
st.plotly_chart(fig, use_container_width=True)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# -------------------- Konfiguration --------------------
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("\U0001F4C8 Live Portfolio Dashboard")

# -------------------- Portfolio-Daten --------------------
portfolio = pd.DataFrame({
    "Type": ["Stock", "ETF", "ETF"],
    "Name": ["Palantir Technologies", "iShares Automation & Robotics", "iShares Core MSCI World"],
    "Ticker": ["PLTR", "RBOT.SW", "IWRD.SW"],
    "Currency": ["EUR", "USD", "USD"],
    "Units": [2, 10, 1],
    "Buy Price": [79.72, 12.26, 101.30],
    "Target Horizon": ["1-2 years", "3-5 years", "3-5 years"]
})

# -------------------- Finanzdaten abrufen --------------------
@st.cache_data(ttl=300)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]
        info = stock.info
        return pd.Series({
            "Current Price": price,
            "EPS": info.get("trailingEps"),
            "PE Ratio": info.get("trailingPE"),
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
            "PEG Ratio": None,
            "Beta": None,
            "Free Cash Flow": None,
            "Revenue Growth YoY (%)": None
        })

kpis = portfolio["Ticker"].apply(fetch_data)
portfolio = pd.concat([portfolio, kpis], axis=1)

# -------------------- Wechselkurs für CHF --------------------
@st.cache_data(ttl=300)
def get_fx_rates():
    eur_chf = yf.Ticker("EURCHF=X").history(period="1d")["Close"].iloc[-1]
    usd_chf = yf.Ticker("USDCHF=X").history(period="1d")["Close"].iloc[-1]
    return eur_chf, usd_chf

eur_chf, usd_chf = get_fx_rates()

# -------------------- Preise umrechnen und Berechnungen --------------------
def convert_to_chf(row):
    if pd.isna(row["Current Price"]):
        return None
    if row["Currency"] == "EUR":
        return row["Current Price"] * eur_chf
    elif row["Currency"] == "USD":
        return row["Current Price"] * usd_chf
    return row["Current Price"]

portfolio["Value (CHF)"] = portfolio["Units"] * portfolio.apply(convert_to_chf, axis=1)
portfolio["Value"] = portfolio["Units"] * portfolio["Current Price"]
portfolio["Cost Basis"] = portfolio["Units"] * portfolio["Buy Price"]
portfolio["Profit/Loss"] = portfolio["Value"] - portfolio["Cost Basis"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

# -------------------- Empfehlungen --------------------
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

# -------------------- Formatierung --------------------
cols_to_round = ["Buy Price", "Current Price", "Value", "Value (CHF)", "Cost Basis", "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[cols_to_round] = portfolio[cols_to_round].round(3)

# -------------------- Portfolio Summary --------------------
cash = 162.07
total_deposit = 500.00
total_value_chf = portfolio["Value (CHF)"].sum() + cash
total_invested = total_deposit - cash
growth_pct = ((total_value_chf - total_deposit) / total_deposit) * 100

st.markdown("### 💰 Portfolio Summary")
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    st.metric(label="Total Deposit", value=f"{total_deposit:.3f} CHF")
    st.markdown("- Invested: {:.2f} CHF  \n- Cash: {:.2f} CHF".format(total_invested, cash))
with col2:
    st.metric(label="Total Value Portfolio", value=f"{total_value_chf:.3f} CHF")
with col3:
    st.metric(label="Value Development", value=f"{growth_pct:.2f} %")

# -------------------- Tabellen getrennt darstellen --------------------
stocks = portfolio[portfolio["Type"] == "Stock"]
etfs = portfolio[portfolio["Type"] == "ETF"]

st.markdown("### 📌 Current Positions – Stocks")
st.dataframe(stocks.style.highlight_null(axis=None), use_container_width=True)

st.markdown("### 📌 Current Positions – ETFs")
st.dataframe(
    etfs[["Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value", "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Target Horizon", "Recommendation"]],
    use_container_width=True
)

# -------------------- Watchlist --------------------
st.markdown("### 👀 Watchlist")
watchlist = pd.DataFrame({
    "Name": ["Nvidia Corp", "ASML Holding", "Tesla Inc"],
    "Ticker": ["NVDA", "ASML", "TSLA"],
    "Currency": ["USD", "EUR", "USD"],
    "Comment": ["High growth", "Strong EU Tech", "Volatile but strategic"]
})
st.dataframe(watchlist, use_container_width=True)

# -------------------- Kursentwicklung --------------------
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
fig.update_layout(title=f"Kursentwicklung von {selected_ticker} (5 Jahre, täglich)", xaxis_title="Datum", yaxis_title="Kurs (lokale Währung)", height=500)
st.plotly_chart(fig, use_container_width=True)
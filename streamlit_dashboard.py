# Portfolio Dashboard: Live-Analyse mit KPIs, Empfehlungen und Kursentwicklung

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# -----------------------------------------------------------------------------
# Konfiguration der Seite
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("\U0001F4CA Live Portfolio Dashboard")

# -----------------------------------------------------------------------------
# Eingabedaten: Portfolio, Cash, Einzahlungen, Watchlist
# -----------------------------------------------------------------------------
portfolio = pd.DataFrame({
    "Type": ["Stock", "ETF", "ETF"],
    "Name": ["Palantir Technologies", "iShares Automation & Robotics", "iShares Core MSCI World"],
    "Ticker": ["PLTR.DE", "RBOT.SW", "IWRD.SW"],
    "Currency": ["EUR", "USD", "USD"],
    "Units": [2, 10, 1],
    "Buy Price": [79.72, 12.26, 101.30],
    "Target Horizon": ["1-2 years", "3-5 years", "3-5 years"]
})

watchlist = pd.DataFrame({
    "Name": ["Nvidia Corp", "ASML Holding", "Tesla Inc"],
    "Ticker": ["NVDA", "ASML", "TSLA"],
    "Currency": ["USD", "EUR", "USD"],
    "Comment": ["High growth", "Strong EU Tech", "Volatile but strategic"]
})

cash = 162.07
total_deposit = 500.00
invested_amount = total_deposit - cash

# -----------------------------------------------------------------------------
# Datenabruf: Kursdaten und Finanzkennzahlen via yfinance
# -----------------------------------------------------------------------------
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
        return pd.Series({col: None for col in [
            "Current Price", "EPS", "PE Ratio", "Market Cap",
            "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]})

kpis = portfolio["Ticker"].apply(fetch_data)
portfolio = pd.concat([portfolio, kpis], axis=1)

# -----------------------------------------------------------------------------
# Berechnungen: Werte, P/L, Empfehlungen
# -----------------------------------------------------------------------------
portfolio["Value"] = portfolio["Units"] * portfolio["Current Price"]
portfolio["Cost Basis"] = portfolio["Units"] * portfolio["Buy Price"]
portfolio["Profit/Loss (CHF)"] = portfolio["Value"] - portfolio["Cost Basis"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

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
    return "HOLD"

portfolio["Recommendation"] = portfolio.apply(recommendation, axis=1)

# Runden auf 3 Nachkommastellen
round_cols = [
    "Buy Price", "Current Price", "Value", "Cost Basis", "Profit/Loss (CHF)",
    "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta",
    "Free Cash Flow", "Revenue Growth YoY (%)"
]
portfolio[round_cols] = portfolio[round_cols].round(3)

# -----------------------------------------------------------------------------
# Visualisierung: Portfolio KPIs
# -----------------------------------------------------------------------------
total_value = portfolio["Value"].sum() + cash
growth_pct = ((total_value - total_deposit) / total_deposit) * 100

st.markdown("### \U0001F4B0 Portfolio Summary")
col1, col2, col3 = st.columns([1.2, 1.2, 1.2])
with col1:
    st.metric(label="Total Deposit", value=f"{total_deposit:.2f} CHF")
    st.markdown(f"""
        <div style='margin-top: -12px; font-size: 0.9em;'>
        • Invested: {invested_amount:.2f} CHF<br>
        • Cash: {cash:.2f} CHF
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.metric(label="Total Value Portfolio", value=f"{total_value:.2f} CHF")
with col3:
    st.metric(label="Value Development", value=f"{growth_pct:.2f} %")

# -----------------------------------------------------------------------------
# Tabellen: Portfolio und Watchlist
# -----------------------------------------------------------------------------
st.markdown("### \U0001F4CC Current Positions")
def highlight_recommendation(val):
    if "BUY" in str(val): return "background-color: #d1f7c4"
    if "SELL" in str(val): return "background-color: #f8d7da"
    if "Review" in str(val) or "Risky" in str(val): return "background-color: #fff3cd"
    return ""

styled_df = portfolio[[
    "Type", "Name", "Ticker", "Units", "Buy Price", "Current Price", "Value",
    "Profit/Loss (CHF)", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta",
    "Free Cash Flow", "Revenue Growth YoY (%)", "Target Horizon", "Recommendation"
]].style.applymap(highlight_recommendation, subset=["Recommendation"])

st.dataframe(styled_df, use_container_width=True)

st.markdown("### \U0001F440 Watchlist")
st.dataframe(watchlist, use_container_width=True)

# -----------------------------------------------------------------------------
# Kursentwicklung: Auswahl aus Portfolio + Watchlist
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("### \U0001F4C8 Kursentwicklung anzeigen")
all_tickers = pd.concat([portfolio[["Ticker", "Name"]], watchlist[["Ticker", "Name"]]], ignore_index=True)
selected_label = st.selectbox("Wähle eine Position aus dem Portfolio oder der Watchlist:",
                              options=all_tickers["Ticker"],
                              format_func=lambda x: all_tickers.loc[all_tickers["Ticker"] == x, "Name"].values[0])

@st.cache_data(ttl=3600)
def get_history(ticker):
    try:
        stock = yf.Ticker(ticker)
        return stock.history(period="5y", interval="1d")
    except:
        return pd.DataFrame()

hist = get_history(selected_label)
if not hist.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
    fig.update_layout(
        title=f"Kursentwicklung von {selected_label} (5 Jahre, täglich)",
        xaxis_title="Datum", yaxis_title="Kurs (in lokaler Währung)", height=500
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Für dieses Wertpapier konnten keine historischen Daten geladen werden.")
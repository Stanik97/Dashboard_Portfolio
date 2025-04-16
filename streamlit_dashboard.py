import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("\U0001F4CA Live Portfolio Dashboard")

# --- INPUT: CASH & DEPOSIT ---
cash = 162.07
manual_deposit = 500.00
invested = manual_deposit - cash

# --- PORTFOLIO POSITIONS ---
portfolio = pd.DataFrame({
    "Type": ["Stock", "ETF", "ETF"],
    "Name": ["Palantir Technologies", "iShares Automation & Robotics", "iShares Core MSCI World"],
    "Ticker": ["PLTR.DE", "RBOT.SW", "IWRD.SW"],
    "Currency": ["EUR", "USD", "USD"],
    "Units": [2, 10, 1],
    "Buy Price": [79.72, 12.26, 101.30],
    "Target Horizon": ["1-2 years", "3-5 years", "3-5 years"]
})

# --- FETCH DATA FROM YAHOO FINANCE ---
@st.cache_data(ttl=300)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = stock.history(period="1d")['Close'].iloc[-1]
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
        return pd.Series({col: None for col in ["Current Price", "EPS", "PE Ratio", "Market Cap", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]})

portfolio = pd.concat([portfolio, portfolio["Ticker"].apply(fetch_data)], axis=1)

# --- CALCULATIONS ---
portfolio["Value"] = portfolio["Units"] * portfolio["Current Price"]
portfolio["Cost Basis"] = portfolio["Units"] * portfolio["Buy Price"]
portfolio["Profit/Loss (CHF)"] = portfolio["Value"] - portfolio["Cost Basis"]
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

total_value = portfolio["Value"].sum() + cash
growth_vs_deposit = ((total_value - manual_deposit) / manual_deposit) * 100

# --- RECOMMENDATION LOGIC ---
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

# --- ROUND VALUES TO 3 DECIMALS ---
numeric_cols = ["Buy Price", "Current Price", "Value", "Cost Basis", "Profit/Loss (CHF)",
                "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[numeric_cols] = portfolio[numeric_cols].round(3)

# --- PORTFOLIO SUMMARY ---
st.markdown("### \U0001F4B0 Portfolio Summary")
scol1, scol2, scol3 = st.columns([1, 1, 1])

with scol1:
    st.metric("Total Deposit", f"{manual_deposit:.2f} CHF")
    st.markdown("<div style='font-size: 13px; margin-top: -10px;'>• Invested: {:.2f} CHF<br>• Cash: {:.2f} CHF</div>".format(invested, cash), unsafe_allow_html=True)
with scol2:
    st.metric("Total Value Portfolio", f"{total_value:.2f} CHF")
with scol3:
    st.metric("Value Development", f"{growth_vs_deposit:.2f} %")

# --- CURRENT POSITIONS TABLE ---
st.markdown("### 📌 Current Positions")
styled_df = portfolio[[
    "Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value",
    "Profit/Loss (CHF)", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta",
    "Free Cash Flow", "Revenue Growth YoY (%)", "Target Horizon", "Recommendation"
]].style.applymap(lambda val: "background-color: #d1f7c4" if "BUY" in str(val)
                  else "background-color: #f8d7da" if "SELL" in str(val)
                  else "background-color: #fff3cd" if "Risky" in str(val) or "Review" in str(val)
                  else "", subset=["Recommendation"])

st.dataframe(styled_df, use_container_width=True)

# --- WATCHLIST ---
st.markdown("### 👀 Watchlist")
watchlist = pd.DataFrame({
    "Name": ["Nvidia Corp", "ASML Holding", "Tesla Inc"],
    "Ticker": ["NVDA", "ASML", "TSLA"],
    "Currency": ["USD", "EUR", "USD"],
    "Comment": ["High growth", "Strong EU Tech", "Volatile but strategic"]
})
st.dataframe(watchlist, use_container_width=True)

# --- HISTORICAL CHART ---
st.markdown("---")
st.markdown("### 📈 Kursentwicklung anzeigen")

# Ticker Auswahl aus Portfolio UND Watchlist
combined_tickers = pd.concat([portfolio[["Name", "Ticker"]], watchlist[["Name", "Ticker"]]])
selected_name = st.selectbox("Wähle eine Position aus dem Portfolio oder der Watchlist:", combined_tickers["Name"])
selected_ticker = combined_tickers[combined_tickers["Name"] == selected_name]["Ticker"].values[0]

@st.cache_data(ttl=3600)
def get_history(ticker):
    try:
        return yf.Ticker(ticker).history(period="5y", interval="1d")
    except:
        return pd.DataFrame()

hist = get_history(selected_ticker)
if not hist.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Kurs", line=dict(color="royalblue")))
    fig.update_layout(title=f"Kursentwicklung von {selected_ticker} (5 Jahre, täglich)",
                      xaxis_title="Datum", yaxis_title="Kurs (in lokaler Währung)", height=500)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Keine Kursdaten verfügbar.")
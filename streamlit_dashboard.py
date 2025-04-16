import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# ------------------------- Page Configuration -------------------------
st.set_page_config(page_title="Portfolio Dashboard", layout="wide")
st.title("📊 Live Portfolio Dashboard")

# ------------------------- Input Data -------------------------
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
invested = total_deposit - cash

# ------------------------- Wechselkurs abrufen -------------------------
@st.cache_data(ttl=600)
def get_fx_rate():
    try:
        return yf.Ticker("EURUSD=X").history(period="1d")["Close"].iloc[-1]
    except:
        return 1.08  # fallback-Kurs

eur_usd = get_fx_rate()

# ------------------------- Kurs- und KPI-Abruf -------------------------
@st.cache_data(ttl=300)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = stock.history(period="1d")["Close"].iloc[-1]
        return pd.Series({
            "Current Price Raw": price,
            "EPS": info.get("trailingEps"),
            "PE Ratio": info.get("trailingPE"),
            "Market Cap": info.get("marketCap"),
            "PEG Ratio": info.get("pegRatio"),
            "Beta": info.get("beta"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Revenue Growth YoY (%)": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None
        })
    except:
        return pd.Series({"Current Price Raw": None, "EPS": None, "PE Ratio": None, "Market Cap": None,
                          "PEG Ratio": None, "Beta": None, "Free Cash Flow": None, "Revenue Growth YoY (%)": None})

kpis = portfolio["Ticker"].apply(fetch_data)
portfolio = pd.concat([portfolio, kpis], axis=1)

# ------------------------- Währungslogik -------------------------
def convert_currency(row):
    if row["Currency"] == "EUR" and not pd.isna(row["Current Price Raw"]):
        return round(row["Current Price Raw"] * eur_usd, 3)
    return round(row["Current Price Raw"], 3) if not pd.isna(row["Current Price Raw"]) else None

portfolio["Current Price"] = portfolio.apply(convert_currency, axis=1)

# ------------------------- Berechnungen -------------------------
portfolio["Value"] = (portfolio["Units"] * portfolio["Current Price"]).round(3)
portfolio["Cost Basis"] = (portfolio["Units"] * portfolio["Buy Price"]).round(3)
portfolio["Profit/Loss"] = (portfolio["Value"] - portfolio["Cost Basis"]).round(3)
portfolio["Profit/Loss (%)"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"] * 100).round(3)

# ------------------------- Empfehlungen -------------------------
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

# ------------------------- Runden aller numerischen Felder -------------------------
round_cols = ["Buy Price", "Current Price", "Value", "Cost Basis", "Profit/Loss", "Profit/Loss (%)",
              "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow", "Revenue Growth YoY (%)"]
portfolio[round_cols] = portfolio[round_cols].round(3)

# ------------------------- Portfolio Summary -------------------------
total_value = portfolio["Value"].sum() + cash
growth_pct = ((total_value - total_deposit) / total_deposit) * 100

st.markdown("### 💰 Portfolio Summary")
col1, col2, col3 = st.columns([1.2, 1.2, 1])
with col1:
    st.metric(label="Total Deposit", value=f"{total_deposit:.3f} CHF")
    st.markdown("""
    <div style='font-size: 0.9rem; margin-top: -10px;'>
        • Invested: {:.2f} CHF<br>
        • Cash: {:.2f} CHF
    </div>""".format(invested, cash), unsafe_allow_html=True)
with col2:
    st.metric(label="Total Value Portfolio", value=f"{total_value:.3f} CHF")
with col3:
    st.metric(label="Value Development", value=f"{growth_pct:.2f} %")

# ------------------------- Positions-Tabelle -------------------------
st.markdown("### 📌 Current Positions")
styled_df = portfolio[[
    "Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value",
    "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta",
    "Free Cash Flow", "Revenue Growth YoY (%)", "Target Horizon", "Recommendation"
]].style.applymap(lambda val: "background-color: #d1f7c4" if "BUY" in str(val)
                  else "background-color: #f8d7da" if "SELL" in str(val)
                  else "background-color: #fff3cd" if "Review" in str(val) or "Risky" in str(val)
                  else "", subset=["Recommendation"])

st.dataframe(styled_df, use_container_width=True)

# ------------------------- Watchlist -------------------------
st.markdown("### 👀 Watchlist")
watchlist = pd.DataFrame({
    "Name": ["Nvidia Corp", "ASML Holding", "Tesla Inc"],
    "Ticker": ["NVDA", "ASML", "TSLA"],
    "Currency": ["USD", "EUR", "USD"],
    "Comment": ["High growth", "Strong EU Tech", "Volatile but strategic"]
})
st.dataframe(watchlist, use_container_width=True)

# ------------------------- Kursverlauf -------------------------
st.markdown("---")
st.markdown("### 📈 Kursentwicklung anzeigen")
selected_ticker = st.selectbox("Wähle eine Position aus dem Portfolio:",
                               pd.concat([portfolio["Ticker"], watchlist["Ticker"]]).unique())

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
                      xaxis_title="Datum", yaxis_title="Kurs (lokale Währung)", height=500)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Keine Kursdaten verfügbar.")
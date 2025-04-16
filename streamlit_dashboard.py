# 📌 Current Positions – Stocks
st.markdown("### 📌 Current Positions – Stocks")
stocks_df = portfolio[portfolio["Type"] == "Stock"]

if not stocks_df.empty:
    st.dataframe(stocks_df[
        ["Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)",
         "Profit/Loss", "Profit/Loss (%)", "EPS", "PE Ratio", "PEG Ratio", "Beta", "Free Cash Flow",
         "Revenue Growth YoY (%)", "Target Horizon", "Recommendation"]
    ], use_container_width=True)
else:
    st.info("Keine Aktienpositionen vorhanden.")

# 📌 Current Positions – ETFs
st.markdown("### 📌 Current Positions – ETFs")
etfs_df = portfolio[portfolio["Type"] == "ETF"]

if not etfs_df.empty:
    st.dataframe(etfs_df[
        ["Type", "Name", "Ticker", "Currency", "Units", "Buy Price", "Current Price", "Value (CHF)",
         "Profit/Loss", "Profit/Loss (%)", "PE Ratio", "Target Horizon", "Recommendation"]
    ], use_container_width=True)
else:
    st.info("Keine ETF-Positionen vorhanden.")

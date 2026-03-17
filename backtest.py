# backtest.py
import streamlit as st
import pandas as pd
from binance.client import Client
import plotly.graph_objects as go

client = Client("API_KEY", "API_SECRET")  # अपना API डालें

def run_backtest(symbol, timeframe, start_date, end_date, initial_capital=10000):
    st.info(f"Backtesting {symbol} on {timeframe} from {start_date} to {end_date}...")

    # Binance से historical data लाओ (1h या 4h बेहतर)
    klines = client.futures_historical_klines(symbol, timeframe, start_date, end_date)
    df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', ...])
    df[['open','high','low','close']] = df[['open','high','low','close']].astype(float)
    df['time'] = pd.to_datetime(df['time'], unit='ms')

    # साधारण EMA क्रॉस स्ट्रेटेजी बैकटेस्ट
    df['EMA9'] = df['close'].ewm(span=9).mean()
    df['EMA21'] = df['close'].ewm(span=21).mean()

    df['signal'] = 0
    df.loc[df['EMA9'] > df['EMA21'], 'signal'] = 1   # Buy
    df.loc[df['EMA9'] < df['EMA21'], 'signal'] = -1  # Sell

    # सिम्पल बैकटेस्ट लॉजिक
    capital = initial_capital
    position = 0
    trades = []

    for i in range(1, len(df)):
        if df['signal'].iloc[i] == 1 and position == 0:
            position = capital / df['close'].iloc[i]
            entry = df['close'].iloc[i]
            trades.append({"Date": df['time'].iloc[i], "Action": "BUY", "Price": entry})

        elif df['signal'].iloc[i] == -1 and position > 0:
            exit_price = df['close'].iloc[i]
            pnl = (exit_price - entry) * position
            capital += pnl
            trades.append({"Date": df['time'].iloc[i], "Action": "SELL", "Price": exit_price, "PnL": pnl})
            position = 0

    final_capital = capital + (position * df['close'].iloc[-1] if position > 0 else 0)
    profit_pct = ((final_capital - initial_capital) / initial_capital) * 100

    st.success(f"Backtest Complete! Final Capital: ${final_capital:,.2f} (+{profit_pct:.2f}%)")

    # ट्रेड्स टेबल
    st.dataframe(pd.DataFrame(trades))

    # Equity Curve
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['time'], y=[initial_capital] * len(df), name="Initial"))
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    st.title("Backtest Engine")
    symbol = st.selectbox("Symbol", ["BTCUSDT", "ETHUSDT"])
    tf = st.selectbox("Timeframe", ["5m", "15m", "1h", "4h"])
    start = st.date_input("Start Date")
    end = st.date_input("End Date")
    if st.button("Run Backtest"):
        run_backtest(symbol, tf, str(start), str(end))
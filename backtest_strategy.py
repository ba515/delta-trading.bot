# backtest_strategy.py
import streamlit as st
import pandas as pd
from binance.client import Client
import plotly.graph_objects as go
from datetime import datetime

client = Client("BjtzH3hIFVKuh47ny8lPXQlgvLO4oRUxhkI6wx0rPuDV2Od9sXu8twYGtyLMqref", "4hLSUf6ZfS0mB13YE3pLKMkUIBpFL4gcPghoT9K2PL7tlLGR0o2NJKAdXaPJW4hJ")  # अपना API डालें

def run_smart_backtest(symbol="BTCUSDT", timeframe="5m", days=180, initial_capital=10000):
    st.title(f"Backtest Report: {symbol} ({timeframe})")
    
    # डेटा लाओ
    since = int((datetime.now().timestamp() - days*86400) * 1000)
    klines = client.futures_historical_klines(symbol, timeframe, since)
    
    df = pd.DataFrame(klines, columns=[
        'time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
        'quote_asset_volume', 'number_of_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    
    df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].astype(float)
    df['time'] = pd.to_datetime(df['time'], unit='ms')

    # इंडिकेटर्स
    df['EMA9']  = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # सिग्नल
    df['signal'] = 0
    df.loc[(df['EMA9'] > df['EMA21']) & (df['RSI'] < 65) & (df['RSI'] > 35), 'signal'] = 1   # Buy
    df.loc[(df['EMA9'] < df['EMA21']) & (df['RSI'] > 35), 'signal'] = -1                    # Sell

    # बैकटेस्ट लॉजिक
    capital = initial_capital
    position = 0
    entry_price = 0
    trades = []
    equity_curve = []

    for i in range(1, len(df)):
        equity_curve.append(capital)

        if df['signal'].iloc[i] == 1 and position == 0:   # Buy
            position = capital / df['close'].iloc[i]
            entry_price = df['close'].iloc[i]
            trades.append({"Date": df['time'].iloc[i], "Action": "BUY", "Price": entry_price})

        elif df['signal'].iloc[i] == -1 and position > 0:  # Sell
            exit_price = df['close'].iloc[i]
            pnl = (exit_price - entry_price) * position
            capital += pnl
            trades.append({"Date": df['time'].iloc[i], "Action": "SELL", "Price": exit_price, "PnL": round(pnl, 2)})
            position = 0

    final_capital = capital + (position * df['close'].iloc[-1] if position > 0 else 0)
    total_return = ((final_capital - initial_capital) / initial_capital) * 100

    st.success(f"✅ बैकटेस्ट पूरा! कुल रिटर्न: **{total_return:.2f}%**")
    st.metric("शुरुआती कैपिटल", f"${initial_capital:,.0f}", f"${final_capital:,.0f} (+{total_return:.1f}%)")

    # ट्रेड्स टेबल
    st.subheader("ट्रेड हिस्ट्री")
    st.dataframe(pd.DataFrame(trades))

    # Equity Curve
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['time'][:len(equity_curve)], y=equity_curve, name="Equity Curve"))
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    st.title("स्मार्ट बैकटेस्ट इंजन")
    symbol = st.selectbox("Symbol", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    tf = st.selectbox("Timeframe", ["5m", "15m", "1h", "4h"])
    days = st.slider("Backtest Period (दिन)", 30, 365, 180)
    capital = st.number_input("Initial Capital (USDT)", value=10000)

    if st.button("Run Backtest", type="primary"):
        run_smart_backtest(symbol, tf, days, capital)
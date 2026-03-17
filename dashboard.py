import streamlit as st
import pandas as pd
from binance.client import Client
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
from telegram import Bot
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

# ==================== API और अलर्ट सेटिंग्स ====================
API_KEY    = "BjtzH3hIFVKuh47ny8lPXQlgvLO4oRUxhkI6wx0rPuDV2Od9sXu8twYGtyLMqref"
API_SECRET = "4hLSUf6ZfS0mB13YE3pLKMkUIBpFL4gcPghoT9K2PL7tlLGR0o2NJKAdXaPJW4hJ"

TELEGRAM_TOKEN  = "8633517801:AAFmmfCr70vGXnLo7BM80WmLujm6sYHaktE"
TELEGRAM_CHAT_ID = "5542675157"

EMAIL_SENDER    = "bhagwatilalprajapati675@gmail.com"
EMAIL_PASSWORD  = "xflm zgpy ojlh uiuw"
EMAIL_RECEIVER  = "bhagwatilalprajapati675@gmail.com"

client = Client(API_KEY, API_SECRET)

ALL_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"]

st.set_page_config(page_title="प्रो ट्रेडिंग डैशबोर्ड", layout="wide")

# ===================== साइडबार =====================
with st.sidebar:
    st.header("⚙️ सेटिंग्स")
    theme = st.selectbox("थीम", ["Dark", "Light"], index=0)
    selected_symbols = st.multiselect("सिंबल चुनें", ALL_SYMBOLS, default=["BTCUSDT", "ETHUSDT"])
    selected_tf = st.selectbox("टाइमफ्रेम", ["5m", "15m", "30m", "1h", "4h", "1d"], index=1)

    st.subheader("लीवरेज कंट्रोल")
    leverage_value = st.slider("लीवरेज (x)", 1, 125, 5, step=1)
    if st.button("सभी पर लीवरेज सेट करें"):
        for sym in selected_symbols:
            try:
                client.futures_change_leverage(symbol=sym, leverage=leverage_value)
                st.success(f"{sym} → {leverage_value}x")
            except Exception as e:
                st.error(f"{sym} में समस्या: {str(e)}")

    st.subheader("ऑटोमेटेड ट्रेडिंग")
    auto_trading = st.toggle("ऑटो ट्रेडिंग चालू/बंद", value=False)

# ===================== टॉप पर कुल PnL + वॉलेट =====================
col1, col2, col3 = st.columns(3)
try:
    account = client.futures_account()
    wallet = float(account['totalWalletBalance'])
    unrealized = float(account['totalUnrealizedProfit'])
    available = float(account['availableBalance'])

    col1.metric("वॉलेट बैलेंस", f"{wallet:,.2f} USDT")
    col2.metric("अनरियलाइज्ड PnL", f"{unrealized:,.2f} USDT", delta_color="normal" if unrealized >= 0 else "inverse")
    col3.metric("उपलब्ध मार्जिन", f"{available:,.2f} USDT")
except:
    st.warning("वॉलेट डेटा लोड नहीं हो पाया")

# ===================== चार्ट प्लेसहोल्डर =====================
chart_placeholders = {}
for sym in selected_symbols:
    with st.container(border=True):
        st.subheader(f"{sym} - {selected_tf}")
        chart_placeholders[sym] = st.empty()

status = st.empty()

# ===================== अलर्ट फंक्शन =====================
async def send_telegram_alert(message):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="HTML")
    except:
        pass

def send_email_alert(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
    except:
        pass

async def send_alert(message, subject="ट्रेडिंग अलर्ट"):
    await send_telegram_alert(message)
    send_email_alert(subject, message)

# ===================== मुख्य अपडेट फंक्शन =====================
def update():
    for symbol in selected_symbols:
        try:
            klines = client.futures_klines(symbol=symbol, interval=selected_tf, limit=200)
            if len(klines) == 0:
                status.error(f"{symbol} में कोई डेटा नहीं मिला!")
                continue

            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])

            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            df['time'] = pd.to_datetime(df['open_time'], unit='ms')

            # EMA + RSI
            df['EMA9']  = df['close'].ewm(span=9, adjust=False).mean()
            df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # MACD
            df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = df['EMA12'] - df['EMA26']
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Histogram'] = df['MACD'] - df['Signal']

            # Bollinger Bands
            df['BB_Middle'] = df['close'].rolling(20).mean()
            df['BB_Std'] = df['close'].rolling(20).std()
            df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
            df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']

            last_rsi = df['RSI'].iloc[-1]

            # अलर्ट ट्रिगर
            if last_rsi > 75:
                asyncio.run(send_alert(f"🚨 {symbol} ओवरबॉट! RSI: {last_rsi:.1f}", f"{symbol} Overbought"))

            if last_rsi < 25:
                asyncio.run(send_alert(f"🟢 {symbol} ओवरसोल्ड! RSI: {last_rsi:.1f}", f"{symbol} Oversold"))

            # MACD + Bollinger सिग्नल अलर्ट
            if df['MACD'].iloc[-1] > df['Signal'].iloc[-1] and df['close'].iloc[-1] < df['BB_Upper'].iloc[-1]:
                asyncio.run(send_alert(f"📈 {symbol} MACD Buy + Bollinger Signal!", f"{symbol} Buy Alert"))

            # Position Info + Trailing SL
            positions = client.futures_position_information(symbol=symbol)
            pos = next((p for p in positions if p['symbol'] == symbol and float(p['positionAmt']) != 0), None)

            trailing_sl = None
            if pos:
                amt = float(pos['positionAmt'])
                side = "Long" if amt > 0 else "Short"
                entry = float(pos['entryPrice'])
                current = float(client.futures_symbol_ticker(symbol=symbol)['price'])
                pnl = float(pos['unRealizedProfit'])
                pnl_pct = pnl / (abs(amt) * entry) * 100 if entry != 0 else 0

                trailing_pct = 0.015
                if side == "Long":
                    highest = df['high'].cummax()
                    trailing_sl = highest * (1 - trailing_pct)
                else:
                    lowest = df['low'].cummin()
                    trailing_sl = lowest * (1 + trailing_pct)

                df['TrailingSL'] = trailing_sl

                col1, col2 = st.columns(2)
                col1.metric(f"{symbol} Position", f"{side} @ {entry:,.2f}", delta=f"{pnl:,.2f} USDT ({pnl_pct:+.2f}%)")
                col2.metric("Leverage", f"{pos['leverage']}x")

                st.caption(f"Liq Price: {float(pos['liquidationPrice']):,.2f}")

                if st.button(f"{symbol} Position बंद करें", type="primary"):
                    try:
                        close_side = "SELL" if side == "Long" else "BUY"
                        close_qty = abs(amt)
                        client.futures_create_order(
                            symbol=symbol,
                            side=close_side,
                            type="MARKET",
                            quantity=close_qty,
                            reduceOnly=True
                        )
                        st.success(f"{symbol} Position बंद हो गया!")
                        asyncio.run(send_alert(f"{symbol} Position मैन्युअली बंद किया गया"))
                    except Exception as e:
                        st.error(f"बंद करने में समस्या: {str(e)}")

            else:
                st.info(f"{symbol}: कोई ओपन पोजीशन नहीं")

            # ==================== 3D व्यू ====================
            try:
                fig_3d = go.Figure()

                fig_3d.add_trace(go.Scatter3d(
                    x=df['time'],
                    y=df['close'],
                    z=df['volume'],
                    mode='lines',
                    name='Price + Volume 3D',
                    line=dict(color=df['close'], colorscale='Viridis', width=4)
                ))

                fig_3d.add_trace(go.Scatter3d(
                    x=df['time'],
                    y=df['RSI'],
                    z=df['close'],
                    mode='markers',
                    name='RSI 3D Points',
                    marker=dict(size=6, color=df['RSI'], colorscale='Plasma', opacity=0.8)
                ))

                fig_3d.update_layout(
                    scene=dict(
                        xaxis_title='समय',
                        yaxis_title='प्राइस (USDT)',
                        zaxis_title='वॉल्यूम / RSI',
                        bgcolor='rgba(0,0,0,0.8)' if theme == "Dark" else 'white'
                    ),
                    height=700,
                    margin=dict(l=0, r=0, b=0, t=40),
                    paper_bgcolor='rgba(0,0,0,0)' if theme == "Dark" else 'white',
                    title=f"{symbol} 3D Price-Volume-RSI View"
                )

                st.plotly_chart(fig_3d, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True})

            except Exception as e:
                st.warning(f"3D व्यू लोड नहीं हो पाया: {str(e)}")

            # ==================== मुख्य 2D चार्ट ====================
            fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                                vertical_spacing=0.03, row_heights=[0.45, 0.20, 0.20, 0.15],
                                subplot_titles=(f"{symbol} {selected_tf}", "MACD + Bollinger", "RSI", "Volume"))

            # Candlestick + EMA + Bollinger
            fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'],
                                         low=df['low'], close=df['close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['time'], y=df['EMA9'], name='EMA9', line=dict(color='blue')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['time'], y=df['EMA21'], name='EMA21', line=dict(color='orange')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['time'], y=df['BB_Upper'], name='BB Upper', line=dict(color='gray', dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['time'], y=df['BB_Lower'], name='BB Lower', line=dict(color='gray', dash='dash')), row=1, col=1)

            # MACD + Signal + Histogram
            fig.add_trace(go.Scatter(x=df['time'], y=df['MACD'], name='MACD', line=dict(color='cyan')), row=2, col=1)
            fig.add_trace(go.Scatter(x=df['time'], y=df['Signal'], name='Signal', line=dict(color='orange')), row=2, col=1)
            fig.add_trace(go.Bar(x=df['time'], y=df['Histogram'], name='Histogram', marker_color=df['Histogram'].apply(lambda x: 'green' if x>0 else 'red')), row=2, col=1)

            # RSI
            fig.add_trace(go.Scatter(x=df['time'], y=df['RSI'], name='RSI', line=dict(color='purple')), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="lime", row=3, col=1)

            # Volume
            fig.add_trace(go.Bar(x=df['time'], y=df['volume'], name='Volume', marker_color='rgba(100,149,237,0.6)'), row=4, col=1)

            fig.update_layout(height=950, showlegend=True, template="plotly_dark" if theme == "Dark" else "plotly",
                              xaxis_rangeslider_visible=False)

            with chart_placeholders[symbol]:
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            status.error(f"{symbol}: {str(e)}")

    status.success(f"अपडेट: {time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    col1, col2 = st.columns([7, 2])
    with col1:
        st.info(f"ट्रैकिंग: {len(selected_symbols)} सिंबल • हर 20 सेकंड अपडेट")
    with col2:
        if st.button("🔄 Refresh Now", type="primary", use_container_width=True):
            update()
            st.success("रिफ्रेश हो गया!")

    while True:
        update()
        time.sleep(20)
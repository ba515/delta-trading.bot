# auto_trading.py
import time
import asyncio
from binance.client import Client
from telegram import Bot

# ==================== सेटिंग्स ====================
API_KEY    = "BjtzH3hIFVKuh47ny8lPXQlgvLO4oRUxhkI6wx0rPuDV2Od9sXu8twYGtyLMqref"
API_SECRET = "4hLSUf6ZfS0mB13YE3pLKMkUIBpFL4gcPghoT9K2PL7tlLGR0o2NJKAdXaPJW4hJ"
TELEGRAM_TOKEN = "8633517801:AAFmmfCr70vGXnLo7BM80WmLujm6sYHaktE"
TELEGRAM_CHAT_ID = "5542675157"

client = Client(API_KEY, API_SECRET)
bot = Bot(token=TELEGRAM_TOKEN)

# स्मार्ट ट्रेडिंग सेटिंग्स
SYMBOL = "BTCUSDT"  # या डायनामिक कर सकते हैं
TIMEFRAME = "5m"
RISK_PER_TRADE = 0.01  # 1% रिस्क प्रति ट्रेड
TRAILING_PCT = 1.5     # ट्रेलिंग SL %
TAKE_PROFIT_PCT = 3.0  # टेक प्रॉफिट %

async def send_alert(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="HTML")
        print(f"[ALERT] {message}")
    except Exception as e:
        print(f"[ALERT ERROR] {e}")

def get_current_position(symbol):
    positions = client.futures_position_information(symbol=symbol)
    pos = next((p for p in positions if p['symbol'] == symbol), None)
    if pos and float(pos['positionAmt']) != 0:
        return {
            "side": "Long" if float(pos['positionAmt']) > 0 else "Short",
            "entry": float(pos['entryPrice']),
            "quantity": abs(float(pos['positionAmt'])),
            "leverage": pos['leverage']
        }
    return None

def place_order(symbol, side, quantity):
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity
        )
        asyncio.run(send_alert(f"ऑर्डर प्लेस हुआ: {side} {symbol} {quantity}"))
        return order
    except Exception as e:
        asyncio.run(send_alert(f"ऑर्डर फेल: {str(e)}"))
        return None

def calculate_position_size(current_price, stop_loss_price, risk_percent=RISK_PER_TRADE):
    risk_amount = current_price * risk_percent
    distance = abs(current_price - stop_loss_price) / current_price
    size = risk_amount / distance
    return round(size, 3)  # प्रिसिजन के अनुसार

def auto_trading_loop():
    st.session_state.auto_trading_running = True
    print("ऑटो ट्रेडिंग शुरू")

    while st.session_state.get('auto_trading_running', False):
        try:
            klines = client.futures_klines(symbol=SYMBOL, interval=TIMEFRAME, limit=100)
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', ...])
            df[['open','high','low','close']] = df[['open','high','low','close']].astype(float)
            df['time'] = pd.to_datetime(df['open_time'], unit='ms')

            df['EMA9']  = df['close'].ewm(span=9).mean()
            df['EMA21'] = df['close'].ewm(span=21).mean()
            df['RSI']   = 100 - (100 / (1 + (df['close'].diff(1).where(lambda x: x > 0, 0).rolling(14).mean() / 
                                        -df['close'].diff(1).where(lambda x: x < 0, 0).rolling(14).mean())))

            last_close = df['close'].iloc[-1]
            last_ema9  = df['EMA9'].iloc[-1]
            last_ema21 = df['EMA21'].iloc[-1]
            last_rsi   = df['RSI'].iloc[-1]

            position = get_current_position(SYMBOL)

            if position is None:
                # कोई पोजीशन नहीं → एंट्री चेक
                if last_ema9 > last_ema21 and last_rsi < 60 and last_rsi > 40:
                    # Buy सिग्नल
                    sl_price = last_close * (1 - 0.015)  # 1.5% SL
                    size = calculate_position_size(last_close, sl_price)
                    order = place_order(SYMBOL, "BUY", size)
                    if order:
                        asyncio.run(send_alert(f"ऑटो BUY: {SYMBOL} @ {last_close:,.2f} | SL: {sl_price:,.2f}"))

            else:
                # पोजीशन है → ट्रेलिंग SL अपडेट + एक्जिट चेक
                if position['side'] == "Long":
                    if last_ema9 < last_ema21 or last_rsi > 75:
                        place_order(SYMBOL, "SELL", position['quantity'])
                        asyncio.run(send_alert(f"ऑटो EXIT Long: {SYMBOL} @ {last_close:,.2f}"))

                else:  # Short
                    if last_ema9 > last_ema21 or last_rsi < 25:
                        place_order(SYMBOL, "BUY", position['quantity'])
                        asyncio.run(send_alert(f"ऑटो EXIT Short: {SYMBOL} @ {last_close:,.2f}"))

        except Exception as e:
            print(f"ऑटो ट्रेडिंग एरर: {e}")

        time.sleep(60)  # हर 1 मिनट चेक

    print("ऑटो ट्रेडिंग बंद")
import ccxt
import time
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from alerts import send_telegram, send_email

# ===================== CONFIG =====================
EXCHANGE_NAME = 'binance'
SYMBOL        = 'BTC/USDT:USDT'     # Binance USDⓈ-M Perpetual Futures symbol
TIMEFRAME     = '5m'                # 1m, 3m, 5m, 15m, 30m, 1h आदि
CANDLES_LIMIT = 100                 # EMA के लिए काफी

# ------------------ नई settings (इन्हें जोड़ो) ------------------
RSI_PERIOD       = 14
RSI_BUY_BELOW    = 45     # RSI < 45 → BUY allowed
RSI_SELL_ABOVE   = 55     # RSI > 55 → SELL allowed

STOP_LOSS_PERCENT   = 1.2   # 1.2%
TAKE_PROFIT_PERCENT = 2.5   # 2.5%

LEVERAGE         = 5
ORDER_AMOUNT_USDT = 20      # हर ट्रेड में कितना USDT यूज करना

API_KEY    = 'BjtzH3hIFVKuh47ny8lPXQlgvLO4oRUxhkI6wx0rPuDV2Od9sXu8twYGtyLMqref'       # ←←← Binance से API Key डालो
API_SECRET = '4hLSUf6ZfS0mB13YE3pLKMkUIBpFL4gcPghoT9K2PL7tlLGR0o2NJKAdXaPJW4hJ'    # ←←← API Secret डालो

SAFE_MODE  = True                         # True = कोई असली ऑर्डर नहीं, सिर्फ प्रिंट
POSITION_SIZE = 0.001                     # उदाहरण: 0.001 BTC (quantity in BTC)

# EMA periods (तुम बदल सकते हो)
EMA_FAST = 9
EMA_SLOW = 21

# ===================== INITIALIZE EXCHANGE =====================
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',              # ← ये सबसे जरूरी
        'adjustForTimeDifference': True,
        'recvWindow': 10000,
    },
    # futures के लिए सही URL (ccxt कभी-कभी डिफॉल्ट में स्पॉट ले लेता है)
    'urls': {
        'api': {
            'fapiPublic': 'https://fapi.binance.com/fapi/v1',
            'fapiPrivate': 'https://fapi.binance.com/fapi/v1',
            'dapiPublic': 'https://dapi.binance.com/dapi/v1',   # अगर coin-margined चाहिए तो
            'dapiPrivate': 'https://dapi.binance.com/dapi/v1',
        }
    }
})

# टेस्ट के लिए प्रिंट कर लें
print("Exchange loaded:", exchange.id)
print("Default type:", exchange.options['defaultType'])

# ===================== HELPERS =====================
def fetch_candles():
    """
    Binance से latest OHLCV (candles) data लाता है।
    Returns:
        pd.DataFrame: OHLCV data with timestamp converted to datetime
    """
    try:
        ohlcv = exchange.fetch_ohlcv(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            limit=CANDLES_LIMIT
        )
        
        # list को DataFrame में बदलना
        df = pd.DataFrame(
            ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        
        # timestamp को readable datetime में बदलना
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # जरूरत पड़ने पर index भी timestamp कर सकते हो
        # df.set_index('timestamp', inplace=True)
        
        return df
    
    except Exception as e:
        print(f"Error fetching candles: {e}")
        return pd.DataFrame()  # खाली dataframe लौटाओ ताकि प्रोग्राम क्रैश न करे
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"[ERROR] Candles fetch failed: {e}")
        return None


def calculate_indicators(df):

    if len(df) < EMA_SLOW + 5:
        return None, None, None, None, None, None

    df['ema_fast'] = df['close'].ewm(span=EMA_FAST).mean()
    df['ema_slow'] = df['close'].ewm(span=EMA_SLOW).mean()

    delta = df['close'].diff()

    gain = (delta.where(delta > 0, 0)).rolling(RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(RSI_PERIOD).mean()

    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    current_price = df['close'].iloc[-1]

    ema_fast = df['ema_fast'].iloc[-1]
    ema_slow = df['ema_slow'].iloc[-1]

    prev_fast = df['ema_fast'].iloc[-2]
    prev_slow = df['ema_slow'].iloc[-2]

    rsi = df['rsi'].iloc[-1]

    return current_price, ema_fast, ema_slow, prev_fast, prev_slow, rsi


def get_signal(current_price, ema_fast, ema_slow, prev_ema_fast, prev_ema_slow):
    if ema_fast is None or prev_ema_fast is None:
        return "HOLD"
    
    # BUY: fast EMA slow के ऊपर क्रॉस करे
    if prev_ema_fast <= prev_ema_slow and ema_fast > ema_slow:
        return "BUY"
    
    # SELL: fast EMA slow के नीचे क्रॉस करे
    if prev_ema_fast >= prev_ema_slow and ema_fast < ema_slow:
        return "SELL"
    
    return "HOLD"

    signal = "BUY"

    if signal == "BUY":
        message = "📈 BUY Signal BTCUSDT"

        send_telegram(message)
        send_email("BUY Signal", message)


def place_order(action):
    """Market order प्लेस करने का फंक्शन"""
    if SAFE_MODE:
        print(f"[SAFE MODE] Would place {action} order → {POSITION_SIZE} {SYMBOL}")
        return

    print(f"REAL MODE: Placing {action} order for {POSITION_SIZE} {SYMBOL}")

    try:
        if action == "BUY":
            order = exchange.create_market_buy_order(SYMBOL, POSITION_SIZE)
            print(f"[ORDER] BUY executed: {order}")

        elif action == "SELL":
            order = exchange.create_market_sell_order(SYMBOL, POSITION_SIZE)
            print(f"[ORDER] SELL executed: {order}")

        else:
            print(f"[INVALID ACTION] Unknown action: {action}")

    except Exception as e:
        print(f"[ORDER ERROR] {e}")


# ==================== MAIN BOT LOOP ====================
# ================= MAIN BOT LOOP =================

def get_signal(current_price, ema_fast, ema_slow, prev_fast, prev_slow, rsi):

    if pd.isna(ema_fast) or pd.isna(ema_slow) or pd.isna(rsi):
        return "HOLD"

    cross_up = (prev_fast < prev_slow) and (ema_fast > ema_slow)
    cross_down = (prev_fast > prev_slow) and (ema_fast < ema_slow)

    if cross_up and rsi < RSI_BUY_BELOW:
        return "BUY"

    if cross_down and rsi > RSI_SELL_ABOVE:
        return "SELL"

    return "HOLD"


def start_bot():

    print("==== Binance Futures Trading Bot Started ====")
    print(f"Symbol: {SYMBOL} | Timeframe: {TIMEFRAME} | Safe Mode: {SAFE_MODE}")
    print(f"EMA Fast: {EMA_FAST} | EMA Slow: {EMA_SLOW}")
    print("Press Ctrl+C to stop")

    position = None
    entry_price = 0.0

    while True:

        try:

            df = fetch_candles()

            if df is None:
                time.sleep(10)
                continue

            current_price, ema_fast, ema_slow, prev_fast, prev_slow, rsi = calculate_indicators(df)

            if current_price is None:
                time.sleep(10)
                continue

            action = get_signal(current_price, ema_fast, ema_slow, prev_fast, prev_slow, rsi)

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"[{ts}] Price: {current_price:.2f} | EMA{EMA_FAST}:{ema_fast:.2f} | EMA{EMA_SLOW}:{ema_slow:.2f} | RSI:{rsi:.1f}")

            # BUY SIGNAL
            if action == "BUY" and position is None:

                print(f"→ BUY Signal @ {current_price:.2f}")

                if SAFE_MODE:
                    print("SAFE MODE - Order skipped")

                else:

                    qty = round((ORDER_USDT_AMOUNT * LEVERAGE) / current_price, 3)

                    order = client.futures_create_order(
                        symbol=SYMBOL,
                        side="BUY",
                        type="MARKET",
                        quantity=qty
                    )

                    print(f"BUY EXECUTED @ {current_price:.2f} | Qty: {qty}")

                    position = "LONG"
                    entry_price = current_price

                    sl_price = round(entry_price * (1 - STOP_LOSS_PCT / 100), 2)
                    tp_price = round(entry_price * (1 + TAKE_PROFIT_PCT / 100), 2)

                    # STOP LOSS
                    client.futures_create_order(
                        symbol=SYMBOL,
                        side="SELL",
                        type="STOP_MARKET",
                        stopPrice=sl_price,
                        closePosition=True
                    )

                    # TAKE PROFIT
                    client.futures_create_order(
                        symbol=SYMBOL,
                        side="SELL",
                        type="TAKE_PROFIT_MARKET",
                        stopPrice=tp_price,
                        closePosition=True
                    )

                    print(f"SL: {sl_price} | TP: {tp_price}")

            time.sleep(10)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(10)


if __name__ == "__main__":
    start_bot()
send_telegram("✅ Bot Running Alert Test")
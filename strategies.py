# strategies.py
# Trading strategies for the bot

from binance.client import Client
import pandas as pd
import talib

rsi = talib.RSI(close_prices, timeperiod=14)
sma = talib.SMA(close_prices, timeperiod=20)
macd, signal, hist = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)

class BaseStrategy:
    def __init__(self, client, symbol, interval):
        self.client = client
        self.symbol = symbol
        self.interval = interval

    def get_historical_data(self, limit=100):
        klines = self.client.get_klines(symbol=self.symbol, interval=self.interval, limit=limit)
        data = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        data['close'] = pd.to_numeric(data['close'])
        data['high'] = pd.to_numeric(data['high'])
        data['low'] = pd.to_numeric(data['low'])
        data['open'] = pd.to_numeric(data['open'])
        return data

class RSIStrategy(BaseStrategy):
    def generate_signal(self):
        data = self.get_historical_data()
        rsi = calculate_rsi(data)
        if rsi.iloc[-1] < 30:
            return 'buy'
        elif rsi.iloc[-1] > 70:
            return 'sell'
        return 'hold'

class MovingAverageCrossover(BaseStrategy):
    def generate_signal(self):
        data = self.get_historical_data()
        short_ma = calculate_ma(data, period=50, ma_type='sma')
        long_ma = calculate_ma(data, period=200, ma_type='sma')
        if short_ma.iloc[-1] > long_ma.iloc[-1] and short_ma.iloc[-2] <= long_ma.iloc[-2]:
            return 'buy'
        elif short_ma.iloc[-1] < long_ma.iloc[-1] and short_ma.iloc[-2] >= long_ma.iloc[-2]:
            return 'sell'
        return 'hold'

class MACDStrategy(BaseStrategy):
    def generate_signal(self):
        data = self.get_historical_data()
        macd, signal, _ = calculate_macd(data)
        if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
            return 'buy'
        elif macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
            return 'sell'
        return 'hold'

# Advanced strategy example: Combine RSI and MA
class AdvancedStrategy(BaseStrategy):
    def generate_signal(self):
        data = self.get_historical_data()
        rsi = calculate_rsi(data)
        short_ma = calculate_ma(data, period=50)
        long_ma = calculate_ma(data, period=200)
        
        if rsi.iloc[-1] < 30 and short_ma.iloc[-1] > long_ma.iloc[-1]:
            return 'buy'
        elif rsi.iloc[-1] > 70 and short_ma.iloc[-1] < long_ma.iloc[-1]:
            return 'sell'
        return 'hold'
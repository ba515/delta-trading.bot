# indicators.py
# Technical indicators for the trading bot

import pandas as pd
import numpy as np
import pandas_ta as ta # Assuming 'ta' library is installed for technical analysis

def calculate_rsi(data, period=14):
    """
    Calculate Relative Strength Index (RSI)
    :param data: DataFrame with 'close' column
    :param period: RSI period
    :return: Series with RSI values
    """
    return ta.momentum.RSIIndicator(data['close'], window=period).rsi()

def calculate_ma(data, period=20, ma_type='sma'):
    """
    Calculate Moving Average
    :param data: DataFrame with 'close' column
    :param period: MA period
    :param ma_type: 'sma' or 'ema'
    :return: Series with MA values
    """
    if ma_type == 'sma':
        return ta.trend.SMAIndicator(data['close'], window=period).sma_indicator()
    elif ma_type == 'ema':
        return ta.trend.EMAIndicator(data['close'], window=period).ema_indicator()
    else:
        raise ValueError("Invalid MA type")

def calculate_macd(data, fast=12, slow=26, signal=9):
    """
    Calculate MACD
    :param data: DataFrame with 'close' column
    :return: Tuple (macd, signal, histogram)
    """
    macd = ta.trend.MACD(data['close'], window_fast=fast, window_slow=slow, window_sign=signal)
    return macd.macd(), macd.macd_signal(), macd.macd_diff()

def calculate_bollinger_bands(data, period=20, std_dev=2):
    """
    Calculate Bollinger Bands
    :param data: DataFrame with 'close' column
    :param period: Period for calculation
    :param std_dev: Standard deviation multiplier
    :return: Tuple (upper, middle, lower)
    """
    bb = ta.volatility.BollingerBands(data['close'], window=period, window_dev=std_dev)
    return bb.bollinger_hband(), bb.bollinger_mavg(), bb.bollinger_lband()
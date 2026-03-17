# config.py
# Configuration file for the Delta Trading Bot

import os
from dotenv import load_dotenv  # नया इंपोर्ट
load_dotenv()  # .env फाइल लोड करो
# Binance API credentials (replace with your own)
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

# Trading parameters
SYMBOL = 'BTCUSDT'  # Default trading pair
INTERVAL = '1h'     # Candlestick interval
QUANTITY = 0.001    # Quantity to trade (in BTC for BTCUSDT)

# Risk management
STOP_LOSS_PERCENT = 0.02  # 2% stop loss
TAKE_PROFIT_PERCENT = 0.05  # 5% take profit

# Database or logging (if needed, e.g., for backtesting)
LOG_FILE = 'logs/bot.log'

# Dashboard settings (if using Flask or similar)
DASHBOARD_PORT = 5000
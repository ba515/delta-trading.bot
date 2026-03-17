import requests
import time
import asyncio
from datetime import datetime

# ------------------ अपनी डिटेल्स ------------------
TOKEN = "8633517801:AAFmmfCr70vGXnLo7BM80WmLujm6sYHaktE"
CHAT_ID = "554267515"

# क्रिप्टो लिस्ट (CoinGecko IDs)
COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "binancecoin": "BNB",
    "ripple": "XRP",
    "cardano": "ADA",
    "dogecoin": "DOGE",
    # और जोड़ सकते हो
}

async def send_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print(f"[{datetime.now()}] अलर्ट भेजा: {message}")
    else:
        print(f"Telegram एरर: {response.text}")

async def main_loop():
    last_change = {}  # पिछले % चेंज ट्रैक करने के लिए (रिपीट रोकने)

    while True:
        # सभी कॉइन्स एक साथ फेच (बैच में, रेट लिमिट बचाने के लिए)
        ids = ",".join(COINS.keys())
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids}&order=market_cap_desc&per_page=250&page=1&sparkline=true&price_change_percentage=24h"
        
        try:
            response = requests.get(url)
            data = response.json()
            
            if not isinstance(data, list):
                print("API रिस्पॉन्स लिस्ट नहीं है:", data)
                await asyncio.sleep(300)
                continue
            
            for coin in data:
                symbol = coin.get('symbol', '').upper()
                if symbol not in COINS.values():
                    continue
                
                current_price = coin.get('current_price', 0)
                high_24h = coin.get('high_24h', current_price)
                low_24h = coin.get('low_24h', current_price)
                price_change_24h = coin.get('price_change_percentage_24h', 0)
                
                breakout = current_price > high_24h * 1.005  # 0.5% ऊपर
                breakdown = current_price < low_24h * 0.995  # 0.5% नीचे
                
                alert_text = ""
                if breakout:
                    alert_text += f"🚀 {symbol} ब्रेकआउट! Price: ${current_price:.2f} (24h High ब्रेक)\n"
                if breakdown:
                    alert_text += f"🔴 {symbol} ब्रेकडाउन! Price: ${current_price:.2f} (24h Low ब्रेक)\n"
                
                # सिंपल RSI जैसा: 24h change से ओवरबॉट/ओवरसोल्ड अनुमान
                if symbol not in last_change:
                    last_change[symbol] = price_change_24h
                
                if price_change_24h > 10 and last_change[symbol] <= 10:
                    alert_text += f"⚠️ {symbol} तेज़ पंप! 24h Change: {price_change_24h:.1f}% → सेल?\n"
                elif price_change_24h < -10 and last_change[symbol] >= -10:
                    alert_text += f"🟢 {symbol} तेज़ डंप! 24h Change: {price_change_24h:.1f}% → बाय चांस?\n"
                
                if alert_text:
                    full_msg = f"🔔 क्रिप्टो अलर्ट ({datetime.now().strftime('%H:%M')})\n{alert_text}Current: ${current_price:.2f} | 24h: {price_change_24h:.1f}%"
                    await send_alert(full_msg)
                
                last_change[symbol] = price_change_24h
                
                print(f"{symbol}: ${current_price:.2f} | 24h: {price_change_24h:.1f}%")
        
        except Exception as e:
            print(f"API एरर: {e}")
        
        print("--- 5 मिनट वेट... ---")
        await asyncio.sleep(300)  # 5 मिनट

if __name__ == "__main__":
    asyncio.run(main_loop())
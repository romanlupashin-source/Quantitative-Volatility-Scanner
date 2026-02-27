import yfinance as yf
import pandas as pd
import requests
import time
from colorama import Fore, init
from datetime import datetime
import pytz

init(autoreset=True)

# КЛЮЧИ ТЕЛЕГРАМ
TG_TOKEN = "8478161813:AAHQQr7jK16wWFB4Hx5aiIW56Sy1AdCT_pk"
TG_CHAT_ID = "ВСТАВЬ_СЮДА_СВОЙ_CHAT_ID" # <--- РОМАН, НЕ ЗАБУДЬ ВСТАВИТЬ СВОИ ЦИФРЫ!

# НАСТРОЙКИ
TICKERS = ["BTC-USD", "ETH-USD", "NVAX", "TSLA", "AAPL"] 
MIN_MOVE_PCT = 2.0 

# ПАМЯТЬ БОТА
positions = {} 

def send_telegram(text):
    """Отправка сообщений в Telegram"""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(Fore.RED + f"Ошибка отправки в TG: {e}")

def analyze_ticker(ticker):
    """Мозг бота с памятью позиций: Покупка -> Продажа"""
    global positions 
    
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d", interval="5m")
        if len(df) < 2: return

        current_price = df['Close'].iloc[-1]
        open_price = df['Open'].iloc[0]
        pct_change = ((current_price - open_price) / open_price) * 100
        
        volume_today = df['Volume'].sum()
        if volume_today * current_price < 100000: return

        if ticker not in positions:
            if pct_change <= -MIN_MOVE_PCT: 
                positions[ticker] = current_price 
                msg = f"🟢 *ПОКУПКА {ticker}*\nЦена: ${current_price:.2f}\nПричина: Просадка {pct_change:.2f}%"
                print(Fore.GREEN + f"BUY {ticker}")
                send_telegram(msg)
                
        else:
            buy_price = positions[ticker]
            profit_pct = ((current_price - buy_price) / buy_price) * 100
            
            if profit_pct >= 2.0 or profit_pct <= -1.0:
                del positions[ticker] 
                emoji = "🚀" if profit_pct > 0 else "🔻"
                msg = f"{emoji} *ПРОДАЖА {ticker}*\nЦена: ${current_price:.2f}\nИтог: {profit_pct:.2f}%"
                print(Fore.YELLOW + f"SELL {ticker}")
                send_telegram(msg)

    except Exception as e:
        print(Fore.RED + f"Ошибка {ticker}: {e}")

if __name__ == "__main__":
    print(Fore.CYAN + "Бот запущен. Умный сканер с памятью позиций активирован...")
    send_telegram("✅ Бот запущен в облаке. Мониторинг начался.")
    
    while True:
        for ticker in TICKERS:
            analyze_ticker(ticker)
        
        now = datetime.now().strftime("%H:%M:%S")
        print(Fore.BLUE + f"[{now}] Цикл завершен. Ожидание 5 минут...")
        time.sleep(300)

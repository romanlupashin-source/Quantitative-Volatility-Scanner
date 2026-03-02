import yfinance as yf
import asyncio
from telegram import Bot
import pandas as pd

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = '8478161813:AAHQQr7jK16wWFB4Hx5aiIW56Sy1AdCT_pk'
CHAT_ID = '6935198093'
bot = Bot(token=TELEGRAM_TOKEN)

# Параметры поиска
MAX_PRICE = 15.0
MIN_VOLUME = 500000  # Ищем акции, которые реально торгуются
VOLATILITY_THRESHOLD = 1.5 # Сигнал, если прыгнула на 1.5% за минуту

# База тикеров для сканирования (добавь сюда побольше "мусора")
SCAN_LIST = ['BNAI', 'TIRX', 'JEM', 'LBGJ', 'KIDZ', 'TPET', 'BURU', 'SABR', 'BATL', 'VEEA', 'JPM', 'TSLA']

async def send_signal(message):
    print(f"Сигнал: {message}")
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка ТГ: {e}")

def analyze_ticker(ticker):
    try:
        # Изменяем period на '1d', чтобы получить минутные свечи за сегодня
        df = yf.download(ticker, period='1d', interval='1m', progress=False)
        
        # Нам нужны только последние несколько минут
        if df.empty or len(df) < 2: 
            return None
        
        last_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        change = ((last_price - prev_price) / prev_price) * 100
        volume = df['Volume'].iloc[-1]

        # Фильтр по цене и волатильности
        if last_price <= MAX_PRICE and abs(change) >= VOLATILITY_THRESHOLD:
            return {
                'ticker': ticker,
                'price': last_price,
                'change': change,
                'volume': volume
            }
    except Exception as e:
        # Печатаем ошибку для отладки, если нужно
        # print(f"Ошибка при анализе {ticker}: {e}")
        return None
    return None

# Словарь для хранения времени последнего сигнала по тикерам
import time
last_signals = {}

async def monitor():
    print("🚀 Авто-сканер запущен. Ищу цели...")
    while True:
        for ticker in SCAN_LIST:
            res = analyze_ticker(ticker)
            
            if res:
                current_time = time.time()
                # Проверяем, слали ли мы этот тикер в последние 15 минут (900 секунд)
                if ticker not in last_signals or (current_time - last_signals[ticker]) > 900:
                    
                    emoji = "🚀 BUY (LONG)" if res['change'] > 0 else "📉 SELL (SHORT)"
                    target = res['price'] * 1.04 if res['change'] > 0 else res['price'] * 0.96
                    
                    msg = (
                        f"🎯 **НАШЕЛ ЦЕЛЬ: {res['ticker']}**\n"
                        f"Действие: {emoji}\n"
                        f"💰 Цена: ${res['price']:.2f}\n"
                        # ... остальной текст сообщения ...
                    )
                    
                    await send_signal(msg)
                    last_signals[ticker] = current_time # Запоминаем время отправки
            
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(monitor())

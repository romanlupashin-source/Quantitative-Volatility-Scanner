import yfinance as yf
import asyncio
from telegram import Bot
import pandas as pd

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = 'ТВОЙ_ТОКЕН_БОТА'
CHAT_ID = 'ТВОЙ_CHAT_ID'
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
        # Получаем данные за последние 5 минут с интервалом 1м
        df = yf.download(ticker, period='5m', interval='1m', progress=False)
        if len(df) < 2: return None
        
        last_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        change = ((last_price - prev_price) / prev_price) * 100
        volume = df['Volume'].iloc[-1]

        # Фильтр: цена до $15 и резкий скачок/падение
        if last_price <= MAX_PRICE and abs(change) >= VOLATILITY_THRESHOLD:
            return {
                'ticker': ticker,
                'price': last_price,
                'change': change,
                'volume': volume
            }
    except:
        return None
    return None

async def monitor():
    print("🚀 Авто-сканер запущен. Ищу цели...")
    while True:
        for ticker in SCAN_LIST:
            res = analyze_ticker(ticker)
            if res:
                emoji = "🚀 BUY (LONG)" if res['change'] > 0 else "📉 SELL (SHORT)"
                target = res['price'] * 1.04 if res['change'] > 0 else res['price'] * 0.96
                
                msg = (
                    f"🎯 **НАШЕЛ ЦЕЛЬ: {res['ticker']}**\n"
                    f"Действие: {emoji}\n"
                    f"💰 Цена: ${res['price']:.2f}\n"
                    f"📊 Изменение: {res['change']:+.2f}%\n"
                    f"🌊 Объем: {res['volume']}\n"
                    f"---------------------------\n"
                    f"🏁 Цель (Limit): ${target:.2f}\n"
                    f"⚠️ *Действуй быстро, задержка 20 мин!*"
                )
                await send_signal(msg)
            
        await asyncio.sleep(60) # Проверка каждую минуту

if __name__ == "__main__":
    asyncio.run(monitor())

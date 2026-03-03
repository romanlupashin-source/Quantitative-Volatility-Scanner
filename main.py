import yfinance as yf
import asyncio
from telegram import Bot
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = '8478161813:AAHQQr7jK16wWFB4Hx5aiIW56Sy1AdCT_pk'
CHAT_ID = '6935198093'
bot = Bot(token=TELEGRAM_TOKEN)

MAX_PRICE = 15.0
MIN_VOLUME = 500000
VOLATILITY_THRESHOLD = 1.5

SCAN_LIST = ['BNAI', 'TIRX', 'JEM', 'LBGJ', 'KIDZ', 'TPET', 'BURU', 'SABR', 'BATL', 'VEEA', 'JPM', 'TSLA']

# Словари для памяти бота
last_signals = {}  # Время последнего сигнала
active_trades = {} # Слежение за открытыми позициями {тикер: {'price': цена, 'time': время}}

async def send_signal(message):
    print(f"Отправка: {message}")
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка ТГ: {e}")

def get_ny_time():
    return datetime.now(pytz.timezone('America/New_York'))

def is_market_open():
    now = get_ny_time()
    if now.weekday() > 4: return False # Выходные
    start = now.replace(hour=9, minute=30, second=0)
    end = now.replace(hour=16, minute=0, second=0)
    return start <= now <= end

def analyze_ticker(ticker):
    try:
        df = yf.download(ticker, period='1d', interval='1m', progress=False)
        if df.empty or len(df) < 2: return None
        
        last_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        change = ((last_price - prev_price) / prev_price) * 100
        volume = int(df['Volume'].iloc[-1])

        if last_price <= MAX_PRICE and abs(change) >= VOLATILITY_THRESHOLD:
            return {'ticker': ticker, 'price': last_price, 'change': change, 'volume': volume}
    except:
        return None
    return None

async def monitor():
    print("🚀 Робот-скальпер запущен.")
    alert_sent = False

    while True:
        now = get_ny_time()
        
        # 1. Проверка на "за 10 минут до открытия"
        if now.hour == 9 and now.minute == 20 and not alert_sent:
            await send_signal("🔔 **ВНИМАНИЕ!** До открытия биржи 10 минут. Проверь баланс в симуляторе!")
            alert_sent = True
        if now.hour == 9 and now.minute == 31: # Сброс флага после открытия
            alert_sent = False

        # 2. Если биржа закрыта — спим
        if not is_market_open():
            # Ночью проверяем раз в 5 минут, чтобы не нагружать систему
            await asyncio.sleep(300)
            continue

        # 3. Основной цикл сканирования
        for ticker in SCAN_LIST:
            res = analyze_ticker(ticker)
            curr_ts = time.time()
            
            # --- ЛОГИКА ВХОДА ---
            if res:
                # Если по тикеру не было сигналов последние 15 мин
                if ticker not in last_signals or (curr_ts - last_signals[ticker]) > 900:
                    emoji = "🚀 BUY" if res['change'] > 0 else "📉 SHORT"
                    msg = (
                        f"🎯 **ЦЕЛЬ НАЙДЕНА: {res['ticker']}**\n"
                        f"Действие: {emoji}\n"
                        f"💰 Цена входа: ${res['price']:.2f}\n"
                        f"📈 Скачок: {res['change']:+.2f}%\n"
                        f"⚠️ *Через 30 мин я проверю эту сделку!*"
                    )
                    await send_signal(msg)
                    last_signals[ticker] = curr_ts
                    # Запоминаем сделку для проверки через 30 мин
                    active_trades[ticker] = {'entry_price': res['price'], 'entry_time': curr_ts}

            # --- ЛОГИКА ПРОВЕРКИ ЧЕРЕЗ 30 МИНУТ ---
            if ticker in active_trades:
                trade = active_trades[ticker]
                # Если прошло 30 минут (1800 секунд)
                if curr_ts - trade['entry_time'] >= 1800:
                    # Получаем текущую цену для проверки
                    df_check = yf.download(ticker, period='1d', interval='1m', progress=False)
                    if not df_check.empty:
                        current_p = float(df_check['Close'].iloc[-1])
                        profit = ((current_p - trade['entry_price']) / trade['entry_price']) * 100
                        
                        if profit > 1.0:
                            status = f"✅ **ФИКСИРУЙ ПРИБЫЛЬ!**\nРост: +{profit:.2f}%"
                        elif profit < -1.0:
                            status = f"❌ **ОТМЕНА / ВЫХОД!**\nЦена пошла вниз: {profit:.2f}%"
                        else:
                            status = f"⏳ **ВРЕМЯ ВЫШЛО.**\nЦена почти не изменилась ({profit:+.2f}%). Лучше выйти и искать новое."
                        
                        await send_signal(f"📢 **ОТЧЕТ ПО {ticker}:**\n{status}\nЦена была: ${trade['entry_price']:.2f}\nЦена сейчас: ${current_p:.2f}")
                        del active_trades[ticker] # Убираем из слежки

        await asyncio.sleep(60) # Пауза 1 минута между циклами

if __name__ == "__main__":
    asyncio.run(monitor())

import yfinance as yf
import asyncio
from telegram import Bot
import pandas as pd
from datetime import datetime
import pytz
import time

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = '8478161813:AAHQQr7jK16wWFB4Hx5aiIW56Sy1AdCT_pk'
CHAT_ID = '6935198093'
bot = Bot(token=TELEGRAM_TOKEN)

MAX_PRICE = 15.0
VOLATILITY_THRESHOLD = 1.5
SCAN_LIST = ['BNAI', 'TIRX', 'JEM', 'LBGJ', 'KIDZ', 'TPET', 'BURU', 'SABR', 'BATL', 'VEEA', 'JPM', 'TSLA']

last_signals = {}  # Память для анти-спама
active_trades = {} # Слежение за сделками для проверки через 30 мин

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
    if now.weekday() > 4: return False
    # Рынок США: 09:30 - 16:00
    start = now.replace(hour=9, minute=30, second=0, microsecond=0)
    end = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return start <= now <= end

def analyze_ticker(ticker):
    try:
        df = yf.download(ticker, period='1d', interval='1m', progress=False)
        if df.empty or len(df) < 2: return None
        
        # Исправляем FutureWarning: переводим в numpy массив
        closes = df['Close'].to_numpy()
        volumes = df['Volume'].to_numpy()
        
        last_price = float(closes[-1])
        prev_price = float(closes[-2])
        change = ((last_price - prev_price) / prev_price) * 100
        volume = int(volumes[-1])

        if last_price <= MAX_PRICE and abs(change) >= VOLATILITY_THRESHOLD:
            return {'ticker': ticker, 'price': last_price, 'change': change, 'volume': volume}
    except:
        return None
    return None

# ... (начало кода остается прежним) ...

async def monitor():
    print("🚀 Робот-скальпер запущен.")
    while True:
        now = get_ny_time()
        curr_ts = time.time()

        # (Блок с проверкой работы рынка...)

        for ticker in SCAN_LIST:
            res = analyze_ticker(ticker)
            
            # --- 1. ПРОВЕРКА ТЕКУЩИХ СДЕЛОК (Динамическая) ---
            if ticker in active_trades:
                trade = active_trades[ticker]
                # Получаем текущую цену для экстренной проверки
                df_check = yf.download(ticker, period='1d', interval='1m', progress=False)
                if not df_check.empty:
                    current_p = float(df_check['Close'].to_numpy()[-1])
                    diff = ((current_p - trade['entry_price']) / trade['entry_price']) * 100
                    
                    # ЭКСТРЕННЫЙ ВЫХОД (если цена упала больше чем на 2% от входа)
                    if diff < -2.0:
                        await send_signal(f"⚠️ **ЭКСТРЕННАЯ ОТМЕНА: {ticker}**\nЦена падает слишком быстро! Выходи сейчас.\nУбыток: {diff:.2f}%")
                        del active_trades[ticker]
                        continue # Пропускаем анализ новых сигналов для этого тикера на этом круге

                    # ПЛАНОВАЯ ПРОВЕРКА (через 30 минут)
                    if curr_ts - trade['time'] >= 1800:
                        status = "✅ ПРИБЫЛЬ" if diff > 1.0 else "❌ ВЫХОДИ"
                        await send_signal(f"📢 **ОТЧЕТ ПО {ticker} (30 мин):**\n{status}: {diff:.2f}%\nЗакрывай сделку, прежде чем открывать шорт.")
                        del active_trades[ticker]

            # --- 2. ЛОГИКА НОВЫХ СИГНАЛОВ ---
            if res:
                # Если уже есть активная сделка по этому тикеру — новые сигналы ИГНОРИРУЕМ
                if ticker in active_trades:
                    continue

                if ticker not in last_signals or (curr_ts - last_signals[ticker]) > 900:
                    # Предлагаем шорт только если нет активного лонга
                    emoji = "🚀 BUY" if res['change'] > 0 else "📉 SHORT"
                    msg = (
                        f"🎯 **ЦЕЛЬ: {res['ticker']}**\n"
                        f"Действие: {emoji}\n"
                        f"💰 Цена: ${res['price']:.2f}\n"
                        f"📈 Скачок: {res['change']:+.2f}%\n"
                        f"⏳ Я слежу за ней, сообщу если что-то пойдет не так!"
                    )
                    await send_signal(msg)
                    last_signals[ticker] = curr_ts
                    active_trades[ticker] = {'entry_price': res['price'], 'time': curr_ts}

        await asyncio.sleep(60)
        
if __name__ == "__main__":
    asyncio.run(monitor())

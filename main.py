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

async def monitor():
    print("🚀 Скрипт запущен. Жду торговую сессию...")
    alert_10m_sent = False

    while True:
        now = get_ny_time()
        curr_ts = time.time()

        # 1. Уведомление за 10 минут до открытия (в 09:20 по NY)
        if now.hour == 9 and now.minute == 20 and not alert_10m_sent:
            await send_signal("🔔 **ЧЕРЕЗ 10 МИНУТ ОТКРЫТИЕ!** Готовь Buying Power в симуляторе.")
            alert_10m_sent = True
        
        # Сброс флага уведомления в конце дня
        if now.hour == 16: alert_10m_sent = False

        # 2. Если биржа закрыта — спим
        if not is_market_open():
            await asyncio.sleep(60)
            continue

        # 3. Активная фаза: сканируем тикеры
        for ticker in SCAN_LIST:
            res = analyze_ticker(ticker)
            
            if res:
                # Анти-спам: не чаще чем раз в 15 минут
                if ticker not in last_signals or (curr_ts - last_signals[ticker]) > 900:
                    emoji = "🚀 BUY" if res['change'] > 0 else "📉 SHORT"
                    msg = (
                        f"🎯 **ЦЕЛЬ: {res['ticker']}**\n"
                        f"Действие: {emoji}\n"
                        f"💰 Цена входа: ${res['price']:.2f}\n"
                        f"📊 Изменение: {res['change']:+.2f}%\n"
                        f"⏳ Проверю через 30 минут!"
                    )
                    await send_signal(msg)
                    last_signals[ticker] = curr_ts
                    active_trades[ticker] = {'entry_price': res['price'], 'time': curr_ts}

            # 4. Проверка сделки через 30 минут
            if ticker in active_trades:
                trade = active_trades[ticker]
                if curr_ts - trade['time'] >= 1800: # 30 минут
                    df_check = yf.download(ticker, period='1d', interval='1m', progress=False)
                    if not df_check.empty:
                        current_p = float(df_check['Close'].to_numpy()[-1])
                        diff = ((current_p - trade['entry_price']) / trade['entry_price']) * 100
                        
                        if diff > 1.0:
                            status = f"✅ **ПРИБЫЛЬ: {diff:.2f}%** — Фиксируй!"
                        elif diff < -1.0:
                            status = f"❌ **УБЫТОК: {diff:.2f}%** — Выходи!"
                        else:
                            status = f"⏳ **СТОЯК: {diff:+.2f}%** — Закрывай, нет движения."
                        
                        await send_signal(f"📢 **ОТЧЕТ ПО {ticker}** (через 30м):\n{status}\nВход: ${trade['entry_price']:.2f} -> Сейчас: ${current_p:.2f}")
                        del active_trades[ticker]

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(monitor())

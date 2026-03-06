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

MAX_PRICE = 60.0  # Поднял до 60, чтобы бот видел BNAI и GO
VOLATILITY_THRESHOLD = 1.5

# Список тикеров, распределенный по категориям
tickers_to_watch = {
    "top_gainers": ["SOC", "TNGX", "AMPX", "TTD", "BVC"],
    "high_volume": ["NVDA", "PLUG", "ONDS", "INTC"],
    "penny_stocks": ["GXAI", "HCTI", "XPON", "BITF"],
    "sniper_list": ["GO", "NPT", "AARD", "SHMD", "BFLY"] # Исправлено здесь
}

# Автоматическое формирование списка для сканирования
SCAN_LIST = list(set(
    tickers_to_watch["top_gainers"] + 
    tickers_to_watch["high_volume"] + 
    tickers_to_watch["penny_stocks"] + 
    tickers_to_watch["sniper_list"] + 
    ["BNAI", "JEM", "TPET", "BATL", "VEEA"]
))

last_signals = {}  
active_trades = {} 

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
    start = now.replace(hour=9, minute=30, second=0, microsecond=0)
    end = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return start <= now <= end

def analyze_ticker(ticker):
    try:
        # Убрали progress=False для чистоты логов
        df = yf.download(ticker, period='1d', interval='1m', progress=False)
        if df.empty or len(df) < 2: return None
        
        closes = df['Close'].to_numpy()
        volumes = df['Volume'].to_numpy()
        
        last_price = float(closes[-1])
        prev_price = float(closes[-2])
        change = ((last_price - prev_price) / prev_price) * 100
        volume = int(volumes[-1])

        # Фильтр по цене и волатильности
        if last_price <= MAX_PRICE and abs(change) >= VOLATILITY_THRESHOLD:
            return {'ticker': ticker, 'price': last_price, 'change': change, 'volume': volume}
    except Exception as e:
        return None
    return None

async def monitor():
    print(f"🚀 Робот-скальпер запущен. В списке {len(SCAN_LIST)} тикеров.")
    alert_10m_sent = False

    while True:
        now = get_ny_time()
        curr_ts = time.time()

        # Будильник перед открытием
        if now.hour == 9 and now.minute == 20 and not alert_10m_sent:
            await send_signal("🔔 **ЧЕРЕЗ 10 МИНУТ ОТКРЫТИЕ!** Готовь Buying Power.")
            alert_10m_sent = True
        if now.hour == 16: alert_10m_sent = False

        if not is_market_open():
            # Если рынок закрыт, проверяем раз в минуту
            await asyncio.sleep(60)
            continue

        for ticker in SCAN_LIST:
            # 1. Сначала проверяем активные сделки
            if ticker in active_trades:
                trade = active_trades[ticker]
                res_check = analyze_ticker(ticker)
                
                if res_check:
                    current_p = res_check['price']
                    diff = ((current_p - trade['entry_price']) / trade['entry_price']) * 100
                    
                    # ЭКСТРЕННЫЙ STOP-LOSS (для Лонга) или TAKE-PROFIT (для Шорта)
                    # Если цена пошла против нас на 2.5%
                    if diff < -2.5: 
                        await send_signal(f"⚠️ **ALARM: {ticker}**\nЦена ушла не туда: {diff:.2f}%\nРекомендую закрыть позицию в симуляторе.")
                        del active_trades[ticker]
                        continue

                    # ПЛАНОВАЯ ПРОВЕРКА (30 минут)
                    if curr_ts - trade['time'] >= 1800:
                        status = "✅ В ПЛЮСЕ" if diff > 0.5 else "❌ В ПРЕСНОЙ ВОДЕ / МИНУСЕ"
                        await send_signal(f"📢 **ОТЧЕТ ПО {ticker} (30 мин):**\n{status}: {diff:.2f}%\nОрдер можно закрывать или переставлять.")
                        del active_trades[ticker]
                continue 

            # 2. Поиск новых сигналов
            res = analyze_ticker(ticker)
            if res:
                if ticker not in last_signals or (curr_ts - last_signals[ticker]) > 900:
                    action = "🚀 BUY" if res['change'] > 0 else "📉 SHORT"
                    
                    msg = (
                        f"🎯 **ЦЕЛЬ: {res['ticker']}**\n"
                        f"Действие: {action}\n"
                        f"💰 Вход: ${res['price']:.2f}\n"
                        f"📈 Импульс: {res['change']:+.2f}%\n"
                        f"📊 Объем: {res['volume']}"
                    )
                    await send_signal(msg)
                    last_signals[ticker] = curr_ts
                    active_trades[ticker] = {'entry_price': res['price'], 'time': curr_ts}

        # Пауза между циклами сканирования всего списка
        await asyncio.sleep(30) # 30 секунд - оптимально, чтобы не забанили IP на yfinance
        
if __name__ == "__main__":
    asyncio.run(monitor())

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

MAX_PRICE = 60.0  
VOLATILITY_THRESHOLD = 0.5  # Сверхчувствительность: ловим микродвижения
LOOP_INTERVAL = 10          # Частота опроса: каждые 10 секунд
ANTISPAM_TIME = 120         # Повторный сигнал по той же акции через 2 минуты

# Список тикеров
tickers_to_watch = {
    "top_gainers": ["SOC", "TNGX", "AMPX", "TTD", "BVC"],
    "high_volume": ["NVDA", "PLUG", "ONDS", "INTC"],
    "penny_stocks": ["GXAI", "HCTI", "XPON", "BITF"],
    "sniper_list": ["GO", "NPT", "AARD", "SHMD", "BFLY"]
}

SCAN_LIST = list(set(
    tickers_to_watch["top_gainers"] + 
    tickers_to_watch["high_volume"] + 
    tickers_to_watch["penny_stocks"] + 
    tickers_to_watch["sniper_list"] + 
    ["BNAI", "JEM", "TPET", "BATL", "VEEA", "AGL", "AIFF", "TURB"]
))

last_signals = {}  
active_trades = {} 

async def send_signal(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Отправка в TG...")
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
        # Загружаем данные за 1 день с минутным интервалом
        df = yf.download(ticker, period='1d', interval='1m', progress=False)
        if df.empty or len(df) < 2: return None
        
        closes = df['Close'].to_numpy()
        volumes = df['Volume'].to_numpy()
        
        last_price = float(closes[-1])
        prev_price = float(closes[-2])
        change = ((last_price - prev_price) / prev_price) * 100
        volume = int(volumes[-1])

        # Фильтр: цена до 60$ и изменение от 0.5% за минуту
        if last_price <= MAX_PRICE and abs(change) >= VOLATILITY_THRESHOLD:
            return {'ticker': ticker, 'price': last_price, 'change': change, 'volume': volume}
    except:
        return None
    return None

async def monitor():
    print(f"🔥 Режим 'Снайпер' активирован. Интервал: {LOOP_INTERVAL}с, Порог: {VOLATILITY_THRESHOLD}%")
    print(f"Сканирую {len(SCAN_LIST)} тикеров...")
    
    alert_10m_sent = False

    while True:
        now = get_ny_time()
        curr_ts = time.time()

        if not is_market_open():
            print("💤 Рынок закрыт. Жду открытия...")
            await asyncio.sleep(60)
            continue

        for ticker in SCAN_LIST:
            # 1. Проверка активных сделок
            if ticker in active_trades:
                trade = active_trades[ticker]
                res_check = analyze_ticker(ticker)
                
                if res_check:
                    current_p = res_check['price']
                    diff = ((current_p - trade['entry_price']) / trade['entry_price']) * 100
                    
                    if diff < -2.5: 
                        await send_signal(f"⚠️ **STOP-LOSS ALERT: {ticker}**\nПросадка: {diff:.2f}%\nСрочно проверь ордер!")
                        del active_trades[ticker]
                        continue

                    if curr_ts - trade['time'] >= 1800:
                        status = "✅ ПРОФИТ" if diff > 0.5 else "⏳ СТАГНАЦИЯ"
                        await send_signal(f"📢 **ОТЧЕТ (30 мин) по {ticker}:**\nРезультат: {diff:.2f}%\nПозиция свободна.")
                        del active_trades[ticker]
                continue 

            # 2. Поиск новых сигналов
            res = analyze_ticker(ticker)
            if res:
                # Анти-спам 2 минуты
                if ticker not in last_signals or (curr_ts - last_signals[ticker]) > ANTISPAM_TIME:
                    action = "🚀 BUY" if res['change'] > 0 else "📉 SHORT"
                    
                    msg = (
                        f"🎯 **ЦЕЛЬ: {res['ticker']}**\n"
                        f"Действие: {action}\n"
                        f"💰 Цена: ${res['price']:.2f}\n"
                        f"⚡ Импульс: {res['change']:+.2f}%\n"
                        f"📊 Объем: {res['volume']}"
                    )
                    await send_signal(msg)
                    last_signals[ticker] = curr_ts
                    active_trades[ticker] = {'entry_price': res['price'], 'time': curr_ts}

        # Боевая пауза
        await asyncio.sleep(LOOP_INTERVAL)

if __name__ == "__main__":
    asyncio.run(monitor())

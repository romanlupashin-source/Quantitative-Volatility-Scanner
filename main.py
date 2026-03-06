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
# Список тикеров, распределенный по категориям
tickers_to_watch = {
    # ЛИДЕРЫ РОСТА (High Momentum) - те, кто дает иксы сегодня
    "top_gainers": [
        "SOC",   # Sable Offshore (Энергетика, +37%)
        "TNGX",  # Tango Therapeutics (Биотех, +36%)
        "AMPX",  # Amprius Tech (Батареи, +18%)
        "TTD",   # The Trade Desk (Реклама, +18%)
        "BVC",   # BitVentures (Крипто-связанные, +18%)
    ],

    # САМЫЕ АКТИВНЫЕ (High Volume) - высокая ликвидность
    "high_volume": [
        "NVDA",  # NVIDIA (Лидер рынка)
        "PLUG",  # Plug Power (Сильная волатильность)
        "ONDS",  # Ondas Holdings
        "INTC",  # Intel (Восстановление)
    ],

    # ПЕРСПЕКТИВНЫЕ МАЛОЦЕНКИ (Penny Stocks / High Risk)
    "penny_stocks": [
        "GXAI",  # Gaxos AI (ИИ-гейминг)
        "HCTI",  # Healthcare Triangle (Медицина)
        "XPON",  # Expion360
        "BITF",  # Bitfarms (Майнинг биткоина)
    ]
}

# Если тебе нужен простой список всех тикеров сразу для цикла:
SCAN_LIST = [
    "SOC", "TNGX", "AMPX", "TTD", "BVC", "NVDA", "PLUG", "ONDS", 
    "INTC", "GXAI", "HCTI", "XPON", "BITF", "BNAI", "JEM", 
    "LBGJ", "KIDZ", "TPET", "BURU", "SABR", "BATL", "VEEA", "JPM", "TSLA"
]

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
    print("🚀 Робот-скальпер перенастроен. Жду сигналов...")
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
            await asyncio.sleep(60)
            continue

        for ticker in SCAN_LIST:
            res = analyze_ticker(ticker)
            
            # --- 1. ПРОВЕРКА ТЕКУЩИХ СДЕЛКИ (Динамическая) ---
            if ticker in active_trades:
                trade = active_trades[ticker]
                df_check = yf.download(ticker, period='1d', interval='1m', progress=False)
                
                if not df_check.empty:
                    current_p = float(df_check['Close'].to_numpy()[-1])
                    diff = ((current_p - trade['entry_price']) / trade['entry_price']) * 100
                    
                    # ЭКСТРЕННАЯ ОТМЕНА (Stop-Loss)
                    if diff < -2.5: # Если упало более чем на 2.5% от покупки
                        await send_signal(f"⚠️ **ОТМЕНА ПО {ticker}!**\nЦена рухнула на {diff:.2f}%. Немедленно закрой или удали ордер в симуляторе!")
                        del active_trades[ticker]
                        continue

                    # ПЛАНОВАЯ ПРОВЕРКА (30 минут)
                    if curr_ts - trade['time'] >= 1800:
                        status = "✅ ПРИБЫЛЬ" if diff > 1.0 else "❌ ВЫХОДИ (НЕТ РОСТА)"
                        await send_signal(f"📢 **ОТЧЕТ ПО {ticker} (30 мин):**\n{status}: {diff:.2f}%\nТеперь можешь рассматривать новые сигналы по этой акции.")
                        del active_trades[ticker]
                continue # Пока сделка активна, новые сигналы по этому тикеру не смотрим

            # --- 2. ПОИСК НОВЫХ СИГНАЛОВ ---
            if res:
                # Если за последние 15 минут уже был сигнал — молчим (анти-спам)
                if ticker not in last_signals or (curr_ts - last_signals[ticker]) > 900:
                    
                    # Если изменение положительное — только BUY, если отрицательное — только SHORT
                    action = "🚀 BUY" if res['change'] > 0 else "📉 SHORT"
                    
                    msg = (
                        f"🎯 **ЦЕЛЬ: {res['ticker']}**\n"
                        f"Действие: {action}\n"
                        f"💰 Цена входа: ${res['price']:.2f}\n"
                        f"📈 Движение: {res['change']:+.2f}%\n"
                        f"🛡️ *Я слежу за ценой. Сообщу, если нужно будет отменить!*"
                    )
                    await send_signal(msg)
                    last_signals[ticker] = curr_ts
                    active_trades[ticker] = {'entry_price': res['price'], 'time': curr_ts}

        await asyncio.sleep(60)
        
if __name__ == "__main__":
    asyncio.run(monitor())

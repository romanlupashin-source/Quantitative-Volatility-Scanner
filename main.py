import yfinance as yf
import telebot
import requests
import pandas as pd
import time
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
TOKEN = '8478161813:AAHQQr7jK16wWFB4Hx5aiIW56Sy1AdCT_pk'
CHAT_ID = '6935198093'
bot = telebot.TeleBot(TOKEN)

START_BALANCE = 100000.0
current_balance = START_BALANCE
positions = {} # { 'TICKER': {'price': 0.0, 'qty': 0} }

# Настройки времени (Твоё местное время после sudo timedatectl)
WORK_START = 10 
WORK_END = 23   

# Настройки стратегии
VOLATILITY_THRESHOLD = 0.4  # Сигнал при изменении > 0.4% за минуту
SCAN_INTERVAL = 15          # Проверка каждые 15 секунд

# --- ФУНКЦИИ МОЗГА ---

def get_volatile_tickers():
    """Сканирует рынок на самые активные акции (Top Gainers/Most Active)"""
    try:
        # Берем список самых активных акций с Yahoo Finance
        url = "https://finance.yahoo.com/markets/stocks/most-active/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        tables = pd.read_html(response.text)
        df = tables[0]
        
        # Берем тикеры и фильтруем по объему (Volume > 1,000,000)
        # Это поможет обходить лимит симулятора в 0.10% дневного объема
        df['Avg Vol (3 month)'] = pd.to_numeric(df['Avg Vol (3 month)'].astype(str).str.replace('M', '000000').str.replace('B', '000000000'), errors='coerce')
        
        top_tickers = df['Symbol'].head(30).tolist()
        
        # Твои "ручные" ракеты (Penny Stocks из портфеля лидера)
        manual_list = ["BNAI", "MRNO", "RMSG", "MARA", "RIOT", "TQQQ", "SOXL", "NVDA", "TSLA"]
        
        return list(set(top_tickers + manual_list))
    except Exception as e:
        print(f"⚠️ Ошибка сбора тикеров: {e}")
        return ["TSLA", "NVDA", "MARA", "TQQQ", "AAPL", "BNAI"]

def send_telegram_signal(ticker, action, price, change):
    """Отправка красивого уведомления в ТГ"""
    emoji = "🚀" if "BUY" in action else "⚠️"
    msg = (
        f"{emoji} **СИГНАЛ: {action} {ticker}**\n"
        f"📈 Изменение: {change:+.2f}%\n"
        f"💵 Цена (Real-time): ${price:.2f}\n"
        f"⏳ В симуляторе цена обновится через ~20 мин!\n"
        f"---------------------------\n"
        f"💰 Твой баланс: ${current_balance:.2f}"
    )
    try:
        bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка ТГ: {e}")

# --- ОСНОВНОЙ ЦИКЛ ---

def monitor():
    global current_balance
    print(f"🤖 Машина времени запущена. Баланс: ${current_balance}")
    
    # Обновляем список тикеров раз в 30 минут
    tickers = get_volatile_tickers()
    last_ticker_update = time.time()

    while True:
        now = datetime.now()
        
        # Обновляем список тикеров
        if time.time() - last_ticker_update > 1800:
            tickers = get_volatile_tickers()
            last_ticker_update = time.time()

        # Работаем только в "человеческое" время
        if WORK_START <= now.hour < WORK_END:
            print(f"🔎 [{now.strftime('%H:%M:%S')}] Сканирую {len(tickers)} акций...")
            
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    # Берем данные за последние 2 минуты с минутным интервалом
                    hist = stock.history(period="2m", interval="1m")
                    
                    if len(hist) < 2: continue
                    
                    price_now = hist['Close'].iloc[-1]
                    price_prev = hist['Close'].iloc[-2]
                    change = ((price_now - price_prev) / price_prev) * 100

                    # Если видим резкий скачок (Машина времени)
                    if abs(change) >= VOLATILITY_THRESHOLD:
                        action = "BUY" if change > 0 else "SELL"
                        send_telegram_signal(ticker, action, price_now, change)
                        # Чтобы не спамить по одной и той же акции:
                        time.sleep(2) 

                except Exception:
                    continue
        else:
            print(f"💤 [{now.strftime('%H:%M:%S')}] Время сна. Жду...")
            time.sleep(600) # Ночью проверяем раз в 10 минут
            continue

        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    monitor()

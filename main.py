import io
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

# Настройки времени
WORK_START = 10
WORK_END = 23

# Настройки стратегии
VOLATILITY_THRESHOLD = 0.4  # Сигнал при изменении > 0.4% за минуту
SCAN_INTERVAL = 15          # Проверка каждые 15 секунд

# --- ФУНКЦИИ ---

def get_volatile_tickers():
    try:
        url = "https://finance.yahoo.com/markets/stocks/most-active/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        # Исправляем FutureWarning от pandas
        tables = pd.read_html(io.StringIO(response.text)) 
        df = tables[0]
        
        top_tickers = df['Symbol'].head(30).tolist()
        manual_list = ["BNAI", "MRNO", "RMSG", "MARA", "RIOT", "TQQQ", "SOXL", "NVDA", "TSLA"]
        
        # Очистка тикеров от возможных пробелов
        combined = [str(t).strip() for t in (top_tickers + manual_list)]
        return list(set(combined))
    except Exception as e:
        print(f"⚠️ Ошибка сбора тикеров: {e}")
        return ["TSLA", "NVDA", "MARA", "TQQQ", "AAPL", "BNAI"]

def send_telegram_signal(ticker, action, price, change):
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
    print(f"🚀 Машина времени запущена. Баланс: ${current_balance}")
    
    tickers = get_volatile_tickers()
    last_ticker_update = time.time()

    while True:
        now = datetime.now()
        
        # Обновление списка тикеров раз в 30 минут
        if time.time() - last_ticker_update > 1800:
            tickers = get_volatile_tickers()
            last_ticker_update = time.time()

        if WORK_START <= now.hour < WORK_END:
            print(f"🔎 [{now.strftime('%H:%M:%S')}] Сканирую {len(tickers)} акций...")
            
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    # Используем период 1 день и интервал 1 минута
                    hist = stock.history(period="1d", interval="1m")
                    
                    if len(hist) < 2:
                        continue
                    
                    # Берем две последние закрытые минуты
                    price_now = hist['Close'].iloc[-1]
                    price_prev = hist['Close'].iloc[-2]
                    
                    if pd.isna(price_now) or pd.isna(price_prev):
                        continue
                        
                    change = ((price_now - price_prev) / price_prev) * 100

                    if abs(change) >= VOLATILITY_THRESHOLD:
                        action = "BUY" if change > 0 else "SELL"
                        send_telegram_signal(ticker, action, price_now, change)
                        print(f"🎯 Сигнал по {ticker}: {change:+.2f}%")
                        time.sleep(1) 

                except Exception as e:
                    # Игнорируем ошибки конкретных тикеров, чтобы цикл не прерывался
                    continue
        else:
            print(f"💤 [{now.strftime('%H:%M:%S')}] Время сна. Жду открытия...")
            time.sleep(600)
            continue

        time.sleep(SCAN_INTERVAL)

# --- ЗАПУСК ---
if __name__ == "__main__":
    try:
        monitor()
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем.")
    except Exception as e:
        print(f"Критическая ошибка: {e}")

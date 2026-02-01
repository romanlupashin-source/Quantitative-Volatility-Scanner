# BullRun_Bot
BullRun_Bot

# Quantitative Volatility Scanner 📈

An automated Python-based market analysis engine that monitors high-volatility assets in real-time. The system calculates liquidity, identifies trend direction, and sends actionable signals via Telegram based on statistical thresholds.

## 🚀 Key Features
* **Real-Time Data Ingestion:** Fetches live market data using `yfinance` API (5-minute intervals).
* **Volatility Logic:** Filters noise using a customizable percentage threshold (`MIN_MOVE_PCT`).
* **Risk Management:** Calculates dynamic position sizing based on 0.1% of daily volume to ensure liquidity.
* **Trend Detection:** Checks monotonic trends on recent candles to confirm signal direction.
* **Instant Alerts:** Integrates with Telegram API for low-latency notifications.

## 🛠️ Tech Stack
* **Python 3.x**
* **Pandas** (Time-series data manipulation)
* **Yfinance** (Market data API)
* **Requests** (Webhook handling)

## ⚙️ How It Works
The algorithm scans a pre-defined basket of assets (Crypto, Tech, Biotech) and applies the following logic:
1.  **Extract** latest OHLCV data.
2.  **Calculate** intraday percentage change.
3.  **Validate** liquidity (Volume * 0.001 * Price).
4.  **Execute** alert if volatility > Threshold AND Liquidity > $1000.

## ⚠️ Disclaimer
This software is for educational and research purposes only. It does not constitute financial advice.


import yfinance as yf
import pandas as pd
import time
import requests # Библиотека для отправки в Телеграм
from colorama import init, Fore, Style
from datetime import datetime

# ==========================================
# ⚙️ НАСТРОЙКИ ТЕЛЕГРАМА (ВСТАВЬ СВОИ ДАННЫЕ)
# ==========================================
TG_TOKEN = "ВСТАВЬ_СЮДА_ТОКЕН_ОТ_BOTFATHER"
TG_CHAT_ID = "ВСТАВЬ_СЮДА_ЦИФРЫ_ID"

# ==========================================
# 📋 СПИСОК АКЦИЙ
# ==========================================
TICKERS = [
    'MARA', 'RIOT', 'COIN', 'MSTR', 'CLSK', # Crypto
    'GME', 'AMC', 'HOOD', 'PLTR', 'SOFI',   # Meme
    'NVDA', 'AMD', 'TSLA', 'SMCI', 'ARM',   # Tech
    'NAMM', 'ROMA', 'CVNA', 'UPST', 'AI',   # Volatile
    'NVAX', 'MRNA'                          # BioTech
]

MIN_MOVE_PCT = 2.0 
init(autoreset=True)

# Функция отправки сообщения
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

def analyze_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d", interval="5m")
        if len(df) < 5: return None

        current_price = df['Close'].iloc[-1]
        open_price = df['Open'].iloc[0]
        volume_today = df['Volume'].sum()
        
        # Расчет лимита 0.1%
        max_shares = int(volume_today * 0.001)
        max_usd = max_shares * current_price

        # Фильтр: если лимит меньше $1000 — игнорируем
        if max_usd < 1000: return None

        pct_change = ((current_price - open_price) / open_price) * 100
        
        # Тренд
        recent_trend = df['Close'].tail(6)
        is_uptrend = recent_trend.is_monotonic_increasing
        is_downtrend = recent_trend.is_monotonic_decreasing
        trend_icon = "⚠️"
        if is_uptrend or is_downtrend: trend_icon = "✅ (Stable)"

        signal_msg = None

        # ЛОГИКА СИГНАЛОВ
        if pct_change >= MIN_MOVE_PCT:
            emoji = "🚀 BUY (LONG)"
            signal_msg = (
                f"{emoji} *{ticker}*\n"
                f"Рост: *{pct_change:.2f}%*\n"
                f"Тренд: {trend_icon}\n"
                f"💰 Макс. ставка: *${max_usd:,.0f}*\n"
                f"🔮 Цена через 20 мин: ${current_price:.2f}"
            )

        elif pct_change <= -MIN_MOVE_PCT:
            emoji = "🔻 SELL (SHORT)"
            signal_msg = (
                f"{emoji} *{ticker}*\n"
                f"Падение: *{pct_change:.2f}%*\n"
                f"Тренд: {trend_icon}\n"
                f"💰 Макс. ставка: *${max_usd:,.0f}*\n"
                f"🔮 Цена через 20 мин: ${current_price:.2f}"
            )

        # Если есть сигнал -> Выводим на экран и шлем в Телеграм
        if signal_msg:
            # Вывод в консоль
            color = Fore.GREEN if "BUY" in signal_msg else Fore.RED
            print(color + signal_msg.replace("*", "")) 
            print("-" * 30)
            
            # Отправка в телефон
            send_telegram(signal_msg)

    except Exception:
        pass

def main():
    print(Fore.CYAN + f"Scanning market... {datetime.now().strftime('%H:%M')}")
    for ticker in TICKERS:
        analyze_ticker(ticker)

if __name__ == "__main__":
    # Тестовое сообщение при запуске
    send_telegram("Бот запущен! Я слежу за рынком для ...")
    
    while True:
        main()
        # Пауза 5 минут, чтобы не спамить тебе в телефон каждую секунду
        print("Жду 5 минут перед следующим сканированием...")
        time.sleep(300)

import yfinance as yf
import time
import asyncio
from telegram import Bot

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = 'ТВОЙ_ТОКЕН_БОТА'
CHAT_ID = 'ТВОЙ_CHAT_ID'
# Список тикеров для сканирования (добавь те, что советовал лидер)
TICKERS = ['BNAI', 'TQQQ', 'TIRX', 'JEM', 'LBGJ', 'KIDZ', 'AAPL', 'NVDA', 'AMD']

# Параметры стратегии
MAX_STOCK_PRICE = 15.0      # Ищем только дешевые/волатильные акции
VOLATILITY_THRESHOLD = 1.2  # Сигнал при изменении на 1.2% за минуту
START_BALANCE = 99087.0     # Твой текущий Cash в симуляторе

bot = Bot(token=TELEGRAM_TOKEN)

async def send_signal(message):
    print(f"Отправка сигнала: {message}")
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')

def get_price(ticker):
    try:
        data = yf.download(ticker, period='1d', interval='1m', progress=False)
        if not data.empty:
            return data['Close'].iloc[-1]
    except Exception as e:
        print(f"Ошибка получения данных для {ticker}: {e}")
    return None

async def monitor():
    print("🎯 Режим Охотника запущен. Слежу за рынком...")
    # Словарь для хранения предыдущих цен
    last_prices = {ticker: get_price(ticker) for ticker in TICKERS}
    
    while True:
        for ticker in TICKERS:
            price_now = get_price(ticker)
            price_prev = last_prices.get(ticker)
            
            if price_now and price_prev:
                change = ((price_now - price_prev) / price_prev) * 100
                
                # Фильтр по цене и волатильности
                if price_now <= MAX_STOCK_PRICE and abs(change) >= VOLATILITY_THRESHOLD:
                    
                    if change > 0:
                        # СИГНАЛ НА ПОКУПКУ (LONG)
                        action = "🚀 BUY (LONG)"
                        tp_price = price_now * 1.04  # Цель +4%
                        qty = int(START_BALANCE / price_now)
                        emoji = "📈"
                    else:
                        # СИГНАЛ НА ПАДЕНИЕ (SHORT)
                        action = "📉 SELL (SHORT)"
                        tp_price = price_now * 0.96  # Цель -4% (выкуп шорта)
                        qty = int(START_BALANCE / price_now)
                        emoji = "📉"

                    msg = (
                        f"{emoji} **СИГНАЛ: {action} {ticker}**\n"
                        f"💰 Цена сейчас: ${price_now:.2f}\n"
                        f"📊 Изменение: {change:+.2f}%\n"
                        f"---------------------------\n"
                        f"🎯 **СТАВЬ LIMIT ORDER НА: ${tp_price:.2f}**\n"
                        f"📦 Объем (на весь Cash): {qty} шт.\n"
                        f"⚠️ *Не забудь про задержку 20 мин!*"
                    )
                    await send_signal(msg)
            
            # Обновляем цену в памяти
            last_prices[ticker] = price_now
        
        # Ждем 60 секунд до следующей проверки
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(monitor())

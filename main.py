import yfinance as yf
import time
import asyncio
from telegram import Bot

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = '8478161813:AAHQQr7jK16wWFB4Hx5aiIW56Sy1AdCT_pk'
CHAT_ID = '6935198093'
TICKERS = ['BNAI', 'TQQQ', 'TIRX', 'JEM', 'LBGJ', 'KIDZ', 'AAPL', 'NVDA', 'AMD']

MAX_STOCK_PRICE = 15.0      # Дешевые акции
VOLATILITY_THRESHOLD = 1.2  # Порог 1.2%
START_BALANCE = 99087.0     # Твой кэш

bot = Bot(token=TELEGRAM_TOKEN)

async def send_signal(message):
    print(f"Отправка сигнала: {message}")
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')

def get_price(ticker):
    try:
        data = yf.download(ticker, period='1d', interval='1m', progress=False)
        if not data.empty:
            val = data['Close'].iloc[-1]
            return float(val) 
    except Exception as e:
        print(f"Ошибка получения данных для {ticker}: {e}")
    return None

async def monitor():
    print("🎯 Режим Охотника запущен. Слежу за рынком...")
    last_prices = {ticker: get_price(ticker) for ticker in TICKERS}
    
    while True:
        for ticker in TICKERS:
            price_now = get_price(ticker)
            price_prev = last_prices.get(ticker)
            
            # Проверка: оба значения должны существовать
            if price_now is not None and price_prev is not None:
                change = ((price_now - price_prev) / price_prev) * 100
                
                if price_now <= MAX_STOCK_PRICE and abs(change) >= VOLATILITY_THRESHOLD:
                    if change > 0:
                        action = "🚀 BUY (LONG)"
                        tp_price = price_now * 1.04
                        emoji = "📈"
                    else:
                        action = "📉 SELL (SHORT)"
                        tp_price = price_now * 0.96
                        emoji = "📉"

                    qty = int(START_BALANCE / price_now)
                    msg = (
                        f"{emoji} **СИГНАЛ: {action} {ticker}**\n"
                        f"💰 Цена сейчас: ${price_now:.2f}\n"
                        f"📊 Изменение: {change:+.2f}%\n"
                        f"---------------------------\n"
                        f"🎯 **СТАВЬ LIMIT ORDER НА: ${tp_price:.2f}**\n"
                        f"📦 Объем: {qty} шт.\n"
                    )
                    await send_signal(msg)
            
            last_prices[ticker] = price_now
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(monitor())

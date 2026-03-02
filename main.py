import yfinance as yf
import telebot
from datetime import datetime
import time

# --- НАСТРОЙКИ ---
TOKEN = '8478161813:AAHQQr7jK16wWFB4Hx5aiIW56Sy1AdCT_pk'
CHAT_ID = '6935198093'
bot = telebot.TeleBot(TOKEN)

# Параметры игры
START_BALANCE = 100000
current_balance = START_BALANCE
risk_per_trade = 0.1  # Используем 10% капитала на сделку
positions = {}        # { 'TSLA': {'price': 150, 'qty': 50, 'time': '14:20'} }

# Часы активности (по твоему местному времени)
WORK_START = 10  # Начинаем в 10:00
WORK_END = 22    # В 22:00 принудительно выходим из всех акций
SLEEP_MODE = 23  # С 23:00 до 09:00 — полная тишина

def get_stats():
    """Считает текущий успех в процентах."""
    profit_pct = ((current_balance - START_BALANCE) / START_BALANCE) * 100
    return f"💰 Баланс: ${current_balance:.2f} ({profit_pct:+.2f}%)"

def close_all_positions():
    """Функция 'Экстренный выход' перед сном."""
    global current_balance, positions
    if not positions:
        return
    
    report = "🔔 **ВНИМАНИЕ: Закрытие смен!**\nПродаю всё, чтобы не рисковать ночью:\n\n"
    
    for ticker in list(positions.keys()):
        try:
            stock = yf.Ticker(ticker)
            price = stock.fast_info['last_price']
            
            buy_price = positions[ticker]['price']
            qty = positions[ticker]['qty']
            profit = (price - buy_price) * qty
            current_balance += profit
            
            report += f"❌ {ticker}: ${price} (Итог: {profit:+.2f})\n"
            del positions[ticker]
        except:
            report += f"⚠️ Ошибка закрытия {ticker}\n"
            
    report += f"\n{get_stats()}\nСпокойной ночи! 💤"
    bot.send_message(CHAT_ID, report, parse_mode='Markdown')

def process_signal(ticker, action, price):
    """Решает, покупать или нет, учитывая время."""
    global current_balance, positions
    now = datetime.now().hour

    # 1. Если уже поздно (например, после 21:00), новые сделки не открываем
    if now >= WORK_END - 1 and action == "BUY":
        print(f"Скоро спать, игнорирую покупку {ticker}")
        return

    if action == "BUY" and ticker not in positions:
        # Считаем сколько купить на 10% от текущего баланса
        cash_to_spend = current_balance * risk_per_trade
        qty = int(cash_to_spend / price)
        
        if qty > 0:
            positions[ticker] = {'price': price, 'qty': qty}
            msg = (f"🚀 **BUY {ticker}**\nЦена: ${price}\n"
                   f"Куплено: {qty} шт.\n"
                   f"Затрачено: ${qty*price:.2f}\n"
                   f"{get_stats()}")
            bot.send_message(CHAT_ID, msg, parse_mode='Markdown')

    elif action == "SELL" and ticker in positions:
        buy_price = positions[ticker]['price']
        qty = positions[ticker]['qty']
        profit = (price - buy_price) * qty
        current_balance += profit
        
        msg = (f"✅ **SELL {ticker}**\nЦена продажи: ${price}\n"
               f"Результат: {profit:+.2f}\n"
               f"{get_stats()}")
        bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
        del positions[ticker]

# --- ГЛАВНЫЙ ЦИКЛ ---
print("🤖 Робот-симулятор запущен...")

while True:
    now = datetime.now()
    current_hour = now.hour
    
    # ЛОГИКА ВРЕМЕНИ:
    # 1. Если наступил час закрытия (22:00) — сбрасываем акции
    if current_hour == WORK_END and positions:
        close_all_positions()

    # 2. Если сейчас "рабочее время" — анализируем рынок
    if WORK_START <= current_hour < WORK_END:
        # Тут твой список тикеров
        for t in ["TSLA", "NVDA", "AAPL"]:
            # Здесь должна быть твоя стратегия (просадка или рост)
            # Для примера имитируем получение цены:
            # price = yf.Ticker(t).fast_info['last_price']
            # process_signal(t, "BUY", price) 
            pass
    
    # 3. Режим глубокого сна (чтобы не нагружать процессор ночью)
    if current_hour >= SLEEP_MODE or current_hour < WORK_START:
        print("Бот в режиме ожидания (ночь)...")
        time.sleep(1800) # Проверка раз в 30 минут
    else:
        time.sleep(60)   # Днем проверка раз в минуту

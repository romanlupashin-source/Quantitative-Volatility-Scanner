# Добавляем "блокнот" памяти бота (положи это где-то под TICKERS)
positions = {} 

def analyze_ticker(ticker):
    """Мозг бота с памятью позиций: Покупка -> Продажа"""
    global positions # Разрешаем боту писать в блокнот
    
    try:
        # 1. Загрузка данных
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d", interval="5m")
        if len(df) < 2: return

        current_price = df['Close'].iloc[-1]
        open_price = df['Open'].iloc[0]
        pct_change = ((current_price - open_price) / open_price) * 100
        
        # Фильтр ликвидности
        volume_today = df['Volume'].sum()
        if volume_today * current_price < 100000: return

        # 2. Логика ПОКУПКИ (Если актива нет в нашем "блокноте")
        if ticker not in positions:
            # Например, покупаем, если цена упала на MIN_MOVE_PCT (ловим дно)
            # Или можешь поменять на > MIN_MOVE_PCT, если хочешь покупать на росте
            if pct_change <= -MIN_MOVE_PCT: 
                positions[ticker] = current_price # Записываем цену покупки
                msg = f"🟢 *ПОКУПКА {ticker}*\nЦена: ${current_price:.2f}\nПричина: Просадка {pct_change:.2f}%"
                print(Fore.GREEN + f"BUY {ticker}")
                send_telegram(msg)
                
        # 3. Логика ПРОДАЖИ (Если актив уже куплен)
        else:
            buy_price = positions[ticker]
            # Считаем, сколько мы заработали или потеряли с момента покупки
            profit_pct = ((current_price - buy_price) / buy_price) * 100
            
            # Продаем, если прибыль больше 2% ИЛИ убыток больше 1% (Stop-Loss)
            if profit_pct >= 2.0 or profit_pct <= -1.0:
                del positions[ticker] # Вычеркиваем из блокнота
                emoji = "🚀" if profit_pct > 0 else "🔻"
                msg = f"{emoji} *ПРОДАЖА {ticker}*\nЦена: ${current_price:.2f}\nИтог: {profit_pct:.2f}%"
                print(Fore.YELLOW + f"SELL {ticker}")
                send_telegram(msg)

    except Exception as e:
        print(Fore.RED + f"Ошибка {ticker}: {e}")

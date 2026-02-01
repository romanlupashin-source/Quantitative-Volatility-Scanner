import yfinance as yf
import pandas as pd
import time
import requests
from colorama import init, Fore, Style
from datetime import datetime

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# NOTE: In a production environment, use os.getenv() for keys.
TG_TOKEN = "YOUR_TOKEN_HERE_OR_ENV_VAR"
TG_CHAT_ID = "YOUR_ID_HERE"

# ==========================================
# 📋 ASSET LIST
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

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

def analyze_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d", interval="5m")
        if len(df) < 5: return None

        current_price = df['Close'].iloc[-1]
        open_price = df['Open'].iloc[0]
        volume_today = df['Volume'].sum()
        
        # Risk Management: 0.1% of daily volume limit
        max_shares = int(volume_today * 0.001)
        max_usd = max_shares * current_price

        # Liquidity Filter: Ignore if limit < $1000
        if max_usd < 1000: return None

        pct_change = ((current_price - open_price) / open_price) * 100
        
        # Trend Analysis
        recent_trend = df['Close'].tail(6)
        is_uptrend = recent_trend.is_monotonic_increasing
        is_downtrend = recent_trend.is_monotonic_decreasing
        trend_icon = "⚠️"
        if is_uptrend or is_downtrend: trend_icon = "✅ (Stable)"

        signal_msg = None

        if pct_change >= MIN_MOVE_PCT:
            emoji = "🚀 BUY (LONG)"
            signal_msg = (
                f"{emoji} *{ticker}*\n"
                f"Growth: *{pct_change:.2f}%*\n"
                f"Trend: {trend_icon}\n"
                f"💰 Max Size: *${max_usd:,.0f}*\n"
                f"🔮 Projected: ${current_price:.2f}"
            )

        elif pct_change <= -MIN_MOVE_PCT:
            emoji = "🔻 SELL (SHORT)"
            signal_msg = (
                f"{emoji} *{ticker}*\n"
                f"Drop: *{pct_change:.2f}%*\n"
                f"Trend: {trend_icon}\n"
                f"💰 Max Size: *${max_usd:,.0f}*\n"
                f"🔮 Projected: ${current_price:.2f}"
            )

        if signal_msg:
            color = Fore.GREEN if "BUY" in signal_msg else Fore.RED
            print(color + signal_msg.replace("*", "")) 
            print("-" * 30)
            # send_telegram(signal_msg) # Uncomment to enable alerts

    except Exception:
        pass

def main():
    print(Fore.CYAN + f"Scanning market... {datetime.now().strftime('%H:%M')}")
    for ticker in TICKERS:
        analyze_ticker(ticker)

if __name__ == "__main__":
    print("Bot started. Monitoring volatility...")
    while True:
        main()
        print("Waiting 5 minutes...")
        time.sleep(300)

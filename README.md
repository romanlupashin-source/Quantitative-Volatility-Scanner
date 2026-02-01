

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

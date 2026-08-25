# 📊 Crypto Signals Bot

Real-time crypto trading signals with technical analysis (RSI, MACD, MA, Bollinger Bands).

## Features
- **Telegram Bot** — interactive signals, prices, alerts
- **Web Dashboard** — live signal cards, price tracker, REST API
- **Technical Indicators** — RSI, MACD, SMA20/50/200, Bollinger Bands
- **Data Source** — Coinbase public API (no API key needed)
- **Markets** — Crypto only (BTC, ETH, SOL, and top 15 by volume)

## Quick Start

### Install
```bash
pip install -r requirements.txt
```

### Run Dashboard
```bash
python dashboard/app.py
```
Visit http://localhost:5000

### Run Telegram Bot
```bash
export BOT_TOKEN=your_token_here
python bot/telegram_bot.py
```

## Telegram Commands
- `/start` — Main menu
- `/signal BTC-USDT` — Get signal for a symbol
- `/top10` — Top 10 signals
- `/prices` — Live prices
- `/help` — Help

## API Endpoints
- `GET /` — Web dashboard
- `GET /prices` — Live prices page
- `GET /api/signals` — Top 10 signals (JSON)
- `GET /api/signal/BTC` — Single symbol signal (JSON)

## Signal Logic
Score: -6 to +6 → STRONG BUY / BUY / NEUTRAL / SELL / STRONG SELL

## Tech Stack
Python, Flask, python-telegram-bot, Coinbase API, Pandas/NumPy

## License
MIT

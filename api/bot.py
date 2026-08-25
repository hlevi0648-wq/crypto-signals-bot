"""
Telegram Bot - Webhook mode for Vercel serverless
Now with paper trading (simulated portfolio)
"""
import sys
import os
import json
import requests
from flask import Flask, request, jsonify

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.market_data import get_klines, get_ticker_price, get_multiple_signals
from indicators.technical import generate_signal
from paper_trading import (
    get_portfolio, deposit, withdraw, buy, sell,
    get_portfolio_summary, get_trade_history
)

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "7836189904:AAEqzPSyCfutHAZJJdXTe7t0lTIfPxiLcNU")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text, parse_mode="Markdown", reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        resp = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        return resp.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None


def answer_callback(callback_id, text=None):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    try:
        requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json=payload, timeout=5)
    except:
        pass


def format_signal(signal):
    lines = []
    lines.append(f"\U0001F4CA *{signal['symbol']}*")
    lines.append(f"Price: ${signal['price']:,.2f}")
    lines.append(f"Signal: *{signal['signal']}*")
    lines.append(f"Score: {signal['score']}")
    lines.append("")
    lines.append("*Indicators:*")
    ind = signal.get("indicators", {})
    if ind.get("rsi"):
        lines.append(f"  - RSI: {ind['rsi']}")
    if ind.get("macd"):
        lines.append(f"  - MACD: {ind['macd']['macd']} / Signal: {ind['macd']['signal']}")
    if ind.get("moving_averages"):
        for k, v in ind["moving_averages"].items():
            lines.append(f"  - {k.upper()}: ${v:,.2f}")
    lines.append("")
    lines.append("*Details:*")
    for d in signal.get("details", []):
        lines.append(f"  - {d}")
    return "\n".join(lines)


def format_portfolio(summary):
    lines = []
    lines.append("\U0001F4BC *Paper Trading Portfolio*")
    lines.append("")
    lines.append(f"Cash: ${summary['cash']:,.2f}")
    lines.append(f"Total Value: ${summary['total_value']:,.2f}")
    lines.append(f"Initial: ${summary['initial_deposit']:,.2f}")
    pnl = summary['total_pnl']
    pct = summary['total_pnl_pct']
    emoji = "\U0001F534" if pnl < 0 else "\U0001F7E2"
    lines.append(f"P&L: {emoji} ${pnl:,.2f} ({pct:+.2f}%)")
    lines.append(f"Trades: {summary['trade_count']}")
    lines.append("")
    if summary['positions']:
        lines.append("*Positions:*")
        for p in summary['positions']:
            sym = p['symbol'].replace('-USDT', '')
            pnl_emoji = "\U0001F534" if p['pnl'] < 0 else "\U0001F7E2"
            lines.append(f"  {sym}: {p['qty']:.6f} @ ${p['avg_price']:,.2f}")
            lines.append(f"    Value: ${p['value']:,.2f} | P&L: {pnl_emoji} ${p['pnl']:,.2f} ({p['pnl_pct']:+.2f}%)")
    else:
        lines.append("_No open positions_")
    return "\n".join(lines)


def get_main_menu():
    return {
        "inline_keyboard": [
            [
                {"text": "\U0001F4CA BTC Signal", "callback_data": "signal_BTC-USDT"},
                {"text": "\U0001F4CA ETH Signal", "callback_data": "signal_ETH-USDT"},
            ],
            [
                {"text": "\U0001F4CA SOL Signal", "callback_data": "signal_SOL-USDT"},
                {"text": "\U0001F525 Top 10", "callback_data": "top10"},
            ],
            [
                {"text": "\U0001F4B0 Prices", "callback_data": "prices"},
                {"text": "\U0001F4BC Portfolio", "callback_data": "portfolio"},
            ],
            [
                {"text": "\U0001F4B8 Buy", "callback_data": "trade_buy"},
                {"text": "\U0001F4B9 Sell", "callback_data": "trade_sell"},
            ],
            [
                {"text": "\U00002753 Help", "callback_data": "help"},
            ],
        ]
    }


def get_buy_menu():
    return {
        "inline_keyboard": [
            [
                {"text": "Buy $100 BTC", "callback_data": "buy_BTC-USDT_100"},
                {"text": "Buy $500 BTC", "callback_data": "buy_BTC-USDT_500"},
            ],
            [
                {"text": "Buy $100 ETH", "callback_data": "buy_ETH-USDT_100"},
                {"text": "Buy $500 ETH", "callback_data": "buy_ETH-USDT_500"},
            ],
            [
                {"text": "Buy $100 SOL", "callback_data": "buy_SOL-USDT_100"},
                {"text": "Buy $500 SOL", "callback_data": "buy_SOL-USDT_500"},
            ],
            [
                {"text": "\U00002B05 Back", "callback_data": "menu"},
            ],
        ]
    }


def get_sell_menu(user_id):
    summary = get_portfolio_summary(user_id)
    if not summary['positions']:
        return {
            "inline_keyboard": [
                [{"text": "\U00002B05 Back", "callback_data": "menu"}],
            ]
        }
    keyboard = []
    for p in summary['positions']:
        sym = p['symbol'].replace('-USDT', '')
        keyboard.append([
            {"text": f"Sell all {sym}", "callback_data": f"sell_{p['symbol']}_all"},
        ])
    keyboard.append([{"text": "\U00002B05 Back", "callback_data": "menu"}])
    return {"inline_keyboard": keyboard}


def handle_command(chat_id, command, args=None, user_id=None):
    uid = user_id or chat_id

    if command == "start":
        portfolio = get_portfolio(uid)
        summary = get_portfolio_summary(uid)
        keyboard = get_main_menu()
        send_message(
            chat_id,
            "*Crypto Trading Signals Bot*\n\n"
            "Real-time signals + paper trading.\n"
            "You start with $10,000 simulated money.\n"
            "Practice trading based on signals — no real money.\n\n"
            f"Your balance: ${summary['cash']:,.2f}\n\n"
            "Select an option:",
            reply_markup=keyboard,
        )
    elif command == "help":
        send_message(
            chat_id,
            "*Commands:*\n"
            "/start - Main menu\n"
            "/signal <SYMBOL> - Get signal\n"
            "/top10 - Top 10 signals\n"
            "/prices - Live prices\n"
            "/portfolio - Your paper portfolio\n"
            "/buy <SYMBOL> <USD> - Buy crypto\n"
            "/sell <SYMBOL> - Sell position\n"
            "/deposit <USD> - Add paper money\n"
            "/withdraw <USD> - Remove paper money\n"
            "/history - Trade history\n"
            "/help - This message",
        )
    elif command == "signal":
        if not args:
            send_message(chat_id, "Usage: /signal <SYMBOL>\nExample: /signal BTC-USDT")
            return
        symbol = args[0].upper()
        send_message(chat_id, f"Fetching {symbol} signal...")
        prices = get_klines(symbol, "3600", 300)
        if len(prices) < 50:
            send_message(chat_id, f"Insufficient data for {symbol}")
            return
        signal = generate_signal(prices, symbol)
        text = format_signal(signal)
        send_message(chat_id, text)
    elif command == "top10":
        send_message(chat_id, "Fetching top 10 signals...")
        signals = get_multiple_signals(limit=10)
        if not signals:
            send_message(chat_id, "No data available")
            return
        text = "*Top 10 Crypto Signals*\n"
        for s in signals:
            text += f"{s['signal']} {s['symbol']} - ${s['price']:,.2f} (score: {s['score']})\n"
        send_message(chat_id, text)
    elif command == "prices":
        symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "DOGE-USDT"]
        text = "*Live Prices*\n"
        for sym in symbols:
            price = get_ticker_price(sym)
            if price:
                text += f"  {sym.replace('-USDT', '')}: ${price:,.2f}\n"
        send_message(chat_id, text)
    elif command == "portfolio":
        summary = get_portfolio_summary(uid)
        text = format_portfolio(summary)
        send_message(chat_id, text)
    elif command == "buy":
        if not args or len(args) < 2:
            send_message(chat_id, "Usage: /buy <SYMBOL> <USD>\nExample: /buy BTC-USDT 100")
            return
        symbol = args[0].upper()
        try:
            amount = float(args[1])
        except ValueError:
            send_message(chat_id, "Amount must be a number")
            return
        result = buy(uid, symbol, amount)
        if "error" in result:
            send_message(chat_id, f"\U0000274C {result['error']}")
        else:
            send_message(chat_id, f"\U00002705 {result['message']}\nCash: ${result['cash_remaining']:,.2f}")
    elif command == "sell":
        if not args:
            send_message(chat_id, "Usage: /sell <SYMBOL>\nExample: /sell BTC-USDT")
            return
        symbol = args[0].upper()
        result = sell(uid, symbol)
        if "error" in result:
            send_message(chat_id, f"\U0000274C {result['error']}")
        else:
            pnl = result['pnl']
            emoji = "\U0001F534" if pnl < 0 else "\U0001F7E2"
            send_message(
                chat_id,
                f"\U00002705 {result['message']}\n"
                f"P&L: {emoji} ${pnl:,.2f} ({result['pnl_pct']:+.2f}%)\n"
                f"Cash: ${result['cash_total']:,.2f}"
            )
    elif command == "deposit":
        if not args:
            send_message(chat_id, "Usage: /deposit <USD>\nExample: /deposit 1000")
            return
        try:
            amount = float(args[0])
        except ValueError:
            send_message(chat_id, "Amount must be a number")
            return
        result = deposit(uid, amount)
        if "error" in result:
            send_message(chat_id, f"\U0000274C {result['error']}")
        else:
            send_message(chat_id, f"\U00002705 {result['message']}\nBalance: ${result['new_balance']:,.2f}")
    elif command == "withdraw":
        if not args:
            send_message(chat_id, "Usage: /withdraw <USD>\nExample: /withdraw 500")
            return
        try:
            amount = float(args[0])
        except ValueError:
            send_message(chat_id, "Amount must be a number")
            return
        result = withdraw(uid, amount)
        if "error" in result:
            send_message(chat_id, f"\U0000274C {result['error']}")
        else:
            send_message(chat_id, f"\U00002705 {result['message']}\nBalance: ${result['new_balance']:,.2f}")
    elif command == "history":
        history = get_trade_history(uid, limit=10)
        if not history:
            send_message(chat_id, "No trades yet. Use /buy to start.")
            return
        text = "*Recent Trades*\n"
        for t in history:
            ts = time.strftime('%H:%M', time.gmtime(t['timestamp']))
            if t['type'] == 'buy':
                text += f"  [{ts}] BUY {t.get('symbol', '').replace('-USDT', '')} - ${t['amount_usd']:,.2f}\n"
            elif t['type'] == 'sell':
                text += f"  [{ts}] SELL {t.get('symbol', '').replace('-USDT', '')} - ${t['amount_usd']:,.2f} (P&L: ${t['pnl']:,.2f})\n"
            elif t['type'] == 'deposit':
                text += f"  [{ts}] DEPOSIT +${t['amount']:,.2f}\n"
            elif t['type'] == 'withdraw':
                text += f"  [{ts}] WITHDRAW -${t['amount']:,.2f}\n"
        send_message(chat_id, text)
    else:
        send_message(chat_id, "Unknown command. Send /help for available commands.")


def handle_callback(chat_id, callback_id, data, user_id=None):
    answer_callback(callback_id)
    uid = user_id or chat_id

    if data == "menu":
        keyboard = get_main_menu()
        send_message(chat_id, "Main menu:", reply_markup=keyboard)
    elif data == "help":
        handle_command(chat_id, "help", user_id=uid)
    elif data.startswith("signal_"):
        symbol = data.replace("signal_", "")
        send_message(chat_id, f"Fetching {symbol} signal...")
        prices = get_klines(symbol, "3600", 300)
        if len(prices) < 50:
            send_message(chat_id, f"Insufficient data for {symbol}")
            return
        signal = generate_signal(prices, symbol)
        text = format_signal(signal)
        keyboard = get_main_menu()
        send_message(chat_id, text, reply_markup=keyboard)
    elif data == "top10":
        send_message(chat_id, "Fetching top 10 signals...")
        signals = get_multiple_signals(limit=10)
        if not signals:
            send_message(chat_id, "No data available")
            return
        text = "*Top 10 Crypto Signals*\n"
        for s in signals:
            text += f"{s['signal']} {s['symbol']} - ${s['price']:,.2f} (score: {s['score']})\n"
        keyboard = get_main_menu()
        send_message(chat_id, text, reply_markup=keyboard)
    elif data == "prices":
        symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "DOGE-USDT"]
        text = "*Live Prices*\n"
        for sym in symbols:
            price = get_ticker_price(sym)
            if price:
                text += f"  {sym.replace('-USDT', '')}: ${price:,.2f}\n"
        keyboard = get_main_menu()
        send_message(chat_id, text, reply_markup=keyboard)
    elif data == "portfolio":
        summary = get_portfolio_summary(uid)
        text = format_portfolio(summary)
        keyboard = get_main_menu()
        send_message(chat_id, text, reply_markup=keyboard)
    elif data == "trade_buy":
        keyboard = get_buy_menu()
        send_message(chat_id, "Select a buy option:", reply_markup=keyboard)
    elif data == "trade_sell":
        keyboard = get_sell_menu(uid)
        send_message(chat_id, "Select a position to sell:", reply_markup=keyboard)
    elif data.startswith("buy_"):
        parts = data.split("_")
        symbol = parts[1]
        amount = float(parts[2])
        result = buy(uid, symbol, amount)
        if "error" in result:
            send_message(chat_id, f"\U0000274C {result['error']}")
        else:
            send_message(chat_id, f"\U00002705 {result['message']}\nCash: ${result['cash_remaining']:,.2f}")
        keyboard = get_main_menu()
        send_message(chat_id, "Back to menu:", reply_markup=keyboard)
    elif data.startswith("sell_"):
        parts = data.split("_")
        symbol = parts[1]
        result = sell(uid, symbol)
        if "error" in result:
            send_message(chat_id, f"\U0000274C {result['error']}")
        else:
            pnl = result['pnl']
            emoji = "\U0001F534" if pnl < 0 else "\U0001F7E2"
            send_message(
                chat_id,
                f"\U00002705 {result['message']}\n"
                f"P&L: {emoji} ${pnl:,.2f} ({result['pnl_pct']:+.2f}%)\n"
                f"Cash: ${result['cash_total']:,.2f}"
            )
        keyboard = get_main_menu()
        send_message(chat_id, "Back to menu:", reply_markup=keyboard)


@app.route("/bot/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return jsonify({"status": "ok"})

    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        callback_id = cb["id"]
        data = cb.get("data", "")
        user_id = cb.get("from", {}).get("id", chat_id)
        handle_callback(chat_id, callback_id, data, user_id)
        return jsonify({"status": "ok"})

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        user_id = msg.get("from", {}).get("id", chat_id)

        if text.startswith("/"):
            parts = text.split(" ", 1)
            command = parts[0].lstrip("/").lower()
            args = parts[1].split(" ") if len(parts) > 1 else None
            handle_command(chat_id, command, args, user_id)
        elif text.lower() in ["hi", "hello", "hey"]:
            keyboard = get_main_menu()
            send_message(chat_id, "Hi! I'm the Crypto Signals Bot. Select an option:", reply_markup=keyboard)
        else:
            symbol = text.upper().replace("/", "-")
            if not symbol.endswith("-USDT"):
                symbol = symbol + "-USDT" if "-" not in symbol else symbol
            send_message(chat_id, f"Fetching {symbol} signal...")
            prices = get_klines(symbol, "3600", 300)
            if len(prices) < 50:
                send_message(chat_id, f"No data for {symbol}. Try /help for commands.")
                return jsonify({"status": "ok"})
            signal = generate_signal(prices, symbol)
            text_out = format_signal(signal)
            keyboard = get_main_menu()
            send_message(chat_id, text_out, reply_markup=keyboard)

    return jsonify({"status": "ok"})


@app.route("/bot/setwebhook", methods=["GET"])
def set_webhook():
    base_url = request.host_url.rstrip("/")
    webhook_url = f"{base_url}/bot/webhook"
    resp = requests.get(f"{TELEGRAM_API}/setWebhook", params={"url": webhook_url}, timeout=10)
    result = resp.json()
    return jsonify({"status": "ok" if result.get("ok") else "error", "telegram_response": result, "webhook_url": webhook_url})


@app.route("/bot/info", methods=["GET"])
def bot_info():
    resp = requests.get(f"{TELEGRAM_API}/getMe", timeout=10)
    return jsonify(resp.json())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

"""
Telegram Bot - Webhook mode for Vercel serverless
Handles updates from Telegram via webhook
"""
import sys
import os
import json
import requests
from flask import Flask, request, jsonify

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.market_data import get_klines, get_ticker_price, get_multiple_signals
from indicators.technical import generate_signal

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "7836189904:AAEqzPSyCfutHAZJJdXTe7t0lTIfPxiLcNU")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text, parse_mode="Markdown", reply_markup=None):
    """Send a message to a Telegram chat"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        resp = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        return resp.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None


def answer_callback(callback_id, text=None):
    """Answer a callback query"""
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    try:
        requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json=payload, timeout=5)
    except:
        pass


def format_signal(signal):
    """Format signal for Telegram message"""
    text = f"""*{signal["symbol"]}*
Price: ${signal["price"]:,.2f}
Signal: *{signal["signal"]}*
Score: {signal["score"]}

*Indicators:*
"""
    ind = signal.get("indicators", {})
    if ind.get("rsi"):
        text += f"  - RSI: {ind["rsi"]}\n"
    if ind.get("macd"):
        text += f"  - MACD: {ind["macd"]["macd"]} / Signal: {ind["macd"]["signal"]}\n"
    if ind.get("moving_averages"):
        for k, v in ind["moving_averages"].items():
            text += f"  - {k.upper()}: ${v:,.2f}\n"
    text += "\n*Details:*\n"
    for d in signal.get("details", []):
        text += f"  - {d}\n"
    return text


def get_main_menu():
    """Return the main menu keyboard"""
    return {
        "inline_keyboard": [
            [
                {"text": "BTC Signal", "callback_data": "signal_BTC-USDT"},
                {"text": "ETH Signal", "callback_data": "signal_ETH-USDT"},
            ],
            [
                {"text": "SOL Signal", "callback_data": "signal_SOL-USDT"},
                {"text": "XRP Signal", "callback_data": "signal_XRP-USDT"},
            ],
            [
                {"text": "Top 10 Signals", "callback_data": "top10"},
                {"text": "Live Prices", "callback_data": "prices"},
            ],
        ]
    }


def handle_command(chat_id, command, args=None):
    """Handle slash commands"""
    if command == "start":
        keyboard = get_main_menu()
        send_message(
            chat_id,
            "*Crypto Trading Signals Bot*\n\n"
            "Real-time technical analysis signals for crypto markets.\n"
            "Powered by Coinbase data + RSI, MACD, MA, Bollinger Bands.\n\n"
            "Select an option:",
            reply_markup=keyboard,
        )
    elif command == "help":
        send_message(
            chat_id,
            "*Commands:*\n"
            "/start - Main menu\n"
            "/signal <SYMBOL> - Get signal (e.g. /signal BTC-USDT)\n"
            "/top10 - Top 10 signals\n"
            "/prices - Live prices\n"
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
            text += f"{s["signal"]} {s["symbol"]} - ${s["price"]:,.2f} (score: {s["score"]})\n"
        send_message(chat_id, text)
    elif command == "prices":
        symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "DOGE-USDT"]
        text = "*Live Prices*\n"
        for sym in symbols:
            price = get_ticker_price(sym)
            if price:
                text += f"  {sym.replace('-USDT', '')}: ${price:,.2f}\n"
        send_message(chat_id, text)
    else:
        send_message(chat_id, "Unknown command. Send /help for available commands.")


def handle_callback(chat_id, callback_id, data):
    """Handle callback queries from inline keyboards"""
    answer_callback(callback_id)
    if data.startswith("signal_"):
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
            text += f"{s["signal"]} {s["symbol"]} - ${s["price"]:,.2f} (score: {s["score"]})\n"
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


@app.route("/bot/webhook", methods=["POST"])
def webhook():
    """Handle incoming Telegram updates"""
    update = request.get_json()
    if not update:
        return jsonify({"status": "ok"})

    # Handle callback queries
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        callback_id = cb["id"]
        data = cb.get("data", "")
        handle_callback(chat_id, callback_id, data)
        return jsonify({"status": "ok"})

    # Handle messages
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text.startswith("/"):
            parts = text.split(" ", 1)
            command = parts[0].lstrip("/").lower()
            args = parts[1].split(" ") if len(parts) > 1 else None
            handle_command(chat_id, command, args)
        elif text.lower() in ["hi", "hello", "hey"]:
            keyboard = get_main_menu()
            send_message(chat_id, "Hi! I'm the Crypto Signals Bot. Select an option:", reply_markup=keyboard)
        else:
            # Try to parse as symbol
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
    """Set the Telegram webhook URL"""
    base_url = request.host_url.rstrip("/")
    webhook_url = f"{base_url}/bot/webhook"

    resp = requests.get(
        f"{TELEGRAM_API}/setWebhook",
        params={"url": webhook_url},
        timeout=10,
    )
    result = resp.json()

    # Also send a welcome message
    if result.get("ok"):
        return jsonify({
            "status": "ok",
            "webhook_url": webhook_url,
            "telegram_response": result,
            "bot_username": "Btccryptominerdoublesbtc_bot",
        })
    else:
        return jsonify({
            "status": "error",
            "telegram_response": result,
        })


@app.route("/bot/info", methods=["GET"])
def bot_info():
    """Get bot info"""
    resp = requests.get(f"{TELEGRAM_API}/getMe", timeout=10)
    return jsonify(resp.json())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

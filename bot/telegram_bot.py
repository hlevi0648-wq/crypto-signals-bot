"""
Telegram Bot - Crypto Trading Signals
"""
import os
import asyncio
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
)
from data.market_data import get_klines, get_ticker_price, get_multiple_signals
from indicators.technical import generate_signal

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")


def format_signal(signal):
    """Format signal for Telegram message"""
    text = f"""📊 *{signal["symbol"]}*
━━━━━━━━━━━━━━━
💰 Price: `${signal["price"]:,.2f}`
🎯 Signal: *{signal["signal"]}*
📈 Score: `{signal["score"]}`

*Indicators:*
"""
    ind = signal.get("indicators", {})
    if ind.get("rsi"):
        text += f"  • RSI: `{ind["rsi"]}`\n"
    if ind.get("macd"):
        text += f"  • MACD: `{ind["macd"]["macd"]}` / Signal: `{ind["macd"]["signal"]}`\n"
    if ind.get("moving_averages"):
        for k, v in ind["moving_averages"].items():
            text += f"  • {k.upper()}: `${v:,.2f}`\n"
    text += "\n*Details:*\n"
    for d in signal.get("details", []):
        text += f"  • {d}\n"
    text += f"\n⏰ {datetime.now(timezone.utc).strftime("%H:%M UTC")}"
    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 BTC Signal", callback_data="signal_BTC-USDT"),
         InlineKeyboardButton("📊 ETH Signal", callback_data="signal_ETH-USDT")],
        [InlineKeyboardButton("🔥 Top 10 Signals", callback_data="top10"),
         InlineKeyboardButton("💰 Prices", callback_data="prices")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🤖 *Crypto Trading Signals Bot*\n\n"
        "Real-time technical analysis signals for crypto markets.\n"
        "Powered by Coinbase data + RSI, MACD, MA, Bollinger Bands.\n\n"
        "Select an option:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def signal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("signal_"):
        symbol = data.replace("signal_", "")
        await query.edit_message_text(f"⏳ Fetching {symbol} signal...")
        prices = get_klines(symbol, "3600", 300)
        if len(prices) < 50:
            await query.edit_message_text(f"❌ Insufficient data for {symbol}")
            return
        signal = generate_signal(prices, symbol)
        text = format_signal(signal)
        await query.edit_message_text(text, parse_mode="Markdown")
    elif data == "top10":
        await query.edit_message_text("⏳ Fetching top 10 signals...")
        signals = get_multiple_signals(limit=10)
        if not signals:
            await query.edit_message_text("❌ No data available")
            return
        text = "🔥 *Top 10 Crypto Signals*\n━━━━━━━━━━━━━━━\n"
        for s in signals:
            text += f"{s["signal"]} *{s["symbol"]}* - `${s["price"]:,.2f}` (score: {s["score"]})\n"
        await query.edit_message_text(text, parse_mode="Markdown")
    elif data == "prices":
        symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "DOGE-USDT"]
        text = "💰 *Live Prices*\n━━━━━━━━━━━━━━━\n"
        for sym in symbols:
            price = get_ticker_price(sym)
            if price:
                text += f"  {sym.replace("-USDT", "")}: `${price:,.2f}`\n"
        await query.edit_message_text(text, parse_mode="Markdown")


async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /signal <SYMBOL>\nExample: /signal BTC-USDT")
        return
    symbol = context.args[0].upper()
    await update.message.reply_text(f"⏳ Fetching {symbol} signal...")
    prices = get_klines(symbol, "3600", 300)
    if len(prices) < 50:
        await update.message.reply_text(f"❌ Insufficient data for {symbol}")
        return
    signal = generate_signal(prices, symbol)
    text = format_signal(signal)
    await update.message.reply_text(text, parse_mode="Markdown")


async def top10_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Fetching top 10 signals...")
    signals = get_multiple_signals(limit=10)
    if not signals:
        await update.message.reply_text("❌ No data available")
        return
    text = "🔥 *Top 10 Crypto Signals*\n━━━━━━━━━━━━━━━\n"
    for s in signals:
        text += f"{s["signal"]} *{s["symbol"]}* - `${s["price"]:,.2f}` (score: {s["score"]})\n"
    await update.message.reply_text(text, parse_mode="Markdown")


async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "DOGE-USDT"]
    text = "💰 *Live Prices*\n━━━━━━━━━━━━━━━\n"
    for sym in symbols:
        price = get_ticker_price(sym)
        if price:
            text += f"  {sym.replace("-USDT", "")}: `${price:,.2f}`\n"
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Commands:*\n"
        "/start - Main menu\n"
        "/signal <SYMBOL> - Get signal\n"
        "/top10 - Top 10 signals\n"
        "/prices - Live prices\n"
        "/help - This message",
        parse_mode="Markdown",
    )


def main():
    if not BOT_TOKEN:
        print("❌ Set BOT_TOKEN environment variable")
        return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("top10", top10_command))
    app.add_handler(CommandHandler("prices", prices_command))
    app.add_handler(CallbackQueryHandler(signal_callback))
    print("🤖 Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()

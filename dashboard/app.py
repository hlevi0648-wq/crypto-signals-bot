"""
Web Dashboard - Crypto Trading Signals
"""
import os
from flask import Flask, render_template_string, jsonify
from data.market_data import get_klines, get_ticker_price, get_multiple_signals
from indicators.technical import generate_signal

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Signals Bot</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0a0e17; color: #e4e7eb; min-height: 100vh; }
        .header { background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%); padding: 20px 40px; border-bottom: 1px solid #21262d; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 24px; background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .badge { background: #1f2937; padding: 6px 14px; border-radius: 20px; font-size: 12px; color: #10b981; }
        .container { max-width: 1200px; margin: 0 auto; padding: 30px 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
        .card { background: #161b22; border: 1px solid #21262d; border-radius: 12px; padding: 20px; transition: transform 0.2s, border-color 0.2s; }
        .card:hover { transform: translateY(-2px); border-color: #30363d; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .symbol { font-size: 18px; font-weight: 700; }
        .price { font-size: 24px; font-weight: 700; color: #58a6ff; }
        .signal { display: inline-block; padding: 4px 12px; border-radius: 6px; font-size: 13px; font-weight: 600; }
        .signal-buy { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .signal-sell { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
        .signal-neutral { background: rgba(156, 163, 175, 0.15); color: #9ca3af; }
        .indicators { margin-top: 15px; }
        .indicator-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #21262d; font-size: 13px; }
        .indicator-row:last-child { border-bottom: none; }
        .indicator-label { color: #8b949e; }
        .indicator-value { font-weight: 600; }
        .score-bar { margin-top: 10px; height: 6px; background: #21262d; border-radius: 3px; overflow: hidden; }
        .score-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
        .details { margin-top: 12px; font-size: 12px; color: #8b949e; }
        .details div { padding: 2px 0; }
        .nav { display: flex; gap: 20px; margin-bottom: 25px; }
        .nav a { color: #8b949e; text-decoration: none; padding: 8px 16px; border-radius: 6px; transition: all 0.2s; }
        .nav a:hover, .nav a.active { color: #e4e7eb; background: #21262d; }
        .stats { display: flex; gap: 30px; margin-bottom: 25px; flex-wrap: wrap; }
        .stat { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 15px 25px; }
        .stat-label { font-size: 12px; color: #8b949e; margin-bottom: 5px; }
        .stat-value { font-size: 22px; font-weight: 700; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Crypto Signals Bot</h1>
        <span class="badge">● LIVE</span>
    </div>
    <div class="container">
        <div class="nav">
            <a href="/" class="active">Signals</a>
            <a href="/prices">Prices</a>
            <a href="/api/signals">API</a>
        </div>
        <div class="stats">
            <div class="stat"><div class="stat-label">Total Signals</div><div class="stat-value">{{ signals|length }}</div></div>
            <div class="stat"><div class="stat-label">Buy Signals</div><div class="stat-value" style="color: #10b981">{{ buy_count }}</div></div>
            <div class="stat"><div class="stat-label">Sell Signals</div><div class="stat-value" style="color: #ef4444">{{ sell_count }}</div></div>
            <div class="stat"><div class="stat-label">Neutral</div><div class="stat-value" style="color: #9ca3af">{{ neutral_count }}</div></div>
        </div>
        <div class="grid">
            {% for s in signals %}
            <div class="card">
                <div class="card-header">
                    <span class="symbol">{{ s.symbol }}</span>
                    <span class="price">${{ "{:,.2f}".format(s.price) }}</span>
                </div>
                <span class="signal {% if "BUY" in s.signal %}signal-buy{% elif "SELL" in s.signal %}signal-sell{% else %}signal-neutral{% endif %}">{{ s.signal }}</span>
                <div class="score-bar">
                    <div class="score-fill" style="width: {{ (s.score + 6) / 12 * 100 }}%; background: {% if s.score > 0 %}#10b981{% elif s.score < 0 %}#ef4444{% else %}#9ca3af{% endif %}"></div>
                </div>
                <div class="indicators">
                    {% if s.indicators.rsi %}
                    <div class="indicator-row"><span class="indicator-label">RSI (14)</span><span class="indicator-value">{{ s.indicators.rsi }}</span></div>
                    {% endif %}
                    {% if s.indicators.macd %}
                    <div class="indicator-row"><span class="indicator-label">MACD</span><span class="indicator-value">{{ s.indicators.macd.macd }}</span></div>
                    {% endif %}
                    {% for k, v in s.indicators.moving_averages.items() %}
                    <div class="indicator-row"><span class="indicator-label">{{ k|upper }}</span><span class="indicator-value">${{ "{:,.2f}".format(v) }}</span></div>
                    {% endfor %}
                </div>
                <div class="details">{% for d in s.details %}<div>• {{ d }}</div>{% endfor %}</div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

PRICES_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Live Prices</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0a0e17; color: #e4e7eb; margin: 0; padding: 40px; }
        .header h1 { color: #58a6ff; }
        .price-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-top: 30px; }
        .price-card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 20px; text-align: center; }
        .price-symbol { font-size: 14px; color: #8b949e; }
        .price-value { font-size: 28px; font-weight: 700; color: #58a6ff; margin-top: 8px; }
    </style>
</head>
<body>
    <div class="header"><h1>💰 Live Crypto Prices</h1></div>
    <div class="price-grid">
        {% for sym, price in prices %}
        <div class="price-card"><div class="price-symbol">{{ sym }}</div><div class="price-value">${{ "{:,.2f}".format(price) }}</div></div>
        {% endfor %}
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    signals = get_multiple_signals(limit=12)
    buy_count = sum(1 for s in signals if "BUY" in s["signal"])
    sell_count = sum(1 for s in signals if "SELL" in s["signal"])
    neutral_count = sum(1 for s in signals if "NEUTRAL" in s["signal"])
    return render_template_string(HTML_TEMPLATE, signals=signals, buy_count=buy_count, sell_count=sell_count, neutral_count=neutral_count)


@app.route("/prices")
def prices():
    symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "ADA-USDT", "DOGE-USDT", "AVAX-USDT", "LINK-USDT"]
    price_data = []
    for sym in symbols:
        p = get_ticker_price(sym)
        if p:
            price_data.append((sym.replace("-USDT", "/USDT"), p))
    return render_template_string(PRICES_TEMPLATE, prices=price_data)


@app.route("/api/signals")
def api_signals():
    signals = get_multiple_signals(limit=10)
    return jsonify(signals)


@app.route("/api/signal/<symbol>")
def api_single_signal(symbol):
    symbol = symbol.upper() + "-USDT" if not symbol.upper().endswith("-USDT") else symbol.upper()
    prices = get_klines(symbol, "3600", 300)
    if len(prices) < 50:
        return jsonify({"error": "Insufficient data"}), 400
    signal = generate_signal(prices, symbol)
    return jsonify(signal)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

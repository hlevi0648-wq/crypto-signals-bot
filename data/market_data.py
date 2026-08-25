"""
Market data fetcher - Coinbase Public API (no API key needed, no geo-blocks)
"""
import requests
import time

COINBASE_API = "https://api.exchange.coinbase.com"


def get_klines(symbol="BTC-USDT", interval="3600", limit=300):
    """Fetch candlestick data from Coinbase"""
    url = f"{COINBASE_API}/products/{symbol}/candles"
    params = {"granularity": interval}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        closes = [float(candle[4]) for candle in sorted(data, key=lambda x: x[0])]
        return closes[-limit:] if len(closes) > limit else closes
    except requests.RequestException as e:
        print(f"Error fetching {symbol}: {e}")
        return []


def get_ticker_price(symbol="BTC-USDT"):
    """Get current price for a symbol"""
    url = f"{COINBASE_API}/products/{symbol}/ticker"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return float(resp.json()["price"])
    except requests.RequestException as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None


def get_top_symbols(limit=20):
    """Get top USDT pairs by volume"""
    popular = [
        ("BTC-USDT", "Bitcoin"), ("ETH-USDT", "Ethereum"), ("SOL-USDT", "Solana"),
        ("XRP-USDT", "Ripple"), ("ADA-USDT", "Cardano"), ("DOGE-USDT", "Dogecoin"),
        ("AVAX-USDT", "Avalanche"), ("LINK-USDT", "Chainlink"), ("DOT-USDT", "Polkadot"),
        ("MATIC-USDT", "Polygon"), ("LTC-USDT", "Litecoin"), ("BCH-USDT", "Bitcoin Cash"),
        ("UNI-USDT", "Uniswap"), ("ATOM-USDT", "Cosmos"), ("NEAR-USDT", "NEAR"),
    ]
    return [(s[0], 0) for s in popular[:limit]]


def get_multiple_signals(symbols=None, interval="3600", limit=300):
    """Get signals for multiple symbols at once"""
    from indicators.technical import generate_signal
    if symbols is None:
        top = get_top_symbols(10)
        symbols = [s[0] for s in top]
    results = []
    for symbol in symbols:
        prices = get_klines(symbol, interval, limit)
        if len(prices) >= 50:
            signal = generate_signal(prices, symbol)
            results.append(signal)
        time.sleep(0.2)
    return results

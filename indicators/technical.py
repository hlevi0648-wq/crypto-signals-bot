"""
Technical Analysis Indicators
RSI, MACD, Moving Averages, Bollinger Bands
"""
import numpy as np
import pandas as pd


def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    delta = pd.Series(prices).diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else None


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD line, signal line, and histogram"""
    prices_series = pd.Series(prices)
    ema_fast = prices_series.ewm(span=fast, adjust=False).mean()
    ema_slow = prices_series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": macd_line.iloc[-1],
        "signal": signal_line.iloc[-1],
        "histogram": histogram.iloc[-1],
    }


def calculate_moving_averages(prices, periods=[20, 50, 200]):
    """Calculate Simple Moving Averages"""
    prices_series = pd.Series(prices)
    mas = {}
    for period in periods:
        if len(prices_series) >= period:
            mas[f"sma_{period}"] = prices_series.rolling(window=period).mean().iloc[-1]
        else:
            mas[f"sma_{period}"] = None
    return mas


def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    prices_series = pd.Series(prices)
    sma = prices_series.rolling(window=period).mean()
    std = prices_series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return {
        "upper": upper.iloc[-1],
        "middle": sma.iloc[-1],
        "lower": lower.iloc[-1],
    }


def generate_signal(prices, symbol="BTC-USDT"):
    """Generate a trading signal based on all indicators"""
    if len(prices) < 50:
        return {"symbol": symbol, "signal": "INSUFFICIENT_DATA", "price": prices[-1] if prices else None}

    rsi = calculate_rsi(prices)
    macd = calculate_macd(prices)
    mas = calculate_moving_averages(prices)
    bb = calculate_bollinger_bands(prices)

    current_price = prices[-1]
    signals = []
    score = 0

    if rsi is not None:
        if rsi < 30:
            signals.append(f"RSI {rsi:.1f} - OVERSOLD (bullish)")
            score += 2
        elif rsi > 70:
            signals.append(f"RSI {rsi:.1f} - OVERBOUGHT (bearish)")
            score -= 2
        else:
            signals.append(f"RSI {rsi:.1f} - neutral")

    if macd["histogram"] > 0 and macd["macd"] > macd["signal"]:
        signals.append("MACD - bullish crossover")
        score += 2
    elif macd["histogram"] < 0 and macd["macd"] < macd["signal"]:
        signals.append("MACD - bearish crossover")
        score -= 2
    else:
        signals.append("MACD - neutral")

    if mas.get("sma_50"):
        if mas.get("sma_200"):
            if mas["sma_50"] > mas["sma_200"]:
                signals.append("SMA50 > SMA200 - golden cross (bullish)")
                score += 2
            else:
                signals.append("SMA50 < SMA200 - death cross (bearish)")
                score -= 2
        else:
            if current_price > mas["sma_50"]:
                signals.append("Price above SMA50 - bullish")
                score += 1
            else:
                signals.append("Price below SMA50 - bearish")
                score -= 1

    if mas.get("sma_20"):
        if current_price > mas["sma_20"]:
            signals.append("Price above SMA20 - bullish")
            score += 1
        else:
            signals.append("Price below SMA20 - bearish")
            score -= 1

    if bb["upper"] and bb["lower"]:
        if current_price <= bb["lower"]:
            signals.append("Price at lower BB - oversold")
            score += 1
        elif current_price >= bb["upper"]:
            signals.append("Price at upper BB - overbought")
            score -= 1

    if score >= 4:
        final = "STRONG BUY"
    elif score >= 2:
        final = "BUY"
    elif score <= -4:
        final = "STRONG SELL"
    elif score <= -2:
        final = "SELL"
    else:
        final = "NEUTRAL"

    return {
        "symbol": symbol,
        "price": current_price,
        "signal": final,
        "score": score,
        "indicators": {
            "rsi": round(rsi, 2) if rsi else None,
            "macd": {k: round(v, 2) for k, v in macd.items()},
            "moving_averages": {k: round(v, 2) for k, v in mas.items() if v},
            "bollinger_bands": {k: round(v, 2) for k, v in bb.items() if v},
        },
        "details": signals,
    }

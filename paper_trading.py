"""
Paper Trading Module
Simulated portfolio — users get $10,000 fake money to practice trading
based on the bot's signals. No real money involved.
"""
import json
import os
import time
from data.market_data import get_ticker_price

# In-memory store (Vercel serverless = ephemeral, but works for demo)
# For production: use Redis/Upstash (free tier)
_portfolio = {}


def get_portfolio(user_id):
    """Get or create a user's portfolio"""
    uid = str(user_id)
    if uid not in _portfolio:
        _portfolio[uid] = {
            "cash": 10000.0,  # Starting balance: $10,000 paper money
            "positions": {},  # {symbol: {qty, avg_price, entry_time}}
            "history": [],     # Trade history
            "initial_deposit": 10000.0,
            "created_at": time.time(),
        }
    return _portfolio[uid]


def deposit(user_id, amount):
    """Add paper money to balance"""
    if amount <= 0:
        return {"error": "Amount must be positive"}
    portfolio = get_portfolio(user_id)
    portfolio["cash"] += amount
    portfolio["history"].append({
        "type": "deposit",
        "amount": amount,
        "timestamp": time.time(),
        "balance_after": portfolio["cash"],
    })
    return {
        "status": "ok",
        "message": f"Deposited ${amount:,.2f} paper money",
        "new_balance": portfolio["cash"],
    }


def withdraw(user_id, amount):
    """Withdraw paper money"""
    if amount <= 0:
        return {"error": "Amount must be positive"}
    portfolio = get_portfolio(user_id)
    if amount > portfolio["cash"]:
        return {"error": f"Insufficient balance. You have ${portfolio['cash']:,.2f}"}
    portfolio["cash"] -= amount
    portfolio["history"].append({
        "type": "withdraw",
        "amount": amount,
        "timestamp": time.time(),
        "balance_after": portfolio["cash"],
    })
    return {
        "status": "ok",
        "message": f"Withdrew ${amount:,.2f} paper money",
        "new_balance": portfolio["cash"],
    }


def buy(user_id, symbol, amount_usd):
    """Buy a crypto with paper money"""
    if amount_usd <= 0:
        return {"error": "Amount must be positive"}
    portfolio = get_portfolio(user_id)
    if amount_usd > portfolio["cash"]:
        return {"error": f"Insufficient balance. You have ${portfolio['cash']:,.2f}"}

    price = get_ticker_price(symbol)
    if not price:
        return {"error": f"Could not get price for {symbol}"}

    qty = amount_usd / price
    if symbol in portfolio["positions"]:
        old_qty = portfolio["positions"][symbol]["qty"]
        old_cost = portfolio["positions"][symbol]["avg_price"] * old_qty
        new_qty = old_qty + qty
        new_avg = (old_cost + amount_usd) / new_qty
        portfolio["positions"][symbol] = {
            "qty": new_qty,
            "avg_price": new_avg,
            "entry_time": portfolio["positions"][symbol]["entry_time"],
        }
    else:
        portfolio["positions"][symbol] = {
            "qty": qty,
            "avg_price": price,
            "entry_time": time.time(),
        }

    portfolio["cash"] -= amount_usd
    portfolio["history"].append({
        "type": "buy",
        "symbol": symbol,
        "qty": qty,
        "price": price,
        "amount_usd": amount_usd,
        "timestamp": time.time(),
    })
    return {
        "status": "ok",
        "message": f"Bought {qty:.6f} {symbol.replace('-USDT', '')} at ${price:,.2f}",
        "position": portfolio["positions"][symbol],
        "cash_remaining": portfolio["cash"],
    }


def sell(user_id, symbol, amount_usd=None):
    """Sell a crypto position (full or partial)"""
    portfolio = get_portfolio(user_id)
    if symbol not in portfolio["positions"]:
        return {"error": f"No position in {symbol}"}

    position = portfolio["positions"][symbol]
    price = get_ticker_price(symbol)
    if not price:
        return {"error": f"Could not get price for {symbol}"}

    if amount_usd is None:
        # Sell all
        qty_to_sell = position["qty"]
    else:
        qty_to_sell = amount_usd / price
        if qty_to_sell > position["qty"]:
            qty_to_sell = position["qty"]

    proceeds = qty_to_sell * price
    portfolio["cash"] += proceeds

    # Calculate P&L
    cost_basis = qty_to_sell * position["avg_price"]
    pnl = proceeds - cost_basis
    pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0

    position["qty"] -= qty_to_sell
    if position["qty"] < 0.000001:
        del portfolio["positions"][symbol]

    portfolio["history"].append({
        "type": "sell",
        "symbol": symbol,
        "qty": qty_to_sell,
        "price": price,
        "amount_usd": proceeds,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "timestamp": time.time(),
    })
    return {
        "status": "ok",
        "message": f"Sold {qty_to_sell:.6f} {symbol.replace('-USDT', '')} at ${price:,.2f}",
        "proceeds": proceeds,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "cash_total": portfolio["cash"],
    }


def get_portfolio_summary(user_id):
    """Get full portfolio summary with current values"""
    portfolio = get_portfolio(user_id)
    total_value = portfolio["cash"]
    positions_list = []

    for symbol, pos in portfolio["positions"].items():
        price = get_ticker_price(symbol)
        if not price:
            price = pos["avg_price"]
        current_value = pos["qty"] * price
        cost_basis = pos["qty"] * pos["avg_price"]
        pnl = current_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
        total_value += current_value
        positions_list.append({
            "symbol": symbol,
            "qty": pos["qty"],
            "avg_price": pos["avg_price"],
            "current_price": price,
            "value": current_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })

    initial = portfolio["initial_deposit"]
    total_pnl = total_value - initial
    total_pnl_pct = (total_pnl / initial * 100) if initial > 0 else 0

    return {
        "cash": portfolio["cash"],
        "positions": positions_list,
        "total_value": total_value,
        "initial_deposit": initial,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "trade_count": len(portfolio["history"]),
    }


def get_trade_history(user_id, limit=10):
    """Get recent trade history"""
    portfolio = get_portfolio(user_id)
    history = portfolio["history"][-limit:]
    history.reverse()
    return history

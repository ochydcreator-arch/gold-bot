#!/usr/bin/env python3
"""
Simple trading analysis bot for XAUUSD.
- Fetches recent price data via yfinance
- Computes SMA short/long and RSI
- Sends a Telegram message with the analysis
Environment variables required:
- BOT_TOKEN
- CHAT_ID
"""
import os
import logging
from datetime import datetime
import requests
import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    logging.error("BOT_TOKEN and CHAT_ID must be set in environment.")
    raise SystemExit("Missing BOT_TOKEN / CHAT_ID")


TICKER = "XAUUSD=X"   # Yahoo Finance ticker for gold vs USD (adjust if needed)


def fetch_data(ticker=TICKER, period="7d", interval="30m"):
    """Download OHLCV data with yfinance."""
    logging.info("Fetching data for %s", ticker)
    df = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
    if df.empty:
        raise RuntimeError("No data returned from yfinance")
    df = df.dropna(subset=["Close"])
    return df


def sma(series: pd.Series, window: int):
    return series.rolling(window).mean()


def rsi(series: pd.Series, window: int = 14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / (avg_loss.replace(0, 1e-10))
    rsi = 100 - (100 / (1 + rs))
    return rsi


def analyze(df: pd.DataFrame):
    close = df["Close"]
    sma_short = sma(close, 5)   # 5 periods (~2.5 hours with 30m bars)
    sma_long = sma(close, 20)   # 20 periods
    rsi_series = rsi(close, 14)

    latest = {
        "time": close.index[-1],
        "price": float(close.iloc[-1]),
        "sma_short": float(sma_short.iloc[-1]) if not pd.isna(sma_short.iloc[-1]) else None,
        "sma_long": float(sma_long.iloc[-1]) if not pd.isna(sma_long.iloc[-1]) else None,
        "rsi": float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else None,
    }

    # simple signal logic
    signal = "neutral"
    if latest["sma_short"] and latest["sma_long"] and latest["rsi"] is not None:
        if latest["sma_short"] > latest["sma_long"] and latest["rsi"] < 70:
            signal = "BUY"
        elif latest["sma_short"] < latest["sma_long"] and latest["rsi"] > 30:
            signal = "SELL"
        else:
            signal = "NEUTRAL"

    latest["signal"] = signal
    return latest


def format_message(result: dict):
    t = result["time"]
    # ensure timezone-naive or convert
    try:
        ts = t.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        ts = str(t)
    msg = (
        f"Analisis XAUUSD\n"
        f"Waktu: {ts}\n"
        f"Harga: {result['price']:.2f} USD\n"
        f"SMA(5): {result['sma_short']:.4f}\n"
        f"SMA(20): {result['sma_long']:.4f}\n"
        f"RSI(14): {result['rsi']:.2f}\n"
        f"Sinyal: {result['signal']}\n\n"
        f"(Dijalankan tiap 30 menit)"
    )
    return msg


def send_telegram(token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    resp = requests.post(url, json=payload, timeout=15)
    if not resp.ok:
        logging.error("Telegram API error: %s %s", resp.status_code, resp.text)
        resp.raise_for_status()
    logging.info("Message sent to Telegram.")


def main():
    try:
        df = fetch_data()
        result = analyze(df)
        msg = format_message(result)
        send_telegram(BOT_TOKEN, CHAT_ID, msg)
    except Exception as e:
        logging.exception("Error in bot run: %s", e)
        # Optionally send error to Telegram (commented out by default)
        # send_telegram(BOT_TOKEN, CHAT_ID, f"Bot error: {e}")


if __name__ == "__main__":
    main()

"""
Bot Analisis XAUUSD — versi GitHub Actions
Jalan sekali per dipanggil, kirim laporan ke Telegram, lalu selesai.
"""
import os, requests, yfinance as yf, pandas as pd
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID   = os.environ["CHAT_ID"]
SYMBOL    = "GC=F"
WIB       = timezone(timedelta(hours=7))

def kirim(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text,
                                 "parse_mode": "Markdown"}, timeout=30)
    print("Status kirim:", r.status_code)

def hitung_rsi(close, period=14):
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    return float((100 - 100 / (1 + gain / loss)).iloc[-1])

def analisis():
    df = yf.download(SYMBOL, period="5d", interval="15m", progress=False)
    if df.empty or len(df) < 60:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    close = df["Close"]
    harga = float(close.iloc[-1])
    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    rsi   = hitung_rsi(close)
    recent = df.tail(40)
    resistance = float(recent["High"].max())
    support    = float(recent["Low"].min())

    skor, alasan = 0, []
    if harga > sma20 and sma20 > sma50:
        skor += 2; alasan.append("✅ Trend NAIK (Harga > SMA20 > SMA50)")
    elif harga < sma20 and sma20 < sma50:
        skor -= 2; alasan.append("❌ Trend TURUN (Harga < SMA20 < SMA50)")
    else:
        alasan.append("➖ Trend belum jelas")

    if rsi < 30:
        skor += 2; alasan.append(f"✅ RSI {rsi:.1f} OVERSOLD — potensi rebound")
    elif rsi > 70:
        skor -= 2; alasan.append(f"❌ RSI {rsi:.1f} OVERBOUGHT — potensi koreksi")
    else:
        alasan.append(f"➖ RSI {rsi:.1f} netral")

    if (harga - support) / harga * 100 < 0.15:
        skor += 1; alasan.append("✅ Harga di dekat SUPPORT")
    if (resistance - harga) / harga * 100 < 0.15:
        skor -= 1; alasan.append("❌ Harga di dekat RESISTANCE")

    if skor >= 3:    sinyal, emoji = "BUY", "🟢"
    elif skor <= -3: sinyal, emoji = "SELL", "🔴"
    else:            sinyal, emoji = "NETRAL / WAIT", "⚪"

    return dict(harga=harga, sma20=sma20, sma50=sma50, rsi=rsi,
                support=support, resistance=resistance,
                sinyal=sinyal, emoji=emoji, skor=skor, alasan=alasan)

def main():
    h = analisis()
    if not h:
        kirim("❌ Gagal mengambil data market"); return
    jam = datetime.now(WIB).strftime("%d %b %H:%M")
    msg = (
        f"📊 *ANALISIS XAUUSD*\n🕒 {jam} WIB\n\n"
        f"💰 Harga: `{h['harga']:.2f}`\n"
        f"📈 SMA20: `{h['sma20']:.2f}` | 📉 SMA50: `{h['sma50']:.2f}`\n"
        f"⚡ RSI(14): `{h['rsi']:.1f}`\n"
        f"🧱 Resistance: `{h['resistance']:.2f}`\n"
        f"🛡️ Support: `{h['support']:.2f}`\n\n"
        f"{h['emoji']} *SINYAL: {h['sinyal']}* (skor {h['skor']:+d})\n\n"
        + "\n".join(h["alasan"])
        + "\n\n⚠️ _Edukasi, bukan saran finansial_"
    )
    kirim(msg)

if __name__ == "__main__":
    main()

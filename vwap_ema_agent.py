#!/usr/bin/env python3
"""VWAP + EMA 9/21 Crossover Trading Agent"""
import os, time, logging, json
from datetime import datetime, timezone
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

vault = {}
for line in open("/root/penelope_vault.env"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        vault[k.strip()] = v.strip()

ALPACA_KEY = vault.get("ALPACA_API_KEY","")
ALPACA_SECRET = vault.get("ALPACA_SECRET_KEY","")
ALPACA_BASE = vault.get("ALPACA_BASE_URL","https://paper-api.alpaca.markets")
TG_TOKEN = vault.get("TELEGRAM_BOT_TOKEN","8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k")
TG_CHAT = vault.get("TELEGRAM_CHAT_ID","6183015901")
WATCHLIST = ["SPY","QQQ","AAPL","NVDA","TSLA","AMD","MSFT","META","AMZN","GOOGL"]
RISK_PCT = 0.02
SCAN_INTERVAL = 60

def tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id":TG_CHAT,"text":f"[VWAP] {msg}"},timeout=10)
    except: pass

def get_bars(sym, limit=50):
    headers = {"APCA-API-KEY-ID":ALPACA_KEY,"APCA-API-SECRET-KEY":ALPACA_SECRET}
    url = f"{ALPACA_BASE}/v2/stocks/{sym}/bars"
    params = {"timeframe":"5Min","limit":limit,"feed":"iex"}
    r = requests.get(url, headers=headers, params=params, timeout=10)
    if r.status_code != 200: return []
    return r.json().get("bars",[])

def ema(prices, period):
    if len(prices) < period: return None
    k = 2/(period+1)
    e = sum(prices[:period])/period
    for p in prices[period:]: e = p*k + e*(1-k)
    return e

def vwap(bars):
    tv, tv2 = 0, 0
    for b in bars:
        typ = (b["h"]+b["l"]+b["c"])/3
        tv += typ*b["v"]
        tv2 += b["v"]
    return tv/tv2 if tv2 else None

def get_account():
    headers = {"APCA-API-KEY-ID":ALPACA_KEY,"APCA-API-SECRET-KEY":ALPACA_SECRET}
    r = requests.get(f"{ALPACA_BASE}/v2/account", headers=headers, timeout=10)
    return r.json()

def place_order(sym, qty, side, stop, take_profit):
    headers = {"APCA-API-KEY-ID":ALPACA_KEY,"APCA-API-SECRET-KEY":ALPACA_SECRET,"Content-Type":"application/json"}
    order = {"symbol":sym,"qty":str(qty),"side":side,"type":"market","time_in_force":"day",
             "order_class":"bracket","stop_loss":{"stop_price":str(round(stop,2))},
             "take_profit":{"limit_price":str(round(take_profit,2))}}
    r = requests.post(f"{ALPACA_BASE}/v2/orders", headers=headers, json=order, timeout=10)
    return r.json()

def session_active():
    now = datetime.now(timezone.utc)
    wday = now.weekday()
    if wday >= 5: return False
    h, m = now.hour, now.minute
    open_min = 9*60+35
    close_min = 15*60+45
    cur_min = h*60+m
    return open_min <= cur_min <= close_min

log.info("VWAP+EMA agent started")
tg("VWAP+EMA agent online - watching " + ",".join(WATCHLIST))

daily_pnl = 0
while True:
    try:
        if not session_active():
            now = datetime.now(timezone.utc)
            if now.hour == 16 and now.minute < 2 and daily_pnl != 0:
                tg(f"Daily summary: PnL={daily_pnl:+.2f}")
                daily_pnl = 0
            time.sleep(60)
            continue

        acct = get_account()
        equity = float(acct.get("equity", 35000))

        for sym in WATCHLIST:
            try:
                bars = get_bars(sym, 60)
                if len(bars) < 22: continue
                closes = [b["c"] for b in bars]
                e9 = ema(closes, 9)
                e21 = ema(closes, 21)
                e55 = ema(closes, 55) if len(closes)>=55 else None
                vw = vwap(bars)
                prev_closes = [b["c"] for b in bars[:-1]]
                pe9 = ema(prev_closes, 9)
                pe21 = ema(prev_closes, 21)
                if not all([e9,e21,vw,pe9,pe21]): continue
                price = closes[-1]
                atr = sum(abs(b["h"]-b["l"]) for b in bars[-14:])/14

                # LONG signal
                if pe9 <= pe21 and e9 > e21 and price > vw and (e55 is None or price > e55):
                    qty = max(1, int((equity*RISK_PCT)/atr))
                    stop = price - atr
                    tp = price + 2*atr
                    r = place_order(sym, qty, "buy", stop, tp)
                    if "id" in r:
                        msg = f"LONG {sym} qty={qty} @ {price:.2f} stop={stop:.2f} tp={tp:.2f}"
                        log.info(msg); tg(msg)

                # SHORT signal
                elif pe9 >= pe21 and e9 < e21 and price < vw and (e55 is None or price < e55):
                    qty = max(1, int((equity*RISK_PCT)/atr))
                    stop = price + atr
                    tp = price - 2*atr
                    r = place_order(sym, qty, "sell", stop, tp)
                    if "id" in r:
                        msg = f"SHORT {sym} qty={qty} @ {price:.2f} stop={stop:.2f} tp={tp:.2f}"
                        log.info(msg); tg(msg)
            except Exception as e:
                log.warning(f"{sym}: {e}")

        time.sleep(SCAN_INTERVAL)
    except Exception as e:
        log.error(f"Main loop error: {e}")
        time.sleep(30)


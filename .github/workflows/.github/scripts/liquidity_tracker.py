import requests
import json
import datetime
import os

def get_liquidations(symbol='BTC'):
    try:
        r = requests.get(
            'https://open-api.coinglass.com/public/v2/liquidation_chart',
            params={'time_type': '24hour', 'symbol': symbol},
            headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = r.json()
        if data.get('code') == '0' and 'data' in data:
            d = data['data']
            long_liq  = sum(float(x.get('longVolUsd', 0))  for x in d.get('list', []))
            short_liq = sum(float(x.get('shortVolUsd', 0)) for x in d.get('list', []))
            return long_liq, short_liq
    except Exception as e:
        print(f"Liq error: {e}")
    return 0, 0

def get_order_book(symbol='BTCUSDT'):
    try:
        r = requests.get('https://api.binance.com/api/v3/depth',
            params={'symbol': symbol, 'limit': 50}, timeout=10)
        data = r.json()
        bid = sum(float(b[1]) for b in data.get('bids', []))
        ask = sum(float(a[1]) for a in data.get('asks', []))
        total = bid + ask
        if total == 0: return 0, 0, 0
        bp = bid/total*100
        return bp, 100-bp, bp - (100-bp)
    except: return 0, 0, 0

def get_funding(symbol='BTCUSDT'):
    try:
        r = requests.get('https://fapi.binance.com/fapi/v1/fundingRate',
            params={'symbol': symbol, 'limit': 1}, timeout=10)
        data = r.json()
        if data: return float(data[0].get('fundingRate', 0)) * 100
    except: pass
    return 0

def get_oi(symbol='BTCUSDT'):
    try:
        r = requests.get('https://fapi.binance.com/fapi/v1/openInterest',
            params={'symbol': symbol}, timeout=10)
        return float(r.json().get('openInterest', 0))
    except: return 0

def calculate(pair, short):
    score = 0
    details = {}
    long_liq, short_liq = get_liquidations(short)
    total = long_liq + short_liq
    details['long_liq_24h']  = round(long_liq, 2)
    details['short_liq_24h'] = round(short_liq, 2)
    details['total_liq_24h'] = round(total, 2)
    if total > 0:
        lr = long_liq / total * 100
        details['long_liq_ratio_pct'] = round(lr, 2)
        if   lr < 30: score += 35
        elif lr < 40: score += 20
        elif lr < 50: score += 10
        elif lr > 70: score -= 35
        elif lr > 60: score -= 20
        elif lr > 50: score -= 10
    bid, ask, imb = get_order_book(pair)
    details['bid_pct']   = round(bid, 2)
    details['ask_pct']   = round(ask, 2)
    details['imbalance'] = round(imb, 2)
    if   imb >  15: score += 25
    elif imb >   5: score += 12
    elif imb < -15: score -= 25
    elif imb <  -5: score -= 12
    funding = get_funding(pair)
    details['funding_rate_pct'] = round(funding, 4)
    if   funding >  0.05: score -= 20
    elif funding >  0.02: score -= 10
    elif funding < -0.05: score += 20
    elif funding < -0.02: score += 10
    details['open_interest'] = get_oi(pair)
    return max(-100, min(100, score)), details

def direction(s):
    if s >  30: return 'STRONG_BULLISH'
    if s >  15: return 'BULLISH'
    if s < -30: return 'STRONG_BEARISH'
    if s < -15: return 'BEARISH'
    return 'NEUTRAL'

def action(s):
    if s >  30: return 'BUY_BIAS'
    if s < -30: return 'SELL_BIAS'
    return 'NEUTRAL'

if __name__ == '__main__':
    btc_score, btc_details = calculate('BTCUSDT', 'BTC')
    eth_score, eth_details = calculate('ETHUSDT', 'ETH')
    result = {
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'BTC': {'liquidity_score': btc_score, 'direction': direction(btc_score),
                'recommended_action': action(btc_score), 'details': btc_details},
        'ETH': {'liquidity_score': eth_score, 'direction': direction(eth_score),
                'recommended_action': action(eth_score), 'details': eth_details},
        'version': '1.0'
    }
    print(f"BTC: {btc_score} ETH: {eth_score}")
    os.makedirs('docs', exist_ok=True)
    with open('docs/liquidity_data.json', 'w') as f:
        json.dump(result, f, indent=2)
    print("File written")

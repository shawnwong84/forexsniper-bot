import requests
import json
import datetime
import os

def get_coingecko(coin_id):
    try:
        r = requests.get(
            f'https://api.coingecko.com/api/v3/simple/price',
            params={'ids': coin_id, 'vs_currencies': 'usd',
                    'include_24hr_change': 'true',
                    'include_24hr_vol': 'true',
                    'include_market_cap': 'true'},
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=15)
        if r.status_code == 200:
            return r.json().get(coin_id, {})
    except Exception as e:
        print(f"CoinGecko {coin_id}: {e}")
    return {}

def get_fear_greed():
    try:
        r = requests.get('https://api.alternative.me/fng/?limit=2',
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code == 200:
            data = r.json()['data']
            return int(data[0]['value']), data[0]['value_classification']
    except Exception as e:
        print(f"F&G: {e}")
    return 50, 'Neutral'

def calculate(coin_id):
    score = 0
    details = {}
    cg = get_coingecko(coin_id)
    if cg:
        price = cg.get('usd', 0)
        change_24h = cg.get('usd_24h_change', 0)
        volume = cg.get('usd_24h_vol', 0)
        details['price'] = price
        details['change_24h'] = round(change_24h, 2)
        details['volume_24h'] = volume
        details['market_cap'] = cg.get('usd_market_cap', 0)
        if change_24h > 5: score += 25
        elif change_24h > 2: score += 12
        elif change_24h < -5: score -= 25
        elif change_24h < -2: score -= 12
    return max(-100, min(100, score)), details

def direction(s):
    if s > 30: return 'STRONG_BULLISH'
    if s > 15: return 'BULLISH'
    if s < -30: return 'STRONG_BEARISH'
    if s < -15: return 'BEARISH'
    return 'NEUTRAL'

def action(s):
    if s > 30: return 'BUY_BIAS'
    if s < -30: return 'SELL_BIAS'
    return 'NEUTRAL'

if __name__ == '__main__':
    print("ForexSniper Liquidity Tracker v2")
    btc_score, btc_details = calculate('bitcoin')
    eth_score, eth_details = calculate('ethereum')
    fg_value, fg_class = get_fear_greed()
    
    # Adjust scores by fear/greed
    if fg_value < 25:
        btc_score += 15
        eth_score += 15
    elif fg_value > 75:
        btc_score -= 15
        eth_score -= 15
    
    btc_score = max(-100, min(100, btc_score))
    eth_score = max(-100, min(100, eth_score))
    
    result = {
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'fear_greed': {'value': fg_value, 'classification': fg_class},
        'BTC': {
            'liquidity_score': btc_score,
            'direction': direction(btc_score),
            'recommended_action': action(btc_score),
            'details': btc_details
        },
        'ETH': {
            'liquidity_score': eth_score,
            'direction': direction(eth_score),
            'recommended_action': action(eth_score),
            'details': eth_details
        },
        'version': '2.0'
    }
    print(f"BTC: {btc_score} | ETH: {eth_score} | F&G: {fg_value}")
    os.makedirs('docs', exist_ok=True)
    with open('docs/liquidity_data.json', 'w') as f:
        json.dump(result, f, indent=2)
    print("Done")

"""Fetch representative baseline data from HoneyDB API and compute baseline metrics.

USAGE:
 - Set environment variables in PowerShell before running:
     $env:HONEYDB_API_KEY = '<your api key>'
     $env:HONEYDB_API_SECRET = '<your api secret>'
 - Then run:
     python .\scripts\fetch_honeydb_baseline.py --days 7

This script will try a few common auth header patterns and save raw JSON to
scripts/baseline_raw.json and computed baseline to scripts/baseline.json.

Security: Do NOT paste API keys into chat. Set them in your local environment.
If you want me to run this here with keys, explicitly confirm and paste keys via a secure channel.
"""
import os
import sys
import time
import json
import argparse
from datetime import datetime, timedelta
import requests

ROOT = os.path.dirname(__file__)
OUT_RAW = os.path.join(ROOT, 'baseline_raw.json')
OUT_BASE = os.path.join(ROOT, 'baseline.json')

def get_auth_headers(key, secret):
    # Try a couple of plausible header forms
    return [
        {'X-Api-Key': key, 'X-Api-Secret': secret},
        {'Authorization': f'Token {key}'},
        {'Authorization': f'Bearer {key}'}
    ]

def try_fetch(base_url, headers, params=None, endpoint='/threats'):
    url = base_url.rstrip('/') + endpoint
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
        else:
            return {'__error__': f'status {r.status_code}', 'text': r.text}
    except Exception as e:
        return {'__error__': str(e)}

def compute_baselines_from_threats(threats):
    # threats: list/dict depending on API. We'll try to extract counts and simple proxies.
    # We'll compute:
    # - avg_events_per_day, service mix if available
    try:
        items = threats if isinstance(threats, list) else threats.get('data') or threats.get('results') or []
    except Exception:
        items = []
    total = len(items)
    dates = []
    services = {}
    for it in items:
        ts = it.get('timestamp') or it.get('created_at') or it.get('time')
        if ts:
            dates.append(ts)
        svc = it.get('service') or it.get('protocol')
        if svc:
            services[svc] = services.get(svc, 0) + 1
    # simple baselines
    baseline = {
        'source_count': total,
        'service_mix': services,
        'sample_window_days': None
    }
    return baseline

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='https://honeydb.io', help='HoneyDB base URL')
    parser.add_argument('--days', type=int, default=7, help='lookback window in days')
    args = parser.parse_args()

    key = os.environ.get('HONEYDB_API_KEY') or os.environ.get('HONEYDB_API_ID')
    secret = os.environ.get('HONEYDB_API_SECRET') or os.environ.get('HONEYDB_API_KEY_SECRET') or ''
    if not key:
        print('HONEYDB_API_KEY not set in environment. Aborting. Set env var and retry.')
        sys.exit(2)

    headers_list = get_auth_headers(key, secret)

    # timeframe
    to_ts = int(time.time())
    from_ts = int((datetime.utcnow() - timedelta(days=args.days)).timestamp())
    params = {'from': from_ts, 'to': to_ts, 'limit': 1000}

    results = None
    for h in headers_list:
        print('Trying headers:', list(h.keys()))
        res = try_fetch(args.base, h, params=params, endpoint='/threats')
        if isinstance(res, dict) and res.get('__error__'):
            print('Attempt failed:', res.get('__error__'))
            continue
        results = res
        print('Fetch succeeded with headers:', list(h.keys()))
        break

    if results is None:
        print('All attempts failed. Inspect endpoints and API key format. Exiting.')
        sys.exit(1)

    with open(OUT_RAW, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print('Wrote raw baseline to', OUT_RAW)

    baseline = compute_baselines_from_threats(results)
    baseline['fetched_at'] = datetime.utcnow().isoformat() + 'Z'
    baseline['lookback_days'] = args.days
    with open(OUT_BASE, 'w', encoding='utf-8') as f:
        json.dump(baseline, f, indent=2)
    print('Wrote baseline summary to', OUT_BASE)

if __name__ == '__main__':
    main()

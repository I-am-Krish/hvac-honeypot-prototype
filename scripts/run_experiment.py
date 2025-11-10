#!/usr/bin/env python3
"""Run a long experiment: simulate attacker and benign activity against local honeypot
and run the engagement analyzer at the end.

Usage: python scripts/run_experiment.py --duration 3600
"""
import requests, time, argparse, random, subprocess, sys, os

BASE = os.environ.get('HVAC_BASE', 'http://127.0.0.1:5000')

def hit(power, role='attacker', pause=0.5):
    headers = {'User-Agent': 'attacker-bot/1.0'}
    try:
        r = requests.post(BASE + '/actuator/heater', json={'power': float(power), 'role': role}, headers=headers, timeout=5)
        # print short status
        # print(role, power, r.status_code)
    except Exception as e:
        # print('request failed', e)
        pass
    time.sleep(pause)

def attacker_pattern(duration):
    # run various patterns until duration elapsed
    start = time.time()
    while time.time() - start < duration:
        # burst: 10 fast high-power requests
        for _ in range(10):
            hit(1.0, 'attacker', pause=0.2)
        # slow-and-low: small power every few seconds
        for _ in range(20):
            hit(0.1, 'attacker', pause=1.5)
        # randomized short pause
        time.sleep(random.uniform(2,5))

def benign_pattern(duration):
    # background benign operator making periodic reasonable adjustments
    start = time.time()
    while time.time() - start < duration:
        hit(0.5, 'tester', pause=10)

def run(duration):
    # run benign operator in background thread (subprocess) to avoid threading complexity
    ben = subprocess.Popen([sys.executable, os.path.join('scripts', 'benign_operator.py')], cwd=os.getcwd()) if os.path.exists(os.path.join('scripts','benign_operator.py')) else None
    try:
        attacker_pattern(duration)
    finally:
        if ben:
            try:
                ben.terminate()
            except Exception:
                pass

    # run analyzer
    try:
        print('Running analyzer...')
        subprocess.run([sys.executable, os.path.join('scripts', 'engagement_analysis.py'), '--plots', '--simulate-normal'], check=False)
    except Exception as e:
        print('Analyzer failed:', e)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--duration', type=int, default=3600, help='Duration in seconds to run the attack')
    p.add_argument('--test-short', action='store_true', help='Run a short test (30s)')
    args = p.parse_args()
    if args.test_short:
        run(30)
    else:
        run(args.duration)

#!/usr/bin/env python3
# attacker/slow_and_low.py — low-and-slow stealthy attacker
import requests, time, random
BASE="http://hvac_honeypot:5000"
ROLE="attacker"

def slow(rate=0.2, duration=300):
    # rate: requests per sec (0.2 -> 1 every 5s)
    interval = 1.0/max(0.001, rate)
    end = time.time() + duration
    while time.time() < end:
        p = 0.6 + random.uniform(-0.1, 0.2)  # near-normal but slightly abnormal
        try:
            requests.post(BASE + "/actuator/heater", json={"power": p, "role": ROLE}, timeout=5)
        except:
            pass
        time.sleep(interval)

if __name__ == "__main__":
    slow()
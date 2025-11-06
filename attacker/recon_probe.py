#!/usr/bin/env python3
# attacker/recon_probe.py
import requests,time

BASE="http://hvac_honeypot:5000"
ROLE="attacker"

def probe(rate=2.0, duration=30):
    interval = 1.0 / max(1, rate)
    end = time.time() + duration
    while time.time() < end:
        try:
            r = requests.get(BASE+"/sensor/temperature", timeout=2.0)
        except Exception as e:
            pass
        time.sleep(interval)

if __name__ == "__main__":
    probe(rate=5.0, duration=30)
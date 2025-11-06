#!/usr/bin/env python3
# attacker/burst_attack.py
import requests, time
BASE="http://hvac_honeypot:5000"
ROLE="attacker"

def burst(burst_size=50, inter_burst=10):
    for b in range(3):
        for i in range(burst_size):
            try:
                r = requests.post(BASE+"/actuator/heater", json={"power": 1.0, "role": ROLE}, timeout=2)
            except:
                pass
        time.sleep(inter_burst)

if __name__ == "__main__":
    burst()
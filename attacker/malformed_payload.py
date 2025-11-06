#!/usr/bin/env python3
# attacker/malformed_payload.py
import requests, time
BASE="http://hvac_honeypot:5000"
ROLE="attacker"

def malformed(count=50):
    for i in range(count):
        # missing "power" key, or wrong type
        payloads = [
            {"role": ROLE}, 
            {"power": "high", "role": ROLE}, 
            {"power": None, "role": ROLE}
        ]
        p = payloads[i % len(payloads)]
        try:
            requests.post(BASE + "/actuator/heater", json=p, timeout=2)
        except:
            pass
        time.sleep(0.2)

if __name__ == "__main__":
    malformed()
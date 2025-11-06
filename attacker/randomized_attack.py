#!/usr/bin/env python3
# attacker/randomized_attack.py
import requests, time, random
BASE="http://hvac_honeypot:5000"
ROLE="attacker"

def randomized(interactions=200, min_wait=0.05, max_wait=1.0):
    for i in range(interactions):
        p = random.choice([0.0, 0.2, 0.5,1.0])
        try:
            requests.post(BASE + "/actuator/heater", json={"power":p, "role": ROLE}, timeout=2)
        except:
            pass
        time.sleep(random.uniform(min_wait, max_wait))

if __name__ == "__main__":
    randomized()
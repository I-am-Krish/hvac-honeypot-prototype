#!/usr/bin/env python3
# Simple scripted attacker that performs a setpoint flood and sensor spoof (demo purposes)
import requests, time

BASE="http://hvac_honeypot:5000"

def set_power(p, role="attacker"):
    r = requests.post(BASE+"/actuator/heater", json={"power": p, "role": role})
    print("set_power", p, "->", r.json())

def run_flood():
    print("Starting setpoint flood...")
    for i in range(20):
        set_power(1.0)
        time.sleep(0.2)

def run_spoof():
    # In this simple prototype, there's no sensor POST endpoint by default.
    # You can emulate spoofing by rapidly toggling setpoints or by modifying logs directly.
    print("Running spoof-like actions (set low power repeatedly)...")
    for i in range(10):
        set_power(0.0)
        time.sleep(0.5)

if __name__ == "__main__":
    time.sleep(1.0)
    run_flood()
    time.sleep(1.0)
    run_spoof()

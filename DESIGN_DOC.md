# Design Doc — HVAC Honeypot Prototype (1 page)

## Goal
Build a single-room HVAC honeypot prototype: simulated thermal model + SCC safety filter + simple API + attacker script. Deliverable: runnable demo that shows SCC overrides and logs attacker actions.

## Scope
- Simulator: first-order RC thermal model
- SCC: enforces T_min and T_max, smooth corrections
- Frontend: HTTP endpoints for sensor & actuator
- Attacker: scripted scenarios (sensor spoofing and actuator flooding)
- Logging: CSV/SQLite with timestamps, requested vs applied commands

## Success criteria (measurable)
- Simulator and frontend run locally
- SCC prevents temperature from leaving bounds during attack scenario
- Demo script produces logs: /logs/attack_demo.csv with at least one SCC override event

## Chosen tech
Python 3.10, Flask, plain CSV logging (SQLite optional), Docker (optional) for isolation.

## Minimal timeline
Step-1: this doc + repo skeleton
Step-2: 5-day sprint (detailed tasks) — see Step-2 plan.

## Risks & containment
(See RISK_CHECKLIST.md)

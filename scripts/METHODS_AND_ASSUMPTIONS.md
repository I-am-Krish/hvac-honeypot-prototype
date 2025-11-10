Methods and assumptions — comparison of adaptive honeypot vs baseline

## Purpose

This short document records the exact metric definitions, data sources, and assumptions used to compute the comparison chart and CSV produced by `scripts/compare_with_baseline.py`.

## Data sources

- Local experiment outputs (primary):
  - `logs/events.csv` — canonical event log produced by the honeypot during the experiment. Used for sessionization and per-event signals.
  - `scripts/engagement_sessions.csv` — session summary produced by `scripts/engagement_analysis.py`.
- Baseline provenance (public sources):
  - HoneyDB public statistics: https://honeydb.io/stats (used to justify event-volume and service-mix assumptions).
  - The Honeynet Project (research & reports): https://www.honeynet.org/ (used to support heuristics around detection & adaptation behavior).
  - Local baseline file: `scripts/baseline.json` — contains the numeric baseline values used for plotting and their short rationales.

## Metric definitions (how computed)

1. Engagement Duration (avg)

   - What: mean session duration in seconds across all detected sessions.
   - How: read `scripts/engagement_sessions.csv`, take the `duration_s` column and compute the arithmetic mean. Implemented in `metric_engagement_duration()`.
   - Caveats: heavily influenced by outliers (very long attacker sessions). Consider using median or trimming for alternate views.

2. Detection Resistance (heuristic probability 0..1)

   - What: proxy for the probability that an attacker did not identify the honeypot and disengage.
   - How (refined heuristic): group events by `client_ip` (fallback `role`). For each client-session:
     - If an SCC override event occurs, check whether the client continued interacting for >= 3 events after the first override; if yes, mark the session as "resistant".
     - If no override observed and the session had >1 events, mark as "resistant".
     - Aggregate: fraction of sessions marked resistant.
   - Motivation: immediate session termination after an override is a signal of detection. This is heuristic — not a ground-truth identification.

3. Policy Adaptation Latency (seconds)

   - What: typical time until the honeypot/SCC responded (first override) after the session started.
   - How: for each client-session, define session start as the first non-system event (or `engagement_start` if present). Find the first override event timestamp, compute difference. Take the median across sessions with an override. Implemented in `metric_policy_adaptation_latency()`.
   - Caveats: zero-second values can arise when system markers and override events share timestamps; consider a floor (e.g., treat <=1s as 'instant') if you prefer.

4. Resource Overhead (normalized score 0..1)

   - What: proxy for CPU + memory cost of running the honeypot system.
   - How (snapshot): if a `logs/resource_usage.csv` exists (expected columns: `timestamp,cpu_percent,memory_mb`) the script uses its mean values. Otherwise the script samples running Python processes 5 times (0.2s interval) and averages CPU% and resident memory (MB). Normalization: cpu/100 and mem/1000MB combined as (0.6*cpu_norm + 0.4*mem_norm).
   - Caveats: this is a quick snapshot. For rigorous comparison, run a time-series monitor for the whole experiment and compute mean/peak.

5. Threat Intelligence Yield (0..1)
   - What: proxy for the quality/diversity of captured attack signals.
   - How: compute normalized Shannon entropy for `user_agent`, `request_path`, and `client_id`, plus a payload-signature diversity computed from `requested_power|applied_power`. Combine as weighted sum (0.3 UA, 0.4 path, 0.2 client_id, 0.1 payload).
   - Caveats: entropy measures diversity, not label quality. To assess intelligence value you should cluster payloads and count novel indicators, or apply labeling (e.g., malware vs scanner signatures).

## Baseline derivation

- The `scripts/baseline.json` file holds the current baseline numeric values. Those numbers are conservative, literature-informed defaults derived from HoneyDB public stats and Honeynet reports:
  - engagement_duration_s: 300 (5 minutes) — conservative median for low-interaction honeypots capturing SSH/HTTP interactions.
  - detection_resistance: 0.35 — heuristic baseline for low-interaction honeypots from literature and typical scanner behavior.
  - policy_adaptation_latency_s: 180 (3 minutes) — baseline representing manual or periodic policy updates in many operational setups.
  - resource_overhead_score: 0.2 — small normalized cost for low-resource honeypot deployments.
  - threat_intel_yield: 0.4 — moderate yield expected for varied internet-facing honeypot networks.

## How to reproduce and improve baselines

1. If you want data-driven baselines, fetch raw interaction records from HoneyDB via their API (the repository includes `scripts/fetch_honeydb_baseline.py` to help). The API requires registration and an API key (see https://honeydb.io/docs/api).
2. To improve resource-overhead comparisons, run a background monitor that writes `logs/resource_usage.csv` (timestamp,cpu_percent,memory_mb) during the experiment and re-run `compare_with_baseline.py`.
3. To improve detection-resistance and threat-intel yield, label a subset of captured sessions (manually or via rules) and compute true positive yields and identification rates.

## Files produced by the toolchain

- `scripts/engagement_sessions.csv` — sessionization produced by `scripts/engagement_analysis.py` (input to comparator).
- `scripts/comparison_results.csv` — the numeric comparison between baseline and adaptive run.
- `scripts/plots/comparison_bar.png` — visualization used in the report.
- `scripts/baseline.json` — baseline metadata and numbers (editable).

## Notes and disclaimers

All metrics here are heuristics and proxies intended to support reporting and decision-making; they are not formal, peer-reviewed definitions of attacker identification or intelligence quality. Where a metric requires ground-truth (e.g., whether an attacker truly identified the honeypot), additional instrumentation or labeling is required.

If you want, I can now:

- run `scripts/fetch_honeydb_baseline.py` locally on your machine (you supply the API key via env var) to compute empirical baselines, or
- implement a short resource monitor that writes `logs/resource_usage.csv` during the next experiment run, then re-run the comparison.

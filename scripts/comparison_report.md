# Adaptive honeypot — comparison report

This short report bundles the numeric comparison, the comparison plot, and the measurement methods.

## Files produced

- `scripts/comparison_results.csv` — numeric comparison between baseline and adaptive run.
- `scripts/plots/comparison_bar.png` — visual bar chart (normalized 0..1) comparing metrics.
- `scripts/METHODS_AND_ASSUMPTIONS.md` — detailed methods and metric definitions.
- `logs/resource_usage.csv` — time-series resource samples (if present) used to compute resource-overhead.

## Key notes

- If you want this as a one-page PDF, convert this markdown using your preferred tool (e.g., pandoc).

## Summary (numeric)

See `scripts/comparison_results.csv` for the exact numeric values produced by the comparator. Example columns:

- metric, baseline_value, adaptive_value, normalized_baseline, normalized_adaptive

## Visual

Open `scripts/plots/comparison_bar.png` to see the normalized comparison chart.

## Methods

For detailed metric definitions and assumptions see `scripts/METHODS_AND_ASSUMPTIONS.md`.

## Next steps

- If you provided HoneyDB credentials, the comparator can be re-run with empirical baselines after `scripts/fetch_honeydb_baseline.py` completes.
- To get continuous resource-overhead over the whole experiment, run `scripts/resource_monitor.py` during the experiment.

## Commands used in this run (PowerShell)

```powershell
python .\scripts\fetch_honeydb_baseline.py --days 7
python .\scripts\resource_monitor.py --duration 10 --interval 1
python .\scripts\compare_with_baseline.py
```

Generated on: <replace-with-run-timestamp>

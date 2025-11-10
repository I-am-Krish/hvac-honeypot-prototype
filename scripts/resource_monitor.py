#!/usr/bin/env python3
"""Simple resource monitor that samples CPU and memory and writes logs/resource_usage.csv

Usage:
  python scripts/resource_monitor.py --duration 30 --interval 1

Writes/append to: logs/resource_usage.csv with columns: timestamp,cpu_percent,memory_mb
"""
from __future__ import annotations
import argparse
import time
import csv
import os
from datetime import datetime

try:
    import psutil
except Exception:
    raise SystemExit("psutil is required. Install with: pip install psutil")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--duration", type=float, default=10.0, help="Total duration in seconds")
    p.add_argument("--interval", type=float, default=1.0, help="Sample interval in seconds")
    p.add_argument("--out", default=os.path.join("..","logs","resource_usage.csv"), help="Output CSV path relative to scripts/")
    args = p.parse_args()

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), args.out))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    header = ["timestamp","cpu_percent","memory_mb"]
    write_header = not os.path.exists(out_path)

    samples = max(1, int(args.duration / max(1e-6, args.interval)))
    start = time.time()

    with open(out_path, "a", newline="") as fh:
        writer = csv.writer(fh)
        if write_header:
            writer.writerow(header)

        while time.time() - start < args.duration:
            # cpu_percent over 0.1s to get instant value
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.Process().memory_info().rss / (1024*1024)
            ts = datetime.utcnow().isoformat() + "Z"
            writer.writerow([ts, f"{cpu:.2f}", f"{mem:.2f}"])
            fh.flush()
            time.sleep(args.interval)

    print(f"Wrote resource usage samples to: {out_path}")


if __name__ == '__main__':
    main()

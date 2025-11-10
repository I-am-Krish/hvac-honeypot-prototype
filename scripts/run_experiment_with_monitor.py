#!/usr/bin/env python3
"""Run an experiment while sampling resource usage, then run analyzer and comparator.

Usage:
  python scripts/run_experiment_with_monitor.py --duration 3600 --interval 1

What it does:
  - Starts `scripts/resource_monitor.py` in the background for (duration + 5s).
  - Runs `scripts/run_experiment.py --duration <duration>` (the existing experiment runner).
  - After experiment exits, runs `scripts/engagement_analysis.py --plots` to regenerate sessions/plots.
  - Runs `scripts/compare_with_baseline.py` to produce updated comparison outputs.

This automates end-to-end experiment -> metrics workflow and ensures the resource monitor covers the whole run.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
import os
import time


def run_cmd(cmd, cwd=None, check=True):
    print('RUN:', ' '.join(cmd))
    res = subprocess.run(cmd, cwd=cwd, shell=False)
    if check and res.returncode != 0:
        raise SystemExit(f'Command failed: {cmd} (rc={res.returncode})')
    return res.returncode


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--duration', type=int, default=60, help='Experiment duration in seconds')
    p.add_argument('--interval', type=float, default=1.0, help='Resource monitor sample interval (s)')
    p.add_argument('--simulate-normal', action='store_true', help='Pass --simulate-normal to engagement_analysis')
    args = p.parse_args()

    root = os.path.abspath(os.path.dirname(__file__))
    scripts_dir = root
    python = sys.executable or 'python'

    # Start resource monitor for duration + 5 seconds to cover wrap-up
    monitor_dur = args.duration + 5
    monitor_cmd = [python, os.path.join(scripts_dir, 'resource_monitor.py'), '--duration', str(monitor_dur), '--interval', str(args.interval)]

    print('Starting resource monitor for', monitor_dur, 's')
    monitor_proc = subprocess.Popen(monitor_cmd, cwd=scripts_dir)

    try:
        # Run the experiment runner
        exp_cmd = [python, os.path.join(scripts_dir, 'run_experiment.py'), '--duration', str(args.duration)]
        print('Starting experiment for', args.duration, 's')
        run_cmd(exp_cmd, cwd=os.path.dirname(root))

        # Wait a tiny bit to ensure monitor captures final writes
        print('Experiment finished; waiting 2s for monitors to flush')
        time.sleep(2)

        # Run analyzer
        analysis_cmd = [python, os.path.join(scripts_dir, 'engagement_analysis.py'), '--plots']
        if args.simulate_normal:
            analysis_cmd.append('--simulate-normal')
        print('Running engagement analysis...')
        run_cmd(analysis_cmd, cwd=os.path.dirname(root))

        # Run comparator
        comp_cmd = [python, os.path.join(scripts_dir, 'compare_with_baseline.py')]
        print('Running comparator...')
        run_cmd(comp_cmd, cwd=os.path.dirname(root))

        print('\nAll steps completed. Outputs:')
        print('- scripts/engagement_sessions.csv')
        print('- scripts/comparison_results.csv')
        print("- scripts/plots/comparison_bar.png and .svg")
        print('- logs/resource_usage.csv')

    finally:
        # Ensure monitor is terminated if still running
        if monitor_proc.poll() is None:
            print('Stopping resource monitor (pid:', monitor_proc.pid, ')')
            monitor_proc.terminate()
            try:
                monitor_proc.wait(timeout=5)
            except Exception:
                monitor_proc.kill()


if __name__ == '__main__':
    main()

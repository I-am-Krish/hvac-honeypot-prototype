"""Create a grouped bar chart comparing adaptive session durations vs simulated 'normal' durations.

This script loads `scripts/engagement_sessions.csv` and `logs/events.csv`,
recomputes the simulated normal 'time-to-cross' per session (same logic as
`engagement_analysis.py`), bins both duration lists using shared bin edges,
and draws a grouped bar chart (counts per bin) for clear comparison.

Outputs:
 - scripts/plots/aggregate_durations_barchart.png
 - scripts/plots/aggregate_durations_barchart.svg
"""
import os
import csv
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = os.path.dirname(__file__)
PLOTS = os.path.join(ROOT, 'plots')
os.makedirs(PLOTS, exist_ok=True)

# reuse simulator for normal honeypot simulation
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from simulator.room import RoomSimulator

SESSIONS_CSV = os.path.join(ROOT, 'engagement_sessions.csv')
LOG_PATH = os.path.join(os.path.dirname(ROOT), 'logs', 'events.csv')


def load_sessions(path=SESSIONS_CSV):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    return df


def load_events(path=LOG_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if 'ts' in df.columns:
        df['ts'] = df['ts'].astype(int)
    return df


def simulate_normal_time_for_session(df_events, client, start_ts, end_ts):
    sel = df_events[(df_events.get('client_ip', df_events.get('role')) == client) & (df_events['ts'] >= start_ts) & (df_events['ts'] <= end_ts)]
    if 'event_type' in sel.columns:
        sel = sel[sel['event_type'] == 'event']
    sel = sel.sort_values('ts').reset_index(drop=True)
    if sel.empty:
        return None
    # initial temperature
    if 'temperature' in sel.columns and not sel['temperature'].isnull().all():
        T0 = float(sel['temperature'].iloc[0])
    else:
        T0 = 22.0
    sim = RoomSimulator(T0=T0)
    crossed = None
    sim_time = 0.0
    for i, row in sel.iterrows():
        p = float(row.get('requested_power', 0) or 0)
        if i < len(sel) - 1:
            next_ts = int(sel.loc[i+1, 'ts'])
            gap = max(1, next_ts - int(row['ts']))
        else:
            gap = int(sim.dt)
        remaining = gap
        while remaining > 0:
            sim.step(P_heater=float(p))
            sim_time += sim.dt
            remaining -= sim.dt
            # boundaries from config were used elsewhere; use default comfortable bounds
            if sim.T < 18.0 or sim.T > 26.0:
                crossed = sim_time
                break
        if crossed is not None:
            break
    return crossed


def make_barchart(adaptive, normal, bins=10, out_png=os.path.join(PLOTS, 'aggregate_durations_barchart.png')):
    # compute shared bin edges
    all_vals = [v for v in (adaptive + normal) if v is not None]
    if not all_vals:
        raise ValueError('No duration values to plot')
    counts_a, edges = np.histogram(adaptive, bins=bins)
    counts_n, _ = np.histogram(normal, bins=edges)

    # bar positions
    x = np.arange(len(counts_a))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10,5))
    ax.bar(x - width/2, counts_a, width, label='Adaptive (recorded)', color='#4C72B0', edgecolor='k')
    ax.bar(x + width/2, counts_n, width, label='Normal (simulated)', color='#DD8452', edgecolor='k')

    # x-axis labels as bin ranges
    labels = [f"{int(edges[i])}-{int(edges[i+1])}s" for i in range(len(edges)-1)]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha='right')
    ax.set_xlabel('Duration bin (s)')
    ax.set_ylabel('Count')
    ax.set_title('Session duration distribution — adaptive vs normal (binned)')
    ax.legend()

    # annotate counts above bars
    for i in range(len(counts_a)):
        ax.annotate(str(counts_a[i]), xy=(x[i]-width/2, counts_a[i]), xytext=(0,4), textcoords='offset points', ha='center', va='bottom', fontsize=9)
        ax.annotate(str(counts_n[i]), xy=(x[i]+width/2, counts_n[i]), xytext=(0,4), textcoords='offset points', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_png.rsplit('.',1)[0] + '.svg')
    plt.close(fig)
    print('Wrote', out_png)


def main():
    sessions_df = load_sessions()
    events_df = load_events()

    adaptive = sessions_df['duration_s'].dropna().astype(float).tolist()

    normal_times = []
    for _, row in sessions_df.iterrows():
        client = row['client']
        start_ts = int(row['start_ts'])
        end_ts = int(row['end_ts'])
        t = simulate_normal_time_for_session(events_df, client, start_ts, end_ts)
        if t is not None:
            normal_times.append(float(t))

    # fallback: if no normal_times found, skip and create histogram of adaptive only
    if not normal_times:
        print('No simulated normal durations found; creating histogram-only barchart for adaptive')
        # create simple histogram and save as bar-like plot
        counts, edges = np.histogram(adaptive, bins=10)
        x = np.arange(len(counts))
        labels = [f"{int(edges[i])}-{int(edges[i+1])}s" for i in range(len(edges)-1)]
        fig, ax = plt.subplots(figsize=(10,5))
        ax.bar(x, counts, color='#4C72B0', edgecolor='k')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha='right')
        ax.set_xlabel('Duration bin (s)')
        ax.set_ylabel('Count')
        ax.set_title('Session duration distribution — adaptive (binned)')
        plt.tight_layout()
        out = os.path.join(PLOTS, 'aggregate_durations_barchart_adaptive_only.png')
        fig.savefig(out, dpi=300)
        fig.savefig(out.rsplit('.',1)[0] + '.svg')
        plt.close(fig)
        print('Wrote', out)
        return

    # choose number of bins automatically based on Freedman–Diaconis or fallback
    # prepare combined values for bin-size estimation
    all_vals = [v for v in (adaptive + normal_times) if v is not None]
    try:
        q75, q25 = np.percentile(all_vals, [75, 25])
        iqr = q75 - q25
        bin_width = 2 * iqr * (len(all_vals) ** (-1/3)) if iqr > 0 else None
        if bin_width and bin_width > 0:
            bins = max(5, int(math.ceil((max(all_vals) - min(all_vals)) / bin_width)))
        else:
            bins = 10
    except Exception:
        bins = 10

    make_barchart(adaptive, normal_times, bins=bins)


if __name__ == '__main__':
    main()

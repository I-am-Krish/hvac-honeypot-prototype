"""Draw an area + line chart comparing adaptive session durations vs simulated normal durations.

Outputs:
 - scripts/plots/aggregate_durations_area.png
 - scripts/plots/aggregate_durations_area.svg

This uses simple histogram densities with light smoothing (moving average) and
plots filled area plus a line for each series. If no normal durations are
available it will plot only the adaptive density.
"""
import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.dirname(__file__)
PLOTS = os.path.join(ROOT, 'plots')
os.makedirs(PLOTS, exist_ok=True)

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from simulator.room import RoomSimulator

SESSIONS_CSV = os.path.join(ROOT, 'engagement_sessions.csv')
LOG_PATH = os.path.join(os.path.dirname(ROOT), 'logs', 'events.csv')


def load_sessions():
    if not os.path.exists(SESSIONS_CSV):
        raise FileNotFoundError(SESSIONS_CSV)
    return pd.read_csv(SESSIONS_CSV)


def load_events():
    if not os.path.exists(LOG_PATH):
        raise FileNotFoundError(LOG_PATH)
    df = pd.read_csv(LOG_PATH)
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
            if sim.T < 18.0 or sim.T > 26.0:
                crossed = sim_time
                break
        if crossed is not None:
            break
    return crossed


def smooth(y, window=5):
    if window <= 1:
        return y
    w = np.ones(window) / window
    return np.convolve(y, w, mode='same')


def plot_area(adaptive, normal, bins=50, out_png=os.path.join(PLOTS, 'aggregate_durations_area.png')):
    # shared x grid
    all_vals = np.array([v for v in (adaptive + normal) if v is not None]) if normal else np.array(adaptive)
    if all_vals.size == 0:
        raise ValueError('No values to plot')
    xmin = 0
    xmax = max(1, np.percentile(all_vals, 99))
    # compute histograms as densities on a common bin grid
    edges = np.linspace(xmin, xmax, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2.0

    ha, _ = np.histogram(adaptive, bins=edges, density=True)
    ha = smooth(ha, window=max(3, int(bins/50)))

    if normal:
        hn, _ = np.histogram(normal, bins=edges, density=True)
        hn = smooth(hn, window=max(3, int(bins/50)))
    else:
        hn = None

    fig, ax = plt.subplots(figsize=(10,5))
    # adaptive area + line
    ax.fill_between(centers, ha, color='#4C72B0', alpha=0.35, label='Adaptive (density)')
    ax.plot(centers, ha, color='#4C72B0', linewidth=2)

    if hn is not None:
        ax.fill_between(centers, hn, color='#DD8452', alpha=0.25, label='Normal (simulated density)')
        ax.plot(centers, hn, color='#DD8452', linewidth=2)

    ax.set_xlabel('Duration (s)')
    ax.set_ylabel('Density')
    ax.set_title('Session duration density — adaptive vs normal')
    ax.legend()
    plt.tight_layout()
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_png.rsplit('.',1)[0] + '.svg')
    plt.close(fig)
    print('Wrote', out_png)


def main():
    sessions = load_sessions()
    events = load_events()
    adaptive = sessions['duration_s'].dropna().astype(float).tolist()
    normal = []
    for _, row in sessions.iterrows():
        client = row['client']
        start_ts = int(row['start_ts'])
        end_ts = int(row['end_ts'])
        t = simulate_normal_time_for_session(events, client, start_ts, end_ts)
        if t is not None:
            normal.append(float(t))

    plot_area(adaptive, normal, bins=80)


if __name__ == '__main__':
    main()

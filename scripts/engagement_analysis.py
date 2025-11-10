"""scripts/engagement_analysis.py

Simple offline analyzer that computes engagement sessions from logs/events.csv.
It groups events by `client_ip` if present, otherwise by `role`, and splits sessions
when the gap between consecutive events exceeds a threshold (default 120s).

Outputs: scripts/engagement_sessions.csv and prints a short summary.
"""
import os
import csv
import time
from datetime import datetime
import argparse
import pandas as pd
import matplotlib.pyplot as plt

# import simulator for normal-honeypot simulation
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from simulator.room import RoomSimulator

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "events.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__), "engagement_sessions.csv")
PLOTS_DIR = os.path.join(os.path.dirname(__file__), "plots")

os.makedirs(PLOTS_DIR, exist_ok=True)

def load_logs(path=LOG_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Log file not found: {path}")
    df = pd.read_csv(path)
    # Ensure ts is integer
    if 'ts' in df.columns:
        df['ts'] = df['ts'].astype(int)
    else:
        raise KeyError('ts column missing from log')
    return df

def annotate_with_ml(df):
    # Try to use ml.predictor if available to add a per-event attacker score/label
    try:
        from ml import predictor
        predictor.load()
        labels = []
        scores = []
        for _, row in df.iterrows():
            ev = {
                'requested_power': row.get('requested_power', 0),
                'applied_power': row.get('applied_power', 0),
                'temperature': row.get('temperature', 0),
                'override': row.get('override', False)
            }
            r = predictor.predict_event(ev)
            labels.append(r['label'])
            scores.append(r['score'])
        df['ml_label'] = labels
        df['ml_score'] = scores
    except Exception as e:
        # silently continue if ML not available
        df['ml_label'] = None
        df['ml_score'] = None
    return df

def sessionize_events(df, id_field, gap_threshold=120):
    sessions = []
    for client, group in df.groupby(id_field):
        g = group.sort_values('ts')
        start = None
        end = None
        ev_count = 0
        overrides = 0
        scores = []
        prev_ts = None
        for _, r in g.iterrows():
            ts = int(r['ts'])
            if start is None:
                # start new session
                start = ts
                end = ts
                ev_count = 1
                overrides = 1 if bool(r.get('override', False)) else 0
                if r.get('ml_score') is not None:
                    scores = [r.get('ml_score')]
                prev_ts = ts
            else:
                if ts - prev_ts > gap_threshold:
                    # close previous session
                    sessions.append({
                        'client': client,
                        'start_ts': start,
                        'end_ts': end,
                        'duration_s': end - start,
                        'event_count': ev_count,
                        'override_count': overrides,
                        'avg_ml_score': (sum(scores)/len(scores)) if scores else None
                    })
                    # start new
                    start = ts
                    end = ts
                    ev_count = 1
                    overrides = 1 if bool(r.get('override', False)) else 0
                    scores = [r.get('ml_score')] if r.get('ml_score') is not None else []
                    prev_ts = ts
                else:
                    # continue session
                    end = ts
                    ev_count += 1
                    if bool(r.get('override', False)):
                        overrides += 1
                    if r.get('ml_score') is not None:
                        scores.append(r.get('ml_score'))
                    prev_ts = ts
        # append last session for this client
        if start is not None:
            sessions.append({
                'client': client,
                'start_ts': start,
                'end_ts': end,
                'duration_s': end - start,
                'event_count': ev_count,
                'override_count': overrides,
                'avg_ml_score': (sum(scores)/len(scores)) if scores else None
            })
    return sessions

def ts_to_iso(ts):
    try:
        return datetime.utcfromtimestamp(int(ts)).isoformat() + 'Z'
    except Exception:
        return str(ts)

def plot_session(df, client, start_ts, end_ts, simulate_normal=False, outdir=PLOTS_DIR):
    # filter events for client and time range, only 'event' rows (skip system markers)
    sel = df[(df.get('client_ip', df.get('role')) == client) & (df['ts'] >= start_ts) & (df['ts'] <= end_ts)]
    # If event_type column exists, filter to event rows
    if 'event_type' in sel.columns:
        sel = sel[sel['event_type'] == 'event']
    sel = sel.sort_values('ts').reset_index(drop=True)
    if sel.empty:
        return None

    times = [datetime.utcfromtimestamp(int(t)) for t in sel['ts']]
    req = sel['requested_power'].fillna(0).astype(float)
    app = sel['applied_power'].fillna(0).astype(float)
    temp = sel['temperature'].fillna(method='ffill')

    plt.figure(figsize=(10,5))
    plt.step(times, req, where='post', label='requested_power', color='red', alpha=0.7)
    plt.step(times, app, where='post', label='applied_power (adaptive)', color='blue', alpha=0.7)
    plt.plot(times, temp, label='recorded_temperature', color='green')

    if simulate_normal:
        # simulate temperature if SCC had not applied overrides (applied=requested)
        sim = RoomSimulator(T0=float(temp.iloc[0]) if not temp.isnull().all() else 22.0)
        temps_norm = []
        for p in req:
            temps_norm.append(sim.step(P_heater=float(p)))
        plt.plot(times, temps_norm, label='simulated_temperature (normal honeypot)', color='orange', linestyle='--')

    plt.title(f'Client {client} session {ts_to_iso(start_ts)}')
    plt.xlabel('Time')
    plt.ylabel('Power / Temperature')
    plt.legend()
    plt.grid(alpha=0.3)
    fname = os.path.join(outdir, f'session_{client}_{start_ts}.png')
    plt.tight_layout()
    plt.savefig(fname)
    plt.close()
    return fname


def main():
    parser = argparse.ArgumentParser(description='Engagement analysis and visualization')
    parser.add_argument('--log', default=LOG_PATH, help='Path to events.csv')
    parser.add_argument('--out', default=OUT_PATH, help='Output sessions CSV')
    parser.add_argument('--gap', default=120, type=int, help='Session gap threshold (s)')
    parser.add_argument('--plots', action='store_true', help='Generate per-session plots')
    parser.add_argument('--simulate-normal', action='store_true', help='Also simulate normal honeypot (no SCC) for comparison')
    args = parser.parse_args()

    df = load_logs(args.log)
    df = annotate_with_ml(df)
    # decide identity field
    if 'client_ip' in df.columns:
        id_field = 'client_ip'
    else:
        id_field = 'role'

    sessions = sessionize_events(df, id_field, gap_threshold=args.gap)
    if not sessions:
        print('No sessions found')
        return
    # write sessions to CSV
    with open(args.out, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['client','start_ts','start_iso','end_ts','end_iso','duration_s','event_count','override_count','avg_ml_score'])
        for s in sessions:
            writer.writerow([s['client'], s['start_ts'], ts_to_iso(s['start_ts']), s['end_ts'], ts_to_iso(s['end_ts']), s['duration_s'], s['event_count'], s['override_count'], s['avg_ml_score']])

    # summary
    durations = [s['duration_s'] for s in sessions]
    counts = [s['event_count'] for s in sessions]
    overrides = [s['override_count'] for s in sessions]
    print(f"Found {len(sessions)} session(s) grouped by '{id_field}'")
    print(f"Total events: {len(df)}")
    print(f"Session durations (s): min={min(durations)}, max={max(durations)}, mean={sum(durations)/len(durations):.1f}")
    print(f"Events per session: min={min(counts)}, max={max(counts)}, mean={sum(counts)/len(counts):.1f}")
    print(f"Overrides per session (sum/mean): {sum(overrides)}/{(sum(overrides)/len(overrides)):.1f}")
    print(f"Wrote sessions to: {args.out}")

    if args.plots:
        os.makedirs(PLOTS_DIR, exist_ok=True)
        print('Generating plots...')
        for s in sessions:
            try:
                fname = plot_session(df, s['client'], s['start_ts'], s['end_ts'], simulate_normal=args.simulate_normal, outdir=PLOTS_DIR)
                if fname:
                    print('Wrote plot:', fname)
            except Exception as e:
                print('Failed to plot session', s['client'], s['start_ts'], e)

        # --- compute normal-honeypot time-to-cross-safety per session ---
        normal_times = []
        # load scc config for bounds
        try:
            cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scc', 'config.yaml')
            with open(cfg_path, 'r') as f:
                import yaml
                scc_cfg = yaml.safe_load(f)
            T_min = float(scc_cfg.get('T_min', 18.0))
            T_max = float(scc_cfg.get('T_max', 26.0))
        except Exception:
            T_min, T_max = 18.0, 26.0

        for s in sessions:
            sel = df[(df.get('client_ip', df.get('role')) == s['client']) & (df['ts'] >= s['start_ts']) & (df['ts'] <= s['end_ts'])]
            if 'event_type' in sel.columns:
                sel = sel[sel['event_type'] == 'event']
            sel = sel.sort_values('ts').reset_index(drop=True)
            if sel.empty:
                normal_times.append(None)
                continue
            # initial temperature
            if 'temperature' in sel.columns and not sel['temperature'].isnull().all():
                T0 = float(sel['temperature'].iloc[0])
            else:
                T0 = 22.0
            sim = RoomSimulator(T0=T0)
            crossed = None
            sim_time = 0
            for i, row in sel.iterrows():
                p = float(row.get('requested_power', 0) or 0)
                if i < len(sel) - 1:
                    next_ts = int(sel.loc[i+1, 'ts'])
                    gap = max(1, next_ts - int(row['ts']))
                else:
                    gap = int(sim.dt)
                remaining = gap
                while remaining > 0:
                    sim.step(P_heater=p)
                    sim_time += sim.dt
                    remaining -= sim.dt
                    if sim.T < T_min or sim.T > T_max:
                        crossed = sim_time
                        break
                if crossed is not None:
                    break
            normal_times.append(crossed)

        # aggregate comparison plots
        adaptive = [s['duration_s'] for s in sessions]
        # treat None as large value for plotting; filter separately
        normal_filtered = [t for t in normal_times if t is not None]

        if normal_filtered:
            plt.figure(figsize=(8,5))
            plt.hist(adaptive, bins=10, alpha=0.6, label='adaptive (recorded)', color='blue')
            plt.hist(normal_filtered, bins=10, alpha=0.6, label='normal (time-to-cross)', color='orange')
            plt.xlabel('Duration (s)')
            plt.ylabel('Count')
            plt.title('Session durations: adaptive vs normal (simulated)')
            plt.legend()
            agg_hist = os.path.join(PLOTS_DIR, 'aggregate_durations_hist.png')
            plt.tight_layout()
            plt.savefig(agg_hist)
            plt.close()

            plt.figure(figsize=(6,5))
            plt.boxplot([adaptive, normal_filtered], labels=['adaptive', 'normal'])
            plt.title('Session duration distribution')
            agg_box = os.path.join(PLOTS_DIR, 'aggregate_durations_box.png')
            plt.tight_layout()
            plt.savefig(agg_box)
            plt.close()
            print('Wrote aggregate plots:', agg_hist, agg_box)
        else:
            print('No normal-cross events simulated (no crossings), skipped aggregate plots for normal')

if __name__ == '__main__':
    main()

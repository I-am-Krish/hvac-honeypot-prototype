"""Compare current experiment metrics with baseline values and produce a bar chart.

Produces:
 - scripts/comparison_results.csv
 - scripts/plots/comparison_bar.png

Baseline defaults are inlined but can be edited in the script or replaced by a JSON file.
"""
import os
import csv
import json
from collections import Counter
import math
import psutil
import pandas as pd
import matplotlib.pyplot as plt
try:
    import seaborn as sns
except Exception:
    sns = None

ROOT = os.path.dirname(__file__)
PLOTS = os.path.join(ROOT, 'plots')
os.makedirs(PLOTS, exist_ok=True)

# baseline defaults (placeholder values). Replace with web-derived numbers if available.
BASELINE = {
    # average session duration in seconds for a typical 'normal' honeypot
    'engagement_duration_s': 300.0,
    # detection resistance (probability of not being identified), 0..1
    'detection_resistance': 0.35,
    # policy adaptation latency in seconds (how quickly policy updates/responds)
    'policy_adaptation_latency_s': 180.0,
    # resource overhead: CPU% (average) + memory (MB) combined metric (lower better).
    'resource_overhead_score': 0.2,
    # threat intelligence yield: score 0..1 measuring diversity and quality
    'threat_intel_yield': 0.4
}

# If a baseline.json exists, load and override BASELINE with its 'baseline' block
try:
    baseline_path = os.path.join(ROOT, 'baseline.json')
    if os.path.exists(baseline_path):
        with open(baseline_path, 'r', encoding='utf-8') as f:
            bj = json.load(f)
            if 'baseline' in bj:
                BASELINE.update(bj['baseline'])
                print('Loaded baseline values from', baseline_path)
except Exception as e:
    print('Could not load baseline.json:', e)

OUT_CSV = os.path.join(ROOT, 'comparison_results.csv')

def load_sessions(path=os.path.join(ROOT, 'engagement_sessions.csv')):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    return df

def metric_engagement_duration(sessions_df):
    # average duration_s
    return float(sessions_df['duration_s'].dropna().mean())

def metric_detection_resistance(events_path=os.path.join(os.path.dirname(ROOT), 'logs', 'events.csv')):
    # Improved heuristic:
    # For each session (group by client_ip or role) compute signals that indicate detection:
    # - session ends shortly after a server-side override (client likely detected behavior)
    # - client issues known reconnaissance methods (HEAD, OPTIONS) repeatedly and then stops
    # We'll mark a session as 'likely not detected' if the client continues interacting for at least 3 events after an override
    # or never saw an override and had >1 events. Returns fraction of sessions that appear resistant (0..1).
    if not os.path.exists(events_path):
        return None
    df = pd.read_csv(events_path)
    # group by client_ip or role
    id_field = 'client_ip' if 'client_ip' in df.columns else 'role'
    resist_count = 0
    total = 0
    for client, g in df.groupby(id_field):
        g = g.sort_values('ts').reset_index(drop=True)
        total += 1
        events = len(g)
        if events == 0:
            continue
        # find override indices
        if 'override' in g.columns:
            overrides = g[g['override'].astype(str).isin(['True', 'true', '1', 'YES', 'Yes'])]
            if not overrides.empty:
                first_idx = overrides.index[0]
                # number of events after override
                after = len(g[g.index > first_idx])
                # if client keeps interacting for >=3 events after override -> resistant
                if after >= 3:
                    resist_count += 1
                # if client never continued (after 0) -> likely detected
            else:
                # no override observed: if >1 events then likely not detected (engaged)
                if events > 1:
                    resist_count += 1
        else:
            # no override column: use events heuristic
            if events > 1:
                resist_count += 1
    return resist_count / max(1, total)

def metric_policy_adaptation_latency(events_path=os.path.join(os.path.dirname(ROOT), 'logs', 'events.csv')):
    # Improved: compute both median and mean latency from first non-system event (session start) to the first override within that session.
    # Ignore sessions with no override. Return median; also write mean into CSV later if needed.
    if not os.path.exists(events_path):
        return None
    df = pd.read_csv(events_path)
    id_field = 'client_ip' if 'client_ip' in df.columns else 'role'
    latencies = []
    for client, g in df.groupby(id_field):
        g = g.sort_values('ts').reset_index(drop=True)
        # start_ts: first non-system event timestamp
        non_system = g[g.get('event_type', '') != 'engagement_start'] if 'event_type' in g.columns else g
        if non_system.empty:
            start_ts = int(g.iloc[0]['ts'])
        else:
            start_ts = int(non_system.iloc[0]['ts'])
        # first override
        if 'override' in g.columns:
            overrides = g[g['override'].astype(str).isin(['True', 'true', '1', 'YES', 'Yes'])]
            if not overrides.empty:
                first_override_ts = int(overrides.iloc[0]['ts'])
                delta = first_override_ts - start_ts
                if delta >= 0:
                    latencies.append(delta)
    if not latencies:
        return None
    ser = pd.Series(latencies)
    return float(ser.median())

def metric_resource_overhead():
    # Improved snapshot: if a resource usage log exists (logs/resource_usage.csv), use that time-series; otherwise sample Python processes several times
    usage_log = os.path.join(os.path.dirname(ROOT), 'logs', 'resource_usage.csv')
    if os.path.exists(usage_log):
        try:
            r = pd.read_csv(usage_log)
            # expect columns: timestamp,cpu_percent,memory_mb
            cpu = r['cpu_percent'].mean()
            mem_mb = r['memory_mb'].mean()
        except Exception:
            cpu = None
            mem_mb = None
    else:
        # sample 5 times at 0.2s intervals
        procs = [p for p in psutil.process_iter(['name','username','cpu_percent','memory_info']) if p.info['name'] and 'python' in p.info['name'].lower()]
        if not procs:
            return None
        cpu_samples = []
        mem_samples = []
        for _ in range(5):
            cpu = sum((p.cpu_percent(interval=0.2) for p in procs))
            mem_mb = sum((p.info['memory_info'].rss for p in procs)) / (1024*1024)
            cpu_samples.append(cpu)
            mem_samples.append(mem_mb)
        cpu = float(pd.Series(cpu_samples).mean())
        mem_mb = float(pd.Series(mem_samples).mean())
    # Combine into a 0..1 score
    cpu_norm = min(max(cpu/100.0, 0.0), 1.0) if cpu is not None else 0.0
    mem_norm = min(max(mem_mb/1000.0, 0.0), 1.0) if mem_mb is not None else 0.0
    score = 0.6 * cpu_norm + 0.4 * mem_norm
    return float(score)

def metric_threat_intel_yield(events_path=os.path.join(os.path.dirname(ROOT), 'logs', 'events.csv')):
    # Improved threat-intel heuristic: combine diversity (entropy) over user_agent/request_path/client_id
    # with the number of distinct payload signatures (requested_power, applied_power sequences) and count of unique paths used by 'attacker' role.
    if not os.path.exists(events_path):
        return None
    df = pd.read_csv(events_path)
    # unique clients
    ua = df['user_agent'].dropna().astype(str)
    paths = df['request_path'].dropna().astype(str)
    client_ids = df['client_id'].dropna().astype(str)
    # payload signatures
    payloads = df[['requested_power', 'applied_power']].astype(str).agg('|'.join, axis=1).dropna()
    # compute simple diversity metric (normalized entropy)
    def norm_entropy(series):
        if series.empty:
            return 0.0
        c = Counter(series)
        total = sum(c.values())
        ent = -sum((v/total) * math.log((v/total)+1e-12) for v in c.values())
        # max entropy is log(unique)
        max_ent = math.log(len(c)) if len(c)>0 else 1.0
        return ent / max_ent if max_ent>0 else 0.0
    ua_div = norm_entropy(ua)
    path_div = norm_entropy(paths)
    client_div = norm_entropy(client_ids)
    payload_div = norm_entropy(payloads)
    # combine with weights (tuneable)
    score = 0.3 * ua_div + 0.4 * path_div + 0.2 * client_div + 0.1 * payload_div
    return float(score)

def make_comparison(metrics, baseline=BASELINE, out_png=os.path.join(PLOTS, 'comparison_bar.png')):
    # metrics: dict with keys matching baseline keys
    keys = ['engagement_duration_s', 'detection_resistance', 'policy_adaptation_latency_s', 'resource_overhead_score', 'threat_intel_yield']
    # normalize each metric to 0..1 for display and ensure directionality (higher-is-better)
    values_adaptive = []
    values_baseline = []
    labels = ['Engagement Duration', 'Detection Resistance', 'Policy Adaptation (fast better)', 'Resource Overhead (low better)', 'Threat Intel Yield']
    for k in keys:
        a = metrics.get(k)
        b = baseline.get(k)
        # simple normalization per metric type
        if k == 'engagement_duration_s':
            # baseline and adaptive normalized by max(b*3, a, b)
            m = max(b*3, a or 0, b)
            a_n = (a or 0)/m
            b_n = b/m
        elif k == 'policy_adaptation_latency_s':
            # lower is better; invert
            maxv = max(b*3, a or 0, b)
            a_n = 1.0 - ((a or 0)/maxv)
            b_n = 1.0 - (b/maxv)
        elif k == 'resource_overhead_score':
            # lower better; invert
            maxv = max(1.0, a or 0, b)
            a_n = 1.0 - min((a or 0)/maxv, 1.0)
            b_n = 1.0 - min(b/maxv, 1.0)
        else:
            # assume 0..1 already
            a_n = float(a or 0)
            b_n = float(b or 0)
        values_adaptive.append(a_n)
        values_baseline.append(b_n)

    # Use seaborn for a cleaner aesthetic if available, otherwise fall back to matplotlib styles
    if sns is not None:
        sns.set(style='whitegrid')
    else:
        # seaborn not available; use matplotlib built-in 'ggplot' style for clean visuals
        plt.style.use('ggplot')

    n = len(labels)
    x = list(range(n))
    width = 0.38

    # larger canvas and constrained layout to avoid overlaps
    fig = plt.figure(figsize=(14, 8), constrained_layout=True)
    ax = fig.add_subplot(111)

    # Colors and per-bar coloring depending on whether adaptive improved over baseline
    if sns is not None:
        palette = sns.color_palette('muted')
        base_color = palette[0]
    else:
        base_color = '#4C72B0'  # blue

    # Decide directionality: True if higher is better
    direction_higher_better = {
        'engagement_duration_s': True,
        'detection_resistance': True,
        'policy_adaptation_latency_s': False,  # lower latency better
        'resource_overhead_score': False,      # lower overhead better
        'threat_intel_yield': True
    }

    adapt_colors = []
    for k, a_val, b_val in zip(keys, values_adaptive, values_baseline):
        # compare considering direction
        higher_better = direction_higher_better.get(k, True)
        improved = (a_val > b_val) if higher_better else (a_val < b_val)
        adapt_colors.append('#2ca02c' if improved else '#d62728')  # green/red

    # Baseline bars (single color)
    bars1 = ax.bar([i - width/2 for i in x], values_baseline, width,
                   label='Baseline (public)', color=base_color, edgecolor='k', alpha=0.9)
    # Adaptive bars (color per-metric)
    bars2 = ax.bar([i + width/2 for i in x], values_adaptive, width,
                   label='Adaptive (this run)', color=adapt_colors, edgecolor='k', alpha=0.95)

    # Labels and ticks
    ax.set_xticks(x)
    # rotate further and align right so long labels don't overlap
    ax.set_xticklabels(labels, rotation=28, ha='right', fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_ylabel('Normalized score (0..1)', fontsize=11)
    ax.set_title('Adaptive honeypot vs baseline — engagement metrics', fontsize=16, weight='bold')

    # Annotate bars with human-friendly original values and an up/down marker
    def format_display(k, raw):
        if raw is None:
            return 'n/a'
        if k == 'engagement_duration_s' or k == 'policy_adaptation_latency_s':
            return f"{int(raw)}s"
        if k == 'detection_resistance':
            return f"{raw:.0%}"
        return f"{raw:.3f}"

    for i, (k, bar_b, bar_a) in enumerate(zip(keys, bars1, bars2)):
        # baseline annotation (above baseline bar)
        bv = baseline.get(k)
        av = metrics.get(k)
        b_text = format_display(k, bv)
        a_text = format_display(k, av)

        # position baseline label
        h_b = bar_b.get_height()
        ax.annotate(b_text, xy=(bar_b.get_x() + bar_b.get_width()/2, h_b),
                    xytext=(0, 6), textcoords='offset points', ha='center', va='bottom', fontsize=9,
                    color='black')

        # position adaptive label; if near top put inside with white text
        h_a = bar_a.get_height()
        if h_a > 0.9:
            ax.annotate(a_text, xy=(bar_a.get_x() + bar_a.get_width()/2, h_a - 0.02),
                        xytext=(0, 0), textcoords='offset points', ha='center', va='top', fontsize=9,
                        color='white', weight='bold')
        else:
            ax.annotate(a_text, xy=(bar_a.get_x() + bar_a.get_width()/2, h_a),
                        xytext=(0, 6), textcoords='offset points', ha='center', va='bottom', fontsize=9,
                        color='black')

        # add small arrow indicator showing which direction is better for clarity
        higher_better = direction_higher_better.get(k, True)
        arrow = '▲' if higher_better else '▼'
        # place arrow under the x-label for the metric
        ax.text(i, -0.08, arrow, transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=12)

    # Add a small caption explaining directionality
    caption_lines = []
    for k in keys:
        better = 'Higher' if direction_higher_better.get(k, True) else 'Lower'
        # nicer names mapping
        nice = {
            'engagement_duration_s': 'Engagement Duration',
            'detection_resistance': 'Detection Resistance',
            'policy_adaptation_latency_s': 'Policy Adaptation Latency',
            'resource_overhead_score': 'Resource Overhead',
            'threat_intel_yield': 'Threat Intel Yield'
        }.get(k, k)
        caption_lines.append(f"{nice}: better → {better}")
    caption = ' | '.join(caption_lines)
    # place caption below the plot
    fig.text(0.5, 0.02, caption, ha='center', fontsize=9, bbox=dict(facecolor='white', alpha=0.8, pad=4))

    # Legend and final layout tweaks
    ax.legend(frameon=True, loc='upper right')
    # ensure no clipping of labels
    plt.subplots_adjust(bottom=0.18)

    # Save high-res PNG and SVG for crisp reports
    fig.savefig(out_png, dpi=300)
    svg_out = out_png.rsplit('.', 1)[0] + '.svg'
    fig.savefig(svg_out)
    plt.close(fig)
    return out_png

def write_results_csv(metrics, baseline=BASELINE, path=OUT_CSV):
    fieldnames = ['metric','baseline_value','adaptive_value']
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(fieldnames)
        for k,v in baseline.items():
            w.writerow([k, v, metrics.get(k)])

def main():
    sessions = load_sessions()
    metrics = {}
    metrics['engagement_duration_s'] = metric_engagement_duration(sessions)
    metrics['detection_resistance'] = metric_detection_resistance()
    metrics['policy_adaptation_latency_s'] = metric_policy_adaptation_latency()
    metrics['resource_overhead_score'] = metric_resource_overhead()
    metrics['threat_intel_yield'] = metric_threat_intel_yield()

    write_results_csv(metrics)
    out_png = make_comparison(metrics)
    print('Wrote comparison CSV:', OUT_CSV)
    print('Wrote comparison plot:', out_png)

if __name__ == '__main__':
    main()

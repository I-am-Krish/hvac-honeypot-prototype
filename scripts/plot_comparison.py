"""Generate an editable grouped bar chart from comparison_results.csv.

This script is intentionally straightforward so you can edit colors, labels,
and normalization defaults directly. It reads `scripts/comparison_results.csv`
and `scripts/baseline.json` (for metadata) and writes `scripts/plots/custom_comparison.png`.

Usage:
    python scripts/plot_comparison.py

Make edits to the CONFIG dict near the top to change appearance.
"""
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
try:
    import seaborn as sns
except Exception:
    sns = None

ROOT = os.path.dirname(__file__)
PLOTS_DIR = os.path.join(ROOT, 'plots')
os.makedirs(PLOTS_DIR, exist_ok=True)

# ---- CONFIG: edit these values to change the plot appearance ----
CONFIG = {
    'normalize': True,           # True: normalize metrics to 0..1 (for side-by-side); False: show raw values per-metric
    'figsize': (12, 7),
    'baseline_color': '#4C72B0',
    'adaptive_color_good': '#2ca02c',
    'adaptive_color_bad': '#d62728',
    'bar_width': 0.36,
    'annot_fontsize': 10,
    'title': 'Adaptive vs Baseline (customizable)'
}


def load_data():
    csv_path = os.path.join(ROOT, 'comparison_results.csv')
    baseline_path = os.path.join(ROOT, 'baseline.json')
    df = pd.read_csv(csv_path)
    baseline = {}
    if os.path.exists(baseline_path):
        with open(baseline_path, 'r', encoding='utf-8') as f:
            bj = json.load(f)
            baseline = bj.get('baseline', {})
    return df, baseline


def nicer_label(key):
    return {
        'engagement_duration_s': 'Engagement Duration (s)',
        'detection_resistance': 'Detection Resistance',
        'policy_adaptation_latency_s': 'Policy Adaptation Latency (s)',
        'resource_overhead_score': 'Resource Overhead',
        'threat_intel_yield': 'Threat Intel Yield'
    }.get(key, key)


def is_higher_better(key):
    return {
        'engagement_duration_s': True,
        'detection_resistance': True,
        'policy_adaptation_latency_s': False,
        'resource_overhead_score': False,
        'threat_intel_yield': True
    }.get(key, True)


def plot(df, baseline, out_png=os.path.join(PLOTS_DIR, 'custom_comparison.png')):
    keys = df['metric'].tolist()
    base_vals = [float(x) for x in df['baseline_value'].tolist()]
    adapt_vals = [float(x) for x in df['adaptive_value'].tolist()]

    labels = [nicer_label(k) for k in keys]

    # normalize to 0..1 for display, per script defaults
    if CONFIG['normalize']:
        norm_base = []
        norm_adapt = []
        for k, b, a in zip(keys, base_vals, adapt_vals):
            if k in ('engagement_duration_s', 'policy_adaptation_latency_s'):
                maxv = max(b * 3, a, b, 1)
                nb = b / maxv
                na = a / maxv
            elif k == 'resource_overhead_score':
                maxv = max(1.0, a, b)
                nb = 1.0 - min(b / maxv, 1.0)
                na = 1.0 - min(a / maxv, 1.0)
            else:
                # already 0..1
                nb = b
                na = a
            norm_base.append(nb)
            norm_adapt.append(na)
        plot_base = norm_base
        plot_adapt = norm_adapt
        y_label = 'Normalized score (0..1)'
    else:
        plot_base = base_vals
        plot_adapt = adapt_vals
        y_label = 'Value (raw)'

    if sns is not None:
        sns.set(style='whitegrid')
    else:
        plt.style.use('ggplot')

    fig, ax = plt.subplots(figsize=CONFIG['figsize'])
    n = len(labels)
    x = list(range(n))
    w = CONFIG['bar_width']

    # decide adaptive colors per-metric depending on whether it's improved
    adapt_colors = []
    for k, a, b in zip(keys, plot_adapt, plot_base):
        hb = is_higher_better(k)
        improved = (a > b) if hb else (a < b)
        adapt_colors.append(CONFIG['adaptive_color_good'] if improved else CONFIG['adaptive_color_bad'])

    bars_b = ax.bar([i - w / 2 for i in x], plot_base, w, label='Baseline', color=CONFIG['baseline_color'], edgecolor='k')
    bars_a = ax.bar([i + w / 2 for i in x], plot_adapt, w, label='Adaptive', color=adapt_colors, edgecolor='k')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha='right')
    ax.set_ylim(0, 1 if CONFIG['normalize'] else max(max(plot_base), max(plot_adapt)) * 1.1)
    ax.set_ylabel(y_label)
    ax.set_title(CONFIG['title'])
    ax.legend()

    # annotate with raw values
    for bar, raw in zip(bars_b, base_vals):
        h = bar.get_height()
        ax.annotate(f"{raw}", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 6), textcoords='offset points', ha='center', va='bottom', fontsize=CONFIG['annot_fontsize'])
    for bar, raw in zip(bars_a, adapt_vals):
        h = bar.get_height()
        ax.annotate(f"{raw}", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 6), textcoords='offset points', ha='center', va='bottom', fontsize=CONFIG['annot_fontsize'])

    plt.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    print('Wrote', out_png)


def main():
    df, baseline = load_data()
    plot(df, baseline)


if __name__ == '__main__':
    main()

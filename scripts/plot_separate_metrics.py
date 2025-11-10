"""Generate one focused plot per metric (baseline vs adaptive).

Produces files in `scripts/plots/`:
 - engagement_duration_s.png/.svg
 - detection_resistance.png/.svg
 - policy_adaptation_latency_s.png/.svg
 - resource_overhead_score.png/.svg
 - threat_intel_yield.png/.svg

Each plot uses raw values and clearly annotates which direction is better.
"""
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
try:
    import seaborn as sns
except Exception:
    sns = None

ROOT = os.path.dirname(__file__)
PLOTS = os.path.join(ROOT, 'plots')
os.makedirs(PLOTS, exist_ok=True)

METRIC_INFO = {
    'engagement_duration_s': {
        'label': 'Engagement Duration (s)',
        'better': 'Higher',
        'fmt': '{:.0f}s'
    },
    'detection_resistance': {
        'label': 'Detection Resistance',
        'better': 'Higher',
        'fmt': '{:.0%}'
    },
    'policy_adaptation_latency_s': {
        'label': 'Policy Adaptation Latency (s)',
        'better': 'Lower',
        'fmt': '{:.0f}s'
    },
    'resource_overhead_score': {
        'label': 'Resource Overhead (score)',
        'better': 'Lower',
        'fmt': '{:.3f}'
    },
    'threat_intel_yield': {
        'label': 'Threat Intel Yield (score)',
        'better': 'Higher',
        'fmt': '{:.3f}'
    }
}


def load_data():
    csv_path = os.path.join(ROOT, 'comparison_results.csv')
    baseline_path = os.path.join(ROOT, 'baseline.json')
    df = pd.read_csv(csv_path)
    baseline = {}
    if os.path.exists(baseline_path):
        with open(baseline_path, 'r', encoding='utf-8') as f:
            baseline = json.load(f).get('baseline', {})
    return df, baseline


def plot_metric(key, bval, aval, info, out_png):
    if sns is not None:
        sns.set(style='whitegrid')
    else:
        plt.style.use('ggplot')

    labels = ['Baseline', 'Adaptive']
    values = [bval, aval]

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = ['#4C72B0', '#2ca02c' if (info['better']=='Higher' and aval> bval) or (info['better']=='Lower' and aval < bval) else '#d62728']
    bars = ax.bar(labels, values, color=colors, edgecolor='k')

    ax.set_title(info['label'], fontsize=12, weight='bold')
    ax.set_ylabel('Value')

    # annotate raw values
    for bar, val in zip(bars, values):
        h = bar.get_height()
        ax.annotate(info['fmt'].format(val), xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 6), textcoords='offset points', ha='center', va='bottom', fontsize=10)

    # add a small text explaining which direction is better
    ax.text(0.5, -0.18, f"Better → {info['better']}", transform=ax.transAxes, ha='center', fontsize=10, bbox=dict(facecolor='white', alpha=0.7))

    plt.tight_layout()
    fig.savefig(out_png, dpi=300)
    svg_out = out_png.rsplit('.',1)[0] + '.svg'
    fig.savefig(svg_out)
    plt.close(fig)


def main():
    df, baseline = load_data()
    for _, row in df.iterrows():
        metric = row['metric']
        b = float(row['baseline_value'])
        a = float(row['adaptive_value'])
        info = METRIC_INFO.get(metric, {'label': metric, 'better': 'Higher', 'fmt': '{:.3f}'})
        safe_name = metric
        out_png = os.path.join(PLOTS, f"{safe_name}.png")
        plot_metric(metric, b, a, info, out_png)
        print('Wrote', out_png)


if __name__ == '__main__':
    main()

"""Streamlit UI to tweak the comparison bar chart interactively.

Run with:
    pip install streamlit
    streamlit run scripts/plot_comparison_ui.py

The app exposes toggles for normalization, colors, and annotations so you can
edit visually and export a PNG using Streamlit's built-in download or a right-click.
"""
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
try:
    import seaborn as sns
except Exception:
    sns = None

ROOT = os.path.dirname(__file__)

@st.cache_data
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


def normalize_values(keys, base_vals, adapt_vals):
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
            nb = b
            na = a
        norm_base.append(nb)
        norm_adapt.append(na)
    return norm_base, norm_adapt


def plot_matplotlib(labels, plot_base, plot_adapt, base_vals, adapt_vals, baseline_color, adapt_colors, normalize):
    fig, ax = plt.subplots(figsize=(12, 6))
    n = len(labels)
    x = list(range(n))
    w = 0.36
    bars_b = ax.bar([i - w / 2 for i in x], plot_base, w, label='Baseline', color=baseline_color, edgecolor='k')
    bars_a = ax.bar([i + w / 2 for i in x], plot_adapt, w, label='Adaptive', color=adapt_colors, edgecolor='k')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha='right')
    ax.set_ylim(0, 1 if normalize else max(max(plot_base), max(plot_adapt)) * 1.1)
    ax.set_ylabel('Normalized score (0..1)' if normalize else 'Value (raw)')
    ax.legend()
    for bar, raw in zip(bars_b, base_vals):
        h = bar.get_height()
        ax.annotate(f"{raw}", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 6), textcoords='offset points', ha='center', va='bottom', fontsize=9)
    for bar, raw in zip(bars_a, adapt_vals):
        h = bar.get_height()
        ax.annotate(f"{raw}", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 6), textcoords='offset points', ha='center', va='bottom', fontsize=9)
    plt.tight_layout()
    return fig


def main():
    st.title('Comparison: Adaptive vs Baseline')
    df, baseline = load_data()
    keys = df['metric'].tolist()
    base_vals = [float(x) for x in df['baseline_value'].tolist()]
    adapt_vals = [float(x) for x in df['adaptive_value'].tolist()]
    labels = [nicer_label(k) for k in keys]

    normalize = st.sidebar.checkbox('Normalize to 0..1 (recommended)', value=True)
    baseline_color = st.sidebar.color_picker('Baseline color', '#4C72B0')
    good_color = st.sidebar.color_picker('Adaptive (improved) color', '#2ca02c')
    bad_color = st.sidebar.color_picker('Adaptive (worse) color', '#d62728')

    if normalize:
        plot_base, plot_adapt = normalize_values(keys, base_vals, adapt_vals)
    else:
        plot_base, plot_adapt = base_vals, adapt_vals

    adapt_colors = []
    for k, a, b in zip(keys, plot_adapt, plot_base):
        hb = is_higher_better(k)
        improved = (a > b) if hb else (a < b)
        adapt_colors.append(good_color if improved else bad_color)

    fig = plot_matplotlib(labels, plot_base, plot_adapt, base_vals, adapt_vals, baseline_color, adapt_colors, normalize)

    st.pyplot(fig)
    # Provide the raw CSV so users can download
    st.download_button('Download comparison CSV', data=df.to_csv(index=False), file_name='comparison_results.csv')

    st.markdown('---')
    st.markdown('Which is better?')
    for k, b, a in zip(keys, base_vals, adapt_vals):
        hb = is_higher_better(k)
        if a == b:
            verdict = 'equal'
        else:
            if hb:
                verdict = 'Adaptive better' if a > b else 'Baseline better'
            else:
                verdict = 'Adaptive better' if a < b else 'Baseline better'
        st.write(f"**{nicer_label(k)}** — baseline: {b}  |  adaptive: {a}  →  **{verdict}**")

if __name__ == '__main__':
    main()

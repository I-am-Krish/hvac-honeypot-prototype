# ml/feature_engineer.py
import pandas as pd
import numpy as np
import os

src = 'dataset/events_combined.csv'
out = 'dataset/events_features.csv'
if not os.path.exists(src):
    raise SystemExit(f"Missing {src}")

df = pd.read_csv(src)
# ensure ts numeric and sorted
df = df.sort_values('ts').reset_index(drop=True)
df['ts'] = pd.to_numeric(df['ts'], errors='coerce').fillna(0).astype(int)

# basic numeric conversions
df['requested_power'] = pd.to_numeric(df['requested_power'], errors='coerce').fillna(0.0)
df['applied_power'] = pd.to_numeric(df['applied_power'], errors='coerce').fillna(0.0)
df['temperature'] = pd.to_numeric(df['temperature'], errors='coerce').fillna(method='ffill').fillna(0.0)
df['override'] = df['override'].astype(str).map({'True':1,'False':0}).fillna(0).astype(int)

# delta features (difference from previous row)
df['delta_requested'] = df['requested_power'].diff().fillna(0.0)
df['delta_applied'] = df['applied_power'].diff().fillna(0.0)
df['delta_temp'] = df['temperature'].diff().fillna(0.0)

# inter-arrival time (ms) from previous event
df['inter_arrival_s'] = df['ts'].diff().fillna(0.0)
# avoid zero division later
df['inter_arrival_s'] = df['inter_arrival_s'].replace(0, 0.0001)

# rolling windows (N previous events) for requested_power, applied_power
window = 3
df['rolling_req_3'] = df['requested_power'].rolling(window, min_periods=1).mean()
df['rolling_app_3'] = df['applied_power'].rolling(window, min_periods=1).mean()

# count requests in last T seconds (approx) - uses ts; this is O(n^2) naive but fine for <100k rows
def count_in_window(ts_series, idx, window_s=30):
    t = ts_series.iloc[idx]
    low = t - window_s
    # find first index >= low
    # we can use searchsorted on numpy array for speed
    arr = ts_series.values
    pos = arr.searchsorted(low, side='left')
    return idx - pos + 1  # inclusive

ts_series = df['ts']
counts = [count_in_window(ts_series, i, window_s=30) for i in range(len(df))]
df['count_last_30s'] = counts

# create target numeric
df['label'] = df['role'].map({'attacker':1,'tester':0})

# save features (keep original columns for reference too)
cols = ['ts','role','requested_power','applied_power','temperature','override',
        'delta_requested','delta_applied','delta_temp','inter_arrival_s',
        'rolling_req_3','rolling_app_3','count_last_30s','label']
df = df[cols]
os.makedirs('dataset', exist_ok=True)
df.to_csv(out, index=False)
print(f"Saved {out} rows={len(df)}")
print(df[['role']].value_counts())
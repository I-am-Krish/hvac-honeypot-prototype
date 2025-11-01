# ml/feature_utils.py
import pandas as pd
import numpy as np

def prepare_events_df(path="logs/events.csv"):
    """
    Read CSV and normalise column types.
    Expects columns: ts,role,requested_power,applied_power,temperature,override
    """
    df = pd.read_csv(path)
    # ensure types
    df['ts'] = pd.to_datetime(df['ts'], unit='s', errors='coerce')
    df['requested_power'] = df['requested_power'].astype(float)
    df['applied_power'] = df['applied_power'].astype(float)
    df['temperature'] = df['temperature'].astype(float)
    # override might be boolean string; coerce to bool/int
    df['override'] = df['override'].astype(str).map({'True':1, 'False':0, '1':1, '0':0}).fillna(0).astype(int)
    # Fill any missing ts by forward/backfill (small prototype)
    if df['ts'].isna().any():
        df['ts'] = pd.date_range(start=pd.Timestamp.now(), periods=len(df), freq='S')
    return df

def add_features(df, window_seconds=10):
    """
    Add features per event using recent history in [ts-window_seconds, ts].
    Returns feature DataFrame aligned with original df index.
    """
    df = df.copy().reset_index(drop=True)
    # base features
    df['delta_power'] = df['requested_power'] - df['applied_power']
    # previous values (lag-1)
    df['req_prev_1'] = df['requested_power'].shift(1).fillna(df['requested_power'])
    df['app_prev_1'] = df['applied_power'].shift(1).fillna(df['applied_power'])
    df['temp_prev_1'] = df['temperature'].shift(1).fillna(df['temperature'])
    # differences
    df['dtemp'] = df['temperature'] - df['temp_prev_1']
    df['dreq'] = df['requested_power'] - df['req_prev_1']
    # Rolling stats on requested_power and applied_power (last N events)
    df['req_roll_mean_3'] = df['requested_power'].rolling(3, min_periods=1).mean()
    df['app_roll_mean_3'] = df['applied_power'].rolling(3, min_periods=1).mean()
    # request rate: number of events within window_seconds
    times = pd.Series(df['ts'])
    # convert to integer seconds
    sec = times.astype('int64') // 10**9
    df['reqs_last_window'] = 0
    for i, t in enumerate(sec):
        start = t - window_seconds
        df.at[i, 'reqs_last_window'] = int(((sec >= start) & (sec <= t)).sum())
    # fraction of overrides in window
    df['overrides_last_window'] = 0.0
    for i, t in enumerate(sec):
        start = t - window_seconds
        mask = (sec >= start) & (sec <= t)
        df.at[i, 'overrides_last_window'] = df.loc[mask, 'override'].sum() / max(1, mask.sum())
    # indicator: requested_power is extreme
    df['req_is_extreme'] = ((df['requested_power'] <= 0.0) | (df['requested_power'] >= 0.95)).astype(int)
    # keep list of features
    feature_cols = [
        'requested_power','applied_power','temperature','override',
        'delta_power','req_prev_1','app_prev_1','temp_prev_1',
        'dtemp','dreq','req_roll_mean_3','app_roll_mean_3',
        'reqs_last_window','overrides_last_window','req_is_extreme'
    ]
    # ensure no NaNs
    df[feature_cols] = df[feature_cols].fillna(0.0)
    return df, feature_cols